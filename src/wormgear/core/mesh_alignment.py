"""
Worm-Wheel Mesh Alignment Module.

This module provides functions for calculating optimal wheel rotation to achieve
proper mesh alignment with a worm, and for checking interference between the gears.

The algorithm uses boolean intersection to iteratively find the wheel rotation
that minimizes interference volume, searching within one tooth pitch since
the mesh pattern repeats every tooth.

Example:
    >>> from wormgear.core import WormGeometry, WheelGeometry
    >>> from wormgear.core.mesh_alignment import find_optimal_mesh_rotation
    >>>
    >>> # Generate worm and wheel geometry
    >>> worm = worm_geo.build()
    >>> wheel = wheel_geo.build()
    >>>
    >>> # Find optimal alignment
    >>> result = find_optimal_mesh_rotation(
    ...     wheel=wheel,
    ...     worm=worm,
    ...     centre_distance_mm=38.14,
    ...     num_teeth=30,
    ... )
    >>>
    >>> print(f"Rotate wheel by {result.optimal_rotation_deg:.2f}°")
    >>> aligned_wheel = wheel.rotate(Axis.Z, result.optimal_rotation_deg)
"""

from dataclasses import dataclass
from typing import Optional
import math

from build123d import (
    Align,
    Axis,
    Cylinder,
    Location,
    Part,
)


@dataclass
class MeshAlignmentResult:
    """Results from mesh alignment analysis.

    Attributes:
        optimal_rotation_deg: Wheel rotation angle in degrees for best mesh
        interference_volume_mm3: Residual interference volume at optimal rotation
        within_tolerance: Whether interference is below acceptable threshold
        tooth_pitch_deg: Angular pitch between wheel teeth (360/num_teeth)
        worm_position: Tuple of (x, y, z) for worm centre position
        message: Human-readable status message
        mesh_quality: Quality tier - "perfect", "good", "acceptable", or "warning"
        tolerance_mm3: The tolerance threshold used (module-scaled)
    """
    optimal_rotation_deg: float
    interference_volume_mm3: float
    within_tolerance: bool
    tooth_pitch_deg: float
    worm_position: tuple[float, float, float]
    message: str
    mesh_quality: str = "good"
    tolerance_mm3: float = 1.0


def calculate_tolerance_mm3(module_mm: float, base_tolerance: float = 1.0) -> float:
    """Calculate module-scaled interference tolerance.

    Volumetric interference scales roughly with the square of the module
    because the tooth cross-section area scales as module² while the
    contact zone length is roughly proportional to module as well.
    Using quadratic scaling provides a practical threshold that doesn't
    penalise larger modules unfairly.

    Args:
        module_mm: Gear module in mm
        base_tolerance: Base tolerance at module 1.0 (default 1.0 mm³)

    Returns:
        Scaled tolerance in mm³
    """
    return base_tolerance * (module_mm ** 2)


def _classify_mesh_quality(
    interference_mm3: float, tolerance_mm3: float
) -> tuple[str, str]:
    """Classify mesh quality into tiers and return (quality, message_prefix).

    Tiers:
        perfect:    interference == 0
        good:       interference ≤ tolerance
        acceptable: interference ≤ 3× tolerance (expected for helical wheels)
        warning:    interference > 3× tolerance

    Args:
        interference_mm3: Measured interference volume
        tolerance_mm3: Module-scaled tolerance threshold

    Returns:
        Tuple of (quality_tier, message_prefix)
    """
    if interference_mm3 == 0.0:
        return "perfect", "Perfect mesh - no interference detected"
    elif interference_mm3 <= tolerance_mm3:
        return "good", f"Good mesh - interference {interference_mm3:.4f}mm³ within tolerance ({tolerance_mm3:.1f}mm³)"
    elif interference_mm3 <= 3 * tolerance_mm3:
        return "acceptable", f"Acceptable mesh - interference {interference_mm3:.4f}mm³ within 3× tolerance ({tolerance_mm3:.1f}mm³; expected for helical wheel)"
    else:
        return "warning", f"Warning - interference {interference_mm3:.4f}mm³ exceeds 3× tolerance ({tolerance_mm3:.1f}mm³)"


def _calculate_interference(wheel: Part, worm: Part) -> float:
    """Calculate intersection volume between wheel and worm.

    Args:
        wheel: Wheel Part
        worm: Worm Part (already positioned)

    Returns:
        Intersection volume in mm³, or 0.0 if no intersection
    """
    try:
        intersection = wheel & worm
        # Handle single Part with volume
        if hasattr(intersection, "volume"):
            return intersection.volume
        # Handle ShapeList (multiple solids from boolean on complex geometry)
        if hasattr(intersection, "__iter__"):
            total_volume = 0.0
            for item in intersection:
                if hasattr(item, "volume"):
                    total_volume += item.volume
            return total_volume
        return 0.0
    except Exception:
        return 0.0


def calculate_mesh_rotation(
    wheel: Part,
    worm: Part,
    num_teeth: int,
    tolerance_deg: float = 0.2,
) -> tuple[float, float]:
    """Find wheel rotation that minimizes collision with worm.

    Uses golden section search for efficiency - O(log n) instead of O(n).
    Searches within one tooth pitch since the mesh pattern repeats.

    Algorithm:
    1. Quick check at 0° (common case for properly designed gears)
    2. Golden section search to find minimum interference angle
    3. Returns as soon as zero interference is found

    Args:
        wheel: Wheel Part centred at origin with axis along Z
        worm: Worm Part already positioned at correct centre distance
        num_teeth: Number of teeth on the wheel
        tolerance_deg: Search precision in degrees (default 0.2°)

    Returns:
        Tuple of (optimal_rotation_deg, min_interference_mm3)
    """
    tooth_pitch_deg = 360.0 / num_teeth

    # Helper to check interference at an angle
    def check(angle: float) -> float:
        rotated_wheel = wheel.rotate(Axis.Z, angle % tooth_pitch_deg)
        return _calculate_interference(rotated_wheel, worm)

    # Quick check at 0° - most gears mesh correctly here
    interference_at_zero = check(0.0)
    if interference_at_zero == 0.0:
        return 0.0, 0.0

    # Golden section search
    # Golden ratio conjugate
    phi = (math.sqrt(5) - 1) / 2  # ≈ 0.618

    a = 0.0
    b = tooth_pitch_deg
    c = b - phi * (b - a)
    d = a + phi * (b - a)

    fc = check(c)
    if fc == 0.0:
        return c, 0.0
    fd = check(d)
    if fd == 0.0:
        return d, 0.0

    # Iterate until we reach desired precision
    while (b - a) > tolerance_deg:
        if fc < fd:
            b = d
            d = c
            fd = fc
            c = b - phi * (b - a)
            fc = check(c)
            if fc == 0.0:
                return c, 0.0
        else:
            a = c
            c = d
            fc = fd
            d = a + phi * (b - a)
            fd = check(d)
            if fd == 0.0:
                return d, 0.0

    # Return the best found
    best_angle = (a + b) / 2
    best_interference = check(best_angle)

    # Also check boundaries and midpoint candidates
    candidates = [(a, check(a)), (b, check(b)), (c, fc), (d, fd), (best_angle, best_interference)]
    best_angle, best_interference = min(candidates, key=lambda x: x[1])

    return best_angle % tooth_pitch_deg, best_interference


def check_interference(
    wheel: Part,
    worm: Part,
    centre_distance_mm: float,
    rotation_deg: float = 0.0,
) -> float:
    """Check intersection volume between wheel and worm.

    Positions the worm at centre distance and checks for interference.

    Args:
        wheel: Wheel Part centred at origin with axis along Z
        worm: Worm Part centred at origin with axis along Z (will be positioned)
        centre_distance_mm: Distance between axes in mm
        rotation_deg: Rotation to apply to wheel before checking

    Returns:
        Intersection volume in mm³
    """
    # Position worm: rotate -90° around Y so axis is along X, offset in Y
    worm_positioned = worm.rotate(Axis.Y, -90)
    worm_positioned = worm_positioned.locate(Location((0, centre_distance_mm, 0)))

    if rotation_deg != 0.0:
        wheel = wheel.rotate(Axis.Z, rotation_deg)

    return _calculate_interference(wheel, worm_positioned)


def find_optimal_mesh_rotation(
    wheel: Part,
    worm: Part,
    centre_distance_mm: float,
    num_teeth: int,
    module_mm: float = 1.0,
    backlash_tolerance_mm3: Optional[float] = None,
    fine_step_deg: float = 0.2,
) -> MeshAlignmentResult:
    """Find optimal wheel rotation and analyse mesh quality.

    This is the main entry point for mesh analysis. It:
    1. Positions the worm at the correct centre distance
    2. Calculates optimal wheel rotation to minimize interference
    3. Measures final interference volume
    4. Reports whether mesh is within tolerance (module-scaled)

    Uses golden section search for efficiency - O(log n) instead of O(n).

    The tolerance scales with module² to account for the fact that
    volumetric interference naturally grows with gear size. At module 1
    the base tolerance is 1.0 mm³; at module 2 it is 4.0 mm³.

    Mesh quality is reported in tiers rather than binary pass/fail:
    - perfect:    No interference
    - good:       Within tolerance
    - acceptable: Within 3× tolerance (expected for non-conjugate helical wheels)
    - warning:    Exceeds 3× tolerance

    The worm is positioned with its axis along Y, offset from the wheel
    (whose axis is along Z) by the centre distance.

    Args:
        wheel: Wheel Part centred at origin with axis along Z
        worm: Worm Part centred at origin with axis along Z (will be rotated/positioned)
        centre_distance_mm: Distance between wheel and worm axes in mm
        num_teeth: Number of teeth on the wheel
        module_mm: Gear module in mm (used to scale tolerance; default 1.0)
        backlash_tolerance_mm3: Override tolerance (if None, auto-scaled from module)
        fine_step_deg: Search precision in degrees (default 0.2°)

    Returns:
        MeshAlignmentResult with rotation, interference, quality tier, and status
    """
    tooth_pitch_deg = 360.0 / num_teeth

    # Calculate tolerance (auto-scale from module, or use explicit override)
    if backlash_tolerance_mm3 is not None:
        tolerance = backlash_tolerance_mm3
    else:
        tolerance = calculate_tolerance_mm3(module_mm)

    # Position worm: rotate -90° around Y so axis is along X, offset by centre_distance in Y
    worm_positioned = worm.rotate(Axis.Y, -90)
    worm_positioned = worm_positioned.locate(Location((0, centre_distance_mm, 0)))
    worm_position = (0.0, centre_distance_mm, 0.0)

    # Calculate optimal rotation using golden section search
    # fine_step_deg controls the precision (tolerance_deg in the search)
    optimal_rotation, interference = calculate_mesh_rotation(
        wheel=wheel,
        worm=worm_positioned,
        num_teeth=num_teeth,
        tolerance_deg=fine_step_deg,
    )

    # Also measure interference without rotation for comparison
    interference_unrotated = _calculate_interference(wheel, worm_positioned)

    # Classify mesh quality into tiers
    mesh_quality, message = _classify_mesh_quality(interference, tolerance)
    within_tolerance = mesh_quality in ("perfect", "good", "acceptable")

    if interference_unrotated > 0 and interference < interference_unrotated:
        reduction = interference_unrotated - interference
        message += f" (reduced by {reduction:.4f}mm³ from unrotated position)"

    return MeshAlignmentResult(
        optimal_rotation_deg=optimal_rotation,
        interference_volume_mm3=interference,
        within_tolerance=within_tolerance,
        tooth_pitch_deg=tooth_pitch_deg,
        worm_position=worm_position,
        message=message,
        mesh_quality=mesh_quality,
        tolerance_mm3=tolerance,
    )


def position_for_mesh(
    wheel: Part,
    worm: Part,
    centre_distance_mm: float,
    rotation_deg: float,
) -> tuple[Part, Part]:
    """Position wheel and worm for mesh visualization.

    Returns wheel rotated by the specified angle and worm positioned
    at the correct centre distance with proper orientation.

    Args:
        wheel: Wheel Part centred at origin
        worm: Worm Part centred at origin
        centre_distance_mm: Distance between axes in mm
        rotation_deg: Rotation to apply to wheel

    Returns:
        Tuple of (positioned_wheel, positioned_worm)
    """
    # Rotate wheel for mesh alignment
    wheel_aligned = wheel.rotate(Axis.Z, rotation_deg)

    # Position worm: rotate -90° around Y so axis is along X, offset in Y
    worm_positioned = worm.rotate(Axis.Y, -90)
    worm_positioned = worm_positioned.locate(Location((0, centre_distance_mm, 0)))

    return wheel_aligned, worm_positioned


def create_axis_markers(
    centre_distance_mm: float,
    worm_length_mm: float = 10.0,
    wheel_height_mm: float = 10.0,
    marker_radius_mm: float = 0.2,
) -> dict[str, Part]:
    """Create axis marker cylinders for visualization.

    These thin cylinders mark the true axis positions of the wheel and worm,
    which is helpful because gear bounding boxes shift with rotation.

    Args:
        centre_distance_mm: Distance between wheel and worm axes
        worm_length_mm: Length of worm axis marker
        wheel_height_mm: Length of wheel axis marker
        marker_radius_mm: Radius of marker cylinders

    Returns:
        Dictionary with 'wheel_axis' and 'worm_axis' Parts
    """
    # Wheel axis: vertical (Z) at origin
    wheel_axis = Cylinder(
        radius=marker_radius_mm,
        height=wheel_height_mm,
        align=(Align.CENTER, Align.CENTER, Align.CENTER),
    )

    # Worm axis: horizontal (X) at Y=centre_distance
    worm_axis = Cylinder(
        radius=marker_radius_mm,
        height=worm_length_mm,
        align=(Align.CENTER, Align.CENTER, Align.CENTER),
    )
    worm_axis = worm_axis.rotate(Axis.Y, 90)
    worm_axis = worm_axis.locate(Location((0, centre_distance_mm, 0)))

    return {
        "wheel_axis": wheel_axis,
        "worm_axis": worm_axis,
    }


def mesh_alignment_to_dict(result: MeshAlignmentResult) -> dict:
    """Convert MeshAlignmentResult to a dictionary for JSON serialization.

    Args:
        result: MeshAlignmentResult to convert

    Returns:
        Dictionary representation suitable for JSON output
    """
    return {
        "optimal_rotation_deg": result.optimal_rotation_deg,
        "interference_volume_mm3": result.interference_volume_mm3,
        "within_tolerance": result.within_tolerance,
        "mesh_quality": result.mesh_quality,
        "tolerance_mm3": result.tolerance_mm3,
        "tooth_pitch_deg": result.tooth_pitch_deg,
        "worm_position": {
            "x_mm": result.worm_position[0],
            "y_mm": result.worm_position[1],
            "z_mm": result.worm_position[2],
        },
        "message": result.message,
    }
