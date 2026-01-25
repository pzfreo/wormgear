"""
Worm geometry generation using build123d.

Creates CNC-ready worm geometry with helical threads.
"""

import math
from typing import Optional, Literal
from build123d import *
from ..io.loaders import WormParams, AssemblyParams
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

    def build(self) -> Part:
        """
        Build the complete worm geometry.

        Returns:
            build123d Part object ready for export
        """
        root_radius = self.params.root_diameter_mm / 2
        tip_radius = self.params.tip_diameter_mm / 2
        lead = self.params.lead_mm

        # Create thread(s) first to determine helix extent
        print(f"    Creating {self.params.num_starts} thread(s)...")
        threads = self._create_threads()
        if threads is None:
            print("    WARNING: No threads created!")
        else:
            print(f"    ✓ Threads created")

        # Create core slightly longer than final worm to match extended threads
        # We'll trim to exact length after union
        extended_length = self.length + 2 * lead  # Add lead on each end
        print(f"    Creating core cylinder (radius={root_radius:.2f}mm, height={extended_length:.2f}mm)...")
        core = Cylinder(
            radius=root_radius,
            height=extended_length,
            align=(Align.CENTER, Align.CENTER, Align.CENTER)
        )

        if threads is not None:
            print(f"    Unioning core with threads...")
            # Use OCP fuse for reliable boolean union
            from OCP.BRepAlgoAPI import BRepAlgoAPI_Fuse

            try:
                core_shape = core.wrapped if hasattr(core, 'wrapped') else core
                threads_shape = threads.wrapped if hasattr(threads, 'wrapped') else threads

                fuse_op = BRepAlgoAPI_Fuse(core_shape, threads_shape)
                fuse_op.Build()

                if fuse_op.IsDone():
                    worm = Part(fuse_op.Shape())
                    print(f"    ✓ OCP union complete")
                else:
                    print(f"    WARNING: OCP union failed, using build123d operator")
                    worm = core + threads
            except Exception as e:
                print(f"    WARNING: OCP union error ({e}), using build123d operator")
                worm = core + threads
        else:
            print(f"    No threads to union - using core only")
            worm = core

        # Trim to exact length - removes fragile tapered thread ends
        print(f"    Trimming to final length ({self.length:.2f}mm)...")

        # Prepare trim dimensions
        trim_diameter = tip_radius * 4  # Large enough for cutting boxes
        half_length = self.length / 2
        print(f"    Cutting at Z = ±{half_length:.2f}mm...")

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
                print(f"    ✓ Top cut successful")
            else:
                print(f"    WARNING: Top cut failed")

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
                print(f"    ✓ Bottom cut successful")
            else:
                print(f"    WARNING: Bottom cut failed")
                worm = Part(worm_shape)

        except Exception as e:
            print(f"    ERROR during cutting: {e}")
            print(f"    Keeping extended worm (no trim)")

        print(f"    ✓ Worm trimmed to length")

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

        print(f"    ✓ Final worm volume: {worm.volume:.2f} mm³")
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
        import math

        pitch_radius = self.params.pitch_diameter_mm / 2
        tip_radius = self.params.tip_diameter_mm / 2
        root_radius = self.params.root_diameter_mm / 2
        lead = self.params.lead_mm
        is_right_hand = self.params.hand.upper() == "RIGHT"
        print(f"      Thread: pitch_r={pitch_radius:.2f}, tip_r={tip_radius:.2f}, root_r={root_radius:.2f}, lead={lead:.2f}mm")

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
        helix = Helix(
            pitch=lead,
            height=helix_height,
            radius=pitch_radius,
            center=(0, 0, -helix_height / 2),
            direction=(0, 0, 1) if is_right_hand else (0, 0, -1)
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
            # Use extended length for taper calculation
            half_width = extended_length / 2.0
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

            # Apply taper to addendum/dedendum (matching globoid approach)
            local_addendum = addendum * taper_factor
            local_dedendum = dedendum * taper_factor

            # Calculate local tip and root radii
            local_tip_radius = pitch_radius + local_addendum
            local_root_radius = pitch_radius - local_dedendum

            # IMPORTANT: Ensure thread root never goes above core radius
            # The core is constant at root_radius, but tapered thread root approaches pitch_radius
            # Clamp the thread root to stay at or below the core radius
            local_root_radius = min(local_root_radius, root_radius)

            # Profile coordinates relative to pitch radius
            inner_r = local_root_radius - pitch_radius
            outer_r = local_tip_radius - pitch_radius

            # Apply taper to thread width
            local_thread_half_width_root = thread_half_width_root * taper_factor
            local_thread_half_width_tip = thread_half_width_tip * taper_factor

            # Radial direction at this point
            angle = math.atan2(point.Y, point.X)
            radial_dir = Vector(math.cos(angle), math.sin(angle), 0)

            # Profile plane perpendicular to helix tangent
            profile_plane = Plane(origin=point, x_dir=radial_dir, z_dir=tangent)

            with BuildSketch(profile_plane) as sk:
                with BuildLine():
                    if self.profile == "ZA":
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

                    elif self.profile == "ZK":
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

                    elif self.profile == "ZI":
                        # ZI profile: Involute helicoid per DIN 3975 Type I
                        # In axial section, appears as straight flanks (generatrix of involute helicoid)
                        # The involute shape is in normal section (perpendicular to thread)
                        # Manufactured by hobbing

                        # Note: For worm gears in axial section, ZI looks identical to ZA
                        # The difference is in the normal section where true involute exists
                        # Since we're modeling in axial section for build123d, use straight flanks

                        root_left = (inner_r, -local_thread_half_width_root)
                        root_right = (inner_r, local_thread_half_width_root)
                        tip_left = (outer_r, -local_thread_half_width_tip)
                        tip_right = (outer_r, local_thread_half_width_tip)

                        Line(root_left, tip_left)      # Left flank (straight generatrix)
                        Line(tip_left, tip_right)      # Tip
                        Line(tip_right, root_right)    # Right flank (straight generatrix)
                        Line(root_right, root_left)    # Root (closes)

                    else:
                        raise ValueError(f"Unknown profile type: {self.profile}")
                make_face()

            sections.append(sk.sketch.faces()[0])

        # Loft with ruled=True for consistent geometry
        print(f"      Lofting {len(sections)} sections...")
        thread = loft(sections, ruled=True)
        print(f"      ✓ Thread lofted successfully")

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

        print(f"    Exporting worm: volume={worm.volume:.2f} mm³")
        if hasattr(worm, 'export_step'):
            worm.export_step(filepath)
        else:
            from build123d import export_step as exp_step
            exp_step(worm, filepath)

        print(f"Exported worm to {filepath}")
