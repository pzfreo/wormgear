"""
Comprehensive unit tests for worm gear validation internals.

Phase 1 of tech debt remediation: build safety net before refactoring.
Tests call internal validator functions directly with minimal dict inputs.
No geometry building — all tests are fast (no @pytest.mark.slow).
"""

import pytest
from dataclasses import dataclass
from typing import Optional

from wormgear.calculator.validation import (
    _get,
    calculate_minimum_teeth,
    calculate_recommended_profile_shift,
    _normalize_profile,
    _normalize_worm_type,
    _normalize_bore_type,
    _get_keyway_depth,
    _validate_geometry_possible,
    _validate_worm_proportions,
    _validate_pressure_angle,
    _validate_clearance,
    _validate_centre_distance,
    _validate_profile,
    _validate_worm_type,
    _validate_manufacturing_compatibility,
    _validate_single_bore,
    _validate_bore_from_settings,
    _validate_bore,
    Severity,
    ValidationMessage,
)
from wormgear.enums import WormProfile, WormType, BoreType, AntiRotation


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _codes(messages):
    """Extract code strings from a list of ValidationMessages."""
    return [m.code for m in messages]


def _severities(messages):
    """Extract (code, severity) pairs."""
    return {m.code: m.severity for m in messages}


def _make_design(**overrides):
    """Build a minimal valid design dict.

    Dot-notation keys are expanded:
        _make_design(**{'worm.root_diameter_mm': 5.0})
    produces:
        {'worm': {'root_diameter_mm': 5.0, ...}, ...}
    """
    design = {
        'worm': {
            'module_mm': 2.0,
            'pitch_diameter_mm': 16.29,
            'tip_diameter_mm': 20.29,
            'root_diameter_mm': 11.29,
            'lead_mm': 6.283,
            'lead_angle_deg': 7.0,
            'num_starts': 1,
            'hand': 'right',
            'profile_shift': 0.0,
            'addendum_mm': 2.0,
            'dedendum_mm': 2.5,
        },
        'wheel': {
            'module_mm': 2.0,
            'num_teeth': 30,
            'pitch_diameter_mm': 60.0,
            'tip_diameter_mm': 64.0,
            'root_diameter_mm': 55.0,
            'throat_diameter_mm': 62.0,
            'addendum_mm': 2.0,
            'dedendum_mm': 2.5,
            'profile_shift': 0.0,
        },
        'assembly': {
            'centre_distance_mm': 38.14,
            'pressure_angle_deg': 20.0,
            'backlash_mm': 0.05,
            'hand': 'right',
            'ratio': 30,
            'efficiency_percent': 75.0,
            'self_locking': False,
        },
        'manufacturing': {
            'profile': 'ZA',
            'virtual_hobbing': False,
            'hobbing_steps': 18,
            'throated_wheel': False,
            'sections_per_turn': 36,
        },
    }

    for dotkey, value in overrides.items():
        parts = dotkey.split('.')
        target = design
        for part in parts[:-1]:
            if part not in target:
                target[part] = {}
            target = target[part]
        target[parts[-1]] = value

    return design


# ---------------------------------------------------------------------------
# Simple dataclasses for testing _get with attribute access
# ---------------------------------------------------------------------------

@dataclass
class _Inner:
    lead_angle_deg: float = 7.0
    root_diameter_mm: float = 11.29


@dataclass
class _Outer:
    worm: Optional[_Inner] = None


# ===========================================================================
# 1. TestGetHelper
# ===========================================================================

class TestGetHelper:
    """Tests for the _get() traversal helper."""

    def test_dict_single_key(self):
        assert _get({'a': 1}, 'a') == 1

    def test_dict_nested_keys(self):
        d = {'worm': {'lead_angle_deg': 7.0}}
        assert _get(d, 'worm', 'lead_angle_deg') == 7.0

    def test_dict_missing_key_returns_default(self):
        assert _get({}, 'missing', default=42) == 42

    def test_dict_missing_key_returns_none(self):
        assert _get({}, 'missing') is None

    def test_dict_none_intermediate(self):
        d = {'worm': None}
        assert _get(d, 'worm', 'lead_angle_deg', default=99) == 99

    def test_dataclass_attribute(self):
        obj = _Outer(worm=_Inner(lead_angle_deg=12.5))
        assert _get(obj, 'worm', 'lead_angle_deg') == 12.5

    def test_dataclass_missing_attribute(self):
        obj = _Outer(worm=_Inner())
        assert _get(obj, 'worm', 'nonexistent', default=-1) == -1

    def test_dataclass_none_intermediate(self):
        obj = _Outer(worm=None)
        assert _get(obj, 'worm', 'lead_angle_deg', default=0) == 0


# ===========================================================================
# 2. TestCalculateMinimumTeeth
# ===========================================================================

class TestCalculateMinimumTeeth:

    def test_20_degrees(self):
        assert calculate_minimum_teeth(20.0) == 18

    def test_14_5_degrees(self):
        # 2 / sin²(14.5°) = 2 / 0.0627 ≈ 31.9 → int(31.9)+1 = 32
        assert calculate_minimum_teeth(14.5) == 32

    def test_25_degrees(self):
        # 2 / sin²(25°) ≈ 11.2 → int(11.2)+1 = 12
        assert calculate_minimum_teeth(25.0) == 12

    def test_45_degrees(self):
        # 2 / sin²(45°) = 2/0.5 = 4 → int(4)+1 = 5
        assert calculate_minimum_teeth(45.0) == 5


# ===========================================================================
# 3. TestCalculateRecommendedProfileShift
# ===========================================================================

class TestCalculateRecommendedProfileShift:

    def test_high_teeth_returns_none(self):
        # 30 teeth >= z_min(20°)=18, so no shift needed
        assert calculate_recommended_profile_shift(30, 20.0) is None

    def test_low_teeth_returns_positive(self):
        shift = calculate_recommended_profile_shift(10, 20.0)
        assert shift is not None
        assert shift > 0

    def test_shift_in_valid_range(self):
        shift = calculate_recommended_profile_shift(10, 20.0)
        assert 0.0 < shift <= 0.8

    def test_borderline_at_z_min_returns_none(self):
        z_min = calculate_minimum_teeth(20.0)  # 18
        assert calculate_recommended_profile_shift(z_min, 20.0) is None


# ===========================================================================
# 4. TestNormalizeFunctions
# ===========================================================================

class TestNormalizeProfile:

    def test_string_lowercase(self):
        assert _normalize_profile("za") == "ZA"

    def test_string_uppercase(self):
        assert _normalize_profile("ZK") == "ZK"

    def test_enum_value(self):
        assert _normalize_profile(WormProfile.ZI) == "ZI"

    def test_none(self):
        assert _normalize_profile(None) is None


class TestNormalizeWormType:

    def test_string_uppercase(self):
        assert _normalize_worm_type("GLOBOID") == "globoid"

    def test_enum_value(self):
        assert _normalize_worm_type(WormType.CYLINDRICAL) == "cylindrical"

    def test_none_defaults_to_cylindrical(self):
        assert _normalize_worm_type(None) == "cylindrical"


class TestNormalizeBoreType:

    def test_string_uppercase(self):
        assert _normalize_bore_type("CUSTOM") == "custom"

    def test_enum_value(self):
        assert _normalize_bore_type(BoreType.NONE) == "none"


# ===========================================================================
# 5. TestGetKeywayDepth
# ===========================================================================

class TestGetKeywayDepth:

    def test_below_range(self):
        assert _get_keyway_depth(5.0, is_shaft=True) == 0.0

    def test_above_range(self):
        assert _get_keyway_depth(100.0, is_shaft=True) == 0.0

    def test_6mm_shaft(self):
        # [6, 8) → shaft_depth = 1.2
        assert _get_keyway_depth(6.0, is_shaft=True) == 1.2

    def test_8mm_hub(self):
        # 8.0 is in [8, 10) not [6, 8) → hub_depth = 1.4
        assert _get_keyway_depth(8.0, is_shaft=False) == 1.4

    def test_boundary_7_99(self):
        # 7.99 is in [6, 8) → shaft_depth = 1.2
        assert _get_keyway_depth(7.99, is_shaft=True) == 1.2

    def test_mid_range_20mm_hub(self):
        # 20mm is in [17, 22) → hub_depth = 2.8
        assert _get_keyway_depth(20.0, is_shaft=False) == 2.8


# ===========================================================================
# 6. TestValidateGeometryPossible
# ===========================================================================

class TestValidateGeometryPossible:

    def test_normal_geometry_no_messages(self):
        design = _make_design()
        msgs = _validate_geometry_possible(design)
        assert len(msgs) == 0

    def test_negative_worm_root(self):
        design = _make_design(**{'worm.root_diameter_mm': -1.0})
        codes = _codes(_validate_geometry_possible(design))
        assert 'WORM_IMPOSSIBLE_GEOMETRY' in codes

    def test_zero_worm_root(self):
        design = _make_design(**{'worm.root_diameter_mm': 0})
        codes = _codes(_validate_geometry_possible(design))
        assert 'WORM_ZERO_ROOT' in codes

    def test_negative_wheel_root(self):
        design = _make_design(**{'wheel.root_diameter_mm': -2.0})
        codes = _codes(_validate_geometry_possible(design))
        assert 'WHEEL_IMPOSSIBLE_GEOMETRY' in codes

    def test_zero_wheel_root(self):
        design = _make_design(**{'wheel.root_diameter_mm': 0})
        codes = _codes(_validate_geometry_possible(design))
        assert 'WHEEL_ZERO_ROOT' in codes

    def test_worm_root_exceeds_tip(self):
        design = _make_design(**{
            'worm.root_diameter_mm': 25.0,
            'worm.tip_diameter_mm': 20.0,
        })
        codes = _codes(_validate_geometry_possible(design))
        assert 'WORM_ROOT_EXCEEDS_TIP' in codes

    def test_wheel_tip_reduction_excessive(self):
        design = _make_design(**{
            'wheel.addendum_mm': 2.0,
            'wheel.tip_reduction_mm': 3.0,
        })
        codes = _codes(_validate_geometry_possible(design))
        assert 'WHEEL_TIP_REDUCTION_EXCESSIVE' in codes


# ===========================================================================
# 7. TestValidateWormProportions
# ===========================================================================

class TestValidateWormProportions:

    def test_normal_proportions(self):
        # ratio = 16.29/2.0 = 8.1 — within [5, 20]
        design = _make_design()
        assert _codes(_validate_worm_proportions(design)) == []

    def test_too_thin(self):
        design = _make_design(**{
            'worm.pitch_diameter_mm': 8.0,
            'worm.module_mm': 2.0,
        })
        # ratio = 4.0 < 5
        codes = _codes(_validate_worm_proportions(design))
        assert 'WORM_TOO_THIN' in codes

    def test_too_thick(self):
        design = _make_design(**{
            'worm.pitch_diameter_mm': 42.0,
            'worm.module_mm': 2.0,
        })
        # ratio = 21.0 > 20
        codes = _codes(_validate_worm_proportions(design))
        assert 'WORM_TOO_THICK' in codes


# ===========================================================================
# 8. TestValidatePressureAngle
# ===========================================================================

class TestValidatePressureAngle:

    def test_standard_20_no_messages(self):
        design = _make_design()
        assert _codes(_validate_pressure_angle(design)) == []

    def test_standard_14_5_no_non_standard(self):
        design = _make_design(**{'assembly.pressure_angle_deg': 14.5})
        codes = _codes(_validate_pressure_angle(design))
        assert 'PRESSURE_ANGLE_NON_STANDARD' not in codes

    def test_non_standard_18(self):
        design = _make_design(**{'assembly.pressure_angle_deg': 18.0})
        codes = _codes(_validate_pressure_angle(design))
        assert 'PRESSURE_ANGLE_NON_STANDARD' in codes

    def test_too_low(self):
        design = _make_design(**{'assembly.pressure_angle_deg': 8.0})
        msgs = _validate_pressure_angle(design)
        codes = _codes(msgs)
        assert 'PRESSURE_ANGLE_TOO_LOW' in codes
        assert 'PRESSURE_ANGLE_NON_STANDARD' in codes
        # TOO_LOW should be ERROR
        sev = _severities(msgs)
        assert sev['PRESSURE_ANGLE_TOO_LOW'] == Severity.ERROR

    def test_too_high(self):
        design = _make_design(**{'assembly.pressure_angle_deg': 35.0})
        msgs = _validate_pressure_angle(design)
        codes = _codes(msgs)
        assert 'PRESSURE_ANGLE_TOO_HIGH' in codes
        assert 'PRESSURE_ANGLE_NON_STANDARD' in codes
        sev = _severities(msgs)
        assert sev['PRESSURE_ANGLE_TOO_HIGH'] == Severity.ERROR


# ===========================================================================
# 9. TestValidateClearance
# ===========================================================================

class TestValidateClearance:

    def test_normal_design_no_messages(self):
        design = _make_design()
        assert _codes(_validate_clearance(design)) == []

    def test_geometric_interference(self):
        # Make worm tip huge so it overlaps wheel root at centre distance
        design = _make_design(**{
            'worm.tip_diameter_mm': 80.0,  # radius 40, close to cd=38.14
            'wheel.root_diameter_mm': 55.0,
        })
        msgs = _validate_clearance(design)
        codes = _codes(msgs)
        assert 'GEOMETRIC_INTERFERENCE' in codes
        assert msgs[0].severity == Severity.ERROR

    def test_clearance_marginal(self):
        # clearance = cd - worm_tip/2 - wheel_root/2
        # Want clearance between -0.1 and 0
        # cd=38.14, wheel_root=55 => wheel_root_r=27.5
        # worm_tip_r = 38.14 - 27.5 - (-0.05) = 10.69 => worm_tip = 21.38
        # clearance = 38.14 - 10.69 - 27.5 = -0.05
        design = _make_design(**{
            'worm.tip_diameter_mm': 21.38,
            'wheel.root_diameter_mm': 55.0,
            'assembly.centre_distance_mm': 38.14,
        })
        codes = _codes(_validate_clearance(design))
        assert 'CLEARANCE_MARGINAL' in codes

    def test_clearance_very_small(self):
        # Want clearance between 0 and 0.05
        # cd=38.14, wheel_root_r=27.5
        # worm_tip_r = 38.14 - 27.5 - 0.02 = 10.62 => worm_tip = 21.24
        # clearance = 38.14 - 10.62 - 27.5 = 0.02
        design = _make_design(**{
            'worm.tip_diameter_mm': 21.24,
            'wheel.root_diameter_mm': 55.0,
            'assembly.centre_distance_mm': 38.14,
        })
        codes = _codes(_validate_clearance(design))
        assert 'CLEARANCE_VERY_SMALL' in codes


# ===========================================================================
# 10. TestValidateCentreDistance
# ===========================================================================

class TestValidateCentreDistance:

    def test_normal_cd_no_messages(self):
        design = _make_design()
        assert _codes(_validate_centre_distance(design)) == []

    def test_very_small_cd(self):
        design = _make_design(**{'assembly.centre_distance_mm': 1.5})
        codes = _codes(_validate_centre_distance(design))
        assert 'CENTRE_DISTANCE_SMALL' in codes


# ===========================================================================
# 11. TestValidateProfile
# ===========================================================================

class TestValidateProfile:

    def test_za_valid(self):
        design = _make_design(**{'manufacturing.profile': 'ZA'})
        assert _codes(_validate_profile(design)) == []

    def test_zk_valid(self):
        design = _make_design(**{'manufacturing.profile': 'ZK'})
        assert _codes(_validate_profile(design)) == []

    def test_invalid_profile(self):
        design = _make_design(**{'manufacturing.profile': 'XX'})
        msgs = _validate_profile(design)
        assert 'PROFILE_INVALID' in _codes(msgs)
        assert msgs[0].severity == Severity.ERROR


# ===========================================================================
# 12. TestValidateWormType
# ===========================================================================

class TestValidateWormType:

    def test_cylindrical_valid(self):
        design = _make_design()
        # Default design has no worm.type key → defaults to cylindrical
        assert 'WORM_TYPE_INVALID' not in _codes(_validate_worm_type(design))

    def test_globoid_normal_throat(self):
        design = _make_design(**{
            'worm.type': 'globoid',
            'worm.throat_reduction_mm': 1.0,
            'worm.module_mm': 2.0,
        })
        # throat_reduction 1.0 is in [0.6, 5.0] range for module 2.0
        codes = _codes(_validate_worm_type(design))
        assert 'WORM_TYPE_INVALID' not in codes
        assert 'THROAT_REDUCTION_SMALL' not in codes
        assert 'THROAT_REDUCTION_LARGE' not in codes

    def test_invalid_type(self):
        design = _make_design(**{'worm.type': 'spiral'})
        msgs = _validate_worm_type(design)
        assert 'WORM_TYPE_INVALID' in _codes(msgs)
        assert msgs[0].severity == Severity.ERROR

    def test_globoid_throat_small(self):
        design = _make_design(**{
            'worm.type': 'globoid',
            'worm.throat_reduction_mm': 0.1,
            'worm.module_mm': 2.0,
        })
        # 0.1 < 0.3 * 2.0 = 0.6
        codes = _codes(_validate_worm_type(design))
        assert 'THROAT_REDUCTION_SMALL' in codes

    def test_globoid_throat_large(self):
        design = _make_design(**{
            'worm.type': 'globoid',
            'worm.throat_reduction_mm': 6.0,
            'worm.module_mm': 2.0,
        })
        # 6.0 > 2.5 * 2.0 = 5.0
        codes = _codes(_validate_worm_type(design))
        assert 'THROAT_REDUCTION_LARGE' in codes


# ===========================================================================
# 13. TestValidateManufacturingCompatibility
# ===========================================================================

class TestValidateManufacturingCompatibility:

    def test_no_manufacturing_dims_skips(self):
        design = _make_design()
        # Default design has no worm_length_mm / wheel_width_mm
        assert _codes(_validate_manufacturing_compatibility(design)) == []

    def test_adequate_worm_length(self):
        design = _make_design(**{
            'manufacturing.worm_length_mm': 30.0,
            'manufacturing.wheel_width_mm': 15.0,
            'worm.lead_mm': 6.283,
        })
        # 30 >= 15 + 6.283 → ok
        assert _codes(_validate_manufacturing_compatibility(design)) == []

    def test_short_worm(self):
        design = _make_design(**{
            'manufacturing.worm_length_mm': 15.0,
            'manufacturing.wheel_width_mm': 15.0,
            'worm.lead_mm': 6.283,
        })
        # 15 < 15 + 6.283 = 21.283 → too short
        codes = _codes(_validate_manufacturing_compatibility(design))
        assert 'WORM_LENGTH_SHORT' in codes


# ===========================================================================
# 14. TestValidateSingleBore
# ===========================================================================

class TestValidateSingleBore:
    """Tests for _validate_single_bore() — the shared bore validation helper."""

    def _call(self, bore_type='custom', bore_diameter=8.0, keyway=None,
              pitch_diameter=16.29, root_diameter=11.29, part_name='WORM',
              min_rim=0.5, warn_rim=1.5, is_shaft=True):
        msgs = []
        _validate_single_bore(
            msgs, part_name, bore_type, bore_diameter, keyway,
            pitch_diameter, root_diameter, min_rim, warn_rim, is_shaft,
        )
        return msgs

    def test_bore_type_none_skips(self):
        # non-custom bore_type → early return, no messages
        msgs = self._call(bore_type='none')
        assert msgs == []

    def test_bore_exceeds_root(self):
        msgs = self._call(bore_diameter=12.0, root_diameter=11.29)
        codes = _codes(msgs)
        assert 'WORM_BORE_TOO_LARGE' in codes
        assert msgs[0].severity == Severity.ERROR

    def test_bore_with_keyway_interference(self):
        # bore=10mm, root=11.29mm
        # rim_base = (11.29 - 10) / 2 = 0.645
        # keyway_depth for 10mm shaft: [10,12) → 2.5
        # effective_rim = 0.645 - 2.5 = -1.855 < 0.5 (min_rim)
        msgs = self._call(bore_diameter=10.0, root_diameter=11.29, keyway='DIN6885')
        codes = _codes(msgs)
        assert 'WORM_BORE_KEYWAY_INTERFERENCE' in codes

    def test_bore_insufficient_rim_no_keyway(self):
        # bore=10.5mm, root=11.29mm
        # rim_base = (11.29 - 10.5) / 2 = 0.395 < 0.5 (min_rim)
        msgs = self._call(bore_diameter=10.5, root_diameter=11.29)
        codes = _codes(msgs)
        assert 'WORM_BORE_TOO_LARGE' in codes

    def test_thin_rim_with_keyway(self):
        # Need: min_rim <= effective_rim < warn_rim
        # bore=8mm, root=14mm => rim_base = 3.0
        # keyway_depth for 8mm shaft: [8,10) → 1.8
        # effective_rim = 3.0 - 1.8 = 1.2
        # With min_rim=0.5, warn_rim=1.5: 0.5 <= 1.2 < 1.5 → thin rim warning
        msgs = self._call(bore_diameter=8.0, root_diameter=14.0,
                          keyway='DIN6885', min_rim=0.5, warn_rim=1.5)
        codes = _codes(msgs)
        assert 'WORM_BORE_THIN_RIM_KEYWAY' in codes

    def test_thin_rim_no_keyway(self):
        # bore=12mm, root=14mm => rim_base = 1.0
        # No keyway → effective_rim = 1.0
        # With min_rim=0.5, warn_rim=1.5: 0.5 <= 1.0 < 1.5 → thin rim warning
        msgs = self._call(bore_diameter=12.0, root_diameter=14.0,
                          min_rim=0.5, warn_rim=1.5)
        codes = _codes(msgs)
        assert 'WORM_BORE_THIN_RIM' in codes

    def test_very_small_bore(self):
        # bore=1.5mm < 2.0 (SMALL_BORE_THRESHOLD)
        # root=11.29mm → rim_base = (11.29 - 1.5)/2 = 4.895 → ok
        msgs = self._call(bore_diameter=1.5, root_diameter=11.29)
        codes = _codes(msgs)
        assert 'WORM_BORE_VERY_SMALL' in codes

    def test_very_small_bore_with_ddcut(self):
        msgs = self._call(bore_diameter=1.5, root_diameter=11.29, keyway='DDCUT')
        codes = _codes(msgs)
        assert 'WORM_BORE_VERY_SMALL' in codes
        assert 'WORM_DDCUT_SMALL_BORE' in codes

    def test_auto_bore_too_small_for_bore(self):
        # bore_diameter=None triggers auto-calculation
        # root=3.0mm → max_bore = 3.0 - 2*max(3.0*0.125, 1.0) = 3.0 - 2.0 = 1.0 < 2.0
        # → calculate_default_bore returns (None, False)
        msgs = self._call(bore_diameter=None, pitch_diameter=4.0, root_diameter=3.0)
        codes = _codes(msgs)
        assert 'WORM_TOO_SMALL_FOR_BORE' in codes

    def test_normal_bore_no_error_warning(self):
        # bore=4mm, root=11.29mm → rim_base = 3.645, no keyway
        # adequate rim, bore >= 2mm → no errors or warnings
        msgs = self._call(bore_diameter=4.0, root_diameter=11.29)
        error_or_warn = [m for m in msgs
                         if m.severity in (Severity.ERROR, Severity.WARNING)]
        assert error_or_warn == []


# ===========================================================================
# 15. TestValidateBoreFromSettings
# ===========================================================================

class TestValidateBoreFromSettings:

    def test_both_none_no_messages(self):
        design = _make_design()
        settings = {
            'worm_bore_type': 'none',
            'wheel_bore_type': 'none',
        }
        msgs = _validate_bore_from_settings(design, settings)
        assert msgs == []

    def test_worm_bore_too_large(self):
        design = _make_design()
        settings = {
            'worm_bore_type': 'custom',
            'worm_bore_diameter': 12.0,  # > root 11.29
            'worm_keyway': 'none',
            'wheel_bore_type': 'none',
        }
        msgs = _validate_bore_from_settings(design, settings)
        codes = _codes(msgs)
        assert 'WORM_BORE_TOO_LARGE' in codes

    def test_wheel_bore_with_keyway(self):
        design = _make_design()
        settings = {
            'worm_bore_type': 'none',
            'wheel_bore_type': 'custom',
            'wheel_bore_diameter': 12.0,
            'wheel_keyway': 'DIN6885',
        }
        msgs = _validate_bore_from_settings(design, settings)
        # 12mm bore, root=55mm => rim_base = (55-12)/2 = 21.5
        # keyway [12,17) hub_depth = 2.3 => eff_rim = 19.2 — no problems
        error_msgs = [m for m in msgs if m.severity == Severity.ERROR]
        assert error_msgs == []


# ===========================================================================
# 16. TestValidateBore — the 3-path dispatcher
# ===========================================================================

class TestValidateBore:

    def test_no_features_no_settings_empty(self):
        design = _make_design()
        # No 'features' section, no bore_settings
        msgs = _validate_bore(design, bore_settings=None)
        assert msgs == []

    def test_settings_path_delegates(self):
        design = _make_design()
        settings = {
            'worm_bore_type': 'custom',
            'worm_bore_diameter': 12.0,
            'worm_keyway': 'none',
            'wheel_bore_type': 'none',
        }
        msgs = _validate_bore(design, bore_settings=settings)
        codes = _codes(msgs)
        assert 'WORM_BORE_TOO_LARGE' in codes

    def test_features_worm_custom_validates_root(self):
        design = _make_design()
        design['features'] = {
            'worm': {
                'bore_type': 'custom',
                'bore_diameter_mm': 12.0,  # > root 11.29
                'anti_rotation': 'none',
            },
        }
        msgs = _validate_bore(design, bore_settings=None)
        codes = _codes(msgs)
        assert 'WORM_BORE_TOO_LARGE' in codes

    def test_features_worm_bore_type_missing(self):
        design = _make_design()
        design['features'] = {
            'worm': {
                # bore_type deliberately omitted
                'bore_diameter_mm': 8.0,
            },
        }
        msgs = _validate_bore(design, bore_settings=None)
        codes = _codes(msgs)
        assert 'WORM_BORE_TYPE_MISSING' in codes

    def test_features_worm_custom_diameter_missing(self):
        design = _make_design()
        design['features'] = {
            'worm': {
                'bore_type': 'custom',
                # bore_diameter_mm deliberately omitted
                'anti_rotation': 'none',
            },
        }
        msgs = _validate_bore(design, bore_settings=None)
        codes = _codes(msgs)
        assert 'WORM_BORE_DIAMETER_MISSING' in codes

    def test_features_wheel_custom_with_keyway_ok(self):
        design = _make_design()
        design['features'] = {
            'wheel': {
                'bore_type': 'custom',
                'bore_diameter_mm': 12.0,
                'anti_rotation': AntiRotation.DIN6885,
            },
        }
        # root=55mm, bore=12mm → rim=21.5mm, keyway [12,17) hub_depth=2.3
        # effective_rim = 19.2 → well above thresholds → INFO WHEEL_BORE_OK
        msgs = _validate_bore(design, bore_settings=None)
        codes = _codes(msgs)
        assert 'WHEEL_BORE_OK' in codes
        errors = [m for m in msgs if m.severity == Severity.ERROR]
        assert errors == []


# ===========================================================================
# 17. TestNormalizeEnum — generic normalizer
# ===========================================================================

from wormgear.calculator.validation import _normalize_enum


class TestNormalizeEnum:

    def test_none_returns_default(self):
        assert _normalize_enum(None) is None
        assert _normalize_enum(None, default='foo') == 'foo'

    def test_string_lower(self):
        assert _normalize_enum('HELLO') == 'hello'
        assert _normalize_enum('ZA') == 'za'

    def test_string_upper(self):
        assert _normalize_enum('hello', case='upper') == 'HELLO'

    def test_enum_value_extracted(self):
        assert _normalize_enum(WormProfile.ZA, case='upper') == 'ZA'
        assert _normalize_enum(WormProfile.ZK, case='upper') == 'ZK'
        assert _normalize_enum(BoreType.NONE) == 'none'
        assert _normalize_enum(BoreType.CUSTOM) == 'custom'

    def test_existing_wrappers_still_work(self):
        """Verify the 3 wrapper functions produce identical results to before."""
        from wormgear.calculator.validation import (
            _normalize_profile, _normalize_worm_type, _normalize_bore_type,
        )
        assert _normalize_profile("za") == "ZA"
        assert _normalize_profile(WormProfile.ZI) == "ZI"
        assert _normalize_profile(None) is None

        assert _normalize_worm_type("GLOBOID") == "globoid"
        assert _normalize_worm_type(WormType.CYLINDRICAL) == "cylindrical"
        assert _normalize_worm_type(None) == "cylindrical"

        assert _normalize_bore_type("CUSTOM") == "custom"
        assert _normalize_bore_type(BoreType.NONE) == "none"
        assert _normalize_bore_type(None) is None


# ===========================================================================
# 18. TestSingleBoreBoreOk — BORE_OK info message from _validate_single_bore
# ===========================================================================

class TestSingleBoreBoreOk:

    def test_bore_ok_emitted_with_keyway(self):
        """_validate_single_bore emits BORE_OK when bore+keyway has adequate rim."""
        msgs = []
        # bore=8mm, root=20mm → rim_base = 6.0
        # keyway_depth for 8mm shaft: [8,10) → 1.8
        # effective_rim = 6.0 - 1.8 = 4.2 → well above warn_rim=1.5
        _validate_single_bore(
            msgs, "WORM", "custom", 8.0, "DIN6885",
            16.0, 20.0, 0.5, 1.5, True
        )
        codes = _codes(msgs)
        assert 'WORM_BORE_OK' in codes
        ok_msg = [m for m in msgs if m.code == 'WORM_BORE_OK'][0]
        assert ok_msg.severity == Severity.INFO
        assert '4.20mm' in ok_msg.message

    def test_bore_ok_not_emitted_without_keyway(self):
        """No BORE_OK when there's no keyway (even if bore is fine)."""
        msgs = []
        _validate_single_bore(
            msgs, "WORM", "custom", 4.0, "none",
            16.0, 20.0, 0.5, 1.5, True
        )
        codes = _codes(msgs)
        assert 'WORM_BORE_OK' not in codes
