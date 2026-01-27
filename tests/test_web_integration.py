"""
Integration test for calculator -> JSON -> generator flow.

Tests the complete web workflow: calculator produces JSON, generator consumes it.
Verifies that all fields are properly serialized and that critical calculations
like throat_reduction_mm are correctly applied.
"""
import json
import pytest
from wormgear.calculator.js_bridge import calculate
from wormgear.io import WormParams, WheelParams, AssemblyParams
from wormgear.core import GloboidWormGeometry


class TestWebIntegration:
    """Tests for the complete web calculator -> generator flow."""

    def test_globoid_throat_reduction_applied(self):
        """Test that throat_reduction_mm affects geometry.

        This was a critical bug: the calculator computed throat_reduction_mm
        but GloboidWormGeometry ignored it entirely.
        """
        input_json = json.dumps({
            'mode': 'from-module',
            'module': 2.0,
            'ratio': 30,
            'pressure_angle': 20.0,
            'backlash': 0.0,
            'num_starts': 1,
            'hand': 'right',
            'profile_shift': 0,
            'profile': 'ZA',
            'worm_type': 'globoid',
            'throat_reduction': 1.0,  # 1mm throat reduction
            'wheel_throated': False,
            'bore': {
                'worm_bore_type': 'none',
                'worm_bore_diameter': None,
                'worm_keyway': 'none',
                'wheel_bore_type': 'none',
                'wheel_bore_diameter': None,
                'wheel_keyway': 'none'
            },
            'manufacturing': {
                'virtual_hobbing': False,
                'hobbing_steps': 72,
                'use_recommended_dims': True,
                'worm_length_mm': None,
                'wheel_width_mm': None
            }
        })

        result = json.loads(calculate(input_json))
        assert result['success'], f"Calculator failed: {result.get('error')}"

        design = json.loads(result['design_json'])

        # Verify throat_reduction_mm is in the output
        assert 'throat_reduction_mm' in design['worm'], \
            "throat_reduction_mm should be in worm params"
        assert design['worm']['throat_reduction_mm'] == 1.0, \
            f"Expected throat_reduction_mm=1.0, got {design['worm'].get('throat_reduction_mm')}"

        # Create geometry objects
        worm = WormParams(**design['worm'])
        assembly = AssemblyParams(**design['assembly'])
        wheel = WheelParams(**design['wheel'])

        # Create globoid worm geometry
        geo = GloboidWormGeometry(
            params=worm,
            assembly_params=assembly,
            wheel_pitch_diameter=wheel.pitch_diameter_mm,
            length=40
        )

        # Verify throat_reduction is applied
        # throat_pitch_radius = centre_distance - wheel_pitch_radius/2 - throat_reduction
        expected = assembly.centre_distance_mm - wheel.pitch_diameter_mm / 2 - worm.throat_reduction_mm
        assert geo.throat_pitch_radius == pytest.approx(expected, rel=0.01), \
            f"Expected throat_pitch_radius={expected:.3f}, got {geo.throat_pitch_radius:.3f}"

    def test_cylindrical_worm_no_throat_reduction(self):
        """Test that cylindrical worms don't use throat_reduction."""
        input_json = json.dumps({
            'mode': 'from-module',
            'module': 2.0,
            'ratio': 30,
            'pressure_angle': 20.0,
            'backlash': 0.0,
            'num_starts': 1,
            'hand': 'right',
            'profile_shift': 0,
            'profile': 'ZA',
            'worm_type': 'cylindrical',
            'throat_reduction': 0,
            'wheel_throated': False,
            'bore': {
                'worm_bore_type': 'none',
                'worm_bore_diameter': None,
                'worm_keyway': 'none',
                'wheel_bore_type': 'none',
                'wheel_bore_diameter': None,
                'wheel_keyway': 'none'
            },
            'manufacturing': {
                'virtual_hobbing': False,
                'hobbing_steps': 72,
                'use_recommended_dims': True,
                'worm_length_mm': None,
                'wheel_width_mm': None
            }
        })

        result = json.loads(calculate(input_json))
        assert result['success'], f"Calculator failed: {result.get('error')}"

        design = json.loads(result['design_json'])
        assert design['worm']['type'] == 'cylindrical'

    def test_enum_values_are_strings_in_json(self):
        """Verify enums are serialized as strings in JSON, not enum objects."""
        input_json = json.dumps({
            'mode': 'from-module',
            'module': 2.0,
            'ratio': 30,
            'pressure_angle': 20.0,
            'backlash': 0.0,
            'num_starts': 1,
            'hand': 'left',
            'profile_shift': 0,
            'profile': 'ZK',
            'worm_type': 'globoid',
            'throat_reduction': 0.5,
            'wheel_throated': False,
            'bore': {
                'worm_bore_type': 'none',
                'worm_bore_diameter': None,
                'worm_keyway': 'none',
                'wheel_bore_type': 'none',
                'wheel_bore_diameter': None,
                'wheel_keyway': 'none'
            },
            'manufacturing': {
                'virtual_hobbing': False,
                'hobbing_steps': 72,
                'use_recommended_dims': True,
                'worm_length_mm': None,
                'wheel_width_mm': None
            }
        })

        result = json.loads(calculate(input_json))
        assert result['success'], f"Calculator failed: {result.get('error')}"

        design = json.loads(result['design_json'])

        # All enum values should be plain strings
        assert design['worm']['type'] == 'globoid', \
            f"worm.type should be 'globoid' string, got {design['worm']['type']}"
        assert design['worm']['hand'] == 'left', \
            f"worm.hand should be 'left' string, got {design['worm']['hand']}"
        assert design['assembly']['hand'] == 'left', \
            f"assembly.hand should be 'left' string, got {design['assembly']['hand']}"
        assert design['manufacturing']['profile'] == 'ZK', \
            f"manufacturing.profile should be 'ZK' string, got {design['manufacturing'].get('profile')}"

    def test_manufacturing_params_present(self):
        """Verify manufacturing section has required fields."""
        input_json = json.dumps({
            'mode': 'from-module',
            'module': 2.0,
            'ratio': 30,
            'pressure_angle': 20.0,
            'backlash': 0.0,
            'num_starts': 1,
            'hand': 'right',
            'profile_shift': 0,
            'profile': 'ZA',
            'worm_type': 'cylindrical',
            'throat_reduction': 0,
            'wheel_throated': False,
            'bore': {
                'worm_bore_type': 'none',
                'worm_bore_diameter': None,
                'worm_keyway': 'none',
                'wheel_bore_type': 'none',
                'wheel_bore_diameter': None,
                'wheel_keyway': 'none'
            },
            'manufacturing': {
                'virtual_hobbing': True,
                'hobbing_steps': 144,
                'use_recommended_dims': True,
                'worm_length_mm': 50.0,
                'wheel_width_mm': 25.0
            }
        })

        result = json.loads(calculate(input_json))
        assert result['success'], f"Calculator failed: {result.get('error')}"

        design = json.loads(result['design_json'])

        # Check manufacturing section exists
        assert 'manufacturing' in design, "manufacturing section missing"
        mfg = design['manufacturing']

        # Check required fields
        assert 'worm_length_mm' in mfg, "worm_length_mm missing from manufacturing"
        assert 'wheel_width_mm' in mfg, "wheel_width_mm missing from manufacturing"
        assert mfg['worm_length_mm'] is not None, "worm_length_mm should be set"
        assert mfg['wheel_width_mm'] is not None, "wheel_width_mm should be set"

    def test_required_geometry_fields_present(self):
        """Verify all fields required by geometry generators are present."""
        input_json = json.dumps({
            'mode': 'from-module',
            'module': 2.0,
            'ratio': 30,
            'pressure_angle': 20.0,
            'backlash': 0.05,
            'num_starts': 1,
            'hand': 'right',
            'profile_shift': 0.1,
            'profile': 'ZA',
            'worm_type': 'cylindrical',
            'throat_reduction': 0,
            'wheel_throated': False,
            'bore': {
                'worm_bore_type': 'none',
                'worm_bore_diameter': None,
                'worm_keyway': 'none',
                'wheel_bore_type': 'none',
                'wheel_bore_diameter': None,
                'wheel_keyway': 'none'
            },
            'manufacturing': {
                'virtual_hobbing': False,
                'hobbing_steps': 72,
                'use_recommended_dims': True,
                'worm_length_mm': None,
                'wheel_width_mm': None
            }
        })

        result = json.loads(calculate(input_json))
        assert result['success'], f"Calculator failed: {result.get('error')}"

        design = json.loads(result['design_json'])

        # Required worm fields for geometry generation
        worm_required = [
            'module_mm', 'num_starts', 'pitch_diameter_mm', 'tip_diameter_mm',
            'root_diameter_mm', 'lead_mm', 'lead_angle_deg', 'addendum_mm',
            'dedendum_mm', 'thread_thickness_mm', 'hand'
        ]
        for field in worm_required:
            assert field in design['worm'], f"worm.{field} required but missing"

        # Required wheel fields for geometry generation
        wheel_required = [
            'module_mm', 'num_teeth', 'pitch_diameter_mm', 'tip_diameter_mm',
            'root_diameter_mm', 'addendum_mm', 'dedendum_mm'
        ]
        for field in wheel_required:
            assert field in design['wheel'], f"wheel.{field} required but missing"

        # Required assembly fields for geometry generation
        assembly_required = [
            'centre_distance_mm', 'pressure_angle_deg', 'backlash_mm', 'hand', 'ratio'
        ]
        for field in assembly_required:
            assert field in design['assembly'], f"assembly.{field} required but missing"


class TestJsBridgeValidation:
    """Tests for the JS bridge input validation."""

    def test_invalid_mode_rejected(self):
        """Test that invalid mode values are rejected."""
        input_json = json.dumps({
            'mode': 'invalid-mode',
            'module': 2.0,
            'ratio': 30,
            'pressure_angle': 20.0,
            'backlash': 0.0,
            'num_starts': 1,
            'hand': 'right',
            'profile_shift': 0,
            'profile': 'ZA',
            'worm_type': 'cylindrical',
            'throat_reduction': 0,
            'wheel_throated': False,
            'bore': {
                'worm_bore_type': 'none',
                'worm_bore_diameter': None,
                'worm_keyway': 'none',
                'wheel_bore_type': 'none',
                'wheel_bore_diameter': None,
                'wheel_keyway': 'none'
            },
            'manufacturing': {
                'virtual_hobbing': False,
                'hobbing_steps': 72,
                'use_recommended_dims': True,
                'worm_length_mm': None,
                'wheel_width_mm': None
            }
        })

        result = json.loads(calculate(input_json))
        assert not result['success'], "Should reject invalid mode"
        assert 'error' in result

    def test_missing_required_param_rejected(self):
        """Test that missing required parameters are rejected."""
        # Missing ratio
        input_json = json.dumps({
            'mode': 'from-module',
            'module': 2.0,
            # ratio missing
            'pressure_angle': 20.0,
            'backlash': 0.0,
            'num_starts': 1,
            'hand': 'right',
            'profile_shift': 0,
            'profile': 'ZA',
            'worm_type': 'cylindrical',
            'throat_reduction': 0,
            'wheel_throated': False,
            'bore': {
                'worm_bore_type': 'none',
                'worm_bore_diameter': None,
                'worm_keyway': 'none',
                'wheel_bore_type': 'none',
                'wheel_bore_diameter': None,
                'wheel_keyway': 'none'
            },
            'manufacturing': {
                'virtual_hobbing': False,
                'hobbing_steps': 72,
                'use_recommended_dims': True,
                'worm_length_mm': None,
                'wheel_width_mm': None
            }
        })

        result = json.loads(calculate(input_json))
        assert not result['success'], "Should reject missing ratio"
        assert 'error' in result
