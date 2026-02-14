"""
Tests for output formatters (to_json, to_markdown, to_summary).

These are fast tests — no geometry building required.
"""

import json
import pytest

from wormgear.calculator.core import design_from_module
from wormgear.calculator.output import (
    to_json,
    to_markdown,
    to_summary,
    _normalize_anti_rotation,
    _build_part_bore_features,
)
from wormgear.calculator.validation import (
    ValidationResult,
    ValidationMessage,
    Severity,
)
from wormgear.io.schema import SCHEMA_VERSION


@pytest.fixture
def basic_design():
    """A simple cylindrical design for output tests."""
    return design_from_module(module=2.0, ratio=30)


@pytest.fixture
def globoid_design():
    """A globoid design for output tests."""
    return design_from_module(module=2.0, ratio=30, globoid=True)


@pytest.fixture
def valid_result():
    """A passing validation result."""
    return ValidationResult(valid=True, messages=[])


@pytest.fixture
def failing_result():
    """A failing validation result with errors, warnings, and infos."""
    return ValidationResult(
        valid=False,
        messages=[
            ValidationMessage(
                severity=Severity.ERROR,
                code="LEAD_ANGLE_LOW",
                message="Lead angle is too low for efficient operation",
                suggestion="Increase module or reduce ratio",
            ),
            ValidationMessage(
                severity=Severity.WARNING,
                code="NON_STANDARD_MODULE",
                message="Module is not a standard ISO value",
                suggestion="Consider using 2.0 mm",
            ),
            ValidationMessage(
                severity=Severity.INFO,
                code="SELF_LOCKING",
                message="This design is self-locking",
                suggestion=None,
            ),
        ],
    )


# ─── _normalize_anti_rotation ────────────────────────────────────────────


class TestNormalizeAntiRotation:
    def test_none_returns_none(self):
        assert _normalize_anti_rotation(None) == "none"

    def test_empty_returns_none(self):
        assert _normalize_anti_rotation("") == "none"

    def test_none_string(self):
        assert _normalize_anti_rotation("none") == "none"

    def test_din6885(self):
        assert _normalize_anti_rotation("DIN6885") == "DIN6885"

    def test_dd_cut_variants(self):
        assert _normalize_anti_rotation("DD-cut") == "ddcut"
        assert _normalize_anti_rotation("ddcut") == "ddcut"

    def test_unknown_passthrough(self):
        assert _normalize_anti_rotation("custom") == "custom"


# ─── _build_part_bore_features ───────────────────────────────────────────


class TestBuildPartBoreFeatures:
    def test_no_bore(self):
        result = _build_part_bore_features(
            {"worm_bore_type": "none"}, "worm", 16.0, 11.0
        )
        assert result == {"bore_type": "none"}

    def test_custom_bore_with_diameter(self):
        result = _build_part_bore_features(
            {"worm_bore_type": "custom", "worm_bore_diameter": 8.0},
            "worm", 16.0, 11.0,
        )
        assert result["bore_type"] == "custom"
        assert result["bore_diameter_mm"] == 8.0

    def test_custom_bore_auto_diameter(self):
        result = _build_part_bore_features(
            {"worm_bore_type": "custom"},
            "worm", 16.0, 11.0,
        )
        assert result["bore_type"] == "custom"
        assert "bore_diameter_mm" in result
        assert result["bore_diameter_mm"] > 0

    def test_custom_bore_with_keyway(self):
        result = _build_part_bore_features(
            {"worm_bore_type": "custom", "worm_bore_diameter": 8.0, "worm_keyway": "DIN6885"},
            "worm", 16.0, 11.0,
        )
        assert result["anti_rotation"] == "DIN6885"

    def test_custom_bore_keyway_none_omitted(self):
        result = _build_part_bore_features(
            {"worm_bore_type": "custom", "worm_bore_diameter": 8.0, "worm_keyway": "none"},
            "worm", 16.0, 11.0,
        )
        assert "anti_rotation" not in result

    def test_unknown_bore_type_returns_none(self):
        result = _build_part_bore_features(
            {"worm_bore_type": "unknown"}, "worm", 16.0, 11.0
        )
        assert result is None

    def test_wheel_part(self):
        result = _build_part_bore_features(
            {"wheel_bore_type": "custom", "wheel_bore_diameter": 12.0, "wheel_keyway": "ddcut"},
            "wheel", 60.0, 55.0,
        )
        assert result["bore_type"] == "custom"
        assert result["bore_diameter_mm"] == 12.0
        assert result["anti_rotation"] == "ddcut"


# ─── to_json ─────────────────────────────────────────────────────────────


class TestToJson:
    def test_basic_json_output(self, basic_design):
        result = to_json(basic_design)
        data = json.loads(result)

        assert data["schema_version"] == SCHEMA_VERSION
        assert "worm" in data
        assert "wheel" in data
        assert "assembly" in data

    def test_json_worm_fields(self, basic_design):
        data = json.loads(to_json(basic_design))
        worm = data["worm"]

        assert worm["module_mm"] == 2.0
        assert worm["num_starts"] == 1
        assert "pitch_diameter_mm" in worm
        assert "tip_diameter_mm" in worm
        assert "root_diameter_mm" in worm
        assert "lead_mm" in worm

    def test_json_removes_redundant_fields(self, basic_design):
        data = json.loads(to_json(basic_design))

        # These should be stripped from output
        assert "axial_pitch_mm" not in data["worm"]
        assert "length_mm" not in data.get("worm", {})

    def test_json_with_validation(self, basic_design, failing_result):
        data = json.loads(to_json(basic_design, validation=failing_result))

        assert data["validation"]["valid"] is False
        assert len(data["validation"]["errors"]) == 1
        assert len(data["validation"]["warnings"]) == 1
        assert len(data["validation"]["infos"]) == 1
        assert data["validation"]["errors"][0]["code"] == "LEAD_ANGLE_LOW"

    def test_json_with_valid_validation(self, basic_design, valid_result):
        data = json.loads(to_json(basic_design, validation=valid_result))

        assert data["validation"]["valid"] is True
        assert data["validation"]["errors"] == []

    def test_json_with_bore_settings(self, basic_design):
        bore = {
            "worm_bore_type": "custom",
            "worm_bore_diameter": 8.0,
            "worm_keyway": "DIN6885",
            "wheel_bore_type": "custom",
            "wheel_bore_diameter": 15.0,
            "wheel_keyway": "none",
        }
        data = json.loads(to_json(basic_design, bore_settings=bore))

        assert data["features"]["worm"]["bore_type"] == "custom"
        assert data["features"]["worm"]["bore_diameter_mm"] == 8.0
        assert data["features"]["worm"]["anti_rotation"] == "DIN6885"
        assert data["features"]["wheel"]["bore_type"] == "custom"
        assert "anti_rotation" not in data["features"]["wheel"]

    def test_json_with_no_bore(self, basic_design):
        bore = {"worm_bore_type": "none", "wheel_bore_type": "none"}
        data = json.loads(to_json(basic_design, bore_settings=bore))

        # bore_type "none" entries are still included in features
        assert data["features"]["worm"]["bore_type"] == "none"
        assert data["features"]["wheel"]["bore_type"] == "none"

    def test_json_with_manufacturing_settings(self, basic_design):
        mfg = {"profile": "ZK", "virtual_hobbing": True, "hobbing_steps": 36}
        data = json.loads(to_json(basic_design, manufacturing_settings=mfg))

        assert data["manufacturing"]["profile"] == "ZK"
        assert data["manufacturing"]["virtual_hobbing"] is True

    def test_json_with_relief_groove(self, basic_design):
        groove = {"diameter_mm": 6.0, "width_mm": 1.5}
        data = json.loads(to_json(basic_design, relief_groove=groove))

        assert data["features"]["worm"]["relief_groove"] == groove

    def test_json_indent(self, basic_design):
        result_2 = to_json(basic_design, indent=2)
        result_4 = to_json(basic_design, indent=4)

        # Both valid JSON
        json.loads(result_2)
        json.loads(result_4)

        # 4-indent is longer
        assert len(result_4) > len(result_2)


# ─── to_markdown ──────────────────────────────────────────────────────────


class TestToMarkdown:
    def test_basic_markdown(self, basic_design):
        md = to_markdown(basic_design)

        assert "# Worm Gear Design Specification" in md
        assert "## Overview" in md
        assert "## Worm Gear (Driving)" in md
        assert "## Worm Wheel (Driven)" in md
        assert "## Assembly & Performance" in md
        assert "## Manufacturing Notes" in md

    def test_markdown_overview_table(self, basic_design):
        md = to_markdown(basic_design)

        assert "Gear Ratio" in md
        assert "30:1" in md
        assert "Module" in md
        assert "Centre Distance" in md

    def test_markdown_worm_dimensions(self, basic_design):
        md = to_markdown(basic_design)

        assert "Number of Starts" in md
        assert "Tip Diameter" in md
        assert "Pitch Diameter" in md
        assert "Lead Angle" in md

    def test_markdown_wheel_dimensions(self, basic_design):
        md = to_markdown(basic_design)

        assert "Number of Teeth" in md
        assert "Helix Angle" in md

    def test_markdown_za_profile_note(self, basic_design):
        md = to_markdown(basic_design)
        assert "straight flanks" in md

    def test_markdown_zk_profile_note(self):
        design = design_from_module(module=2.0, ratio=30, profile="ZK")
        md = to_markdown(design, manufacturing_settings={"profile": "ZK"})
        # The profile is shown from design_dict.manufacturing.profile
        assert "ZK" in md

    def test_markdown_with_validation_passing(self, basic_design, valid_result):
        md = to_markdown(basic_design, validation=valid_result)
        assert "Design is valid" in md

    def test_markdown_with_validation_failing(self, basic_design, failing_result):
        md = to_markdown(basic_design, validation=failing_result)

        assert "Design has errors" in md
        assert "LEAD_ANGLE_LOW" in md
        assert "Suggestion" in md
        assert "### Warnings" in md
        assert "### Information" in md

    def test_markdown_with_bore_settings(self, basic_design):
        bore = {
            "worm_bore_type": "custom",
            "worm_bore_diameter": 8.0,
            "worm_keyway": "DIN6885",
            "wheel_bore_type": "custom",
            "wheel_bore_diameter": 15.0,
        }
        md = to_markdown(basic_design, bore_settings=bore)

        assert "## Bore & Anti-Rotation Features" in md
        assert "8.0 mm" in md
        assert "DIN6885" in md

    def test_markdown_bore_auto_calculated(self, basic_design):
        bore = {"worm_bore_type": "custom"}
        md = to_markdown(basic_design, bore_settings=bore)
        assert "Auto-calculated" in md

    def test_markdown_footer(self, basic_design):
        md = to_markdown(basic_design)
        assert "Generated by Wormgear Calculator" in md

    def test_markdown_globoid_throat_info(self, globoid_design):
        md = to_markdown(globoid_design)
        assert "globoid" in md.lower()

    def test_markdown_manufacturing_recommendations(self):
        design = design_from_module(module=2.0, ratio=30)
        md = to_markdown(design)
        if design.manufacturing and design.manufacturing.worm_length_mm:
            assert "Recommended Length" in md


# ─── to_summary ──────────────────────────────────────────────────────────


class TestToSummary:
    def test_basic_summary(self, basic_design):
        summary = to_summary(basic_design)

        assert "Worm Gear Design" in summary
        assert "Ratio: 30:1" in summary
        assert "Module:" in summary

    def test_summary_worm_section(self, basic_design):
        summary = to_summary(basic_design)

        assert "Worm:" in summary
        assert "Tip diameter" in summary
        assert "Pitch diameter" in summary
        assert "Root diameter" in summary
        assert "Lead angle" in summary
        assert "Starts:" in summary

    def test_summary_wheel_section(self, basic_design):
        summary = to_summary(basic_design)

        assert "Wheel:" in summary
        assert "Teeth:" in summary

    def test_summary_assembly_info(self, basic_design):
        summary = to_summary(basic_design)

        assert "Centre distance:" in summary
        assert "Efficiency" in summary
        assert "Self-locking:" in summary

    def test_summary_manufacturing_recommendations(self, basic_design):
        summary = to_summary(basic_design)

        if basic_design.manufacturing.worm_length_mm:
            assert "Recommended Dimensions" in summary
            assert "Worm length" in summary
        if basic_design.manufacturing.wheel_width_mm:
            assert "Wheel width" in summary

    def test_summary_globoid_throat(self, globoid_design):
        summary = to_summary(globoid_design)
        assert "globoid" in summary.lower()

    def test_summary_helix_angle(self, basic_design):
        summary = to_summary(basic_design)
        assert "Helix angle" in summary
