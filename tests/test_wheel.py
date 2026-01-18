"""
Tests for wheel geometry generation.
"""

import math
import pytest

from wormgear_geometry.io import load_design_json, WormParams, WheelParams, AssemblyParams
from wormgear_geometry.wheel import WheelGeometry


class TestWheelGeometry:
    """Tests for WheelGeometry class."""

    @pytest.fixture
    def worm_params(self, sample_design_7mm):
        """Create WormParams from sample design."""
        return WormParams(
            module_mm=sample_design_7mm["worm"]["module_mm"],
            num_starts=sample_design_7mm["worm"]["num_starts"],
            pitch_diameter_mm=sample_design_7mm["worm"]["pitch_diameter_mm"],
            tip_diameter_mm=sample_design_7mm["worm"]["tip_diameter_mm"],
            root_diameter_mm=sample_design_7mm["worm"]["root_diameter_mm"],
            lead_mm=sample_design_7mm["worm"]["lead_mm"],
            lead_angle_deg=sample_design_7mm["worm"]["lead_angle_deg"],
            addendum_mm=sample_design_7mm["worm"]["addendum_mm"],
            dedendum_mm=sample_design_7mm["worm"]["dedendum_mm"],
            thread_thickness_mm=sample_design_7mm["worm"]["thread_thickness_mm"],
            hand="right",
            profile_shift=0.0
        )

    @pytest.fixture
    def wheel_params(self, sample_design_7mm):
        """Create WheelParams from sample design."""
        return WheelParams(
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

    @pytest.fixture
    def assembly_params(self, sample_design_7mm):
        """Create AssemblyParams from sample design."""
        return AssemblyParams(
            centre_distance_mm=sample_design_7mm["assembly"]["centre_distance_mm"],
            pressure_angle_deg=sample_design_7mm["assembly"]["pressure_angle_deg"],
            backlash_mm=sample_design_7mm["assembly"]["backlash_mm"],
            hand=sample_design_7mm["assembly"]["hand"],
            ratio=sample_design_7mm["assembly"]["ratio"]
        )

    def test_wheel_geometry_creation(self, wheel_params, worm_params, assembly_params):
        """Test creating a WheelGeometry instance."""
        wheel_geo = WheelGeometry(
            params=wheel_params,
            worm_params=worm_params,
            assembly_params=assembly_params,
            face_width=5.0
        )

        assert wheel_geo.params == wheel_params
        assert wheel_geo.worm_params == worm_params
        assert wheel_geo.face_width == 5.0

    def test_wheel_auto_face_width(self, wheel_params, worm_params, assembly_params):
        """Test that face width is auto-calculated when not specified."""
        wheel_geo = WheelGeometry(
            params=wheel_params,
            worm_params=worm_params,
            assembly_params=assembly_params,
            face_width=None
        )

        # Auto face width should be positive and reasonable
        assert wheel_geo.face_width > 0
        # Typically around 0.5-0.7 times worm tip diameter
        assert wheel_geo.face_width < worm_params.tip_diameter_mm * 1.5

    def test_wheel_build_returns_solid(self, wheel_params, worm_params, assembly_params):
        """Test that build() returns a valid solid."""
        wheel_geo = WheelGeometry(
            params=wheel_params,
            worm_params=worm_params,
            assembly_params=assembly_params,
            face_width=4.0
        )
        wheel = wheel_geo.build()

        assert wheel is not None
        assert hasattr(wheel, 'volume')
        assert wheel.volume > 0

    def test_wheel_volume_reasonable(self, wheel_params, worm_params, assembly_params):
        """Test that wheel volume is within reasonable bounds."""
        face_width = 4.0
        wheel_geo = WheelGeometry(
            params=wheel_params,
            worm_params=worm_params,
            assembly_params=assembly_params,
            face_width=face_width
        )
        wheel = wheel_geo.build()

        # Volume should be less than solid cylinder at tip diameter
        tip_radius = wheel_params.tip_diameter_mm / 2
        max_volume = math.pi * tip_radius**2 * face_width

        # And more than a small fraction of that (teeth take up space)
        min_volume = max_volume * 0.3

        assert wheel.volume > min_volume
        assert wheel.volume < max_volume

    def test_wheel_correct_tooth_count(self, wheel_params, worm_params, assembly_params):
        """Test wheel with different tooth counts."""
        for num_teeth in [10, 12, 20, 30]:
            params = WheelParams(
                module_mm=wheel_params.module_mm,
                num_teeth=num_teeth,
                pitch_diameter_mm=wheel_params.module_mm * num_teeth,
                tip_diameter_mm=wheel_params.module_mm * num_teeth + 2 * wheel_params.addendum_mm,
                root_diameter_mm=wheel_params.module_mm * num_teeth - 2 * wheel_params.dedendum_mm,
                throat_diameter_mm=wheel_params.module_mm * num_teeth + wheel_params.addendum_mm,
                helix_angle_deg=wheel_params.helix_angle_deg,
                addendum_mm=wheel_params.addendum_mm,
                dedendum_mm=wheel_params.dedendum_mm,
                profile_shift=0.0
            )

            wheel_geo = WheelGeometry(
                params=params,
                worm_params=worm_params,
                assembly_params=assembly_params,
                face_width=4.0
            )
            wheel = wheel_geo.build()

            assert wheel is not None
            assert wheel.volume > 0, f"Wheel with {num_teeth} teeth has zero volume"

    def test_wheel_different_face_widths(self, wheel_params, worm_params, assembly_params):
        """Test wheel generation with different face widths."""
        volumes = []
        for face_width in [2.0, 4.0, 6.0]:
            wheel_geo = WheelGeometry(
                params=wheel_params,
                worm_params=worm_params,
                assembly_params=assembly_params,
                face_width=face_width
            )
            wheel = wheel_geo.build()

            assert wheel is not None
            assert wheel.volume > 0
            volumes.append(wheel.volume)

        # Larger face width should mean larger volume
        assert volumes[1] > volumes[0]
        assert volumes[2] > volumes[1]

    def test_wheel_is_watertight(self, wheel_params, worm_params, assembly_params):
        """Test that the wheel geometry is watertight (valid solid)."""
        wheel_geo = WheelGeometry(
            params=wheel_params,
            worm_params=worm_params,
            assembly_params=assembly_params,
            face_width=4.0
        )
        wheel = wheel_geo.build()

        assert wheel.is_valid

    def test_wheel_bounding_box_reasonable(self, wheel_params, worm_params, assembly_params):
        """Test that wheel bounding box matches expected dimensions."""
        face_width = 4.0
        wheel_geo = WheelGeometry(
            params=wheel_params,
            worm_params=worm_params,
            assembly_params=assembly_params,
            face_width=face_width
        )
        wheel = wheel_geo.build()

        bbox = wheel.bounding_box()
        tip_diameter = wheel_params.tip_diameter_mm

        # X and Y extents should be approximately tip diameter
        x_extent = bbox.max.X - bbox.min.X
        y_extent = bbox.max.Y - bbox.min.Y
        z_extent = bbox.max.Z - bbox.min.Z

        # Throat cut reduces the wheel diameter, so allow more tolerance
        assert abs(x_extent - tip_diameter) < 2.0
        assert abs(y_extent - tip_diameter) < 2.0
        # Z extent should be close to face width (throat cut might reduce it slightly)
        assert z_extent <= face_width + 0.5
        assert z_extent >= face_width * 0.7

    def test_wheel_larger_design(self, sample_design_large):
        """Test wheel with larger design parameters."""
        worm_params = WormParams(
            module_mm=sample_design_large["worm"]["module_mm"],
            num_starts=sample_design_large["worm"]["num_starts"],
            pitch_diameter_mm=sample_design_large["worm"]["pitch_diameter_mm"],
            tip_diameter_mm=sample_design_large["worm"]["tip_diameter_mm"],
            root_diameter_mm=sample_design_large["worm"]["root_diameter_mm"],
            lead_mm=sample_design_large["worm"]["lead_mm"],
            lead_angle_deg=sample_design_large["worm"]["lead_angle_deg"],
            addendum_mm=sample_design_large["worm"]["addendum_mm"],
            dedendum_mm=sample_design_large["worm"]["dedendum_mm"],
            thread_thickness_mm=sample_design_large["worm"]["thread_thickness_mm"],
            hand="right",
            profile_shift=0.0
        )
        wheel_params = WheelParams(
            module_mm=sample_design_large["wheel"]["module_mm"],
            num_teeth=sample_design_large["wheel"]["num_teeth"],
            pitch_diameter_mm=sample_design_large["wheel"]["pitch_diameter_mm"],
            tip_diameter_mm=sample_design_large["wheel"]["tip_diameter_mm"],
            root_diameter_mm=sample_design_large["wheel"]["root_diameter_mm"],
            throat_diameter_mm=sample_design_large["wheel"]["throat_diameter_mm"],
            helix_angle_deg=sample_design_large["wheel"]["helix_angle_deg"],
            addendum_mm=sample_design_large["wheel"]["addendum_mm"],
            dedendum_mm=sample_design_large["wheel"]["dedendum_mm"],
            profile_shift=0.0
        )
        assembly_params = AssemblyParams(
            centre_distance_mm=sample_design_large["assembly"]["centre_distance_mm"],
            pressure_angle_deg=sample_design_large["assembly"]["pressure_angle_deg"],
            backlash_mm=sample_design_large["assembly"]["backlash_mm"],
            hand=sample_design_large["assembly"]["hand"],
            ratio=sample_design_large["assembly"]["ratio"]
        )

        wheel_geo = WheelGeometry(
            params=wheel_params,
            worm_params=worm_params,
            assembly_params=assembly_params,
            face_width=15.0
        )
        wheel = wheel_geo.build()

        assert wheel is not None
        assert wheel.volume > 0
        assert wheel.is_valid


class TestWheelFromJsonFile:
    """Tests using actual JSON files."""

    def test_build_wheel_from_7mm_json(self, examples_dir):
        """Test building wheel from 7mm.json example file."""
        example_file = examples_dir / "7mm.json"
        if not example_file.exists():
            pytest.skip("Example file not found")

        design = load_design_json(example_file)
        wheel_geo = WheelGeometry(
            params=design.wheel,
            worm_params=design.worm,
            assembly_params=design.assembly,
            face_width=4.0
        )
        wheel = wheel_geo.build()

        assert wheel is not None
        assert wheel.volume > 0
        assert wheel.is_valid
