"""Advanced / opt-in helpers for wormgear.

The main public API (``wormgear.WormGear``, ``WormWheel``, ``make_pair``,
``check_mesh``) covers the 90 % case. The ``wormgear.advanced`` namespace
holds expert-mode tools whose use is deliberate rather than default.

Today this is just ``virtual_hobbing`` (kinematic-simulation wheel
generation). Future entries: envelope-based wheel construction,
custom contact analysis, etc.
"""

from .virtual_hobbing import virtual_hobbing

__all__ = ["virtual_hobbing"]
