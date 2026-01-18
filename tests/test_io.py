"""
Tests for the IO module - JSON loading and parameter parsing.
"""

import json
import pytest
from pathlib import Path

from wormgear_geometry.io import (
    load_design_json,
    WormParams,
    WheelParams,
    AssemblyParams,
    WormGearDesign,
)


class TestLoadDesignJson:
    """Tests for load_design_json function."""

    def test_load_valid_json(self, temp_json_file):
        """Test loading a valid JSON design file."""
        design = load_design_json(temp_json_file)

        assert isinstance(design, WormGearDesign)
        assert isinstance(design.worm, WormParams)
        assert isinstance(design.wheel, WheelParams)
        assert isinstance(design.assembly, AssemblyParams)

    def test_load_worm_params(self, temp_json_file):
        """Test that worm parameters are correctly parsed."""
        design = load_design_json(temp_json_file)

        assert design.worm.module_mm == 0.5
        assert design.worm.num_starts == 1
        assert design.worm.pitch_diameter_mm == 6.0
        assert design.worm.tip_diameter_mm == 7.0
        assert design.worm.root_diameter_mm == 4.75
        assert design.worm.lead_mm == 1.571
        assert design.worm.lead_angle_deg == 4.76
        assert design.worm.addendum_mm == 0.5
        assert design.worm.dedendum_mm == 0.625
        assert design.worm.thread_thickness_mm == 0.685

    def test_load_wheel_params(self, temp_json_file):
        """Test that wheel parameters are correctly parsed."""
        design = load_design_json(temp_json_file)

        assert design.wheel.module_mm == 0.5
        assert design.wheel.num_teeth == 12
        assert design.wheel.pitch_diameter_mm == 6.0
        assert design.wheel.tip_diameter_mm == 7.3
        assert design.wheel.root_diameter_mm == 5.05
        assert design.wheel.throat_diameter_mm == 6.5
        assert design.wheel.helix_angle_deg == 85.24
        assert design.wheel.addendum_mm == 0.65
        assert design.wheel.dedendum_mm == 0.475

    def test_load_assembly_params(self, temp_json_file):
        """Test that assembly parameters are correctly parsed."""
        design = load_design_json(temp_json_file)

        assert design.assembly.centre_distance_mm == 6.0
        assert design.assembly.ratio == 12
        assert design.assembly.pressure_angle_deg == 25
        assert design.assembly.backlash_mm == 0.1
        assert design.assembly.hand == "right"

    def test_hand_in_assembly_section(self, tmp_path, sample_design_7mm):
        """Test that hand field in assembly section is correctly handled."""
        # hand is already in assembly section in sample_design_7mm
        json_file = tmp_path / "test.json"
        with open(json_file, 'w') as f:
            json.dump(sample_design_7mm, f)

        design = load_design_json(json_file)
        assert design.worm.hand == "right"
        assert design.assembly.hand == "right"

    def test_hand_in_worm_section(self, tmp_path, sample_design_7mm):
        """Test that hand field in worm section is correctly handled."""
        # Move hand from assembly to worm section
        sample_design_7mm["worm"]["hand"] = "left"
        del sample_design_7mm["assembly"]["hand"]

        json_file = tmp_path / "test.json"
        with open(json_file, 'w') as f:
            json.dump(sample_design_7mm, f)

        design = load_design_json(json_file)
        assert design.worm.hand == "left"

    def test_load_nonexistent_file(self):
        """Test that loading a nonexistent file raises an error."""
        with pytest.raises(FileNotFoundError):
            load_design_json("nonexistent_file.json")

    def test_load_invalid_json(self, tmp_path):
        """Test that loading invalid JSON raises an error."""
        invalid_file = tmp_path / "invalid.json"
        invalid_file.write_text("not valid json {")

        with pytest.raises(json.JSONDecodeError):
            load_design_json(invalid_file)

    def test_load_missing_required_field(self, tmp_path, sample_design_7mm):
        """Test that missing required fields raise an error."""
        # Remove a required field
        del sample_design_7mm["worm"]["module_mm"]

        json_file = tmp_path / "test.json"
        with open(json_file, 'w') as f:
            json.dump(sample_design_7mm, f)

        with pytest.raises(KeyError):
            load_design_json(json_file)

    def test_load_with_optional_fields_missing(self, tmp_path, sample_design_7mm):
        """Test loading JSON with optional fields missing."""
        # Remove optional fields
        if "profile_shift" in sample_design_7mm["worm"]:
            del sample_design_7mm["worm"]["profile_shift"]
        if "profile_shift" in sample_design_7mm["wheel"]:
            del sample_design_7mm["wheel"]["profile_shift"]

        json_file = tmp_path / "test.json"
        with open(json_file, 'w') as f:
            json.dump(sample_design_7mm, f)

        design = load_design_json(json_file)
        assert design.worm.profile_shift == 0.0
        assert design.wheel.profile_shift == 0.0

    def test_load_examples_7mm(self, examples_dir):
        """Test loading the actual 7mm.json example file."""
        example_file = examples_dir / "7mm.json"
        if not example_file.exists():
            pytest.skip("Example file not found")

        design = load_design_json(example_file)
        assert design.worm.module_mm == 0.5
        assert design.wheel.num_teeth == 12


class TestWormParams:
    """Tests for WormParams dataclass."""

    def test_worm_params_creation(self):
        """Test creating WormParams directly."""
        params = WormParams(
            module_mm=1.0,
            num_starts=1,
            pitch_diameter_mm=10.0,
            tip_diameter_mm=12.0,
            root_diameter_mm=7.5,
            lead_mm=3.142,
            lead_angle_deg=9.04,
            addendum_mm=1.0,
            dedendum_mm=1.25,
            thread_thickness_mm=1.37,
            hand="right",
            profile_shift=0.0
        )

        assert params.module_mm == 1.0
        assert params.hand == "right"


class TestWheelParams:
    """Tests for WheelParams dataclass."""

    def test_wheel_params_creation(self):
        """Test creating WheelParams directly."""
        params = WheelParams(
            module_mm=1.0,
            num_teeth=20,
            pitch_diameter_mm=20.0,
            tip_diameter_mm=22.0,
            root_diameter_mm=17.5,
            throat_diameter_mm=21.0,
            helix_angle_deg=80.96,
            addendum_mm=1.0,
            dedendum_mm=1.25,
            profile_shift=0.0
        )

        assert params.num_teeth == 20
        assert params.helix_angle_deg == 80.96


class TestAssemblyParams:
    """Tests for AssemblyParams dataclass."""

    def test_assembly_params_creation(self):
        """Test creating AssemblyParams directly."""
        params = AssemblyParams(
            centre_distance_mm=15.0,
            pressure_angle_deg=20.0,
            backlash_mm=0.05,
            hand="right",
            ratio=20
        )

        assert params.centre_distance_mm == 15.0
        assert params.ratio == 20
