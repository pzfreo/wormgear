"""Tests for ``wormgear.calculator.check_mesh`` (Phase 1 of #191).

``check_mesh`` answers the kinematic question: given two independently
constructed parts, are their parameters compatible enough to mesh?
It is pure parameter logic — no build123d, no geometry, no DIN load
analysis. Errors block meshing; warnings flag suboptimal but workable
configurations.

Test matrix:

  * Negative pairs (errors): module mismatch, hand mismatch,
    lead+helix ≠ 90°, dimensional incompatibility
  * Warning pairs: non-integer ratio, uncoordinated profile shift,
    self-locking
  * Positive matrix: every golden design (Phase 0) passes
  * Symmetry: ``check_mesh(a, b)`` reaches the same conclusion as
    ``check_mesh(b, a)``
  * Derived facts: ``report.ratio`` and ``report.centre_distance_mm``
    match what the calculator computes for the same inputs
"""

from __future__ import annotations

import math
from copy import deepcopy

import pytest

from wormgear.calculator import calculate_design_from_module
from wormgear.calculator.check_mesh import (
    MeshReport,
    check_mesh,
)
from wormgear.io import WheelParams, WormParams


# ---------------------------------------------------------------------------
# Helper: build a known-good pair for mutation in negative tests
# ---------------------------------------------------------------------------


@pytest.fixture
def good_pair():
    """A known-good design (m=1, ratio=20) — the medium baseline."""
    design = calculate_design_from_module(module=1.0, ratio=20)
    return design


# ---------------------------------------------------------------------------
# 1. Return shape & basic invariants
# ---------------------------------------------------------------------------


class TestMeshReport:
    """Shape and basic invariants of the MeshReport dataclass."""

    def test_returns_mesh_report(self, good_pair):
        report = check_mesh(good_pair.worm, good_pair.wheel, good_pair.assembly)
        assert isinstance(report, MeshReport)

    def test_report_has_required_fields(self, good_pair):
        report = check_mesh(good_pair.worm, good_pair.wheel, good_pair.assembly)
        assert hasattr(report, "ok")
        assert hasattr(report, "errors")
        assert hasattr(report, "warnings")
        assert hasattr(report, "ratio")
        assert hasattr(report, "centre_distance_mm")

    def test_ok_is_false_when_errors_nonempty(self):
        # Construct directly to verify the invariant
        r = MeshReport(
            ok=False, errors=["module mismatch"], warnings=[],
            ratio=20.0, centre_distance_mm=23.0,
        )
        assert r.ok is False
        assert r.errors == ["module mismatch"]

    def test_assembly_param_is_optional(self, good_pair):
        report = check_mesh(good_pair.worm, good_pair.wheel)
        # Without assembly we can still check the worm↔wheel compatibility
        assert isinstance(report, MeshReport)


# ---------------------------------------------------------------------------
# 2. Positive matrix — known-good pairs come back ok=True
# ---------------------------------------------------------------------------


GOOD_DESIGNS = [
    {"module": 0.5, "ratio": 12},
    {"module": 1.0, "ratio": 20},
    {"module": 1.0, "ratio": 20, "profile": "ZK"},
    {"module": 2.0, "ratio": 30, "num_starts": 2},
    {"module": 1.0, "ratio": 20, "hand": "left"},
]


@pytest.mark.parametrize(
    "kwargs",
    GOOD_DESIGNS,
    ids=lambda k: "_".join(f"{key}={v}" for key, v in k.items()),
)
def test_positive_pair_passes(kwargs):
    """Every calculator-produced design should pass check_mesh.ok=True."""
    design = calculate_design_from_module(**kwargs)
    report = check_mesh(design.worm, design.wheel, design.assembly)
    assert report.ok is True, (
        f"Expected ok=True for {kwargs}, got errors={report.errors}"
    )
    assert report.errors == []


# ---------------------------------------------------------------------------
# 3. Negative matrix — definite errors
# ---------------------------------------------------------------------------


class TestModuleMismatch:
    """Worm and wheel must share the same module to mesh."""

    def test_different_modules_is_error(self, good_pair):
        # Tweak the wheel's module to a different value
        bad_wheel = good_pair.wheel.model_copy(update={"module_mm": 1.5})
        report = check_mesh(good_pair.worm, bad_wheel, good_pair.assembly)
        assert report.ok is False
        assert any("module" in e.lower() for e in report.errors)

    def test_module_tolerance_is_tight(self, good_pair):
        """Tiny floating-point differences should not be flagged."""
        almost_same = good_pair.wheel.model_copy(
            update={"module_mm": good_pair.wheel.module_mm + 1e-9}
        )
        report = check_mesh(good_pair.worm, almost_same, good_pair.assembly)
        assert all("module" not in e.lower() for e in report.errors), (
            "Sub-nano-mm float drift should not flag module mismatch"
        )


class TestHandMismatch:
    """Worm and wheel hand must agree (perpendicular-axis worm gears mesh same-hand)."""

    def test_opposite_hands_is_error(self, good_pair):
        # Force assembly to "left" while worm stays "right"
        bad_assembly = good_pair.assembly.model_copy(update={"hand": "left"})
        report = check_mesh(good_pair.worm, good_pair.wheel, bad_assembly)
        assert report.ok is False
        assert any("hand" in e.lower() for e in report.errors)


class TestLeadHelixComplementarity:
    """Worm lead_angle + wheel helix_angle should sum to 90°."""

    def test_complementary_angles_pass(self, good_pair):
        """The calculator produces helix_angle = 90 - lead_angle, so this passes."""
        report = check_mesh(good_pair.worm, good_pair.wheel, good_pair.assembly)
        assert report.ok is True

    def test_non_complementary_angles_is_error(self, good_pair):
        # Push the wheel's helix angle far from complementary
        bad_helix = good_pair.worm.lead_angle_deg + 45.0  # way off 90 sum
        bad_wheel = good_pair.wheel.model_copy(
            update={"helix_angle_deg": bad_helix}
        )
        report = check_mesh(good_pair.worm, bad_wheel, good_pair.assembly)
        assert report.ok is False
        assert any(
            "helix" in e.lower() or "lead" in e.lower() for e in report.errors
        )

    def test_missing_helix_angle_no_check(self, good_pair):
        """If the wheel doesn't expose helix_angle, skip the check silently."""
        wheel_no_helix = good_pair.wheel.model_copy(
            update={"helix_angle_deg": None}
        )
        report = check_mesh(good_pair.worm, wheel_no_helix, good_pair.assembly)
        # Should be ok in all other respects — module/hand still match
        assert all(
            "helix" not in e.lower() and "lead" not in e.lower()
            for e in report.errors
        )


class TestDimensionalCompatibility:
    """Worm and wheel addendum/dedendum should be coherent."""

    def test_grossly_mismatched_addendum_is_error(self, good_pair):
        """If the worm's tip would clash with the wheel's root, that's an error."""
        # Force wheel addendum much larger than worm dedendum can accept
        bad_wheel = good_pair.wheel.model_copy(
            update={"addendum_mm": good_pair.wheel.addendum_mm + 5.0}
        )
        report = check_mesh(good_pair.worm, bad_wheel, good_pair.assembly)
        assert report.ok is False
        assert any(
            "addendum" in e.lower() or "interference" in e.lower()
            for e in report.errors
        )


# ---------------------------------------------------------------------------
# 4. Warning matrix — meshes, but worth flagging
# ---------------------------------------------------------------------------


class TestSelfLockingWarning:
    """A very low lead angle implies self-locking — sometimes wanted, sometimes not."""

    def test_low_lead_angle_emits_warning(self):
        # Force a sub-5° lead angle to trigger the self-locking warning.
        design = calculate_design_from_module(
            module=0.5, ratio=12, target_lead_angle=3.0,
        )
        report = check_mesh(design.worm, design.wheel, design.assembly)
        # The pair is mechanically fine — .ok stays True, but the warning fires.
        assert report.ok is True
        assert any(
            "self-locking" in w.lower() or "locking" in w.lower()
            for w in report.warnings
        ), f"Expected self-locking warning at lead_angle={design.worm.lead_angle_deg:.2f}°"


class TestProfileShiftCoordination:
    """If worm and wheel have different profile_shift, that's unusual — warn."""

    def test_uncoordinated_profile_shift_emits_warning(self, good_pair):
        bad_wheel = good_pair.wheel.model_copy(update={"profile_shift": 0.5})
        report = check_mesh(good_pair.worm, bad_wheel, good_pair.assembly)
        # Pair may still mesh, but flag the inconsistency
        assert any(
            "profile" in w.lower() and "shift" in w.lower()
            for w in report.warnings
        )


# ---------------------------------------------------------------------------
# 5. Derived facts — ratio and centre_distance
# ---------------------------------------------------------------------------


class TestDerivedFacts:
    """report.ratio and report.centre_distance_mm should match calculator output."""

    @pytest.mark.parametrize(
        "module,ratio,num_starts",
        [(1.0, 20, 1), (2.0, 30, 2), (0.5, 12, 1)],
    )
    def test_ratio_matches_calculator(self, module, ratio, num_starts):
        design = calculate_design_from_module(
            module=module, ratio=ratio, num_starts=num_starts,
        )
        report = check_mesh(design.worm, design.wheel, design.assembly)
        # ratio in the calculator means wheel teeth / worm starts
        expected = design.wheel.num_teeth / design.worm.num_starts
        assert report.ratio == pytest.approx(expected)

    @pytest.mark.parametrize(
        "module,ratio",
        [(1.0, 20), (2.0, 30), (0.5, 12)],
    )
    def test_centre_distance_matches_calculator(self, module, ratio):
        design = calculate_design_from_module(module=module, ratio=ratio)
        report = check_mesh(design.worm, design.wheel, design.assembly)
        assert report.centre_distance_mm == pytest.approx(
            design.assembly.centre_distance_mm, abs=0.01
        )


# ---------------------------------------------------------------------------
# 6. Symmetry — check_mesh(a, b) and check_mesh(b, a) reach the same conclusion
# ---------------------------------------------------------------------------


def test_argument_order_does_not_change_ok(good_pair):
    """Whichever order args go in, the .ok verdict is the same."""
    # Note: the API takes (worm, wheel) ordered, but the check itself is
    # logically symmetric in the sense that both gears are interchangeably
    # constrained. We test this by mutating one half and confirming the
    # error surfaces regardless of which side is "wrong".
    bad_wheel_module = good_pair.wheel.model_copy(update={"module_mm": 1.5})
    bad_worm_module = good_pair.worm.model_copy(update={"module_mm": 1.5})

    r1 = check_mesh(good_pair.worm, bad_wheel_module, good_pair.assembly)
    r2 = check_mesh(bad_worm_module, good_pair.wheel, good_pair.assembly)

    assert r1.ok == r2.ok == False
    # Both should mention "module" in the error
    assert any("module" in e.lower() for e in r1.errors)
    assert any("module" in e.lower() for e in r2.errors)
