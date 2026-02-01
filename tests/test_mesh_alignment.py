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
    check_interference,
    find_optimal_mesh_rotation,
    position_for_mesh,
    create_axis_markers,
    mesh_alignment_to_dict,
)


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
        )

        assert result.optimal_rotation_deg == 5.5
        assert result.interference_volume_mm3 == 0.001
        assert result.within_tolerance is True
        assert result.tooth_pitch_deg == 12.0
        assert result.worm_position == (38.14, 0.0, 0.0)
        assert result.message == "Perfect mesh"

    def test_dataclass_with_zero_interference(self):
        """Test result with zero interference (perfect mesh)."""
        result = MeshAlignmentResult(
            optimal_rotation_deg=0.0,
            interference_volume_mm3=0.0,
            within_tolerance=True,
            tooth_pitch_deg=30.0,
            worm_position=(10.0, 0.0, 0.0),
            message="Perfect mesh - no interference detected",
        )

        assert result.interference_volume_mm3 == 0.0
        assert result.within_tolerance is True

    def test_dataclass_with_high_interference(self):
        """Test result with interference exceeding tolerance."""
        result = MeshAlignmentResult(
            optimal_rotation_deg=3.2,
            interference_volume_mm3=5.5,
            within_tolerance=False,
            tooth_pitch_deg=12.0,
            worm_position=(38.14, 0.0, 0.0),
            message="Warning - interference exceeds tolerance",
        )

        assert result.interference_volume_mm3 == 5.5
        assert result.within_tolerance is False


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
        )

        d = mesh_alignment_to_dict(result)

        assert d["optimal_rotation_deg"] == 5.5
        assert d["interference_volume_mm3"] == 0.001
        assert d["within_tolerance"] is True
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
        )

        d = mesh_alignment_to_dict(result)
        json_str = json.dumps(d)

        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert parsed["optimal_rotation_deg"] == 5.5


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
            profile_shift=0.0,
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
            profile_shift=0.0,
        )

    @pytest.fixture
    def assembly_params(self, sample_design_7mm):
        """Create AssemblyParams from sample design."""
        return AssemblyParams(
            centre_distance_mm=sample_design_7mm["assembly"]["centre_distance_mm"],
            pressure_angle_deg=sample_design_7mm["assembly"]["pressure_angle_deg"],
            backlash_mm=sample_design_7mm["assembly"]["backlash_mm"],
            hand=sample_design_7mm["assembly"]["hand"],
            ratio=sample_design_7mm["assembly"]["ratio"],
        )

    @pytest.fixture
    def worm_and_wheel(self, worm_params, wheel_params, assembly_params):
        """Create worm and wheel geometry."""
        worm_geo = WormGeometry(
            params=worm_params,
            assembly_params=assembly_params,
            length=10.0,
            sections_per_turn=12,
        )
        worm = worm_geo.build()

        wheel_geo = WheelGeometry(
            params=wheel_params,
            worm_params=worm_params,
            assembly_params=assembly_params,
            face_width=5.0,
        )
        wheel = wheel_geo.build()

        return worm, wheel

    def test_find_optimal_rotation_returns_result(
        self, worm_and_wheel, assembly_params, wheel_params
    ):
        """Test that find_optimal_mesh_rotation returns a valid result."""
        worm, wheel = worm_and_wheel

        result = find_optimal_mesh_rotation(
            wheel=wheel,
            worm=worm,
            centre_distance_mm=assembly_params.centre_distance_mm,
            num_teeth=wheel_params.num_teeth,
        )

        assert isinstance(result, MeshAlignmentResult)
        assert 0 <= result.optimal_rotation_deg < result.tooth_pitch_deg
        assert result.interference_volume_mm3 >= 0.0
        assert isinstance(result.within_tolerance, bool)
        assert result.message is not None

    def test_tooth_pitch_calculation(
        self, worm_and_wheel, assembly_params, wheel_params
    ):
        """Test that tooth pitch is calculated correctly."""
        worm, wheel = worm_and_wheel

        result = find_optimal_mesh_rotation(
            wheel=wheel,
            worm=worm,
            centre_distance_mm=assembly_params.centre_distance_mm,
            num_teeth=wheel_params.num_teeth,
        )

        expected_tooth_pitch = 360.0 / wheel_params.num_teeth
        assert abs(result.tooth_pitch_deg - expected_tooth_pitch) < 0.001

    def test_worm_position_in_result(
        self, worm_and_wheel, assembly_params, wheel_params
    ):
        """Test that worm position is recorded correctly."""
        worm, wheel = worm_and_wheel

        result = find_optimal_mesh_rotation(
            wheel=wheel,
            worm=worm,
            centre_distance_mm=assembly_params.centre_distance_mm,
            num_teeth=wheel_params.num_teeth,
        )

        # Worm should be at centre_distance in Y (axis along X)
        assert result.worm_position[0] == 0.0
        assert result.worm_position[1] == assembly_params.centre_distance_mm
        assert result.worm_position[2] == 0.0

    def test_position_for_mesh_returns_parts(
        self, worm_and_wheel, assembly_params, wheel_params
    ):
        """Test that position_for_mesh returns positioned parts."""
        worm, wheel = worm_and_wheel

        # First find optimal rotation
        result = find_optimal_mesh_rotation(
            wheel=wheel,
            worm=worm,
            centre_distance_mm=assembly_params.centre_distance_mm,
            num_teeth=wheel_params.num_teeth,
        )

        # Then position for mesh
        wheel_positioned, worm_positioned = position_for_mesh(
            wheel=wheel,
            worm=worm,
            centre_distance_mm=assembly_params.centre_distance_mm,
            rotation_deg=result.optimal_rotation_deg,
        )

        assert wheel_positioned is not None
        assert worm_positioned is not None
        assert wheel_positioned.volume > 0
        assert worm_positioned.volume > 0

    def test_positioned_worm_offset_correct(
        self, worm_and_wheel, assembly_params, wheel_params
    ):
        """Test that positioned worm is at correct centre distance."""
        worm, wheel = worm_and_wheel

        wheel_positioned, worm_positioned = position_for_mesh(
            wheel=wheel,
            worm=worm,
            centre_distance_mm=assembly_params.centre_distance_mm,
            rotation_deg=0.0,
        )

        # Worm bounding box centre should be at centre_distance in Y (axis along X)
        worm_bbox = worm_positioned.bounding_box()
        worm_center_y = (worm_bbox.max.Y + worm_bbox.min.Y) / 2
        assert abs(worm_center_y - assembly_params.centre_distance_mm) < 1.0

    def test_check_interference_returns_volume(
        self, worm_and_wheel, assembly_params
    ):
        """Test that check_interference returns a numeric volume."""
        worm, wheel = worm_and_wheel

        interference = check_interference(
            wheel=wheel,
            worm=worm,
            centre_distance_mm=assembly_params.centre_distance_mm,
            rotation_deg=0.0,
        )

        assert isinstance(interference, float)
        assert interference >= 0.0


class TestCalculateMeshRotation:
    """Tests for calculate_mesh_rotation function."""

    @pytest.fixture
    def simple_gear_pair(self, sample_design_7mm):
        """Create a simple worm/wheel pair for rotation tests."""
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
            profile_shift=0.0,
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
            profile_shift=0.0,
        )
        assembly_params = AssemblyParams(
            centre_distance_mm=sample_design_7mm["assembly"]["centre_distance_mm"],
            pressure_angle_deg=sample_design_7mm["assembly"]["pressure_angle_deg"],
            backlash_mm=sample_design_7mm["assembly"]["backlash_mm"],
            hand=sample_design_7mm["assembly"]["hand"],
            ratio=sample_design_7mm["assembly"]["ratio"],
        )

        worm_geo = WormGeometry(
            params=worm_params,
            assembly_params=assembly_params,
            length=10.0,
            sections_per_turn=12,
        )
        worm = worm_geo.build()

        wheel_geo = WheelGeometry(
            params=wheel_params,
            worm_params=worm_params,
            assembly_params=assembly_params,
            face_width=5.0,
        )
        wheel = wheel_geo.build()

        # Position worm at centre distance for testing
        from build123d import Pos, Rot

        worm_positioned = Pos(assembly_params.centre_distance_mm, 0, 0) * Rot(X=90) * worm

        return wheel, worm_positioned, wheel_params.num_teeth

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

    @pytest.fixture
    def large_gear_pair(self, sample_design_large):
        """Create a larger worm/wheel pair."""
        module_mm = sample_design_large["worm"]["module_mm"]
        worm_params = WormParams(
            module_mm=module_mm,
            num_starts=sample_design_large["worm"]["num_starts"],
            pitch_diameter_mm=sample_design_large["worm"]["pitch_diameter_mm"],
            tip_diameter_mm=sample_design_large["worm"]["tip_diameter_mm"],
            root_diameter_mm=sample_design_large["worm"]["root_diameter_mm"],
            lead_mm=sample_design_large["worm"]["lead_mm"],
            axial_pitch_mm=sample_design_large["worm"]["axial_pitch_mm"],
            lead_angle_deg=sample_design_large["worm"]["lead_angle_deg"],
            addendum_mm=sample_design_large["worm"]["addendum_mm"],
            dedendum_mm=sample_design_large["worm"]["dedendum_mm"],
            thread_thickness_mm=sample_design_large["worm"]["thread_thickness_mm"],
            hand="right",
            profile_shift=0.0,
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
            profile_shift=0.0,
        )
        assembly_params = AssemblyParams(
            centre_distance_mm=sample_design_large["assembly"]["centre_distance_mm"],
            pressure_angle_deg=sample_design_large["assembly"]["pressure_angle_deg"],
            backlash_mm=sample_design_large["assembly"]["backlash_mm"],
            hand=sample_design_large["assembly"]["hand"],
            ratio=sample_design_large["assembly"]["ratio"],
        )

        worm_geo = WormGeometry(
            params=worm_params,
            assembly_params=assembly_params,
            length=30.0,
            sections_per_turn=12,
        )
        worm = worm_geo.build()

        wheel_geo = WheelGeometry(
            params=wheel_params,
            worm_params=worm_params,
            assembly_params=assembly_params,
            face_width=15.0,
        )
        wheel = wheel_geo.build()

        return worm, wheel, wheel_params, assembly_params

    def test_large_gear_alignment(self, large_gear_pair):
        """Test mesh alignment with larger gears."""
        worm, wheel, wheel_params, assembly_params = large_gear_pair

        result = find_optimal_mesh_rotation(
            wheel=wheel,
            worm=worm,
            centre_distance_mm=assembly_params.centre_distance_mm,
            num_teeth=wheel_params.num_teeth,
        )

        assert isinstance(result, MeshAlignmentResult)
        assert result.tooth_pitch_deg == 360.0 / wheel_params.num_teeth

    def test_large_gear_position_for_mesh(self, large_gear_pair):
        """Test positioning larger gears for mesh."""
        worm, wheel, wheel_params, assembly_params = large_gear_pair

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
