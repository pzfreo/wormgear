"""
Wormgear Core - Pure geometry generation engine.

This module provides the core 3D geometry generation capabilities using build123d.
No JSON dependencies - pure Python API.

Example:
    >>> from wormgear.core import WormGeometry, WormParams, AssemblyParams
    >>>
    >>> worm_params = WormParams(
    ...     module_mm=2.0,
    ...     num_starts=1,
    ...     pitch_diameter_mm=16.0,
    ...     # ... other params
    ... )
    >>>
    >>> assembly_params = AssemblyParams(
    ...     centre_distance_mm=38.0,
    ...     pressure_angle_deg=20.0,
    ...     # ... other params
    ... )
    >>>
    >>> worm = WormGeometry(worm_params, assembly_params, length=40.0)
    >>> part = worm.build()
    >>> part.export_step("worm.step")
"""

# Geometry classes (to be moved from parent directory)
from ..worm import WormGeometry
from ..wheel import WheelGeometry
from ..globoid_worm import GloboidWormGeometry
from ..virtual_hobbing import VirtualHobbingWheelGeometry

# Features (to be moved)
from ..features import (
    BoreFeature,
    KeywayFeature,
    DDCutFeature,
    SetScrewFeature,
    HubFeature,
    calculate_default_bore,
    calculate_default_ddcut,
    get_din_6885_keyway,
)

# Parameters (to be created - extracted from io.py)
# TODO: Create parameters.py

__all__ = [
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
    "calculate_default_bore",
    "calculate_default_ddcut",
    "get_din_6885_keyway",
]
