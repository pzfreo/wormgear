"""
Tests for JavaScript-Python boundary layer.

These tests ensure proper handling of JavaScript types (null, undefined, etc.)
when passing data between JavaScript and Python in Pyodide.
"""

import pytest
from src.wormgear.calculator.js_bridge import (
    sanitize_js_value,
    sanitize_numeric,
    sanitize_boolean,
    sanitize_string,
    sanitize_dict,
    validate_manufacturing_settings,
    validate_bore_settings,
)


class JsNull:
    """Mock JsNull class to simulate Pyodide's JavaScript null."""
    pass


class TestSanitizeJsValue:
    """Test sanitize_js_value function."""

    def test_none_returns_none(self):
        assert sanitize_js_value(None) is None

    def test_jsnull_returns_none(self):
        # Simulate JsNull object
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


class TestSanitizeNumeric:
    """Test sanitize_numeric function."""

    def test_valid_number(self):
        assert sanitize_numeric(42) == 42.0
        assert sanitize_numeric(3.14) == 3.14

    def test_string_number(self):
        assert sanitize_numeric("42") == 42.0
        assert sanitize_numeric("3.14") == 3.14

    def test_none_with_allow_none(self):
        assert sanitize_numeric(None, allow_none=True) is None

    def test_none_without_allow_none(self):
        with pytest.raises(ValueError):
            sanitize_numeric(None, allow_none=False)

    def test_invalid_with_allow_none(self):
        assert sanitize_numeric("not a number", allow_none=True) is None

    def test_invalid_without_allow_none(self):
        with pytest.raises(ValueError):
            sanitize_numeric("not a number", allow_none=False)


class TestSanitizeBoolean:
    """Test sanitize_boolean function."""

    def test_true(self):
        assert sanitize_boolean(True) is True

    def test_false(self):
        assert sanitize_boolean(False) is False

    def test_none_uses_default(self):
        assert sanitize_boolean(None, default=True) is True
        assert sanitize_boolean(None, default=False) is False

    def test_string_true(self):
        assert sanitize_boolean("true") is True
        assert sanitize_boolean("True") is True
        assert sanitize_boolean("1") is True
        assert sanitize_boolean("yes") is True

    def test_string_false(self):
        assert sanitize_boolean("false") is False
        assert sanitize_boolean("False") is False
        assert sanitize_boolean("0") is False


class TestSanitizeString:
    """Test sanitize_string function."""

    def test_valid_string(self):
        assert sanitize_string("hello") == "hello"

    def test_number_converted_to_string(self):
        assert sanitize_string(42) == "42"

    def test_none_with_allow_none(self):
        assert sanitize_string(None, allow_none=True) is None

    def test_none_without_allow_none(self):
        with pytest.raises(ValueError):
            sanitize_string(None, allow_none=False)


class TestSanitizeDict:
    """Test sanitize_dict function."""

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

    def test_none_values_preserved(self):
        input_dict = {'key': None}
        result = sanitize_dict(input_dict)
        assert 'key' in result
        assert result['key'] is None


class TestValidateManufacturingSettings:
    """Test validate_manufacturing_settings function."""

    def test_empty_settings(self):
        result = validate_manufacturing_settings(None)
        # Should return defaults even when settings is None
        assert result['virtual_hobbing'] is False
        assert result['hobbing_steps'] == 72
        assert result['use_recommended_dims'] is True
        assert result['worm_length'] is None
        assert result['wheel_width'] is None

    def test_valid_settings(self):
        settings = {
            'virtual_hobbing': True,
            'hobbing_steps': 144,
            'use_recommended_dims': False,
            'worm_length': 50.0,
            'wheel_width': 15.0,
        }
        result = validate_manufacturing_settings(settings)
        assert result['virtual_hobbing'] is True
        assert result['hobbing_steps'] == 144
        assert result['use_recommended_dims'] is False
        assert result['worm_length'] == 50.0
        assert result['wheel_width'] == 15.0

    def test_defaults(self):
        settings = {}
        result = validate_manufacturing_settings(settings)
        assert result['virtual_hobbing'] is False
        assert result['hobbing_steps'] == 72
        assert result['use_recommended_dims'] is True
        assert result['worm_length'] is None
        assert result['wheel_width'] is None

    def test_null_dimensions_when_recommended(self):
        settings = {
            'use_recommended_dims': True,
            'worm_length': None,  # JavaScript null
            'wheel_width': None,  # JavaScript null
        }
        result = validate_manufacturing_settings(settings)
        assert result['worm_length'] is None
        assert result['wheel_width'] is None


class TestValidateBoreSettings:
    """Test validate_bore_settings function."""

    def test_empty_settings(self):
        result = validate_bore_settings(None)
        assert result == {}

    def test_worm_auto_bore(self):
        settings = {
            'worm_bore_type': 'auto',
            'worm_keyway': 'DIN6885',
        }
        result = validate_bore_settings(settings)
        assert result['worm_bore_type'] == 'auto'
        assert result['worm_keyway'] == 'DIN6885'

    def test_worm_custom_bore(self):
        settings = {
            'worm_bore_type': 'custom',
            'worm_bore_diameter': 8.0,
            'worm_keyway': 'DIN6885',
        }
        result = validate_bore_settings(settings)
        assert result['worm_bore_type'] == 'custom'
        assert result['worm_bore_diameter'] == 8.0
        assert result['worm_keyway'] == 'DIN6885'

    def test_none_bore_type_filtered(self):
        settings = {
            'worm_bore_type': 'none',  # Should be filtered out
        }
        result = validate_bore_settings(settings)
        assert 'worm_bore_type' not in result

    def test_wheel_bore(self):
        settings = {
            'wheel_bore_type': 'auto',
            'wheel_keyway': 'DIN6885',
        }
        result = validate_bore_settings(settings)
        assert result['wheel_bore_type'] == 'auto'
        assert result['wheel_keyway'] == 'DIN6885'
