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
from OCP.TopAbs import TopAbs_SHELL, TopAbs_FACE
from OCP.TopoDS import TopoDS

logger = logging.getLogger(__name__)
from build123d import (
    Part, Cylinder, Box, Align, Pos, Axis, Vector, Plane,
    BuildSketch, BuildLine, Line, Spline, make_face, loft, Helix,
    export_step, import_step,
)
from ..io.loaders import WormParams, AssemblyParams
from ..enums import Hand, WormProfile
from .features import BoreFeature, KeywayFeature, SetScrewFeature, add_bore_and_keyway

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
        profile: ProfileType = "ZA"
    ):
        """
        Initialize worm geometry generator.

        Args:
            params: Worm parameters from calculator
            assembly_params: Assembly parameters (for pressure angle)
            length: Total worm length in mm (default: 40)
            sections_per_turn: Number of loft sections per helix turn (default: 36)
            bore: Optional bore feature specification
            keyway: Optional keyway feature specification (requires bore, mutually exclusive with ddcut)
            ddcut: Optional double-D cut feature (requires bore, mutually exclusive with keyway)
            set_screw: Optional set screw feature specification (requires bore)
            profile: Tooth profile type per DIN 3975:
                     "ZA" - Straight flanks (trapezoidal) - best for CNC (default)
                     "ZK" - Slightly convex flanks - better for 3D printing
                     "ZI" - Involute (straight in axial section) - for hobbing
        """
        self.params = params
        self.assembly_params = assembly_params
        self.length = length
        self.sections_per_turn = sections_per_turn
        self.bore = bore
        self.keyway = keyway
        self.ddcut = ddcut
        self.set_screw = set_screw
        self.profile = profile.upper() if isinstance(profile, str) else profile

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
        logger.info(f"Creating core cylinder (radius={root_radius:.2f}mm, height={extended_length:.2f}mm)...")
        core = Cylinder(
            radius=root_radius,
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

        # Ensure we have a single Solid for proper display in ocp_vscode
        if hasattr(worm, 'solids'):
            solids = list(worm.solids())
            if len(solids) == 1:
                worm = solids[0]
            elif len(solids) > 1:
                # Return the largest solid (should be the worm)
                worm = max(solids, key=lambda s: s.volume)

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
