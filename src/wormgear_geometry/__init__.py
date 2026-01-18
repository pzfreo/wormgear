"""
Worm Gear Geometry Generator

Generates CNC-ready STEP files from worm gear parameters using build123d.

This is Tool 2 in the worm gear design system. It accepts JSON output from
the calculator (Tool 1) and produces exact 3D CAD models.

Calculator: https://github.com/pzfreo/wormgearcalc
Web Calculator: https://pzfreo.github.io/wormgearcalc/
"""

__version__ = "0.1.0"

from .worm import WormGeometry
from .wheel import WheelGeometry
from .io import (
    load_design_json,
    WormParams,
    WheelParams,
    AssemblyParams,
    WormGearDesign
)
from .features import (
    BoreFeature,
    KeywayFeature,
    get_din_6885_keyway,
    calculate_default_bore,
)

__all__ = [
    "WormGeometry",
    "WheelGeometry",
    "load_design_json",
    "WormParams",
    "WheelParams",
    "AssemblyParams",
    "WormGearDesign",
    "BoreFeature",
    "KeywayFeature",
    "get_din_6885_keyway",
    "calculate_default_bore",
]
