"""
Worm Gear Calculator - Engineering calculations for worm gear design.

This module provides calculator functions ported from wormgearcalc.
Returns WormGearDesign objects compatible with geometry generation.

Example:
    >>> from wormgear.calculator import calculate_design_from_module
    >>> from wormgear.core import WormGeometry
    >>>
    >>> # Calculate design parameters
    >>> design = calculate_design_from_module(module=2.0, ratio=30)
    >>>
    >>> # Generate 3D geometry
    >>> worm = WormGeometry(design.worm, design.assembly, length=40)
    >>> worm.build().export_step("worm.step")
"""

from .core import (
    # Constants
    STANDARD_MODULES,

    # Utility functions
    nearest_standard_module,
    is_standard_module,
    estimate_efficiency,

    # Low-level calculation functions
    calculate_worm,
    calculate_wheel,
    calculate_centre_distance,
    calculate_globoid_throat_radii,
    calculate_recommended_wheel_width,
    calculate_recommended_worm_length,

    # High-level design functions
    design_from_module,
    design_from_centre_distance,
    design_from_wheel,
)

from .validation import (
    # Validation
    validate_design,
    calculate_minimum_teeth,
    calculate_recommended_profile_shift,
    Severity,
    ValidationMessage,
    ValidationResult,
)

# Convenience imports
from ..io import WormParams, WheelParams, AssemblyParams, WormGearDesign, ManufacturingParams


def _dict_to_worm_gear_design(design_dict: dict) -> WormGearDesign:
    """Convert dict from calculator to WormGearDesign dataclass."""
    worm = WormParams(**design_dict["worm"])
    wheel = WheelParams(**design_dict["wheel"])
    assembly = AssemblyParams(**design_dict["assembly"])
    manufacturing = ManufacturingParams(**design_dict.get("manufacturing", {}))

    return WormGearDesign(
        worm=worm,
        wheel=wheel,
        assembly=assembly,
        manufacturing=manufacturing
    )


# Wrapper functions that return proper dataclass instances
def calculate_design_from_module(
    module: float,
    ratio: int,
    worm_pitch_diameter: float = None,
    target_lead_angle: float = 7.0,
    pressure_angle: float = 20.0,
    backlash: float = 0.0,
    num_starts: int = 1,
    clearance_factor: float = 0.25,
    hand: str = "right",
    profile_shift: float = 0.0,
    profile: str = "ZA",
    globoid: bool = False,
    throat_reduction: float = 0.0,
    wheel_throated: bool = False
) -> WormGearDesign:
    """
    Design worm gear pair from module specification.

    Returns WormGearDesign dataclass ready for geometry generation.
    See core.design_from_module for full documentation.
    """
    design_dict = design_from_module(
        module=module,
        ratio=ratio,
        worm_pitch_diameter=worm_pitch_diameter,
        target_lead_angle=target_lead_angle,
        pressure_angle=pressure_angle,
        backlash=backlash,
        num_starts=num_starts,
        clearance_factor=clearance_factor,
        hand=hand,
        profile_shift=profile_shift,
        profile=profile,
        globoid=globoid,
        throat_reduction=throat_reduction,
        wheel_throated=wheel_throated
    )
    return _dict_to_worm_gear_design(design_dict)


def calculate_design_from_centre_distance(
    centre_distance: float,
    ratio: int,
    worm_to_wheel_ratio: float = 0.3,
    pressure_angle: float = 20.0,
    backlash: float = 0.0,
    num_starts: int = 1,
    clearance_factor: float = 0.25,
    hand: str = "right",
    profile_shift: float = 0.0,
    profile: str = "ZA",
    globoid: bool = False,
    throat_reduction: float = 0.0,
    wheel_throated: bool = False
) -> WormGearDesign:
    """
    Design worm gear pair from centre distance constraint.

    Returns WormGearDesign dataclass ready for geometry generation.
    See core.design_from_centre_distance for full documentation.
    """
    design_dict = design_from_centre_distance(
        centre_distance=centre_distance,
        ratio=ratio,
        worm_to_wheel_ratio=worm_to_wheel_ratio,
        pressure_angle=pressure_angle,
        backlash=backlash,
        num_starts=num_starts,
        clearance_factor=clearance_factor,
        hand=hand,
        profile_shift=profile_shift,
        profile=profile,
        globoid=globoid,
        throat_reduction=throat_reduction,
        wheel_throated=wheel_throated
    )
    return _dict_to_worm_gear_design(design_dict)


def calculate_design_from_wheel(
    wheel_od: float,
    ratio: int,
    target_lead_angle: float = 7.0,
    pressure_angle: float = 20.0,
    backlash: float = 0.0,
    num_starts: int = 1,
    clearance_factor: float = 0.25,
    hand: str = "right",
    profile_shift: float = 0.0,
    profile: str = "ZA",
    globoid: bool = False,
    throat_reduction: float = 0.0,
    wheel_throated: bool = False
) -> WormGearDesign:
    """
    Design worm gear pair from wheel OD constraint.

    Returns WormGearDesign dataclass ready for geometry generation.
    See core.design_from_wheel for full documentation.
    """
    design_dict = design_from_wheel(
        wheel_od=wheel_od,
        ratio=ratio,
        target_lead_angle=target_lead_angle,
        pressure_angle=pressure_angle,
        backlash=backlash,
        num_starts=num_starts,
        clearance_factor=clearance_factor,
        hand=hand,
        profile_shift=profile_shift,
        profile=profile,
        globoid=globoid,
        throat_reduction=throat_reduction,
        wheel_throated=wheel_throated
    )
    return _dict_to_worm_gear_design(design_dict)


__all__ = [
    # Constants
    "STANDARD_MODULES",

    # Utility functions
    "nearest_standard_module",
    "is_standard_module",
    "estimate_efficiency",

    # Low-level calculation functions
    "calculate_worm",
    "calculate_wheel",
    "calculate_centre_distance",
    "calculate_globoid_throat_radii",
    "calculate_recommended_wheel_width",
    "calculate_recommended_worm_length",

    # High-level design functions (return dicts)
    "design_from_module",
    "design_from_centre_distance",
    "design_from_wheel",

    # Wrapper functions (return WormGearDesign dataclass)
    "calculate_design_from_module",
    "calculate_design_from_centre_distance",
    "calculate_design_from_wheel",

    # Validation
    "validate_design",
    "calculate_minimum_teeth",
    "calculate_recommended_profile_shift",
    "Severity",
    "ValidationMessage",
    "ValidationResult",
]
