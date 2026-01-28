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

Note: All imports are lazy-loaded for fast startup. The calculator can be
imported without triggering geometry (build123d) or IO (Pydantic) imports.
"""

__version__ = "1.0.0-alpha"

# Define which names come from which submodule
# All imports are lazy to minimize startup time

_ENUMS = {"Hand", "WormProfile", "WormType", "BoreType", "AntiRotation"}

_CALCULATOR = {
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
    "calculate_default_bore",
}

_IO = {
    "load_design_json",
    "save_design_json",
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
}

_CORE = {
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

# Cache for lazy-loaded modules
_modules = {}


def __getattr__(name):
    """Lazy load submodules when their attributes are accessed."""
    global _modules

    if name in _ENUMS:
        if "enums" not in _modules:
            from . import enums
            _modules["enums"] = enums
        return getattr(_modules["enums"], name)

    if name in _CALCULATOR:
        if "calculator" not in _modules:
            from . import calculator
            _modules["calculator"] = calculator
        return getattr(_modules["calculator"], name)

    if name in _IO:
        if "io" not in _modules:
            from . import io
            _modules["io"] = io
        return getattr(_modules["io"], name)

    if name in _CORE:
        if "core" not in _modules:
            from . import core
            _modules["core"] = core
        return getattr(_modules["core"], name)

    raise AttributeError(f"module 'wormgear' has no attribute {name!r}")


__all__ = [
    # Version
    "__version__",

    # Geometry classes (lazy loaded from core)
    "WormGeometry",
    "WheelGeometry",
    "GloboidWormGeometry",
    "VirtualHobbingWheelGeometry",
    "HOBBING_PRESETS",
    "get_hobbing_preset",
    "get_preset_steps",

    # Features (lazy loaded from core)
    "BoreFeature",
    "KeywayFeature",
    "DDCutFeature",
    "SetScrewFeature",
    "HubFeature",
    "calculate_default_bore",
    "calculate_default_ddcut",
    "get_din_6885_keyway",

    # Enums (lazy loaded from enums)
    "Hand",
    "WormProfile",
    "WormType",
    "BoreType",
    "AntiRotation",

    # Calculator (lazy loaded from calculator)
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

    # IO (lazy loaded from io)
    "load_design_json",
    "save_design_json",

    # Parameters (lazy loaded from io)
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
