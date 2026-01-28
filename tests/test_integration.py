"""
Integration tests for complete worm gear pair generation.
"""

import math
import pytest
from pathlib import Path
import tempfile

from wormgear import (
    load_design_json, WormParams, WheelParams, AssemblyParams,
    WormGeometry, WheelGeometry,
)


class TestWormWheelPair:
    """Tests for generating matching worm and wheel pairs."""

    @pytest.fixture
    def design_7mm(self, sample_design_7mm):
        """Create design objects from 7mm sample."""
        module_mm = sample_design_7mm["worm"]["module_mm"]
        worm_params = WormParams(
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
        )
        wheel_params = WheelParams(
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
        )
        assembly_params = AssemblyParams(
            centre_distance_mm=sample_design_7mm["assembly"]["centre_distance_mm"],
            pressure_angle_deg=sample_design_7mm["assembly"]["pressure_angle_deg"],
            backlash_mm=sample_design_7mm["assembly"]["backlash_mm"],
            hand=sample_design_7mm["assembly"]["hand"],
            ratio=sample_design_7mm["assembly"]["ratio"]
        )
        return worm_params, wheel_params, assembly_params

    def test_generate_matching_pair(self, design_7mm):
        """Test generating a matching worm and wheel pair."""
        worm_params, wheel_params, assembly_params = design_7mm

        worm_geo = WormGeometry(
            params=worm_params,
            assembly_params=assembly_params,
            length=10.0,
            sections_per_turn=12
        )
        worm = worm_geo.build()

        wheel_geo = WheelGeometry(
            params=wheel_params,
            worm_params=worm_params,
            assembly_params=assembly_params,
            face_width=4.0
        )
        wheel = wheel_geo.build()

        # Both should be valid
        assert worm.is_valid
        assert wheel.is_valid

        # Both should have positive volume
        assert worm.volume > 0
        assert wheel.volume > 0

    def test_centre_distance_compatibility(self, design_7mm):
        """Test that worm and wheel dimensions are compatible with centre distance."""
        worm_params, wheel_params, assembly_params = design_7mm

        # Centre distance should be approximately sum of pitch radii
        worm_pitch_radius = worm_params.pitch_diameter_mm / 2
        wheel_pitch_radius = wheel_params.pitch_diameter_mm / 2
        expected_centre = worm_pitch_radius + wheel_pitch_radius

        assert abs(assembly_params.centre_distance_mm - expected_centre) < 0.5

    def test_module_compatibility(self, design_7mm):
        """Test that worm and wheel have compatible modules."""
        worm_params, wheel_params, assembly_params = design_7mm

        assert worm_params.module_mm == wheel_params.module_mm

    def test_pair_at_different_scales(self, sample_design_7mm, sample_design_large):
        """Test generating pairs at different scales."""
        for design_data in [sample_design_7mm, sample_design_large]:
            module_mm = design_data["worm"]["module_mm"]
            worm_params = WormParams(
                module_mm=module_mm,
                num_starts=design_data["worm"]["num_starts"],
                pitch_diameter_mm=design_data["worm"]["pitch_diameter_mm"],
                tip_diameter_mm=design_data["worm"]["tip_diameter_mm"],
                root_diameter_mm=design_data["worm"]["root_diameter_mm"],
                lead_mm=design_data["worm"]["lead_mm"],
                axial_pitch_mm=module_mm * math.pi,
                lead_angle_deg=design_data["worm"]["lead_angle_deg"],
                addendum_mm=design_data["worm"]["addendum_mm"],
                dedendum_mm=design_data["worm"]["dedendum_mm"],
                thread_thickness_mm=design_data["worm"]["thread_thickness_mm"],
                hand="right",
                profile_shift=0.0
            )
            wheel_params = WheelParams(
                module_mm=design_data["wheel"]["module_mm"],
                num_teeth=design_data["wheel"]["num_teeth"],
                pitch_diameter_mm=design_data["wheel"]["pitch_diameter_mm"],
                tip_diameter_mm=design_data["wheel"]["tip_diameter_mm"],
                root_diameter_mm=design_data["wheel"]["root_diameter_mm"],
                throat_diameter_mm=design_data["wheel"]["throat_diameter_mm"],
                helix_angle_deg=design_data["wheel"]["helix_angle_deg"],
                addendum_mm=design_data["wheel"]["addendum_mm"],
                dedendum_mm=design_data["wheel"]["dedendum_mm"],
                profile_shift=0.0
            )
            assembly_params = AssemblyParams(
                centre_distance_mm=design_data["assembly"]["centre_distance_mm"],
                pressure_angle_deg=design_data["assembly"]["pressure_angle_deg"],
                backlash_mm=design_data["assembly"]["backlash_mm"],
                hand=design_data["assembly"]["hand"],
                ratio=design_data["assembly"]["ratio"]
            )

            worm_geo = WormGeometry(
                params=worm_params,
                assembly_params=assembly_params,
                length=worm_params.pitch_diameter_mm * 2,
                sections_per_turn=12
            )
            worm = worm_geo.build()

            wheel_geo = WheelGeometry(
                params=wheel_params,
                worm_params=worm_params,
                assembly_params=assembly_params
            )
            wheel = wheel_geo.build()

            assert worm.is_valid, f"Worm invalid for module {worm_params.module_mm}"
            assert wheel.is_valid, f"Wheel invalid for module {wheel_params.module_mm}"


class TestSTEPExport:
    """Tests for STEP file export."""

    def test_export_worm_step(self, sample_design_7mm):
        """Test exporting worm to STEP file."""
        from build123d import export_step

        module_mm = sample_design_7mm["worm"]["module_mm"]
        worm_params = WormParams(
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
        )
        assembly_params = AssemblyParams(
            centre_distance_mm=sample_design_7mm["assembly"]["centre_distance_mm"],
            pressure_angle_deg=sample_design_7mm["assembly"]["pressure_angle_deg"],
            backlash_mm=sample_design_7mm["assembly"]["backlash_mm"],
            hand=sample_design_7mm["assembly"]["hand"],
            ratio=sample_design_7mm["assembly"]["ratio"]
        )

        worm_geo = WormGeometry(
            params=worm_params,
            assembly_params=assembly_params,
            length=10.0,
            sections_per_turn=12
        )
        worm = worm_geo.build()

        with tempfile.NamedTemporaryFile(suffix=".step", delete=False) as f:
            step_path = Path(f.name)

        try:
            export_step(worm, str(step_path))
            assert step_path.exists()
            assert step_path.stat().st_size > 0
        finally:
            step_path.unlink(missing_ok=True)

    def test_export_wheel_step(self, sample_design_7mm):
        """Test exporting wheel to STEP file."""
        from build123d import export_step

        module_mm = sample_design_7mm["worm"]["module_mm"]
        worm_params = WormParams(
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
        )
        wheel_params = WheelParams(
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
        )
        assembly_params = AssemblyParams(
            centre_distance_mm=sample_design_7mm["assembly"]["centre_distance_mm"],
            pressure_angle_deg=sample_design_7mm["assembly"]["pressure_angle_deg"],
            backlash_mm=sample_design_7mm["assembly"]["backlash_mm"],
            hand=sample_design_7mm["assembly"]["hand"],
            ratio=sample_design_7mm["assembly"]["ratio"]
        )

        wheel_geo = WheelGeometry(
            params=wheel_params,
            worm_params=worm_params,
            assembly_params=assembly_params,
            face_width=4.0
        )
        wheel = wheel_geo.build()

        with tempfile.NamedTemporaryFile(suffix=".step", delete=False) as f:
            step_path = Path(f.name)

        try:
            export_step(wheel, str(step_path))
            assert step_path.exists()
            assert step_path.stat().st_size > 0
        finally:
            step_path.unlink(missing_ok=True)

    def test_reimport_step_preserves_volume(self, sample_design_7mm):
        """Test that STEP export/import preserves geometry volume."""
        from build123d import export_step, import_step

        module_mm = sample_design_7mm["worm"]["module_mm"]
        worm_params = WormParams(
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
        )
        assembly_params = AssemblyParams(
            centre_distance_mm=sample_design_7mm["assembly"]["centre_distance_mm"],
            pressure_angle_deg=sample_design_7mm["assembly"]["pressure_angle_deg"],
            backlash_mm=sample_design_7mm["assembly"]["backlash_mm"],
            hand=sample_design_7mm["assembly"]["hand"],
            ratio=sample_design_7mm["assembly"]["ratio"]
        )

        worm_geo = WormGeometry(
            params=worm_params,
            assembly_params=assembly_params,
            length=10.0,
            sections_per_turn=12
        )
        worm = worm_geo.build()
        original_volume = worm.volume

        with tempfile.NamedTemporaryFile(suffix=".step", delete=False) as f:
            step_path = Path(f.name)

        try:
            export_step(worm, str(step_path))
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
