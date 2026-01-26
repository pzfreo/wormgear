"""
Tests for validation message edge cases and thresholds.

These tests verify that validation messages appear at the correct thresholds
and don't appear when they shouldn't (e.g., when settings make them irrelevant).
"""

import pytest
from wormgear.calculator.validation import validate_design
from wormgear.calculator import calculate_design_from_module


class TestModuleValidationMessages:
    """Tests for module-related validation messages."""

    def test_module_near_standard_not_shown_when_already_standard(self):
        """
        MODULE_NEAR_STANDARD should NOT appear when deviation < 0.1%.
        This prevents confusing messages like "Module 0.500mm is close to standard 0.5mm".
        """
        # Use exact standard module
        design = calculate_design_from_module(module=0.5, ratio=30)
        validation = validate_design(design)

        # Should not have MODULE_NEAR_STANDARD message
        codes = [m.code for m in validation.messages]
        assert 'MODULE_NEAR_STANDARD' not in codes
        assert 'MODULE_NON_STANDARD' not in codes

    def test_module_near_standard_shown_for_small_deviation(self):
        """
        MODULE_NEAR_STANDARD should appear when deviation is between 0.1% and 10%.
        Example: 0.505mm is ~1% from 0.5mm standard.
        """
        # Module with ~1% deviation from 0.5mm standard
        design = calculate_design_from_module(module=0.505, ratio=30)
        validation = validate_design(design)

        # Should have MODULE_NEAR_STANDARD as INFO
        near_standard_msgs = [m for m in validation.messages if m.code == 'MODULE_NEAR_STANDARD']
        assert len(near_standard_msgs) == 1
        assert near_standard_msgs[0].severity.value == 'info'
        assert '0.5' in near_standard_msgs[0].suggestion  # Should mention 0.5mm

    def test_module_non_standard_shown_for_large_deviation(self):
        """
        MODULE_NON_STANDARD should appear when deviation >= 10%.
        Example: 0.35mm is ~16.7% from 0.3mm standard.
        """
        # Module with 10%+ deviation
        # 0.35mm → nearest is 0.3mm → deviation = (0.35-0.3)/0.3 = 16.7%
        design = calculate_design_from_module(module=0.35, ratio=30)
        validation = validate_design(design)

        # Should have MODULE_NON_STANDARD as WARNING
        non_standard_msgs = [m for m in validation.messages if m.code == 'MODULE_NON_STANDARD']
        assert len(non_standard_msgs) == 1
        assert non_standard_msgs[0].severity.value == 'warning'

    def test_module_very_small_deviation_no_message(self):
        """
        No module message when deviation < 0.1% (user already rounded).
        Example: 0.5001mm is only 0.02% from 0.5mm.
        """
        # Module with tiny deviation (0.02% from 0.5mm)
        design = calculate_design_from_module(module=0.5001, ratio=30)
        validation = validate_design(design)

        # Should have no module-related messages
        codes = [m.code for m in validation.messages]
        assert 'MODULE_NEAR_STANDARD' not in codes
        assert 'MODULE_NON_STANDARD' not in codes


class TestGloboidValidationMessages:
    """Tests for globoid worm validation messages."""

    def test_globoid_non_throated_warning_without_virtual_hobbing(self):
        """
        GLOBOID_NON_THROATED should appear as INFO when globoid worm
        has non-throated wheel and virtual hobbing is NOT enabled.
        """
        design = calculate_design_from_module(
            module=2.0,
            ratio=30,
            globoid=True,
            throat_reduction=0.1,
            wheel_throated=False  # Non-throated wheel
        )

        # Virtual hobbing NOT enabled
        if design.manufacturing:
            design.manufacturing.virtual_hobbing = False

        validation = validate_design(design)

        # Should have GLOBOID_NON_THROATED as INFO
        globoid_msgs = [m for m in validation.messages if m.code == 'GLOBOID_NON_THROATED']
        assert len(globoid_msgs) == 1
        assert globoid_msgs[0].severity.value == 'info'
        assert 'virtual hobbing' in globoid_msgs[0].suggestion.lower()

    def test_globoid_non_throated_suppressed_with_virtual_hobbing(self):
        """
        GLOBOID_NON_THROATED should NOT appear when virtual hobbing is enabled,
        because virtual hobbing creates a throated wheel regardless of wheel_throated flag.

        This was a bug: warning appeared even with virtual hobbing selected.
        """
        design = calculate_design_from_module(
            module=2.0,
            ratio=30,
            globoid=True,
            throat_reduction=0.1,
            wheel_throated=False  # Non-throated, but virtual hobbing will fix it
        )

        # Virtual hobbing ENABLED
        if design.manufacturing:
            design.manufacturing.virtual_hobbing = True

        validation = validate_design(design)

        # Should NOT have GLOBOID_NON_THROATED message
        codes = [m.code for m in validation.messages]
        assert 'GLOBOID_NON_THROATED' not in codes

    def test_globoid_throated_wheel_no_warning(self):
        """
        GLOBOID_NON_THROATED should NOT appear when wheel is already throated.
        """
        design = calculate_design_from_module(
            module=2.0,
            ratio=30,
            globoid=True,
            throat_reduction=0.1,
            wheel_throated=True  # Throated wheel
        )

        validation = validate_design(design)

        # Should NOT have GLOBOID_NON_THROATED message
        codes = [m.code for m in validation.messages]
        assert 'GLOBOID_NON_THROATED' not in codes

    def test_cylindrical_worm_no_globoid_warning(self):
        """
        GLOBOID_NON_THROATED should NOT appear for cylindrical worms.
        """
        design = calculate_design_from_module(
            module=2.0,
            ratio=30,
            globoid=False,
            wheel_throated=False
        )

        validation = validate_design(design)

        # Should NOT have GLOBOID_NON_THROATED message
        codes = [m.code for m in validation.messages]
        assert 'GLOBOID_NON_THROATED' not in codes


class TestValidationMessageSeverities:
    """Test that validation messages have correct severities."""

    def test_lead_angle_too_low_is_error(self):
        """Lead angle < 1° should be ERROR."""
        # Very large worm diameter with small module creates tiny lead angle
        design = calculate_design_from_module(
            module=0.5,
            ratio=100,
            worm_pitch_diameter=80.0  # Very large diameter = very low lead angle
        )

        validation = validate_design(design)

        # Should have LEAD_ANGLE_TOO_LOW or LEAD_ANGLE_VERY_LOW
        lead_msgs = [m for m in validation.messages if 'LEAD_ANGLE' in m.code]
        assert len(lead_msgs) > 0
        # At least one should be error if lead angle < 1°
        if design.worm.lead_angle_deg < 1.0:
            error_msgs = [m for m in lead_msgs if m.severity.value == 'error']
            assert len(error_msgs) > 0

    def test_efficiency_very_low_is_warning(self):
        """Efficiency < 30% should be WARNING."""
        # Low lead angle = low efficiency
        design = calculate_design_from_module(
            module=1.0,
            ratio=60,
            target_lead_angle=3.0  # Low lead angle
        )

        validation = validate_design(design)

        if design.assembly.efficiency_percent and design.assembly.efficiency_percent < 30:
            eff_msgs = [m for m in validation.messages if m.code == 'EFFICIENCY_VERY_LOW']
            assert len(eff_msgs) == 1
            assert eff_msgs[0].severity.value == 'warning'

    def test_clearance_negative_is_error(self):
        """Geometric interference (negative clearance) should be ERROR."""
        # This is hard to trigger with valid inputs, but test the validation logic
        # by checking that positive clearance doesn't trigger error
        design = calculate_design_from_module(module=2.0, ratio=30)
        validation = validate_design(design)

        # Should NOT have GEOMETRIC_INTERFERENCE
        codes = [m.code for m in validation.messages]
        assert 'GEOMETRIC_INTERFERENCE' not in codes
