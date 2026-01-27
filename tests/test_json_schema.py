"""
Tests for JSON schema validation.

These tests ensure the JSON schema validator correctly validates
the structure and types of wormgear JSON documents.
"""

import pytest
from wormgear.calculator.json_schema import (
    validate_design_json,
    validate_and_raise,
    ValidationError,
)


class TestValidateDesignJson:
    """Test validate_design_json function."""

    def test_valid_minimal_design(self):
        """Minimal valid design should pass validation."""
        data = {
            "worm": {
                "module_mm": 2.0,
                "num_starts": 1,
                "pitch_diameter_mm": 16.0,
                "tip_diameter_mm": 20.0,
                "root_diameter_mm": 11.0,
                "lead_mm": 6.283,
                "lead_angle_deg": 7.0,
                "addendum_mm": 2.0,
                "dedendum_mm": 2.5,
                "thread_thickness_mm": 3.14,
                "hand": "right",
            },
            "wheel": {
                "module_mm": 2.0,
                "num_teeth": 30,
                "pitch_diameter_mm": 60.0,
                "tip_diameter_mm": 64.0,
                "root_diameter_mm": 55.0,
                "throat_diameter_mm": 62.0,
                "helix_angle_deg": 83.0,
                "addendum_mm": 2.0,
                "dedendum_mm": 2.5,
            },
            "assembly": {
                "centre_distance_mm": 38.0,
                "pressure_angle_deg": 20.0,
                "backlash_mm": 0.05,
                "ratio": 30.0,
                "hand": "right",
            },
        }
        is_valid, errors = validate_design_json(data)
        assert is_valid, f"Validation failed: {errors}"
        assert len(errors) == 0

    def test_missing_root_section(self):
        """Missing required root sections should fail."""
        data = {
            "worm": {},
            # Missing wheel and assembly
        }
        is_valid, errors = validate_design_json(data)
        assert not is_valid
        assert any("wheel" in e for e in errors)
        assert any("assembly" in e for e in errors)

    def test_invalid_root_type(self):
        """Root must be a dict."""
        is_valid, errors = validate_design_json([])
        assert not is_valid
        assert "Root must be a JSON object/dict" in errors

    def test_missing_worm_field(self):
        """Missing required worm fields should fail."""
        data = {
            "worm": {
                "module_mm": 2.0,
                # Missing other required fields
            },
            "wheel": {
                "module_mm": 2.0,
                "num_teeth": 30,
                "pitch_diameter_mm": 60.0,
                "tip_diameter_mm": 64.0,
                "root_diameter_mm": 55.0,
                "throat_diameter_mm": 62.0,
                "helix_angle_deg": 83.0,
                "addendum_mm": 2.0,
                "dedendum_mm": 2.5,
            },
            "assembly": {
                "centre_distance_mm": 38.0,
                "pressure_angle_deg": 20.0,
                "backlash_mm": 0.05,
                "ratio": 30.0,
                "hand": "right",
            },
        }
        is_valid, errors = validate_design_json(data)
        assert not is_valid
        assert any("num_starts" in e for e in errors)

    def test_invalid_worm_field_type(self):
        """Worm fields with wrong types should fail."""
        data = {
            "worm": {
                "module_mm": "not a number",  # Invalid type
                "num_starts": 1,
                "pitch_diameter_mm": 16.0,
                "tip_diameter_mm": 20.0,
                "root_diameter_mm": 11.0,
                "lead_mm": 6.283,
                "lead_angle_deg": 7.0,
                "addendum_mm": 2.0,
                "dedendum_mm": 2.5,
                "thread_thickness_mm": 3.14,
                "hand": "right",
            },
            "wheel": {
                "module_mm": 2.0,
                "num_teeth": 30,
                "pitch_diameter_mm": 60.0,
                "tip_diameter_mm": 64.0,
                "root_diameter_mm": 55.0,
                "throat_diameter_mm": 62.0,
                "helix_angle_deg": 83.0,
                "addendum_mm": 2.0,
                "dedendum_mm": 2.5,
            },
            "assembly": {
                "centre_distance_mm": 38.0,
                "pressure_angle_deg": 20.0,
                "backlash_mm": 0.05,
                "ratio": 30.0,
                "hand": "right",
            },
        }
        is_valid, errors = validate_design_json(data)
        assert not is_valid
        assert any("module_mm" in e and "numeric" in e for e in errors)

    def test_invalid_hand_value(self):
        """Hand must be 'right' or 'left'."""
        data = {
            "worm": {
                "module_mm": 2.0,
                "num_starts": 1,
                "pitch_diameter_mm": 16.0,
                "tip_diameter_mm": 20.0,
                "root_diameter_mm": 11.0,
                "lead_mm": 6.283,
                "lead_angle_deg": 7.0,
                "addendum_mm": 2.0,
                "dedendum_mm": 2.5,
                "thread_thickness_mm": 3.14,
                "hand": "invalid",  # Invalid value
            },
            "wheel": {
                "module_mm": 2.0,
                "num_teeth": 30,
                "pitch_diameter_mm": 60.0,
                "tip_diameter_mm": 64.0,
                "root_diameter_mm": 55.0,
                "throat_diameter_mm": 62.0,
                "helix_angle_deg": 83.0,
                "addendum_mm": 2.0,
                "dedendum_mm": 2.5,
            },
            "assembly": {
                "centre_distance_mm": 38.0,
                "pressure_angle_deg": 20.0,
                "backlash_mm": 0.05,
                "ratio": 30.0,
                "hand": "right",
            },
        }
        is_valid, errors = validate_design_json(data)
        assert not is_valid
        assert any("hand" in e and "right" in e and "left" in e for e in errors)

    def test_optional_manufacturing_section(self):
        """Manufacturing section is optional but must be valid if present."""
        data = {
            "worm": {
                "module_mm": 2.0,
                "num_starts": 1,
                "pitch_diameter_mm": 16.0,
                "tip_diameter_mm": 20.0,
                "root_diameter_mm": 11.0,
                "lead_mm": 6.283,
                "lead_angle_deg": 7.0,
                "addendum_mm": 2.0,
                "dedendum_mm": 2.5,
                "thread_thickness_mm": 3.14,
                "hand": "right",
            },
            "wheel": {
                "module_mm": 2.0,
                "num_teeth": 30,
                "pitch_diameter_mm": 60.0,
                "tip_diameter_mm": 64.0,
                "root_diameter_mm": 55.0,
                "throat_diameter_mm": 62.0,
                "helix_angle_deg": 83.0,
                "addendum_mm": 2.0,
                "dedendum_mm": 2.5,
            },
            "assembly": {
                "centre_distance_mm": 38.0,
                "pressure_angle_deg": 20.0,
                "backlash_mm": 0.05,
                "ratio": 30.0,
                "hand": "right",
            },
            "manufacturing": {
                "worm_type": "cylindrical",
                "profile": "ZA",
                "virtual_hobbing": True,
                "hobbing_steps": 72,
            },
        }
        is_valid, errors = validate_design_json(data)
        assert is_valid, f"Validation failed: {errors}"

    def test_invalid_manufacturing_worm_type(self):
        """Invalid manufacturing worm_type should fail."""
        data = {
            "worm": {
                "module_mm": 2.0,
                "num_starts": 1,
                "pitch_diameter_mm": 16.0,
                "tip_diameter_mm": 20.0,
                "root_diameter_mm": 11.0,
                "lead_mm": 6.283,
                "lead_angle_deg": 7.0,
                "addendum_mm": 2.0,
                "dedendum_mm": 2.5,
                "thread_thickness_mm": 3.14,
                "hand": "right",
            },
            "wheel": {
                "module_mm": 2.0,
                "num_teeth": 30,
                "pitch_diameter_mm": 60.0,
                "tip_diameter_mm": 64.0,
                "root_diameter_mm": 55.0,
                "throat_diameter_mm": 62.0,
                "helix_angle_deg": 83.0,
                "addendum_mm": 2.0,
                "dedendum_mm": 2.5,
            },
            "assembly": {
                "centre_distance_mm": 38.0,
                "pressure_angle_deg": 20.0,
                "backlash_mm": 0.05,
                "ratio": 30.0,
                "hand": "right",
            },
            "manufacturing": {
                "worm_type": "invalid",  # Invalid value
            },
        }
        is_valid, errors = validate_design_json(data)
        assert not is_valid
        assert any("worm_type" in e for e in errors)

    def test_optional_features_section(self):
        """Features section is optional but must be valid if present."""
        data = {
            "worm": {
                "module_mm": 2.0,
                "num_starts": 1,
                "pitch_diameter_mm": 16.0,
                "tip_diameter_mm": 20.0,
                "root_diameter_mm": 11.0,
                "lead_mm": 6.283,
                "lead_angle_deg": 7.0,
                "addendum_mm": 2.0,
                "dedendum_mm": 2.5,
                "thread_thickness_mm": 3.14,
                "hand": "right",
            },
            "wheel": {
                "module_mm": 2.0,
                "num_teeth": 30,
                "pitch_diameter_mm": 60.0,
                "tip_diameter_mm": 64.0,
                "root_diameter_mm": 55.0,
                "throat_diameter_mm": 62.0,
                "helix_angle_deg": 83.0,
                "addendum_mm": 2.0,
                "dedendum_mm": 2.5,
            },
            "assembly": {
                "centre_distance_mm": 38.0,
                "pressure_angle_deg": 20.0,
                "backlash_mm": 0.05,
                "ratio": 30.0,
                "hand": "right",
            },
            "features": {
                "worm": {
                    "bore_diameter_mm": 8.0,
                    "auto_bore": False,
                    "anti_rotation": "DIN6885",
                },
                "wheel": {
                    "bore_diameter_mm": 12.0,
                    "auto_bore": False,
                    "anti_rotation": "none",
                },
            },
        }
        is_valid, errors = validate_design_json(data)
        assert is_valid, f"Validation failed: {errors}"

    def test_invalid_bore_diameter(self):
        """Bore diameter must be positive numeric."""
        data = {
            "worm": {
                "module_mm": 2.0,
                "num_starts": 1,
                "pitch_diameter_mm": 16.0,
                "tip_diameter_mm": 20.0,
                "root_diameter_mm": 11.0,
                "lead_mm": 6.283,
                "lead_angle_deg": 7.0,
                "addendum_mm": 2.0,
                "dedendum_mm": 2.5,
                "thread_thickness_mm": 3.14,
                "hand": "right",
            },
            "wheel": {
                "module_mm": 2.0,
                "num_teeth": 30,
                "pitch_diameter_mm": 60.0,
                "tip_diameter_mm": 64.0,
                "root_diameter_mm": 55.0,
                "throat_diameter_mm": 62.0,
                "helix_angle_deg": 83.0,
                "addendum_mm": 2.0,
                "dedendum_mm": 2.5,
            },
            "assembly": {
                "centre_distance_mm": 38.0,
                "pressure_angle_deg": 20.0,
                "backlash_mm": 0.05,
                "ratio": 30.0,
                "hand": "right",
            },
            "features": {
                "worm": {
                    "bore_diameter_mm": -5.0,  # Invalid (negative)
                },
            },
        }
        is_valid, errors = validate_design_json(data)
        assert not is_valid
        assert any("bore_diameter_mm" in e and "positive" in e for e in errors)


class TestValidateAndRaise:
    """Test validate_and_raise function."""

    def test_valid_design_no_exception(self):
        """Valid design should not raise."""
        data = {
            "worm": {
                "module_mm": 2.0,
                "num_starts": 1,
                "pitch_diameter_mm": 16.0,
                "tip_diameter_mm": 20.0,
                "root_diameter_mm": 11.0,
                "lead_mm": 6.283,
                "lead_angle_deg": 7.0,
                "addendum_mm": 2.0,
                "dedendum_mm": 2.5,
                "thread_thickness_mm": 3.14,
                "hand": "right",
            },
            "wheel": {
                "module_mm": 2.0,
                "num_teeth": 30,
                "pitch_diameter_mm": 60.0,
                "tip_diameter_mm": 64.0,
                "root_diameter_mm": 55.0,
                "throat_diameter_mm": 62.0,
                "helix_angle_deg": 83.0,
                "addendum_mm": 2.0,
                "dedendum_mm": 2.5,
            },
            "assembly": {
                "centre_distance_mm": 38.0,
                "pressure_angle_deg": 20.0,
                "backlash_mm": 0.05,
                "ratio": 30.0,
                "hand": "right",
            },
        }
        # Should not raise
        validate_and_raise(data)

    def test_invalid_design_raises_validation_error(self):
        """Invalid design should raise ValidationError."""
        data = {
            "worm": {},  # Missing required fields
            "wheel": {},
            "assembly": {},
        }
        with pytest.raises(ValidationError) as exc_info:
            validate_and_raise(data)

        error_msg = str(exc_info.value)
        assert "JSON validation failed" in error_msg
        assert "missing required field" in error_msg
