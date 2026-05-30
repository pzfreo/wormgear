"""Wormgear core — internal geometry routines and public feature/utility classes.

The geometry **classes** (``_WormGeometry``, ``_WheelGeometry``,
``_GloboidWormGeometry``, ``_VirtualHobbingWheelGeometry``) are private as
of 0.1.0; the public construction surface is ``wormgear.WormGear`` /
``wormgear.WormWheel`` / ``wormgear.make_pair``.

What remains exported from this module:

  * **Feature classes** (``BoreFeature``, ``KeywayFeature``, etc.) — used
    as kwargs to the facade constructors. Public.
  * **Mesh alignment** helpers (``find_optimal_mesh_rotation``, etc.) —
    public utility for analysing built pairs.
  * **Rim thickness** measurement utilities — public.
  * **bore_sizing** helpers — pure-Python, always available.

Example::

    >>> from wormgear import WormGear, WormWheel
    >>> from wormgear.core import BoreFeature, KeywayFeature
    >>> worm = WormGear(module=2.0, length=40.0, bore=BoreFeature(diameter=8.0))
"""

# bore_sizing has no build123d dependency — always available.
from .bore_sizing import calculate_default_bore

# Removed in 0.1.0 (#200) — kept here so ``__getattr__`` can give a helpful
# error when users hit ``from wormgear.core import WormGeometry`` etc.
_REMOVED_IN_010 = {
    "WormGeometry": "wormgear.WormGear",
    "WheelGeometry": "wormgear.WormWheel",
    "GloboidWormGeometry": "wormgear.make_pair(globoid=True)",
    "VirtualHobbingWheelGeometry": "wormgear.advanced.virtual_hobbing",
}

# Everything else requires build123d. If it's not installed (Pyodide path),
# only bore_sizing + the removed-name __getattr__ are available.
try:
    # Features — public, used as facade kwargs.
    from .features import (
        BoreFeature,
        DDCutFeature,
        HubFeature,
        KeywayFeature,
        ReliefGrooveFeature,
        SetScrewFeature,
        calculate_default_ddcut,
        get_din_6885_keyway,
    )

    # Mesh alignment — public utility.
    from .mesh_alignment import (
        MeshAlignmentResult,
        calculate_mesh_rotation,
        calculate_tolerance_mm3,
        check_interference,
        create_axis_markers,
        find_optimal_mesh_rotation,
        mesh_alignment_to_dict,
        position_for_mesh,
    )

    # Geometry validation — check a built part realises its calculated spec.
    from .validate_geometry import (
        DimensionCheck,
        GeometryReport,
        check_pair_geometry,
        check_wheel_geometry,
        check_worm_geometry,
    )

    # Rim thickness — public utility.
    from .rim_thickness import (
        WHEEL_RIM_WARNING_THRESHOLD_MM,
        WORM_RIM_WARNING_THRESHOLD_MM,
        RimThicknessResult,
        measure_rim_thickness,
        rim_thickness_to_dict,
    )

    # Hobbing presets — used by virtual hobbing. Re-exported from
    # ``wormgear.advanced.virtual_hobbing`` post-#203; kept here for
    # backwards compatibility with the (now-private) hobbing wheel.
    from .virtual_hobbing import (
        HOBBING_PRESETS,
        get_hobbing_preset,
        get_preset_steps,
    )

    __all__ = [
        # Features
        "BoreFeature",
        "KeywayFeature",
        "DDCutFeature",
        "SetScrewFeature",
        "HubFeature",
        "ReliefGrooveFeature",
        "calculate_default_bore",
        "calculate_default_ddcut",
        "get_din_6885_keyway",
        # Mesh alignment
        "MeshAlignmentResult",
        "find_optimal_mesh_rotation",
        "calculate_mesh_rotation",
        "calculate_tolerance_mm3",
        "check_interference",
        "position_for_mesh",
        "create_axis_markers",
        "mesh_alignment_to_dict",
        # Geometry validation
        "check_worm_geometry",
        "check_wheel_geometry",
        "check_pair_geometry",
        "GeometryReport",
        "DimensionCheck",
        # Rim thickness
        "RimThicknessResult",
        "measure_rim_thickness",
        "rim_thickness_to_dict",
        "WHEEL_RIM_WARNING_THRESHOLD_MM",
        "WORM_RIM_WARNING_THRESHOLD_MM",
        # Hobbing presets
        "HOBBING_PRESETS",
        "get_hobbing_preset",
        "get_preset_steps",
    ]
except ImportError:
    # Pyodide path — no build123d.
    __all__ = ["calculate_default_bore"]


def __getattr__(name):
    """Helpful error for removed names (#200, removed in 0.1.0)."""
    if name in _REMOVED_IN_010:
        raise ImportError(
            f"{name} was removed in wormgear 0.1.0. "
            f"Use {_REMOVED_IN_010[name]} instead. See #200 for migration."
        )
    raise AttributeError(f"module 'wormgear.core' has no attribute {name!r}")
