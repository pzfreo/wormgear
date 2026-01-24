"""
Worm geometry generation using build123d.

Creates CNC-ready worm geometry with helical threads.
"""

import math
from typing import Optional, Literal
from build123d import *
from .io import WormParams, AssemblyParams
from .features import BoreFeature, KeywayFeature, SetScrewFeature, add_bore_and_keyway

# Profile types per DIN 3975
# ZA: Straight flanks in axial section (Archimedean) - best for CNC machining
# ZK: Slightly convex flanks - better for 3D printing (reduces stress concentrations)
ProfileType = Literal["ZA", "ZK"]


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
            keyway: Optional keyway feature specification (requires bore)
            set_screw: Optional set screw feature specification (requires bore)
            profile: Tooth profile type per DIN 3975:
                     "ZA" - Straight flanks (trapezoidal) - best for CNC (default)
                     "ZK" - Slightly convex flanks - better for 3D printing
        """
        self.params = params
        self.assembly_params = assembly_params
        self.length = length
        self.sections_per_turn = sections_per_turn
        self.bore = bore
        self.keyway = keyway
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
            worm = core + threads
            print(f"    ✓ Union complete")
        else:
            print(f"    No threads to union - using core only")
            worm = core

        # Trim to exact length - removes fragile tapered thread ends
        print(f"    Trimming to final length ({self.length:.2f}mm)...")
        try:
            pre_trim_volume = worm.volume
            print(f"    Pre-trim volume: {pre_trim_volume:.2f} mm³")
        except:
            print(f"    Pre-trim volume: unable to calculate")

        # Trim box needs to be large enough in XY to contain the worm diameter
        # but exact in Z (height) to trim to the desired length
        trim_diameter = tip_radius * 4  # Plenty of margin
        trim_box = Box(
            length=trim_diameter,  # Large enough in XY
            width=trim_diameter,
            height=self.length,    # Exact length in Z
            align=(Align.CENTER, Align.CENTER, Align.CENTER)
        )
        print(f"    Trim box: {trim_diameter:.2f} x {trim_diameter:.2f} x {self.length:.2f} mm")

        worm = worm & trim_box

        try:
            post_trim_volume = worm.volume
            print(f"    Post-trim volume: {post_trim_volume:.2f} mm³")
        except:
            print(f"    Post-trim volume: unable to calculate")

        print(f"    ✓ Worm trimmed to length")

        # Ensure we have a single Solid for proper display in ocp_vscode
        if hasattr(worm, 'solids'):
            solids = list(worm.solids())
            if len(solids) == 1:
                worm = solids[0]
            elif len(solids) > 1:
                # Return the largest solid (should be the worm)
                worm = max(solids, key=lambda s: s.volume)

        # Add bore, keyway, and set screw if specified
        if self.bore is not None or self.keyway is not None or self.set_screw is not None:
            worm = add_bore_and_keyway(
                worm,
                part_length=self.length,
                bore=self.bore,
                keyway=self.keyway,
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
                    else:
                        # ZK profile: Slightly convex flanks per DIN 3975
                        # Better for 3D printing - reduces stress concentrations
                        num_flank_points = 5
                        left_flank = []
                        right_flank = []

                        for j in range(num_flank_points):
                            # Parameter along the flank (0 = root, 1 = tip)
                            t_flank = j / (num_flank_points - 1)
                            r_pos = inner_r + t_flank * (outer_r - inner_r)

                            # Interpolate width with slight convex curve
                            linear_width = local_thread_half_width_root + t_flank * (local_thread_half_width_tip - local_thread_half_width_root)
                            # Add subtle convex bulge - max at middle of flank
                            curve_factor = 4 * t_flank * (1 - t_flank)  # Parabolic, peaks at 0.5
                            bulge = curve_factor * 0.05 * (local_thread_half_width_root - local_thread_half_width_tip)
                            width = linear_width + bulge

                            left_flank.append((r_pos, -width))
                            right_flank.append((r_pos, width))

                        # Build profile with curved flanks
                        Spline(left_flank)
                        Line(left_flank[-1], right_flank[-1])  # Tip
                        Spline(list(reversed(right_flank)))
                        Line(right_flank[0], left_flank[0])    # Root (closes)
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
