"""
Integration tests for complete worm gear pair generation.
"""

import math
import pytest
from pathlib import Path
import tempfile

from wormgear import load_design_json, WormGeometry, WheelGeometry

pytestmark = pytest.mark.slow


class TestWormWheelPair:
    """Tests for generating matching worm and wheel pairs."""

    def test_generate_matching_pair(self, built_worm_7mm, built_wheel_7mm):
        """Test generating a matching worm and wheel pair."""
        assert built_worm_7mm.is_valid
        assert built_wheel_7mm.is_valid
        assert built_worm_7mm.volume > 0
        assert built_wheel_7mm.volume > 0

    def test_centre_distance_compatibility(
        self, worm_params_7mm, wheel_params_7mm, assembly_params_7mm
    ):
        """Test that worm and wheel dimensions are compatible with centre distance."""
        worm_pitch_radius = worm_params_7mm.pitch_diameter_mm / 2
        wheel_pitch_radius = wheel_params_7mm.pitch_diameter_mm / 2
        expected_centre = worm_pitch_radius + wheel_pitch_radius

        assert abs(assembly_params_7mm.centre_distance_mm - expected_centre) < 0.5

    def test_module_compatibility(self, worm_params_7mm, wheel_params_7mm):
        """Test that worm and wheel have compatible modules."""
        assert worm_params_7mm.module_mm == wheel_params_7mm.module_mm

    def test_pair_at_different_scales(
        self, built_worm_7mm, built_wheel_7mm, built_worm_large, built_wheel_large
    ):
        """Test generating pairs at different scales."""
        assert built_worm_7mm.is_valid, "Worm invalid for 7mm design"
        assert built_wheel_7mm.is_valid, "Wheel invalid for 7mm design"
        assert built_worm_large.is_valid, "Worm invalid for large design"
        assert built_wheel_large.is_valid, "Wheel invalid for large design"


class TestSTEPExport:
    """Tests for STEP file export."""

    def test_export_worm_step(self, built_worm_7mm):
        """Test exporting worm to STEP file."""
        from build123d import export_step

        with tempfile.NamedTemporaryFile(suffix=".step", delete=False) as f:
            step_path = Path(f.name)

        try:
            export_step(built_worm_7mm, str(step_path))
            assert step_path.exists()
            assert step_path.stat().st_size > 0
        finally:
            step_path.unlink(missing_ok=True)

    def test_export_wheel_step(self, built_wheel_7mm):
        """Test exporting wheel to STEP file."""
        from build123d import export_step

        with tempfile.NamedTemporaryFile(suffix=".step", delete=False) as f:
            step_path = Path(f.name)

        try:
            export_step(built_wheel_7mm, str(step_path))
            assert step_path.exists()
            assert step_path.stat().st_size > 0
        finally:
            step_path.unlink(missing_ok=True)

    def test_reimport_step_preserves_volume(self, built_worm_7mm):
        """Test that STEP export/import preserves geometry volume."""
        from build123d import export_step, import_step

        original_volume = built_worm_7mm.volume

        with tempfile.NamedTemporaryFile(suffix=".step", delete=False) as f:
            step_path = Path(f.name)

        try:
            export_step(built_worm_7mm, str(step_path))
            reimported = import_step(str(step_path))

            # Volume should be preserved within tolerance
            reimported_volume = reimported.volume
            assert abs(reimported_volume - original_volume) / original_volume < 0.01
        finally:
            step_path.unlink(missing_ok=True)


class TestFromExampleFiles:
    """Integration tests using actual example files."""

    def test_full_workflow_7mm(self, examples_dir):
        """Test complete workflow with 7mm.json example."""
        example_file = examples_dir / "7mm.json"
        if not example_file.exists():
            pytest.skip("Example file not found")

        design = load_design_json(example_file)

        # Generate worm
        worm_geo = WormGeometry(
            params=design.worm,
            assembly_params=design.assembly,
            length=7.0,
            sections_per_turn=12
        )
        worm = worm_geo.build()

        # Generate wheel
        wheel_geo = WheelGeometry(
            params=design.wheel,
            worm_params=design.worm,
            assembly_params=design.assembly
        )
        wheel = wheel_geo.build()

        # Verify both
        assert worm.is_valid
        assert wheel.is_valid
        assert worm.volume > 0
        assert wheel.volume > 0

        # Test export
        from build123d import export_step
        with tempfile.TemporaryDirectory() as tmpdir:
            worm_path = Path(tmpdir) / "worm.step"
            wheel_path = Path(tmpdir) / "wheel.step"

            export_step(worm, str(worm_path))
            export_step(wheel, str(wheel_path))

            assert worm_path.exists()
            assert wheel_path.exists()
            assert worm_path.stat().st_size > 0
            assert wheel_path.stat().st_size > 0
