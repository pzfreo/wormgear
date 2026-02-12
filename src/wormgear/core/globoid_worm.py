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
from .features import BoreFeature, KeywayFeature, SetScrewFeature, ReliefGrooveFeature, add_bore_and_keyway, create_relief_groove

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
        relief_groove: Optional[ReliefGrooveFeature] = None,
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
        self.relief_groove = relief_groove
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
        # The throat pitch radius defines the hourglass shape: smaller at center, larger at ends.
        #
        # We use throat_reduction_mm directly rather than deriving from centre_distance,
        # because the JSON may have inconsistent values (e.g., if throat_reduction was
        # auto-defaulted after centre_distance was already calculated).
        #
        # throat_pitch_radius = nominal_pitch_radius - throat_reduction_mm
        #
        # The nominal pitch radius is used at the ends where the worm transitions
        # back to cylindrical form.
        self.nominal_pitch_radius = pitch_radius  # Standard pitch radius at ends
        self.throat_pitch_radius = self.nominal_pitch_radius - self.throat_reduction_mm

        # Use assembly centre distance directly — the calculator now accounts for
        # throat reduction when computing CD for globoid worms.
        self.effective_centre_distance = assembly_params.centre_distance_mm

        # Validate throat geometry makes sense
        if self.throat_pitch_radius <= 0:
            raise ValueError(
                f"Invalid globoid geometry: throat_pitch_radius={self.throat_pitch_radius:.2f}mm "
                f"(nominal={self.nominal_pitch_radius:.2f}mm - throat_reduction={self.throat_reduction_mm:.2f}mm). "
                f"Throat reduction is too large for this worm diameter."
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
        Build the globoid worm geometry using CORE + THREAD UNION approach.

        Creates hourglass core (revolve) + helical threads (loft), then unions.
        Threads extend past root into core for clean boolean union.

        Returns:
            build123d Part object representing the worm
        """
        self._report_progress(
            f"Building globoid worm (throat_pitch_radius={self.throat_pitch_radius:.2f}mm, "
            f"length={self.length:.2f}mm)...",
            0.0
        )

        self._report_progress("  Creating hourglass core...", 5.0)
        core = self._create_hourglass_core_exact()
        self._report_progress("  ✓ Core complete", 20.0)

        # Create threads
        self._report_progress("  Creating helical threads...", 25.0)
        threads = []
        for start_idx in range(self.params.num_starts):
            self._report_progress(f"    Thread {start_idx + 1}/{self.params.num_starts}...",
                                  25.0 + 40.0 * start_idx / self.params.num_starts, verbose=False)
            thread = self._create_thread_extended(start_idx)
            if thread is not None:
                threads.append(thread)

        if not threads:
            logger.warning("No threads created, using core only")
            result = core
        else:
            # Union all threads together first
            self._report_progress("  Unioning threads...", 70.0)
            from OCP.BRepAlgoAPI import BRepAlgoAPI_Fuse

            combined_threads = threads[0]
            for i, thread in enumerate(threads[1:], 1):
                try:
                    fuse_op = BRepAlgoAPI_Fuse(
                        combined_threads.wrapped if hasattr(combined_threads, 'wrapped') else combined_threads,
                        thread.wrapped if hasattr(thread, 'wrapped') else thread
                    )
                    fuse_op.Build()
                    if fuse_op.IsDone():
                        combined_threads = Part(fuse_op.Shape())
                    else:
                        combined_threads = combined_threads + thread
                except Exception:
                    combined_threads = combined_threads + thread

            # Union core with all threads
            self._report_progress("  Unioning core with threads...", 80.0)
            try:
                fuse_op = BRepAlgoAPI_Fuse(
                    core.wrapped if hasattr(core, 'wrapped') else core,
                    combined_threads.wrapped if hasattr(combined_threads, 'wrapped') else combined_threads
                )
                fuse_op.Build()
                if fuse_op.IsDone():
                    result = Part(fuse_op.Shape())
                else:
                    result = core + combined_threads
            except Exception as e:
                logger.warning(f"Union failed: {e}, using fallback")
                result = core + combined_threads

        self._report_progress("  ✓ Geometry complete", 85.0)

        # Trim to exact length - removes fragile tapered thread ends
        self._report_progress(f"  Trimming to final length ({self.length:.2f}mm)...", 87.0)
        result = self._trim_to_length(result)
        self._report_progress("  ✓ Trimmed to length", 90.0)

        # Cut relief grooves at thread termination points (before bore features)
        if self.relief_groove is not None:
            axial_pitch = self.params.lead_mm / self.params.num_starts
            result = create_relief_groove(
                result,
                root_diameter_mm=self.params.root_diameter_mm,
                tip_diameter_mm=self.params.tip_diameter_mm,
                axial_pitch_mm=axial_pitch,
                part_length=self.length,
                groove=self.relief_groove,
                axis=Axis.Z
            )

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

    def _build_from_horizontal_slices(self) -> Part:
        """
        Build the worm from horizontal (Z-perpendicular) cross-sections.

        Each slice is a 2D shape: circle (core) + tooth bumps at thread positions.
        Lofting these creates a unified solid with no surface-type mismatches.
        """
        lead = self.params.lead_mm
        half_width = self.extended_length / 2.0
        num_starts = self.params.num_starts
        is_right_hand = self.assembly_params.hand == Hand.RIGHT

        pressure_angle_rad = math.radians(self.assembly_params.pressure_angle_deg)
        addendum = self.params.addendum_mm
        dedendum = self.params.dedendum_mm
        thread_half_width_pitch = self.params.thread_thickness_mm / 2

        R_c = self.throat_curvature_radius
        taper_length = lead

        # Number of Z slices - more slices = smoother result
        num_slices = int((self.extended_length / lead) * self.sections_per_turn) + 1
        num_slices = max(10, num_slices)

        sections = []
        logger.info(f"  Creating {num_slices} horizontal slices...")

        for i in range(num_slices):
            t = i / (num_slices - 1)
            z = -half_width + t * self.extended_length

            # Taper factor
            dist_from_start = z + half_width
            dist_from_end = half_width - z

            if dist_from_start < taper_length:
                taper_factor = dist_from_start / taper_length
            elif dist_from_end < taper_length:
                taper_factor = dist_from_end / taper_length
            else:
                taper_factor = 1.0

            taper_factor = (1 - math.cos(taper_factor * math.pi)) / 2
            taper_factor = max(0.05, taper_factor)

            # Calculate local pitch radius using hourglass formula
            if abs(z) < R_c:
                under_sqrt = R_c**2 - z**2
                if under_sqrt >= 0:
                    local_pitch_radius = self.throat_pitch_radius + R_c - math.sqrt(under_sqrt)
                else:
                    local_pitch_radius = self.nominal_pitch_radius
            else:
                local_pitch_radius = self.nominal_pitch_radius

            local_pitch_radius = max(self.throat_pitch_radius,
                                    min(self.nominal_pitch_radius, local_pitch_radius))

            # Local dimensions with taper
            local_addendum = addendum * taper_factor
            local_dedendum = dedendum * taper_factor
            local_root_radius = local_pitch_radius - local_dedendum
            local_tip_radius = local_pitch_radius + local_addendum

            # Thread angular position at this Z (from helix equation)
            thread_base_angle = (z + half_width) / lead * 360.0
            if not is_right_hand:
                thread_base_angle = -thread_base_angle

            # Thread angular half-width at tip level (smallest)
            local_thread_half_pitch = thread_half_width_pitch * taper_factor
            thread_half_width_tip = max(0.05, local_thread_half_pitch - local_addendum * math.tan(pressure_angle_rad))
            thread_angular_half_tip = math.degrees(thread_half_width_tip / local_tip_radius) if local_tip_radius > 0 else 5

            # Thread angular half-width at root level (largest)
            thread_half_width_root = local_thread_half_pitch + local_dedendum * math.tan(pressure_angle_rad)
            thread_angular_half_root = math.degrees(thread_half_width_root / local_root_radius) if local_root_radius > 0 else 10

            # Build the cross-section profile as points
            # Go around 360 degrees, creating core circle with tooth bumps
            # CRITICAL: Rotate sampling points WITH the helix so corresponding
            # points across slices are at the same position relative to teeth.
            # This prevents the loft from connecting misaligned points.
            num_points_per_rev = 120  # Points for smooth circle
            profile_points = []

            for j in range(num_points_per_rev):
                # Rotate sampling points with helix - this is the key fix!
                # Sample point j is always at the same position relative to tooth
                base_angle = j * 360.0 / num_points_per_rev
                angle_deg = base_angle + thread_base_angle  # ROTATE with helix
                angle_rad = math.radians(angle_deg)

                # Check if this angle is within any thread tooth
                r = local_root_radius  # Default to root (core)

                for start_idx in range(num_starts):
                    # Tooth center in helix-rotated coordinates
                    # (no thread_base_angle - it's already in angle_deg)
                    tooth_center = (360.0 / num_starts) * start_idx

                    # Angular distance from tooth center (in rotated coords)
                    angle_diff = (base_angle - tooth_center + 180) % 360 - 180

                    # Check if within tooth
                    if abs(angle_diff) < thread_angular_half_root:
                        # Inside the tooth region - interpolate radius
                        # At center (angle_diff=0): r = tip
                        # At edge (angle_diff=half_root): r = root
                        relative_pos = abs(angle_diff) / thread_angular_half_root

                        # Use trapezoidal profile: flat tip, angled flanks
                        if abs(angle_diff) < thread_angular_half_tip:
                            # In the flat tip region
                            r = local_tip_radius
                        else:
                            # On the flank - linear interpolation from tip to root
                            flank_pos = (abs(angle_diff) - thread_angular_half_tip) / (thread_angular_half_root - thread_angular_half_tip)
                            flank_pos = min(1.0, max(0.0, flank_pos))
                            r = local_tip_radius - (local_tip_radius - local_root_radius) * flank_pos
                        break

                x = r * math.cos(angle_rad)
                y = r * math.sin(angle_rad)
                profile_points.append(Vector(x, y, 0))

            # Create the face from these points
            section_plane = Plane(origin=Vector(0, 0, z), z_dir=Vector(0, 0, 1))

            try:
                with BuildSketch(section_plane) as sk:
                    with BuildLine():
                        # periodic=True automatically closes the loop - don't add duplicate point
                        Spline(profile_points, periodic=True)
                    make_face()

                if sk.sketch.faces():
                    sections.append(sk.sketch.faces()[0])
            except Exception as e:
                logger.warning(f"Slice {i} at z={z:.2f} failed: {e}")
                continue

        if len(sections) < 2:
            raise ValueError(f"Not enough sections for loft: {len(sections)}")

        logger.info(f"  Lofting {len(sections)} sections...")
        try:
            # Use smooth loft (ruled=False) for continuous surfaces without seams
            result = loft(sections, ruled=False)
            return result
        except Exception as e:
            logger.error(f"Loft failed: {e}")
            raise

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

            # Clamp to valid range: throat to nominal (never exceed cylindrical)
            local_pitch_radius = max(self.throat_pitch_radius,
                                    min(self.nominal_pitch_radius, local_pitch_radius))

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

    def _create_hourglass_core_exact(self) -> Part:
        """
        Create hourglass core at EXACT thread root radius - no gap.

        The core outer surface is at (local_pitch_radius - local_dedendum)
        which is exactly where the thread inner surface will be.
        """
        half_width = self.extended_length / 2.0
        dedendum = self.params.dedendum_mm
        lead = self.params.lead_mm
        R_c = self.throat_curvature_radius

        num_profile_points = 40  # More points for smooth profile
        profile_points = []
        taper_length = lead

        for i in range(num_profile_points + 1):
            t = i / num_profile_points
            z = -half_width + t * self.extended_length

            # Taper factor
            dist_from_start = z + half_width
            dist_from_end = half_width - z

            if dist_from_start < taper_length:
                taper_factor = dist_from_start / taper_length
            elif dist_from_end < taper_length:
                taper_factor = dist_from_end / taper_length
            else:
                taper_factor = 1.0

            taper_factor = (1 - math.cos(taper_factor * math.pi)) / 2
            taper_factor = max(0.05, taper_factor)

            # Calculate local pitch radius using hourglass formula
            if abs(z) < R_c:
                under_sqrt = R_c**2 - z**2
                if under_sqrt >= 0:
                    local_pitch_radius = self.throat_pitch_radius + R_c - math.sqrt(under_sqrt)
                else:
                    local_pitch_radius = self.nominal_pitch_radius
            else:
                local_pitch_radius = self.nominal_pitch_radius

            local_pitch_radius = max(self.throat_pitch_radius,
                                    min(self.nominal_pitch_radius, local_pitch_radius))

            # Core radius is EXACTLY at thread root - NO GAP
            local_dedendum = dedendum * taper_factor
            r = local_pitch_radius - local_dedendum

            profile_points.append((r, z))

        # Create and revolve
        with BuildPart() as core_builder:
            with BuildSketch(Plane.XZ) as profile_sketch:
                points = [Vector(r, 0, z) for r, z in profile_points]
                with BuildLine():
                    Polyline(*points)
                    Line(points[-1], Vector(0, 0, half_width))
                    Line(Vector(0, 0, half_width), Vector(0, 0, -half_width))
                    Line(Vector(0, 0, -half_width), points[0])
                make_face()
            revolve(axis=Axis.Z)

        return core_builder.part

    def _create_pie_slice_thread(self, start_index: int) -> Optional[Part]:
        """
        Create a thread as a pie-slice shape extending from axis to tip.

        Each profile is a radial wedge from center to tip, ensuring
        no gaps since there's no separate core to union with.

        Args:
            start_index: Index of this start (0 to num_starts-1)

        Returns:
            build123d Part representing the thread
        """
        lead = self.params.lead_mm
        half_width = self.extended_length / 2.0
        num_turns = self.extended_length / lead
        is_right_hand = self.assembly_params.hand == Hand.RIGHT

        pressure_angle_rad = math.radians(self.assembly_params.pressure_angle_deg)
        addendum = self.params.addendum_mm
        dedendum = self.params.dedendum_mm
        thread_half_width_pitch = self.params.thread_thickness_mm / 2

        R_c = self.throat_curvature_radius
        taper_length = lead

        # Angular offset for this start
        angle_offset = (360.0 / self.params.num_starts) * start_index

        # Generate helix points
        helix_points = self._generate_globoid_helix_points(start_angle=angle_offset)
        helix_path = Spline(*helix_points)

        # Create profiles along helix
        num_sections = int(num_turns * self.sections_per_turn) + 1
        num_sections = max(2, num_sections)
        sections = []

        for i in range(num_sections):
            t = i / (num_sections - 1)
            point = helix_path @ t
            tangent = helix_path % t

            z_position = point.Z
            dist_from_start = z_position + half_width
            dist_from_end = half_width - z_position

            if dist_from_start < taper_length:
                taper_factor = dist_from_start / taper_length
            elif dist_from_end < taper_length:
                taper_factor = dist_from_end / taper_length
            else:
                taper_factor = 1.0

            taper_factor = (1 - math.cos(taper_factor * math.pi)) / 2
            taper_factor = max(0.05, taper_factor)

            # Local dimensions
            local_pitch_radius = math.sqrt(point.X**2 + point.Y**2)
            local_addendum = addendum * taper_factor
            local_dedendum = dedendum * taper_factor

            # PIE SLICE: extends from axis (r=0) to tip
            inner_r = 0  # Start at axis!
            outer_r = local_addendum  # Relative to pitch

            # Thread widths
            local_half_pitch = thread_half_width_pitch * taper_factor
            half_width_at_axis = local_half_pitch + local_pitch_radius * math.tan(pressure_angle_rad)
            half_width_at_tip = max(0.05, local_half_pitch - local_addendum * math.tan(pressure_angle_rad))
            half_width_at_root = local_half_pitch + local_dedendum * math.tan(pressure_angle_rad)

            # Profile plane perpendicular to helix
            angle = math.atan2(point.Y, point.X)
            radial_dir = Vector(math.cos(angle), math.sin(angle), 0)
            profile_plane = Plane(origin=point, x_dir=radial_dir, z_dir=tangent)

            # Create pie-slice profile from axis to tip
            # The profile is in local coordinates where:
            #   x = 0 is at pitch radius
            #   positive x is outward (toward tip)
            #   negative x is inward (toward axis, which is at -local_pitch_radius)

            axis_r = -local_pitch_radius  # Where the axis is in local coords

            try:
                with BuildSketch(profile_plane) as sk:
                    with BuildLine():
                        # Pie slice shape: axis -> root edge -> tip edge -> axis
                        # Left side: axis to root_left to tip_left
                        # Right side: tip_right to root_right to axis

                        root_r = -local_dedendum  # Root in local coords

                        # Points defining the pie slice
                        axis_pt = (axis_r, 0)  # Center axis point
                        root_left = (root_r, -half_width_at_root)
                        root_right = (root_r, half_width_at_root)
                        tip_left = (outer_r, -half_width_at_tip)
                        tip_right = (outer_r, half_width_at_tip)

                        # Draw the outline
                        Line(axis_pt, root_left)
                        Line(root_left, tip_left)
                        Line(tip_left, tip_right)
                        Line(tip_right, root_right)
                        Line(root_right, axis_pt)

                    make_face()

                if sk.sketch.faces():
                    sections.append(sk.sketch.faces()[0])

            except Exception as e:
                logger.warning(f"Section {i} failed: {e}")
                continue

        if len(sections) < 2:
            return None

        try:
            thread = loft(sections, ruled=True)
            return thread
        except Exception as e:
            logger.warning(f"Pie-slice loft failed: {e}")
            return None

    def _create_unified_worm(self) -> Part:
        """
        Create the worm as a single unified solid by lofting cross-sections
        that include both core and thread in each section.

        Each cross-section is a circle (core) with thread teeth added at the
        appropriate angular positions. This eliminates any gaps between
        core and thread since they're part of the same geometry.

        Returns:
            build123d Part representing the complete worm
        """
        lead = self.params.lead_mm
        half_width = self.extended_length / 2.0
        num_turns = self.extended_length / lead
        num_starts = self.params.num_starts
        is_right_hand = self.assembly_params.hand == Hand.RIGHT

        # Thread dimensions
        pressure_angle_rad = math.radians(self.assembly_params.pressure_angle_deg)
        addendum = self.params.addendum_mm
        dedendum = self.params.dedendum_mm
        thread_half_width_pitch = self.params.thread_thickness_mm / 2

        R_c = self.throat_curvature_radius
        taper_length = lead

        # Create cross-sections along the worm
        num_sections = int(num_turns * self.sections_per_turn) + 1
        num_sections = max(2, num_sections)
        sections = []

        logger.info(f"  Creating {num_sections} unified cross-sections...")

        for i in range(num_sections):
            t = i / (num_sections - 1)
            z = -half_width + t * self.extended_length

            # Calculate taper factor
            dist_from_start = z + half_width
            dist_from_end = half_width - z

            if dist_from_start < taper_length:
                taper_factor = dist_from_start / taper_length
            elif dist_from_end < taper_length:
                taper_factor = dist_from_end / taper_length
            else:
                taper_factor = 1.0

            taper_factor = (1 - math.cos(taper_factor * math.pi)) / 2
            taper_factor = max(0.05, taper_factor)

            # Calculate local pitch radius using hourglass formula
            if abs(z) < R_c:
                under_sqrt = R_c**2 - z**2
                if under_sqrt >= 0:
                    local_pitch_radius = self.throat_pitch_radius + R_c - math.sqrt(under_sqrt)
                else:
                    local_pitch_radius = self.nominal_pitch_radius
            else:
                local_pitch_radius = self.nominal_pitch_radius

            local_pitch_radius = max(self.throat_pitch_radius,
                                    min(self.nominal_pitch_radius, local_pitch_radius))

            # Local thread dimensions with taper
            local_addendum = addendum * taper_factor
            local_dedendum = dedendum * taper_factor
            local_tip_radius = local_pitch_radius + local_addendum
            local_root_radius = local_pitch_radius - local_dedendum

            # Thread width at different heights
            local_thread_half_pitch = thread_half_width_pitch * taper_factor
            thread_half_width_root = local_thread_half_pitch + local_dedendum * math.tan(pressure_angle_rad)
            thread_half_width_tip = max(0.05, local_thread_half_pitch - local_addendum * math.tan(pressure_angle_rad))

            # Skip degenerate sections
            if local_tip_radius - local_root_radius < 0.1:
                continue

            # Calculate thread angular position at this Z
            # Each start is offset by 360/num_starts degrees
            base_angle = (z + half_width) / lead * 360.0
            if not is_right_hand:
                base_angle = -base_angle

            # Create cross-section on XY plane at this Z
            section_plane = Plane(origin=Vector(0, 0, z), z_dir=Vector(0, 0, 1))

            try:
                with BuildSketch(section_plane) as sk:
                    # For each thread start, add a tooth to the core circle
                    # We'll build the shape by creating the outline

                    with BuildLine():
                        # Build the complete outline: core circle with tooth bumps
                        # We go around 360° and insert tooth shapes at thread positions

                        num_arc_points = 72  # Points for smooth circle
                        points = []

                        for j in range(num_arc_points):
                            angle_deg = j * 360.0 / num_arc_points

                            # Check if this angle is within a thread tooth
                            in_tooth = False
                            for start_idx in range(num_starts):
                                tooth_center = base_angle + (360.0 / num_starts) * start_idx
                                tooth_center = tooth_center % 360.0

                                # Angular width of tooth at root level (approximate)
                                tooth_angular_half = math.degrees(thread_half_width_root / local_root_radius)

                                # Check if angle is within tooth
                                angle_diff = (angle_deg - tooth_center + 180) % 360 - 180
                                if abs(angle_diff) < tooth_angular_half:
                                    in_tooth = True
                                    # Calculate radius based on position within tooth
                                    # Interpolate from root to tip based on distance from center
                                    relative_pos = abs(angle_diff) / tooth_angular_half  # 0 at center, 1 at edge
                                    # Simple linear interpolation for trapezoidal profile
                                    r = local_tip_radius - (local_tip_radius - local_root_radius) * relative_pos
                                    break

                            if not in_tooth:
                                r = local_root_radius

                            angle_rad = math.radians(angle_deg)
                            x = r * math.cos(angle_rad)
                            y = r * math.sin(angle_rad)
                            points.append((x, y))

                        # Close the loop
                        points.append(points[0])

                        # Create spline through points
                        Spline([Vector(x, y, 0) for x, y in points], periodic=True)

                    make_face()

                if sk.sketch.faces():
                    sections.append(sk.sketch.faces()[0])

            except Exception as e:
                logger.warning(f"Section {i} failed: {e}")
                continue

        if len(sections) < 2:
            raise ValueError("Not enough sections for loft")

        # Loft the sections together
        logger.info(f"  Lofting {len(sections)} sections...")
        try:
            result = loft(sections, ruled=True)
            return result
        except Exception as e:
            logger.error(f"Loft failed: {e}")
            raise

    def _create_hourglass_blank(self) -> Part:
        """
        Create an hourglass-shaped blank at the TIP diameter.

        This is a solid from axis to tip radius, following the hourglass profile.
        Thread grooves will be cut from this blank.

        Returns:
            build123d Part representing the hourglass blank
        """
        half_width = self.extended_length / 2.0
        addendum = self.params.addendum_mm
        lead = self.params.lead_mm
        R_c = self.throat_curvature_radius

        num_profile_points = 40  # More points for smooth hourglass
        profile_points = []

        taper_length = lead

        for i in range(num_profile_points + 1):
            t = i / num_profile_points
            z = -half_width + t * self.extended_length

            # Calculate taper factor for thread depth at ends
            dist_from_start = z + half_width
            dist_from_end = half_width - z

            if dist_from_start < taper_length:
                taper_factor = dist_from_start / taper_length
            elif dist_from_end < taper_length:
                taper_factor = dist_from_end / taper_length
            else:
                taper_factor = 1.0

            taper_factor = (1 - math.cos(taper_factor * math.pi)) / 2
            taper_factor = max(0.05, taper_factor)

            # Calculate local pitch radius using hourglass formula
            if abs(z) < R_c:
                under_sqrt = R_c**2 - z**2
                if under_sqrt >= 0:
                    local_pitch_radius = self.throat_pitch_radius + R_c - math.sqrt(under_sqrt)
                else:
                    local_pitch_radius = self.nominal_pitch_radius
            else:
                local_pitch_radius = self.nominal_pitch_radius

            local_pitch_radius = max(self.throat_pitch_radius,
                                    min(self.nominal_pitch_radius, local_pitch_radius))

            # Blank radius is at TIP (pitch + addendum), with taper at ends
            local_addendum = addendum * taper_factor
            r = local_pitch_radius + local_addendum

            profile_points.append((r, z))

        # Create the profile and revolve
        with BuildPart() as blank_builder:
            with BuildSketch(Plane.XZ) as profile_sketch:
                points = [Vector(r, 0, z) for r, z in profile_points]
                with BuildLine():
                    Polyline(*points)
                    Line(points[-1], Vector(0, 0, half_width))
                    Line(Vector(0, 0, half_width), Vector(0, 0, -half_width))
                    Line(Vector(0, 0, -half_width), points[0])
                make_face()
            revolve(axis=Axis.Z)

        return blank_builder.part

    def _create_thread_groove(self, start_index: int) -> Optional[Part]:
        """
        Create the groove (space between threads) as a helical solid.

        This is the INVERSE of the thread - the space that needs to be
        cut away from the blank to leave the thread standing.

        Args:
            start_index: Index of this start (0 to num_starts-1)

        Returns:
            build123d Part representing the groove, or None if creation fails
        """
        lead = self.params.lead_mm
        pressure_angle_rad = math.radians(self.assembly_params.pressure_angle_deg)
        addendum = self.params.addendum_mm
        dedendum = self.params.dedendum_mm

        # Groove dimensions - the space between threads
        # Groove width at pitch = lead/num_starts - thread_thickness
        axial_pitch = lead / self.params.num_starts
        groove_width_pitch = axial_pitch - self.params.thread_thickness_mm

        # Groove flanks follow pressure angle
        groove_half_width_pitch = groove_width_pitch / 2
        groove_half_width_tip = groove_half_width_pitch + addendum * math.tan(pressure_angle_rad)
        groove_half_width_root = max(0.1, groove_half_width_pitch - dedendum * math.tan(pressure_angle_rad))

        # Angular offset for multi-start
        angle_offset = (360.0 / self.params.num_starts) * start_index
        # Offset by half a tooth pitch to center groove between threads
        groove_angle_offset = angle_offset + (axial_pitch / lead) * 180.0

        # Generate helix points for the groove center
        helix_points = self._generate_globoid_helix_points(start_angle=groove_angle_offset)
        helix_path = Spline(*helix_points)

        # Create groove profiles along the helix
        num_turns = self.extended_length / lead
        num_sections = int(num_turns * self.sections_per_turn) + 1
        num_sections = max(2, num_sections)
        sections = []

        taper_length = lead
        half_width = self.extended_length / 2.0

        for i in range(num_sections):
            t = i / (num_sections - 1)
            point = helix_path @ t
            tangent = helix_path % t

            # Calculate taper factor
            z_position = point.Z
            dist_from_start = z_position + half_width
            dist_from_end = half_width - z_position

            if dist_from_start < taper_length:
                taper_factor = dist_from_start / taper_length
            elif dist_from_end < taper_length:
                taper_factor = dist_from_end / taper_length
            else:
                taper_factor = 1.0

            taper_factor = (1 - math.cos(taper_factor * math.pi)) / 2
            taper_factor = max(0.05, taper_factor)

            # Local dimensions
            local_addendum = addendum * taper_factor
            local_dedendum = dedendum * taper_factor

            # Groove extends from just above tip to below root
            # (slightly past to ensure clean cut)
            outer_r = local_addendum + 0.5  # Extend past tip
            inner_r = -local_dedendum - 0.5  # Extend past root

            # Skip degenerate sections
            profile_height = outer_r - inner_r
            if profile_height < 0.2:
                continue

            # Apply taper to groove width
            local_groove_half_width_tip = max(0.05, groove_half_width_tip * taper_factor)
            local_groove_half_width_root = max(0.05, groove_half_width_root * taper_factor)

            # APPROACH C: Profile plane oriented RADIALLY (z_dir = Z axis)
            # This makes inner edges lie on horizontal circles that match
            # the hourglass's surface of revolution
            angle = math.atan2(point.Y, point.X)
            radial_dir = Vector(math.cos(angle), math.sin(angle), 0)
            profile_plane = Plane(origin=point, x_dir=radial_dir, z_dir=Vector(0, 0, 1))

            # Create groove profile (trapezoidal, wider at root, narrower at tip)
            with BuildSketch(profile_plane) as sk:
                with BuildLine():
                    # Groove profile: narrow at top (tip), wide at bottom (root)
                    root_left = (inner_r, -local_groove_half_width_root)
                    root_right = (inner_r, local_groove_half_width_root)
                    tip_left = (outer_r, -local_groove_half_width_tip)
                    tip_right = (outer_r, local_groove_half_width_tip)

                    Line(root_left, tip_left)
                    Line(tip_left, tip_right)
                    Line(tip_right, root_right)
                    Line(root_right, root_left)
                make_face()

            sections.append(sk.sketch.faces()[0])

        # Loft into solid groove
        if len(sections) < 2:
            return None

        try:
            groove = loft(sections, ruled=True)
            return groove
        except Exception as e:
            logger.warning(f"Groove loft failed: {e}")
            return None

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

            # Clamp to valid range: throat to nominal (never exceed cylindrical)
            r = max(self.throat_pitch_radius,
                    min(self.nominal_pitch_radius, r))

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

            # APPROACH C: Profile plane oriented RADIALLY (z_dir = Z axis)
            # This makes inner edges lie on horizontal circles that match
            # the hourglass's surface of revolution
            profile_plane = Plane(origin=point, x_dir=radial_dir, z_dir=Vector(0, 0, 1))

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
            # inner_r at EXACT dedendum - matches core outer surface exactly
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

    def _create_thread_extended(self, start_index: int) -> Optional[Part]:
        """
        Create a helical thread that extends PAST the root into the core.

        This ensures clean boolean union with the hourglass core by providing
        substantial overlap. The thread extends to 50% of the local pitch radius
        (well past the root) so the union has plenty of material to work with.

        Args:
            start_index: Index of this start (0 to num_starts-1)

        Returns:
            build123d Part representing the thread, or None if creation fails
        """
        lead = self.params.lead_mm
        pressure_angle_rad = math.radians(self.assembly_params.pressure_angle_deg)
        addendum = self.params.addendum_mm
        dedendum = self.params.dedendum_mm
        thread_half_width_pitch = self.params.thread_thickness_mm / 2
        thread_half_width_root = thread_half_width_pitch + dedendum * math.tan(pressure_angle_rad)
        thread_half_width_tip = max(0.1, thread_half_width_pitch - addendum * math.tan(pressure_angle_rad))

        # Angular offset for multi-start
        angle_offset = (360.0 / self.params.num_starts) * start_index

        # Generate helix points and create path
        helix_points = self._generate_globoid_helix_points(start_angle=angle_offset)
        helix_path = Spline(*helix_points)

        # Create profiles along the helix
        num_turns = self.extended_length / lead
        num_sections = int(num_turns * self.sections_per_turn) + 1
        num_sections = max(2, num_sections)
        sections = []

        taper_length = lead
        half_width = self.extended_length / 2.0

        for i in range(num_sections):
            t = i / (num_sections - 1)
            point = helix_path @ t
            tangent = helix_path % t

            z_position = point.Z
            dist_from_start = z_position + half_width
            dist_from_end = half_width - z_position

            if dist_from_start < taper_length:
                taper_factor = dist_from_start / taper_length
            elif dist_from_end < taper_length:
                taper_factor = dist_from_end / taper_length
            else:
                taper_factor = 1.0

            taper_factor = (1 - math.cos(taper_factor * math.pi)) / 2
            taper_factor = max(0.05, taper_factor)

            # Calculate local pitch radius from point position
            local_pitch_radius = math.sqrt(point.X**2 + point.Y**2)

            # Local dimensions with taper
            local_addendum = addendum * taper_factor
            local_dedendum = dedendum * taper_factor

            # Profile extends from tip down to 50% of pitch radius (well past root)
            # This ensures substantial overlap with the hourglass core
            outer_r = local_addendum  # Above pitch (toward tip)
            inner_r = -local_pitch_radius * 0.5  # Extend to 50% of pitch radius (past root)

            profile_height = outer_r - inner_r
            if profile_height < 0.2:
                continue

            # Thread widths with taper
            local_thread_half_width_root = max(0.05, thread_half_width_root * taper_factor)
            local_thread_half_width_tip = max(0.05, thread_half_width_tip * taper_factor)

            # Profile plane - use helix-perpendicular for proper sweep
            angle = math.atan2(point.Y, point.X)
            radial_dir = Vector(math.cos(angle), math.sin(angle), 0)
            profile_plane = Plane(origin=point, x_dir=radial_dir, z_dir=tangent)

            # Create trapezoidal profile (ZA style for simplicity)
            try:
                with BuildSketch(profile_plane) as sk:
                    with BuildLine():
                        # Extended profile: narrow at top, wide at bottom
                        # Use same angle as normal trapezoidal profile
                        tip_left = (outer_r, -local_thread_half_width_tip)
                        tip_right = (outer_r, local_thread_half_width_tip)

                        # Calculate width at inner_r using pressure angle
                        depth_below_root = (-local_dedendum) - inner_r
                        extra_width = depth_below_root * math.tan(pressure_angle_rad)
                        inner_half_width = local_thread_half_width_root + extra_width

                        inner_left = (inner_r, -inner_half_width)
                        inner_right = (inner_r, inner_half_width)

                        Line(inner_left, tip_left)
                        Line(tip_left, tip_right)
                        Line(tip_right, inner_right)
                        Line(inner_right, inner_left)
                    make_face()

                if sk.sketch.faces():
                    sections.append(sk.sketch.faces()[0])

            except Exception as e:
                logger.warning(f"Section {i} failed: {e}")
                continue

        if len(sections) < 2:
            return None

        try:
            thread = loft(sections, ruled=True)
            return thread
        except Exception as e:
            logger.warning(f"Extended thread loft failed: {e}")
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

    def export_gltf(self, filepath: str, binary: bool = True):
        """Export globoid worm to glTF file (builds if not already built).

        Args:
            filepath: Output path (.glb for binary, .gltf for text)
            binary: If True, export as binary .glb (default)
        """
        if self._part is None:
            raise ValueError("Geometry not built yet. Call build() first.")

        from build123d import export_gltf as b3d_export_gltf
        b3d_export_gltf(
            self._part, filepath, binary=binary,
            linear_deflection=0.001, angular_deflection=0.1,
        )
        logger.info(f"Exported globoid worm to {filepath}")
