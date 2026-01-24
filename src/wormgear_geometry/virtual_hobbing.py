"""
Virtual Hobbing Wheel Geometry - Experimental

Generates worm wheel geometry by simulating the hobbing manufacturing process.
This approach creates more accurate conjugate tooth profiles by performing
boolean subtractions at discrete angular positions.

EXPERIMENTAL: This is computationally intensive and may be slow for high
step counts. Use for validation or when accuracy is critical.

Theory:
- Real hobbing uses a hob (essentially a worm-shaped cutter) that meshes
  with the wheel blank as both rotate in sync
- The envelope of all hob positions defines the conjugate tooth surface
- We approximate this by sampling N positions and performing boolean cuts

Trade-offs:
- More steps = more accurate but slower
- Fewer steps = faster but may have faceting artifacts
- Typical: 72-360 steps for a full wheel rotation
"""

import math
from typing import Optional, Literal
from build123d import *
from .io import WheelParams, WormParams, AssemblyParams
from .features import (
    BoreFeature,
    KeywayFeature,
    SetScrewFeature,
    HubFeature,
    add_bore_and_keyway,
    create_hub
)

ProfileType = Literal["ZA", "ZK"]


class VirtualHobbingWheelGeometry:
    """
    Generates wheel geometry by simulating the hobbing (gear cutting) process.

    This experimental approach creates a mathematically accurate conjugate
    tooth profile by simulating how a real hobbing machine would cut the wheel.

    The hob (worm-shaped cutter) and wheel blank rotate in sync according to
    the gear ratio, and we perform boolean subtractions at each step to
    approximate the envelope surface.

    EXPERIMENTAL: Computationally intensive. Use --hobbing-steps to control
    accuracy vs speed trade-off.
    """

    def __init__(
        self,
        params: WheelParams,
        worm_params: WormParams,
        assembly_params: AssemblyParams,
        face_width: float = None,
        hobbing_steps: int = 72,
        bore: Optional[BoreFeature] = None,
        keyway: Optional[KeywayFeature] = None,
        set_screw: Optional[SetScrewFeature] = None,
        hub: Optional[HubFeature] = None,
        profile: ProfileType = "ZA",
        hob_geometry: Optional[Part] = None
    ):
        """
        Initialize virtual hobbing wheel generator.

        Args:
            params: Wheel parameters from calculator
            worm_params: Worm parameters (defines hob geometry)
            assembly_params: Assembly parameters
            face_width: Wheel face width in mm (default: auto-calculated)
            hobbing_steps: Number of boolean operations per full wheel rotation
                          More steps = more accurate but slower
                          Typical values: 72 (fast), 144 (balanced), 360 (high accuracy)
            bore: Optional bore feature specification
            keyway: Optional keyway feature specification (requires bore)
            set_screw: Optional set screw feature specification (requires bore)
            hub: Optional hub feature specification
            profile: Tooth profile type per DIN 3975 ("ZA" or "ZK")
            hob_geometry: Optional pre-built worm geometry to use as hob.
                         If provided, uses this exact shape (e.g., globoid worm).
                         If None, creates a cylindrical hob from worm_params.
        """
        self.params = params
        self.worm_params = worm_params
        self.assembly_params = assembly_params
        self.hobbing_steps = hobbing_steps
        self.bore = bore
        self.keyway = keyway
        self.set_screw = set_screw
        self.hub = hub
        self.profile = profile.upper() if isinstance(profile, str) else profile
        self.hob_geometry = hob_geometry

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

    def build(self) -> Part:
        """
        Build the wheel geometry using virtual hobbing simulation.

        Returns:
            build123d Part object ready for export
        """
        print(f"    Virtual hobbing with {self.hobbing_steps} steps...")

        # Create wheel blank
        wheel = self._create_blank()

        # Use provided hob geometry or create cylindrical hob
        if self.hob_geometry is not None:
            print(f"    Using provided worm geometry as hob (e.g., globoid)")
            hob = self.hob_geometry
        else:
            # Create the hob (cutting tool based on worm geometry)
            hob = self._create_hob()

        # Perform virtual hobbing
        wheel = self._simulate_hobbing(wheel, hob)

        # Add bore, keyway, and set screw if specified
        if self.bore is not None or self.keyway is not None or self.set_screw is not None:
            wheel = add_bore_and_keyway(
                wheel,
                part_length=self.face_width,
                bore=self.bore,
                keyway=self.keyway,
                set_screw=self.set_screw,
                axis=Axis.Z
            )

        # Add hub if specified
        if self.hub is not None:
            bore_diameter = self.bore.diameter if self.bore is not None else None
            wheel = create_hub(
                wheel,
                hub=self.hub,
                wheel_face_width=self.face_width,
                wheel_root_diameter=self.params.root_diameter_mm,
                bore_diameter=bore_diameter,
                axis=Axis.Z
            )

        return wheel

    def _create_blank(self) -> Part:
        """Create the wheel blank cylinder."""
        tip_radius = self.params.tip_diameter_mm / 2

        blank = Cylinder(
            radius=tip_radius,
            height=self.face_width,
            align=(Align.CENTER, Align.CENTER, Align.CENTER)
        )

        print(f"    ✓ Blank: radius={tip_radius:.2f}mm, height={self.face_width:.2f}mm")
        return blank

    def _create_hob(self) -> Part:
        """
        Create the hob (cutting tool) based on worm geometry.

        The hob is essentially a worm with slightly enlarged dimensions
        to create clearance. For this simulation, we use the exact worm
        profile since backlash is handled separately.
        """
        pitch_radius = self.worm_params.pitch_diameter_mm / 2
        tip_radius = self.worm_params.tip_diameter_mm / 2
        root_radius = self.worm_params.root_diameter_mm / 2
        lead = self.worm_params.lead_mm
        is_right_hand = self.worm_params.hand.upper() == "RIGHT"

        # Thread profile dimensions
        pressure_angle_rad = math.radians(self.assembly_params.pressure_angle_deg)
        thread_half_width_pitch = self.worm_params.thread_thickness_mm / 2
        addendum = self.worm_params.addendum_mm
        dedendum = self.worm_params.dedendum_mm

        thread_half_width_root = thread_half_width_pitch + dedendum * math.tan(pressure_angle_rad)
        thread_half_width_tip = max(0.1, thread_half_width_pitch - addendum * math.tan(pressure_angle_rad))

        # Hob length should extend beyond wheel face width
        hob_length = self.face_width + 4 * lead

        # Create helix path at pitch radius
        helix = Helix(
            pitch=lead,
            height=hob_length,
            radius=pitch_radius,
            center=(0, 0, -hob_length / 2),
            direction=(0, 0, 1) if is_right_hand else (0, 0, -1)
        )

        # Profile coordinates relative to pitch radius
        inner_r = root_radius - pitch_radius
        outer_r = tip_radius - pitch_radius

        # Create profiles along the helix for lofting
        sections_per_turn = 24  # Fewer sections for hob (speed)
        num_sections = int((hob_length / lead) * sections_per_turn) + 1
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
                    if self.profile == "ZA":
                        # ZA: Straight flanks
                        root_left = (inner_r, -thread_half_width_root)
                        root_right = (inner_r, thread_half_width_root)
                        tip_left = (outer_r, -thread_half_width_tip)
                        tip_right = (outer_r, thread_half_width_tip)

                        Line(root_left, tip_left)
                        Line(tip_left, tip_right)
                        Line(tip_right, root_right)
                        Line(root_right, root_left)
                    else:
                        # ZK: Slightly convex flanks
                        num_flank_points = 5
                        left_flank = []
                        right_flank = []

                        for j in range(num_flank_points):
                            t_flank = j / (num_flank_points - 1)
                            r_pos = inner_r + t_flank * (outer_r - inner_r)
                            linear_width = thread_half_width_root + t_flank * (thread_half_width_tip - thread_half_width_root)
                            curve_factor = 4 * t_flank * (1 - t_flank)
                            bulge = curve_factor * 0.05 * (thread_half_width_root - thread_half_width_tip)
                            width = linear_width + bulge

                            left_flank.append((r_pos, -width))
                            right_flank.append((r_pos, width))

                        Spline(left_flank)
                        Line(left_flank[-1], right_flank[-1])
                        Spline(list(reversed(right_flank)))
                        Line(right_flank[0], left_flank[0])
                make_face()

            sections.append(sk.sketch.faces()[0])

        # Loft thread
        thread = loft(sections, ruled=True)

        # Create core cylinder and union with thread
        core = Cylinder(
            radius=root_radius,
            height=hob_length,
            align=(Align.CENTER, Align.CENTER, Align.CENTER)
        )

        # Multi-start threads
        all_threads = thread
        for start_idx in range(1, self.worm_params.num_starts):
            angle_offset = (360 / self.worm_params.num_starts) * start_idx
            rotated_thread = thread.rotate(Axis.Z, angle_offset)
            all_threads = all_threads + rotated_thread

        hob = core + all_threads

        print(f"    ✓ Hob created: length={hob_length:.2f}mm, {self.worm_params.num_starts} start(s)")
        return hob

    def _simulate_hobbing(self, blank: Part, hob: Part) -> Part:
        """
        Simulate the hobbing process by rotating hob and wheel in sync.

        The hob and wheel rotate according to the gear ratio:
        - For each increment of wheel rotation, hob rotates by (wheel_teeth / worm_starts) times more
        - We perform a boolean subtraction at each step

        The envelope of all hob positions approximates the true conjugate surface.
        """
        centre_distance = self.assembly_params.centre_distance_mm
        wheel_teeth = self.params.num_teeth
        worm_starts = self.worm_params.num_starts
        ratio = wheel_teeth / worm_starts

        # Position hob at centre distance, rotated so its axis is along Y
        # (perpendicular to wheel axis which is along Z)
        hob_positioned = Pos(centre_distance, 0, 0) * Rot(X=90) * hob

        # Calculate angular increments
        # Full wheel rotation = 360 degrees
        # Divide by hobbing_steps to get increment
        wheel_increment = 360.0 / self.hobbing_steps
        hob_increment = wheel_increment * ratio

        wheel = blank

        print(f"    Hobbing simulation: {self.hobbing_steps} steps, ratio 1:{ratio:.1f}")

        # Track progress
        progress_interval = max(1, self.hobbing_steps // 10)

        for step in range(self.hobbing_steps):
            # Current rotations
            wheel_angle = step * wheel_increment
            hob_angle = step * hob_increment

            # Rotate hob around its own axis (Y after positioning)
            # Then the whole assembly rotates around Z (wheel axis)
            hob_rotated = Rot(Z=wheel_angle) * Pos(centre_distance, 0, 0) * Rot(X=90) * Rot(Z=hob_angle) * hob

            # Subtract hob from wheel
            try:
                wheel = wheel - hob_rotated
            except Exception as e:
                print(f"    WARNING: Step {step} boolean failed: {e}")

            # Progress indicator
            if (step + 1) % progress_interval == 0:
                pct = ((step + 1) / self.hobbing_steps) * 100
                print(f"      {pct:.0f}% complete ({step + 1}/{self.hobbing_steps} steps)")

        print(f"    ✓ Virtual hobbing complete")
        return wheel

    def show(self):
        """Display the wheel in OCP viewer."""
        wheel = self.build()
        try:
            from ocp_vscode import show as ocp_show
            ocp_show(wheel)
        except ImportError:
            try:
                show(wheel)
            except:
                print("No viewer available.")
        return wheel

    def export_step(self, filepath: str):
        """Build and export wheel to STEP file."""
        wheel = self.build()

        if hasattr(wheel, 'export_step'):
            wheel.export_step(filepath)
        else:
            from build123d import export_step as exp_step
            exp_step(wheel, filepath)

        print(f"Exported wheel to {filepath}")
