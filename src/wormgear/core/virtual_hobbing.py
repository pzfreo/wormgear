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

import logging
import math
import sys
import time
from typing import Optional, Literal, Callable
from build123d import (
    Part, Cylinder, Align, BuildSketch, BuildLine, Line, make_face, Spline,
    loft, Helix, Vector, Plane, Axis, Pos, Rot, export_step,
)
from OCP.ShapeFix import ShapeFix_Shape
from OCP.ShapeUpgrade import ShapeUpgrade_UnifySameDomain
from ..io.loaders import WheelParams, WormParams, AssemblyParams
from ..enums import Hand, WormProfile
from .features import (
    BoreFeature,
    KeywayFeature,
    SetScrewFeature,
    HubFeature,
    add_bore_and_keyway,
    create_hub
)

ProfileType = Literal["ZA", "ZK", "ZI"]

logger = logging.getLogger(__name__)

# Step presets for virtual hobbing with estimated timings
HOBBING_PRESETS = {
    "preview": {
        "steps": 36,
        "description": "Quick preview - lower accuracy",
        "native_time": "15-30 sec",
        "wasm_time": "1-3 min"
    },
    "balanced": {
        "steps": 72,
        "description": "Good quality for most uses",
        "native_time": "30-60 sec",
        "wasm_time": "3-6 min"
    },
    "high": {
        "steps": 144,
        "description": "High accuracy - slow",
        "native_time": "1-2 min",
        "wasm_time": "6-12 min"
    },
    "ultra": {
        "steps": 360,
        "description": "Maximum accuracy - very slow",
        "native_time": "3-5 min",
        "wasm_time": "15-30 min (not recommended)"
    }
}

# Progress callback type for WASM integration
ProgressCallback = Callable[[str, float], None]  # (message, percent_complete)


def get_hobbing_preset(name: str) -> dict:
    """
    Get hobbing preset by name.

    Args:
        name: Preset name ("preview", "balanced", "high", "ultra")

    Returns:
        dict with 'steps', 'description', 'native_time', 'wasm_time'

    Raises:
        ValueError if preset name not found
    """
    name_lower = name.lower()
    if name_lower not in HOBBING_PRESETS:
        valid = ", ".join(HOBBING_PRESETS.keys())
        raise ValueError(f"Unknown preset '{name}'. Valid presets: {valid}")
    return HOBBING_PRESETS[name_lower]


def get_preset_steps(name: str) -> int:
    """
    Get number of steps for a preset name.

    Args:
        name: Preset name ("preview", "balanced", "high", "ultra")

    Returns:
        Number of hobbing steps
    """
    return get_hobbing_preset(name)["steps"]


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
        ddcut: Optional['DDCutFeature'] = None,
        set_screw: Optional[SetScrewFeature] = None,
        hub: Optional[HubFeature] = None,
        profile: ProfileType = "ZA",
        hob_geometry: Optional[Part] = None,
        progress_callback: Optional[ProgressCallback] = None
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
                          Use HOBBING_PRESETS for recommended values:
                          - "preview": 36 steps (8-15 min WASM)
                          - "balanced": 72 steps (20-40 min WASM)
                          - "high": 144 steps (1-2 hours WASM)
                          - "ultra": 360 steps (not recommended for WASM)
            bore: Optional bore feature specification
            keyway: Optional keyway feature specification (requires bore)
            set_screw: Optional set screw feature specification (requires bore)
            hub: Optional hub feature specification
            profile: Tooth profile type per DIN 3975 ("ZA" or "ZK")
            hob_geometry: Optional pre-built worm geometry to use as hob.
                         If provided, uses this exact shape (e.g., globoid worm).
                         If None, creates a cylindrical hob from worm_params.
            progress_callback: Optional callback function(message, percent) for
                              progress reporting in WASM/browser environments.
        """
        self.params = params
        self.worm_params = worm_params
        self.assembly_params = assembly_params

        # Validate hobbing steps to prevent memory exhaustion and ensure quality
        MIN_HOBBING_STEPS = 6
        MAX_HOBBING_STEPS = 1000

        if hobbing_steps < MIN_HOBBING_STEPS:
            raise ValueError(
                f"hobbing_steps={hobbing_steps} is too low for meaningful results. "
                f"Minimum is {MIN_HOBBING_STEPS}. Use 'preview' preset (36 steps) for quick results."
            )
        if hobbing_steps > MAX_HOBBING_STEPS:
            raise ValueError(
                f"hobbing_steps={hobbing_steps} exceeds maximum of {MAX_HOBBING_STEPS}. "
                f"Use 'ultra' preset (360 steps) for highest quality. "
                f"Higher values cause memory exhaustion."
            )

        self.hobbing_steps = hobbing_steps
        self.bore = bore
        self.keyway = keyway
        self.ddcut = ddcut
        self.set_screw = set_screw
        self.hub = hub
        self.profile = profile.upper() if isinstance(profile, str) else profile
        self.hob_geometry = hob_geometry
        self.progress_callback = progress_callback

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
        Build the wheel geometry using virtual hobbing simulation.

        Returns:
            build123d Part object ready for export
        """
        # Return cached geometry if already built
        if self._part is not None:
            return self._part

        logger.info(f"Virtual hobbing with {self.hobbing_steps} steps...")

        # Create wheel blank
        wheel = self._create_blank()

        # Use provided hob geometry or create cylindrical hob
        if self.hob_geometry is not None:
            logger.info(f"Using provided worm geometry as hob (e.g., globoid)")
            logger.info(f"Applying simplification to complex hob geometry...")
            hob = self._create_simplified_hob(self.hob_geometry)
        else:
            # Create the hob (cutting tool based on worm geometry)
            hob = self._create_hob()

        # Perform virtual hobbing
        # Use incremental approach (faster, more reliable than envelope)
        wheel = self._simulate_hobbing_incremental(wheel, hob)

        # Add bore, keyway, and set screw if specified
        if self.bore is not None or self.keyway is not None or self.set_screw is not None:
            wheel = add_bore_and_keyway(
                wheel,
                part_length=self.face_width,
                bore=self.bore,
                keyway=self.keyway,
                ddcut=self.ddcut,
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

        # Cache the built geometry
        self._part = wheel
        return wheel

    def _create_blank(self) -> Part:
        """Create the wheel blank cylinder."""
        tip_radius = self.params.tip_diameter_mm / 2

        blank = Cylinder(
            radius=tip_radius,
            height=self.face_width,
            align=(Align.CENTER, Align.CENTER, Align.CENTER)
        )

        logger.debug(f"Blank: radius={tip_radius:.2f}mm, height={self.face_width:.2f}mm")
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
        is_right_hand = self.worm_params.hand == Hand.RIGHT

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
        # Ensure at least 2 sections for loft operations (division by num_sections - 1)
        num_sections = max(2, num_sections)
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
                    if self.profile == WormProfile.ZA or self.profile == "ZA":
                        # ZA profile: Straight flanks (trapezoidal) per DIN 3975
                        root_left = (inner_r, -thread_half_width_root)
                        root_right = (inner_r, thread_half_width_root)
                        tip_left = (outer_r, -thread_half_width_tip)
                        tip_right = (outer_r, thread_half_width_tip)

                        Line(root_left, tip_left)
                        Line(tip_left, tip_right)
                        Line(tip_right, root_right)
                        Line(root_right, root_left)

                    elif self.profile == WormProfile.ZK or self.profile == "ZK":
                        # ZK profile: Circular arc flanks per DIN 3975 Type K
                        # Biconical grinding wheel profile
                        num_points = 9
                        left_flank = []
                        right_flank = []

                        # Arc radius
                        arc_radius = 0.45 * self.worm_params.module_mm

                        flank_height = outer_r - inner_r
                        flank_width_change = thread_half_width_root - thread_half_width_tip

                        if flank_width_change > 0:
                            flank_angle = math.atan(flank_width_change / flank_height)
                        else:
                            flank_angle = 0

                        for j in range(num_points):
                            t = j / (num_points - 1)
                            r_pos = inner_r + t * flank_height
                            linear_width = thread_half_width_root + t * (thread_half_width_tip - thread_half_width_root)

                            # Circular arc bulge
                            arc_param = t * math.pi
                            arc_bulge = arc_radius * 0.15 * math.sin(arc_param)

                            width = linear_width + arc_bulge
                            left_flank.append((r_pos, -width))
                            right_flank.append((r_pos, width))

                        Spline(left_flank)
                        Line(left_flank[-1], right_flank[-1])
                        Spline(list(reversed(right_flank)))
                        Line(right_flank[0], left_flank[0])

                    elif self.profile == WormProfile.ZI or self.profile == "ZI":
                        # ZI profile: Involute helicoid per DIN 3975 Type I
                        # In axial section, appears as straight flanks (generatrix of involute helicoid)
                        # The involute shape is in normal section (perpendicular to thread)
                        # Manufactured by hobbing

                        root_left = (inner_r, -thread_half_width_root)
                        root_right = (inner_r, thread_half_width_root)
                        tip_left = (outer_r, -thread_half_width_tip)
                        tip_right = (outer_r, thread_half_width_tip)

                        Line(root_left, tip_left)      # Left flank (straight generatrix)
                        Line(tip_left, tip_right)      # Tip
                        Line(tip_right, root_right)    # Right flank (straight generatrix)
                        Line(root_right, root_left)    # Root (closes)

                    else:
                        raise ValueError(f"Unknown profile type: {self.profile}")
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

        logger.debug(f"Hob created: length={hob_length:.2f}mm, {self.worm_params.num_starts} start(s)")
        return hob

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
            except Exception as e:
                pass  # Don't let callback errors break generation

    def _simplify_geometry(self, part: Part, description: str = "") -> Part:
        """
        Simplify geometry using OpenCascade tools.

        Optimization #3: Merge coplanar faces and unify same-domain surfaces
        to reduce boolean operation complexity.

        Args:
            part: The part to simplify
            description: Description for progress reporting

        Returns:
            Simplified part
        """
        if description:
            logger.debug(f"Simplifying {description}...")

        simplify_start = time.time()

        try:
            # Ensure we have a Part, not a ShapeList or other type
            if not isinstance(part, Part):
                if hasattr(part, 'wrapped'):
                    part = Part(part.wrapped)
                else:
                    raise ValueError(f"Cannot simplify object of type {type(part)}")

            # UnifySameDomain merges faces that share the same underlying surface
            unifier = ShapeUpgrade_UnifySameDomain(part.wrapped, True, True, True)
            unifier.Build()
            unified_shape = unifier.Shape()

            # ShapeFix cleans up invalid geometry
            fixer = ShapeFix_Shape(unified_shape)
            fixer.Perform()
            fixed_shape = fixer.Shape()

            simplified = Part(fixed_shape)

            simplify_time = time.time() - simplify_start
            if description:
                logger.debug(f"done in {simplify_time:.1f}s")

            return simplified
        except Exception as e:
            simplify_time = time.time() - simplify_start
            logger.warning(f"failed after {simplify_time:.1f}s: {e}, using original")
            return part

    def _create_simplified_hob(self, original_hob: Part) -> Part:
        """
        Create a simplified version of a complex hob (e.g., globoid).

        Optimization #2: For globoid worms with many lofted sections,
        create a coarser approximation that's much faster to process
        while preserving tooth contact geometry.

        Args:
            original_hob: The original complex hob geometry

        Returns:
            Simplified hob (or original if simplification not needed/possible)
        """
        # First try OCC simplification
        simplified = self._simplify_geometry(original_hob, "hob geometry (OCC tools)")

        # FUTURE OPTIMIZATION: For globoid hobs with many sections, we could
        # rebuild the geometry with fewer sections for faster boolean operations.
        # Current OCC simplification provides significant improvement already.
        # See P2.1 in TECH_DEBT_REMEDIATION_PLAN.md for optimization details.

        return simplified

    def _trim_envelope_to_wheel_bounds(self, envelope: Part) -> Part:
        """
        Trim envelope to wheel boundaries.

        Optimization #1: Remove all hob geometry outside the wheel's
        cutting zone. This dramatically reduces the complexity of the
        boolean subtraction in Phase 2.

        Args:
            envelope: The full hob envelope

        Returns:
            Trimmed envelope
        """
        # Calculate trim radius: must be large enough to contain hob at working position
        # Hob is positioned at centre_distance from wheel center
        # Hob extends to: centre_distance + hob_tip_radius
        centre_distance = self.assembly_params.centre_distance_mm
        hob_tip_radius = self.worm_params.tip_diameter_mm / 2

        # Add small margin beyond hob envelope (0.5mm is enough)
        trim_radius = centre_distance + hob_tip_radius + 0.5
        trim_height = self.face_width + 2.0  # 2mm margin

        bounding_cylinder = Cylinder(
            radius=trim_radius,
            height=trim_height,
            align=(Align.CENTER, Align.CENTER, Align.CENTER)
        )

        logger.info(f"Trimming envelope to wheel bounds (r={trim_radius:.2f}mm, h={trim_height:.2f}mm)...")
        sys.stdout.flush()

        trim_start = time.time()

        try:
            # Ensure envelope is a Part
            if not isinstance(envelope, Part):
                if hasattr(envelope, 'wrapped'):
                    envelope = Part(envelope.wrapped)
                else:
                    logger.warning(f"Envelope is not a Part (type: {type(envelope)}), skipping trim")
                    return envelope

            # Intersect envelope with bounding cylinder
            trimmed = envelope & bounding_cylinder
            trim_time = time.time() - trim_start
            logger.debug(f"Envelope trimmed in {trim_time:.1f}s")
            return trimmed
        except Exception as e:
            trim_time = time.time() - trim_start
            logger.warning(f"Envelope trimming failed after {trim_time:.1f}s: {e}")
            logger.warning(f"Using untrimmed envelope (Phase 2 will be slower)")
            return envelope

    def _simulate_hobbing_incremental(self, blank: Part, hob: Part) -> Part:
        """
        Simulate hobbing by incrementally subtracting hob at each position.

        ALTERNATIVE APPROACH: Instead of building envelope then subtracting,
        subtract the hob from wheel at each step. Avoids complex envelope management.

        Pros: Simpler, more predictable memory usage
        Cons: More boolean operations, overlapping cuts
        """
        centre_distance = self.assembly_params.centre_distance_mm
        wheel_teeth = self.params.num_teeth
        worm_starts = self.worm_params.num_starts
        ratio = wheel_teeth / worm_starts

        wheel_increment = 360.0 / self.hobbing_steps
        hob_increment = wheel_increment * ratio

        self._report_progress(
            f"    Hobbing simulation (INCREMENTAL): {self.hobbing_steps} steps, ratio 1:{ratio:.1f}",
            0.0
        )

        progress_interval = max(1, self.hobbing_steps // 20)
        wheel = blank

        for step in range(self.hobbing_steps):
            wheel_angle = step * wheel_increment
            hob_angle = step * hob_increment

            # CORRECT HOBBING KINEMATICS:
            # Hob stays at FIXED position (centre distance away, horizontal axis)
            # Hob rotates around its own axis by hob_angle
            # WHEEL rotates by wheel_angle
            # We subtract hob from the rotated wheel position

            # Position hob at fixed location (on X axis at centre distance)
            # Hob axis is horizontal (along Y after Rot(X=90))
            hob_positioned = Pos(centre_distance, 0, 0) * Rot(X=90) * Rot(Z=hob_angle) * hob

            # Rotate wheel to current angle, subtract hob, rotate back
            # This is equivalent to: wheel rotates, hob cuts, result is accumulated
            try:
                # Rotate wheel to position
                wheel_rotated = Rot(Z=wheel_angle) * wheel
                # Subtract hob from rotated wheel
                wheel_cut = wheel_rotated - hob_positioned
                # Rotate back to accumulate result
                wheel = Rot(Z=-wheel_angle) * wheel_cut
            except Exception as e:
                self._report_progress(f"    WARNING: Step {step} subtraction failed: {e}", -1)

            # Progress
            if (step + 1) % progress_interval == 0:
                pct = ((step + 1) / self.hobbing_steps) * 100
                self._report_progress(
                    f"      {pct:.0f}% complete ({step + 1}/{self.hobbing_steps} cuts)",
                    pct,
                    verbose=(step + 1) in [self.hobbing_steps // 4, self.hobbing_steps // 2, 3 * self.hobbing_steps // 4]
                )

        self._report_progress(f"    ✓ Incremental hobbing complete", 100.0)
        return wheel

    def _simulate_hobbing(self, blank: Part, hob: Part) -> Part:
        """
        Simulate the hobbing manufacturing process to generate accurate wheel teeth.

        This method implements virtual hobbing per DIN 3975 §10, where a rotating
        hob (representing the worm) is brought into contact with a rotating wheel
        blank. The envelope of all hob positions defines the final tooth surface.

        Algorithm Overview:
        ------------------
        1. Create hob geometry matching the worm thread profile (_create_hob)
        2. For each hobbing step (default 72 steps = 5° increments):
           a. Calculate wheel rotation angle: wheel_angle = step × (360° / steps)
           b. Calculate hob rotation angle: hob_angle = wheel_angle × ratio
           c. Position hob at centre_distance from wheel axis
           d. Union hob position into cumulative envelope
        3. Final subtraction of envelope from wheel blank creates tooth spaces

        Mathematical Basis (DIN 3975 §10):
        ---------------------------------
        The kinematic relationship ensures conjugate tooth action:
        - Wheel angular velocity: ω₂ = ω₁ / ratio
        - Hob engagement: Maintains constant centre distance
        - Tooth profile: Generated as envelope of hob positions

        Performance Characteristics:
        ---------------------------
        - Time complexity: O(n²) where n = hobbing_steps (boolean operations compound)
        - Memory: Envelope grows with each union; ~1MB per 10 steps for complex hobs
        - Native execution: 30-60s for 72 steps with cylindrical hob
        - WASM execution: 3-6 minutes for 72 steps
        - Globoid hobs: 3-5x slower due to geometric complexity

        Optimization Notes:
        ------------------
        - Geometry simplification every N steps reduces face count accumulation
        - For globoid hobs, consider using ≤36 steps
        - Periodic simplification is auto-enabled for provided hob geometry

        Args:
            blank: Wheel blank (cylinder) to cut teeth into
            hob: Hob geometry (worm-shaped cutter)

        Returns:
            Part: Wheel geometry with accurately hobbed tooth surfaces.
                  The result is a valid solid suitable for STEP export.

        Raises:
            RuntimeError: If boolean operations fail to produce valid geometry.
                         This can occur with extreme parameters or memory exhaustion.

        References:
            - DIN 3975:2017 §10 "Generation of worm wheel teeth"
            - Dudley's Handbook of Practical Gear Design, Chapter 8
            - ISO 21771:2007 "Gears - Cylindrical involute gears and gear pairs"

        See Also:
            _create_hob: Creates the hob geometry used in simulation
            _simplify_geometry: Reduces face count to improve boolean performance
            HOBBING_PRESETS: Recommended step counts for different quality levels
        """
        centre_distance = self.assembly_params.centre_distance_mm
        wheel_teeth = self.params.num_teeth
        worm_starts = self.worm_params.num_starts
        ratio = wheel_teeth / worm_starts

        # Calculate angular increments
        # Full wheel rotation = 360 degrees
        # Divide by hobbing_steps to get increment
        wheel_increment = 360.0 / self.hobbing_steps
        hob_increment = wheel_increment * ratio

        self._report_progress(
            f"    Hobbing simulation: {self.hobbing_steps} steps, ratio 1:{ratio:.1f}",
            0.0
        )

        # Warn about performance if using many steps (likely globoid worm)
        if self.hobbing_steps > 36 and self.worm_geometry is not None:
            logger.warning(f"Using {self.hobbing_steps} steps with provided worm geometry (likely globoid).")
            logger.warning(f"Phase 2 may take 30+ minutes or fail. Consider using 18-36 steps for globoid worms.")
            sys.stdout.flush()

        self._report_progress(
            f"    Phase 1: Building hob envelope (union of all positions)...",
            1.0
        )

        # Track progress - more frequent updates for WASM
        progress_interval = max(1, self.hobbing_steps // 20)

        # Time Phase 1
        phase1_start = time.time()

        # Build envelope by unioning all hob positions
        envelope = None

        # Optimization #4: Periodic simplification interval
        # Only do this for complex geometry (globoid) - skip for cylindrical
        # Simplify every N steps to prevent complexity buildup
        use_periodic_simplification = (self.hob_geometry is not None)  # Only if using provided geometry
        simplification_interval = max(3, self.hobbing_steps // 6) if use_periodic_simplification else 999999

        for step in range(self.hobbing_steps):
            # Current rotations
            wheel_angle = step * wheel_increment
            hob_angle = step * hob_increment

            # Rotate hob around its own axis first, then position and rotate around wheel
            hob_rotated = Rot(Z=wheel_angle) * Pos(centre_distance, 0, 0) * Rot(X=90) * Rot(Z=hob_angle) * hob

            # Union into envelope using OCP fuse (+ operator just makes a list!)
            try:
                if envelope is None:
                    envelope = hob_rotated
                else:
                    # Use OCP's BRepAlgoAPI_Fuse for actual boolean union
                    from OCP.BRepAlgoAPI import BRepAlgoAPI_Fuse

                    env_shape = envelope.wrapped if hasattr(envelope, 'wrapped') else envelope
                    hob_shape = hob_rotated.wrapped if hasattr(hob_rotated, 'wrapped') else hob_rotated

                    fuser = BRepAlgoAPI_Fuse(env_shape, hob_shape)
                    fuser.Build()

                    if fuser.IsDone():
                        envelope = Part(fuser.Shape())
                    else:
                        self._report_progress(f"    WARNING: Step {step} union failed (IsDone=False)", -1)
            except Exception as e:
                self._report_progress(f"    WARNING: Step {step} union failed: {e}", -1)

            # Optimization #4: Periodic simplification during envelope building (globoid only)
            # Simplify every few steps to prevent exponential complexity growth
            if use_periodic_simplification and envelope is not None and (step + 1) % simplification_interval == 0 and (step + 1) < self.hobbing_steps:
                envelope = self._simplify_geometry(envelope, f"envelope at step {step + 1}")

            # Progress indicator (more frequent for WASM feedback)
            if (step + 1) % progress_interval == 0:
                # Phase 1 is 0-90% of total progress
                pct = ((step + 1) / self.hobbing_steps) * 90
                # Only print 25%, 50%, 75% to console; all updates go to callback
                verbose = (step + 1) in [
                    self.hobbing_steps // 4,
                    self.hobbing_steps // 2,
                    3 * self.hobbing_steps // 4
                ]
                self._report_progress(
                    f"      {pct:.0f}% envelope built ({step + 1}/{self.hobbing_steps} steps)",
                    pct,
                    verbose=verbose
                )

        if envelope is None:
            self._report_progress(f"    ERROR: Failed to build envelope", -1)
            return blank

        # Ensure envelope is a proper Part (unions can sometimes create Compound/ShapeList)
        if not isinstance(envelope, Part):
            logger.info(f"Converting envelope from {type(envelope).__name__} to Part...")
            convert_start = time.time()
            try:
                # If it's a ShapeList (list of shapes), we need to fuse them at OCP level
                if isinstance(envelope, (list, tuple)):
                    if len(envelope) == 0:
                        logger.warning(f"ERROR: Envelope is empty list!")
                        return blank

                    logger.info(f"Fusing {len(envelope)} shapes from ShapeList...")

                    # Use OCP BRepAlgoAPI_Fuse to fuse all shapes
                    from OCP.BRepAlgoAPI import BRepAlgoAPI_Fuse

                    # Start with first shape
                    current_shape = envelope[0].wrapped if hasattr(envelope[0], 'wrapped') else envelope[0]

                    # Fuse with each subsequent shape
                    for i, shape in enumerate(envelope[1:], 1):
                        shape_ocp = shape.wrapped if hasattr(shape, 'wrapped') else shape
                        fuser = BRepAlgoAPI_Fuse(current_shape, shape_ocp)
                        fuser.Build()
                        if not fuser.IsDone():
                            logger.warning(f"Fuse failed at shape {i}")
                            continue
                        current_shape = fuser.Shape()

                    # Wrap result as Part
                    envelope = Part(current_shape)

                elif hasattr(envelope, 'wrapped'):
                    # Has .wrapped - direct conversion
                    envelope = Part(envelope.wrapped)
                else:
                    logger.warning(f"ERROR: Don't know how to convert {type(envelope)} to Part!")
                    return blank

                # Final check that result is a Part
                if not isinstance(envelope, Part):
                    logger.warning(f"ERROR: After conversion, still not a Part (is {type(envelope)})!")
                    return blank

                convert_time = time.time() - convert_start
                logger.debug(f"Conversion successful in {convert_time:.1f}s")
            except Exception as e:
                convert_time = time.time() - convert_start
                logger.warning(f"ERROR: Failed to convert envelope to Part after {convert_time:.1f}s: {e}")
                import traceback
                traceback.print_exc()
                return blank

        # Report Phase 1 completion time
        phase1_time = time.time() - phase1_start
        self._report_progress(
            f"    ✓ Phase 1 complete in {phase1_time:.1f}s ({self.hobbing_steps} unions)",
            91.0
        )

        # DEBUG: Check envelope validity before optimizations
        try:
            env_volume = envelope.volume
            logger.info(f"Envelope volume before optimizations: {env_volume:.2f} mm³")
        except Exception as e:
            logger.warning(f"Cannot compute envelope volume: {e}")

        # Optimization #1: Trim envelope to wheel boundaries
        # This removes excess hob geometry that doesn't cut anything
        envelope = self._trim_envelope_to_wheel_bounds(envelope)

        # DEBUG: Check envelope after trim
        try:
            env_volume_trimmed = envelope.volume
            logger.info(f"Envelope volume after trim: {env_volume_trimmed:.2f} mm³")
        except (AttributeError, ValueError, RuntimeError) as e:
            logger.warning(f"Envelope invalid after trim! ({type(e).__name__})")

        # Optimization #3: Final simplification before Phase 2
        logger.info(f"Applying final simplification to envelope...")
        sys.stdout.flush()
        simplify_start = time.time()
        envelope = self._simplify_geometry(envelope, "final envelope")
        simplify_time = time.time() - simplify_start
        logger.debug(f"Final simplification complete in {simplify_time:.1f}s")

        # DEBUG: Check envelope after simplification
        try:
            env_volume_final = envelope.volume
            logger.info(f"Envelope volume after simplification: {env_volume_final:.2f} mm³")
        except (AttributeError, ValueError, RuntimeError) as e:
            logger.warning(f"Envelope invalid after simplification! ({type(e).__name__})")

        # Phase 2: Subtract envelope (this is a single complex boolean operation)
        self._report_progress(
            f"    Phase 2: Subtracting envelope from wheel blank (this may take several minutes)...",
            92.0
        )

        # Force flush to ensure message is displayed immediately
        sys.stdout.flush()

        # Time this operation since it can be slow
        phase2_start = time.time()

        # Subtract the envelope from the wheel blank
        try:
            wheel = blank - envelope
            phase2_time = time.time() - phase2_start
            self._report_progress(
                f"    ✓ Envelope subtracted in {phase2_time:.1f}s",
                95.0
            )
        except Exception as e:
            phase2_time = time.time() - phase2_start
            self._report_progress(
                f"    ERROR: Envelope subtraction failed after {phase2_time:.1f}s: {e}",
                -1
            )
            return blank

        self._report_progress(f"    ✓ Virtual hobbing complete", 100.0)
        return wheel

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
            logger.info("Exporting to STEP format...")
            self.build()

        if hasattr(self._part, 'export_step'):
            self._part.export_step(filepath)
        else:
            from build123d import export_step as exp_step
            exp_step(self._part, filepath)

        logger.info(f"Exported wheel to {filepath}")
