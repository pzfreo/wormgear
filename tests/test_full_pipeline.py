"""
Full pipeline integration tests: calculator -> save -> load -> geometry -> STEP.

Phase 4.2 of the tech debt remediation plan. Tests end-to-end workflows
that cross multiple layers, catching integration issues that unit tests miss.
"""

import json
import tempfile
from pathlib import Path

import pytest
from wormgear.calculator.core import design_from_module
from wormgear.calculator.validation import validate_design
from wormgear.io.loaders import load_design_json, save_design_json
from wormgear.core import (
    WormGeometry,
    WheelGeometry,
    GloboidWormGeometry,
    VirtualHobbingWheelGeometry,
    BoreFeature,
    KeywayFeature,
)


# ---------------------------------------------------------------------------
# Helpers (also available from conftest for use by other test files)
# ---------------------------------------------------------------------------

from build123d import export_step, import_step


def _assert_valid_part(part, min_volume: float = 1.0):
    """Assert a built Part is valid and has meaningful volume."""
    assert part.is_valid, "Part is not a valid solid"
    assert part.volume > min_volume, f"Part volume {part.volume:.2f} too small"


def _assert_step_roundtrip(part, tmp_path, name="part"):
    """Assert STEP export succeeds and reimport preserves volume within 1%."""
    step_path = tmp_path / f"{name}.step"
    export_step(part, str(step_path))
    assert step_path.exists(), "STEP file not created"
    assert step_path.stat().st_size > 100, "STEP file suspiciously small"

    reimported = import_step(str(step_path))
    ratio = abs(reimported.volume - part.volume) / part.volume
    assert ratio < 0.01, (
        f"STEP roundtrip volume drift: {ratio:.3%} "
        f"(original={part.volume:.2f}, reimported={reimported.volume:.2f})"
    )


# ---------------------------------------------------------------------------
# Save/Load Roundtrip Tests
# ---------------------------------------------------------------------------

class TestSaveLoadRoundtrip:
    """Calculator -> save JSON -> load JSON -> geometry -> STEP export."""

    pytestmark = pytest.mark.slow

    def test_cylindrical_roundtrip(self, tmp_path):
        """Full roundtrip: design_from_module -> save -> load -> worm+wheel -> STEP."""
        design = design_from_module(module=2.0, ratio=30)
        json_path = tmp_path / "design.json"
        save_design_json(design, json_path)

        loaded = load_design_json(json_path)

        # Verify key params survived the roundtrip
        assert loaded.worm.module_mm == design.worm.module_mm
        assert loaded.wheel.num_teeth == design.wheel.num_teeth
        assert loaded.assembly.centre_distance_mm == design.assembly.centre_distance_mm

        # Build worm from loaded design
        worm = WormGeometry(
            params=loaded.worm,
            assembly_params=loaded.assembly,
            length=30.0,
            sections_per_turn=12,
        ).build()
        _assert_valid_part(worm)
        _assert_step_roundtrip(worm, tmp_path, "worm")

        # Build wheel from loaded design
        wheel = WheelGeometry(
            params=loaded.wheel,
            worm_params=loaded.worm,
            assembly_params=loaded.assembly,
            face_width=12.0,
        ).build()
        _assert_valid_part(wheel)
        _assert_step_roundtrip(wheel, tmp_path, "wheel")

    def test_globoid_roundtrip(self, tmp_path):
        """Globoid worm design through save -> load -> build -> STEP."""
        design = design_from_module(
            module=2.0, ratio=30, globoid=True, throat_reduction=2.0,
        )
        json_path = tmp_path / "globoid.json"
        save_design_json(design, json_path)

        loaded = load_design_json(json_path)

        globoid = GloboidWormGeometry(
            params=loaded.worm,
            assembly_params=loaded.assembly,
            wheel_pitch_diameter=loaded.wheel.pitch_diameter_mm,
            length=30.0,
            sections_per_turn=12,
        ).build()
        _assert_valid_part(globoid)
        _assert_step_roundtrip(globoid, tmp_path, "globoid")

    def test_virtual_hobbing_roundtrip(self, tmp_path):
        """Virtual hobbing wheel through save -> load -> build -> STEP."""
        design = design_from_module(module=2.0, ratio=20, num_starts=1)
        json_path = tmp_path / "vhob.json"
        save_design_json(design, json_path)

        loaded = load_design_json(json_path)

        wheel = VirtualHobbingWheelGeometry(
            params=loaded.wheel,
            worm_params=loaded.worm,
            assembly_params=loaded.assembly,
            face_width=10.0,
            hobbing_steps=6,
        ).build()
        _assert_valid_part(wheel)

    def test_profile_zk_persists_through_roundtrip(self, tmp_path):
        """ZK profile survives save/load and is accessible in loaded design."""
        design = design_from_module(module=2.0, ratio=30, profile="ZK")
        json_path = tmp_path / "zk.json"
        save_design_json(design, json_path)

        loaded = load_design_json(json_path)

        # Build worm — should work regardless of profile stored in design
        worm = WormGeometry(
            params=loaded.worm,
            assembly_params=loaded.assembly,
            length=30.0,
            sections_per_turn=12,
        ).build()
        _assert_valid_part(worm)


# ---------------------------------------------------------------------------
# Paired Geometry Tests
# ---------------------------------------------------------------------------

class TestPairedGeometry:
    """Worm + wheel from single design — dimensional compatibility."""

    pytestmark = pytest.mark.slow

    def test_matching_pair_both_export(self, tmp_path):
        """Single design -> build worm + wheel -> both STEP exports valid."""
        design = design_from_module(module=2.0, ratio=30)

        worm = WormGeometry(
            params=design.worm,
            assembly_params=design.assembly,
            length=30.0,
            sections_per_turn=12,
        ).build()

        wheel = WheelGeometry(
            params=design.wheel,
            worm_params=design.worm,
            assembly_params=design.assembly,
            face_width=12.0,
        ).build()

        _assert_valid_part(worm)
        _assert_valid_part(wheel)
        _assert_step_roundtrip(worm, tmp_path, "worm")
        _assert_step_roundtrip(wheel, tmp_path, "wheel")

    def test_pair_with_features(self, tmp_path):
        """Worm with bore+keyway, wheel with bore+keyway -> both STEP valid."""
        design = design_from_module(module=2.0, ratio=30)

        worm = WormGeometry(
            params=design.worm,
            assembly_params=design.assembly,
            length=30.0,
            sections_per_turn=12,
            bore=BoreFeature(diameter=8.0),
            keyway=KeywayFeature(),
        ).build()

        wheel = WheelGeometry(
            params=design.wheel,
            worm_params=design.worm,
            assembly_params=design.assembly,
            face_width=12.0,
            bore=BoreFeature(diameter=12.0),
            keyway=KeywayFeature(),
        ).build()

        _assert_valid_part(worm)
        _assert_valid_part(wheel)
        _assert_step_roundtrip(worm, tmp_path, "worm_feat")
        _assert_step_roundtrip(wheel, tmp_path, "wheel_feat")

    def test_pair_dimensional_compatibility(self):
        """Worm pitch_diameter + wheel pitch_diameter = 2 * centre_distance."""
        design = design_from_module(module=2.0, ratio=30)

        worm_pitch_r = design.worm.pitch_diameter_mm / 2
        wheel_pitch_r = design.wheel.pitch_diameter_mm / 2
        expected_cd = worm_pitch_r + wheel_pitch_r

        assert abs(design.assembly.centre_distance_mm - expected_cd) < 0.5, (
            f"Centre distance mismatch: assembly={design.assembly.centre_distance_mm:.2f}, "
            f"expected={expected_cd:.2f}"
        )


# ---------------------------------------------------------------------------
# Feature Combination Tests
# ---------------------------------------------------------------------------

class TestFeatureCombinations:
    """Parametrized feature matrix on worm and wheel."""

    pytestmark = pytest.mark.slow

    @pytest.mark.parametrize(
        "bore,keyway,desc",
        [
            (None, None, "solid"),
            (BoreFeature(diameter=8.0), None, "bore_only"),
            (BoreFeature(diameter=8.0), KeywayFeature(), "bore_keyway"),
        ],
        ids=["solid", "bore_only", "bore_keyway"],
    )
    def test_worm_feature_combinations(self, bore, keyway, desc, tmp_path):
        """Build and export worm with various feature combinations."""
        design = design_from_module(module=2.0, ratio=30)

        worm = WormGeometry(
            params=design.worm,
            assembly_params=design.assembly,
            length=30.0,
            sections_per_turn=12,
            bore=bore,
            keyway=keyway,
        ).build()

        _assert_valid_part(worm)
        _assert_step_roundtrip(worm, tmp_path, f"worm_{desc}")

    @pytest.mark.parametrize(
        "bore,keyway,desc",
        [
            (None, None, "solid"),
            (BoreFeature(diameter=12.0), None, "bore_only"),
            (BoreFeature(diameter=12.0), KeywayFeature(), "bore_keyway"),
        ],
        ids=["solid", "bore_only", "bore_keyway"],
    )
    def test_wheel_feature_combinations(self, bore, keyway, desc, tmp_path):
        """Build and export wheel with various feature combinations."""
        design = design_from_module(module=2.0, ratio=30)

        wheel = WheelGeometry(
            params=design.wheel,
            worm_params=design.worm,
            assembly_params=design.assembly,
            face_width=12.0,
            bore=bore,
            keyway=keyway,
        ).build()

        _assert_valid_part(wheel)
        _assert_step_roundtrip(wheel, tmp_path, f"wheel_{desc}")

    def test_bore_reduces_volume(self):
        """Worm with bore should have less volume than solid."""
        design = design_from_module(module=2.0, ratio=30)

        solid = WormGeometry(
            params=design.worm,
            assembly_params=design.assembly,
            length=30.0,
            sections_per_turn=12,
        ).build()

        with_bore = WormGeometry(
            params=design.worm,
            assembly_params=design.assembly,
            length=30.0,
            sections_per_turn=12,
            bore=BoreFeature(diameter=8.0),
        ).build()

        assert with_bore.volume < solid.volume, (
            f"Bore should reduce volume: solid={solid.volume:.2f}, "
            f"with_bore={with_bore.volume:.2f}"
        )


# ---------------------------------------------------------------------------
# Error Path Tests (fast — no geometry)
# ---------------------------------------------------------------------------

class TestErrorPaths:
    """Failure modes for JSON loading — these run fast (no geometry)."""

    def test_invalid_json_raises_error(self, tmp_path):
        """Malformed JSON -> json.JSONDecodeError."""
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("not valid json {{{")
        with pytest.raises(json.JSONDecodeError):
            load_design_json(bad_file)

    def test_missing_required_section_raises_error(self, tmp_path):
        """JSON missing 'worm' section -> ValueError."""
        incomplete = tmp_path / "incomplete.json"
        incomplete.write_text(json.dumps({"wheel": {}, "assembly": {}}))
        with pytest.raises(ValueError, match="must contain"):
            load_design_json(incomplete)

    def test_missing_file_raises_error(self):
        """Non-existent file -> FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_design_json("/nonexistent/path/design.json")

    def test_empty_json_object_raises_error(self, tmp_path):
        """Empty JSON object -> ValueError."""
        empty = tmp_path / "empty.json"
        empty.write_text("{}")
        with pytest.raises(ValueError, match="must contain"):
            load_design_json(empty)


# ---------------------------------------------------------------------------
# Scale Variation Tests
# ---------------------------------------------------------------------------

class TestScaleVariations:
    """Full pipeline across different module/ratio scales."""

    pytestmark = pytest.mark.slow

    @pytest.mark.parametrize(
        "module,ratio",
        [
            (0.5, 20),   # small
            (2.0, 30),   # standard
            (8.0, 15),   # large
        ],
        ids=["small_0.5", "standard_2.0", "large_8.0"],
    )
    def test_full_pipeline_at_various_scales(self, module, ratio, tmp_path):
        """Calculator -> geometry -> STEP across module scales."""
        design = design_from_module(module=module, ratio=ratio)

        worm = WormGeometry(
            params=design.worm,
            assembly_params=design.assembly,
            length=max(10.0, module * 10),
            sections_per_turn=12,
        ).build()
        _assert_valid_part(worm, min_volume=0.1)

        wheel = WheelGeometry(
            params=design.wheel,
            worm_params=design.worm,
            assembly_params=design.assembly,
            face_width=max(4.0, module * 5),
        ).build()
        _assert_valid_part(wheel, min_volume=0.1)

        _assert_step_roundtrip(worm, tmp_path, f"worm_m{module}")
        _assert_step_roundtrip(wheel, tmp_path, f"wheel_m{module}")

    def test_multi_start_pipeline(self, tmp_path):
        """Multi-start worm (2 starts) through full pipeline."""
        design = design_from_module(module=2.0, ratio=15, num_starts=2)

        worm = WormGeometry(
            params=design.worm,
            assembly_params=design.assembly,
            length=30.0,
            sections_per_turn=12,
        ).build()
        _assert_valid_part(worm)
        _assert_step_roundtrip(worm, tmp_path, "worm_2start")


# ---------------------------------------------------------------------------
# Validation + Build Tests
# ---------------------------------------------------------------------------

class TestValidationThenBuild:
    """Designs that pass validation should always build successfully."""

    pytestmark = pytest.mark.slow

    def test_validated_design_builds_worm(self):
        """Design passing validation -> worm builds without error."""
        design = design_from_module(module=2.0, ratio=30)
        result = validate_design(design)
        assert result.valid, f"Expected valid design, got: {result.messages}"

        worm = WormGeometry(
            params=design.worm,
            assembly_params=design.assembly,
            length=30.0,
            sections_per_turn=12,
        ).build()
        _assert_valid_part(worm)

    def test_validated_design_builds_wheel(self):
        """Design passing validation -> wheel builds without error."""
        design = design_from_module(module=2.0, ratio=30)
        result = validate_design(design)
        assert result.valid

        wheel = WheelGeometry(
            params=design.wheel,
            worm_params=design.worm,
            assembly_params=design.assembly,
            face_width=12.0,
        ).build()
        _assert_valid_part(wheel)

    def test_left_hand_validated_and_builds(self, tmp_path):
        """Left-hand design validates and builds both parts."""
        design = design_from_module(module=1.5, ratio=20, hand="left")
        result = validate_design(design)
        assert result.valid

        worm = WormGeometry(
            params=design.worm,
            assembly_params=design.assembly,
            length=20.0,
            sections_per_turn=12,
        ).build()
        _assert_valid_part(worm)

        wheel = WheelGeometry(
            params=design.wheel,
            worm_params=design.worm,
            assembly_params=design.assembly,
            face_width=8.0,
        ).build()
        _assert_valid_part(wheel)
