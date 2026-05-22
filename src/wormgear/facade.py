"""Build123d-friendly facade for worm gear construction (Phase 2 of #191).

``WormGear`` and ``WormWheel`` are ``BasePartObject`` subclasses that take
**engineering parameters** as input and return a ``build123d.Part`` you can
immediately compose, ``show()``, or ``export_step()``.

This is the on-ramp for the build123d ecosystem (gggears, bd_warehouse,
etc.) — three lines instead of the four-step calculator → params →
geometry → build dance:

    >>> from wormgear import WormGear, WormWheel
    >>> worm = WormGear(module=2.0, num_starts=1, length=40)
    >>> wheel = WormWheel(module=2.0, num_teeth=30)

Internally they delegate to the existing ``WormGeometry`` /
``WheelGeometry`` classes — geometric behavior is identical, pinned by
the Phase 0 golden tests. The classes do not provide an ``API`` that the
calculator's full param-set lacks; they are an ergonomic re-shaping of
the existing surface.

Layering: the facade lives in ``wormgear/`` (not ``wormgear/core/``) and
lazy-imports both calculator and core inside ``__init__``. The calculator
runs the same DIN-3975 derivation it always does; the user just doesn't
see the Pydantic models unless they want to.
"""

from __future__ import annotations

from typing import Optional, Union

from build123d import Align, BasePartObject, Mode, RotationLike

from .enums import Hand, WormProfile

__all__ = ["WormGear", "WormWheel", "make_pair"]


def _design_profile(design) -> str:
    """Extract profile from design.manufacturing if present, else ``"ZA"``."""
    mfg = getattr(design, "manufacturing", None)
    if mfg is not None:
        profile = getattr(mfg, "profile", None)
        if profile is not None:
            return profile.value if hasattr(profile, "value") else str(profile)
    return "ZA"


# ---------------------------------------------------------------------------
# WormGear — the worm (driving gear)
# ---------------------------------------------------------------------------


class WormGear(BasePartObject):
    """A worm (the driving gear) as a build123d ``Part``.

    Parameters
    ----------
    module:
        Axial module in mm. Standard ISO 54 values: 0.5, 1.0, 1.5, 2.0, ...
    num_starts:
        Number of thread starts (typically 1-4). Default 1.
    length:
        Worm length in mm.
    target_lead_angle:
        Target lead angle in degrees; controls pitch diameter. Default 7°
        (a balanced compromise between efficiency and back-driving).
    hand:
        Thread hand, ``"right"`` or ``"left"`` (or ``Hand`` enum). Default
        ``"right"``.
    profile:
        Tooth profile per DIN-3975: ``"ZA"`` (straight flanks, CNC default)
        or ``"ZK"`` (slightly convex flanks, better for 3D printing).
        Default ``"ZA"``.
    pressure_angle:
        Pressure angle in degrees. Default 20.
    backlash:
        Backlash allowance in mm. Default 0.
    profile_shift:
        Profile shift coefficient. Default 0.
    sections_per_turn:
        Helical sweep resolution. Default 36 (matches ``WormGeometry``).
    bore, keyway, ddcut, set_screw:
        Optional feature objects (see ``wormgear.core.features``).
    rotation, align, mode:
        Standard build123d Part placement parameters.
    """

    def __init__(
        self,
        module: float,
        num_starts: int = 1,
        length: float = 30.0,
        *,
        target_lead_angle: float = 7.0,
        hand: Union[Hand, str] = "right",
        profile: Union[WormProfile, str] = "ZA",
        pressure_angle: float = 20.0,
        backlash: float = 0.0,
        profile_shift: float = 0.0,
        sections_per_turn: int = 36,
        bore=None,
        keyway=None,
        ddcut=None,
        set_screw=None,
        rotation: RotationLike = (0, 0, 0),
        align: Optional[Align] = None,
        mode: Mode = Mode.ADD,
    ):
        # Lazy imports — keeps the facade module load-time clean and avoids
        # build123d/Pydantic loading until the user actually constructs a part.
        from .calculator import design_from_module
        from .core.worm import WormGeometry

        # The calculator wants a ratio context. WormGear alone doesn't care
        # about wheel teeth, but the calculator's worm derivation does depend
        # on num_starts + target_lead_angle to compute pitch diameter — none
        # of which involves the wheel side. We pass a placeholder ratio of 10
        # solely to satisfy the function signature; the worm dimensions are
        # identical for any ratio.
        design = design_from_module(
            module=module,
            ratio=10,  # placeholder — worm dims don't depend on wheel teeth
            num_starts=num_starts,
            target_lead_angle=target_lead_angle,
            hand=hand,
            profile=profile,
            pressure_angle=pressure_angle,
            backlash=backlash,
            profile_shift=profile_shift,
        )

        geo = WormGeometry(
            params=design.worm,
            assembly_params=design.assembly,
            length=length,
            sections_per_turn=sections_per_turn,
            profile=profile,
            bore=bore,
            keyway=keyway,
            ddcut=ddcut,
            set_screw=set_screw,
        )
        part = geo.build()

        # Stash the engineering inputs as attributes so downstream code
        # (notably check_mesh and Phase 3 from_design) can introspect.
        self._params = design.worm
        self._assembly_params = design.assembly
        self.module = module
        self.num_starts = num_starts
        self.length = length
        self.hand = design.worm.hand
        self.profile = profile.upper() if isinstance(profile, str) else profile.value

        super().__init__(part=part, rotation=rotation, align=align, mode=mode)

    @classmethod
    def from_design(cls, design, length: float, **overrides) -> "WormGear":
        """Build a ``WormGear`` from a calculator-produced ``WormGearDesign``.

        Useful when you already have a ``WormGearDesign`` in hand — loaded
        from JSON, produced by ``design_from_module``, etc. The classmethod
        unpacks the relevant fields into the regular ``__init__`` so the
        result is bit-identical to constructing directly.

        Parameters
        ----------
        design:
            A ``WormGearDesign`` (calculator output).
        length:
            Worm length in mm. Not stored in the design — caller decides.
        **overrides:
            Any ``WormGear.__init__`` parameter can be overridden here.

        Returns
        -------
        WormGear
        """
        kwargs = dict(
            module=design.worm.module_mm,
            num_starts=design.worm.num_starts,
            length=length,
            target_lead_angle=design.worm.lead_angle_deg,
            hand=design.worm.hand,
            profile=_design_profile(design),
            pressure_angle=design.assembly.pressure_angle_deg,
            backlash=design.assembly.backlash_mm,
            profile_shift=design.worm.profile_shift,
        )
        kwargs.update(overrides)
        return cls(**kwargs)


# ---------------------------------------------------------------------------
# WormWheel — the driven gear
# ---------------------------------------------------------------------------


class WormWheel(BasePartObject):
    """A worm wheel (the driven gear) as a build123d ``Part``.

    Parameters
    ----------
    module:
        Axial module in mm. Must match the worm's module.
    num_teeth:
        Number of teeth on the wheel.
    face_width:
        Wheel face width in mm. ``None`` (default) auto-calculates from worm
        tip diameter following the calculator's recommendation.
    profile:
        Tooth profile, ``"ZA"`` or ``"ZK"``. Default ``"ZA"``.
    worm_num_starts:
        Worm starts (controls helix angle). Default 1.
    worm_target_lead_angle:
        Worm lead angle in degrees (controls helix angle). Default 7°.
        ``helix_angle = 90 - worm_lead_angle`` for perpendicular meshing.
    hand:
        Thread hand of the mating worm (must match for perpendicular
        meshing). Default ``"right"``.
    throated:
        If True, generate a throated wheel for accurate worm engagement.
        Default False (simple helical wheel).
    pressure_angle, backlash, profile_shift:
        Standard gear parameters. Defaults match calculator.
    bore, keyway, ddcut, set_screw:
        Optional features.
    rotation, align, mode:
        build123d placement.
    """

    def __init__(
        self,
        module: float,
        num_teeth: int,
        face_width: Optional[float] = None,
        *,
        profile: Union[WormProfile, str] = "ZA",
        worm_num_starts: int = 1,
        worm_target_lead_angle: float = 7.0,
        hand: Union[Hand, str] = "right",
        throated: bool = False,
        pressure_angle: float = 20.0,
        backlash: float = 0.0,
        profile_shift: float = 0.0,
        bore=None,
        keyway=None,
        ddcut=None,
        set_screw=None,
        rotation: RotationLike = (0, 0, 0),
        align: Optional[Align] = None,
        mode: Mode = Mode.ADD,
    ):
        from .calculator import design_from_module
        from .core.wheel import WheelGeometry

        # The wheel needs full worm + assembly context for derivation.
        # We derive an effective ratio from num_teeth and worm_num_starts.
        ratio = num_teeth // worm_num_starts
        # Sanity: if num_teeth isn't divisible by num_starts, design's
        # wheel.num_teeth may differ. Patch by re-emitting wheel params.
        design = design_from_module(
            module=module,
            ratio=ratio,
            num_starts=worm_num_starts,
            target_lead_angle=worm_target_lead_angle,
            hand=hand,
            profile=profile,
            pressure_angle=pressure_angle,
            backlash=backlash,
            profile_shift=profile_shift,
        )

        # Defensive: if the calculator's derived num_teeth differs from
        # what the user asked for, override.
        if design.wheel.num_teeth != num_teeth:
            design.wheel = design.wheel.model_copy(
                update={
                    "num_teeth": num_teeth,
                    "pitch_diameter_mm": module * num_teeth,
                    "tip_diameter_mm": module * num_teeth + 2 * design.wheel.addendum_mm,
                    "root_diameter_mm": module * num_teeth - 2 * design.wheel.dedendum_mm,
                }
            )

        geo = WheelGeometry(
            params=design.wheel,
            worm_params=design.worm,
            assembly_params=design.assembly,
            face_width=face_width,
            profile=profile,
            throated=throated,
            bore=bore,
            keyway=keyway,
            ddcut=ddcut,
            set_screw=set_screw,
        )
        part = geo.build()

        # Stash params for check_mesh / from_design introspection
        self._params = design.wheel
        self._worm_params = design.worm
        self._assembly_params = design.assembly
        self.module = module
        self.num_teeth = num_teeth
        self.face_width = geo.face_width  # auto-calc may differ from user input
        self.profile = profile.upper() if isinstance(profile, str) else profile.value
        self.throated = throated

        super().__init__(part=part, rotation=rotation, align=align, mode=mode)

    @classmethod
    def from_design(
        cls,
        design,
        face_width: Optional[float] = None,
        **overrides,
    ) -> "WormWheel":
        """Build a ``WormWheel`` from a calculator-produced ``WormGearDesign``.

        Mirror of :meth:`WormGear.from_design`. Extracts the relevant worm
        and wheel fields and passes them into the regular constructor.

        Parameters
        ----------
        design:
            A ``WormGearDesign`` (calculator output).
        face_width:
            Wheel face width in mm. ``None`` = auto from worm tip diameter.
        **overrides:
            Any ``WormWheel.__init__`` parameter can be overridden here.

        Returns
        -------
        WormWheel
        """
        kwargs = dict(
            module=design.wheel.module_mm,
            num_teeth=design.wheel.num_teeth,
            face_width=face_width,
            profile=_design_profile(design),
            worm_num_starts=design.worm.num_starts,
            worm_target_lead_angle=design.worm.lead_angle_deg,
            hand=design.assembly.hand,
            pressure_angle=design.assembly.pressure_angle_deg,
            backlash=design.assembly.backlash_mm,
            profile_shift=design.wheel.profile_shift,
        )
        kwargs.update(overrides)
        return cls(**kwargs)


# ---------------------------------------------------------------------------
# make_pair — top-level convenience for the "I don't want to think" path
# ---------------------------------------------------------------------------


def make_pair(
    module: float,
    ratio: int,
    length: float,
    face_width: Optional[float] = None,
    *,
    num_starts: int = 1,
    target_lead_angle: float = 7.0,
    hand: Union[Hand, str] = "right",
    profile: Union[WormProfile, str] = "ZA",
    pressure_angle: float = 20.0,
    backlash: float = 0.0,
    profile_shift: float = 0.0,
    throated: bool = False,
    sections_per_turn: int = 36,
) -> "tuple[WormGear, WormWheel]":
    """Build a matched ``(WormGear, WormWheel)`` pair from engineering parameters.

    The one-liner alternative to constructing each gear separately. The
    pair is guaranteed compatible (passes ``check_mesh``) because it goes
    through the same calculator path that the individual constructors do.

    Parameters
    ----------
    module:
        Gear module in mm. Shared by both gears.
    ratio:
        Gear ratio (typically ``wheel_teeth / worm_starts``).
    length:
        Worm length in mm.
    face_width:
        Wheel face width. ``None`` = auto.
    num_starts, target_lead_angle, hand, profile, pressure_angle,
    backlash, profile_shift, throated, sections_per_turn:
        Standard kwargs forwarded to ``WormGear`` and ``WormWheel``.

    Returns
    -------
    (WormGear, WormWheel)
        Matched pair, guaranteed kinematically compatible.

    Examples
    --------
    >>> from wormgear import make_pair, check_mesh
    >>> worm, wheel = make_pair(module=2.0, ratio=30, length=40.0)
    >>> assert check_mesh(worm._params, wheel._params, worm._assembly_params).ok
    """
    from .calculator import design_from_module

    design = design_from_module(
        module=module,
        ratio=ratio,
        num_starts=num_starts,
        target_lead_angle=target_lead_angle,
        hand=hand,
        profile=profile,
        pressure_angle=pressure_angle,
        backlash=backlash,
        profile_shift=profile_shift,
    )

    worm = WormGear.from_design(
        design,
        length=length,
        sections_per_turn=sections_per_turn,
    )
    wheel = WormWheel.from_design(
        design,
        face_width=face_width,
        throated=throated,
    )
    return worm, wheel
