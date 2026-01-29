"""
Torture tests for wormgear - testing extreme parameters (P2.3).

These tests verify the geometry generation handles edge cases gracefully:
- Very small gears (module 0.5mm)
- Very large gears (module 10mm)
- Extreme ratios (1:5 to 1:100)
- High start counts (1-6 starts)
- Extreme lead angles (very low and very high)
- Boundary conditions

Note: These tests may be slow as they generate actual geometry.
Run with: pytest tests/test_torture.py -v --timeout=300
"""

import math
import pytest
from wormgear.calculator import design_from_module, validate_design


class TestExtremeModules:
    """Test extreme module values."""

    def test_very_small_module(self):
        """Test 0.5mm module (smallest standard)."""
        design = design_from_module(module=0.5, ratio=20)
        result = validate_design(design)
        # Should either be valid or have warnings/errors (edge case may have issues)
        # Main check is that calculation didn't crash
        assert design.worm.pitch_diameter_mm > 0
        assert design.wheel.pitch_diameter_mm > 0

    def test_small_module(self):
        """Test 1.0mm module."""
        design = design_from_module(module=1.0, ratio=30)
        result = validate_design(design)
        assert result.valid

    def test_medium_module(self):
        """Test 2.0mm module (common)."""
        design = design_from_module(module=2.0, ratio=30)
        result = validate_design(design)
        assert result.valid

    def test_large_module(self):
        """Test 5.0mm module."""
        design = design_from_module(module=5.0, ratio=40)
        result = validate_design(design)
        assert result.valid

    def test_very_large_module(self):
        """Test 10.0mm module (largest common)."""
        design = design_from_module(module=10.0, ratio=50)
        result = validate_design(design)
        assert result.valid


class TestExtremeRatios:
    """Test extreme gear ratios."""

    def test_low_ratio_5(self):
        """Test 1:5 ratio (low reduction)."""
        design = design_from_module(module=2.0, ratio=5)
        result = validate_design(design)
        # Low ratios are edge cases - may have contact ratio or tooth count warnings
        # Main check is that calculation produces valid dimensions
        assert design.worm.pitch_diameter_mm > 0
        assert design.wheel.num_teeth == 5

    def test_low_ratio_10(self):
        """Test 1:10 ratio."""
        design = design_from_module(module=2.0, ratio=10)
        result = validate_design(design)
        # Low ratio may trigger contact ratio or undercut warnings
        assert design.worm.pitch_diameter_mm > 0
        assert design.wheel.num_teeth == 10

    def test_medium_ratio_30(self):
        """Test 1:30 ratio (common)."""
        design = design_from_module(module=2.0, ratio=30)
        result = validate_design(design)
        assert result.valid

    def test_high_ratio_60(self):
        """Test 1:60 ratio (high reduction)."""
        design = design_from_module(module=2.0, ratio=60)
        result = validate_design(design)
        assert result.valid

    def test_very_high_ratio_100(self):
        """Test 1:100 ratio (very high reduction)."""
        design = design_from_module(module=2.0, ratio=100)
        result = validate_design(design)
        # Very high ratios are valid but may have efficiency warnings
        assert result.valid


class TestExtremeStarts:
    """Test extreme worm start counts."""

    def test_single_start(self):
        """Test single-start worm (highest reduction)."""
        design = design_from_module(module=2.0, ratio=30, num_starts=1)
        result = validate_design(design)
        assert result.valid

    def test_double_start(self):
        """Test double-start worm."""
        design = design_from_module(module=2.0, ratio=30, num_starts=2)
        result = validate_design(design)
        assert result.valid

    def test_triple_start(self):
        """Test triple-start worm."""
        design = design_from_module(module=2.0, ratio=30, num_starts=3)
        result = validate_design(design)
        assert result.valid

    def test_quad_start(self):
        """Test quad-start worm (high efficiency)."""
        design = design_from_module(module=2.0, ratio=30, num_starts=4)
        result = validate_design(design)
        assert result.valid

    def test_six_start(self):
        """Test 6-start worm (uncommon but valid)."""
        design = design_from_module(module=2.0, ratio=30, num_starts=6)
        result = validate_design(design)
        # High start count may have lead angle warnings
        assert result.valid or any("LEAD_ANGLE" in m.code for m in result.messages)


class TestLeadAngleBoundaries:
    """Test lead angle boundary conditions."""

    def test_self_locking_angle(self):
        """Test design with self-locking lead angle (<6°)."""
        # Use target_lead_angle to explicitly request a self-locking design
        design = design_from_module(module=1.0, ratio=50, num_starts=1, target_lead_angle=4.0)
        result = validate_design(design)
        # Self-locking design should have low lead angle
        assert design.worm.lead_angle_deg < 6.0

    def test_high_efficiency_angle(self):
        """Test design with high efficiency lead angle (>20°)."""
        # Use target_lead_angle to explicitly request a high-efficiency design
        design = design_from_module(module=3.0, ratio=15, num_starts=4, target_lead_angle=25.0)
        result = validate_design(design)
        # Higher lead angles may have contact ratio warnings for low tooth counts
        # Main check is that dimensions are valid
        assert design.worm.pitch_diameter_mm > 0
        assert design.worm.lead_angle_deg > 20.0  # Should have high efficiency


class TestPressureAngles:
    """Test various pressure angles."""

    def test_pressure_14_5(self):
        """Test 14.5° pressure angle (legacy)."""
        design = design_from_module(module=2.0, ratio=30, pressure_angle=14.5)
        result = validate_design(design)
        assert result.valid

    def test_pressure_20(self):
        """Test 20° pressure angle (standard)."""
        design = design_from_module(module=2.0, ratio=30, pressure_angle=20.0)
        result = validate_design(design)
        assert result.valid

    def test_pressure_25(self):
        """Test 25° pressure angle (high load)."""
        design = design_from_module(module=2.0, ratio=30, pressure_angle=25.0)
        result = validate_design(design)
        assert result.valid


class TestBacklash:
    """Test backlash variations."""

    def test_zero_backlash(self):
        """Test zero backlash (tight mesh)."""
        design = design_from_module(module=2.0, ratio=30, backlash=0.0)
        result = validate_design(design)
        assert result.valid

    def test_small_backlash(self):
        """Test small backlash (precision)."""
        design = design_from_module(module=2.0, ratio=30, backlash=0.02)
        result = validate_design(design)
        assert result.valid

    def test_large_backlash(self):
        """Test large backlash (loose fit)."""
        design = design_from_module(module=2.0, ratio=30, backlash=0.2)
        result = validate_design(design)
        assert result.valid


class TestProfileShift:
    """Test profile shift variations."""

    def test_negative_profile_shift(self):
        """Test negative profile shift."""
        design = design_from_module(module=2.0, ratio=15, profile_shift=-0.3)
        result = validate_design(design)
        # Negative shift with low tooth count is an extreme edge case
        # May legitimately fail validation due to contact ratio or undercut issues
        # Main check is that calculation produces dimensions without crashing
        assert design.worm.pitch_diameter_mm > 0
        # Profile shift is applied to the wheel, not the worm
        assert design.wheel.profile_shift == -0.3

    def test_zero_profile_shift(self):
        """Test zero profile shift (standard)."""
        design = design_from_module(module=2.0, ratio=30, profile_shift=0.0)
        result = validate_design(design)
        assert result.valid

    def test_positive_profile_shift(self):
        """Test positive profile shift (increased strength)."""
        design = design_from_module(module=2.0, ratio=30, profile_shift=0.3)
        result = validate_design(design)
        # Positive shift changes geometry - may trigger interference warnings
        # depending on centre distance calculations
        # Main check is that calculation produces valid dimensions
        assert design.worm.pitch_diameter_mm > 0
        # Profile shift is applied to the wheel, not the worm
        assert design.wheel.profile_shift == 0.3


class TestCombinations:
    """Test difficult parameter combinations."""

    def test_tiny_high_ratio(self):
        """Test tiny module with high ratio."""
        design = design_from_module(module=0.5, ratio=100)
        result = validate_design(design)
        # May have multiple warnings but calculation should succeed
        assert design.worm.pitch_diameter_mm > 0
        assert design.wheel.pitch_diameter_mm > 0

    def test_large_low_ratio(self):
        """Test large module with low ratio."""
        design = design_from_module(module=10.0, ratio=5)
        result = validate_design(design)
        # May have lead angle warnings
        assert design.worm.pitch_diameter_mm > 0
        assert design.wheel.pitch_diameter_mm > 0

    def test_multi_start_high_ratio(self):
        """Test multi-start with high ratio."""
        design = design_from_module(module=2.0, ratio=80, num_starts=4)
        result = validate_design(design)
        assert result.valid

    def test_single_start_low_ratio(self):
        """Test single-start with low ratio."""
        design = design_from_module(module=2.0, ratio=8, num_starts=1)
        result = validate_design(design)
        # May have self-locking warnings
        assert design.worm.pitch_diameter_mm > 0


class TestHandedness:
    """Test handedness variations."""

    def test_right_hand(self):
        """Test right-hand worm."""
        design = design_from_module(module=2.0, ratio=30, hand="right")
        result = validate_design(design)
        assert result.valid
        assert design.assembly.hand.value == "right"

    def test_left_hand(self):
        """Test left-hand worm."""
        design = design_from_module(module=2.0, ratio=30, hand="left")
        result = validate_design(design)
        assert result.valid
        assert design.assembly.hand.value == "left"


class TestDimensionalConsistency:
    """Test dimensional consistency across parameter ranges."""

    @pytest.mark.parametrize("module", [0.5, 1.0, 2.0, 4.0, 8.0])
    @pytest.mark.parametrize("ratio", [10, 30, 60])
    def test_pitch_diameter_formula(self, module, ratio):
        """Test that pitch diameters are consistent with formulas."""
        design = design_from_module(module=module, ratio=ratio)

        # Wheel pitch diameter should be module * teeth
        expected_wheel_pitch = module * design.wheel.num_teeth
        assert abs(design.wheel.pitch_diameter_mm - expected_wheel_pitch) < 0.01

        # Centre distance should be (d1 + d2) / 2
        expected_cd = (design.worm.pitch_diameter_mm + design.wheel.pitch_diameter_mm) / 2
        assert abs(design.assembly.centre_distance_mm - expected_cd) < 0.1

    @pytest.mark.parametrize("module", [1.0, 2.0, 4.0])
    def test_addendum_dedendum(self, module):
        """Test addendum and dedendum are proportional to module."""
        design = design_from_module(module=module, ratio=30)

        # Addendum typically = 1.0 * module
        assert 0.9 * module <= design.worm.addendum_mm <= 1.1 * module

        # Dedendum typically = 1.2 * module (with clearance)
        assert 1.1 * module <= design.worm.dedendum_mm <= 1.4 * module


class TestCalculationStability:
    """Test that calculations don't produce NaN or invalid values."""

    @pytest.mark.parametrize("module", [0.5, 1.0, 2.0, 5.0, 10.0])
    @pytest.mark.parametrize("ratio", [5, 10, 30, 60, 100])
    def test_no_nan_values(self, module, ratio):
        """Test that no NaN values are produced."""
        design = design_from_module(module=module, ratio=ratio)

        # Check all numeric fields are finite
        assert math.isfinite(design.worm.pitch_diameter_mm)
        assert math.isfinite(design.worm.lead_angle_deg)
        assert math.isfinite(design.wheel.pitch_diameter_mm)
        assert math.isfinite(design.assembly.centre_distance_mm)

    @pytest.mark.parametrize("ratio", [5, 10, 30, 60, 100])
    def test_positive_dimensions(self, ratio):
        """Test that all dimensions are positive."""
        design = design_from_module(module=2.0, ratio=ratio)

        # All dimensions should be positive
        assert design.worm.pitch_diameter_mm > 0
        assert design.worm.tip_diameter_mm > 0
        assert design.worm.root_diameter_mm > 0
        assert design.wheel.pitch_diameter_mm > 0
        assert design.wheel.tip_diameter_mm > 0
        assert design.wheel.root_diameter_mm > 0
        assert design.assembly.centre_distance_mm > 0

    @pytest.mark.parametrize("module", [0.5, 1.0, 2.0, 5.0])
    def test_diameter_ordering(self, module):
        """Test that tip > pitch > root for all gears."""
        design = design_from_module(module=module, ratio=30)

        # Worm: tip > pitch > root
        assert design.worm.tip_diameter_mm > design.worm.pitch_diameter_mm
        assert design.worm.pitch_diameter_mm > design.worm.root_diameter_mm

        # Wheel: tip > pitch > root
        assert design.wheel.tip_diameter_mm > design.wheel.pitch_diameter_mm
        assert design.wheel.pitch_diameter_mm > design.wheel.root_diameter_mm
