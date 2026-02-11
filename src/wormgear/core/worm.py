"""
Worm geometry generation using build123d.

Creates CNC-ready worm geometry with helical threads.
"""

import logging
import math
from typing import Optional, Literal

from OCP.ShapeFix import ShapeFix_Shape, ShapeFix_Solid
from OCP.ShapeUpgrade import ShapeUpgrade_UnifySameDomain
from OCP.BRepBuilderAPI import BRepBuilderAPI_Sewing, BRepBuilderAPI_MakeSolid
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_SHELL, TopAbs_FACE, TopAbs_EDGE
from OCP.TopoDS import TopoDS

logger = logging.getLogger(__name__)
from build123d import (
    Part, Cylinder, Box, Align, Pos, Axis, Vector, Plane,
    BuildSketch, BuildLine, Line, Spline, make_face, loft, sweep, Helix,
    export_step, import_step,
)
from ..io.loaders import WormParams, AssemblyParams
from ..enums import Hand, WormProfile
from .features import BoreFeature, KeywayFeature, SetScrewFeature, ReliefGrooveFeature, add_bore_and_keyway, create_relief_groove

# Profile types per DIN 3975
# ZA: Straight flanks in axial section (Archimedean) - best for CNC machining
# ZK: Slightly convex flanks - better for 3D printing (reduces stress concentrations)
# ZI: Involute helicoid (true involute in normal section) - NOT YET IMPLEMENTED
ProfileType = Literal["ZA", "ZK", "ZI"]


class WormGeometry:
    """
    Generates 3D geometry for a worm.

    Creates worm by sweeping thread profile along helical path,
    then unioning with core cylinder. Optionally adds bore and keyway.
    """

    # Valid generation methods for thread creation
    GENERATION_METHODS = ("loft", "sweep")

    def __init__(
        self,
        params: WormParams,
        assembly_params: AssemblyParams,
        length: float = 40.0,
        sections_per_turn: int = 36,
        bore: Optional[BoreFeature] = None,
        keyway: Optional[KeywayFeature] = None,
        ddcut: Optional['DDCutFeature'] = None,
        set_screw: Optional[SetScrewFeature] = None,
        relief_groove: Optional[ReliefGrooveFeature] = None,
        profile: ProfileType = "ZA",
        generation_method: Literal["loft", "sweep"] = "loft"
    ):
        """
        Initialize worm geometry generator.

        Args:
            params: Worm parameters from calculator
            assembly_params: Assembly parameters (for pressure angle)
            length: Total worm length in mm (default: 40)
            sections_per_turn: Number of loft sections per helix turn (default: 36,
                               only used by loft method)
            bore: Optional bore feature specification
            keyway: Optional keyway feature specification (requires bore, mutually exclusive with ddcut)
            ddcut: Optional double-D cut feature (requires bore, mutually exclusive with keyway)
            set_screw: Optional set screw feature specification (requires bore)
            relief_groove: Optional relief groove at thread termination points
            profile: Tooth profile type per DIN 3975:
                     "ZA" - Straight flanks (trapezoidal) - best for CNC (default)
                     "ZK" - Slightly convex flanks - better for 3D printing
                     "ZI" - Involute (straight in axial section) - for hobbing
            generation_method: Thread generation method:
                     "loft" - Proven loft-based approach (default)
                     "sweep" - Experimental sweep of single profile along helix
        """
        self.params = params
        self.assembly_params = assembly_params
        self.length = length
        self.sections_per_turn = sections_per_turn
        self.bore = bore
        self.keyway = keyway
        self.ddcut = ddcut
        self.set_screw = set_screw
        self.relief_groove = relief_groove
        self.profile = profile.upper() if isinstance(profile, str) else profile
        self.generation_method = generation_method
        if generation_method not in self.GENERATION_METHODS:
            raise ValueError(
                f"Unknown generation_method: {generation_method!r}. "
                f"Must be one of {self.GENERATION_METHODS}"
            )

        # Set keyway as shaft type if specified
        if self.keyway is not None:
            self.keyway.is_shaft = True

        # Cache for built geometry (avoids rebuilding on export)
        self._part = None

    def build(self) -> Part:
        """
        Build the complete worm geometry.

        Returns:
            build123d Part object ready for export
        """
        # Return cached geometry if already built
        if self._part is not None:
            return self._part

        # Multi-start sweep uses per-start build to avoid complex boolean
        # failures (pipe shell topology doesn't survive composite fuse+cut).
        if (self.generation_method == "sweep"
                and self.params.num_starts > 1):
            return self._build_sweep_multi_start()

        root_radius = self.params.root_diameter_mm / 2
        tip_radius = self.params.tip_diameter_mm / 2
        lead = self.params.lead_mm

        # Create thread(s) first to determine helix extent
        logger.info(f"Creating {self.params.num_starts} thread(s)...")
        threads = self._create_threads()
        if threads is None:
            logger.warning("No threads created!")
        else:
            logger.debug("Threads created successfully")

        # Create core slightly longer than final worm to match extended threads
        # We'll trim to exact length after union
        extended_length = self.length + 2 * lead  # Add lead on each end
        # Sweep threads touch core exactly at root_r (zero overlap) causing
        # OCC Fuse to produce disjoint solids.  A tiny overlap forces merge.
        core_radius_adj = root_radius + (0.05 if self.generation_method == "sweep" else 0)
        logger.info(f"Creating core cylinder (radius={core_radius_adj:.2f}mm, height={extended_length:.2f}mm)...")
        core = Cylinder(
            radius=core_radius_adj,
            height=extended_length,
            align=(Align.CENTER, Align.CENTER, Align.CENTER)
        )

        if threads is not None:
            logger.info("Unioning core with threads...")
            # Use OCP fuse for reliable boolean union
            from OCP.BRepAlgoAPI import BRepAlgoAPI_Fuse

            try:
                core_shape = core.wrapped if hasattr(core, 'wrapped') else core
                threads_shape = threads.wrapped if hasattr(threads, 'wrapped') else threads

                fuse_op = BRepAlgoAPI_Fuse(core_shape, threads_shape)
                fuse_op.Build()

                if fuse_op.IsDone():
                    worm = Part(fuse_op.Shape())
                    logger.debug("OCP union complete")
                else:
                    logger.warning("OCP union failed, using build123d operator")
                    worm = core + threads
            except Exception as e:
                logger.warning(f"OCP union error ({e}), using build123d operator")
                worm = core + threads
        else:
            logger.info("No threads to union - using core only")
            worm = core

        # Trim to exact length - removes fragile tapered thread ends
        logger.info(f"Trimming to final length ({self.length:.2f}mm)...")

        # Prepare trim dimensions
        trim_diameter = tip_radius * 4  # Large enough for cutting boxes
        half_length = self.length / 2
        logger.info(f"Cutting at Z = ±{half_length:.2f}mm...")

        from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut

        try:
            worm_shape = worm.wrapped if hasattr(worm, 'wrapped') else worm

            # Create top cutting box (remove everything above +half_length)
            top_cut_box = Box(
                length=trim_diameter,
                width=trim_diameter,
                height=extended_length,
                align=(Align.CENTER, Align.CENTER, Align.MIN)
            )
            # Move box to start at Z = +half_length
            top_cut_box = Pos(0, 0, half_length) * top_cut_box

            # Cut away top part
            cut_top = BRepAlgoAPI_Cut(worm_shape, top_cut_box.wrapped)
            cut_top.Build()

            if cut_top.IsDone():
                worm_shape = cut_top.Shape()
                logger.debug("Top cut successful")
            else:
                logger.warning("Top cut failed")

            # Create bottom cutting box (remove everything below -half_length)
            bottom_cut_box = Box(
                length=trim_diameter,
                width=trim_diameter,
                height=extended_length,
                align=(Align.CENTER, Align.CENTER, Align.MAX)
            )
            # Move box to end at Z = -half_length
            bottom_cut_box = Pos(0, 0, -half_length) * bottom_cut_box

            # Cut away bottom part
            cut_bottom = BRepAlgoAPI_Cut(worm_shape, bottom_cut_box.wrapped)
            cut_bottom.Build()

            if cut_bottom.IsDone():
                worm = Part(cut_bottom.Shape())
                logger.debug("Bottom cut successful")
            else:
                logger.warning("Bottom cut failed")
                worm = Part(worm_shape)

        except Exception as e:
            logger.error(f"Error during cutting: {e}")
            logger.info("Keeping extended worm (no trim)")

        logger.debug("Worm trimmed to length")

        # Repair geometry after complex boolean operations
        worm = self._repair_geometry(worm)

        # Ensure we have a single Solid for proper display and volume.
        # Repair may return a Compound wrapping one valid solid (volume=0 on
        # the Compound but correct on the inner Solid), and boolean trim may
        # split geometry into multiple solids.
        if hasattr(worm, 'solids'):
            solids = list(worm.solids())
            if len(solids) == 1:
                worm = solids[0]
            elif len(solids) > 1:
                worm = max(solids, key=lambda s: s.volume)

        # Cut relief grooves at thread termination points (before bore features)
        if self.relief_groove is not None:
            axial_pitch = self.params.lead_mm / self.params.num_starts
            worm = create_relief_groove(
                worm,
                root_diameter_mm=self.params.root_diameter_mm,
                tip_diameter_mm=self.params.tip_diameter_mm,
                axial_pitch_mm=axial_pitch,
                part_length=self.length,
                groove=self.relief_groove,
                axis=Axis.Z
            )

        # Add bore, keyway/ddcut, and set screw if specified
        if self.bore is not None or self.keyway is not None or self.ddcut is not None or self.set_screw is not None:
            worm = add_bore_and_keyway(
                worm,
                part_length=self.length,
                bore=self.bore,
                keyway=self.keyway,
                ddcut=self.ddcut,
                set_screw=self.set_screw,
                axis=Axis.Z
            )

        logger.debug(f"Final worm volume: {worm.volume:.2f} mm³")
        # Cache the built geometry
        self._part = worm
        return worm

    def _build_sweep_multi_start(self) -> Part:
        """Build multi-start sweep worm by fusing all threads with a shared core.

        Pipe shell solids touch the core cylinder exactly at root_r (zero
        overlap), which causes OCC Fuse to create a compound of disjoint
        solids instead of merging them.  A tiny core radius increase (0.05 mm)
        forces genuine overlap so Fuse produces a single merged solid that
        trims and repairs cleanly.
        """
        from OCP.BRepAlgoAPI import BRepAlgoAPI_Fuse, BRepAlgoAPI_Cut

        root_radius = self.params.root_diameter_mm / 2
        tip_radius = self.params.tip_diameter_mm / 2
        lead = self.params.lead_mm
        extended_length = self.length + 2 * lead
        trim_diameter = tip_radius * 4
        half_length = self.length / 2

        # Build all threads
        threads = []
        for start_index in range(self.params.num_starts):
            angle_offset = (360 / self.params.num_starts) * start_index
            logger.info(f"Building sweep start {start_index} (angle={angle_offset:.0f}°)...")
            thread = self._create_single_thread_sweep(angle_offset)
            if thread is not None:
                threads.append(thread)
                logger.debug(f"Thread {start_index}: volume={thread.volume:.1f}")

        if not threads:
            logger.error("No threads created")
            core = Cylinder(
                radius=root_radius, height=self.length,
                align=(Align.CENTER, Align.CENTER, Align.CENTER)
            )
            self._part = core
            return core

        # Core with 0.05mm overlap so fuse merges into one solid
        core = Cylinder(
            radius=root_radius + 0.05,
            height=extended_length,
            align=(Align.CENTER, Align.CENTER, Align.CENTER)
        )

        # Fuse core + all threads sequentially
        logger.info("Fusing core with threads...")
        worm_shape = core.wrapped
        for thread in threads:
            fuse = BRepAlgoAPI_Fuse(worm_shape, thread.wrapped)
            fuse.Build()
            if fuse.IsDone():
                worm_shape = fuse.Shape()
            else:
                logger.warning("Thread fuse failed")

        # Trim to length
        logger.info(f"Trimming to {self.length:.1f}mm...")
        top_box = Box(
            length=trim_diameter, width=trim_diameter,
            height=extended_length,
            align=(Align.CENTER, Align.CENTER, Align.MIN)
        )
        top_box = Pos(0, 0, half_length) * top_box
        cut = BRepAlgoAPI_Cut(worm_shape, top_box.wrapped)
        cut.Build()
        if cut.IsDone():
            worm_shape = cut.Shape()

        bottom_box = Box(
            length=trim_diameter, width=trim_diameter,
            height=extended_length,
            align=(Align.CENTER, Align.CENTER, Align.MAX)
        )
        bottom_box = Pos(0, 0, -half_length) * bottom_box
        cut = BRepAlgoAPI_Cut(worm_shape, bottom_box.wrapped)
        cut.Build()
        if cut.IsDone():
            worm_shape = cut.Shape()

        worm = Part(worm_shape)

        # Remove degenerate zero-volume solids
        if hasattr(worm, 'solids'):
            solids = list(worm.solids())
            real = [s for s in solids if s.volume > 0.01]
            if len(real) == 1:
                worm = real[0]
            elif len(real) > 1 and len(real) < len(solids):
                shape = real[0].wrapped
                for s in real[1:]:
                    f = BRepAlgoAPI_Fuse(shape, s.wrapped)
                    f.Build()
                    if f.IsDone():
                        shape = f.Shape()
                worm = Part(shape)

        worm = self._repair_geometry(worm)

        # Add features (bore, keyway, etc.)
        if self.relief_groove is not None:
            axial_pitch = self.params.lead_mm / self.params.num_starts
            worm = create_relief_groove(
                worm,
                root_diameter_mm=self.params.root_diameter_mm,
                tip_diameter_mm=self.params.tip_diameter_mm,
                axial_pitch_mm=axial_pitch,
                part_length=self.length,
                groove=self.relief_groove,
                axis=Axis.Z
            )

        if self.bore is not None or self.keyway is not None or self.ddcut is not None or self.set_screw is not None:
            worm = add_bore_and_keyway(
                worm,
                part_length=self.length,
                bore=self.bore,
                keyway=self.keyway,
                ddcut=self.ddcut,
                set_screw=self.set_screw,
                axis=Axis.Z
            )

        logger.debug(f"Final multi-start worm volume: {worm.volume:.2f} mm³")
        self._part = worm
        return worm

    def _repair_geometry(self, part: Part) -> Part:
        """
        Repair topology after complex boolean operations.

        Multi-start worms with lower sections_per_turn can produce geometry
        where OCP boolean operations create multiple shells. This method
        uses multiple repair strategies:
        1. Unify coincident faces
        2. Sew faces into a single shell
        3. Build solid from sewn shell
        4. Apply ShapeFix to fix remaining issues
        5. STEP export/reimport as last resort

        Args:
            part: Part to repair

        Returns:
            Repaired Part (or original if repair fails/unnecessary)
        """
        # If already valid, no repair needed
        if part.is_valid:
            return part

        try:
            shape = part.wrapped if hasattr(part, 'wrapped') else part

            # First try: Unify faces that share the same underlying surface
            unifier = ShapeUpgrade_UnifySameDomain(shape, True, True, True)
            unifier.Build()
            unified = unifier.Shape()

            # Check if repair was sufficient
            result = Part(unified)
            if result.is_valid:
                logger.debug("Geometry repair successful (unify)")
                return result

            # Second try: Sew all faces together into a single shell
            # This is more aggressive and can fix multiple-shell issues
            sewer = BRepBuilderAPI_Sewing(1e-6)  # tolerance in mm

            # Add all faces from the shape
            explorer = TopExp_Explorer(unified, TopAbs_FACE)
            face_count = 0
            while explorer.More():
                sewer.Add(explorer.Current())
                face_count += 1
                explorer.Next()

            if face_count > 0:
                sewer.Perform()
                sewn = sewer.SewedShape()

                # Try to make a solid from the sewn shell
                shell_explorer = TopExp_Explorer(sewn, TopAbs_SHELL)
                if shell_explorer.More():
                    shell = TopoDS.Shell_s(shell_explorer.Current())
                    solid_maker = BRepBuilderAPI_MakeSolid(shell)
                    if solid_maker.IsDone():
                        solid = solid_maker.Solid()

                        # Apply ShapeFix_Solid for final cleanup
                        solid_fixer = ShapeFix_Solid(solid)
                        solid_fixer.Perform()
                        fixed_solid = solid_fixer.Solid()

                        result = Part(fixed_solid)
                        if result.is_valid:
                            logger.debug("Geometry repair successful (sew + solid)")
                            return result

            # Third try: Just use ShapeFix_Shape on original
            fixer = ShapeFix_Shape(unified)
            fixer.Perform()
            fixed = fixer.Shape()

            result = Part(fixed)
            if result.is_valid:
                logger.debug("Geometry repair successful (ShapeFix)")
                return result

            # Fourth try: STEP export/reimport roundtrip
            # This is a reliable fallback that fixes most topology issues
            # by letting the STEP writer/reader normalize the geometry
            import tempfile
            from pathlib import Path

            with tempfile.NamedTemporaryFile(suffix='.step', delete=False) as f:
                step_path = Path(f.name)

            try:
                export_step(part, str(step_path))
                reimported = import_step(str(step_path))

                if reimported.is_valid:
                    logger.debug("Geometry repair successful (STEP roundtrip)")
                    return reimported
            finally:
                step_path.unlink(missing_ok=True)

            # If nothing worked, return the original
            logger.debug("Geometry repair did not achieve valid solid, using original")
            return part

        except Exception as e:
            logger.debug(f"Geometry repair skipped: {e}")
            return part

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
            # Use OCC fuse directly — build123d's + operator can fail on
            # STEP-roundtripped Solids (incompatible Compound/Solid types).
            from OCP.BRepAlgoAPI import BRepAlgoAPI_Fuse as _ThreadFuse
            result_shape = threads[0].wrapped
            for thread in threads[1:]:
                fuse = _ThreadFuse(result_shape, thread.wrapped)
                fuse.Build()
                if fuse.IsDone():
                    result_shape = fuse.Shape()
                else:
                    logger.warning("Thread union failed, using build123d fallback")
                    result = threads[0]
                    for t in threads[1:]:
                        result = result + t
                    return result
            return Part(result_shape)

    def _create_single_thread(self, start_angle: float = 0) -> Part:
        """Dispatch to loft or sweep thread creation method."""
        if self.generation_method == "sweep":
            return self._create_single_thread_sweep(start_angle)
        return self._create_single_thread_loft(start_angle)

    def _create_single_thread_loft(self, start_angle: float = 0) -> Part:
        """
        Create a single helical thread by lofting profiles along a helix.

        Creates many cross-section profiles positioned along the helical path
        and lofts between them with ruled=True for consistent geometry.
        Proven approach with cosine-ramped taper at thread ends.
        """
        import math

        pitch_radius = self.params.pitch_diameter_mm / 2
        tip_radius = self.params.tip_diameter_mm / 2
        root_radius = self.params.root_diameter_mm / 2
        lead = self.params.lead_mm
        is_right_hand = self.params.hand == Hand.RIGHT
        logger.debug(f"Thread: pitch_r={pitch_radius:.2f}, tip_r={tip_radius:.2f}, root_r={root_radius:.2f}, lead={lead:.2f}mm")

        # Thread profile dimensions
        pressure_angle_rad = math.radians(self.assembly_params.pressure_angle_deg)

        # Thread width at pitch circle (axial measurement)
        thread_half_width_pitch = self.params.thread_thickness_mm / 2

        # Thread is WIDER at root, NARROWER at tip due to pressure angle
        addendum = self.params.addendum_mm
        dedendum = self.params.dedendum_mm
        thread_half_width_root = thread_half_width_pitch + dedendum * math.tan(pressure_angle_rad)
        thread_half_width_tip = max(0.1, thread_half_width_pitch - addendum * math.tan(pressure_angle_rad))

        # Extend thread length beyond worm length so we can trim to exact length
        extended_length = self.length + 2 * lead  # Add lead on each end

        # Build helix with extended length
        helix_height = extended_length
        num_turns = extended_length / lead  # Exact number of turns for extended length

        # Create helix path at pitch radius
        # For left-hand worms, use negative pitch to reverse rotation direction
        # (not negative Z direction, which would shift the helix out of range)
        helix = Helix(
            pitch=lead if is_right_hand else -lead,
            height=helix_height,
            radius=pitch_radius,
            center=(0, 0, -helix_height / 2),
            direction=(0, 0, 1)
        )

        if start_angle != 0:
            helix = helix.rotate(Axis.Z, start_angle)

        # Get addendum and dedendum for tapering
        addendum = self.params.addendum_mm
        dedendum = self.params.dedendum_mm

        # Extend thread length beyond worm length so we can trim to exact length
        # This removes the fragile tapered ends
        extended_length = self.length + 2 * lead  # Add lead on each end

        # Create profiles along the helix for lofting
        # Use extended length for sections calculation
        num_sections = int((extended_length / lead) * self.sections_per_turn) + 1
        # Ensure at least 2 sections for loft operations (division by num_sections - 1)
        num_sections = max(2, num_sections)
        sections = []

        # Thread end taper: ramp down thread depth over ~1 lead at each end
        # These tapered ends will be trimmed off, but they ensure smooth geometry
        taper_length = lead  # Taper zone length at each end

        for i in range(num_sections):
            t = i / (num_sections - 1)
            point = helix @ t
            tangent = helix % t

            # Calculate taper factor for smooth thread ends
            # Ramps from 0 to 1 over taper_length at each end
            # Use parameter t along helix (0 to 1) instead of z_position
            # This works correctly for both left and right hand worms
            dist_along_helix = t * extended_length
            dist_from_start = dist_along_helix
            dist_from_end = extended_length - dist_along_helix

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

            # Apply taper to addendum/dedendum
            local_addendum = addendum * taper_factor
            local_dedendum = dedendum * taper_factor

            # Calculate local tip and root radii
            local_tip_radius = pitch_radius + local_addendum
            local_root_radius = pitch_radius - local_dedendum

            # Validate profile is meaningful (avoid degenerate profiles)
            profile_height = local_addendum + local_dedendum
            if profile_height < 0.1:  # Less than 0.1mm - skip degenerate section
                continue

            # Profile coordinates relative to pitch radius
            # inner_r is negative (below pitch), outer_r is positive (above pitch)
            inner_r = -local_dedendum
            outer_r = local_addendum

            # Apply taper to thread width with minimum to avoid zero-width profiles
            local_thread_half_width_root = max(0.05, thread_half_width_root * taper_factor)
            local_thread_half_width_tip = max(0.05, thread_half_width_tip * taper_factor)

            # Radial direction at this point
            angle = math.atan2(point.Y, point.X)
            radial_dir = Vector(math.cos(angle), math.sin(angle), 0)

            # Profile plane perpendicular to helix tangent
            profile_plane = Plane(origin=point, x_dir=radial_dir, z_dir=tangent)

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
                        # Arc should be tangent at approximately pitch radius
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
                            # Maximum at mid-flank
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
                        # surface geometry, not the 2D cross-section shape. Both have
                        # straight flanks in the axial section.
                        #
                        # Therefore, ZI for worms = ZA (straight trapezoidal profile)
                        # The involute helicoid property is achieved through the helix
                        # sweep, not through curved cross-section flanks.

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
                make_face()

            sections.append(sk.sketch.faces()[0])

        # Loft with ruled=True for consistent geometry
        logger.debug(f"Lofting {len(sections)} sections...")
        thread = loft(sections, ruled=True)
        logger.debug("Thread lofted successfully")

        return thread

    def _create_single_thread_sweep(self, start_angle: float = 0) -> Part:
        """
        Create a single helical thread by sweeping one profile along a helix.

        Uses OCC's BRepOffsetAPI_MakePipeShell directly with a Z-axis auxiliary
        direction to keep the profile radially oriented. This produces a
        continuous helical surface without loft seams, resulting in cleaner
        topology and smaller STEP files.

        The direct OCC approach (vs build123d's sweep wrapper) gives:
        - Consistent radial dimensions at all Z positions
        - Correct volume matching loft within 0.5%
        - Proper solid creation via STEP roundtrip normalization
        """
        from OCP.BRepOffsetAPI import BRepOffsetAPI_MakePipeShell
        from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeWire
        from OCP.gp import gp_Dir

        pitch_radius = self.params.pitch_diameter_mm / 2
        lead = self.params.lead_mm
        is_right_hand = self.params.hand == Hand.RIGHT
        logger.debug(f"Sweep thread: pitch_r={pitch_radius:.2f}, lead={lead:.2f}mm")

        # Thread profile dimensions
        pressure_angle_rad = math.radians(self.assembly_params.pressure_angle_deg)
        thread_half_width_pitch = self.params.thread_thickness_mm / 2

        addendum = self.params.addendum_mm
        dedendum = self.params.dedendum_mm
        thread_half_width_root = thread_half_width_pitch + dedendum * math.tan(pressure_angle_rad)
        thread_half_width_tip = max(0.1, thread_half_width_pitch - addendum * math.tan(pressure_angle_rad))

        # Extend helix beyond worm length so trim-to-length removes thread ends
        extended_length = self.length + 2 * lead

        # Create helix path at pitch radius
        helix = Helix(
            pitch=lead if is_right_hand else -lead,
            height=extended_length,
            radius=pitch_radius,
            center=(0, 0, -extended_length / 2),
            direction=(0, 0, 1)
        )

        if start_angle != 0:
            helix = helix.rotate(Axis.Z, start_angle)

        # Position profile at helix start, perpendicular to tangent
        start_point = helix @ 0
        start_tangent = helix % 0
        angle = math.atan2(start_point.Y, start_point.X)
        radial_dir = Vector(math.cos(angle), math.sin(angle), 0)

        profile_plane = Plane(origin=start_point, x_dir=radial_dir, z_dir=start_tangent)

        inner_r = -dedendum
        outer_r = addendum

        # Build the 2D profile on the profile plane
        with BuildSketch(profile_plane) as sk:
            with BuildLine():
                if self.profile in (WormProfile.ZA, "ZA", WormProfile.ZI, "ZI"):
                    Line((inner_r, -thread_half_width_root), (outer_r, -thread_half_width_tip))
                    Line((outer_r, -thread_half_width_tip), (outer_r, thread_half_width_tip))
                    Line((outer_r, thread_half_width_tip), (inner_r, thread_half_width_root))
                    Line((inner_r, thread_half_width_root), (inner_r, -thread_half_width_root))

                elif self.profile in (WormProfile.ZK, "ZK"):
                    num_points = 9
                    left_flank = []
                    right_flank = []
                    arc_radius = 0.45 * self.params.module_mm
                    flank_height = outer_r - inner_r

                    for j in range(num_points):
                        t = j / (num_points - 1)
                        r_pos = inner_r + t * flank_height
                        linear_width = thread_half_width_root + t * (thread_half_width_tip - thread_half_width_root)
                        arc_param = t * math.pi
                        arc_bulge = arc_radius * 0.15 * math.sin(arc_param)
                        width = linear_width + arc_bulge
                        left_flank.append((r_pos, -width))
                        right_flank.append((r_pos, width))

                    Spline(left_flank)
                    Line(left_flank[-1], right_flank[-1])
                    Spline(list(reversed(right_flank)))
                    Line(right_flank[0], left_flank[0])

                else:
                    raise ValueError(f"Unknown profile type: {self.profile}")
            make_face()

        profile_face = sk.sketch.faces()[0]

        # Build helix wire for OCC pipe shell
        wire_maker = BRepBuilderAPI_MakeWire()
        explorer = TopExp_Explorer(helix.wrapped, TopAbs_EDGE)
        while explorer.More():
            wire_maker.Add(TopoDS.Edge_s(explorer.Current()))
            explorer.Next()
        helix_wire = wire_maker.Wire()

        # Create pipe shell with Z-axis auxiliary direction.
        # SetMode(gp_Dir(0,0,1)) constrains the profile frame so the radial
        # direction always points away from the Z axis as the profile sweeps
        # along the helix — producing constant tip/root radii at all Z.
        logger.debug("Sweeping profile along helix (OCC MakePipeShell)...")
        pipe = BRepOffsetAPI_MakePipeShell(helix_wire)
        pipe.SetMode(gp_Dir(0, 0, 1))
        pipe.Add(profile_face.outer_wire().wrapped)
        pipe.Build()

        if not pipe.IsDone():
            raise RuntimeError("OCC MakePipeShell failed to build")

        pipe.MakeSolid()

        # STEP roundtrip normalizes the pipe shell topology so that:
        # - Part.volume reports correctly (raw pipe shell returns 0)
        # - Boolean fuse/cut operations work reliably (multi-start union)
        # This adds ~0.5s overhead but avoids multiple downstream issues.
        import tempfile
        from pathlib import Path

        with tempfile.NamedTemporaryFile(suffix='.step', delete=False) as f:
            step_path = Path(f.name)

        try:
            export_step(Part(pipe.Shape()), str(step_path))
            imported = import_step(str(step_path))
            # import_step returns a Compound; extract the single Solid so that
            # downstream BRepAlgoAPI_Fuse gets a TopoDS_Solid, not a Compound.
            solids = list(imported.solids())
            if len(solids) == 1:
                thread = solids[0]
            else:
                thread = max(solids, key=lambda s: s.volume)
            logger.debug(f"Sweep completed: volume={thread.volume:.1f}")
        finally:
            step_path.unlink(missing_ok=True)

        return thread

    def show(self):
        """Display the worm in OCP viewer (requires ocp_vscode)."""
        worm = self.build()
        try:
            from ocp_vscode import show as ocp_show
            ocp_show(worm)
        except ImportError:
            pass  # No viewer available - silent fallback
        return worm

    def export_step(self, filepath: str):
        """Export worm to STEP file (builds if not already built)."""
        if self._part is None:
            self.build()

        logger.info(f"Exporting worm: volume={self._part.volume:.2f} mm³")
        if hasattr(self._part, 'export_step'):
            self._part.export_step(filepath)
        else:
            from build123d import export_step as exp_step
            exp_step(self._part, filepath)

        logger.info(f"Exported worm to {filepath}")
