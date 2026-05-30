"""Geometry-realizes-spec tests (#230).

These exercise the public geometry-validation API
(:func:`wormgear.check_worm_geometry` / :func:`wormgear.check_wheel_geometry`
and the ``.validate()`` facade methods) — the same entry points a customer
uses to confirm a built model matches its calculation. Dogfooding the public
API here means the suite and the shipped feature can never drift apart.

This answers *"does the geometry realise the calculation?"* — distinct from
*"is the calculation correct per DIN-3975?"* (#229). It is also distinct from:

  * ``test_golden_volumes`` — pins volume/bbox/face-count against a recorded
    baseline; catches drift but a wrong baseline passes (how #224 and #231 hid).
  * ``test_check_mesh`` — kinematic pair check, not per-part dimensions.

Every assertion compares the measured solid to the spec it was built from, so
it is independent of any recorded baseline — it would have caught #231 (wheel
root cut 0.3 mm deep) directly.

Scope and known gaps are documented on ``wormgear.core.validate_geometry``.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from wormgear import WormGear, WormWheel, check_wheel_geometry, check_worm_geometry

pytestmark = pytest.mark.slow


# ---------------------------------------------------------------------------
# Design matrix — cylindrical worms + helical/throated wheels
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WormSpec:
    module: float
    num_starts: int
    length: float
    hand: str = "right"
    profile: str = "ZA"


@dataclass(frozen=True)
class WheelSpec:
    module: float
    num_teeth: int
    face_width: float
    profile: str = "ZA"
    throated: bool = False


WORM_SPECS: dict[str, WormSpec] = {
    "m1_1start_rh": WormSpec(module=1.0, num_starts=1, length=20.0),
    "m2_2start_rh": WormSpec(module=2.0, num_starts=2, length=30.0),
    "m1_1start_lh": WormSpec(module=1.0, num_starts=1, length=20.0, hand="left"),
    "m1_1start_zk": WormSpec(module=1.0, num_starts=1, length=20.0, profile="ZK"),
    "m05_1start_rh": WormSpec(module=0.5, num_starts=1, length=8.0),
}

WHEEL_SPECS: dict[str, WheelSpec] = {
    "m1_z20_za": WheelSpec(module=1.0, num_teeth=20, face_width=6.0),
    "m1_z20_zk": WheelSpec(module=1.0, num_teeth=20, face_width=6.0, profile="ZK"),
    "m2_z60_za": WheelSpec(module=2.0, num_teeth=60, face_width=10.0),
    "m05_z12_za": WheelSpec(module=0.5, num_teeth=12, face_width=2.5),
    "m1_z20_throated": WheelSpec(module=1.0, num_teeth=20, face_width=6.0, throated=True),
}


def _build_worm(spec: WormSpec) -> WormGear:
    return WormGear(
        module=spec.module,
        num_starts=spec.num_starts,
        length=spec.length,
        target_lead_angle=7.0,
        hand=spec.hand,
        profile=spec.profile,
    )


def _build_wheel(spec: WheelSpec) -> WormWheel:
    return WormWheel(
        module=spec.module,
        num_teeth=spec.num_teeth,
        face_width=spec.face_width,
        worm_num_starts=1,
        worm_target_lead_angle=7.0,
        profile=spec.profile,
        throated=spec.throated,
    )


def _check(report, expected_checks: set[str]) -> None:
    """Assert the report passed and contains exactly the expected dimensions."""
    assert report.ok, f"{report.kind} validation failed:\n{report}"
    names = {c.name for c in report.checks}
    assert names == expected_checks, f"unexpected checks {names} != {expected_checks}"
    assert all(c.ok for c in report.checks)


# ---------------------------------------------------------------------------
# Worm: tip + root + length match the spec it was built from
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", list(WORM_SPECS))
def test_worm_realises_spec(name: str) -> None:
    spec = WORM_SPECS[name]
    worm = _build_worm(spec)
    # Both the free function and the .validate() convenience are exercised.
    report = check_worm_geometry(worm, worm._params, length=spec.length)
    _check(report, {"tip_diameter", "root_diameter", "length"})
    assert worm.validate().ok


# ---------------------------------------------------------------------------
# Wheel: tip (all), root (non-throated) match the spec; throated skips root
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name", [n for n, s in WHEEL_SPECS.items() if not s.throated]
)
def test_wheel_realises_spec(name: str) -> None:
    wheel = _build_wheel(WHEEL_SPECS[name])
    report = check_wheel_geometry(wheel, wheel._params)
    _check(report, {"tip_diameter", "root_diameter"})
    assert wheel.validate().ok


def test_throated_wheel_checks_tip_only() -> None:
    wheel = _build_wheel(WHEEL_SPECS["m1_z20_throated"])
    report = wheel.validate()
    _check(report, {"tip_diameter"})
    assert any("throated" in w for w in report.warnings)


def test_bored_wheel_skips_root_check() -> None:
    # A bore makes the minimum vertex radius the bore wall, not the tooth root,
    # so the root check must be skipped (and noted) rather than misread the bore
    # and falsely fail. Tip is unaffected by the bore and is still checked.
    from wormgear.core import BoreFeature

    wheel = WormWheel(
        module=2.0, num_teeth=30, worm_num_starts=1, bore=BoreFeature(diameter=8.0)
    )
    report = wheel.validate()
    names = {c.name for c in report.checks}
    assert names == {"tip_diameter"}
    assert report.ok
    assert any("bore" in w for w in report.warnings)


def test_degenerate_worm_topology_skips_root_check() -> None:
    # A swept worm thread's discrete topology is length-dependent: at certain
    # lengths the trim leaves only tip vertices, with no root vertices, so the
    # minimum radius is the tip. The root check must then be skipped (and noted)
    # rather than mistake the tip for the root and falsely fail. m2 / 1-start /
    # length 30 is a known such config (only 2 vertices, both at the tip).
    worm = WormGear(module=2.0, num_starts=1, length=30.0)
    report = worm.validate()
    names = {c.name for c in report.checks}
    assert "root_diameter" not in names
    assert {"tip_diameter", "length"} <= names
    assert report.ok
    assert any("did not expose the tooth root" in w for w in report.warnings)


# ---------------------------------------------------------------------------
# The validator must FAIL a part that does not match its spec (not just pass
# good ones). Pinned to the #231 over-cut direction as the motivating bug.
# ---------------------------------------------------------------------------


def test_validator_fails_on_wrong_tip_diameter() -> None:
    wheel = _build_wheel(WHEEL_SPECS["m1_z20_za"])

    class WrongSpec:
        # 0.5 mm larger than reality — well outside the 0.02 mm tip tolerance.
        tip_diameter_mm = wheel._params.tip_diameter_mm + 0.5
        root_diameter_mm = wheel._params.root_diameter_mm

    report = check_wheel_geometry(wheel, WrongSpec())
    assert not report.ok
    assert any("tip_diameter" in e for e in report.errors)


def test_validator_fails_on_overcut_root() -> None:
    # Simulate the #231 regression: a spec whose root is shallower than the
    # geometry (i.e. the geometry is cut deeper) must fail.
    wheel = _build_wheel(WHEEL_SPECS["m1_z20_za"])

    class OvercutSpec:
        tip_diameter_mm = wheel._params.tip_diameter_mm
        # Pretend nominal root is 0.3 mm larger (shallower) than what was cut.
        root_diameter_mm = wheel._params.root_diameter_mm + 0.3

    report = check_wheel_geometry(wheel, OvercutSpec())
    assert not report.ok
    assert any("root_diameter" in e for e in report.errors)
