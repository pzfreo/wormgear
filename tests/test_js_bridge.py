"""
Tests for JavaScript-Python bridge.

Tests the clean bridge between JavaScript and Python for the web calculator.
The bridge uses a single entry point: calculate(input_json) -> output_json
"""

import json
import pytest
from wormgear.calculator.js_bridge import (
    calculate,
    sanitize_js_value,
    sanitize_dict,
    BoreSettings,
    ManufacturingSettings,
    CalculatorInputs,
    CalculatorOutput,
)


class JsNull:
    """Mock JsNull class to simulate Pyodide's JavaScript null."""
    pass


class TestSanitizeJsValue:
    """Test sanitize_js_value function (legacy support)."""

    def test_none_returns_none(self):
        assert sanitize_js_value(None) is None

    def test_jsnull_returns_none(self):
        js_null = JsNull()
        result = sanitize_js_value(js_null)
        assert result is None

    def test_empty_string_returns_none(self):
        assert sanitize_js_value('') is None

    def test_boolean_false_returns_false(self):
        assert sanitize_js_value(False) is False

    def test_boolean_true_returns_true(self):
        assert sanitize_js_value(True) is True

    def test_valid_number_returns_unchanged(self):
        assert sanitize_js_value(42) == 42
        assert sanitize_js_value(3.14) == 3.14

    def test_valid_string_returns_unchanged(self):
        assert sanitize_js_value("hello") == "hello"


class TestSanitizeDict:
    """Test sanitize_dict function (legacy support)."""

    def test_empty_dict(self):
        assert sanitize_dict({}) == {}

    def test_none_returns_empty_dict(self):
        assert sanitize_dict(None) == {}

    def test_nested_dict(self):
        input_dict = {
            'level1': {
                'level2': {
                    'value': 42
                }
            }
        }
        result = sanitize_dict(input_dict)
        assert result == input_dict

    def test_list_values(self):
        input_dict = {
            'numbers': [1, 2, 3],
            'strings': ['a', 'b', 'c']
        }
        result = sanitize_dict(input_dict)
        assert result == input_dict


class TestBoreSettings:
    """Test BoreSettings Pydantic model."""

    def test_defaults(self):
        settings = BoreSettings()
        assert settings.worm_bore_type == "none"
        assert settings.worm_bore_diameter is None
        assert settings.worm_keyway == "none"
        assert settings.wheel_bore_type == "none"
        assert settings.wheel_bore_diameter is None
        assert settings.wheel_keyway == "none"

    def test_custom_bore(self):
        settings = BoreSettings(
            worm_bore_type="custom",
            worm_bore_diameter=8.0,
            worm_keyway="DIN6885"
        )
        assert settings.worm_bore_type == "custom"
        assert settings.worm_bore_diameter == 8.0
        assert settings.worm_keyway == "DIN6885"


class TestManufacturingSettings:
    """Test ManufacturingSettings Pydantic model."""

    def test_defaults(self):
        settings = ManufacturingSettings()
        assert settings.virtual_hobbing is False
        assert settings.hobbing_steps == 72
        assert settings.use_recommended_dims is True
        assert settings.worm_length is None
        assert settings.wheel_width is None

    def test_custom_values(self):
        settings = ManufacturingSettings(
            virtual_hobbing=True,
            hobbing_steps=144,
            use_recommended_dims=False,
            worm_length=50.0,
            wheel_width=15.0
        )
        assert settings.virtual_hobbing is True
        assert settings.hobbing_steps == 144
        assert settings.use_recommended_dims is False
        assert settings.worm_length == 50.0
        assert settings.wheel_width == 15.0


class TestCalculatorInputs:
    """Test CalculatorInputs Pydantic model."""

    def test_defaults(self):
        inputs = CalculatorInputs()
        assert inputs.mode == "from-module"
        assert inputs.pressure_angle == 20.0
        assert inputs.backlash == 0.05
        assert inputs.num_starts == 1
        assert inputs.hand == "right"
        assert inputs.profile == "ZA"
        assert inputs.worm_type == "cylindrical"

    def test_normalizes_hand_to_lowercase(self):
        inputs = CalculatorInputs(hand="RIGHT")
        assert inputs.hand == "right"
        inputs = CalculatorInputs(hand="Left")
        assert inputs.hand == "left"

    def test_normalizes_profile_to_uppercase(self):
        inputs = CalculatorInputs(profile="za")
        assert inputs.profile == "ZA"
        inputs = CalculatorInputs(profile="zk")
        assert inputs.profile == "ZK"

    def test_normalizes_worm_type_to_lowercase(self):
        inputs = CalculatorInputs(worm_type="CYLINDRICAL")
        assert inputs.worm_type == "cylindrical"
        inputs = CalculatorInputs(worm_type="Globoid")
        assert inputs.worm_type == "globoid"


class TestCalculate:
    """Test the main calculate() entry point."""

    def test_from_module_success(self):
        """Test successful calculation from module."""
        inputs = {
            'mode': 'from-module',
            'module': 2.0,
            'ratio': 30,
            'pressure_angle': 20.0,
            'backlash': 0.05,
            'num_starts': 1,
            'hand': 'right',
            'profile': 'ZA',
            'worm_type': 'cylindrical',
        }
        result_json = calculate(json.dumps(inputs))
        result = json.loads(result_json)

        assert result['success'] is True
        assert result['valid'] is True
        assert 'design_json' in result
        assert 'summary' in result
        assert 'markdown' in result

        # Verify design structure
        design = json.loads(result['design_json'])
        assert design['worm']['module_mm'] == 2.0
        assert design['assembly']['ratio'] == 30

    def test_from_centre_distance_success(self):
        """Test successful calculation from centre distance."""
        inputs = {
            'mode': 'from-centre-distance',
            'centre_distance': 40.0,
            'ratio': 30,
            'pressure_angle': 20.0,
            'backlash': 0.05,
            'num_starts': 1,
        }
        result_json = calculate(json.dumps(inputs))
        result = json.loads(result_json)

        assert result['success'] is True
        design = json.loads(result['design_json'])
        assert abs(design['assembly']['centre_distance_mm'] - 40.0) < 0.1

    def test_from_wheel_success(self):
        """Test successful calculation from wheel OD."""
        inputs = {
            'mode': 'from-wheel',
            'wheel_od': 65.0,
            'ratio': 30,
            'pressure_angle': 20.0,
            'backlash': 0.05,
            'num_starts': 1,
        }
        result_json = calculate(json.dumps(inputs))
        result = json.loads(result_json)

        assert result['success'] is True

    def test_envelope_success(self):
        """Test successful envelope calculation."""
        inputs = {
            'mode': 'envelope',
            'worm_od': 20.0,
            'wheel_od': 65.0,
            'ratio': 30,
            'pressure_angle': 20.0,
            'backlash': 0.05,
            'num_starts': 1,
            'od_as_maximum': True,
            'use_standard_module': True,
        }
        result_json = calculate(json.dumps(inputs))
        result = json.loads(result_json)

        assert result['success'] is True

    def test_invalid_json_returns_error(self):
        """Test that invalid JSON returns an error."""
        result_json = calculate("not valid json")
        result = json.loads(result_json)

        assert result['success'] is False
        assert 'error' in result
        assert 'Invalid JSON' in result['error']

    def test_missing_required_params_returns_error(self):
        """Test that missing required parameters return an error."""
        inputs = {
            'mode': 'from-module',
            # Missing module and ratio
        }
        result_json = calculate(json.dumps(inputs))
        result = json.loads(result_json)

        assert result['success'] is False
        assert 'error' in result

    def test_globoid_worm_type(self):
        """Test globoid worm type."""
        inputs = {
            'mode': 'from-module',
            'module': 2.0,
            'ratio': 30,
            'worm_type': 'globoid',
            'throat_reduction': 0.2,
        }
        result_json = calculate(json.dumps(inputs))
        result = json.loads(result_json)

        assert result['success'] is True

    def test_left_hand_gear(self):
        """Test left hand gear."""
        inputs = {
            'mode': 'from-module',
            'module': 2.0,
            'ratio': 30,
            'hand': 'left',
        }
        result_json = calculate(json.dumps(inputs))
        result = json.loads(result_json)

        assert result['success'] is True
        design = json.loads(result['design_json'])
        assert design['assembly']['hand'] == 'left'

    def test_manufacturing_settings_passed_through(self):
        """Test that manufacturing settings are passed through."""
        inputs = {
            'mode': 'from-module',
            'module': 2.0,
            'ratio': 30,
            'manufacturing': {
                'virtual_hobbing': True,
                'hobbing_steps': 144,
            },
        }
        result_json = calculate(json.dumps(inputs))
        result = json.loads(result_json)

        assert result['success'] is True
        design = json.loads(result['design_json'])
        assert design['manufacturing']['virtual_hobbing'] is True
        assert design['manufacturing']['hobbing_steps'] == 144

    def test_bore_settings_passed_through(self):
        """Test that bore settings are passed through."""
        inputs = {
            'mode': 'from-module',
            'module': 2.0,
            'ratio': 30,
            'bore': {
                'worm_bore_type': 'auto',
                'worm_keyway': 'DIN6885',
                'wheel_bore_type': 'custom',
                'wheel_bore_diameter': 12.0,
            },
        }
        result_json = calculate(json.dumps(inputs))
        result = json.loads(result_json)

        assert result['success'] is True
        design = json.loads(result['design_json'])
        # Bore settings should be in the output
        assert 'bore' in design or 'features' in design
