"""
Worm geometry generation using build123d.

Creates CNC-ready worm geometry with helical threads.
"""

import math
from typing import Optional
from build123d import *
from .io import WormParams, AssemblyParams
from .features import BoreFeature, KeywayFeature, add_bore_and_keyway


class WormGeometry:
    """
    Generates 3D geometry for a worm.

    Creates worm by sweeping thread profile along helical path,
    then unioning with core cylinder. Optionally adds bore and keyway.
    """

    def __init__(
        self,
        params: WormParams,
        assembly_params: AssemblyParams,
        length: float = 40.0,
        sections_per_turn: int = 36,
        bore: Optional[BoreFeature] = None,
        keyway: Optional[KeywayFeature] = None
    ):
        """
        Initialize worm geometry generator.

        Args:
            params: Worm parameters from calculator
            assembly_params: Assembly parameters (for pressure angle)
            length: Total worm length in mm (default: 40)
            sections_per_turn: Number of loft sections per helix turn (default: 36)
            bore: Optional bore feature specification
            keyway: Optional keyway feature specification (requires bore)
        """
        self.params = params
        self.assembly_params = assembly_params
        self.length = length
        self.sections_per_turn = sections_per_turn
        self.bore = bore
        self.keyway = keyway

        # Set keyway as shaft type if specified
        if self.keyway is not None:
            self.keyway.is_shaft = True

    def build(self) -> Part:
        """
        Build the complete worm geometry.

        Returns:
            build123d Part object ready for export
        """
        root_radius = self.params.root_diameter_mm / 2
        tip_radius = self.params.tip_diameter_mm / 2

        # Create thread(s) first to determine helix extent
        threads = self._create_threads()

        # Calculate helix extent from thread parameters
        lead = self.params.lead_mm
        num_turns = math.ceil(self.length / lead) + 1
        helix_height = num_turns * lead

        # Create core cylinder matching helix height for clean boolean operations
        core = Cylinder(
            radius=root_radius,
            height=helix_height,
            align=(Align.CENTER, Align.CENTER, Align.CENTER)
        )

        if threads is not None:
            worm = core + threads
        else:
            worm = core

        # Trim to exact length by intersecting with a box
        trim_box = Box(
            tip_radius * 4, tip_radius * 4, self.length,
            align=(Align.CENTER, Align.CENTER, Align.CENTER)
        )
        worm = worm & trim_box

        # Ensure we have a single Solid for proper display in ocp_vscode
        if hasattr(worm, 'solids'):
            solids = list(worm.solids())
            if len(solids) == 1:
                worm = solids[0]
            elif len(solids) > 1:
                # Return the largest solid (should be the worm)
                worm = max(solids, key=lambda s: s.volume)

        # Add bore and keyway if specified
        if self.bore is not None or self.keyway is not None:
            worm = add_bore_and_keyway(
                worm,
                part_length=self.length,
                bore=self.bore,
                keyway=self.keyway,
                axis=Axis.Z
            )

        return worm

    def _create_threads(self) -> Part:
        """Create helical thread(s) to add to the core."""
        threads = []

        for start_index in range(self.params.num_starts):
            angle_offset = (360 / self.params.num_starts) * start_index
            thread = self._create_single_thread(angle_offset)
            if thread is not None:
                threads.append(thread)

        if len(threads) == 0:
            return None
        elif len(threads) == 1:
            return threads[0]
        else:
            result = threads[0]
            for thread in threads[1:]:
                result = result + thread
            return result

    def _create_single_thread(self, start_angle: float = 0) -> Part:
        """
        Create a single helical thread using sweep with auxiliary spine.

        Uses the worm axis as an auxiliary spine to control profile orientation,
        ensuring the profile stays aligned with the radial direction as it sweeps.
        """
        pitch_radius = self.params.pitch_diameter_mm / 2
        tip_radius = self.params.tip_diameter_mm / 2
        root_radius = self.params.root_diameter_mm / 2
        lead = self.params.lead_mm
        is_right_hand = self.params.hand.upper() == "RIGHT"

        # Thread profile dimensions
        pressure_angle_rad = math.radians(self.assembly_params.pressure_angle_deg)

        # Thread width at pitch circle (axial measurement)
        thread_half_width_pitch = self.params.thread_thickness_mm / 2

        # Thread is WIDER at root, NARROWER at tip due to pressure angle
        addendum = self.params.addendum_mm
        dedendum = self.params.dedendum_mm
        thread_half_width_root = thread_half_width_pitch + dedendum * math.tan(pressure_angle_rad)
        thread_half_width_tip = max(0.1, thread_half_width_pitch - addendum * math.tan(pressure_angle_rad))

        # Number of turns needed - add just 1 extra turn, keep it close to length
        num_turns = math.ceil(self.length / lead) + 1
        helix_height = num_turns * lead

        # Create helix path at pitch radius
        helix = Helix(
            pitch=lead,
            height=helix_height,
            radius=pitch_radius,
            center=(0, 0, -helix_height / 2),
            direction=(0, 0, 1) if is_right_hand else (0, 0, -1)
        )

        if start_angle != 0:
            helix = helix.rotate(Axis.Z, start_angle)

        # Profile coordinates relative to pitch radius
        inner_r = root_radius - pitch_radius
        outer_r = tip_radius - pitch_radius

        # Create profiles along the helix for lofting
        num_sections = int(num_turns * self.sections_per_turn) + 1
        sections = []

        for i in range(num_sections):
            t = i / (num_sections - 1)
            point = helix @ t
            tangent = helix % t

            # Radial direction at this point
            angle = math.atan2(point.Y, point.X)
            radial_dir = Vector(math.cos(angle), math.sin(angle), 0)

            # Profile plane perpendicular to helix tangent
            profile_plane = Plane(origin=point, x_dir=radial_dir, z_dir=tangent)

            with BuildSketch(profile_plane) as sk:
                with BuildLine():
                    # Create involute-like curved flanks for better wear
                    # Use spline through points that approximate involute curve
                    num_flank_points = 5
                    left_flank = []
                    right_flank = []

                    for j in range(num_flank_points):
                        # Parameter along the flank (0 = root, 1 = tip)
                        t_flank = j / (num_flank_points - 1)
                        r_pos = inner_r + t_flank * (outer_r - inner_r)

                        # Interpolate width with slight curve (involute approximation)
                        # True involute has slight bulge in the middle
                        linear_width = thread_half_width_root + t_flank * (thread_half_width_tip - thread_half_width_root)
                        # Add subtle curve - max bulge at middle of flank
                        curve_factor = 4 * t_flank * (1 - t_flank)  # Parabolic, peaks at 0.5
                        bulge = curve_factor * 0.05 * (thread_half_width_root - thread_half_width_tip)
                        width = linear_width + bulge

                        left_flank.append((r_pos, -width))
                        right_flank.append((r_pos, width))

                    # Build profile: left flank up, across tip, right flank down, across root
                    Spline(left_flank)
                    Line(left_flank[-1], right_flank[-1])  # Tip
                    Spline(list(reversed(right_flank)))
                    Line(right_flank[0], left_flank[0])  # Root (closes the profile)
                make_face()

            sections.append(sk.sketch.faces()[0])

        # Loft with ruled=True for consistent geometry
        thread = loft(sections, ruled=True)

        return thread

    def show(self):
        """Display the worm in OCP viewer."""
        worm = self.build()
        try:
            from ocp_vscode import show as ocp_show
            ocp_show(worm)
        except ImportError:
            try:
                show(worm)
            except:
                print("No viewer available.")
        return worm

    def export_step(self, filepath: str):
        """Build and export worm to STEP file."""
        worm = self.build()

        if hasattr(worm, 'export_step'):
            worm.export_step(filepath)
        else:
            from build123d import export_step as exp_step
            exp_step(worm, filepath)

        print(f"Exported worm to {filepath}")
