"""
Wormgear Core - Pure geometry generation engine.

This module provides the core 3D geometry generation capabilities using build123d.
No JSON dependencies - pure Python API.

Example:
    >>> from wormgear.core import WormGeometry
    >>> from wormgear.io import WormParams, AssemblyParams
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

# Bore sizing is always available (no build123d dependency)
from .bore_sizing import calculate_default_bore

# Geometry classes require build123d - make import conditional
# This allows calculator (in Pyodide) to import core.bore_sizing without build123d
try:
    from .worm import WormGeometry
    from .wheel import WheelGeometry
    from .globoid_worm import GloboidWormGeometry
    from .virtual_hobbing import VirtualHobbingWheelGeometry, HOBBING_PRESETS, get_hobbing_preset, get_preset_steps

    # Features (also require build123d)
    from .features import (
        BoreFeature,
        KeywayFeature,
        DDCutFeature,
        SetScrewFeature,
        HubFeature,
        calculate_default_ddcut,
        get_din_6885_keyway,
    )

    # Mesh alignment
    from .mesh_alignment import (
        MeshAlignmentResult,
        find_optimal_mesh_rotation,
        calculate_mesh_rotation,
        check_interference,
        position_for_mesh,
        create_axis_markers,
        mesh_alignment_to_dict,
    )

    # Rim thickness measurement
    from .rim_thickness import (
        RimThicknessResult,
        measure_rim_thickness,
        rim_thickness_to_dict,
        WHEEL_RIM_WARNING_THRESHOLD_MM,
        WORM_RIM_WARNING_THRESHOLD_MM,
    )

    __all__ = [
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

        # Mesh alignment
        "MeshAlignmentResult",
        "find_optimal_mesh_rotation",
        "calculate_mesh_rotation",
        "check_interference",
        "position_for_mesh",
        "create_axis_markers",
        "mesh_alignment_to_dict",

        # Rim thickness measurement
        "RimThicknessResult",
        "measure_rim_thickness",
        "rim_thickness_to_dict",
        "WHEEL_RIM_WARNING_THRESHOLD_MM",
        "WORM_RIM_WARNING_THRESHOLD_MM",
    ]
except ImportError:
    # build123d not available (e.g., in Pyodide calculator without geometry)
    # Only expose bore_sizing functions
    __all__ = [
        "calculate_default_bore",
    ]
