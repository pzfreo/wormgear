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
    BoreFeature,
    KeywayFeature,
    DDCutFeature,
    SetScrewFeature,
    HubFeature,
)

# Calculator (Layer 2a)
# Will be populated as we port from wormgearcalc

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

    # Features
    "BoreFeature",
    "KeywayFeature",
    "DDCutFeature",
    "SetScrewFeature",
    "HubFeature",

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
