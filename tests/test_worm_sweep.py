"""
Sweep vs loft comparison tests for worm geometry.

Phase 3 of the sweep implementation plan: verify that sweep-generated
worms match loft-generated worms within tolerance, across a range of
parameters (modules, starts, hands, profiles).

Marked slow because they build 3D geometry via build123d.
"""

import math
import time
import pytest
from wormgear import WormGeometry
from wormgear.calculator.core import design_from_module
from tests.helpers.geometry_sampling import (
    measure_radial_profile,
    measure_lead,
)

pytestmark = pytest.mark.slow


def _build_worm(generation_method, module=2.0, ratio=30, num_starts=1,
                hand="right", profile="ZA", length=40.0, sections_per_turn=36):
    """Build a worm with the given generation method."""
    design = design_from_module(module=module, ratio=ratio,
                                num_starts=num_starts, hand=hand,
                                profile=profile)
    geo = WormGeometry(
        params=design.worm,
        assembly_params=design.assembly,
        length=length,
        sections_per_turn=sections_per_turn,
        profile=profile,
        generation_method=generation_method,
    )
    solid = geo.build()
    return solid, design


class TestSweepProducesValidSolid:
    """Basic validity tests for sweep-generated worms."""

    def test_sweep_valid_solid(self):
        solid, _ = _build_worm("sweep")
        assert solid.volume > 0, "Sweep worm has zero volume"

    def test_sweep_watertight(self):
        solid, _ = _build_worm("sweep")
        assert solid.is_valid, "Sweep worm is not watertight"

    def test_sweep_volume_positive(self):
        solid, design = _build_worm("sweep")
        root_r = design.worm.root_diameter_mm / 2
        tip_r = design.worm.tip_diameter_mm / 2
        min_vol = math.pi * root_r ** 2 * 40.0
        max_vol = math.pi * tip_r ** 2 * 40.0
        assert solid.volume > min_vol * 0.8, \
            f"Volume {solid.volume:.1f} too small (min={min_vol * 0.8:.1f})"
        assert solid.volume < max_vol * 1.2, \
            f"Volume {solid.volume:.1f} too large (max={max_vol * 1.2:.1f})"

    def test_sweep_left_hand(self):
        solid, _ = _build_worm("sweep", hand="left")
        assert solid.volume > 0

    def test_sweep_zk_profile(self):
        solid, _ = _build_worm("sweep", profile="ZK")
        assert solid.volume > 0


class TestSweepMatchesLoft:
    """Compare sweep output against loft reference (sections_per_turn=72)."""

    @pytest.fixture
    def loft_reference(self):
        """High-quality loft as the reference."""
        solid, design = _build_worm("loft", sections_per_turn=72)
        return solid, design

    @pytest.fixture
    def sweep_result(self):
        solid, design = _build_worm("sweep")
        return solid, design

    def test_volume_within_tolerance(self, loft_reference, sweep_result):
        loft_solid, _ = loft_reference
        sweep_solid, _ = sweep_result
        rel_diff = abs(sweep_solid.volume - loft_solid.volume) / loft_solid.volume
        assert rel_diff < 0.03, \
            f"Volume mismatch: sweep={sweep_solid.volume:.2f}, loft={loft_solid.volume:.2f} ({rel_diff*100:.1f}%)"

    def test_bounding_box_matches(self, loft_reference, sweep_result):
        loft_solid, _ = loft_reference
        sweep_solid, _ = sweep_result
        loft_bb = loft_solid.bounding_box()
        sweep_bb = sweep_solid.bounding_box()

        for axis in ['X', 'Y', 'Z']:
            loft_min = getattr(loft_bb.min, axis)
            loft_max = getattr(loft_bb.max, axis)
            sweep_min = getattr(sweep_bb.min, axis)
            sweep_max = getattr(sweep_bb.max, axis)
            assert abs(loft_min - sweep_min) < 0.3, \
                f"BBox min.{axis}: loft={loft_min:.2f}, sweep={sweep_min:.2f}"
            assert abs(loft_max - sweep_max) < 0.3, \
                f"BBox max.{axis}: loft={loft_max:.2f}, sweep={sweep_max:.2f}"

    def test_tip_diameter_matches(self, loft_reference, sweep_result):
        loft_solid, design = loft_reference
        sweep_solid, _ = sweep_result
        loft_profile = measure_radial_profile(loft_solid, z=0.0)
        sweep_profile = measure_radial_profile(sweep_solid, z=0.0)
        assert abs(loft_profile["max_radius"] - sweep_profile["max_radius"]) < 0.2, \
            f"Tip radius: loft={loft_profile['max_radius']:.3f}, sweep={sweep_profile['max_radius']:.3f}"

    def test_lead_matches(self, loft_reference, sweep_result):
        loft_solid, design = loft_reference
        sweep_solid, _ = sweep_result
        pr = design.worm.pitch_diameter_mm / 2
        loft_lead = measure_lead(loft_solid, pr, worm_length=40.0)
        sweep_lead = measure_lead(sweep_solid, pr, worm_length=40.0)
        assert loft_lead is not None and sweep_lead is not None, "Lead measurement failed"
        assert abs(loft_lead - sweep_lead) / loft_lead < 0.02, \
            f"Lead: loft={loft_lead:.3f}, sweep={sweep_lead:.3f}"


class TestSweepDimensionalAccuracy:
    """Sweep must meet the same dimensional specs as loft."""

    def test_tip_diameter(self):
        solid, design = _build_worm("sweep")
        profile = measure_radial_profile(solid, z=0.0)
        expected = design.worm.tip_diameter_mm / 2
        assert profile["max_radius"] == pytest.approx(expected, abs=0.15)

    def test_root_diameter(self):
        solid, design = _build_worm("sweep")
        profile = measure_radial_profile(solid, z=0.0)
        expected = design.worm.root_diameter_mm / 2
        assert profile["min_radius"] == pytest.approx(expected, abs=0.15)

    def test_lead(self):
        solid, design = _build_worm("sweep")
        measured = measure_lead(solid, design.worm.pitch_diameter_mm / 2, worm_length=40.0)
        assert measured is not None
        assert measured == pytest.approx(design.worm.lead_mm, rel=0.03)

    def test_consistent_tip_along_length(self):
        solid, design = _build_worm("sweep")
        expected = design.worm.tip_diameter_mm / 2
        for z in [-10.0, 0.0, 10.0]:
            profile = measure_radial_profile(solid, z)
            assert profile["max_radius"] == pytest.approx(expected, abs=0.15), \
                f"Tip radius at z={z}: {profile['max_radius']:.3f} != {expected:.3f}"


class TestSweepAcrossParameters:
    """Test sweep across a matrix of parameters."""

    @pytest.mark.parametrize("module,ratio", [(1.0, 30), (2.0, 30), (5.0, 20)])
    def test_sweep_modules(self, module, ratio):
        length = max(40.0, module * 20)
        solid, design = _build_worm("sweep", module=module, ratio=ratio, length=length)
        assert solid.volume > 0, f"Module {module}: zero volume"
        profile = measure_radial_profile(solid, z=0.0)
        expected_tip = design.worm.tip_diameter_mm / 2
        assert profile["max_radius"] == pytest.approx(expected_tip, abs=0.2 + module * 0.03)

    @pytest.mark.parametrize("num_starts", [1, 2])
    def test_sweep_starts(self, num_starts):
        ratio = 30 if num_starts == 1 else 15
        solid, _ = _build_worm("sweep", num_starts=num_starts, ratio=ratio)
        assert solid.volume > 0

    @pytest.mark.parametrize("hand", ["right", "left"])
    def test_sweep_hands(self, hand):
        solid, _ = _build_worm("sweep", hand=hand)
        assert solid.volume > 0

    @pytest.mark.parametrize("profile", ["ZA", "ZK"])
    def test_sweep_profiles(self, profile):
        solid, _ = _build_worm("sweep", profile=profile)
        assert solid.volume > 0

    def test_sweep_vs_loft_across_configs(self):
        """Comprehensive comparison across multiple configurations."""
        configs = [
            {"module": 2.0, "ratio": 30, "num_starts": 1, "hand": "right", "profile": "ZA"},
            {"module": 2.0, "ratio": 30, "num_starts": 1, "hand": "left", "profile": "ZA"},
            {"module": 2.0, "ratio": 15, "num_starts": 2, "hand": "right", "profile": "ZA"},
            {"module": 2.0, "ratio": 30, "num_starts": 1, "hand": "right", "profile": "ZK"},
        ]
        for cfg in configs:
            length = 40.0
            loft_solid, _ = _build_worm("loft", length=length, sections_per_turn=72, **cfg)
            sweep_solid, _ = _build_worm("sweep", length=length, **cfg)
            rel_diff = abs(sweep_solid.volume - loft_solid.volume) / loft_solid.volume
            assert rel_diff < 0.05, \
                f"Config {cfg}: volume diff={rel_diff*100:.1f}% " \
                f"(loft={loft_solid.volume:.1f}, sweep={sweep_solid.volume:.1f})"


class TestSweepPerformance:
    """Performance comparison (informational, not pass/fail)."""

    def test_sweep_timing(self):
        """Log generation times for loft vs sweep."""
        t0 = time.time()
        _build_worm("loft", sections_per_turn=36)
        loft_time = time.time() - t0

        t0 = time.time()
        _build_worm("sweep")
        sweep_time = time.time() - t0

        print(f"\n  Loft (36 sections): {loft_time:.2f}s")
        print(f"  Sweep: {sweep_time:.2f}s")
        print(f"  Speedup: {loft_time/sweep_time:.1f}x" if sweep_time > 0 else "")
        # No assertion - informational only
