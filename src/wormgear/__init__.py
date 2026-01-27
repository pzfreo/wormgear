"""
Wormgear - Unified worm gear calculator and 3D geometry generator.

Complete worm gear design system from engineering calculations to CNC-ready STEP files.

Example:
    >>> from wormgear.calculator import design_from_module
    >>> from wormgear.core import WormGeometry
    >>> from wormgear.io import save_design_json
    >>>
    >>> # Calculate parameters
    >>> design = design_from_module(module=2.0, ratio=30)
    >>>
    >>> # Generate 3D model
    >>> worm = WormGeometry(design.worm, design.assembly, length=40)
    >>> worm.build().export_step("worm.step")
    >>>
    >>> # Save design
    >>> save_design_json(design, "design.json")
"""

__version__ = "1.0.0-alpha"

# Enums (shared types - no heavy dependencies)
from .enums import (
    Hand,
    WormProfile,
    WormType,
)

# Calculator (Layer 2a - no build123d dependency)
from .calculator import (
    STANDARD_MODULES,
    calculate_design_from_module,
    calculate_design_from_centre_distance,
    calculate_design_from_wheel,
    nearest_standard_module,
    is_standard_module,
    estimate_efficiency,
    validate_design,
    Severity,
    ValidationResult,
    calculate_default_bore,
)

# IO (Layer 2b - no build123d dependency)
from .io import (
    load_design_json,
    save_design_json,
    WormParams,
    WheelParams,
    AssemblyParams,
    WormGearDesign,
    Features,
    WormFeatures,
    WheelFeatures,
    SetScrewSpec,
    HubSpec,
    ManufacturingParams,
)

# Core geometry (Layer 1) - LAZY LOADED to avoid build123d import
# These are only imported when actually accessed
_core_names = {
    "WormGeometry",
    "WheelGeometry",
    "GloboidWormGeometry",
    "VirtualHobbingWheelGeometry",
    "HOBBING_PRESETS",
    "get_hobbing_preset",
    "get_preset_steps",
    "BoreFeature",
    "KeywayFeature",
    "DDCutFeature",
    "SetScrewFeature",
    "HubFeature",
    "calculate_default_ddcut",
    "get_din_6885_keyway",
}

_core_module = None


def __getattr__(name):
    """Lazy load core geometry module when its attributes are accessed."""
    global _core_module
    if name in _core_names:
        if _core_module is None:
            from . import core as _core_module
        return getattr(_core_module, name)
    raise AttributeError(f"module 'wormgear' has no attribute {name!r}")


__all__ = [
    # Version
    "__version__",

    # Geometry classes (lazy loaded)
    "WormGeometry",
    "WheelGeometry",
    "GloboidWormGeometry",
    "VirtualHobbingWheelGeometry",
    "HOBBING_PRESETS",
    "get_hobbing_preset",
    "get_preset_steps",

    # Features (lazy loaded)
    "BoreFeature",
    "KeywayFeature",
    "DDCutFeature",
    "SetScrewFeature",
    "HubFeature",
    "calculate_default_bore",
    "calculate_default_ddcut",
    "get_din_6885_keyway",

    # Enums (type-safe)
    "Hand",
    "WormProfile",
    "WormType",

    # Calculator
    "STANDARD_MODULES",
    "calculate_design_from_module",
    "calculate_design_from_centre_distance",
    "calculate_design_from_wheel",
    "nearest_standard_module",
    "is_standard_module",
    "estimate_efficiency",
    "validate_design",
    "Severity",
    "ValidationResult",

    # IO
    "load_design_json",
    "save_design_json",

    # Parameters
    "WormParams",
    "WheelParams",
    "AssemblyParams",
    "WormGearDesign",
    "Features",
    "WormFeatures",
    "WheelFeatures",
    "SetScrewSpec",
    "HubSpec",
    "ManufacturingParams",
]
