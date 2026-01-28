"""
Tests for standard module rounding post-processing.

When "Use standard module" is checked in the UI, the calculator should:
1. Calculate design with initial parameters
2. Round module to nearest standard (ISO 54)
3. Recalculate design using standard module
4. Preserve key constraints based on mode

This tests the Python side logic that supports this workflow.
"""

import pytest
from wormgear.calculator import (
    calculate_design_from_module,
    calculate_design_from_centre_distance,
    calculate_design_from_wheel,
    nearest_standard_module,
    is_standard_module,
    STANDARD_MODULES,
)


class TestStandardModuleRounding:
    """Tests for standard module rounding workflow."""

    def test_nearest_standard_module_rounds_correctly(self):
        """Test that nearest_standard_module finds correct standard."""
        # Test various calculated modules
        assert nearest_standard_module(2.3) == 2.25
        assert nearest_standard_module(2.0) == 2.0  # Already standard
        assert nearest_standard_module(1.7) == 1.75
        assert nearest_standard_module(0.45) == 0.4  # Closer to 0.4 than 0.5
        assert nearest_standard_module(4.8) == 5.0

    def test_is_standard_module_detection(self):
        """Test standard module detection."""
        assert is_standard_module(2.0) is True
        assert is_standard_module(1.5) is True
        assert is_standard_module(0.5) is True
        assert is_standard_module(2.1) is False
        assert is_standard_module(1.55) is False

    def test_from_centre_distance_then_round(self):
        """
        Test workflow: design from centre distance, then round to standard module.

        This simulates what the UI does when "Use standard module" is checked.
        """
        # Step 1: Calculate from centre distance
        initial_design = calculate_design_from_centre_distance(
            centre_distance=40.0,
            ratio=30
        )

        calculated_module = initial_design.worm.module_mm
        standard_module = nearest_standard_module(calculated_module)

        # If module is already standard (within 0.1%), we're done
        if abs(calculated_module - standard_module) > 0.001:
            # Step 2: Recalculate using standard module
            # For non-envelope modes, use standard module directly
            rounded_design = calculate_design_from_module(
                module=standard_module,
                ratio=30,
                pressure_angle=initial_design.assembly.pressure_angle_deg,
                backlash=initial_design.assembly.backlash_mm,
                num_starts=initial_design.worm.num_starts,
                hand=initial_design.assembly.hand,
            )

            # Verify module was rounded
            assert rounded_design.worm.module_mm == standard_module
            assert is_standard_module(rounded_design.worm.module_mm)

            # Ratio should be preserved
            assert rounded_design.assembly.ratio == 30

    def test_from_wheel_then_round(self):
        """
        Test workflow: design from wheel OD, then round to standard module.
        """
        # Step 1: Calculate from wheel OD
        initial_design = calculate_design_from_wheel(
            wheel_od=65.0,
            ratio=30,
            target_lead_angle=7.0
        )

        calculated_module = initial_design.worm.module_mm
        standard_module = nearest_standard_module(calculated_module)

        if abs(calculated_module - standard_module) > 0.001:
            # Step 2: Recalculate using standard module
            rounded_design = calculate_design_from_module(
                module=standard_module,
                ratio=30,
                target_lead_angle=7.0,
                pressure_angle=initial_design.assembly.pressure_angle_deg,
                backlash=initial_design.assembly.backlash_mm,
            )

            # Verify module was rounded
            assert rounded_design.worm.module_mm == standard_module
            assert is_standard_module(rounded_design.worm.module_mm)

    def test_from_module_no_rounding_needed(self):
        """
        When mode is 'from-module', no rounding should occur
        because user explicitly specified the module.
        """
        # User specifies module directly
        design = calculate_design_from_module(module=2.0, ratio=30)

        # Module should be exactly as specified
        assert design.worm.module_mm == 2.0

        # No rounding needed (already standard)
        assert is_standard_module(design.worm.module_mm)

    def test_envelope_mode_preserves_worm_od(self):
        """
        For envelope mode with rounding, should preserve worm OD
        by adjusting pitch diameter to compensate for addendum change.

        OD = pitch_diameter + 2 * addendum
        addendum = module

        If module increases, pitch diameter should decrease to keep OD similar.
        """
        # Simulate envelope calculation that gives non-standard module
        # (In real code this would come from design_from_envelope)

        # Example: envelope gave module=2.3mm, worm pitch=16mm
        # worm OD = 16 + 2*2.3 = 20.6mm
        initial_module = 2.3
        initial_pitch = 16.0
        initial_od = initial_pitch + 2 * initial_module  # 20.6mm

        # Round to standard
        standard_module = nearest_standard_module(initial_module)  # 2.25mm
        assert standard_module == 2.25

        # Adjust pitch diameter to preserve OD
        addendum_change = standard_module - initial_module  # 2.25 - 2.3 = -0.05
        adjusted_pitch = initial_pitch - 2 * addendum_change  # 16 - 2*(-0.05) = 16.1

        # New OD should be very close to original
        new_od = adjusted_pitch + 2 * standard_module  # 16.1 + 2*2.25 = 20.6mm

        assert abs(new_od - initial_od) < 0.01  # Within 0.01mm

    def test_rounding_preserves_ratio(self):
        """
        Rounding module should preserve gear ratio.
        """
        initial_design = calculate_design_from_centre_distance(
            centre_distance=50.0,
            ratio=40
        )

        calculated_module = initial_design.worm.module_mm
        standard_module = nearest_standard_module(calculated_module)

        if abs(calculated_module - standard_module) > 0.001:
            rounded_design = calculate_design_from_module(
                module=standard_module,
                ratio=40,
                pressure_angle=initial_design.assembly.pressure_angle_deg,
            )

            # Ratio must be preserved exactly
            assert rounded_design.assembly.ratio == 40
            assert rounded_design.wheel.num_teeth == 40

    def test_all_standard_modules_valid(self):
        """
        Verify that all standard modules in STANDARD_MODULES list
        can be used to create valid designs.
        """
        for module in STANDARD_MODULES:
            if module >= 0.5:  # Skip very small modules that might cause issues
                design = calculate_design_from_module(module=module, ratio=30)

                assert design.worm.module_mm == module
                assert design.wheel.num_teeth == 30
                assert design.worm.pitch_diameter_mm > 0
                assert design.wheel.pitch_diameter_mm > 0

    def test_rounding_up_vs_down(self):
        """
        Test that rounding goes to nearest standard, not always up or down.
        """
        # Module 2.1 should round down to 2.0
        assert nearest_standard_module(2.1) == 2.0

        # Module 2.2 should round up to 2.25
        assert nearest_standard_module(2.2) == 2.25

        # Module exactly between should round to one or the other
        midpoint = (2.0 + 2.25) / 2  # 2.125
        rounded = nearest_standard_module(midpoint)
        assert rounded in [2.0, 2.25]


class TestStandardModuleEdgeCases:
    """Test edge cases in standard module rounding."""

    def test_very_small_non_standard_module(self):
        """Test rounding for very small modules."""
        # Module 0.45mm should round to 0.4mm (nearest)
        assert nearest_standard_module(0.45) == 0.4

    def test_very_large_non_standard_module(self):
        """Test rounding for large modules."""
        # Module 9.5mm should round to 9mm (nearest)
        assert nearest_standard_module(9.5) == 9.0

    def test_already_standard_no_change(self):
        """
        If module is already standard, rounding should return same value.
        """
        for module in [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0]:
            assert nearest_standard_module(module) == module
            assert is_standard_module(module)

    def test_rounding_with_different_parameters(self):
        """
        Test that rounding works with various design parameters.
        """
        # High ratio
        design = calculate_design_from_centre_distance(centre_distance=80.0, ratio=100)
        calc_mod = design.worm.module_mm
        std_mod = nearest_standard_module(calc_mod)

        if abs(calc_mod - std_mod) > 0.001:
            rounded = calculate_design_from_module(module=std_mod, ratio=100)
            assert is_standard_module(rounded.worm.module_mm)

        # Multi-start worm
        design = calculate_design_from_centre_distance(
            centre_distance=40.0,
            ratio=30,
            num_starts=2
        )
        calc_mod = design.worm.module_mm
        std_mod = nearest_standard_module(calc_mod)

        if abs(calc_mod - std_mod) > 0.001:
            rounded = calculate_design_from_module(
                module=std_mod,
                ratio=30,
                num_starts=2
            )
            assert is_standard_module(rounded.worm.module_mm)
            assert rounded.worm.num_starts == 2

    def test_rounding_preserves_hand(self):
        """Test that rounding preserves left/right hand."""
        design = calculate_design_from_centre_distance(
            centre_distance=40.0,
            ratio=30,
            hand="left"
        )

        calc_mod = design.worm.module_mm
        std_mod = nearest_standard_module(calc_mod)

        if abs(calc_mod - std_mod) > 0.001:
            rounded = calculate_design_from_module(
                module=std_mod,
                ratio=30,
                hand="left"
            )

            # Hand is an enum
            from wormgear.enums import Hand
            assert rounded.assembly.hand == Hand.LEFT
