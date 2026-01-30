"""Tests for post-build rim thickness measurement."""

import pytest
from wormgear.io.loaders import load_design_json
from wormgear.core.wheel import WheelGeometry
from wormgear.core.worm import WormGeometry
from wormgear.core.features import BoreFeature, KeywayFeature, DDCutFeature
from wormgear.core.rim_thickness import (
    measure_rim_thickness,
    rim_thickness_to_dict,
    RimThicknessResult,
    WHEEL_RIM_WARNING_THRESHOLD_MM,
    WORM_RIM_WARNING_THRESHOLD_MM,
)
from pathlib import Path


# Get the example design file
EXAMPLE_FILE = Path(__file__).parent.parent / "examples" / "sample_m2_ratio30.json"


@pytest.fixture
def design():
    """Load the example design."""
    return load_design_json(EXAMPLE_FILE)


@pytest.fixture
def wheel_with_bore(design):
    """Build a wheel with a 15mm bore and keyway."""
    bore = BoreFeature(diameter=15.0)
    keyway = KeywayFeature()
    wheel_geo = WheelGeometry(
        params=design.wheel,
        worm_params=design.worm,
        assembly_params=design.assembly,
        bore=bore,
        keyway=keyway,
    )
    return wheel_geo.build()


@pytest.fixture
def wheel_with_bore_no_keyway(design):
    """Build a wheel with a 15mm bore but no keyway."""
    bore = BoreFeature(diameter=15.0)
    wheel_geo = WheelGeometry(
        params=design.wheel,
        worm_params=design.worm,
        assembly_params=design.assembly,
        bore=bore,
    )
    return wheel_geo.build()


@pytest.fixture
def worm_with_bore(design):
    """Build a worm with a 4mm bore."""
    bore = BoreFeature(diameter=4.0)
    worm_geo = WormGeometry(
        params=design.worm,
        assembly_params=design.assembly,
        length=40.0,
        bore=bore,
    )
    return worm_geo.build()


class TestRimThicknessMeasurement:
    """Test rim thickness measurement functionality."""

    def test_wheel_rim_with_keyway(self, wheel_with_bore):
        """Test that wheel rim is measured at keyway (thinnest point)."""
        result = measure_rim_thickness(
            wheel_with_bore,
            bore_diameter_mm=15.0,
            is_worm=False,
        )

        assert result.is_valid
        # With keyway, rim should be around 2.1-2.3mm (keyway depth)
        assert 1.5 < result.minimum_thickness_mm < 3.0
        assert result.bore_diameter_mm == 15.0
        assert result.measurement_point_bore is not None
        assert result.measurement_point_outer is not None

    def test_wheel_rim_without_keyway(self, wheel_with_bore_no_keyway, design):
        """Test that wheel rim without keyway is bore to tooth root."""
        result = measure_rim_thickness(
            wheel_with_bore_no_keyway,
            bore_diameter_mm=15.0,
            is_worm=False,
        )

        assert result.is_valid
        # Without keyway, rim should be (root_diameter - bore_diameter) / 2
        # root_diameter = 55mm, bore = 15mm, expected rim ≈ 20mm
        expected_rim = (design.wheel.root_diameter_mm - 15.0) / 2
        # Allow some tolerance for geometry details
        assert result.minimum_thickness_mm > expected_rim * 0.9
        assert result.minimum_thickness_mm < expected_rim * 1.1

    def test_worm_rim_measurement(self, worm_with_bore, design):
        """Test worm rim measurement from bore to thread root."""
        result = measure_rim_thickness(
            worm_with_bore,
            bore_diameter_mm=4.0,
            is_worm=True,
        )

        assert result.is_valid
        # Worm rim should be (root_diameter - bore_diameter) / 2
        # root_diameter ≈ 11.3mm, bore = 4mm, expected rim ≈ 3.6mm
        expected_rim = (design.worm.root_diameter_mm - 4.0) / 2
        assert result.minimum_thickness_mm > expected_rim * 0.9
        assert result.minimum_thickness_mm < expected_rim * 1.1

    def test_warning_threshold_wheel(self, design):
        """Test that thin wheel rim triggers warning."""
        # Use a large bore to create thin rim
        large_bore = design.wheel.root_diameter_mm - 1.0  # Very thin rim
        bore = BoreFeature(diameter=large_bore)
        wheel_geo = WheelGeometry(
            params=design.wheel,
            worm_params=design.worm,
            assembly_params=design.assembly,
            bore=bore,
        )
        wheel = wheel_geo.build()

        result = measure_rim_thickness(
            wheel,
            bore_diameter_mm=large_bore,
            is_worm=False,
        )

        assert result.is_valid
        assert result.has_warning  # Should warn for very thin rim
        assert result.warning_threshold_mm == WHEEL_RIM_WARNING_THRESHOLD_MM

    def test_warning_threshold_worm(self, design):
        """Test that thin worm rim triggers warning."""
        # Use a large bore to create thin rim
        large_bore = design.worm.root_diameter_mm - 1.5  # Very thin rim
        bore = BoreFeature(diameter=large_bore)
        worm_geo = WormGeometry(
            params=design.worm,
            assembly_params=design.assembly,
            length=40.0,
            bore=bore,
        )
        worm = worm_geo.build()

        result = measure_rim_thickness(
            worm,
            bore_diameter_mm=large_bore,
            is_worm=True,
        )

        assert result.is_valid
        assert result.has_warning  # Should warn for very thin rim
        assert result.warning_threshold_mm == WORM_RIM_WARNING_THRESHOLD_MM

    def test_custom_warning_threshold(self, wheel_with_bore):
        """Test custom warning threshold."""
        result = measure_rim_thickness(
            wheel_with_bore,
            bore_diameter_mm=15.0,
            warning_threshold_mm=5.0,  # High threshold
        )

        assert result.is_valid
        assert result.has_warning  # 2.16mm < 5.0mm threshold
        assert result.warning_threshold_mm == 5.0


class TestRimThicknessResultConversion:
    """Test RimThicknessResult to dict conversion."""

    def test_to_dict_basic(self, wheel_with_bore):
        """Test basic conversion to dictionary."""
        result = measure_rim_thickness(
            wheel_with_bore,
            bore_diameter_mm=15.0,
        )

        d = rim_thickness_to_dict(result)

        assert "minimum_thickness_mm" in d
        assert "bore_diameter_mm" in d
        assert "is_valid" in d
        assert "has_warning" in d
        assert "warning_threshold_mm" in d
        assert "message" in d
        assert d["bore_diameter_mm"] == 15.0
        assert d["is_valid"] is True

    def test_to_dict_includes_points(self, wheel_with_bore):
        """Test that measurement points are included in dict."""
        result = measure_rim_thickness(
            wheel_with_bore,
            bore_diameter_mm=15.0,
        )

        d = rim_thickness_to_dict(result)

        assert "measurement_point_bore" in d
        assert "measurement_point_outer" in d
        assert "x_mm" in d["measurement_point_bore"]
        assert "y_mm" in d["measurement_point_bore"]
        assert "z_mm" in d["measurement_point_bore"]

    def test_to_dict_values_rounded(self, wheel_with_bore):
        """Test that values are properly rounded."""
        result = measure_rim_thickness(
            wheel_with_bore,
            bore_diameter_mm=15.0,
        )

        d = rim_thickness_to_dict(result)

        # Check that values are rounded to 4 decimal places
        thickness_str = str(d["minimum_thickness_mm"])
        if "." in thickness_str:
            decimals = len(thickness_str.split(".")[1])
            assert decimals <= 4


class TestRimThicknessEdgeCases:
    """Test edge cases and error handling."""

    def test_small_bore(self, design):
        """Test measurement with small bore diameter."""
        bore = BoreFeature(diameter=2.0)  # Very small bore
        worm_geo = WormGeometry(
            params=design.worm,
            assembly_params=design.assembly,
            length=40.0,
            bore=bore,
        )
        worm = worm_geo.build()

        result = measure_rim_thickness(
            worm,
            bore_diameter_mm=2.0,
            is_worm=True,
        )

        assert result.is_valid
        # Small bore should give larger rim
        assert result.minimum_thickness_mm > 4.0

    def test_different_axial_samples(self, wheel_with_bore):
        """Test that different axial sample counts work."""
        result1 = measure_rim_thickness(
            wheel_with_bore,
            bore_diameter_mm=15.0,
            axial_samples=3,
        )

        result2 = measure_rim_thickness(
            wheel_with_bore,
            bore_diameter_mm=15.0,
            axial_samples=10,
        )

        # Both should be valid and similar (within 10%)
        assert result1.is_valid
        assert result2.is_valid
        assert abs(result1.minimum_thickness_mm - result2.minimum_thickness_mm) < 0.5

    def test_different_angular_samples(self, wheel_with_bore):
        """Test that different angular sample counts work."""
        result1 = measure_rim_thickness(
            wheel_with_bore,
            bore_diameter_mm=15.0,
            angular_samples=36,
        )

        result2 = measure_rim_thickness(
            wheel_with_bore,
            bore_diameter_mm=15.0,
            angular_samples=144,
        )

        # Both should be valid and similar
        assert result1.is_valid
        assert result2.is_valid
        # More samples might find slightly thinner point
        assert result2.minimum_thickness_mm <= result1.minimum_thickness_mm + 0.1


class TestRimThicknessWithDDCut:
    """Test rim thickness with DD-cut feature."""

    def test_wheel_with_ddcut(self, design):
        """Test wheel rim measurement with DD-cut (should be thinner than keyway)."""
        bore = BoreFeature(diameter=15.0)
        # DD-cut with 25% depth is deeper than typical keyway
        ddcut = DDCutFeature(depth=15.0 * 0.25)  # 3.75mm depth
        wheel_geo = WheelGeometry(
            params=design.wheel,
            worm_params=design.worm,
            assembly_params=design.assembly,
            bore=bore,
            ddcut=ddcut,
        )
        wheel = wheel_geo.build()

        result = measure_rim_thickness(
            wheel,
            bore_diameter_mm=15.0,
        )

        assert result.is_valid
        # DD-cut should create thinner rim than keyway
        # But still reasonable
        assert result.minimum_thickness_mm > 0.5
