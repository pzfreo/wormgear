"""
Tests for bore, keyway, and DD-cut geometry operations (requires build123d).

Fast dataclass/validation tests are in test_features_fast.py.
"""

import math
import pytest

from wormgear import (
    load_design_json, WormParams, WheelParams, AssemblyParams,
    WormGeometry, WheelGeometry,
    BoreFeature, KeywayFeature, DDCutFeature,
    calculate_default_ddcut,
)
from wormgear.core.features import (
    create_bore, create_keyway, create_ddcut,
)
from build123d import Cylinder, Axis, Align

pytestmark = pytest.mark.slow


class TestCreateDDCut:
    """Tests for create_ddcut function."""

    def test_create_ddcut_increases_volume(self):
        """Test that DD-cut adds material back to bore, increasing volume."""
        cylinder = Cylinder(radius=10, height=20,
                           align=(Align.CENTER, Align.CENTER, Align.CENTER))
        bore = BoreFeature(diameter=6.0)
        cylinder_with_bore = create_bore(cylinder, bore, 20, Axis.Z)
        bore_volume = cylinder_with_bore.volume

        ddcut = DDCutFeature(depth=0.6)
        cylinder_with_ddcut = create_ddcut(cylinder_with_bore, bore, ddcut, 20, Axis.Z)

        assert cylinder_with_ddcut.volume > bore_volume
        assert cylinder_with_ddcut.is_valid

    def test_create_ddcut_different_axes(self):
        """Test DD-cut creation along different axes."""
        cylinder = Cylinder(radius=10, height=20,
                           align=(Align.CENTER, Align.CENTER, Align.CENTER))
        bore = BoreFeature(diameter=4.0)
        ddcut = DDCutFeature(depth=0.4)

        for axis in [Axis.Z, Axis.X, Axis.Y]:
            cyl = create_bore(cylinder, bore, 20, axis)
            result = create_ddcut(cyl, bore, ddcut, 20, axis)
            assert result.is_valid

    def test_create_ddcut_with_angular_offset(self):
        """Test DD-cut with angular offset rotates the flats."""
        cylinder = Cylinder(radius=10, height=20,
                           align=(Align.CENTER, Align.CENTER, Align.CENTER))
        bore = BoreFeature(diameter=4.0)
        cylinder_with_bore = create_bore(cylinder, bore, 20, Axis.Z)

        ddcut_0 = DDCutFeature(depth=0.4, angular_offset=0.0)
        result_0 = create_ddcut(cylinder_with_bore, bore, ddcut_0, 20, Axis.Z)

        ddcut_45 = DDCutFeature(depth=0.4, angular_offset=45.0)
        result_45 = create_ddcut(cylinder_with_bore, bore, ddcut_45, 20, Axis.Z)

        assert result_0.is_valid
        assert result_45.is_valid
        assert abs(result_0.volume - result_45.volume) < 0.1


class TestCreateBore:
    """Tests for create_bore function."""

    def test_create_bore_through(self):
        """Test creating a through bore in a cylinder."""
        cylinder = Cylinder(radius=20, height=30,
                           align=(Align.CENTER, Align.CENTER, Align.CENTER))
        original_volume = cylinder.volume

        bore = BoreFeature(diameter=10)
        result = create_bore(cylinder, bore, 30, Axis.Z)

        assert result.volume < original_volume
        assert result.is_valid

        bore_volume = math.pi * 5**2 * 30
        expected_volume = original_volume - bore_volume
        assert abs(result.volume - expected_volume) < expected_volume * 0.05


class TestWormWithBore:
    """Tests for worm geometry with bore feature."""

    @pytest.fixture
    def worm_params(self, sample_design_7mm):
        """Create WormParams from sample design."""
        module_mm = sample_design_7mm["worm"]["module_mm"]
        return WormParams(
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

    def test_worm_with_bore(self, worm_params, assembly_params):
        """Test worm with bore has reduced volume."""
        worm_no_bore = WormGeometry(
            params=worm_params, assembly_params=assembly_params, length=10.0
        ).build()

        worm_with_bore = WormGeometry(
            params=worm_params, assembly_params=assembly_params, length=10.0,
            bore=BoreFeature(diameter=1.0)
        ).build()

        assert worm_with_bore.volume < worm_no_bore.volume
        assert worm_with_bore.is_valid

    def test_worm_with_bore_and_keyway(self, worm_params, assembly_params):
        """Test worm with bore and keyway."""
        worm_bore = WormGeometry(
            params=worm_params, assembly_params=assembly_params, length=10.0,
            bore=BoreFeature(diameter=6.0)
        ).build()

        worm_both = WormGeometry(
            params=worm_params, assembly_params=assembly_params, length=10.0,
            bore=BoreFeature(diameter=6.0), keyway=KeywayFeature()
        ).build()

        assert worm_both.volume < worm_bore.volume
        assert worm_both.is_valid


class TestWheelWithBore:
    """Tests for wheel geometry with bore feature."""

    @pytest.fixture
    def worm_params(self, sample_design_7mm):
        """Create WormParams from sample design."""
        module_mm = sample_design_7mm["worm"]["module_mm"]
        return WormParams(
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

    def test_wheel_with_bore(self, wheel_params, worm_params, assembly_params):
        """Test wheel with bore has reduced volume."""
        wheel_no_bore = WheelGeometry(
            params=wheel_params, worm_params=worm_params,
            assembly_params=assembly_params, face_width=4.0
        ).build()

        wheel_with_bore = WheelGeometry(
            params=wheel_params, worm_params=worm_params,
            assembly_params=assembly_params, face_width=4.0,
            bore=BoreFeature(diameter=1.5)
        ).build()

        assert wheel_with_bore.volume < wheel_no_bore.volume
        assert wheel_with_bore.is_valid

    def test_wheel_with_bore_and_keyway(self, wheel_params, worm_params, assembly_params):
        """Test wheel with bore and keyway using larger example design."""
        import json
        with open("examples/sample_m2_ratio30.json") as f:
            raw_data = json.load(f)
        design_data = raw_data.get("design", raw_data)

        from wormgear.io import WheelParams, WormParams, AssemblyParams

        large_wheel = WheelParams(
            module_mm=design_data["wheel"]["module_mm"],
            num_teeth=design_data["wheel"]["num_teeth"],
            pitch_diameter_mm=design_data["wheel"]["pitch_diameter_mm"],
            tip_diameter_mm=design_data["wheel"]["tip_diameter_mm"],
            root_diameter_mm=design_data["wheel"]["root_diameter_mm"],
            throat_diameter_mm=design_data["wheel"]["throat_diameter_mm"],
            helix_angle_deg=design_data["wheel"]["helix_angle_deg"],
            addendum_mm=design_data["wheel"]["addendum_mm"],
            dedendum_mm=design_data["wheel"]["dedendum_mm"],
            profile_shift=design_data["wheel"].get("profile_shift", 0.0)
        )
        worm_module = design_data["worm"]["module_mm"]
        large_worm = WormParams(
            module_mm=worm_module,
            num_starts=design_data["worm"]["num_starts"],
            pitch_diameter_mm=design_data["worm"]["pitch_diameter_mm"],
            tip_diameter_mm=design_data["worm"]["tip_diameter_mm"],
            root_diameter_mm=design_data["worm"]["root_diameter_mm"],
            lead_mm=design_data["worm"]["lead_mm"],
            axial_pitch_mm=worm_module * math.pi,
            lead_angle_deg=design_data["worm"]["lead_angle_deg"],
            addendum_mm=design_data["worm"]["addendum_mm"],
            dedendum_mm=design_data["worm"]["dedendum_mm"],
            thread_thickness_mm=design_data["worm"]["thread_thickness_mm"],
            hand=design_data["worm"].get("hand", design_data["assembly"].get("hand", "right")),
            profile_shift=design_data["worm"].get("profile_shift", 0.0)
        )
        large_assembly = AssemblyParams(
            centre_distance_mm=design_data["assembly"]["centre_distance_mm"],
            pressure_angle_deg=design_data["assembly"]["pressure_angle_deg"],
            backlash_mm=design_data["assembly"]["backlash_mm"],
            hand=design_data["assembly"]["hand"],
            ratio=design_data["assembly"]["ratio"]
        )

        wheel_bore = WheelGeometry(
            params=large_wheel, worm_params=large_worm,
            assembly_params=large_assembly, face_width=10.0,
            bore=BoreFeature(diameter=12.0)
        ).build()

        wheel_both = WheelGeometry(
            params=large_wheel, worm_params=large_worm,
            assembly_params=large_assembly, face_width=10.0,
            bore=BoreFeature(diameter=12.0), keyway=KeywayFeature()
        ).build()

        assert wheel_both.volume < wheel_bore.volume
        assert wheel_both.is_valid

    def test_wheel_throated_with_bore(self, wheel_params, worm_params, assembly_params):
        """Test throated wheel with bore."""
        wheel = WheelGeometry(
            params=wheel_params, worm_params=worm_params,
            assembly_params=assembly_params, face_width=4.0,
            throated=True, bore=BoreFeature(diameter=2.0)
        ).build()

        assert wheel.volume > 0
        assert wheel.is_valid


class TestFromJsonFile:
    """Tests using actual JSON file."""

    def test_worm_with_features_from_json(self, examples_dir):
        """Test worm with bore and keyway from JSON."""
        example_file = examples_dir / "7mm.json"
        if not example_file.exists():
            pytest.skip("Example file not found")

        design = load_design_json(example_file)
        worm = WormGeometry(
            params=design.worm, assembly_params=design.assembly, length=10.0,
            bore=BoreFeature(diameter=6.0), keyway=KeywayFeature()
        ).build()

        assert worm.volume > 0
        assert worm.is_valid

    def test_wheel_with_features_from_json(self, examples_dir):
        """Test wheel with bore and keyway from JSON."""
        example_file = examples_dir / "7mm.json"
        if not example_file.exists():
            pytest.skip("Example file not found")

        design = load_design_json(example_file)
        wheel = WheelGeometry(
            params=design.wheel, worm_params=design.worm,
            assembly_params=design.assembly, face_width=4.0,
            bore=BoreFeature(diameter=6.0), keyway=KeywayFeature()
        ).build()

        assert wheel.volume > 0
        assert wheel.is_valid


class TestWormWithDDCut:
    """Tests for worm geometry with DD-cut feature."""

    @pytest.fixture
    def worm_params(self, sample_design_7mm):
        module_mm = sample_design_7mm["worm"]["module_mm"]
        return WormParams(
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
            hand="right", profile_shift=0.0
        )

    @pytest.fixture
    def assembly_params(self, sample_design_7mm):
        return AssemblyParams(
            centre_distance_mm=sample_design_7mm["assembly"]["centre_distance_mm"],
            pressure_angle_deg=sample_design_7mm["assembly"]["pressure_angle_deg"],
            backlash_mm=sample_design_7mm["assembly"]["backlash_mm"],
            hand=sample_design_7mm["assembly"]["hand"],
            ratio=sample_design_7mm["assembly"]["ratio"]
        )

    def test_worm_with_ddcut(self, worm_params, assembly_params):
        """Test worm with bore and DD-cut."""
        worm_bore = WormGeometry(
            params=worm_params, assembly_params=assembly_params, length=10.0,
            bore=BoreFeature(diameter=3.0)
        ).build()

        worm_ddcut = WormGeometry(
            params=worm_params, assembly_params=assembly_params, length=10.0,
            bore=BoreFeature(diameter=3.0), ddcut=DDCutFeature(depth=0.4)
        ).build()

        assert worm_ddcut.volume > worm_bore.volume
        assert worm_ddcut.is_valid

    def test_worm_ddcut_vs_keyway_mutually_exclusive(self, worm_params, assembly_params):
        with pytest.raises(ValueError, match="Cannot specify both"):
            WormGeometry(
                params=worm_params, assembly_params=assembly_params, length=10.0,
                bore=BoreFeature(diameter=6.0), keyway=KeywayFeature(),
                ddcut=DDCutFeature(depth=0.6)
            ).build()

    def test_worm_ddcut_requires_bore(self, worm_params, assembly_params):
        with pytest.raises(ValueError, match="DD-cut requires a bore"):
            WormGeometry(
                params=worm_params, assembly_params=assembly_params, length=10.0,
                ddcut=DDCutFeature(depth=0.4)
            ).build()

    def test_worm_with_default_ddcut(self, worm_params, assembly_params):
        ddcut = calculate_default_ddcut(3.0)
        worm = WormGeometry(
            params=worm_params, assembly_params=assembly_params, length=10.0,
            bore=BoreFeature(diameter=3.0), ddcut=ddcut
        ).build()

        assert worm.volume > 0
        assert worm.is_valid


class TestWheelWithDDCut:
    """Tests for wheel geometry with DD-cut feature."""

    @pytest.fixture
    def worm_params(self, sample_design_7mm):
        module_mm = sample_design_7mm["worm"]["module_mm"]
        return WormParams(
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
            hand="right", profile_shift=0.0
        )

    @pytest.fixture
    def wheel_params(self, sample_design_7mm):
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
        return AssemblyParams(
            centre_distance_mm=sample_design_7mm["assembly"]["centre_distance_mm"],
            pressure_angle_deg=sample_design_7mm["assembly"]["pressure_angle_deg"],
            backlash_mm=sample_design_7mm["assembly"]["backlash_mm"],
            hand=sample_design_7mm["assembly"]["hand"],
            ratio=sample_design_7mm["assembly"]["ratio"]
        )

    def test_wheel_with_ddcut(self, wheel_params, worm_params, assembly_params):
        wheel_bore = WheelGeometry(
            params=wheel_params, worm_params=worm_params,
            assembly_params=assembly_params, face_width=4.0,
            bore=BoreFeature(diameter=2.0)
        ).build()

        wheel_ddcut = WheelGeometry(
            params=wheel_params, worm_params=worm_params,
            assembly_params=assembly_params, face_width=4.0,
            bore=BoreFeature(diameter=2.0), ddcut=DDCutFeature(depth=0.3)
        ).build()

        assert wheel_ddcut.volume > wheel_bore.volume
        assert wheel_ddcut.is_valid

    def test_wheel_ddcut_vs_keyway_mutually_exclusive(self, wheel_params, worm_params, assembly_params):
        with pytest.raises(ValueError, match="Cannot specify both"):
            WheelGeometry(
                params=wheel_params, worm_params=worm_params,
                assembly_params=assembly_params, face_width=4.0,
                bore=BoreFeature(diameter=6.0), keyway=KeywayFeature(),
                ddcut=DDCutFeature(depth=0.6)
            ).build()

    def test_wheel_ddcut_requires_bore(self, wheel_params, worm_params, assembly_params):
        with pytest.raises(ValueError, match="DD-cut requires a bore"):
            WheelGeometry(
                params=wheel_params, worm_params=worm_params,
                assembly_params=assembly_params, face_width=4.0,
                ddcut=DDCutFeature(depth=0.3)
            ).build()

    def test_wheel_throated_with_ddcut(self, wheel_params, worm_params, assembly_params):
        wheel = WheelGeometry(
            params=wheel_params, worm_params=worm_params,
            assembly_params=assembly_params, face_width=4.0,
            throated=True, bore=BoreFeature(diameter=2.0),
            ddcut=DDCutFeature(depth=0.3)
        ).build()

        assert wheel.volume > 0
        assert wheel.is_valid

    def test_wheel_with_default_ddcut(self, wheel_params, worm_params, assembly_params):
        ddcut = calculate_default_ddcut(2.0)
        wheel = WheelGeometry(
            params=wheel_params, worm_params=worm_params,
            assembly_params=assembly_params, face_width=4.0,
            bore=BoreFeature(diameter=2.0), ddcut=ddcut
        ).build()

        assert wheel.volume > 0
        assert wheel.is_valid
