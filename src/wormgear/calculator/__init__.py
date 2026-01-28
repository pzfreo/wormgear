"""
Worm Gear Calculator - Engineering calculations for worm gear design.

This module provides calculator functions for worm gear design.
All design functions return WormGearDesign dataclasses for type safety.

Example:
    >>> from wormgear.calculator import design_from_module
    >>> from wormgear.core import WormGeometry
    >>>
    >>> # Calculate design parameters
    >>> design = design_from_module(module=2.0, ratio=30)
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
    calculate_manufacturing_params,

    # High-level design functions (return WormGearDesign dataclass)
    design_from_module,
    design_from_centre_distance,
    design_from_wheel,
    design_from_envelope,
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

from ..enums import (
    # Type-safe enums
    Hand,
    WormProfile,
    WormType,
)

from .output import (
    # Output formatters
    to_json,
    to_markdown,
    to_summary,
)

from ..core.bore_sizing import (
    # Bore calculation (pure geometry math, moved to core)
    calculate_default_bore,
)

# Convenience imports
from ..io import WormParams, WheelParams, AssemblyParams, WormGearDesign, ManufacturingParams


# Legacy aliases - design_from_* now return WormGearDesign directly
# These are kept for backward compatibility with existing code
calculate_design_from_module = design_from_module
calculate_design_from_centre_distance = design_from_centre_distance
calculate_design_from_wheel = design_from_wheel
calculate_design_from_envelope = design_from_envelope


__all__ = [
    # Constants
    "STANDARD_MODULES",

    # Enums (type-safe)
    "Hand",
    "WormProfile",
    "WormType",

    # Dataclasses
    "WormParams",
    "WheelParams",
    "AssemblyParams",
    "ManufacturingParams",
    "WormGearDesign",

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
    "calculate_manufacturing_params",

    # High-level design functions (return WormGearDesign dataclass)
    "design_from_module",
    "design_from_centre_distance",
    "design_from_wheel",
    "design_from_envelope",

    # Legacy aliases (same as design_from_* functions)
    "calculate_design_from_module",
    "calculate_design_from_centre_distance",
    "calculate_design_from_wheel",
    "calculate_design_from_envelope",

    # Validation
    "validate_design",
    "calculate_minimum_teeth",
    "calculate_recommended_profile_shift",
    "Severity",
    "ValidationMessage",
    "ValidationResult",

    # Output formatters
    "to_json",
    "to_markdown",
    "to_summary",
]
