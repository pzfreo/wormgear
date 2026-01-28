"""
Tests for bore and keyway features.
"""

import math
import pytest

from wormgear import (
    load_design_json, WormParams, WheelParams, AssemblyParams,
    WormGeometry, WheelGeometry,
    BoreFeature, KeywayFeature, DDCutFeature,
    get_din_6885_keyway, calculate_default_bore, calculate_default_ddcut,
)
from wormgear.core.features import SetScrewFeature, HubFeature, get_set_screw_size
from wormgear.core.features import (
    create_bore, create_keyway, create_ddcut,
    add_bore_and_keyway, DIN_6885_KEYWAYS,
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
        # 24mm pitch = 6mm target, large root gives room, rounds to 6.0
        bore, warning = calculate_default_bore(pitch_diameter=24.0, root_diameter=20.0)
        assert bore == 6.0
        assert warning is False

        # 30mm pitch = 7.5mm target, rounds to 7.5
        bore, warning = calculate_default_bore(pitch_diameter=30.0, root_diameter=26.0)
        assert bore == 7.5
        assert warning is False

    def test_large_gear_rounds_to_whole_mm(self):
        """Test large gear bore rounds to 1mm increments."""
        # 60mm pitch = 15mm target, rounds to 15
        bore, warning = calculate_default_bore(pitch_diameter=60.0, root_diameter=55.0)
        assert bore == 15.0
        assert warning is False

        # 80mm pitch = 20mm target, rounds to 20
        bore, warning = calculate_default_bore(pitch_diameter=80.0, root_diameter=72.0)
        assert bore == 20.0
        assert warning is False

    def test_minimum_bore_is_2mm(self):
        """Test minimum bore is 2mm for small gears."""
        # 6mm pitch = 1.5mm target, but min is 2mm
        # root 8mm gives max_bore = 6mm, so 2mm is valid
        bore, warning = calculate_default_bore(pitch_diameter=6.0, root_diameter=8.0)
        assert bore == 2.0
        # rim = (8 - 2) / 2 = 3mm, no warning
        assert warning is False

    def test_small_bore_without_keyway(self):
        """Test small bore (< 6mm) works but won't have DIN 6885 keyway."""
        # 12mm pitch = 3mm target, root 10mm = max ~7.5mm
        bore, warning = calculate_default_bore(pitch_diameter=12.0, root_diameter=10.0)
        assert bore == 3.0
        # No DIN 6885 keyway for bore < 6mm
        assert get_din_6885_keyway(bore) is None
        # rim = (10 - 3) / 2 = 3.5mm, no warning
        assert warning is False

    def test_returns_none_for_very_small_gear(self):
        """Test returns None when gear is too small for any bore."""
        # 4mm root: min_rim = max(4*0.125, 1.0) = 1.0mm per side
        # max_bore = 4 - 2*1 = 2mm, equals min_bore, should work
        # But 3mm root would fail
        bore, warning = calculate_default_bore(pitch_diameter=3.0, root_diameter=3.0)
        assert bore is None
        assert warning is False

    def test_maximum_bore_respects_rim_thickness(self):
        """Test maximum bore leaves percentage-based rim from root."""
        # 100mm pitch, 40mm root:
        # min_rim = max(40*0.125, 1.0) = 5mm per side
        # max_bore = 40 - 2*5 = 30mm
        # target = 25mm (25% of pitch), which is under max
        bore, warning = calculate_default_bore(pitch_diameter=100.0, root_diameter=40.0)
        assert bore == 25.0
        # rim = (40 - 25) / 2 = 7.5mm, no warning
        assert warning is False

        # Small root limits the bore
        # 100mm pitch, 12mm root:
        # min_rim = max(12*0.125, 1.0) = 1.5mm per side
        # max_bore = 12 - 2*1.5 = 9mm
        # target = 25mm, clamped to 9mm
        bore, warning = calculate_default_bore(pitch_diameter=100.0, root_diameter=12.0)
        assert bore == 9.0  # Clamped to max_bore
        # rim = (12 - 9) / 2 = 1.5mm, borderline but no warning (threshold is < 1.5)
        assert warning is False

    def test_thin_rim_warning(self):
        """Test warning is returned when rim is thin (< 1.5mm)."""
        # 6mm pitch, 4.75mm root (like 7mm worm):
        # min_rim = max(4.75*0.125, 1.0) = 1.0mm per side
        # max_bore = 4.75 - 2*1 = 2.75mm
        # target = 1.5mm, min is 2mm, so bore = 2mm
        # rim = (4.75 - 2) / 2 = 1.375mm < 1.5mm, should warn
        bore, warning = calculate_default_bore(pitch_diameter=6.0, root_diameter=4.75)
        assert bore == 2.0
        assert warning is True

    def test_7mm_worm_gets_bore_with_warning(self):
        """Test actual 7mm worm design gets a small bore with warning."""
        # From examples/7mm.json: pitch=6.0, root=4.75
        bore, warning = calculate_default_bore(pitch_diameter=6.0, root_diameter=4.75)
        assert bore == 2.0
        assert warning is True  # Thin rim warning


class TestDDCutFeature:
    """Tests for DDCutFeature dataclass."""

    def test_ddcut_creation_with_depth(self):
        """Test creating DD-cut with depth specification."""
        ddcut = DDCutFeature(depth=0.5)
        assert ddcut.depth == 0.5
        assert ddcut.flat_to_flat is None
        assert ddcut.angular_offset == 0.0
        assert ddcut.get_depth(3.0) == 0.5

    def test_ddcut_creation_with_flat_to_flat(self):
        """Test creating DD-cut with flat-to-flat specification."""
        ddcut = DDCutFeature(flat_to_flat=2.2)
        assert ddcut.flat_to_flat == 2.2
        assert ddcut.depth is None
        # 3mm bore: depth = (3.0 - 2.2) / 2 = 0.4
        assert ddcut.get_depth(3.0) == pytest.approx(0.4)

    def test_ddcut_with_angular_offset(self):
        """Test DD-cut with angular offset."""
        ddcut = DDCutFeature(depth=0.3, angular_offset=45.0)
        assert ddcut.angular_offset == 45.0

    def test_ddcut_requires_one_parameter(self):
        """Test that either depth or flat_to_flat must be specified."""
        with pytest.raises(ValueError, match="Must specify either"):
            DDCutFeature()  # Neither specified

    def test_ddcut_mutually_exclusive(self):
        """Test that depth and flat_to_flat are mutually exclusive."""
        with pytest.raises(ValueError, match="Cannot specify both"):
            DDCutFeature(depth=0.5, flat_to_flat=2.2)

    def test_ddcut_depth_must_be_positive(self):
        """Test that depth must be positive."""
        with pytest.raises(ValueError, match="must be positive"):
            DDCutFeature(depth=0)
        with pytest.raises(ValueError, match="must be positive"):
            DDCutFeature(depth=-0.5)

    def test_ddcut_flat_to_flat_must_be_positive(self):
        """Test that flat_to_flat must be positive."""
        with pytest.raises(ValueError, match="must be positive"):
            DDCutFeature(flat_to_flat=0)
        with pytest.raises(ValueError, match="must be positive"):
            DDCutFeature(flat_to_flat=-2.0)

    def test_ddcut_depth_too_large(self):
        """Test that depth cannot exceed bore radius."""
        ddcut = DDCutFeature(depth=2.0)  # 2mm depth
        # For 3mm bore (radius 1.5mm), depth of 2mm is too large
        with pytest.raises(ValueError, match="too large for bore diameter"):
            ddcut.get_depth(3.0)

    def test_ddcut_flat_to_flat_too_large(self):
        """Test that flat_to_flat cannot exceed bore diameter."""
        ddcut = DDCutFeature(flat_to_flat=4.0)  # 4mm flat-to-flat
        # For 3mm bore, this would require negative depth
        with pytest.raises(ValueError, match="too large for bore diameter"):
            ddcut.get_depth(3.0)

    def test_ddcut_flat_to_flat_at_boundary(self):
        """Test edge case where flat_to_flat approaches bore diameter."""
        # When flat_to_flat is very close to bore diameter, depth approaches 0
        ddcut = DDCutFeature(flat_to_flat=2.99)  # Almost the same as 3mm bore
        depth = ddcut.get_depth(3.0)
        # depth = (3.0 - 2.99)/2 = 0.005mm (very small but valid)
        assert depth == pytest.approx(0.005)
        assert depth > 0


class TestCalculateDefaultDDCut:
    """Tests for calculate_default_ddcut function."""

    def test_default_15_percent(self):
        """Test default 15% depth calculation."""
        ddcut = calculate_default_ddcut(3.0)
        # 15% of 3mm = 0.45mm, rounded to 0.4mm
        assert ddcut.depth == 0.4
        assert ddcut.flat_to_flat is None

    def test_custom_10_percent(self):
        """Test custom 10% depth calculation."""
        ddcut = calculate_default_ddcut(3.0, depth_percent=10.0)
        # 10% of 3mm = 0.3mm
        assert ddcut.depth == 0.3

    def test_custom_20_percent(self):
        """Test custom 20% depth calculation."""
        ddcut = calculate_default_ddcut(5.0, depth_percent=20.0)
        # 20% of 5mm = 1.0mm
        assert ddcut.depth == 1.0

    def test_rounding_to_tenth_mm(self):
        """Test that depth rounds to nearest 0.1mm."""
        ddcut = calculate_default_ddcut(3.3)
        # 15% of 3.3mm = 0.495mm, rounds to 0.5mm
        assert ddcut.depth == 0.5

    def test_minimum_depth_0_2mm(self):
        """Test minimum depth is 0.2mm."""
        ddcut = calculate_default_ddcut(1.0)  # Very small bore
        # 15% of 1mm = 0.15mm, but min is 0.2mm
        assert ddcut.depth >= 0.2

    def test_maximum_depth_25_percent(self):
        """Test maximum depth is clamped to 25% of diameter."""
        ddcut = calculate_default_ddcut(2.0, depth_percent=50.0)  # Request 50%
        # Should be clamped to 25% max: 0.5mm
        assert ddcut.depth == 0.5

    def test_various_bore_sizes(self):
        """Test sensible defaults for various bore sizes."""
        # 2mm bore: 15% = 0.3mm
        assert calculate_default_ddcut(2.0).depth == 0.3

        # 4mm bore: 15% = 0.6mm
        assert calculate_default_ddcut(4.0).depth == 0.6

        # 6mm bore: 15% = 0.9mm
        assert calculate_default_ddcut(6.0).depth == 0.9

        # 10mm bore: 15% = 1.5mm
        assert calculate_default_ddcut(10.0).depth == 1.5


class TestCreateDDCut:
    """Tests for create_ddcut function."""

    def test_create_ddcut_increases_volume(self):
        """Test that DD-cut adds material back to bore, increasing volume."""
        # Create a test cylinder with bore
        cylinder = Cylinder(radius=10, height=20,
                           align=(Align.CENTER, Align.CENTER, Align.CENTER))
        bore = BoreFeature(diameter=6.0)
        cylinder_with_bore = create_bore(cylinder, bore, 20, Axis.Z)
        bore_volume = cylinder_with_bore.volume

        # Add DD-cut (fills in parts of the bore)
        ddcut = DDCutFeature(depth=0.6)  # 15% of 4mm
        cylinder_with_ddcut = create_ddcut(cylinder_with_bore, bore, ddcut, 20, Axis.Z)

        # Volume should increase (material added back)
        assert cylinder_with_ddcut.volume > bore_volume
        assert cylinder_with_ddcut.is_valid

    def test_create_ddcut_different_axes(self):
        """Test DD-cut creation along different axes."""
        cylinder = Cylinder(radius=10, height=20,
                           align=(Align.CENTER, Align.CENTER, Align.CENTER))
        bore = BoreFeature(diameter=4.0)
        ddcut = DDCutFeature(depth=0.4)

        # Test Z axis
        cyl_z = create_bore(cylinder, bore, 20, Axis.Z)
        result_z = create_ddcut(cyl_z, bore, ddcut, 20, Axis.Z)
        assert result_z.is_valid

        # Test X axis
        cyl_x = create_bore(cylinder, bore, 20, Axis.X)
        result_x = create_ddcut(cyl_x, bore, ddcut, 20, Axis.X)
        assert result_x.is_valid

        # Test Y axis
        cyl_y = create_bore(cylinder, bore, 20, Axis.Y)
        result_y = create_ddcut(cyl_y, bore, ddcut, 20, Axis.Y)
        assert result_y.is_valid

    def test_create_ddcut_with_angular_offset(self):
        """Test DD-cut with angular offset rotates the flats."""
        cylinder = Cylinder(radius=10, height=20,
                           align=(Align.CENTER, Align.CENTER, Align.CENTER))
        bore = BoreFeature(diameter=4.0)
        cylinder_with_bore = create_bore(cylinder, bore, 20, Axis.Z)

        # DD-cut with 0° offset
        ddcut_0 = DDCutFeature(depth=0.4, angular_offset=0.0)
        result_0 = create_ddcut(cylinder_with_bore, bore, ddcut_0, 20, Axis.Z)

        # DD-cut with 45° offset
        ddcut_45 = DDCutFeature(depth=0.4, angular_offset=45.0)
        result_45 = create_ddcut(cylinder_with_bore, bore, ddcut_45, 20, Axis.Z)

        # Both should be valid but have different geometry
        assert result_0.is_valid
        assert result_45.is_valid
        # Volumes should be the same (same depth, just rotated)
        assert abs(result_0.volume - result_45.volume) < 0.1


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


class TestWormWithDDCut:
    """Tests for worm geometry with DD-cut feature."""

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

    def test_worm_with_ddcut(self, worm_params, assembly_params):
        """Test worm with bore and DD-cut."""
        # Build with bore only
        worm_geo_bore = WormGeometry(
            params=worm_params,
            assembly_params=assembly_params,
            length=10.0,
            bore=BoreFeature(diameter=3.0)
        )
        worm_bore = worm_geo_bore.build()

        # Build with bore and DD-cut
        worm_geo_ddcut = WormGeometry(
            params=worm_params,
            assembly_params=assembly_params,
            length=10.0,
            bore=BoreFeature(diameter=3.0),
            ddcut=DDCutFeature(depth=0.4)
        )
        worm_ddcut = worm_geo_ddcut.build()

        # Volume should increase (DD-cut fills in bore)
        assert worm_ddcut.volume > worm_bore.volume
        assert worm_ddcut.is_valid

    def test_worm_ddcut_vs_keyway_mutually_exclusive(self, worm_params, assembly_params):
        """Test that worm cannot have both DD-cut and keyway."""
        with pytest.raises(ValueError, match="Cannot specify both"):
            worm_geo = WormGeometry(
                params=worm_params,
                assembly_params=assembly_params,
                length=10.0,
                bore=BoreFeature(diameter=6.0),
                keyway=KeywayFeature(),
                ddcut=DDCutFeature(depth=0.6)
            )
            worm_geo.build()

    def test_worm_ddcut_requires_bore(self, worm_params, assembly_params):
        """Test that DD-cut requires a bore."""
        with pytest.raises(ValueError, match="DD-cut requires a bore"):
            worm_geo = WormGeometry(
                params=worm_params,
                assembly_params=assembly_params,
                length=10.0,
                ddcut=DDCutFeature(depth=0.4)  # No bore specified
            )
            worm_geo.build()

    def test_worm_with_default_ddcut(self, worm_params, assembly_params):
        """Test worm with auto-calculated DD-cut depth."""
        ddcut = calculate_default_ddcut(3.0)  # 15% of 3mm = 0.4mm
        worm_geo = WormGeometry(
            params=worm_params,
            assembly_params=assembly_params,
            length=10.0,
            bore=BoreFeature(diameter=3.0),
            ddcut=ddcut
        )
        worm = worm_geo.build()

        assert worm.volume > 0
        assert worm.is_valid


class TestWheelWithDDCut:
    """Tests for wheel geometry with DD-cut feature."""

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

    def test_wheel_with_ddcut(self, wheel_params, worm_params, assembly_params):
        """Test wheel with bore and DD-cut."""
        # Build with bore only
        wheel_geo_bore = WheelGeometry(
            params=wheel_params,
            worm_params=worm_params,
            assembly_params=assembly_params,
            face_width=4.0,
            bore=BoreFeature(diameter=2.0)
        )
        wheel_bore = wheel_geo_bore.build()

        # Build with bore and DD-cut
        wheel_geo_ddcut = WheelGeometry(
            params=wheel_params,
            worm_params=worm_params,
            assembly_params=assembly_params,
            face_width=4.0,
            bore=BoreFeature(diameter=2.0),
            ddcut=DDCutFeature(depth=0.3)
        )
        wheel_ddcut = wheel_geo_ddcut.build()

        # Volume should increase (DD-cut fills in bore)
        assert wheel_ddcut.volume > wheel_bore.volume
        assert wheel_ddcut.is_valid

    def test_wheel_ddcut_vs_keyway_mutually_exclusive(self, wheel_params, worm_params, assembly_params):
        """Test that wheel cannot have both DD-cut and keyway."""
        with pytest.raises(ValueError, match="Cannot specify both"):
            wheel_geo = WheelGeometry(
                params=wheel_params,
                worm_params=worm_params,
                assembly_params=assembly_params,
                face_width=4.0,
                bore=BoreFeature(diameter=6.0),
                keyway=KeywayFeature(),
                ddcut=DDCutFeature(depth=0.6)
            )
            wheel_geo.build()

    def test_wheel_ddcut_requires_bore(self, wheel_params, worm_params, assembly_params):
        """Test that DD-cut requires a bore."""
        with pytest.raises(ValueError, match="DD-cut requires a bore"):
            wheel_geo = WheelGeometry(
                params=wheel_params,
                worm_params=worm_params,
                assembly_params=assembly_params,
                face_width=4.0,
                ddcut=DDCutFeature(depth=0.3)  # No bore specified
            )
            wheel_geo.build()

    def test_wheel_throated_with_ddcut(self, wheel_params, worm_params, assembly_params):
        """Test throated wheel with DD-cut."""
        wheel_geo = WheelGeometry(
            params=wheel_params,
            worm_params=worm_params,
            assembly_params=assembly_params,
            face_width=4.0,
            throated=True,
            bore=BoreFeature(diameter=2.0),
            ddcut=DDCutFeature(depth=0.3)
        )
        wheel = wheel_geo.build()

        assert wheel.volume > 0
        assert wheel.is_valid

    def test_wheel_with_default_ddcut(self, wheel_params, worm_params, assembly_params):
        """Test wheel with auto-calculated DD-cut depth."""
        ddcut = calculate_default_ddcut(2.0)  # 15% of 2mm = 0.3mm
        wheel_geo = WheelGeometry(
            params=wheel_params,
            worm_params=worm_params,
            assembly_params=assembly_params,
            face_width=4.0,
            bore=BoreFeature(diameter=2.0),
            ddcut=ddcut
        )
        wheel = wheel_geo.build()

        assert wheel.volume > 0
        assert wheel.is_valid


class TestSetScrewFeature:
    """Tests for SetScrewFeature dataclass (P1.3)."""

    def test_set_screw_creation_default(self):
        """Test creating a set screw feature with defaults."""
        ss = SetScrewFeature()
        assert ss.size is None  # Auto-size
        assert ss.diameter is None  # Auto-size
        assert ss.count == 1
        assert ss.angular_offset == 90.0  # Default 90° from keyway

    def test_set_screw_with_explicit_size(self):
        """Test creating set screw with explicit M3 size."""
        ss = SetScrewFeature(size="M3", diameter=3.0)
        assert ss.size == "M3"
        assert ss.diameter == 3.0

    def test_set_screw_multiple_count(self):
        """Test creating multiple set screws."""
        ss = SetScrewFeature(count=2)
        assert ss.count == 2

        ss3 = SetScrewFeature(count=3)
        assert ss3.count == 3

    def test_set_screw_angular_offset(self):
        """Test set screw with custom angular offset."""
        ss = SetScrewFeature(angular_offset=45.0)
        assert ss.angular_offset == 45.0

    def test_set_screw_invalid_count_low(self):
        """Test that count < 1 raises error."""
        with pytest.raises(ValueError, match="must be 1-3"):
            SetScrewFeature(count=0)

    def test_set_screw_invalid_count_high(self):
        """Test that count > 3 raises error."""
        with pytest.raises(ValueError, match="must be 1-3"):
            SetScrewFeature(count=4)

    def test_set_screw_invalid_diameter(self):
        """Test that negative diameter raises error."""
        with pytest.raises(ValueError, match="must be positive"):
            SetScrewFeature(diameter=-1.0)

        with pytest.raises(ValueError, match="must be positive"):
            SetScrewFeature(diameter=0)

    def test_set_screw_auto_size_small_bore(self):
        """Test auto-sizing for small bore returns small screw."""
        ss = SetScrewFeature()
        size, diameter = ss.get_screw_specs(bore_diameter=4.0)
        # 4mm bore should get M2 or similar small screw
        assert diameter <= 2.5
        assert size is not None

    def test_set_screw_auto_size_medium_bore(self):
        """Test auto-sizing for medium bore."""
        ss = SetScrewFeature()
        size, diameter = ss.get_screw_specs(bore_diameter=10.0)
        # 10mm bore should get M3 or M4
        assert 2.5 <= diameter <= 4.5
        assert size in ["M3", "M4"]

    def test_set_screw_auto_size_large_bore(self):
        """Test auto-sizing for large bore."""
        ss = SetScrewFeature()
        size, diameter = ss.get_screw_specs(bore_diameter=20.0)
        # 20mm bore should get M4 or M5
        assert 4.0 <= diameter <= 6.0

    def test_set_screw_explicit_overrides_auto(self):
        """Test that explicit size/diameter override auto-sizing."""
        ss = SetScrewFeature(size="M6", diameter=6.0)
        size, diameter = ss.get_screw_specs(bore_diameter=5.0)  # Small bore
        # Should still use explicit values
        assert size == "M6"
        assert diameter == 6.0


class TestHubFeature:
    """Tests for HubFeature dataclass (P1.4)."""

    def test_hub_flush_default(self):
        """Test creating flush hub (default)."""
        hub = HubFeature()
        assert hub.hub_type == "flush"
        assert hub.length is None  # No extension for flush

    def test_hub_extended(self):
        """Test creating extended hub."""
        hub = HubFeature(hub_type="extended")
        assert hub.hub_type == "extended"
        assert hub.length == 10.0  # Default 10mm extension

    def test_hub_extended_custom_length(self):
        """Test extended hub with custom length."""
        hub = HubFeature(hub_type="extended", length=15.0)
        assert hub.hub_type == "extended"
        assert hub.length == 15.0

    def test_hub_flanged(self):
        """Test creating flanged hub."""
        hub = HubFeature(hub_type="flanged", flange_diameter=30.0)
        assert hub.hub_type == "flanged"
        assert hub.length == 10.0  # Default
        assert hub.flange_thickness == 5.0  # Default
        assert hub.flange_diameter == 30.0
        assert hub.bolt_holes == 4  # Default

    def test_hub_flanged_custom(self):
        """Test flanged hub with custom dimensions."""
        hub = HubFeature(
            hub_type="flanged",
            length=20.0,
            flange_diameter=40.0,
            flange_thickness=8.0,
            bolt_holes=6,
            bolt_diameter=5.0
        )
        assert hub.length == 20.0
        assert hub.flange_diameter == 40.0
        assert hub.flange_thickness == 8.0
        assert hub.bolt_holes == 6
        assert hub.bolt_diameter == 5.0

    def test_hub_invalid_type(self):
        """Test that invalid hub type raises error."""
        with pytest.raises(ValueError, match="must be one of"):
            HubFeature(hub_type="invalid")

    def test_hub_extended_invalid_length(self):
        """Test that invalid length raises error."""
        with pytest.raises(ValueError, match="must be positive"):
            HubFeature(hub_type="extended", length=0)

        with pytest.raises(ValueError, match="must be positive"):
            HubFeature(hub_type="extended", length=-5.0)

    def test_hub_flanged_invalid_thickness(self):
        """Test that invalid flange thickness raises error."""
        with pytest.raises(ValueError, match="must be positive"):
            HubFeature(hub_type="flanged", flange_thickness=0)

    def test_hub_flanged_invalid_bolt_holes(self):
        """Test that invalid bolt hole count raises error."""
        with pytest.raises(ValueError, match="Bolt holes must be"):
            HubFeature(hub_type="flanged", bolt_holes=-1)

        with pytest.raises(ValueError, match="Bolt holes must be"):
            HubFeature(hub_type="flanged", bolt_holes=9)

    def test_hub_flush_ignores_length(self):
        """Test that flush hub ignores length parameter."""
        hub = HubFeature(hub_type="flush", length=20.0)
        # Length is set but not used for flush hub
        assert hub.hub_type == "flush"


class TestGetSetScrewSize:
    """Tests for get_set_screw_size function."""

    def test_very_small_bore(self):
        """Test set screw sizing for very small bores."""
        size, diameter = get_set_screw_size(3.0)
        assert size == "M2"
        assert diameter == 2.0

    def test_small_bore(self):
        """Test set screw sizing for small bores."""
        size, diameter = get_set_screw_size(6.0)
        assert size in ["M2", "M2.5", "M3"]
        assert diameter <= 3.0

    def test_medium_bore(self):
        """Test set screw sizing for medium bores."""
        size, diameter = get_set_screw_size(12.0)
        assert size in ["M3", "M4"]
        assert 3.0 <= diameter <= 4.0

    def test_large_bore(self):
        """Test set screw sizing for large bores."""
        size, diameter = get_set_screw_size(25.0)
        assert size in ["M4", "M5", "M6"]
        assert 4.0 <= diameter <= 6.0

    def test_very_large_bore(self):
        """Test set screw sizing for very large bores."""
        size, diameter = get_set_screw_size(50.0)
        assert size in ["M6", "M8"]
        assert 6.0 <= diameter <= 8.0
