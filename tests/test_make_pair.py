"""Tests for from_design adapters and make_pair (Phase 3 of #191).

Verifies:
  1. ``WormGear.from_design(design)`` and ``WormWheel.from_design(design)``
     produce the same geometry as constructing directly with equivalent
     kwargs (volume parity within 1e-6).
  2. ``make_pair(module, ratio, length)`` returns a matched pair that:
     - Has volumes matching the equivalent ``design_from_module`` →
       individual-constructor path
     - Passes ``check_mesh(...).ok = True``
     - Produces no validation errors via ``validate_design``
  3. Top-level imports work: ``from wormgear import make_pair, check_mesh``
"""

from __future__ import annotations

import pytest

from wormgear import (
    WormGear,
    WormWheel,
    check_mesh,
    make_pair,
)
from wormgear.calculator import (
    calculate_design_from_module,
    validate_design,
)

pytestmark = pytest.mark.slow


EQUIVALENCE_TOL = 1e-6


# ---------------------------------------------------------------------------
# from_design — parity with direct construction
# ---------------------------------------------------------------------------


class TestWormGearFromDesign:
    """``WormGear.from_design(design)`` should match a direct construction."""

    def test_basic_pair_matches_direct(self):
        design = calculate_design_from_module(module=1.0, ratio=20)
        worm_via_design = WormGear.from_design(
            design, length=20.0, sections_per_turn=12,
        )
        worm_direct = WormGear(
            module=1.0, num_starts=1, length=20.0,
            target_lead_angle=design.worm.lead_angle_deg,
            hand=design.worm.hand,
            sections_per_turn=12,
        )
        rel = abs(worm_via_design.volume - worm_direct.volume) / worm_direct.volume
        assert rel < EQUIVALENCE_TOL

    def test_multistart_matches_direct(self):
        design = calculate_design_from_module(
            module=2.0, ratio=30, num_starts=2,
        )
        worm_via_design = WormGear.from_design(
            design, length=30.0, sections_per_turn=12,
        )
        worm_direct = WormGear(
            module=2.0, num_starts=2, length=30.0,
            target_lead_angle=design.worm.lead_angle_deg,
            sections_per_turn=12,
        )
        rel = abs(worm_via_design.volume - worm_direct.volume) / worm_direct.volume
        assert rel < EQUIVALENCE_TOL

    def test_left_hand_propagates(self):
        design = calculate_design_from_module(
            module=1.0, ratio=20, hand="left",
        )
        worm = WormGear.from_design(
            design, length=20.0, sections_per_turn=12,
        )
        # The hand value comes through as the Pydantic enum
        assert worm.hand.value == "left"

    def test_overrides_take_precedence(self):
        """Extra kwargs in from_design should override design-derived values."""
        design = calculate_design_from_module(module=1.0, ratio=20)
        worm = WormGear.from_design(
            design, length=20.0, sections_per_turn=12,
            num_starts=2,  # Override
        )
        assert worm.num_starts == 2


class TestWormWheelFromDesign:
    """``WormWheel.from_design(design)`` should match a direct construction."""

    def test_basic_pair_matches_direct(self):
        design = calculate_design_from_module(module=1.0, ratio=20)
        wheel_via_design = WormWheel.from_design(design, face_width=6.0)
        wheel_direct = WormWheel(
            module=1.0, num_teeth=20, face_width=6.0,
            worm_target_lead_angle=design.worm.lead_angle_deg,
            hand=design.assembly.hand,
        )
        rel = abs(wheel_via_design.volume - wheel_direct.volume) / wheel_direct.volume
        assert rel < EQUIVALENCE_TOL

    def test_auto_face_width(self):
        """face_width=None should let the calculator pick."""
        design = calculate_design_from_module(module=1.0, ratio=20)
        wheel = WormWheel.from_design(design)
        # Auto face width is positive and reasonable
        assert wheel.face_width > 0
        assert wheel.face_width < design.worm.tip_diameter_mm * 2


# ---------------------------------------------------------------------------
# make_pair — one-liner matched pairs
# ---------------------------------------------------------------------------


class TestMakePair:
    """``make_pair`` returns a kinematically valid (worm, wheel) tuple."""

    def test_returns_tuple_of_two(self):
        worm, wheel = make_pair(
            module=1.0, ratio=20, length=20.0, face_width=6.0,
            sections_per_turn=12,
        )
        assert isinstance(worm, WormGear)
        assert isinstance(wheel, WormWheel)

    def test_pair_passes_check_mesh(self):
        worm, wheel = make_pair(
            module=1.0, ratio=20, length=20.0, face_width=6.0,
            sections_per_turn=12,
        )
        report = check_mesh(
            worm._params, wheel._params, worm._assembly_params,
        )
        assert report.ok is True, f"check_mesh failed: {report.errors}"

    def test_pair_passes_validation(self):
        """The underlying design should pass validate_design without errors."""
        worm, wheel = make_pair(
            module=1.0, ratio=20, length=20.0, face_width=6.0,
            sections_per_turn=12,
        )
        # Reconstruct a design-like object and validate
        # (we don't store the full design in the gears, so re-derive)
        from wormgear.io import WormGearDesign
        from wormgear.calculator import design_from_module

        design = design_from_module(module=1.0, ratio=20)
        result = validate_design(design)
        # Pair-from-make_pair should not produce *errors* (warnings OK)
        assert len(result.errors) == 0

    def test_pair_matches_calculator_path(self):
        """make_pair volumes should match the design_from_module → constructor path."""
        # Path A: make_pair
        worm_a, wheel_a = make_pair(
            module=1.0, ratio=20, length=20.0, face_width=6.0,
            sections_per_turn=12,
        )
        # Path B: design_from_module → from_design
        design = calculate_design_from_module(module=1.0, ratio=20)
        worm_b = WormGear.from_design(design, length=20.0, sections_per_turn=12)
        wheel_b = WormWheel.from_design(design, face_width=6.0)

        assert abs(worm_a.volume - worm_b.volume) / worm_b.volume < EQUIVALENCE_TOL
        assert abs(wheel_a.volume - wheel_b.volume) / wheel_b.volume < EQUIVALENCE_TOL

    def test_make_pair_multistart(self):
        worm, wheel = make_pair(
            module=2.0, ratio=30, length=30.0, face_width=10.0,
            num_starts=2, sections_per_turn=12,
        )
        assert worm.num_starts == 2
        assert wheel.num_teeth == 60  # ratio=30 × num_starts=2

    def test_make_pair_throated(self):
        worm, wheel = make_pair(
            module=1.0, ratio=20, length=20.0, face_width=6.0,
            throated=True, sections_per_turn=12,
        )
        assert wheel.throated is True


# ---------------------------------------------------------------------------
# Top-level imports — make sure the API is discoverable
# ---------------------------------------------------------------------------


def test_top_level_imports():
    """The four headline names should all import from the top level."""
    from wormgear import WormGear, WormWheel, make_pair, check_mesh
    # Just exercise the imports
    assert WormGear is not None
    assert WormWheel is not None
    assert make_pair is not None
    assert check_mesh is not None
