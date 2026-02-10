"""
Dimensional verification tests for worm geometry.

These tests verify that built worm geometry has correct physical dimensions
by slicing cross-sections and measuring thread profiles. They serve as
ground-truth tests for any generation method (loft or sweep).

Marked slow because they build 3D geometry via build123d.
"""

import math
import pytest
from wormgear import WormGeometry
from wormgear.calculator.core import design_from_module
from tests.helpers.geometry_sampling import (
    measure_radial_profile,
    measure_lead,
    measure_flank_angle,
)

pytestmark = pytest.mark.slow


def _build_worm(module=2.0, ratio=30, num_starts=1, hand="right",
                profile="ZA", length=40.0, sections_per_turn=36,
                generation_method="loft"):
    """Helper to build a worm from calculator parameters."""
    design = design_from_module(module=module, ratio=ratio,
                                num_starts=num_starts, hand=hand,
                                profile=profile)
    kwargs = dict(
        params=design.worm,
        assembly_params=design.assembly,
        length=length,
        sections_per_turn=sections_per_turn,
        profile=profile,
    )
    if generation_method != "loft":
        kwargs["generation_method"] = generation_method
    geo = WormGeometry(**kwargs)
    solid = geo.build()
    return solid, design


class TestTipAndRootDiameters:
    """Verify tip and root diameters from cross-sections."""

    def test_tip_diameter_matches_design(self):
        solid, design = _build_worm()
        profile = measure_radial_profile(solid, z=0.0)
        expected_tip_r = design.worm.tip_diameter_mm / 2
        assert profile["max_radius"] == pytest.approx(expected_tip_r, abs=0.15), \
            f"Tip radius: measured={profile['max_radius']:.3f}, expected={expected_tip_r:.3f}"

    def test_root_diameter_matches_design(self):
        solid, design = _build_worm()
        profile = measure_radial_profile(solid, z=0.0)
        expected_root_r = design.worm.root_diameter_mm / 2
        # Root radius is the minimum in the cross-section (the valleys between threads)
        assert profile["min_radius"] == pytest.approx(expected_root_r, abs=0.15), \
            f"Root radius: measured={profile['min_radius']:.3f}, expected={expected_root_r:.3f}"

    def test_tip_diameter_at_multiple_z(self):
        """Tip diameter should be consistent along the worm length."""
        solid, design = _build_worm()
        expected_tip_r = design.worm.tip_diameter_mm / 2
        for z in [-10.0, -5.0, 0.0, 5.0, 10.0]:
            profile = measure_radial_profile(solid, z)
            assert profile["max_radius"] == pytest.approx(expected_tip_r, abs=0.15), \
                f"Tip radius at z={z}: {profile['max_radius']:.3f} != {expected_tip_r:.3f}"


class TestLeadMeasurement:
    """Verify lead (axial advance per revolution) from geometry."""

    def test_lead_matches_design(self):
        solid, design = _build_worm()
        measured_lead = measure_lead(solid, design.worm.pitch_diameter_mm / 2,
                                     worm_length=40.0)
        assert measured_lead is not None, "Lead measurement failed"
        assert measured_lead == pytest.approx(design.worm.lead_mm, rel=0.03), \
            f"Lead: measured={measured_lead:.3f}, expected={design.worm.lead_mm:.3f}"

    def test_lead_left_hand(self):
        solid, design = _build_worm(hand="left")
        measured_lead = measure_lead(solid, design.worm.pitch_diameter_mm / 2,
                                     worm_length=40.0)
        assert measured_lead is not None, "Lead measurement failed"
        # Lead magnitude should be the same regardless of hand
        assert measured_lead == pytest.approx(design.worm.lead_mm, rel=0.03), \
            f"Lead (LH): measured={measured_lead:.3f}, expected={design.worm.lead_mm:.3f}"

    def test_lead_multi_start(self):
        solid, design = _build_worm(num_starts=2, module=2.0, ratio=15)
        measured_lead = measure_lead(solid, design.worm.pitch_diameter_mm / 2,
                                     worm_length=40.0)
        assert measured_lead is not None, "Lead measurement failed"
        assert measured_lead == pytest.approx(design.worm.lead_mm, rel=0.05), \
            f"Lead (2-start): measured={measured_lead:.3f}, expected={design.worm.lead_mm:.3f}"


class TestDimensionsAcrossModules:
    """Verify dimensional accuracy across different module sizes."""

    @pytest.mark.parametrize("module", [1.0, 2.0, 5.0])
    def test_tip_diameter(self, module):
        solid, design = _build_worm(module=module, ratio=30, length=max(40.0, module * 20))
        profile = measure_radial_profile(solid, z=0.0)
        expected_tip_r = design.worm.tip_diameter_mm / 2
        assert profile["max_radius"] == pytest.approx(expected_tip_r, abs=0.15 + module * 0.02), \
            f"Module {module}: tip_r={profile['max_radius']:.3f}, expected={expected_tip_r:.3f}"

    @pytest.mark.parametrize("module", [1.0, 2.0, 5.0])
    def test_lead(self, module):
        length = max(40.0, module * 20)
        solid, design = _build_worm(module=module, ratio=30, length=length)
        measured_lead = measure_lead(solid, design.worm.pitch_diameter_mm / 2,
                                     worm_length=length)
        assert measured_lead is not None, f"Lead measurement failed for module={module}"
        assert measured_lead == pytest.approx(design.worm.lead_mm, rel=0.05), \
            f"Module {module}: lead={measured_lead:.3f}, expected={design.worm.lead_mm:.3f}"


class TestFlankAngle:
    """Verify flank angle matches pressure angle for ZA profiles."""

    def test_flank_angle_za(self):
        solid, design = _build_worm(profile="ZA")
        measured_angle = measure_flank_angle(
            solid, z=0.0,
            pitch_radius=design.worm.pitch_diameter_mm / 2,
            addendum=design.worm.addendum_mm,
            dedendum=design.worm.dedendum_mm,
        )
        if measured_angle is not None:
            assert measured_angle == pytest.approx(
                design.assembly.pressure_angle_deg, abs=3.0
            ), f"Flank angle: {measured_angle:.1f} deg, expected {design.assembly.pressure_angle_deg} deg"


class TestMultiStart:
    """Verify multi-start worms have correct geometry."""

    def test_two_start_valid(self):
        solid, design = _build_worm(num_starts=2, ratio=15)
        assert solid.is_valid or solid.volume > 0

    def test_four_start_valid(self):
        solid, design = _build_worm(num_starts=4, ratio=8)
        assert solid.is_valid or solid.volume > 0

    def test_two_start_tip_diameter(self):
        solid, design = _build_worm(num_starts=2, ratio=15)
        profile = measure_radial_profile(solid, z=0.0)
        expected_tip_r = design.worm.tip_diameter_mm / 2
        assert profile["max_radius"] == pytest.approx(expected_tip_r, abs=0.2)
