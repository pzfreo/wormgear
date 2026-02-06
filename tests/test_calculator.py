"""
Tests for calculator module.
"""

import pytest
from wormgear.calculator import (
    calculate_design_from_module,
    calculate_design_from_wheel,
    calculate_design_from_centre_distance,
    STANDARD_MODULES,
    nearest_standard_module,
    is_standard_module,
    estimate_efficiency,
)
from wormgear import WormParams, WheelParams, AssemblyParams, WormGearDesign


class TestDesignFromModule:
    """Tests for design_from_module function."""

    def test_basic_design(self):
        """Test basic design from module and ratio."""
        design = calculate_design_from_module(module=2.0, ratio=30)

        assert isinstance(design, WormGearDesign)
        assert design.worm.module_mm == 2.0
        assert design.wheel.num_teeth == 30
        assert design.assembly.ratio == 30

    def test_custom_lead_angle(self):
        """Test design with custom target lead angle."""
        design = calculate_design_from_module(
            module=2.0,
            ratio=30,
            target_lead_angle=10.0
        )

        # Lead angle should be close to target
        assert abs(design.worm.lead_angle_deg - 10.0) < 0.5

    def test_globoid_worm(self):
        """Test globoid worm design."""
        design = calculate_design_from_module(
            module=2.0,
            ratio=30,
            globoid=True,
            throat_reduction=0.1
        )

        # Centre distance is always (worm_pd + wheel_pd) / 2, even for globoid
        # Throat reduction affects worm shape, not axis spacing
        standard_cd = (design.worm.pitch_diameter_mm + design.wheel.pitch_diameter_mm) / 2
        assert design.assembly.centre_distance_mm == pytest.approx(standard_cd, rel=1e-6)

    def test_profile_shift(self):
        """Test design with profile shift."""
        design = calculate_design_from_module(
            module=2.0,
            ratio=30,
            profile_shift=0.2
        )

        # Profile shift should affect wheel addendum/dedendum
        assert design.wheel.profile_shift == 0.2
        assert design.wheel.addendum_mm > design.worm.module_mm  # Increased by shift

    def test_hand_configuration(self):
        """Test left-hand thread."""
        design = calculate_design_from_module(
            module=2.0,
            ratio=30,
            hand="left"
        )

        # hand is now Hand enum, compare value
        assert design.assembly.hand.value == "left"
        assert design.worm.hand.value == "left"

    def test_multi_start_worm(self):
        """Test multi-start worm."""
        design = calculate_design_from_module(
            module=2.0,
            ratio=30,
            num_starts=2
        )

        assert design.worm.num_starts == 2
        assert design.wheel.num_teeth == 60  # ratio × num_starts
        assert design.assembly.ratio == 30  # Still 30:1

    def test_efficiency_calculation(self):
        """Test that efficiency is calculated."""
        design = calculate_design_from_module(module=2.0, ratio=30)

        assert design.assembly.efficiency_percent > 0
        assert design.assembly.efficiency_percent <= 100

    def test_self_locking_low_lead_angle(self):
        """Test self-locking with low lead angle."""
        design = calculate_design_from_module(
            module=1.0,
            ratio=60,
            target_lead_angle=4.0
        )

        # Low lead angle should be self-locking
        assert design.assembly.self_locking is True

    def test_not_self_locking_high_lead_angle(self):
        """Test non-self-locking with higher lead angle."""
        design = calculate_design_from_module(
            module=2.0,
            ratio=10,
            target_lead_angle=15.0
        )

        # High lead angle should not be self-locking
        assert design.assembly.self_locking is False


class TestDesignFromWheel:
    """Tests for design_from_wheel function."""

    def test_basic_design_from_wheel(self):
        """Test design from wheel OD."""
        design = calculate_design_from_wheel(wheel_od=64.0, ratio=30)

        # Wheel OD should match
        assert abs(design.wheel.tip_diameter_mm - 64.0) < 0.01
        assert design.wheel.num_teeth == 30
        assert design.assembly.ratio == 30

    def test_wheel_od_determines_module(self):
        """Test that wheel OD determines module."""
        design = calculate_design_from_wheel(wheel_od=64.0, ratio=30)

        # For 30 teeth, OD = (30 + 2) × module
        # So module = 64 / 32 = 2.0
        assert abs(design.worm.module_mm - 2.0) < 0.01


class TestDesignFromCentreDistance:
    """Tests for design_from_centre_distance function."""

    def test_basic_design_from_centre_distance(self):
        """Test design from centre distance."""
        design = calculate_design_from_centre_distance(
            centre_distance=40.0,
            ratio=30
        )

        # Centre distance should match
        assert abs(design.assembly.centre_distance_mm - 40.0) < 0.01
        assert design.assembly.ratio == 30

    def test_worm_to_wheel_ratio_affects_diameters(self):
        """Test that worm_to_wheel_ratio parameter works."""
        design1 = calculate_design_from_centre_distance(
            centre_distance=40.0,
            ratio=30,
            worm_to_wheel_ratio=0.3
        )

        design2 = calculate_design_from_centre_distance(
            centre_distance=40.0,
            ratio=30,
            worm_to_wheel_ratio=0.5
        )

        # Different ratio should give different worm diameters
        assert design1.worm.pitch_diameter_mm != design2.worm.pitch_diameter_mm


class TestUtilityFunctions:
    """Tests for utility functions."""

    def test_standard_modules_list(self):
        """Test that standard modules list is available."""
        assert len(STANDARD_MODULES) > 0
        assert 2.0 in STANDARD_MODULES
        assert 1.5 in STANDARD_MODULES

    def test_nearest_standard_module(self):
        """Test nearest standard module finder."""
        assert nearest_standard_module(2.3) == 2.25
        assert nearest_standard_module(2.0) == 2.0
        assert nearest_standard_module(1.7) == 1.75

    def test_is_standard_module(self):
        """Test standard module checker."""
        assert is_standard_module(2.0) is True
        assert is_standard_module(1.5) is True
        assert is_standard_module(2.1) is False
        assert is_standard_module(2.0001, tolerance=0.01) is True

    def test_estimate_efficiency(self):
        """Test efficiency estimation."""
        # Higher lead angle = higher efficiency
        eff_low = estimate_efficiency(5.0)
        eff_high = estimate_efficiency(15.0)

        assert eff_low < eff_high
        assert 0 <= eff_low <= 100
        assert 0 <= eff_high <= 100


class TestGeometryCompatibility:
    """Tests for compatibility with geometry generation."""

    def test_design_works_with_worm_geometry(self):
        """Test that calculated design works with WormGeometry."""
        from wormgear import WormGeometry

        design = calculate_design_from_module(module=2.0, ratio=30)

        # Should be able to create geometry without errors
        worm_geo = WormGeometry(
            params=design.worm,
            assembly_params=design.assembly,
            length=40.0
        )

        assert worm_geo is not None

    def test_design_works_with_wheel_geometry(self):
        """Test that calculated design works with WheelGeometry."""
        from wormgear import WheelGeometry

        design = calculate_design_from_module(module=2.0, ratio=30)

        # Should be able to create geometry without errors
        wheel_geo = WheelGeometry(
            params=design.wheel,
            worm_params=design.worm,
            assembly_params=design.assembly
        )

        assert wheel_geo is not None


class TestManufacturingParams:
    """Tests for manufacturing parameters."""

    def test_manufacturing_params_included(self):
        """Test that manufacturing params are included in design."""
        design = calculate_design_from_module(module=2.0, ratio=30)

        assert design.manufacturing is not None
        # profile is now WormProfile enum
        assert design.manufacturing.profile.value in ["ZA", "ZK"]

    def test_profile_parameter(self):
        """Test profile parameter."""
        design_za = calculate_design_from_module(module=2.0, ratio=30, profile="ZA")
        design_zk = calculate_design_from_module(module=2.0, ratio=30, profile="ZK")

        # profile is now WormProfile enum, compare values
        assert design_za.manufacturing.profile.value == "ZA"
        assert design_zk.manufacturing.profile.value == "ZK"

    def test_wheel_throated_parameter(self):
        """Test wheel_throated parameter."""
        design = calculate_design_from_module(
            module=2.0,
            ratio=30,
            wheel_throated=True
        )

        assert design.manufacturing.throated_wheel is True
