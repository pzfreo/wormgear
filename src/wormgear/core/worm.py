"""
Worm geometry generation using build123d.

Creates CNC-ready worm geometry with helical threads.
"""

import logging
import math
from typing import Optional, Literal

from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_EDGE
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
from .geometry_base import BaseGeometry
from .geometry_repair import repair_geometry

# Profile types per DIN 3975
# ZA: Straight flanks in axial section (Archimedean) - best for CNC machining
# ZK: Slightly convex flanks - better for 3D printing (reduces stress concentrations)
# ZI: Involute helicoid (true involute in normal section) - NOT YET IMPLEMENTED
ProfileType = Literal["ZA", "ZK", "ZI"]


class WormGeometry(BaseGeometry):
    """
    Generates 3D geometry for a worm.

    Creates worm by sweeping thread profile along helical path,
    then unioning with core cylinder. Optionally adds bore and keyway.
    """

    _part_name = "worm"
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
        generation_method: Literal["loft", "sweep"] = "sweep"
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

    def _compute_thread_dimensions(self) -> dict:
        """Compute common thread profile dimensions from parameters.

        Returns dict with: pitch_radius, lead, is_right_hand, pressure_angle_rad,
        addendum, dedendum, thread_half_width_pitch, thread_half_width_root,
        thread_half_width_tip
        """
        pitch_radius = self.params.pitch_diameter_mm / 2
        lead = self.params.lead_mm
        is_right_hand = self.params.hand == Hand.RIGHT
        pressure_angle_rad = math.radians(self.assembly_params.pressure_angle_deg)
        thread_half_width_pitch = self.params.thread_thickness_mm / 2
        addendum = self.params.addendum_mm
        dedendum = self.params.dedendum_mm
        thread_half_width_root = thread_half_width_pitch + dedendum * math.tan(pressure_angle_rad)
        thread_half_width_tip = max(0.1, thread_half_width_pitch - addendum * math.tan(pressure_angle_rad))
        return {
            'pitch_radius': pitch_radius,
            'lead': lead,
            'is_right_hand': is_right_hand,
            'pressure_angle_rad': pressure_angle_rad,
            'addendum': addendum,
            'dedendum': dedendum,
            'thread_half_width_pitch': thread_half_width_pitch,
            'thread_half_width_root': thread_half_width_root,
            'thread_half_width_tip': thread_half_width_tip,
        }

    def _create_helix(self, height: float, start_angle: float = 0):
        """Create a helix at pitch radius with optional rotation.

        Args:
            height: Total helix height
            start_angle: Angular offset in degrees (for multi-start)
        """
        pitch_radius = self.params.pitch_diameter_mm / 2
        lead = self.params.lead_mm
        is_right_hand = self.params.hand == Hand.RIGHT
        helix = Helix(
            pitch=lead if is_right_hand else -lead,
            height=height,
            radius=pitch_radius,
            center=(0, 0, -height / 2),
            direction=(0, 0, 1)
        )
        if start_angle != 0:
            helix = helix.rotate(Axis.Z, start_angle)
        return helix

    @staticmethod
    def _create_profile_plane(point, z_dir) -> Plane:
        """Create a profile plane at point with x_dir pointing radially outward."""
        angle = math.atan2(point.Y, point.X)
        radial_dir = Vector(math.cos(angle), math.sin(angle), 0)
        return Plane(origin=point, x_dir=radial_dir, z_dir=z_dir)

    @staticmethod
    def _helix_to_wire(helix):
        """Convert a build123d Helix to an OCC TopoDS_Wire."""
        from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeWire
        wire_maker = BRepBuilderAPI_MakeWire()
        explorer = TopExp_Explorer(helix.wrapped, TopAbs_EDGE)
        while explorer.More():
            wire_maker.Add(TopoDS.Edge_s(explorer.Current()))
            explorer.Next()
        return wire_maker.Wire()

    def _trim_to_length(self, worm_shape) -> Part:
        """Trim worm shape to exact self.length using top/bottom box cuts.

        Args:
            worm_shape: TopoDS_Shape or Part to trim

        Returns:
            Trimmed Part with exact self.length dimension
        """
        from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut

        tip_radius = self.params.tip_diameter_mm / 2
        lead = self.params.lead_mm
        extended_length = self.length + 2 * lead
        trim_diameter = tip_radius * 4
        half_length = self.length / 2

        shape = worm_shape.wrapped if hasattr(worm_shape, 'wrapped') else worm_shape

        try:
            top_box = Box(
                length=trim_diameter, width=trim_diameter,
                height=extended_length,
                align=(Align.CENTER, Align.CENTER, Align.MIN)
            )
            top_box = Pos(0, 0, half_length) * top_box
            cut = BRepAlgoAPI_Cut(shape, top_box.wrapped)
            cut.Build()
            if cut.IsDone():
                shape = cut.Shape()
                logger.debug("Top cut successful")
            else:
                logger.warning("Top cut failed")

            bottom_box = Box(
                length=trim_diameter, width=trim_diameter,
                height=extended_length,
                align=(Align.CENTER, Align.CENTER, Align.MAX)
            )
            bottom_box = Pos(0, 0, -half_length) * bottom_box
            cut = BRepAlgoAPI_Cut(shape, bottom_box.wrapped)
            cut.Build()
            if cut.IsDone():
                shape = cut.Shape()
                logger.debug("Bottom cut successful")
            else:
                logger.warning("Bottom cut failed")

            return Part(shape)

        except Exception as e:
            logger.error(f"Error during cutting: {e}")
            logger.info("Keeping extended worm (no trim)")
            return worm_shape if isinstance(worm_shape, Part) else Part(shape)

    @staticmethod
    def _extract_single_solid(part: Part) -> Part:
        """Extract a single solid from a Part, fusing significant solids if needed."""
        if not hasattr(part, 'solids'):
            return part
        solids = list(part.solids())
        if len(solids) == 1:
            return solids[0]
        if len(solids) == 0:
            return part
        real = [s for s in solids if s.volume > 1.0]
        if len(real) == 1:
            return real[0]
        elif len(real) > 1:
            from OCP.BRepAlgoAPI import BRepAlgoAPI_Fuse as _Fuse
            shape = real[0].wrapped
            for s in real[1:]:
                f = _Fuse(shape, s.wrapped)
                f.Build()
                if f.IsDone():
                    shape = f.Shape()
            return Part(shape)
        else:
            return max(solids, key=lambda s: s.volume)

    def _apply_features(self, part: Part) -> Part:
        """Apply relief groove, bore, keyway, DD-cut, and set screw features."""
        if self.relief_groove is not None:
            axial_pitch = self.params.lead_mm / self.params.num_starts
            part = create_relief_groove(
                part,
                root_diameter_mm=self.params.root_diameter_mm,
                tip_diameter_mm=self.params.tip_diameter_mm,
                axial_pitch_mm=axial_pitch,
                part_length=self.length,
                groove=self.relief_groove,
                axis=Axis.Z
            )
        if self.bore is not None or self.keyway is not None or self.ddcut is not None or self.set_screw is not None:
            part = add_bore_and_keyway(
                part,
                part_length=self.length,
                bore=self.bore,
                keyway=self.keyway,
                ddcut=self.ddcut,
                set_screw=self.set_screw,
                axis=Axis.Z
            )
        return part

    def build(self) -> Part:
        """
        Build the complete worm geometry.

        Returns:
            build123d Part object ready for export
        """
        # Return cached geometry if already built
        if self._part is not None:
            return self._part

        # Sweep uses groove-cut approach (full cylinder minus swept grooves)
        # because OCC BRepAlgoAPI_Fuse cannot merge pipe shell solids with
        # concentric cylinders — it produces disjoint compounds instead.
        if self.generation_method == "sweep":
            return self._build_sweep()

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
        worm = self._trim_to_length(worm)

        # Repair geometry after complex boolean operations
        worm = repair_geometry(worm)

        # Ensure we have a single Solid for proper display and volume
        worm = self._extract_single_solid(worm)

        # Apply features (relief grooves, bore, keyway, etc.)
        worm = self._apply_features(worm)

        logger.debug(f"Final worm volume: {worm.volume:.2f} mm³")
        # Cache the built geometry
        self._part = worm
        return worm

    def _build_sweep(self) -> Part:
        """Build sweep worm by cutting grooves from a full cylinder.

        OCC's BRepAlgoAPI_Fuse cannot merge pipe shell solids with concentric
        cylinders — it always produces disjoint compounds regardless of overlap.
        The groove-cut approach avoids this: start with a full cylinder at tip
        radius, then cut swept groove profiles to create the thread geometry.
        This works for both single-start and multi-start worms.
        """
        from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut

        tip_radius = self.params.tip_diameter_mm / 2
        lead = self.params.lead_mm
        extended_length = self.length + 2 * lead

        # Full cylinder at tip radius.
        # The blank must be slightly taller than the groove helix to avoid
        # coincident end-cap faces, which cause OCC boolean cuts to fail
        # silently (the cut succeeds but removes zero material).
        blank_length = extended_length + 2  # 1mm margin beyond each end
        logger.info(f"Creating full cylinder (radius={tip_radius:.2f}mm)...")
        worm_shape = Cylinder(
            radius=tip_radius,
            height=blank_length,
            align=(Align.CENTER, Align.CENTER, Align.CENTER)
        ).wrapped

        # Cut groove for each start
        for start_index in range(self.params.num_starts):
            angle_offset = (360 / self.params.num_starts) * start_index
            logger.info(f"Cutting groove {start_index} (angle={angle_offset:.0f}°)...")
            groove = self._create_single_groove_sweep(angle_offset)
            if groove is not None:
                cut = BRepAlgoAPI_Cut(worm_shape, groove.wrapped)
                cut.Build()
                if cut.IsDone():
                    worm_shape = cut.Shape()
                    logger.debug(f"Groove {start_index} cut successfully")
                else:
                    logger.warning(f"Groove {start_index} cut failed")

        # Trim to length
        logger.info(f"Trimming to {self.length:.1f}mm...")
        worm = self._trim_to_length(worm_shape)

        # Extract single solid or fuse significant solids
        worm = self._extract_single_solid(worm)

        worm = repair_geometry(worm)

        # Apply features (relief grooves, bore, keyway, etc.)
        worm = self._apply_features(worm)

        logger.debug(f"Final sweep worm volume: {worm.volume:.2f} mm³")
        self._part = worm
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
        dims = self._compute_thread_dimensions()
        pitch_radius = dims['pitch_radius']
        lead = dims['lead']
        addendum = dims['addendum']
        dedendum = dims['dedendum']
        thread_half_width_root = dims['thread_half_width_root']
        thread_half_width_tip = dims['thread_half_width_tip']
        logger.debug(f"Thread: pitch_r={pitch_radius:.2f}, tip_r={self.params.tip_diameter_mm/2:.2f}, root_r={self.params.root_diameter_mm/2:.2f}, lead={lead:.2f}mm")

        # Extend thread length beyond worm length so we can trim to exact length
        extended_length = self.length + 2 * lead
        helix = self._create_helix(extended_length, start_angle)

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

            # Profile plane perpendicular to helix tangent
            profile_plane = self._create_profile_plane(point, tangent)

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

    def _create_single_groove_sweep(self, start_angle: float = 0) -> Part:
        """
        Create a single helical groove solid for the groove-cut approach.

        The groove is the space between thread teeth — its profile is the
        complement of the thread profile. Swept along a helix offset by
        half the axial pitch from the thread helix.

        The groove profile extends past both root and tip radii to ensure
        clean boolean cuts against the full cylinder.
        """
        from OCP.BRepOffsetAPI import BRepOffsetAPI_MakePipeShell
        from OCP.gp import gp_Dir

        lead = self.params.lead_mm
        axial_pitch = lead / self.params.num_starts

        # Thread profile dimensions
        pressure_angle_rad = math.radians(self.assembly_params.pressure_angle_deg)
        thread_half_width_pitch = self.params.thread_thickness_mm / 2

        addendum = self.params.addendum_mm
        dedendum = self.params.dedendum_mm

        # Groove is the complement of the thread
        # At pitch: groove_width = axial_pitch - thread_width
        groove_half_width_pitch = (axial_pitch - self.params.thread_thickness_mm) / 2

        # Extend groove radially past tip for clean boolean cuts.
        # Scale with module so it's proportional at all sizes.
        groove_extend = max(0.1, self.params.module_mm * 0.25)

        # Groove flanks: width varies linearly with radial position (ZA profile).
        # Compute width at the actual outer_r and inner_r positions so the
        # trapezoid shape is correct at the tip surface (not interpolated).
        groove_half_width_outer = groove_half_width_pitch + (addendum + groove_extend) * math.tan(pressure_angle_rad)
        groove_half_width_root = max(0.1, groove_half_width_pitch - dedendum * math.tan(pressure_angle_rad))


        # Extended helix, offset by half axial pitch from thread
        extended_length = self.length + 2 * lead
        groove_angle = start_angle + (180.0 / self.params.num_starts)
        helix = self._create_helix(extended_length, groove_angle)

        # Position profile at helix start
        start_point = helix @ 0
        start_tangent = helix % 0
        profile_plane = self._create_profile_plane(start_point, start_tangent)

        # Groove radial extent: exactly at root, past tip for clean cut.
        # inner_r at root preserves correct root diameter (remaining cylinder
        # material below root forms the core). outer_r extends past tip to
        # cut cleanly through the full cylinder surface.
        inner_r = -dedendum
        outer_r = addendum + groove_extend

        with BuildSketch(profile_plane) as sk:
            with BuildLine():
                if self.profile in (WormProfile.ZA, "ZA", WormProfile.ZI, "ZI"):
                    # Trapezoidal groove (complement of thread)
                    Line((inner_r, -groove_half_width_root), (outer_r, -groove_half_width_outer))
                    Line((outer_r, -groove_half_width_outer), (outer_r, groove_half_width_outer))
                    Line((outer_r, groove_half_width_outer), (inner_r, groove_half_width_root))
                    Line((inner_r, groove_half_width_root), (inner_r, -groove_half_width_root))

                elif self.profile in (WormProfile.ZK, "ZK"):
                    # ZK groove: arc flanks (complement of ZK thread arc)
                    num_points = 9
                    left_flank = []
                    right_flank = []
                    arc_radius = 0.45 * self.params.module_mm
                    flank_height = outer_r - inner_r

                    for j in range(num_points):
                        t = j / (num_points - 1)
                        r_pos = inner_r + t * flank_height
                        linear_width = groove_half_width_root + t * (groove_half_width_outer - groove_half_width_root)
                        arc_param = t * math.pi
                        # Groove arc bulges inward (negative) where thread bulges outward
                        arc_bulge = -arc_radius * 0.15 * math.sin(arc_param)
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

        groove_face = sk.sketch.faces()[0]

        # Build helix wire
        helix_wire = self._helix_to_wire(helix)

        # Sweep groove along helix
        logger.debug("Sweeping groove profile along helix...")
        pipe = BRepOffsetAPI_MakePipeShell(helix_wire)
        pipe.SetMode(gp_Dir(0, 0, 1))
        pipe.Add(groove_face.outer_wire().wrapped)
        pipe.Build()

        if not pipe.IsDone():
            raise RuntimeError("OCC MakePipeShell failed for groove sweep")

        pipe.MakeSolid()

        groove = Part(pipe.Shape())
        logger.debug(f"Groove sweep completed")

        return groove

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
        from OCP.gp import gp_Dir

        dims = self._compute_thread_dimensions()
        addendum = dims['addendum']
        dedendum = dims['dedendum']
        thread_half_width_root = dims['thread_half_width_root']
        thread_half_width_tip = dims['thread_half_width_tip']
        lead = dims['lead']
        logger.debug(f"Sweep thread: pitch_r={dims['pitch_radius']:.2f}, lead={lead:.2f}mm")

        # Extend helix beyond worm length so trim-to-length removes thread ends
        extended_length = self.length + 2 * lead
        helix = self._create_helix(extended_length, start_angle)

        # Position profile at helix start, perpendicular to tangent
        start_point = helix @ 0
        start_tangent = helix % 0
        profile_plane = self._create_profile_plane(start_point, start_tangent)

        # Profile radial positions:
        # root_r = original root position (at core surface)
        # ext_r  = extended position 0.5mm inside core for genuine fuse overlap
        # outer_r = tip position
        # The rectangular extension (ext_r to root_r) is invisible after fuse
        # with the core cylinder, but ensures BRepAlgoAPI_Fuse merges the
        # thread and core into a single solid instead of producing disjoint bodies.
        overlap_ext = 0.5
        root_r = -dedendum
        ext_r = root_r - overlap_ext
        outer_r = addendum

        # Build the 2D profile on the profile plane
        with BuildSketch(profile_plane) as sk:
            with BuildLine():
                if self.profile in (WormProfile.ZA, "ZA", WormProfile.ZI, "ZI"):
                    # 6-point profile: rectangular extension + original trapezoid
                    # Preserves flank angles while extending into core
                    Line((ext_r, -thread_half_width_root), (root_r, -thread_half_width_root))  # Bottom-left horizontal
                    Line((root_r, -thread_half_width_root), (outer_r, -thread_half_width_tip))  # Left flank
                    Line((outer_r, -thread_half_width_tip), (outer_r, thread_half_width_tip))   # Tip
                    Line((outer_r, thread_half_width_tip), (root_r, thread_half_width_root))     # Right flank
                    Line((root_r, thread_half_width_root), (ext_r, thread_half_width_root))      # Bottom-right horizontal
                    Line((ext_r, thread_half_width_root), (ext_r, -thread_half_width_root))      # Bottom (closes)

                elif self.profile in (WormProfile.ZK, "ZK"):
                    num_points = 9
                    left_flank = []
                    right_flank = []
                    arc_radius = 0.45 * self.params.module_mm
                    flank_height = outer_r - root_r  # Flank from root_r (not ext_r)

                    for j in range(num_points):
                        t = j / (num_points - 1)
                        r_pos = root_r + t * flank_height  # Flanks start at root_r
                        linear_width = thread_half_width_root + t * (thread_half_width_tip - thread_half_width_root)
                        arc_param = t * math.pi
                        arc_bulge = arc_radius * 0.15 * math.sin(arc_param)
                        width = linear_width + arc_bulge
                        left_flank.append((r_pos, -width))
                        right_flank.append((r_pos, width))

                    # Add rectangular extension below flanks for core overlap
                    ext_bottom_left = (ext_r, left_flank[0][1])
                    ext_bottom_right = (ext_r, right_flank[0][1])
                    Line(ext_bottom_left, left_flank[0])             # Bottom-left to root-left
                    Spline(left_flank)                                # Left flank (arc)
                    Line(left_flank[-1], right_flank[-1])             # Tip
                    Spline(list(reversed(right_flank)))               # Right flank (arc)
                    Line(right_flank[0], ext_bottom_right)            # Root-right to bottom-right
                    Line(ext_bottom_right, ext_bottom_left)           # Bottom (closes)

                else:
                    raise ValueError(f"Unknown profile type: {self.profile}")
            make_face()

        profile_face = sk.sketch.faces()[0]

        # Build helix wire for OCC pipe shell
        helix_wire = self._helix_to_wire(helix)

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

