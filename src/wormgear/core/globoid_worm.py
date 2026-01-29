"""
Globoid (double-enveloping) worm geometry generation using build123d.

Creates hourglass-shaped worms with helical threads following the curved surface.
This is a simplified prototype implementation.
"""

import logging
import math
from typing import Optional, Literal, Callable
from build123d import (
    Part, Cylinder, Box, Axis, Align, BuildPart, BuildSketch, Plane, Vector,
    BuildLine, Polyline, Line, make_face, revolve, Spline, loft, export_step, Pos,
)
from ..io.loaders import WormParams, AssemblyParams
from ..enums import Hand, WormProfile
from .features import BoreFeature, KeywayFeature, SetScrewFeature, add_bore_and_keyway

# Profile types per DIN 3975
# ZA: Straight flanks in axial section (Archimedean) - best for CNC machining
# ZK: Slightly convex flanks - better for 3D printing (reduces stress concentrations)
ProfileType = Literal["ZA", "ZK", "ZI"]

# Progress callback type for WASM integration
ProgressCallback = Callable[[str, float], None]  # (message, percent_complete)

logger = logging.getLogger(__name__)


class GloboidWormGeometry:
    """
    Generates 3D geometry for a globoid (hourglass) worm.

    Uses simplified geometric model:
    - Hourglass core with throat at center
    - Threads follow curved surface with varying helix radius
    - Thread depth varies along axis
    """

    def __init__(
        self,
        params: WormParams,
        assembly_params: AssemblyParams,
        wheel_pitch_diameter: float,
        length: float = None,
        face_width: float = None,  # Deprecated, use length instead
        sections_per_turn: int = 36,
        bore: Optional[BoreFeature] = None,
        keyway: Optional[KeywayFeature] = None,
        ddcut: Optional['DDCutFeature'] = None,
        set_screw: Optional[SetScrewFeature] = None,
        profile: ProfileType = "ZA",
        progress_callback: Optional[ProgressCallback] = None
    ):
        """
        Initialize globoid worm geometry generator.

        Args:
            params: Worm parameters from calculator
            assembly_params: Assembly parameters (for pressure angle)
            wheel_pitch_diameter: Wheel pitch diameter (needed for throat calculation)
            length: Worm length in mm (auto-calculated if None). This is the total
                   length including thread taper zones at the ends.
            face_width: (Deprecated, use 'length' instead) Worm face width in mm
            sections_per_turn: Number of loft sections per helix turn (default: 36)
            bore: Optional bore feature specification
            keyway: Optional keyway feature specification (requires bore)
            set_screw: Optional set screw feature specification (requires bore)
            profile: Tooth profile type per DIN 3975:
                     "ZA" - Straight flanks (trapezoidal) - best for CNC (default)
                     "ZK" - Slightly convex flanks - better for 3D printing
            progress_callback: Optional callback function(message, percent) for
                              progress reporting in WASM/browser environments.
        """
        self.params = params
        self.assembly_params = assembly_params
        self.wheel_pitch_diameter = wheel_pitch_diameter
        self.sections_per_turn = sections_per_turn
        self.bore = bore
        self.keyway = keyway
        self.ddcut = ddcut
        self.set_screw = set_screw
        self.profile = profile.upper() if isinstance(profile, str) else profile
        self.progress_callback = progress_callback

        # Extract throat reduction from params (calculator-computed value)
        self.throat_reduction_mm = params.throat_reduction_mm or 0.0

        # Store basic parameters
        pitch_radius = params.pitch_diameter_mm / 2.0
        root_radius = params.root_diameter_mm / 2.0
        wheel_pitch_radius = wheel_pitch_diameter / 2.0
        self.wheel_pitch_radius = wheel_pitch_radius
        num_teeth_wheel = int(wheel_pitch_diameter / params.module_mm)

        # Globoid worm throat calculation - GEOMETRY-BASED per DIN 3975
        # The throat pitch radius is derived from center distance and wheel geometry
        # to ensure proper conjugate action where worm surface envelopes wheel pitch cylinder
        #
        # For a true globoid, at the throat (center):
        #   throat_pitch_radius = center_distance - wheel_pitch_radius - throat_reduction
        #
        # The throat_reduction_mm is computed by the calculator and allows the user
        # to control how much the worm "wraps around" the wheel.
        # The nominal pitch radius is used at the ends where the worm transitions
        # back to cylindrical form.
        center_distance = assembly_params.centre_distance_mm
        self.throat_pitch_radius = center_distance - wheel_pitch_radius - self.throat_reduction_mm
        self.nominal_pitch_radius = pitch_radius  # Standard pitch radius at ends

        # Validate throat geometry makes sense
        if self.throat_pitch_radius <= 0:
            raise ValueError(
                f"Invalid globoid geometry: throat_pitch_radius={self.throat_pitch_radius:.2f}mm "
                f"(center_distance={center_distance:.2f}mm - wheel_pitch_radius={wheel_pitch_radius:.2f}mm). "
                f"Center distance must be greater than wheel pitch radius."
            )

        # Warn if throat is too aggressive (more than 20% reduction from nominal)
        throat_reduction = (self.nominal_pitch_radius - self.throat_pitch_radius) / self.nominal_pitch_radius
        if throat_reduction > 0.20:
            logger.info(f"Note: Aggressive throat reduction ({throat_reduction*100:.1f}%). "
                  f"Throat radius={self.throat_pitch_radius:.2f}mm vs nominal={self.nominal_pitch_radius:.2f}mm")

        # The curvature radius (how much the hourglass curves) matches wheel pitch
        self.throat_curvature_radius = wheel_pitch_radius

        # Determine worm length (support both length and face_width for backwards compatibility)
        if length is not None:
            self.length = length
        elif face_width is not None:
            self.length = face_width
        else:
            # Auto-calculate length if not provided
            # Rule from literature: face width ≈ worm diameter at thread root
            # Use 1.3× pitch diameter as a good starting point
            # This gives 2.5-3 thread turns for reasonable engagement
            self.length = params.pitch_diameter_mm * 1.3

        # face_width is now an alias for length (for backwards compatibility)
        self.face_width = self.length

        # Extended length for extend-and-trim strategy
        # Extend by 1 lead on each end to create tapered sections that will be trimmed off
        lead = params.lead_mm
        self.extended_length = self.length + 2 * lead

        self._part = None

    def _report_progress(self, message: str, percent: float, verbose: bool = True):
        """Report progress via callback if available.

        Args:
            message: Progress message
            percent: Completion percentage (0-100)
            verbose: If True, also print to console. If False, only call callback.
        """
        if verbose:
            logger.info(message)
        if self.progress_callback:
            try:
                self.progress_callback(message, percent)
            except Exception:
                pass  # Don't let callback errors break generation

    def build(self) -> Part:
        """
        Build the globoid worm geometry.

        Returns:
            build123d Part object representing the worm
        """
        self._report_progress(
            f"Building globoid worm (throat_pitch_radius={self.throat_pitch_radius:.2f}mm, "
            f"length={self.length:.2f}mm)...",
            0.0
        )

        # Create hourglass core
        self._report_progress("  Creating hourglass core...", 5.0)
        core = self._create_hourglass_core()
        self._report_progress("  ✓ Core complete", 20.0)

        # Create threads for each start
        threads = []
        num_starts = self.params.num_starts
        for start_idx in range(num_starts):
            # Progress: 20-80% is thread creation
            thread_progress = 20 + (start_idx / num_starts) * 60
            # Only print to console for first thread or single-start worms
            self._report_progress(
                f"  Creating thread {start_idx + 1}/{num_starts}...",
                thread_progress,
                verbose=(start_idx == 0 or num_starts == 1)
            )
            thread = self._create_thread(start_idx)
            if thread:
                threads.append(thread)

        self._report_progress("  Combining core and threads...", 80.0)

        # Union core and threads using OCP fuse for reliable result
        from OCP.BRepAlgoAPI import BRepAlgoAPI_Fuse

        if len(threads) == 0:
            result = core
        elif len(threads) == 1:
            try:
                core_shape = core.wrapped if hasattr(core, 'wrapped') else core
                thread_shape = threads[0].wrapped if hasattr(threads[0], 'wrapped') else threads[0]
                fuse_op = BRepAlgoAPI_Fuse(core_shape, thread_shape)
                fuse_op.Build()
                if fuse_op.IsDone():
                    result = Part(fuse_op.Shape())
                else:
                    result = core + threads[0]
            except Exception:
                result = core + threads[0]
        else:
            # Union all threads together first
            thread_union = threads[0]
            for thread in threads[1:]:
                try:
                    t1_shape = thread_union.wrapped if hasattr(thread_union, 'wrapped') else thread_union
                    t2_shape = thread.wrapped if hasattr(thread, 'wrapped') else thread
                    fuse_op = BRepAlgoAPI_Fuse(t1_shape, t2_shape)
                    fuse_op.Build()
                    if fuse_op.IsDone():
                        thread_union = Part(fuse_op.Shape())
                    else:
                        thread_union = thread_union + thread
                except Exception:
                    thread_union = thread_union + thread
            # Union threads with core
            try:
                core_shape = core.wrapped if hasattr(core, 'wrapped') else core
                threads_shape = thread_union.wrapped if hasattr(thread_union, 'wrapped') else thread_union
                fuse_op = BRepAlgoAPI_Fuse(core_shape, threads_shape)
                fuse_op.Build()
                if fuse_op.IsDone():
                    result = Part(fuse_op.Shape())
                else:
                    result = core + thread_union
            except Exception:
                result = core + thread_union

        self._report_progress("  ✓ Geometry combined", 85.0)

        # Trim to exact length - removes fragile tapered thread ends
        self._report_progress(f"  Trimming to final length ({self.length:.2f}mm)...", 87.0)
        result = self._trim_to_length(result)
        self._report_progress("  ✓ Trimmed to length", 90.0)

        # Add features (bore, keyway/ddcut, set screw)
        if self.bore or self.keyway or self.ddcut or self.set_screw:
            self._report_progress("  Adding bore/keyway/DD-cut features...", 92.0)
            result = add_bore_and_keyway(
                part=result,
                part_length=self.length,
                bore=self.bore,
                keyway=self.keyway,
                ddcut=self.ddcut,
                set_screw=self.set_screw,
                axis=Axis.Z
            )

        self._part = result
        self._report_progress("Globoid worm geometry complete.", 100.0)
        return self._part

    def _trim_to_length(self, worm: Part) -> Part:
        """
        Trim extended worm to exact target length using two OCP cut operations.

        The worm was created with extended_length (self.length + 2*lead) to allow
        for tapered thread ends. This method cuts away the extended portions,
        leaving clean ends with full-depth threads.

        Args:
            worm: Extended worm Part to trim

        Returns:
            Trimmed Part with exact self.length dimension
        """
        from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut

        # Calculate cutting positions
        half_length = self.length / 2
        tip_radius = self.params.tip_diameter_mm / 2
        trim_diameter = tip_radius * 4  # Large enough for cutting boxes

        try:
            worm_shape = worm.wrapped if hasattr(worm, 'wrapped') else worm

            # Create top cutting box (remove everything above +half_length)
            top_cut_box = Box(
                length=trim_diameter,
                width=trim_diameter,
                height=self.extended_length,
                align=(Align.CENTER, Align.CENTER, Align.MIN)
            )
            # Move box to start at Z = +half_length
            top_cut_box = Pos(0, 0, half_length) * top_cut_box

            # Cut away top part
            cut_top = BRepAlgoAPI_Cut(worm_shape, top_cut_box.wrapped)
            cut_top.Build()

            if cut_top.IsDone():
                worm_shape = cut_top.Shape()
            else:
                logger.warning(f"Top cut failed, keeping extended geometry")

            # Create bottom cutting box (remove everything below -half_length)
            bottom_cut_box = Box(
                length=trim_diameter,
                width=trim_diameter,
                height=self.extended_length,
                align=(Align.CENTER, Align.CENTER, Align.MAX)
            )
            # Move box to end at Z = -half_length
            bottom_cut_box = Pos(0, 0, -half_length) * bottom_cut_box

            # Cut away bottom part
            cut_bottom = BRepAlgoAPI_Cut(worm_shape, bottom_cut_box.wrapped)
            cut_bottom.Build()

            if cut_bottom.IsDone():
                worm = Part(cut_bottom.Shape())
            else:
                logger.warning(f"Bottom cut failed, using partial trim")
                worm = Part(worm_shape)

        except Exception as e:
            logger.error(f"during cutting: {e}")
            logger.info(f"Keeping extended worm (no trim)")

        return worm

    def _create_hourglass_core(self) -> Part:
        """
        Create the hourglass-shaped core.

        The core must be SMALLER than the thread root radius everywhere,
        so threads sit ON TOP of the core, not inside it.

        The core extends to extended_length to match the extended threads,
        and will be trimmed to exact length after union.

        Returns:
            build123d Part representing the hourglass core
        """
        # Core extends to extended length (will be trimmed after union)
        half_width = self.extended_length / 2.0

        # Core should match the thread root radius (where threads meet the core)
        # Calculate using same circular arc formula as helix path for perfect alignment
        # Use tiny clearance (0.05mm) for numerical safety in boolean union

        dedendum = self.params.dedendum_mm
        lead = self.params.lead_mm

        # Create profile points for hourglass core
        # Use same circular arc formula as the helix path for consistency
        num_profile_points = 20
        profile_points = []
        R_c = self.throat_curvature_radius

        # Core length matches extended worm length
        core_length = self.extended_length

        # Taper zone length (same as threads)
        taper_length = lead

        for i in range(num_profile_points + 1):
            t = i / num_profile_points  # 0 to 1
            z = -half_width + t * core_length

            # Calculate taper factor (same logic as threads)
            dist_from_start = z + half_width
            dist_from_end = half_width - z

            if dist_from_start < taper_length:
                taper_factor = dist_from_start / taper_length
            elif dist_from_end < taper_length:
                taper_factor = dist_from_end / taper_length
            else:
                taper_factor = 1.0

            # Smooth with cosine
            taper_factor = (1 - math.cos(taper_factor * math.pi)) / 2
            taper_factor = max(0.05, taper_factor)

            # Calculate local pitch radius using circular arc formula (same as helix)
            z_for_radius = z

            if abs(z_for_radius) < R_c:
                under_sqrt = R_c**2 - z_for_radius**2
                if under_sqrt >= 0:
                    local_pitch_radius = self.throat_pitch_radius + R_c - math.sqrt(under_sqrt)
                else:
                    local_pitch_radius = self.nominal_pitch_radius
            else:
                local_pitch_radius = self.nominal_pitch_radius

            # Clamp to reasonable range
            local_pitch_radius = max(self.throat_pitch_radius,
                                    min(self.nominal_pitch_radius * 1.05, local_pitch_radius))

            # Core radius is local pitch radius minus tapered dedendum minus tiny clearance
            local_dedendum = dedendum * taper_factor
            r = local_pitch_radius - local_dedendum - 0.05

            profile_points.append((r, z))

        # Create the profile curve
        with BuildPart() as core_builder:
            with BuildSketch(Plane.XZ) as profile_sketch:
                # Create polyline for the profile
                points = [Vector(r, 0, z) for r, z in profile_points]
                with BuildLine():
                    Polyline(*points)
                    # Close the profile by connecting to axis
                    Line(points[-1], Vector(0, 0, half_width))
                    Line(Vector(0, 0, half_width), Vector(0, 0, -half_width))
                    Line(Vector(0, 0, -half_width), points[0])
                make_face()

            # Revolve around Z axis to create hourglass
            revolve(axis=Axis.Z)

        return core_builder.part

    def _generate_globoid_helix_points(self, start_angle: float = 0):
        """
        Generate points for a helix following the hourglass surface.

        The helix has varying radius calculated from the hourglass formula:
        r(z) = throat_pitch_radius + R_c - sqrt(R_c² - z²)

        Uses extended_length to create helix with tapering at ends that will be trimmed.

        Args:
            start_angle: Angular offset for multi-start worms (degrees)

        Returns:
            List of Vector points that form the helix path
        """
        lead = self.params.lead_mm
        half_width = self.extended_length / 2.0
        num_turns = self.extended_length / lead
        is_right_hand = self.assembly_params.hand == Hand.RIGHT

        # Match cylindrical worm's section density
        points_per_turn = self.sections_per_turn
        num_points = int(num_turns * points_per_turn) + 1

        points = []
        R_c = self.throat_curvature_radius

        for i in range(num_points):
            t = i / (num_points - 1)
            z = -half_width + t * self.extended_length

            # Calculate local pitch radius using circular arc hourglass formula
            if abs(z) < R_c:
                under_sqrt = R_c**2 - z**2
                if under_sqrt >= 0:
                    r = self.throat_pitch_radius + R_c - math.sqrt(under_sqrt)
                else:
                    r = self.nominal_pitch_radius
            else:
                r = self.nominal_pitch_radius

            # Clamp to reasonable range (90-105% of nominal)
            r = max(self.throat_pitch_radius,
                    min(self.nominal_pitch_radius * 1.05, r))

            # Calculate rotation angle (cumulative along axis)
            theta = start_angle + (z + half_width) / lead * 360.0
            if not is_right_hand:
                theta = -theta

            theta_rad = math.radians(theta)
            x = r * math.cos(theta_rad)
            y = r * math.sin(theta_rad)

            points.append(Vector(x, y, z))

        return points

    def _create_thread(self, start_index: int) -> Optional[Part]:
        """
        Create a single helical thread following the hourglass surface.

        Adapted from cylindrical worm's _create_single_thread() method,
        using a custom varying-radius Spline path instead of constant Helix.

        Args:
            start_index: Index of this start (0 to num_starts-1)

        Returns:
            build123d Part representing the thread, or None if creation fails
        """
        # Thread dimensions
        pitch_radius = self.params.pitch_diameter_mm / 2
        tip_radius = self.params.tip_diameter_mm / 2
        root_radius = self.params.root_diameter_mm / 2
        lead = self.params.lead_mm

        logger.debug(f"Thread {start_index}: pitch_r={pitch_radius:.2f}, "
                     f"tip_r={tip_radius:.2f}, root_r={root_radius:.2f}, lead={lead:.2f}mm")

        # Thread profile dimensions (same as cylindrical worm)
        pressure_angle_rad = math.radians(self.assembly_params.pressure_angle_deg)
        thread_half_width_pitch = self.params.thread_thickness_mm / 2

        addendum = self.params.addendum_mm
        dedendum = self.params.dedendum_mm
        thread_half_width_root = thread_half_width_pitch + dedendum * math.tan(pressure_angle_rad)
        thread_half_width_tip = max(0.1, thread_half_width_pitch - addendum * math.tan(pressure_angle_rad))

        # Calculate angular offset for multi-start
        angle_offset = (360.0 / self.params.num_starts) * start_index

        # Generate varying-radius helix points and create Spline path
        helix_points = self._generate_globoid_helix_points(start_angle=angle_offset)
        helix_path = Spline(*helix_points)

        # Create profiles along the helix for lofting
        # Use extended_length for section calculation
        num_turns = self.extended_length / lead
        num_sections = int(num_turns * self.sections_per_turn) + 1
        # Ensure at least 2 sections for loft operations (division by num_sections - 1)
        num_sections = max(2, num_sections)
        sections = []

        # Thread end taper: ramp down thread depth over ~1 lead at each end
        taper_length = lead  # Taper zone length at each end

        logger.info(f"  Creating {num_sections} profile sections with end tapering...")

        for i in range(num_sections):
            t = i / (num_sections - 1)

            # Get point and tangent on helix path
            point = helix_path @ t
            tangent = helix_path % t

            # Calculate taper factor for smooth thread ends
            # Ramps from 0 to 1 over taper_length at each end
            # Use extended_length for taper calculation
            half_width = self.extended_length / 2.0
            z_position = point.Z
            dist_from_start = z_position + half_width
            dist_from_end = half_width - z_position

            if dist_from_start < taper_length:
                # Taper at start end
                taper_factor = dist_from_start / taper_length
            elif dist_from_end < taper_length:
                # Taper at end
                taper_factor = dist_from_end / taper_length
            else:
                # Full depth in middle
                taper_factor = 1.0

            # Smooth the taper with a cosine curve for better appearance
            taper_factor = (1 - math.cos(taper_factor * math.pi)) / 2

            # Ensure minimum taper factor to avoid degenerate profiles
            taper_factor = max(0.05, taper_factor)

            # Calculate radial direction at this point
            angle = math.atan2(point.Y, point.X)
            radial_dir = Vector(math.cos(angle), math.sin(angle), 0)

            # CRITICAL: Profile plane perpendicular to helix tangent
            profile_plane = Plane(origin=point, x_dir=radial_dir, z_dir=tangent)

            # Calculate local pitch radius from point position
            local_pitch_radius = math.sqrt(point.X**2 + point.Y**2)

            # Local tip and root radii with taper factor applied
            local_addendum = addendum * taper_factor
            local_dedendum = dedendum * taper_factor
            local_tip_radius = local_pitch_radius + local_addendum
            local_root_radius = local_pitch_radius - local_dedendum

            # Validate profile is meaningful (avoid degenerate profiles)
            profile_height = local_addendum + local_dedendum
            if profile_height < 0.1:  # Less than 0.1mm - skip degenerate section
                continue

            # Profile coordinates relative to local pitch radius
            # inner_r is negative (below pitch), outer_r is positive (above pitch)
            inner_r = -local_dedendum
            outer_r = local_addendum

            # Apply taper factor to thread width with minimum to avoid zero-width profiles
            local_thread_half_width_root = max(0.05, thread_half_width_root * taper_factor)
            local_thread_half_width_tip = max(0.05, thread_half_width_tip * taper_factor)

            # Create filled profile based on profile type
            with BuildSketch(profile_plane) as sk:
                with BuildLine():
                    if self.profile == WormProfile.ZA or self.profile == "ZA":
                        # ZA profile: Straight flanks (trapezoidal) per DIN 3975
                        # Best for CNC machining - simple, accurate, standard
                        root_left = (inner_r, -local_thread_half_width_root)
                        root_right = (inner_r, local_thread_half_width_root)
                        tip_left = (outer_r, -local_thread_half_width_tip)
                        tip_right = (outer_r, local_thread_half_width_tip)

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
                        flank_height = outer_r - inner_r
                        flank_width_change = local_thread_half_width_root - local_thread_half_width_tip

                        # Angle of straight flank for reference
                        if flank_width_change > 0:
                            flank_angle = math.atan(flank_width_change / flank_height)
                        else:
                            flank_angle = 0

                        # Generate arc points
                        for j in range(num_points):
                            t = j / (num_points - 1)
                            r_pos = inner_r + t * flank_height

                            # Circular arc deviation from straight line
                            linear_width = local_thread_half_width_root + t * (local_thread_half_width_tip - local_thread_half_width_root)

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
                        #
                        # IMPORTANT: For worms, ZI does NOT mean curved flanks in the
                        # axial cross-section! A worm acts like a helical rack, and a
                        # rack's "involute" profile is a STRAIGHT LINE at the pressure angle.
                        #
                        # The difference between ZA and ZI for worms is in the 3D helicoid
                        # surface geometry, not the 2D cross-section shape.
                        #
                        # Therefore, ZI for worms = ZA (straight trapezoidal profile)

                        root_left = (inner_r, -local_thread_half_width_root)
                        root_right = (inner_r, local_thread_half_width_root)
                        tip_left = (outer_r, -local_thread_half_width_tip)
                        tip_right = (outer_r, local_thread_half_width_tip)

                        Line(root_left, tip_left)      # Left flank (straight)
                        Line(tip_left, tip_right)      # Tip
                        Line(tip_right, root_right)    # Right flank (straight)
                        Line(root_right, root_left)    # Root (closes)

                    else:
                        raise ValueError(f"Unknown profile type: {self.profile}")
                make_face()  # CRITICAL: Creates filled face with area

            sections.append(sk.sketch.faces()[0])

        # Loft into solid thread (same as cylindrical worm)
        logger.info(f"  Lofting {len(sections)} sections...")
        try:
            thread = loft(sections, ruled=True)
            logger.debug(f"Thread lofted successfully")
            return thread
        except Exception as e:
            logger.warning(f"Loft failed: {e}")
            return None

    def export_step(self, filename: str):
        """
        Export the worm geometry to a STEP file.

        Args:
            filename: Output filename (e.g., 'globoid_worm.step')
        """
        if self._part is None:
            raise ValueError("Geometry not built yet. Call build() first.")

        logger.info(f"Exporting globoid worm: volume={self._part.volume:.2f} mm³")
        if hasattr(self._part, 'export_step'):
            self._part.export_step(filename)
        else:
            from build123d import export_step as exp_step
            exp_step(self._part, filename)

        logger.info(f"Exported globoid worm to {filename}")
