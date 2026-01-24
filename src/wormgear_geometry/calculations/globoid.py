"""
Globoid worm gear calculations.

These functions will be imported by wormgearcalc to provide
a single source of truth for globoid geometry calculations.

TODO: Implement these functions when integrating with calculator.
"""

import math
from typing import Dict, List, Tuple


def validate_clearance(
    centre_distance_mm: float,
    worm_tip_radius_mm: float,
    wheel_root_radius_mm: float,
    min_clearance_mm: float = 0.05
) -> Dict[str, any]:
    """
    Validate that worm and wheel have adequate clearance.

    This is the critical check for hobbing - ensures the hob cuts deep enough.

    Args:
        centre_distance_mm: Assembly centre distance
        worm_tip_radius_mm: Worm tip radius (smallest radius on teeth)
        wheel_root_radius_mm: Wheel root radius
        min_clearance_mm: Minimum acceptable clearance (default 0.05mm)

    Returns:
        {
            "valid": bool,
            "clearance_mm": float,
            "error": str (if invalid),
            "warning": str (if tight)
        }

    Example:
        >>> validate_clearance(6.1, 3.5, 2.55)
        {"valid": True, "clearance_mm": 0.05}
    """
    clearance = centre_distance_mm - worm_tip_radius_mm - wheel_root_radius_mm

    result: Dict[str, any] = {
        "valid": clearance >= 0,
        "clearance_mm": round(clearance, 3)
    }

    if clearance < 0:
        result["error"] = f"Interference! Worm tip overlaps wheel root by {abs(clearance):.3f}mm"
    elif clearance < min_clearance_mm:
        result["warning"] = f"Tight clearance ({clearance:.3f}mm < {min_clearance_mm}mm) - manufacturing tolerance issues likely"

    return result


def recommend_wheel_width(
    worm_pitch_diameter_mm: float,
    module_mm: float,
    contact_ratio_factor: float = 1.3
) -> float:
    """
    Recommend wheel width based on design guidelines.

    Wheel width is NOT a geometric constraint - it's a design choice
    based on contact ratio, strength, and engagement requirements.

    Args:
        worm_pitch_diameter_mm: Worm pitch diameter
        module_mm: Module
        contact_ratio_factor: Multiplier for worm diameter (default 1.3)

    Returns:
        Recommended wheel width in mm

    Example:
        >>> recommend_wheel_width(6.2, 0.4)
        8.1  # 6.2 * 1.3
    """
    # TODO: Implement
    raise NotImplementedError("To be implemented when integrating calculator")


def recommend_worm_length(
    wheel_width_mm: float,
    lead_mm: float,
    margin_mm: float = 1.0
) -> float:
    """
    Recommend worm length for proper engagement.

    Worm should extend beyond wheel edges for proper tooth engagement,
    plus end taper zones.

    Args:
        wheel_width_mm: Wheel face width
        lead_mm: Worm lead
        margin_mm: Additional margin (default 1.0mm)

    Returns:
        Recommended worm length in mm (rounded to 0.5mm)

    Example:
        >>> recommend_worm_length(1.5, 1.257)
        6.0  # 1.5 + 2*1.257 + 1.0 = 5.0, rounded up
    """
    # TODO: Implement
    raise NotImplementedError("To be implemented when integrating calculator")


def validate_throat_reduction(
    throat_reduction_mm: float,
    module_mm: float
) -> List[str]:
    """
    Validate that throat reduction is reasonable.

    Args:
        throat_reduction_mm: Hourglass reduction
        module_mm: Module

    Returns:
        List of warning messages (empty if all OK)

    Example:
        >>> validate_throat_reduction(0.01, 0.4)
        ["Throat reduction <0.02mm - nearly cylindrical, minimal globoid benefit"]
    """
    # TODO: Implement
    raise NotImplementedError("To be implemented when integrating calculator")


def calculate_throat_geometry(
    worm_pitch_diameter_mm: float,
    wheel_pitch_diameter_mm: float,
    throat_reduction_mm: float
) -> Dict[str, float]:
    """
    Calculate throat-related geometry for globoid worm.

    Args:
        worm_pitch_diameter_mm: Nominal worm pitch diameter
        wheel_pitch_diameter_mm: Wheel pitch diameter
        throat_reduction_mm: Desired throat reduction

    Returns:
        Dict with:
        {
            "centre_distance_mm": float,
            "throat_pitch_radius_mm": float,
            "nominal_pitch_radius_mm": float,
            "throat_curvature_radius_mm": float
        }

    Example:
        >>> calculate_throat_geometry(
        ...     worm_pitch_diameter_mm=6.8,
        ...     wheel_pitch_diameter_mm=6.0,
        ...     throat_reduction_mm=0.05
        ... )
        {
            "centre_distance_mm": 6.35,
            "throat_pitch_radius_mm": 3.35,
            "nominal_pitch_radius_mm": 3.40,
            "throat_curvature_radius_mm": 3.0
        }
    """
    # TODO: Implement throat geometry calculation
    raise NotImplementedError("To be implemented when integrating calculator")
