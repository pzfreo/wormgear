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
    """
    optimal_rotation_deg: float
    interference_volume_mm3: float
    within_tolerance: bool
    tooth_pitch_deg: float
    worm_position: tuple[float, float, float]
    message: str


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
    coarse_step_deg: float = 1.0,
    fine_step_deg: float = 0.2,
) -> tuple[float, float]:
    """Find wheel rotation that minimizes collision with worm.

    Uses two-phase grid search with early exit optimization:
    1. Coarse search: 1° steps over one tooth pitch
    2. Fine search: 0.2° steps around best coarse angle
    3. Early exit: Stop immediately if zero interference found

    Args:
        wheel: Wheel Part centred at origin with axis along Z
        worm: Worm Part already positioned at correct centre distance
        num_teeth: Number of teeth on the wheel
        coarse_step_deg: Step size for initial search (default 1.0°)
        fine_step_deg: Step size for refinement (default 0.2°)

    Returns:
        Tuple of (optimal_rotation_deg, min_interference_mm3)
    """
    tooth_pitch_deg = 360.0 / num_teeth

    best_rotation = 0.0
    min_interference = float("inf")

    # Coarse search over one tooth pitch
    num_coarse_steps = int(tooth_pitch_deg / coarse_step_deg) + 1
    for i in range(num_coarse_steps):
        angle = i * coarse_step_deg
        rotated_wheel = wheel.rotate(Axis.Z, angle)
        interference = _calculate_interference(rotated_wheel, worm)

        if interference < min_interference:
            min_interference = interference
            best_rotation = angle

        # Early exit on zero interference
        if interference == 0.0:
            return angle, 0.0

    # Fine search around best angle
    fine_range = int(coarse_step_deg / fine_step_deg) + 1
    for d in range(-fine_range, fine_range + 1):
        angle = best_rotation + d * fine_step_deg
        normalized_angle = angle % tooth_pitch_deg

        rotated_wheel = wheel.rotate(Axis.Z, normalized_angle)
        interference = _calculate_interference(rotated_wheel, worm)

        if interference < min_interference:
            min_interference = interference
            best_rotation = normalized_angle

        # Early exit on zero interference
        if interference == 0.0:
            return normalized_angle, 0.0

    return best_rotation, min_interference


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
    backlash_tolerance_mm3: float = 1.0,
    coarse_step_deg: float = 1.0,
    fine_step_deg: float = 0.2,
) -> MeshAlignmentResult:
    """Find optimal wheel rotation and analyse mesh quality.

    This is the main entry point for mesh analysis. It:
    1. Positions the worm at the correct centre distance
    2. Calculates optimal wheel rotation to minimize interference
    3. Measures final interference volume
    4. Reports whether mesh is within tolerance

    Uses two-phase grid search with early exit for efficiency.

    The worm is positioned with its axis along Y, offset from the wheel
    (whose axis is along Z) by the centre distance.

    Args:
        wheel: Wheel Part centred at origin with axis along Z
        worm: Worm Part centred at origin with axis along Z (will be rotated/positioned)
        centre_distance_mm: Distance between wheel and worm axes in mm
        num_teeth: Number of teeth on the wheel
        backlash_tolerance_mm3: Maximum acceptable interference volume (default 1.0)
        coarse_step_deg: Coarse search step size (default 1.0°)
        fine_step_deg: Fine search step size (default 0.2°)

    Returns:
        MeshAlignmentResult with rotation, interference, and status
    """
    tooth_pitch_deg = 360.0 / num_teeth

    # Position worm: rotate -90° around Y so axis is along X, offset by centre_distance in Y
    worm_positioned = worm.rotate(Axis.Y, -90)
    worm_positioned = worm_positioned.locate(Location((0, centre_distance_mm, 0)))
    worm_position = (0.0, centre_distance_mm, 0.0)

    # Calculate optimal rotation
    optimal_rotation, interference = calculate_mesh_rotation(
        wheel=wheel,
        worm=worm_positioned,
        num_teeth=num_teeth,
        coarse_step_deg=coarse_step_deg,
        fine_step_deg=fine_step_deg,
    )

    # Also measure interference without rotation for comparison
    interference_unrotated = _calculate_interference(wheel, worm_positioned)

    within_tolerance = interference <= backlash_tolerance_mm3

    # Build status message
    if interference == 0.0:
        message = "Perfect mesh - no interference detected"
    elif within_tolerance:
        message = f"Good mesh - interference {interference:.4f}mm³ within tolerance"
    else:
        message = f"Warning - interference {interference:.4f}mm³ exceeds tolerance"

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
        "tooth_pitch_deg": result.tooth_pitch_deg,
        "worm_position": {
            "x_mm": result.worm_position[0],
            "y_mm": result.worm_position[1],
            "z_mm": result.worm_position[2],
        },
        "message": result.message,
    }
