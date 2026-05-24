"""Virtual hobbing — kinematic-simulation wheel generation.

For users who need conjugate tooth profiles more accurate than the
``WormWheel(throated=True)`` approximation. Significantly slower —
the simulation runs ``steps`` boolean operations per full wheel
rotation. Use only when high-precision contact is required.

Contrast with ``WormWheel(throated=True)``:

  * ``WormWheel(throated=True)`` is a single throat cut, fast, good enough
    for most engineering applications. Geometry deviation from the true
    conjugate profile is typically <1 % on tooth flank position.
  * ``virtual_hobbing(worm, wheel, steps=72)`` simulates the actual
    hobbing manufacturing process — 72 (default) discrete boolean cuts at
    angular positions of the worm. Reproduces the conjugate profile to
    sub-tenth-percent accuracy. Takes seconds to minutes depending on
    ``steps``.

Most users want ``WormWheel(throated=True)``. Reach for this helper when
you specifically need the kinematic accuracy — high-load applications,
contact-stress analysis, or comparing to manufacturer specs.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from build123d import BasePartObject

if TYPE_CHECKING:
    from ..facade import WormGear, WormWheel

__all__ = ["virtual_hobbing"]


def virtual_hobbing(
    worm: "WormGear",
    wheel: "WormWheel",
    steps: int = 72,
    *,
    progress_callback=None,
) -> "WormWheel":
    """Generate a wheel using kinematic hobbing simulation.

    Parameters
    ----------
    worm:
        A ``WormGear`` instance — defines the hob geometry. The simulation
        rotates the worm around the wheel and subtracts the swept volume.
    wheel:
        A ``WormWheel`` (typically built with ``throated=False``) whose
        engineering parameters seed the simulation. The geometry of this
        wheel is replaced; only its parameters carry over.
    steps:
        Number of boolean operations per full wheel rotation. Default 72
        (good balance of accuracy vs runtime). Use ``HOBBING_PRESETS``
        for named values: ``"preview"`` (36), ``"balanced"`` (72),
        ``"high"`` (144), ``"ultra"`` (360).
    progress_callback:
        Optional ``(message: str, percent: float) -> None`` callback for
        long-running builds — useful in WASM / browser environments.

    Returns
    -------
    WormWheel
        A new ``WormWheel`` with the kinematically-simulated geometry.
        Engineering parameters (``module``, ``num_teeth``, etc.) match
        the input wheel; the underlying Part is rebuilt.

    Examples
    --------
    >>> from wormgear import WormGear, WormWheel
    >>> from wormgear.advanced import virtual_hobbing
    >>> worm = WormGear(module=2.0, num_starts=1, length=40)
    >>> wheel = WormWheel(module=2.0, num_teeth=30)
    >>> precise_wheel = virtual_hobbing(worm, wheel, steps=72)
    """
    # Lazy import to keep wormgear.advanced module-load cheap.
    from ..core.virtual_hobbing import _VirtualHobbingWheelGeometry
    from ..facade import WormWheel  # local import to avoid circular
    from ..io.loaders import AssemblyParams

    # The standalone-worm case (``WormGear(...)`` without ``ratio=``) leaves
    # ``_assembly_params`` as ``None`` — we can still synthesise a valid
    # AssemblyParams from worm + wheel params because we have both gears in
    # hand. This preserves the natural workflow ``virtual_hobbing(worm, wheel)``
    # even when the worm was built without wheel context.
    assembly_params = worm._assembly_params
    if assembly_params is None:
        wp = worm._params
        whp = wheel._params
        assembly_params = AssemblyParams(
            centre_distance_mm=(wp.pitch_diameter_mm + whp.pitch_diameter_mm) / 2.0,
            pressure_angle_deg=20.0,  # standard; not exposed on WormParams
            backlash_mm=0.0,
            hand=wp.hand,
            ratio=whp.num_teeth // wp.num_starts,
        )

    # ``hob_geometry=None`` lets the simulator build a simpler internal
    # cylindrical hob from the worm parameters. WormGear is cylindrical-only,
    # so this is the correct path. A future extension might detect globoid
    # worms (e.g., from ``make_pair(globoid=True)``) and pass the full part.
    geo = _VirtualHobbingWheelGeometry(
        params=wheel._params,
        worm_params=worm._params,
        assembly_params=assembly_params,
        face_width=wheel.face_width,
        hobbing_steps=steps,
        bore=None,  # features on the source WormWheel are not preserved;
                    # virtual hobbing focuses on tooth geometry.
        profile=wheel.profile,
        hob_geometry=None,
        progress_callback=progress_callback,
    )
    part = geo.build()

    # Wrap as a fresh WormWheel — preserves the type for downstream tooling
    # (check_mesh, etc.) without changing the engineering inputs.
    instance = WormWheel.__new__(WormWheel)
    BasePartObject.__init__(instance, part=part)
    instance._params = wheel._params
    instance._worm_params = worm._params
    instance._assembly_params = assembly_params
    instance.module = wheel.module
    instance.num_teeth = wheel.num_teeth
    instance.face_width = wheel.face_width
    instance.profile = wheel.profile
    instance.throated = False  # virtually-hobbed ≠ throated approximation
    return instance
