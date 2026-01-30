"""Post-build rim thickness measurement module.

This module provides functions for measuring the actual minimum rim thickness
from bore surfaces (including keyway slots and DD-cut flats) to outer boundaries
(tooth roots for wheels, thread roots for worms).

Uses ray casting through OpenCascade's IntCurvesFace_ShapeIntersector for
accurate radial distance measurement on the actual built geometry.
"""

from dataclasses import dataclass
from math import sqrt, cos, sin, pi
from typing import Optional, Tuple

from build123d import Part

from OCP.gp import gp_Pnt, gp_Dir, gp_Lin
from OCP.IntCurvesFace import IntCurvesFace_ShapeIntersector


# Default warning thresholds
WHEEL_RIM_WARNING_THRESHOLD_MM = 0.75
WORM_RIM_WARNING_THRESHOLD_MM = 1.0

# Number of angular samples for ray casting
DEFAULT_ANGULAR_SAMPLES = 72  # Every 5 degrees
DEFAULT_AXIAL_SAMPLES = 5  # 5 Z positions


@dataclass
class RimThicknessResult:
    """Result of post-build rim thickness measurement.

    Attributes:
        minimum_thickness_mm: True minimum distance from bore surface to outer boundary.
            For wheels, this is typically bore to tooth root or keyway bottom.
            For worms, this is typically bore to thread root.
        measurement_point_bore: (x, y, z) coordinates on bore surface at minimum.
        measurement_point_outer: (x, y, z) coordinates on outer surface at minimum.
        bore_diameter_mm: Bore diameter that was used.
        is_valid: Whether the measurement succeeded.
        has_warning: True if minimum_thickness_mm < warning_threshold_mm.
        warning_threshold_mm: Threshold below which warning is issued.
        message: Human-readable status message.
    """

    minimum_thickness_mm: float
    measurement_point_bore: Optional[Tuple[float, float, float]] = None
    measurement_point_outer: Optional[Tuple[float, float, float]] = None
    bore_diameter_mm: float = 0.0
    is_valid: bool = True
    has_warning: bool = False
    warning_threshold_mm: float = WHEEL_RIM_WARNING_THRESHOLD_MM
    message: str = ""


def measure_rim_thickness(
    part: Part,
    bore_diameter_mm: float,
    part_height_mm: Optional[float] = None,
    warning_threshold_mm: Optional[float] = None,
    is_worm: bool = False,
    angular_samples: int = DEFAULT_ANGULAR_SAMPLES,
    axial_samples: int = DEFAULT_AXIAL_SAMPLES,
) -> RimThicknessResult:
    """Measure minimum rim thickness from bore surface to outer boundary.

    Uses ray casting to measure the radial distance from points on the bore
    surface to the nearest outer surface. This correctly handles keyways,
    DD-cuts, and other bore features.

    Args:
        part: Built Part with all features applied (bore, keyway, etc.)
        bore_diameter_mm: Nominal bore diameter.
        part_height_mm: Height of the part (auto-detected if None).
        warning_threshold_mm: Threshold for thin rim warning.
            Defaults to 0.75mm for wheels, 1.0mm for worms.
        is_worm: True if measuring a worm (affects default warning threshold).
        angular_samples: Number of angles to sample around bore (default 72 = 5°).
        axial_samples: Number of Z positions to sample (default 5).

    Returns:
        RimThicknessResult with measurement details and warning status.

    Example:
        >>> wheel = WheelGeometry(..., bore=BoreFeature(12.0), keyway=KeywayFeature())
        >>> wheel_part = wheel.build()
        >>> result = measure_rim_thickness(wheel_part, bore_diameter_mm=12.0)
        >>> print(f"Minimum rim: {result.minimum_thickness_mm:.2f}mm")
        Minimum rim: 2.30mm  # At keyway bottom
    """
    # Set default warning threshold based on part type
    if warning_threshold_mm is None:
        warning_threshold_mm = (
            WORM_RIM_WARNING_THRESHOLD_MM if is_worm else WHEEL_RIM_WARNING_THRESHOLD_MM
        )

    bore_radius = bore_diameter_mm / 2

    # Get part bounding box to determine Z range
    try:
        bbox = part.bounding_box()
        if part_height_mm is None:
            part_height_mm = bbox.max.Z - bbox.min.Z
        z_min = bbox.min.Z
        z_max = bbox.max.Z
    except Exception as e:
        return RimThicknessResult(
            minimum_thickness_mm=0.0,
            bore_diameter_mm=bore_diameter_mm,
            is_valid=False,
            warning_threshold_mm=warning_threshold_mm,
            message=f"Failed to get part bounding box: {e}",
        )

    # Create ray intersector
    try:
        intersector = IntCurvesFace_ShapeIntersector()
        intersector.Load(part.wrapped, 0.001)  # 1um tolerance
    except Exception as e:
        return RimThicknessResult(
            minimum_thickness_mm=0.0,
            bore_diameter_mm=bore_diameter_mm,
            is_valid=False,
            warning_threshold_mm=warning_threshold_mm,
            message=f"Failed to create ray intersector: {e}",
        )

    # Sample points on bore surface and cast rays radially outward
    min_rim = float("inf")
    min_bore_point = None
    min_outer_point = None

    # Sample at multiple Z positions (avoiding exact edges)
    z_margin = part_height_mm * 0.1
    z_positions = [
        z_min + z_margin + (z_max - z_min - 2 * z_margin) * i / (axial_samples - 1)
        for i in range(axial_samples)
    ]

    for z in z_positions:
        for i in range(angular_samples):
            angle = i * 2 * pi / angular_samples

            # Point on bore surface
            x = bore_radius * cos(angle)
            y = bore_radius * sin(angle)

            # Ray direction: radially outward
            dx = cos(angle)
            dy = sin(angle)

            # Create ray
            origin = gp_Pnt(x, y, z)
            direction = gp_Dir(dx, dy, 0)
            line = gp_Lin(origin, direction)

            # Find intersections
            intersector.Perform(line, -1000, 1000)

            if intersector.NbPnt() > 0:
                # Find the first intersection OUTWARD from bore (parameter > 0)
                for j in range(1, intersector.NbPnt() + 1):
                    param = intersector.WParameter(j)
                    # Small offset to skip the bore surface itself
                    if param > 0.01:
                        if param < min_rim:
                            min_rim = param
                            min_bore_point = (x, y, z)
                            outer_x = x + param * dx
                            outer_y = y + param * dy
                            min_outer_point = (outer_x, outer_y, z)
                        break

    # Check if we found any valid measurements
    if min_rim == float("inf"):
        return RimThicknessResult(
            minimum_thickness_mm=0.0,
            bore_diameter_mm=bore_diameter_mm,
            is_valid=False,
            warning_threshold_mm=warning_threshold_mm,
            message="No outer surface found - geometry may be invalid or hollow",
        )

    # Determine warning status
    has_warning = min_rim < warning_threshold_mm

    # Build message
    part_type = "worm" if is_worm else "wheel"
    if has_warning:
        message = (
            f"Warning: {part_type} rim thickness ({min_rim:.2f}mm) "
            f"is below recommended minimum ({warning_threshold_mm:.2f}mm)"
        )
    else:
        message = f"{part_type.capitalize()} rim thickness: {min_rim:.2f}mm"

    return RimThicknessResult(
        minimum_thickness_mm=min_rim,
        measurement_point_bore=min_bore_point,
        measurement_point_outer=min_outer_point,
        bore_diameter_mm=bore_diameter_mm,
        is_valid=True,
        has_warning=has_warning,
        warning_threshold_mm=warning_threshold_mm,
        message=message,
    )


def rim_thickness_to_dict(result: RimThicknessResult) -> dict:
    """Convert RimThicknessResult to dictionary for JSON serialization.

    Args:
        result: RimThicknessResult to convert.

    Returns:
        Dictionary suitable for JSON serialization.
    """
    d = {
        "minimum_thickness_mm": round(result.minimum_thickness_mm, 4),
        "bore_diameter_mm": result.bore_diameter_mm,
        "is_valid": result.is_valid,
        "has_warning": result.has_warning,
        "warning_threshold_mm": result.warning_threshold_mm,
        "message": result.message,
    }

    if result.measurement_point_bore is not None:
        d["measurement_point_bore"] = {
            "x_mm": round(result.measurement_point_bore[0], 4),
            "y_mm": round(result.measurement_point_bore[1], 4),
            "z_mm": round(result.measurement_point_bore[2], 4),
        }

    if result.measurement_point_outer is not None:
        d["measurement_point_outer"] = {
            "x_mm": round(result.measurement_point_outer[0], 4),
            "y_mm": round(result.measurement_point_outer[1], 4),
            "z_mm": round(result.measurement_point_outer[2], 4),
        }

    return d
