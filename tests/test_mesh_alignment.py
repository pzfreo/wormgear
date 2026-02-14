"""
Tests for mesh alignment module.

Tests the mesh alignment functionality for optimal wheel rotation
to achieve proper meshing with a worm.
"""

import math
import pytest

from wormgear import (
    WormParams,
    WheelParams,
    AssemblyParams,
    WormGeometry,
    WheelGeometry,
)
from wormgear.core.mesh_alignment import (
    MeshAlignmentResult,
    calculate_mesh_rotation,
    calculate_tolerance_mm3,
    _classify_mesh_quality,
    check_interference,
    find_optimal_mesh_rotation,
    position_for_mesh,
    create_axis_markers,
    mesh_alignment_to_dict,
)

pytestmark = pytest.mark.slow


class TestMeshAlignmentResult:
    """Tests for MeshAlignmentResult dataclass."""

    def test_dataclass_creation(self):
        """Test creating MeshAlignmentResult with valid data."""
        result = MeshAlignmentResult(
            optimal_rotation_deg=5.5,
            interference_volume_mm3=0.001,
            within_tolerance=True,
            tooth_pitch_deg=12.0,
            worm_position=(38.14, 0.0, 0.0),
            message="Perfect mesh",
            mesh_quality="perfect",
            tolerance_mm3=4.0,
        )

        assert result.optimal_rotation_deg == 5.5
        assert result.interference_volume_mm3 == 0.001
        assert result.within_tolerance is True
        assert result.tooth_pitch_deg == 12.0
        assert result.worm_position == (38.14, 0.0, 0.0)
        assert result.message == "Perfect mesh"
        assert result.mesh_quality == "perfect"
        assert result.tolerance_mm3 == 4.0

    def test_dataclass_defaults(self):
        """Test that new fields have sensible defaults."""
        result = MeshAlignmentResult(
            optimal_rotation_deg=0.0,
            interference_volume_mm3=0.0,
            within_tolerance=True,
            tooth_pitch_deg=12.0,
            worm_position=(0.0, 0.0, 0.0),
            message="test",
        )

        assert result.mesh_quality == "good"
        assert result.tolerance_mm3 == 1.0

    def test_dataclass_with_zero_interference(self):
        """Test result with zero interference (perfect mesh)."""
        result = MeshAlignmentResult(
            optimal_rotation_deg=0.0,
            interference_volume_mm3=0.0,
            within_tolerance=True,
            tooth_pitch_deg=30.0,
            worm_position=(10.0, 0.0, 0.0),
            message="Perfect mesh - no interference detected",
            mesh_quality="perfect",
        )

        assert result.interference_volume_mm3 == 0.0
        assert result.within_tolerance is True
        assert result.mesh_quality == "perfect"

    def test_dataclass_with_high_interference(self):
        """Test result with interference exceeding tolerance."""
        result = MeshAlignmentResult(
            optimal_rotation_deg=3.2,
            interference_volume_mm3=5.5,
            within_tolerance=False,
            tooth_pitch_deg=12.0,
            worm_position=(38.14, 0.0, 0.0),
            message="Warning - interference exceeds tolerance",
            mesh_quality="warning",
        )

        assert result.interference_volume_mm3 == 5.5
        assert result.within_tolerance is False
        assert result.mesh_quality == "warning"


class TestMeshAlignmentToDict:
    """Tests for mesh_alignment_to_dict conversion."""

    def test_conversion_to_dict(self):
        """Test converting MeshAlignmentResult to dictionary."""
        result = MeshAlignmentResult(
            optimal_rotation_deg=5.5,
            interference_volume_mm3=0.001,
            within_tolerance=True,
            tooth_pitch_deg=12.0,
            worm_position=(38.14, 0.0, 0.0),
            message="Good mesh",
            mesh_quality="good",
            tolerance_mm3=4.0,
        )

        d = mesh_alignment_to_dict(result)

        assert d["optimal_rotation_deg"] == 5.5
        assert d["interference_volume_mm3"] == 0.001
        assert d["within_tolerance"] is True
        assert d["mesh_quality"] == "good"
        assert d["tolerance_mm3"] == 4.0
        assert d["tooth_pitch_deg"] == 12.0
        assert d["worm_position"]["x_mm"] == 38.14
        assert d["worm_position"]["y_mm"] == 0.0
        assert d["worm_position"]["z_mm"] == 0.0
        assert d["message"] == "Good mesh"

    def test_dict_is_json_serializable(self):
        """Test that the output dictionary can be serialized to JSON."""
        import json

        result = MeshAlignmentResult(
            optimal_rotation_deg=5.5,
            interference_volume_mm3=0.001,
            within_tolerance=True,
            tooth_pitch_deg=12.0,
            worm_position=(38.14, 0.0, 0.0),
            message="Good mesh",
            mesh_quality="good",
            tolerance_mm3=4.0,
        )

        d = mesh_alignment_to_dict(result)
        json_str = json.dumps(d)

        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert parsed["optimal_rotation_deg"] == 5.5
        assert parsed["mesh_quality"] == "good"
        assert parsed["tolerance_mm3"] == 4.0


class TestCalculateToleranceMm3:
    """Tests for module-scaled tolerance calculation."""

    def test_module_1_gives_base_tolerance(self):
        """Module 1 should give the base tolerance of 1.0 mm³."""
        assert calculate_tolerance_mm3(1.0) == 1.0

    def test_module_2_scales_quadratically(self):
        """Module 2 should give 4.0 mm³ (2² × 1.0)."""
        assert calculate_tolerance_mm3(2.0) == 4.0

    def test_module_5_scales_quadratically(self):
        """Module 5 should give 25.0 mm³ (5² × 1.0)."""
        assert calculate_tolerance_mm3(5.0) == 25.0

    def test_custom_base_tolerance(self):
        """Custom base tolerance should scale correctly."""
        assert calculate_tolerance_mm3(2.0, base_tolerance=0.5) == 2.0

    def test_small_module(self):
        """Sub-1.0 modules should give smaller tolerances."""
        assert calculate_tolerance_mm3(0.5) == 0.25


class TestClassifyMeshQuality:
    """Tests for mesh quality tier classification."""

    def test_perfect_at_zero(self):
        """Zero interference should classify as perfect."""
        quality, msg = _classify_mesh_quality(0.0, 4.0)
        assert quality == "perfect"
        assert "Perfect" in msg

    def test_good_within_tolerance(self):
        """Interference within tolerance should classify as good."""
        quality, msg = _classify_mesh_quality(2.0, 4.0)
        assert quality == "good"
        assert "Good" in msg

    def test_good_at_tolerance_boundary(self):
        """Interference exactly at tolerance should classify as good."""
        quality, msg = _classify_mesh_quality(4.0, 4.0)
        assert quality == "good"

    def test_acceptable_within_3x_tolerance(self):
        """Interference within 3× tolerance should classify as acceptable."""
        quality, msg = _classify_mesh_quality(8.0, 4.0)
        assert quality == "acceptable"
        assert "Acceptable" in msg
        assert "helical" in msg

    def test_acceptable_at_3x_boundary(self):
        """Interference exactly at 3× tolerance should classify as acceptable."""
        quality, msg = _classify_mesh_quality(12.0, 4.0)
        assert quality == "acceptable"

    def test_warning_above_3x_tolerance(self):
        """Interference above 3× tolerance should classify as warning."""
        quality, msg = _classify_mesh_quality(13.0, 4.0)
        assert quality == "warning"
        assert "Warning" in msg

    def test_within_tolerance_for_module_2_at_3_57(self):
        """3.57 mm³ at module 2 (tolerance 4.0) should be 'good' not 'warning'."""
        tolerance = calculate_tolerance_mm3(2.0)
        quality, _ = _classify_mesh_quality(3.57, tolerance)
        assert quality == "good"


class TestAxisMarkers:
    """Tests for create_axis_markers function."""

    def test_creates_wheel_and_worm_markers(self):
        """Test that axis markers are created for both axes."""
        markers = create_axis_markers(
            centre_distance_mm=40.0,
            worm_length_mm=30.0,
            wheel_height_mm=20.0,
            marker_radius_mm=0.5,
        )

        assert "wheel_axis" in markers
        assert "worm_axis" in markers
        assert markers["wheel_axis"] is not None
        assert markers["worm_axis"] is not None

    def test_marker_geometry_is_valid(self):
        """Test that axis marker geometry is valid."""
        markers = create_axis_markers(centre_distance_mm=40.0)

        # Both should be valid solids with positive volume
        assert markers["wheel_axis"].volume > 0
        assert markers["worm_axis"].volume > 0
        assert markers["wheel_axis"].is_valid
        assert markers["worm_axis"].is_valid

    def test_marker_positions(self):
        """Test that markers are positioned correctly."""
        centre_distance = 50.0
        markers = create_axis_markers(centre_distance_mm=centre_distance)

        # Wheel axis should be at origin
        wheel_bbox = markers["wheel_axis"].bounding_box()
        wheel_center_x = (wheel_bbox.max.X + wheel_bbox.min.X) / 2
        wheel_center_y = (wheel_bbox.max.Y + wheel_bbox.min.Y) / 2
        assert abs(wheel_center_x) < 1.0
        assert abs(wheel_center_y) < 1.0

        # Worm axis should be offset by centre_distance in Y (axis along X)
        worm_bbox = markers["worm_axis"].bounding_box()
        worm_center_y = (worm_bbox.max.Y + worm_bbox.min.Y) / 2
        assert abs(worm_center_y - centre_distance) < 1.0


class TestMeshAlignmentIntegration:
    """Integration tests using actual worm and wheel geometry."""

    def test_find_optimal_rotation_returns_result(
        self, built_worm_and_wheel_7mm, assembly_params_7mm, wheel_params_7mm
    ):
        """Test that find_optimal_mesh_rotation returns a valid result."""
        worm, wheel = built_worm_and_wheel_7mm

        result = find_optimal_mesh_rotation(
            wheel=wheel,
            worm=worm,
            centre_distance_mm=assembly_params_7mm.centre_distance_mm,
            num_teeth=wheel_params_7mm.num_teeth,
            module_mm=wheel_params_7mm.module_mm,
        )

        assert isinstance(result, MeshAlignmentResult)
        assert 0 <= result.optimal_rotation_deg < result.tooth_pitch_deg
        assert result.interference_volume_mm3 >= 0.0
        assert isinstance(result.within_tolerance, bool)
        assert result.message is not None
        assert result.mesh_quality in ("perfect", "good", "acceptable", "warning")
        assert result.tolerance_mm3 > 0.0

    def test_tooth_pitch_calculation(
        self, built_worm_and_wheel_7mm, assembly_params_7mm, wheel_params_7mm
    ):
        """Test that tooth pitch is calculated correctly."""
        worm, wheel = built_worm_and_wheel_7mm

        result = find_optimal_mesh_rotation(
            wheel=wheel,
            worm=worm,
            centre_distance_mm=assembly_params_7mm.centre_distance_mm,
            num_teeth=wheel_params_7mm.num_teeth,
        )

        expected_tooth_pitch = 360.0 / wheel_params_7mm.num_teeth
        assert abs(result.tooth_pitch_deg - expected_tooth_pitch) < 0.001

    def test_worm_position_in_result(
        self, built_worm_and_wheel_7mm, assembly_params_7mm, wheel_params_7mm
    ):
        """Test that worm position is recorded correctly."""
        worm, wheel = built_worm_and_wheel_7mm

        result = find_optimal_mesh_rotation(
            wheel=wheel,
            worm=worm,
            centre_distance_mm=assembly_params_7mm.centre_distance_mm,
            num_teeth=wheel_params_7mm.num_teeth,
        )

        # Worm should be at centre_distance in Y (axis along X)
        assert result.worm_position[0] == 0.0
        assert result.worm_position[1] == assembly_params_7mm.centre_distance_mm
        assert result.worm_position[2] == 0.0

    def test_position_for_mesh_returns_parts(
        self, built_worm_and_wheel_7mm, assembly_params_7mm, wheel_params_7mm
    ):
        """Test that position_for_mesh returns positioned parts."""
        worm, wheel = built_worm_and_wheel_7mm

        # First find optimal rotation
        result = find_optimal_mesh_rotation(
            wheel=wheel,
            worm=worm,
            centre_distance_mm=assembly_params_7mm.centre_distance_mm,
            num_teeth=wheel_params_7mm.num_teeth,
        )

        # Then position for mesh
        wheel_positioned, worm_positioned = position_for_mesh(
            wheel=wheel,
            worm=worm,
            centre_distance_mm=assembly_params_7mm.centre_distance_mm,
            rotation_deg=result.optimal_rotation_deg,
        )

        assert wheel_positioned is not None
        assert worm_positioned is not None
        assert wheel_positioned.volume > 0
        assert worm_positioned.volume > 0

    def test_positioned_worm_offset_correct(
        self, built_worm_and_wheel_7mm, assembly_params_7mm
    ):
        """Test that positioned worm is at correct centre distance."""
        worm, wheel = built_worm_and_wheel_7mm

        wheel_positioned, worm_positioned = position_for_mesh(
            wheel=wheel,
            worm=worm,
            centre_distance_mm=assembly_params_7mm.centre_distance_mm,
            rotation_deg=0.0,
        )

        # Worm bounding box centre should be at centre_distance in Y (axis along X)
        worm_bbox = worm_positioned.bounding_box()
        worm_center_y = (worm_bbox.max.Y + worm_bbox.min.Y) / 2
        assert abs(worm_center_y - assembly_params_7mm.centre_distance_mm) < 1.0

    def test_check_interference_returns_volume(
        self, built_worm_and_wheel_7mm, assembly_params_7mm
    ):
        """Test that check_interference returns a numeric volume."""
        worm, wheel = built_worm_and_wheel_7mm

        interference = check_interference(
            wheel=wheel,
            worm=worm,
            centre_distance_mm=assembly_params_7mm.centre_distance_mm,
            rotation_deg=0.0,
        )

        assert isinstance(interference, float)
        assert interference >= 0.0


class TestCalculateMeshRotation:
    """Tests for calculate_mesh_rotation function."""

    @pytest.fixture(scope="module")
    def simple_gear_pair(self, built_worm_and_wheel_7mm, assembly_params_7mm, wheel_params_7mm):
        """Create a positioned worm/wheel pair for rotation tests."""
        worm, wheel = built_worm_and_wheel_7mm

        # Position worm at centre distance for testing
        from build123d import Pos, Rot

        worm_positioned = Pos(assembly_params_7mm.centre_distance_mm, 0, 0) * Rot(X=90) * worm

        return wheel, worm_positioned, wheel_params_7mm.num_teeth

    def test_rotation_within_tooth_pitch(self, simple_gear_pair):
        """Test that optimal rotation is within one tooth pitch."""
        wheel, worm, num_teeth = simple_gear_pair
        tooth_pitch = 360.0 / num_teeth

        rotation, interference = calculate_mesh_rotation(
            wheel=wheel,
            worm=worm,
            num_teeth=num_teeth,
        )

        assert 0 <= rotation < tooth_pitch

    def test_returns_non_negative_interference(self, simple_gear_pair):
        """Test that returned interference is non-negative."""
        wheel, worm, num_teeth = simple_gear_pair

        rotation, interference = calculate_mesh_rotation(
            wheel=wheel,
            worm=worm,
            num_teeth=num_teeth,
        )

        assert interference >= 0.0

    def test_custom_tolerance(self, simple_gear_pair):
        """Test with custom tolerance for golden section search."""
        wheel, worm, num_teeth = simple_gear_pair

        # Use larger tolerance for faster test
        rotation, interference = calculate_mesh_rotation(
            wheel=wheel,
            worm=worm,
            num_teeth=num_teeth,
            tolerance_deg=1.0,
        )

        tooth_pitch = 360.0 / num_teeth
        assert 0 <= rotation < tooth_pitch
        assert interference >= 0.0


class TestLargerGearMeshAlignment:
    """Tests with larger gear design to ensure algorithm scales."""

    def test_large_gear_alignment(self, built_worm_large, built_wheel_large, wheel_params_large, assembly_params_large):
        """Test mesh alignment with larger gears."""
        worm, wheel = built_worm_large, built_wheel_large
        wheel_params, assembly_params = wheel_params_large, assembly_params_large

        result = find_optimal_mesh_rotation(
            wheel=wheel,
            worm=worm,
            centre_distance_mm=assembly_params.centre_distance_mm,
            num_teeth=wheel_params.num_teeth,
        )

        assert isinstance(result, MeshAlignmentResult)
        assert result.tooth_pitch_deg == 360.0 / wheel_params.num_teeth

    def test_large_gear_position_for_mesh(self, built_worm_large, built_wheel_large, wheel_params_large, assembly_params_large):
        """Test positioning larger gears for mesh."""
        worm, wheel = built_worm_large, built_wheel_large
        wheel_params, assembly_params = wheel_params_large, assembly_params_large

        result = find_optimal_mesh_rotation(
            wheel=wheel,
            worm=worm,
            centre_distance_mm=assembly_params.centre_distance_mm,
            num_teeth=wheel_params.num_teeth,
        )

        wheel_positioned, worm_positioned = position_for_mesh(
            wheel=wheel,
            worm=worm,
            centre_distance_mm=assembly_params.centre_distance_mm,
            rotation_deg=result.optimal_rotation_deg,
        )

        # Both should remain valid solids
        assert wheel_positioned.is_valid
        assert worm_positioned.is_valid
