"""
Tests for the IO module - JSON loading and parameter parsing.
"""

import json
import pytest
from pathlib import Path

from wormgear import (
    load_design_json,
    save_design_json,
    WormParams,
    WheelParams,
    AssemblyParams,
    WormGearDesign,
    ManufacturingParams,
    Hand,
    WormProfile,
)
from wormgear.io.loaders import ManufacturingFeatures


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
        assert design.assembly.hand == Hand.RIGHT

    def test_hand_in_assembly_section(self, tmp_path, sample_design_7mm):
        """Test that hand field in assembly section is correctly handled."""
        # hand is already in assembly section in sample_design_7mm
        json_file = tmp_path / "test.json"
        with open(json_file, 'w') as f:
            json.dump(sample_design_7mm, f)

        design = load_design_json(json_file)
        assert design.worm.hand == Hand.RIGHT
        assert design.assembly.hand == Hand.RIGHT

    def test_hand_in_worm_section(self, tmp_path, sample_design_7mm):
        """Test that hand field in worm section is correctly handled."""
        # Move hand from assembly to worm section
        sample_design_7mm["worm"]["hand"] = "left"
        del sample_design_7mm["assembly"]["hand"]

        json_file = tmp_path / "test.json"
        with open(json_file, 'w') as f:
            json.dump(sample_design_7mm, f)

        design = load_design_json(json_file)
        assert design.worm.hand == Hand.LEFT

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
        from pydantic import ValidationError

        # Remove a required field
        del sample_design_7mm["worm"]["module_mm"]

        json_file = tmp_path / "test.json"
        with open(json_file, 'w') as f:
            json.dump(sample_design_7mm, f)

        with pytest.raises(ValidationError):
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
        import math
        params = WormParams(
            module_mm=1.0,
            num_starts=1,
            pitch_diameter_mm=10.0,
            tip_diameter_mm=12.0,
            root_diameter_mm=7.5,
            lead_mm=3.142,
            axial_pitch_mm=1.0 * math.pi,
            lead_angle_deg=9.04,
            addendum_mm=1.0,
            dedendum_mm=1.25,
            thread_thickness_mm=1.37,
            hand="right",
            profile_shift=0.0
        )

        assert params.module_mm == 1.0
        assert params.hand == Hand.RIGHT


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


class TestManufacturingParams:
    """Tests for ManufacturingParams dataclass and profile serialization."""

    def test_manufacturing_params_default_profile(self):
        """Test that default profile is ZA."""
        params = ManufacturingParams()
        assert params.profile == WormProfile.ZA

    def test_manufacturing_params_zk_profile(self):
        """Test setting ZK profile."""
        params = ManufacturingParams(profile="ZK")
        assert params.profile == WormProfile.ZK

    def test_manufacturing_params_all_fields(self):
        """Test creating ManufacturingParams with all fields."""
        params = ManufacturingParams(
            profile="ZK",
            virtual_hobbing=True,
            hobbing_steps=24,
            throated_wheel=True,
            sections_per_turn=48
        )

        assert params.profile == WormProfile.ZK
        assert params.virtual_hobbing is True
        assert params.hobbing_steps == 24
        assert params.throated_wheel is True
        assert params.sections_per_turn == 48


class TestProfileJsonSerialization:
    """Tests for profile field JSON serialization."""

    @pytest.fixture
    def base_design(self, sample_design_7mm):
        """Create a base WormGearDesign from sample data."""
        import math
        module_mm = sample_design_7mm["worm"]["module_mm"]
        return WormGearDesign(
            worm=WormParams(
                module_mm=module_mm,
                num_starts=sample_design_7mm["worm"]["num_starts"],
                pitch_diameter_mm=sample_design_7mm["worm"]["pitch_diameter_mm"],
                tip_diameter_mm=sample_design_7mm["worm"]["tip_diameter_mm"],
                root_diameter_mm=sample_design_7mm["worm"]["root_diameter_mm"],
                lead_mm=sample_design_7mm["worm"]["lead_mm"],
                axial_pitch_mm=module_mm * math.pi,
                lead_angle_deg=sample_design_7mm["worm"]["lead_angle_deg"],
                addendum_mm=sample_design_7mm["worm"]["addendum_mm"],
                dedendum_mm=sample_design_7mm["worm"]["dedendum_mm"],
                thread_thickness_mm=sample_design_7mm["worm"]["thread_thickness_mm"],
                hand="right",
                profile_shift=0.0
            ),
            wheel=WheelParams(
                module_mm=sample_design_7mm["wheel"]["module_mm"],
                num_teeth=sample_design_7mm["wheel"]["num_teeth"],
                pitch_diameter_mm=sample_design_7mm["wheel"]["pitch_diameter_mm"],
                tip_diameter_mm=sample_design_7mm["wheel"]["tip_diameter_mm"],
                root_diameter_mm=sample_design_7mm["wheel"]["root_diameter_mm"],
                throat_diameter_mm=sample_design_7mm["wheel"]["throat_diameter_mm"],
                helix_angle_deg=sample_design_7mm["wheel"]["helix_angle_deg"],
                addendum_mm=sample_design_7mm["wheel"]["addendum_mm"],
                dedendum_mm=sample_design_7mm["wheel"]["dedendum_mm"],
                profile_shift=0.0
            ),
            assembly=AssemblyParams(
                centre_distance_mm=sample_design_7mm["assembly"]["centre_distance_mm"],
                pressure_angle_deg=sample_design_7mm["assembly"]["pressure_angle_deg"],
                backlash_mm=sample_design_7mm["assembly"]["backlash_mm"],
                hand=sample_design_7mm["assembly"]["hand"],
                ratio=sample_design_7mm["assembly"]["ratio"]
            )
        )

    def test_save_and_load_za_profile(self, tmp_path, base_design):
        """Test saving and loading ZA profile."""
        base_design.manufacturing = ManufacturingParams(profile="ZA")

        json_file = tmp_path / "test_za.json"
        save_design_json(base_design, json_file)

        loaded = load_design_json(json_file)
        assert loaded.manufacturing is not None
        assert loaded.manufacturing.profile == WormProfile.ZA

    def test_save_and_load_zk_profile(self, tmp_path, base_design):
        """Test saving and loading ZK profile."""
        base_design.manufacturing = ManufacturingParams(profile="ZK")

        json_file = tmp_path / "test_zk.json"
        save_design_json(base_design, json_file)

        loaded = load_design_json(json_file)
        assert loaded.manufacturing is not None
        assert loaded.manufacturing.profile == WormProfile.ZK

    def test_profile_in_saved_json_content(self, tmp_path, base_design):
        """Test that profile field appears correctly in saved JSON."""
        base_design.manufacturing = ManufacturingParams(profile="ZK")

        json_file = tmp_path / "test.json"
        save_design_json(base_design, json_file)

        with open(json_file) as f:
            data = json.load(f)

        assert "manufacturing" in data
        assert "profile" in data["manufacturing"]
        assert data["manufacturing"]["profile"] == "ZK"

    def test_load_json_without_profile_defaults_to_za(self, tmp_path, sample_design_7mm):
        """Test that loading JSON without profile defaults to ZA."""
        # Add manufacturing section without profile
        sample_design_7mm["manufacturing"] = {
            "worm_type": "cylindrical",
            "worm_length": 40.0
        }

        json_file = tmp_path / "test.json"
        with open(json_file, 'w') as f:
            json.dump(sample_design_7mm, f)

        loaded = load_design_json(json_file)
        assert loaded.manufacturing is not None
        assert loaded.manufacturing.profile == WormProfile.ZA

    def test_save_complete_design_with_all_manufacturing(self, tmp_path, base_design):
        """Test saving complete design with all manufacturing and features."""
        from wormgear import Features, WormFeatures, WheelFeatures, HubSpec, SetScrewSpec

        base_design.manufacturing = ManufacturingParams(
            profile="ZK",
            virtual_hobbing=True,
            hobbing_steps=24,
            throated_wheel=True,
            sections_per_turn=48
        )

        base_design.features = Features(
            worm=WormFeatures(
                bore_type="custom",
                bore_diameter_mm=8.0,
                anti_rotation="DIN6885"
            ),
            wheel=WheelFeatures(
                bore_type="custom",
                bore_diameter_mm=12.0,
                anti_rotation="DIN6885",
                hub=HubSpec(type="extended", length_mm=15.0)
            )
        )

        json_file = tmp_path / "complete.json"
        save_design_json(base_design, json_file)

        loaded = load_design_json(json_file)
        assert loaded.manufacturing is not None
        assert loaded.manufacturing.profile == WormProfile.ZK
        assert loaded.manufacturing.virtual_hobbing is True
        assert loaded.features is not None
        assert loaded.features.worm is not None
        assert loaded.features.worm.bore_type.value == "custom"
        assert loaded.features.worm.bore_diameter_mm == 8.0
        assert loaded.features.wheel is not None
        assert loaded.features.wheel.bore_type.value == "custom"
        assert loaded.features.wheel.hub is not None
        assert loaded.features.wheel.hub.type == "extended"


class TestSchemaMigration:
    """Tests for schema version detection and migration."""

    def test_detect_schema_version_explicit(self):
        """Test detecting explicit schema version."""
        from wormgear.io.schema import detect_schema_version

        data = {"schema_version": "2.0", "worm": {}}
        assert detect_schema_version(data) == "2.0"

        data = {"schema_version": "1.0", "worm": {}}
        assert detect_schema_version(data) == "1.0"

    def test_detect_schema_version_heuristics(self):
        """Test detecting schema version via heuristics."""
        from wormgear.io.schema import detect_schema_version

        # Has features section -> 2.0
        data = {"worm": {}, "features": {"worm": {}}}
        assert detect_schema_version(data) == "2.0"

        # No features, no version -> 1.0
        data = {"worm": {}}
        assert detect_schema_version(data) == "1.0"

    def test_upgrade_schema_no_change_needed(self):
        """Test upgrade_schema when already at target version."""
        from wormgear.io.schema import upgrade_schema

        data = {
            "schema_version": "2.0",
            "worm": {},
            "wheel": {},
            "assembly": {},
            "features": {"worm": {"bore_type": "auto"}}
        }

        result = upgrade_schema(data, "2.0")
        assert result["schema_version"] == "2.0"
        assert result["features"]["worm"]["bore_type"] == "auto"

    def test_upgrade_schema_migrates_features(self):
        """Test that features in manufacturing are migrated to features section."""
        from wormgear.io.schema import upgrade_schema

        old_data = {
            "schema_version": "1.0",
            "worm": {},
            "wheel": {},
            "assembly": {},
            "manufacturing": {
                "profile": "ZA",
                "worm_features": {"bore_type": "custom", "bore_diameter_mm": 8.0},
                "wheel_features": {"bore_type": "auto"}
            }
        }

        migrated = upgrade_schema(old_data, "2.0")

        # Features should be in features section
        assert "features" in migrated
        assert migrated["features"]["worm"]["bore_type"] == "custom"
        assert migrated["features"]["worm"]["bore_diameter_mm"] == 8.0
        assert migrated["features"]["wheel"]["bore_type"] == "auto"

        # worm_features and wheel_features should be removed from manufacturing
        assert "worm_features" not in migrated.get("manufacturing", {})
        assert "wheel_features" not in migrated.get("manufacturing", {})

        # profile should remain in manufacturing
        assert migrated["manufacturing"]["profile"] == "ZA"

    def test_upgrade_schema_normalizes_hand(self):
        """Test that hand enum values are normalized to lowercase."""
        from wormgear.io.schema import upgrade_schema

        old_data = {
            "schema_version": "1.0",
            "worm": {"hand": "RIGHT"},
            "wheel": {},
            "assembly": {"hand": "LEFT"}
        }

        migrated = upgrade_schema(old_data, "2.0")

        assert migrated["worm"]["hand"] == "right"
        assert migrated["assembly"]["hand"] == "left"

    def test_upgrade_schema_normalizes_profile(self):
        """Test that profile enum values are normalized to uppercase."""
        from wormgear.io.schema import upgrade_schema

        old_data = {
            "schema_version": "1.0",
            "worm": {},
            "wheel": {},
            "assembly": {},
            "manufacturing": {"profile": "za"}
        }

        migrated = upgrade_schema(old_data, "2.0")

        assert migrated["manufacturing"]["profile"] == "ZA"

    def test_upgrade_schema_preserves_existing_features(self):
        """Test that existing features section is not overwritten."""
        from wormgear.io.schema import upgrade_schema

        old_data = {
            "schema_version": "1.0",
            "worm": {},
            "wheel": {},
            "assembly": {},
            "features": {"worm": {"bore_type": "custom", "bore_diameter_mm": 10.0}},
            "manufacturing": {
                "worm_features": {"bore_type": "auto"}  # Should not overwrite
            }
        }

        migrated = upgrade_schema(old_data, "2.0")

        # Original features should be preserved (not overwritten)
        assert migrated["features"]["worm"]["bore_type"] == "custom"
        assert migrated["features"]["worm"]["bore_diameter_mm"] == 10.0

    def test_upgrade_schema_rejects_downgrade(self):
        """Test that downgrading schema raises an error."""
        from wormgear.io.schema import upgrade_schema

        data = {"schema_version": "3.0", "worm": {}}

        with pytest.raises(ValueError, match="Cannot downgrade"):
            upgrade_schema(data, "2.0")

    def test_validate_schema_version_supported(self):
        """Test that supported versions pass validation."""
        from wormgear.io.schema import validate_schema_version

        assert validate_schema_version({"schema_version": "1.0"}) is True
        assert validate_schema_version({"schema_version": "2.0"}) is True

    def test_validate_schema_version_unsupported(self):
        """Test that unsupported versions fail validation."""
        from wormgear.io.schema import validate_schema_version

        # Version 0.5 (too old) - but actually our MIN_SUPPORTED is 1.0
        # and detect_schema_version defaults to 1.0, so this will pass
        # Let's test a version that would be detected as newer
        # Actually validate_schema_version checks against max supported too
        assert validate_schema_version({"schema_version": "99.0"}) is False

    def test_manufacturing_params_ignores_old_feature_fields(self):
        """Test that ManufacturingParams ignores worm_features/wheel_features."""
        # This verifies that old JSON with these fields can still be loaded
        # without errors (they're just ignored due to extra='ignore')
        params = ManufacturingParams(
            profile="ZA",
            worm_features={"bore_type": "auto"},  # Should be ignored
            wheel_features={"bore_type": "auto"}  # Should be ignored
        )

        # The fields should not exist on the model
        assert not hasattr(params, 'worm_features') or params.worm_features is None
        assert not hasattr(params, 'wheel_features') or params.wheel_features is None
