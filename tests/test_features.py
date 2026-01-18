"""
Tests for bore and keyway features.
"""

import math
import pytest

from wormgear_geometry.io import load_design_json, WormParams, WheelParams, AssemblyParams
from wormgear_geometry.worm import WormGeometry
from wormgear_geometry.wheel import WheelGeometry
from wormgear_geometry.features import (
    BoreFeature,
    KeywayFeature,
    get_din_6885_keyway,
    calculate_default_bore,
    create_bore,
    create_keyway,
    add_bore_and_keyway,
    DIN_6885_KEYWAYS,
)
from build123d import Cylinder, Axis, Align


class TestBoreFeature:
    """Tests for BoreFeature dataclass."""

    def test_bore_creation(self):
        """Test creating a bore feature."""
        bore = BoreFeature(diameter=10.0)
        assert bore.diameter == 10.0
        assert bore.through is True
        assert bore.depth is None

    def test_bore_non_through(self):
        """Test creating a non-through bore."""
        bore = BoreFeature(diameter=8.0, through=False, depth=15.0)
        assert bore.diameter == 8.0
        assert bore.through is False
        assert bore.depth == 15.0

    def test_bore_invalid_diameter(self):
        """Test that invalid diameter raises error."""
        with pytest.raises(ValueError):
            BoreFeature(diameter=0)
        with pytest.raises(ValueError):
            BoreFeature(diameter=-5)

    def test_bore_non_through_requires_depth(self):
        """Test that non-through bore requires depth."""
        with pytest.raises(ValueError):
            BoreFeature(diameter=10, through=False)

    def test_bore_invalid_depth(self):
        """Test that invalid depth raises error."""
        with pytest.raises(ValueError):
            BoreFeature(diameter=10, through=False, depth=0)
        with pytest.raises(ValueError):
            BoreFeature(diameter=10, through=False, depth=-5)


class TestKeywayFeature:
    """Tests for KeywayFeature dataclass."""

    def test_keyway_creation(self):
        """Test creating a keyway feature."""
        keyway = KeywayFeature()
        assert keyway.width is None
        assert keyway.depth is None
        assert keyway.length is None
        assert keyway.is_shaft is False

    def test_keyway_with_custom_dimensions(self):
        """Test creating keyway with custom dimensions."""
        keyway = KeywayFeature(width=5.0, depth=2.5, length=20.0)
        assert keyway.width == 5.0
        assert keyway.depth == 2.5
        assert keyway.length == 20.0

    def test_keyway_get_dimensions_auto(self):
        """Test auto-calculating keyway dimensions from bore."""
        keyway = KeywayFeature()
        width, depth = keyway.get_dimensions(bore_diameter=9.0)
        # DIN 6885 for 8-10mm range: width=3, hub_depth=1.4
        assert width == 3.0
        assert depth == 1.4  # Hub depth (is_shaft=False)

    def test_keyway_get_dimensions_shaft(self):
        """Test shaft keyway dimensions."""
        keyway = KeywayFeature(is_shaft=True)
        width, depth = keyway.get_dimensions(bore_diameter=9.0)
        # DIN 6885 for 8-10mm range: width=3, shaft_depth=1.8
        assert width == 3.0
        assert depth == 1.8  # Shaft depth

    def test_keyway_get_dimensions_custom(self):
        """Test custom keyway dimensions are used."""
        keyway = KeywayFeature(width=4.0, depth=2.0)
        width, depth = keyway.get_dimensions(bore_diameter=10.0)
        assert width == 4.0
        assert depth == 2.0

    def test_keyway_invalid_bore_size(self):
        """Test error for bore outside DIN 6885 range."""
        keyway = KeywayFeature()
        with pytest.raises(ValueError):
            keyway.get_dimensions(bore_diameter=5.0)  # Too small
        with pytest.raises(ValueError):
            keyway.get_dimensions(bore_diameter=100.0)  # Too large


class TestDIN6885Lookup:
    """Tests for DIN 6885 lookup function."""

    def test_lookup_6mm(self):
        """Test lookup for 6mm bore."""
        dims = get_din_6885_keyway(6.0)
        assert dims == (2, 2, 1.2, 1.0)

    def test_lookup_9mm(self):
        """Test lookup for 9mm bore (in 8-10 range)."""
        dims = get_din_6885_keyway(9.0)
        assert dims == (3, 3, 1.8, 1.4)

    def test_lookup_11mm(self):
        """Test lookup for 11mm bore (in 10-12 range)."""
        dims = get_din_6885_keyway(11.0)
        assert dims == (4, 4, 2.5, 1.8)

    def test_lookup_boundary(self):
        """Test lookup at boundary values."""
        # Just below 10mm boundary
        dims_9 = get_din_6885_keyway(9.9)
        assert dims_9 == (3, 3, 1.8, 1.4)  # 8-10 range

        # At 10mm boundary (starts new range)
        dims_10 = get_din_6885_keyway(10.0)
        assert dims_10 == (4, 4, 2.5, 1.8)  # 10-12 range

        # Just below 12mm boundary
        dims_11 = get_din_6885_keyway(11.9)
        assert dims_11 == (4, 4, 2.5, 1.8)  # 10-12 range

    def test_lookup_outside_range(self):
        """Test lookup outside DIN 6885 range."""
        assert get_din_6885_keyway(5.0) is None
        assert get_din_6885_keyway(100.0) is None


class TestCalculateDefaultBore:
    """Tests for calculate_default_bore function."""

    def test_small_gear_rounds_to_half_mm(self):
        """Test small gear bore rounds to 0.5mm increments."""
        # 24mm pitch = 6mm target, rounds to 6.0
        bore = calculate_default_bore(pitch_diameter=24.0, root_diameter=20.0)
        assert bore == 6.0

        # 30mm pitch = 7.5mm target, rounds to 7.5
        bore = calculate_default_bore(pitch_diameter=30.0, root_diameter=26.0)
        assert bore == 7.5

    def test_large_gear_rounds_to_whole_mm(self):
        """Test large gear bore rounds to 1mm increments."""
        # 60mm pitch = 15mm target, rounds to 15
        bore = calculate_default_bore(pitch_diameter=60.0, root_diameter=55.0)
        assert bore == 15.0

        # 80mm pitch = 20mm target, rounds to 20
        bore = calculate_default_bore(pitch_diameter=80.0, root_diameter=72.0)
        assert bore == 20.0

    def test_minimum_bore_is_6mm(self):
        """Test minimum bore is 6mm (smallest DIN 6885 keyway)."""
        # 16mm pitch = 4mm target, but min is 6mm
        bore = calculate_default_bore(pitch_diameter=16.0, root_diameter=14.0)
        assert bore == 6.0

    def test_maximum_bore_respects_rim_thickness(self):
        """Test maximum bore leaves 3mm rim from root."""
        # 100mm pitch, 40mm root = max bore 34mm
        # 25% of 100 = 25mm, which is under max
        bore = calculate_default_bore(pitch_diameter=100.0, root_diameter=40.0)
        assert bore == 25.0

        # Very small root limits the bore
        # 100mm pitch, 15mm root = max bore 9mm
        bore = calculate_default_bore(pitch_diameter=100.0, root_diameter=15.0)
        assert bore == 9.0  # Clamped to max_bore


class TestCreateBore:
    """Tests for create_bore function."""

    def test_create_bore_through(self):
        """Test creating a through bore in a cylinder."""
        # Create a test cylinder
        cylinder = Cylinder(radius=20, height=30,
                           align=(Align.CENTER, Align.CENTER, Align.CENTER))
        original_volume = cylinder.volume

        # Create bore
        bore = BoreFeature(diameter=10)
        result = create_bore(cylinder, bore, 30, Axis.Z)

        # Volume should be reduced
        assert result.volume < original_volume
        assert result.is_valid

        # Check approximate volume reduction (bore volume)
        bore_volume = math.pi * 5**2 * 30  # radius=5, height=30 (part length)
        expected_volume = original_volume - bore_volume
        # Allow 5% tolerance for floating point and geometry differences
        assert abs(result.volume - expected_volume) < expected_volume * 0.05


class TestWormWithBore:
    """Tests for worm geometry with bore feature."""

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
        # Build without bore
        worm_geo_no_bore = WormGeometry(
            params=worm_params,
            assembly_params=assembly_params,
            length=10.0
        )
        worm_no_bore = worm_geo_no_bore.build()

        # Build with bore
        worm_geo_with_bore = WormGeometry(
            params=worm_params,
            assembly_params=assembly_params,
            length=10.0,
            bore=BoreFeature(diameter=1.0)
        )
        worm_with_bore = worm_geo_with_bore.build()

        # Volume should be reduced
        assert worm_with_bore.volume < worm_no_bore.volume
        assert worm_with_bore.is_valid

    def test_worm_with_bore_and_keyway(self, worm_params, assembly_params):
        """Test worm with bore and keyway."""
        # Build with bore only
        worm_geo_bore = WormGeometry(
            params=worm_params,
            assembly_params=assembly_params,
            length=10.0,
            bore=BoreFeature(diameter=6.0)
        )
        worm_bore = worm_geo_bore.build()

        # Build with bore and keyway
        worm_geo_both = WormGeometry(
            params=worm_params,
            assembly_params=assembly_params,
            length=10.0,
            bore=BoreFeature(diameter=6.0),
            keyway=KeywayFeature()
        )
        worm_both = worm_geo_both.build()

        # Volume with keyway should be less than bore only
        assert worm_both.volume < worm_bore.volume
        assert worm_both.is_valid


class TestWheelWithBore:
    """Tests for wheel geometry with bore feature."""

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

    def test_wheel_with_bore(self, wheel_params, worm_params, assembly_params):
        """Test wheel with bore has reduced volume."""
        # Build without bore
        wheel_geo_no_bore = WheelGeometry(
            params=wheel_params,
            worm_params=worm_params,
            assembly_params=assembly_params,
            face_width=4.0
        )
        wheel_no_bore = wheel_geo_no_bore.build()

        # Build with bore
        wheel_geo_with_bore = WheelGeometry(
            params=wheel_params,
            worm_params=worm_params,
            assembly_params=assembly_params,
            face_width=4.0,
            bore=BoreFeature(diameter=1.5)
        )
        wheel_with_bore = wheel_geo_with_bore.build()

        # Volume should be reduced
        assert wheel_with_bore.volume < wheel_no_bore.volume
        assert wheel_with_bore.is_valid

    def test_wheel_with_bore_and_keyway(self, wheel_params, worm_params, assembly_params):
        """Test wheel with bore and keyway using larger example design."""
        # Use larger design that can accommodate a realistic bore/keyway
        # The 7mm design is too small for a 6mm bore - root diameter is only ~5mm
        # Use sample_m2_ratio30 design which has a larger wheel
        import json
        with open("examples/sample_m2_ratio30.json") as f:
            raw_data = json.load(f)
        # Handle nested "design" key if present
        design_data = raw_data.get("design", raw_data)

        from wormgear_geometry.io import WheelParams, WormParams, AssemblyParams

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
        large_worm = WormParams(
            module_mm=design_data["worm"]["module_mm"],
            num_starts=design_data["worm"]["num_starts"],
            pitch_diameter_mm=design_data["worm"]["pitch_diameter_mm"],
            tip_diameter_mm=design_data["worm"]["tip_diameter_mm"],
            root_diameter_mm=design_data["worm"]["root_diameter_mm"],
            lead_mm=design_data["worm"]["lead_mm"],
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

        # Build with bore only (12mm bore fits in 60mm pitch diameter wheel)
        wheel_geo_bore = WheelGeometry(
            params=large_wheel,
            worm_params=large_worm,
            assembly_params=large_assembly,
            face_width=10.0,
            bore=BoreFeature(diameter=12.0)
        )
        wheel_bore = wheel_geo_bore.build()

        # Build with bore and keyway
        wheel_geo_both = WheelGeometry(
            params=large_wheel,
            worm_params=large_worm,
            assembly_params=large_assembly,
            face_width=10.0,
            bore=BoreFeature(diameter=12.0),
            keyway=KeywayFeature()
        )
        wheel_both = wheel_geo_both.build()

        # Volume with keyway should be less than bore only
        assert wheel_both.volume < wheel_bore.volume
        assert wheel_both.is_valid

    def test_wheel_throated_with_bore(self, wheel_params, worm_params, assembly_params):
        """Test throated wheel with bore."""
        wheel_geo = WheelGeometry(
            params=wheel_params,
            worm_params=worm_params,
            assembly_params=assembly_params,
            face_width=4.0,
            throated=True,
            bore=BoreFeature(diameter=2.0)
        )
        wheel = wheel_geo.build()

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
        worm_geo = WormGeometry(
            params=design.worm,
            assembly_params=design.assembly,
            length=10.0,
            bore=BoreFeature(diameter=6.0),
            keyway=KeywayFeature()
        )
        worm = worm_geo.build()

        assert worm.volume > 0
        assert worm.is_valid

    def test_wheel_with_features_from_json(self, examples_dir):
        """Test wheel with bore and keyway from JSON."""
        example_file = examples_dir / "7mm.json"
        if not example_file.exists():
            pytest.skip("Example file not found")

        design = load_design_json(example_file)
        wheel_geo = WheelGeometry(
            params=design.wheel,
            worm_params=design.worm,
            assembly_params=design.assembly,
            face_width=4.0,
            bore=BoreFeature(diameter=6.0),
            keyway=KeywayFeature()
        )
        wheel = wheel_geo.build()

        assert wheel.volume > 0
        assert wheel.is_valid
