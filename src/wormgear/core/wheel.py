"""
Wheel geometry generation using build123d.

Creates worm wheel with two options:
1. Helical: Pure helical gear teeth (flat root) - simpler, point contact
2. Hobbed/Throated: Arc-bottomed teeth that match worm curvature - better contact
"""

import logging
import math
from typing import Optional, Literal
from build123d import (
    Part, Cylinder, Align, Vector, Plane,
    BuildSketch, BuildLine, Line, Spline, make_face, loft, Axis,
    export_step,
)
from ..io.loaders import WheelParams, WormParams, AssemblyParams
from ..enums import WormProfile
from .features import (
    BoreFeature,
    KeywayFeature,
    SetScrewFeature,
    HubFeature,
    add_bore_and_keyway,
    create_hub
)

# Profile types per DIN 3975
# ZA: Straight flanks in axial section (Archimedean) - best for CNC machining
# ZK: Slightly convex flanks - better for 3D printing (reduces stress concentrations)
ProfileType = Literal["ZA", "ZK", "ZI"]

logger = logging.getLogger(__name__)


class WheelGeometry:
    """
    Generates 3D geometry for a worm wheel.

    Supports two tooth types:
    - helical: Pure helical gear teeth (no throat cut) - simpler geometry
    - hobbed: Helical teeth with toroidal throat cut - attempts to match worm

    Optionally adds bore and keyway features.
    """

    def __init__(
        self,
        params: WheelParams,
        worm_params: WormParams,
        assembly_params: AssemblyParams,
        face_width: float = None,
        throated: bool = False,
        bore: Optional[BoreFeature] = None,
        keyway: Optional[KeywayFeature] = None,
        ddcut: Optional['DDCutFeature'] = None,
        set_screw: Optional[SetScrewFeature] = None,
        hub: Optional[HubFeature] = None,
        profile: ProfileType = "ZA"
    ):
        """
        Initialize wheel geometry generator.

        Args:
            params: Wheel parameters from calculator
            worm_params: Worm parameters (needed for throating)
            assembly_params: Assembly parameters
            face_width: Wheel face width in mm (default: auto-calculated)
            throated: If True, apply throat cut (hobbed style); if False, pure helical
            bore: Optional bore feature specification
            keyway: Optional keyway feature specification (requires bore)
            set_screw: Optional set screw feature specification (requires bore)
            hub: Optional hub feature specification (flush/extended/flanged)
            profile: Tooth profile type per DIN 3975:
                     "ZA" - Straight flanks (trapezoidal) - best for CNC (default)
                     "ZK" - Slightly convex flanks - better for 3D printing
        """
        self.params = params
        self.worm_params = worm_params
        self.assembly_params = assembly_params
        self.throated = throated
        self.bore = bore
        self.keyway = keyway
        self.ddcut = ddcut
        self.set_screw = set_screw
        self.hub = hub
        self.profile = profile.upper() if isinstance(profile, str) else profile

        # Set keyway as hub type if specified
        if self.keyway is not None:
            self.keyway.is_shaft = False

        # Calculate face width if not provided
        if face_width is None:
            d1 = worm_params.pitch_diameter_mm
            ratio = assembly_params.ratio
            self.face_width = 0.73 * (d1 ** (1/3)) * math.sqrt(ratio)
            self.face_width = max(0.3 * d1, min(0.67 * d1, self.face_width))
        else:
            self.face_width = face_width

        # Cache for built geometry (avoids rebuilding on export)
        self._part = None

    def build(self) -> Part:
        """
        Build the complete wheel geometry.

        Returns:
            build123d Part object ready for export
        """
        # Return cached geometry if already built
        if self._part is not None:
            return self._part

        # Create helical gear (throating is built into the tooth profile)
        gear = self._create_helical_gear()

        # Add bore, keyway, and set screw if specified
        if self.bore is not None or self.keyway is not None or self.ddcut is not None or self.set_screw is not None:
            gear = add_bore_and_keyway(
                gear,
                part_length=self.face_width,
                bore=self.bore,
                keyway=self.keyway,
                ddcut=self.ddcut,
                set_screw=self.set_screw,
                axis=Axis.Z
            )

        # Add hub if specified (additive feature, comes after subtractive features)
        if self.hub is not None:
            bore_diameter = self.bore.diameter if self.bore is not None else None
            gear = create_hub(
                gear,
                hub=self.hub,
                wheel_face_width=self.face_width,
                wheel_root_diameter=self.params.root_diameter_mm,
                bore_diameter=bore_diameter,
                axis=Axis.Z
            )

        # Cache the built geometry
        self._part = gear
        return gear

    def _create_helical_gear(self) -> Part:
        """
        Create helical gear by extruding and twisting tooth space profiles.

        Uses extrusion with rotation rather than helix sweep to avoid
        self-intersection issues with tight helix pitches.

        For throated wheels, the tooth space profile has an arc at the root
        that matches the worm's curvature, creating the throat naturally
        as part of the tooth geometry.
        """
        z = self.params.num_teeth
        m = self.params.module_mm
        tip_radius = self.params.tip_diameter_mm / 2
        root_radius = self.params.root_diameter_mm / 2
        pitch_radius = self.params.pitch_diameter_mm / 2
        pressure_angle = math.radians(self.assembly_params.pressure_angle_deg)

        # The wheel's helix angle equals 90° - worm lead angle
        # This determines how much the teeth twist over the face width
        lead_angle = math.radians(self.worm_params.lead_angle_deg)

        # Total twist angle over face width
        # At pitch radius, the teeth advance by (face_width * tan(lead_angle)) axially
        # This corresponds to a rotation of: twist = face_width * tan(lead_angle) / pitch_radius (radians)
        twist_radians = self.face_width * math.tan(lead_angle) / pitch_radius
        twist_degrees = math.degrees(twist_radians)

        # Create gear blank
        blank = Cylinder(
            radius=tip_radius,
            height=self.face_width,
            align=(Align.CENTER, Align.CENTER, Align.CENTER)
        )

        # Calculate tooth space dimensions
        circular_pitch = math.pi * m
        space_width_pitch = circular_pitch / 2 + self.assembly_params.backlash_mm

        # Space is wider at tip, narrower at root (inverse of tooth shape)
        space_width_tip = space_width_pitch + 2 * (tip_radius - pitch_radius) * math.tan(pressure_angle)
        space_width_root = space_width_pitch - 2 * (pitch_radius - root_radius) * math.tan(pressure_angle)
        space_width_root = max(0.1 * m, space_width_root)

        half_root = space_width_root / 2
        half_tip = space_width_tip / 2

        # Extend cut beyond face to get clean edges
        extension = 0.5
        cut_height = self.face_width + 2 * extension

        # Number of sections for lofting the twisted extrusion
        num_sections = max(8, int(abs(twist_degrees) / 5) + 1)

        # For throated wheels, calculate the worm position for arc profile
        if self.throated:
            centre_distance = self.assembly_params.centre_distance_mm
            worm_tip_radius = self.worm_params.tip_diameter_mm / 2
            # Add small clearance for fit
            arc_radius = worm_tip_radius + 0.1

        # Cut tooth spaces
        gear = blank

        for i in range(z):
            base_angle = (360 / z) * i

            # Create sections along Z for lofting
            sections = []

            for s in range(num_sections):
                t = s / (num_sections - 1)  # 0 to 1
                z_pos = -cut_height / 2 + t * cut_height

                # Rotation at this Z position (linear interpolation of twist)
                rotation_at_z = -twist_degrees / 2 + t * twist_degrees
                section_angle = base_angle + rotation_at_z
                section_angle_rad = math.radians(section_angle)

                # Create profile plane at this Z, rotated appropriately
                radial = Vector(math.cos(section_angle_rad), math.sin(section_angle_rad), 0)
                tangent = Vector(-math.sin(section_angle_rad), math.cos(section_angle_rad), 0)

                # Profile plane: origin at pitch radius, X = radial outward, Y = tangential
                origin = Vector(
                    pitch_radius * math.cos(section_angle_rad),
                    pitch_radius * math.sin(section_angle_rad),
                    z_pos
                )
                profile_plane = Plane(origin=origin, x_dir=radial, z_dir=Vector(0, 0, 1))

                # Profile offsets from pitch radius (in radial direction)
                inner = root_radius - pitch_radius - 0.3  # Extend below root
                outer = tip_radius + 0.3 - pitch_radius

                # For throated wheels, the root depth varies with Z position
                # to match the worm's cylindrical surface
                if self.throated and abs(z_pos) < arc_radius:
                    # Calculate where the worm surface is at this Z
                    # Guard against floating-point precision issues at boundary
                    under_sqrt = arc_radius**2 - z_pos**2
                    if under_sqrt >= 0:
                        worm_surface_dist = centre_distance - math.sqrt(under_sqrt)
                        throated_inner = worm_surface_dist - pitch_radius
                        # Use the shallower of the two (worm surface or calculated root)
                        actual_inner = max(inner, throated_inner)
                    else:
                        # Fallback at boundary due to floating-point precision
                        actual_inner = inner
                else:
                    actual_inner = inner

                with BuildSketch(profile_plane) as sk:
                    with BuildLine():
                        if self.profile == WormProfile.ZA or self.profile == "ZA":
                            # ZA profile: Straight flanks (trapezoidal) per DIN 3975
                            # Best for CNC machining - simple, accurate, standard
                            root_left = (actual_inner, -half_root)
                            root_right = (actual_inner, half_root)
                            tip_left = (outer, -half_tip)
                            tip_right = (outer, half_tip)

                            Line(root_left, tip_left)      # Left flank (straight)
                            Line(tip_left, tip_right)      # Tip
                            Line(tip_right, root_right)    # Right flank (straight)
                            Line(root_right, root_left)    # Root (closes)

                        elif self.profile == WormProfile.ZK or self.profile == "ZK":
                            # ZK profile: Circular arc flanks per DIN 3975 Type K
                            # Biconical grinding wheel profile - convex circular arc
                            # Better for 3D printing and reduces stress concentrations

                            # Generate circular arc flanks
                            num_points = 9  # Points per flank for smooth arc
                            left_flank = []
                            right_flank = []

                            # Arc radius typically 0.4-0.5 × module for biconical cutter
                            arc_radius = 0.45 * self.params.module_mm

                            # Calculate arc center position
                            flank_height = outer - actual_inner
                            flank_width_change = half_root - half_tip

                            # Angle of straight flank for reference
                            if flank_width_change > 0 and flank_height > 0:
                                flank_angle = math.atan(flank_width_change / flank_height)
                            else:
                                flank_angle = 0

                            # Generate arc points
                            for j in range(num_points):
                                t = j / (num_points - 1)
                                r_pos = actual_inner + t * flank_height

                                # Circular arc deviation from straight line
                                linear_width = half_root + t * (half_tip - half_root)

                                # Arc bulge (circular, not parabolic)
                                arc_param = t * math.pi  # 0 to π
                                arc_bulge = arc_radius * 0.15 * math.sin(arc_param)  # Circular arc approximation

                                width = linear_width + arc_bulge
                                left_flank.append((r_pos, -width))
                                right_flank.append((r_pos, width))

                            # Build profile with circular arc flanks
                            Spline(left_flank)
                            Line(left_flank[-1], right_flank[-1])  # Tip
                            Spline(list(reversed(right_flank)))
                            Line(right_flank[0], left_flank[0])    # Root (closes)

                        elif self.profile == WormProfile.ZI or self.profile == "ZI":
                            # ZI profile: Involute helicoid per DIN 3975 Type I
                            # True involute tooth flanks for proper conjugate action

                            # Calculate base circle radius
                            pressure_angle_rad = math.radians(self.assembly_params.pressure_angle_deg)
                            base_radius = pitch_radius * math.cos(pressure_angle_rad)

                            # Generate involute flank points
                            num_points = 11  # Points per flank for smooth curve
                            left_flank = []
                            right_flank = []

                            # Involute function: inv(α) = tan(α) - α
                            def involute(alpha):
                                return math.tan(alpha) - alpha

                            # Pressure angle at pitch circle
                            inv_pitch = involute(pressure_angle_rad)

                            # Half tooth thickness at pitch (in radians around the gear)
                            tooth_thickness_rad = (half_root + half_tip) / pitch_radius

                            # Minimum half width to prevent degenerate geometry
                            min_half_width = 0.02 * m  # 2% of module

                            # Track if involute is valid (no self-intersection)
                            involute_valid = True

                            for j in range(num_points):
                                t = j / (num_points - 1)
                                r_pos = actual_inner + t * (outer - actual_inner)

                                # Actual radius from gear center
                                r_actual = pitch_radius + r_pos

                                # Straight flank width (fallback)
                                half_width_straight = half_root + t * (half_tip - half_root)

                                # Check if we're above base circle
                                if r_actual > base_radius and involute_valid:
                                    # Pressure angle at this radius
                                    cos_alpha_r = base_radius / r_actual
                                    # Clamp to valid range for acos
                                    cos_alpha_r = max(-1.0, min(1.0, cos_alpha_r))
                                    alpha_r = math.acos(cos_alpha_r)

                                    # Involute deviation from radial line
                                    inv_r = involute(alpha_r)

                                    # Angular position of involute at this radius relative to pitch
                                    # The involute curves away from the tooth centerline
                                    delta_angle = inv_pitch - inv_r

                                    # Convert to linear width at this radius
                                    involute_offset = r_actual * delta_angle

                                    # Apply involute curvature (flanks curve inward toward root)
                                    half_width = half_width_straight - involute_offset

                                    # Check for invalid geometry (negative or too small width)
                                    if half_width < min_half_width:
                                        # Involute causes self-intersection at small modules
                                        # Fall back to straight flanks for remaining points
                                        involute_valid = False
                                        half_width = max(min_half_width, half_width_straight)
                                else:
                                    # Below base circle or invalid involute - use straight line
                                    half_width = max(min_half_width, half_width_straight)

                                left_flank.append((r_pos, -half_width))
                                right_flank.append((r_pos, half_width))

                            # Use Line instead of Spline if profile is nearly straight (small module)
                            profile_height = outer - actual_inner
                            if profile_height < 0.5 or not involute_valid:
                                # Small profile or invalid involute - use lines for robustness
                                Line(left_flank[0], left_flank[-1])
                                Line(left_flank[-1], right_flank[-1])  # Tip
                                Line(right_flank[-1], right_flank[0])
                                Line(right_flank[0], left_flank[0])    # Root (closes)
                            else:
                                # Build profile with involute flanks
                                Spline(left_flank)
                                Line(left_flank[-1], right_flank[-1])  # Tip
                                Spline(list(reversed(right_flank)))
                                Line(right_flank[0], left_flank[0])    # Root (closes)

                        else:
                            raise ValueError(f"Unknown profile type: {self.profile}")
                    make_face()

                sections.append(sk.sketch.faces()[0])

            # Loft the sections to create twisted tooth space
            try:
                space = loft(sections, ruled=True)
                gear = gear - space
            except Exception as e:
                logger.warning(f"Tooth space {i} failed: {e}")

        return gear

    def show(self):
        """Display the wheel in OCP viewer (requires ocp_vscode)."""
        wheel = self.build()
        try:
            from ocp_vscode import show as ocp_show
            ocp_show(wheel)
        except ImportError:
            pass  # No viewer available - silent fallback
        return wheel

    def export_step(self, filepath: str):
        """Export wheel to STEP file (builds if not already built)."""
        if self._part is None:
            self.build()

        if hasattr(self._part, 'export_step'):
            self._part.export_step(filepath)
        else:
            from build123d import export_step as exp_step
            exp_step(self._part, filepath)

        logger.info(f"Exported wheel to {filepath}")
