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

# Core geometry generation (Layer 1)
from .core import (
    WormGeometry,
    WheelGeometry,
    GloboidWormGeometry,
    VirtualHobbingWheelGeometry,
    HOBBING_PRESETS,
    get_hobbing_preset,
    get_preset_steps,
    BoreFeature,
    KeywayFeature,
    DDCutFeature,
    SetScrewFeature,
    HubFeature,
    calculate_default_bore,
    calculate_default_ddcut,
    get_din_6885_keyway,
)

# Calculator (Layer 2a)
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
)

# IO (Layer 2b)
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

__all__ = [
    # Version
    "__version__",

    # Geometry classes
    "WormGeometry",
    "WheelGeometry",
    "GloboidWormGeometry",
    "VirtualHobbingWheelGeometry",
    "HOBBING_PRESETS",
    "get_hobbing_preset",
    "get_preset_steps",

    # Features
    "BoreFeature",
    "KeywayFeature",
    "DDCutFeature",
    "SetScrewFeature",
    "HubFeature",
    "calculate_default_bore",
    "calculate_default_ddcut",
    "get_din_6885_keyway",

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
