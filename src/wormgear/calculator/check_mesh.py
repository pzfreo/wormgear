"""Kinematic mesh-compatibility check for a worm + wheel pair.

This is Phase 1 of the BD-friendly API restructure (#191). It answers the
single question: *given two independently constructed parts, are their
parameters compatible enough to mesh?*

Crucially it is **kinematic only** — pure parameter logic, no build123d,
no geometry, no DIN load capacity analysis. That belongs in
``wormgear.calculator.validation``.

The distinction matters:

  * ``validate_design`` answers "is this a *good* design?" against
    DIN-3975 rules. It runs on a single design produced by the calculator.
  * ``check_mesh`` answers "do these two independently built things engage?"
    It runs on two parts that may never have been calculated together.

When users build via the upcoming ``WormGear`` / ``WormWheel`` facades
they will hand-pick parameters. ``check_mesh`` is the optional safety
net for that path; it does not replace ``validate_design``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from ..enums import Hand
from ..io.loaders import AssemblyParams, WheelParams, WormParams

__all__ = ["MeshReport", "check_mesh"]


# Tolerances — module is a literal float that must match across the pair
# (any nontrivial difference means different gear standards entirely), so
# we use a tight float epsilon. Angle and dimensional checks have looser
# physical tolerances driven by manufacturing reality.
MODULE_MATCH_TOL = 1e-6
ANGLE_COMPLEMENTARITY_TOL_DEG = 0.5
DIMENSIONAL_TOL_MM = 0.05
SELF_LOCKING_LEAD_ANGLE_DEG = 5.0  # below this, worm cannot be back-driven
PROFILE_SHIFT_MATCH_TOL = 0.01


@dataclass(frozen=True)
class MeshReport:
    """Result of a kinematic mesh-compatibility check.

    Attributes
    ----------
    ok:
        ``True`` iff ``errors`` is empty. Convenience flag; the canonical
        verdict is the contents of ``errors``.
    errors:
        Conditions that prevent the pair from meshing. If non-empty, the
        gears as specified cannot engage — geometry would interfere,
        teeth would skip, or axes would not align.
    warnings:
        Conditions that work but are unusual or worth flagging:
        self-locking, uncoordinated profile shift, etc.
    ratio:
        Effective ratio ``wheel.num_teeth / worm.num_starts``. May be
        non-integer; non-integer ratios produce uneven tooth wear and
        emit a warning.
    centre_distance_mm:
        Geometric centre distance computed from pitch diameters:
        ``(worm.pitch_diameter + wheel.pitch_diameter) / 2``. If
        ``AssemblyParams`` was supplied, this is checked against
        ``assembly.centre_distance_mm`` and the assembly value is
        preferred for the report.
    """

    ok: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    ratio: float = 0.0
    centre_distance_mm: float = 0.0


def check_mesh(
    worm: WormParams,
    wheel: WheelParams,
    assembly: Optional[AssemblyParams] = None,
) -> MeshReport:
    """Check whether ``worm`` and ``wheel`` parameters are compatible for meshing.

    Performs kinematic checks only. Does not call build123d, does not
    validate DIN-3975 design rules (use ``validate_design`` for that).

    Parameters
    ----------
    worm, wheel:
        Dimensional parameters for each gear. Either calculator-produced
        Pydantic models or duck-typed equivalents that expose the same
        attributes.
    assembly:
        Optional. If supplied, ``hand`` and ``centre_distance_mm``
        consistency are checked. Without it, those checks are skipped.

    Returns
    -------
    MeshReport
        Carries ``ok``, ``errors``, ``warnings``, and derived facts.
    """
    errors: List[str] = []
    warnings: List[str] = []

    # ---- Errors (must-fix) -------------------------------------------------

    # Module must match exactly. Different modules == different gear systems.
    if abs(worm.module_mm - wheel.module_mm) > MODULE_MATCH_TOL:
        errors.append(
            f"Module mismatch: worm.module_mm={worm.module_mm} but "
            f"wheel.module_mm={wheel.module_mm}. Worm and wheel must share "
            f"the same module to mesh."
        )

    # Hand: for perpendicular-axis worm gears, worm and wheel must share hand.
    # We use assembly.hand as the authoritative reference when available.
    if assembly is not None:
        worm_hand = _hand_value(worm.hand)
        asm_hand = _hand_value(assembly.hand)
        if worm_hand != asm_hand:
            errors.append(
                f"Hand mismatch: worm.hand={worm_hand!r} but "
                f"assembly.hand={asm_hand!r}. Perpendicular-axis worm gears "
                f"require both gears to share the same hand."
            )

    # Lead angle (worm) + helix angle (wheel) must sum to 90° for meshing
    # on perpendicular shafts. The wheel may not expose helix_angle_deg
    # (it's optional metadata); skip if missing.
    if wheel.helix_angle_deg is not None:
        angle_sum = worm.lead_angle_deg + wheel.helix_angle_deg
        if abs(angle_sum - 90.0) > ANGLE_COMPLEMENTARITY_TOL_DEG:
            errors.append(
                f"Lead/helix angles not complementary: "
                f"worm.lead_angle_deg={worm.lead_angle_deg:.3f} + "
                f"wheel.helix_angle_deg={wheel.helix_angle_deg:.3f} = "
                f"{angle_sum:.3f}° (expected ~90°). On perpendicular shafts "
                f"these must sum to 90°."
            )

    # Dimensional compatibility — wheel addendum must not exceed worm
    # dedendum (otherwise wheel tooth tip clashes with worm thread root).
    if wheel.addendum_mm > worm.dedendum_mm + DIMENSIONAL_TOL_MM:
        errors.append(
            f"Wheel addendum ({wheel.addendum_mm:.3f} mm) exceeds worm "
            f"dedendum ({worm.dedendum_mm:.3f} mm); tooth tip would "
            f"interfere with thread root."
        )

    # ---- Warnings (workable but unusual) ----------------------------------

    # Self-locking: lead angle below ~5° (with typical bronze/steel friction
    # coefficients) prevents back-driving. Sometimes intentional, sometimes
    # surprising. Flag either way.
    if worm.lead_angle_deg < SELF_LOCKING_LEAD_ANGLE_DEG:
        warnings.append(
            f"Self-locking: lead angle {worm.lead_angle_deg:.2f}° is below "
            f"~{SELF_LOCKING_LEAD_ANGLE_DEG:.0f}°. The worm cannot be "
            f"back-driven by the wheel under normal friction. Intentional "
            f"for hoists, surprising for general motion control."
        )

    # Profile shift coordination: independent profile shifts are unusual
    # (DIN-3975 designs typically use matched values or shift only the wheel).
    if abs(worm.profile_shift - wheel.profile_shift) > PROFILE_SHIFT_MATCH_TOL:
        warnings.append(
            f"Uncoordinated profile shift: worm={worm.profile_shift:.3f}, "
            f"wheel={wheel.profile_shift:.3f}. Independent shifts are "
            f"unusual; verify both values are intentional."
        )

    # Non-integer effective ratio — wheel teeth not divisible by worm starts.
    ratio = wheel.num_teeth / worm.num_starts
    if ratio != int(ratio):
        warnings.append(
            f"Non-integer effective ratio: wheel.num_teeth={wheel.num_teeth} "
            f"/ worm.num_starts={worm.num_starts} = {ratio:.4f}. This is "
            f"valid but produces uneven tooth wear over time."
        )

    # ---- Derived facts ----------------------------------------------------

    # Geometric centre distance from pitch diameters.
    geometric_cd = (worm.pitch_diameter_mm + wheel.pitch_diameter_mm) / 2.0

    # If assembly is provided, sanity-check the stored centre distance.
    if assembly is not None:
        if abs(assembly.centre_distance_mm - geometric_cd) > DIMENSIONAL_TOL_MM:
            warnings.append(
                f"Centre distance drift: assembly.centre_distance_mm="
                f"{assembly.centre_distance_mm:.3f} differs from geometric "
                f"value {geometric_cd:.3f} (from pitch diameters). May "
                f"indicate a globoid worm with throat reduction, or a "
                f"calculation inconsistency."
            )
        report_cd = assembly.centre_distance_mm
    else:
        report_cd = geometric_cd

    return MeshReport(
        ok=not errors,
        errors=errors,
        warnings=warnings,
        ratio=ratio,
        centre_distance_mm=report_cd,
    )


def _hand_value(hand) -> str:
    """Normalise a Hand enum / string to a lowercase string."""
    if isinstance(hand, Hand):
        return hand.value
    return str(hand).lower()
