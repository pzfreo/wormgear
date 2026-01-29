"""
Tests for globoid (double-enveloping) worm geometry generation.
"""

import math
import pytest

from wormgear import (
    load_design_json, WormParams, AssemblyParams,
    GloboidWormGeometry,
    BoreFeature, KeywayFeature, SetScrewFeature,
)


class TestGloboidWormGeometry:
    """Tests for GloboidWormGeometry class."""

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

    @pytest.fixture
    def wheel_pitch_diameter(self, sample_design_7mm):
        """Get wheel pitch diameter from sample design."""
        return sample_design_7mm["wheel"]["pitch_diameter_mm"]

    def test_globoid_worm_geometry_creation(self, worm_params, assembly_params, wheel_pitch_diameter):
        """Test creating a GloboidWormGeometry instance."""
        globoid_geo = GloboidWormGeometry(
            params=worm_params,
            assembly_params=assembly_params,
            wheel_pitch_diameter=wheel_pitch_diameter,
            length=20.0,
            sections_per_turn=36
        )

        assert globoid_geo.params == worm_params
        assert globoid_geo.length == 20.0
        assert globoid_geo.sections_per_turn == 36
        assert globoid_geo.wheel_pitch_radius == wheel_pitch_diameter / 2

    def test_globoid_hourglass_parameters(self, worm_params, assembly_params, wheel_pitch_diameter):
        """Test that hourglass parameters are calculated correctly using geometry-based formula."""
        globoid_geo = GloboidWormGeometry(
            params=worm_params,
            assembly_params=assembly_params,
            wheel_pitch_diameter=wheel_pitch_diameter,
            length=20.0
        )

        pitch_radius = worm_params.pitch_diameter_mm / 2
        center_distance = assembly_params.centre_distance_mm
        wheel_pitch_radius = wheel_pitch_diameter / 2

        # Throat radius should be: center_distance - wheel_pitch_radius (geometry-based)
        expected_throat_radius = center_distance - wheel_pitch_radius
        assert globoid_geo.throat_pitch_radius == pytest.approx(expected_throat_radius, rel=0.01)
        assert globoid_geo.nominal_pitch_radius == pytest.approx(pitch_radius, rel=0.01)

        # Curvature radius should match wheel pitch radius
        assert globoid_geo.throat_curvature_radius == pytest.approx(wheel_pitch_radius, rel=0.01)

    def test_globoid_auto_length_calculation(self, worm_params, assembly_params, wheel_pitch_diameter):
        """Test auto-calculation of worm length when not specified."""
        globoid_geo = GloboidWormGeometry(
            params=worm_params,
            assembly_params=assembly_params,
            wheel_pitch_diameter=wheel_pitch_diameter
        )

        # Auto length should be ~1.3× pitch diameter
        expected_length = worm_params.pitch_diameter_mm * 1.3
        assert globoid_geo.length == pytest.approx(expected_length, rel=0.01)

    def test_globoid_custom_length(self, worm_params, assembly_params, wheel_pitch_diameter):
        """Test specifying custom worm length."""
        custom_length = 12.0
        globoid_geo = GloboidWormGeometry(
            params=worm_params,
            assembly_params=assembly_params,
            wheel_pitch_diameter=wheel_pitch_diameter,
            length=custom_length
        )

        assert globoid_geo.length == custom_length

    def test_globoid_build_returns_solid(self, worm_params, assembly_params, wheel_pitch_diameter):
        """Test that build() returns a valid solid."""
        globoid_geo = GloboidWormGeometry(
            params=worm_params,
            assembly_params=assembly_params,
            wheel_pitch_diameter=wheel_pitch_diameter,
            length=10.0,
            sections_per_turn=12
        )
        globoid = globoid_geo.build()

        # Should return a solid with positive volume
        assert globoid is not None
        assert hasattr(globoid, 'volume')
        assert globoid.volume > 0

    def test_globoid_volume_reasonable(self, worm_params, assembly_params, wheel_pitch_diameter):
        """Test that globoid volume is within reasonable bounds."""
        length = 10.0
        globoid_geo = GloboidWormGeometry(
            params=worm_params,
            assembly_params=assembly_params,
            wheel_pitch_diameter=wheel_pitch_diameter,
            length=length,
            sections_per_turn=12
        )
        globoid = globoid_geo.build()

        # Volume should be between core cylinder and tip cylinder
        # Use throat radius for minimum (narrowest point)
        throat_radius = worm_params.pitch_diameter_mm / 2 * 0.90
        tip_radius = worm_params.tip_diameter_mm / 2

        min_volume = math.pi * throat_radius**2 * length
        max_volume = math.pi * tip_radius**2 * length

        assert globoid.volume > min_volume * 0.8  # Allow tolerance for hourglass shape
        assert globoid.volume < max_volume * 1.1

    def test_globoid_different_lengths(self, worm_params, assembly_params, wheel_pitch_diameter):
        """Test globoid generation with different lengths."""
        for length in [5.0, 10.0, 15.0, 20.0]:
            globoid_geo = GloboidWormGeometry(
                params=worm_params,
                assembly_params=assembly_params,
                wheel_pitch_diameter=wheel_pitch_diameter,
                length=length,
                sections_per_turn=12
            )
            globoid = globoid_geo.build()

            assert globoid is not None
            assert globoid.volume > 0, f"Globoid with length {length} has zero volume"

    def test_globoid_helix_points_generation(self, worm_params, assembly_params, wheel_pitch_diameter):
        """Test that varying-radius helix points are generated correctly."""
        globoid_geo = GloboidWormGeometry(
            params=worm_params,
            assembly_params=assembly_params,
            wheel_pitch_diameter=wheel_pitch_diameter,
            length=12.0
        )

        # Generate helix points
        points = globoid_geo._generate_globoid_helix_points(start_angle=0)

        # Should have points
        assert len(points) > 0

        # Points should span the extended_length (length + 2*lead for tapering)
        z_values = [p.Z for p in points]
        z_range = max(z_values) - min(z_values)
        expected_extended_length = 12.0 + 2 * worm_params.lead_mm
        assert z_range == pytest.approx(expected_extended_length, rel=0.01)

        # Radii should vary (hourglass shape)
        radii = [math.sqrt(p.X**2 + p.Y**2) for p in points]
        assert min(radii) < max(radii), "Hourglass should have varying radius"

        # Center should be narrower than ends
        center_idx = len(points) // 2
        center_radius = radii[center_idx]
        end_radius = radii[0]
        assert center_radius < end_radius, "Center should be narrower than ends"

    def test_globoid_multi_start(self, assembly_params, wheel_pitch_diameter):
        """Test globoid worm with multiple starts."""
        params = WormParams(
            module_mm=2.0,
            num_starts=2,
            pitch_diameter_mm=20.0,
            tip_diameter_mm=24.0,
            root_diameter_mm=15.0,
            lead_mm=12.566,
            axial_pitch_mm=2.0 * math.pi,
            lead_angle_deg=17.66,
            addendum_mm=2.0,
            dedendum_mm=2.5,
            thread_thickness_mm=2.74,
            hand="right",
            profile_shift=0.0
        )

        globoid_geo = GloboidWormGeometry(
            params=params,
            assembly_params=assembly_params,
            wheel_pitch_diameter=wheel_pitch_diameter,
            length=20.0,
            sections_per_turn=12
        )
        globoid = globoid_geo.build()

        assert globoid is not None
        assert globoid.volume > 0

    def test_globoid_left_hand(self, sample_design_left_hand):
        """Test left-hand globoid worm generation."""
        module_mm = sample_design_left_hand["worm"]["module_mm"]
        worm_params = WormParams(
            module_mm=module_mm,
            num_starts=sample_design_left_hand["worm"]["num_starts"],
            pitch_diameter_mm=sample_design_left_hand["worm"]["pitch_diameter_mm"],
            tip_diameter_mm=sample_design_left_hand["worm"]["tip_diameter_mm"],
            root_diameter_mm=sample_design_left_hand["worm"]["root_diameter_mm"],
            lead_mm=sample_design_left_hand["worm"]["lead_mm"],
            axial_pitch_mm=module_mm * math.pi,
            lead_angle_deg=sample_design_left_hand["worm"]["lead_angle_deg"],
            addendum_mm=sample_design_left_hand["worm"]["addendum_mm"],
            dedendum_mm=sample_design_left_hand["worm"]["dedendum_mm"],
            thread_thickness_mm=sample_design_left_hand["worm"]["thread_thickness_mm"],
            hand="left",
            profile_shift=0.0
        )
        assembly_params = AssemblyParams(
            centre_distance_mm=sample_design_left_hand["assembly"]["centre_distance_mm"],
            pressure_angle_deg=sample_design_left_hand["assembly"]["pressure_angle_deg"],
            backlash_mm=sample_design_left_hand["assembly"]["backlash_mm"],
            hand="left",
            ratio=sample_design_left_hand["assembly"]["ratio"]
        )
        wheel_pitch_diameter = sample_design_left_hand["wheel"]["pitch_diameter_mm"]

        globoid_geo = GloboidWormGeometry(
            params=worm_params,
            assembly_params=assembly_params,
            wheel_pitch_diameter=wheel_pitch_diameter,
            length=15.0,
            sections_per_turn=12
        )
        globoid = globoid_geo.build()

        assert globoid is not None
        assert globoid.volume > 0

    def test_globoid_thread_tapering(self, worm_params, assembly_params, wheel_pitch_diameter):
        """Test that thread ends are tapered smoothly."""
        # This is tested indirectly - if tapering is broken, lofting fails or creates invalid geometry
        globoid_geo = GloboidWormGeometry(
            params=worm_params,
            assembly_params=assembly_params,
            wheel_pitch_diameter=wheel_pitch_diameter,
            length=12.0,
            sections_per_turn=24
        )
        globoid = globoid_geo.build()

        assert globoid is not None
        assert globoid.volume > 0
        assert globoid.is_valid

    def test_globoid_is_watertight(self, worm_params, assembly_params, wheel_pitch_diameter):
        """Test that the globoid geometry is watertight (valid solid)."""
        globoid_geo = GloboidWormGeometry(
            params=worm_params,
            assembly_params=assembly_params,
            wheel_pitch_diameter=wheel_pitch_diameter,
            length=10.0,
            sections_per_turn=12
        )
        globoid = globoid_geo.build()

        # A watertight solid should have is_valid() return True
        assert globoid.is_valid

    def test_globoid_bounding_box_reasonable(self, worm_params, assembly_params, wheel_pitch_diameter):
        """Test that globoid bounding box matches expected dimensions."""
        length = 15.0
        globoid_geo = GloboidWormGeometry(
            params=worm_params,
            assembly_params=assembly_params,
            wheel_pitch_diameter=wheel_pitch_diameter,
            length=length,
            sections_per_turn=12
        )
        globoid = globoid_geo.build()

        bbox = globoid.bounding_box()
        tip_diameter = worm_params.tip_diameter_mm

        # X and Y extents should be approximately tip diameter
        x_extent = bbox.max.X - bbox.min.X
        y_extent = bbox.max.Y - bbox.min.Y
        z_extent = bbox.max.Z - bbox.min.Z

        assert abs(x_extent - tip_diameter) < 1.0
        assert abs(y_extent - tip_diameter) < 1.0
        assert abs(z_extent - length) < 1.0

    def test_globoid_with_bore(self, worm_params, assembly_params, wheel_pitch_diameter):
        """Test globoid worm with bore feature."""
        bore = BoreFeature(diameter=4.0)
        globoid_geo = GloboidWormGeometry(
            params=worm_params,
            assembly_params=assembly_params,
            wheel_pitch_diameter=wheel_pitch_diameter,
            length=10.0,
            sections_per_turn=12,
            bore=bore
        )
        globoid = globoid_geo.build()

        # Handle potential ShapeList result
        from build123d import ShapeList
        if isinstance(globoid, ShapeList):
            solids = list(globoid.solids())
            if len(solids) > 0:
                globoid = solids[0]

        assert globoid is not None
        assert globoid.volume > 0
        assert globoid.is_valid

        # Volume should be less than solid version due to bore
        globoid_solid = GloboidWormGeometry(
            params=worm_params,
            assembly_params=assembly_params,
            wheel_pitch_diameter=wheel_pitch_diameter,
            length=10.0,
            sections_per_turn=12
        ).build()

        assert globoid.volume < globoid_solid.volume

    def test_globoid_with_keyway(self, worm_params, assembly_params, wheel_pitch_diameter):
        """Test globoid worm with bore and keyway features."""
        # Use a bore that fits within the root diameter (4.75mm for this fixture)
        # DIN 6885 doesn't cover bores below 6mm, so specify custom dimensions
        bore = BoreFeature(diameter=2.0)
        keyway = KeywayFeature(width=1.0, depth=0.5)  # Custom dimensions for small bore

        globoid_geo = GloboidWormGeometry(
            params=worm_params,
            assembly_params=assembly_params,
            wheel_pitch_diameter=wheel_pitch_diameter,
            length=10.0,
            sections_per_turn=12,
            bore=bore,
            keyway=keyway
        )

        # Just verify that build completes without error
        # (Keyway on small parts may create complex geometry)
        try:
            globoid = globoid_geo.build()
            assert globoid is not None
        except Exception as e:
            pytest.fail(f"Failed to build globoid with keyway: {e}")

    def test_globoid_with_set_screw(self, worm_params, assembly_params, wheel_pitch_diameter):
        """Test globoid worm with set screw feature."""
        # Use a bore that fits within the root diameter (4.75mm for this fixture)
        bore = BoreFeature(diameter=2.0)
        set_screw = SetScrewFeature(count=2)

        globoid_geo = GloboidWormGeometry(
            params=worm_params,
            assembly_params=assembly_params,
            wheel_pitch_diameter=wheel_pitch_diameter,
            length=12.0,
            sections_per_turn=12,
            bore=bore,
            set_screw=set_screw
        )

        # Just verify that build completes without error
        # (Set screws on small parts may create complex geometry)
        try:
            globoid = globoid_geo.build()
            assert globoid is not None
        except Exception as e:
            pytest.fail(f"Failed to build globoid with set screw: {e}")

    def test_globoid_sections_per_turn_affects_smoothness(self, worm_params, assembly_params, wheel_pitch_diameter):
        """Test that more sections per turn doesn't break geometry."""
        for sections in [12, 24, 36, 72]:
            globoid_geo = GloboidWormGeometry(
                params=worm_params,
                assembly_params=assembly_params,
                wheel_pitch_diameter=wheel_pitch_diameter,
                length=10.0,
                sections_per_turn=sections
            )
            globoid = globoid_geo.build()

            assert globoid is not None
            assert globoid.volume > 0, f"Globoid with {sections} sections has zero volume"


class TestGloboidWormFromJsonFile:
    """Tests using actual JSON files."""

    def test_build_globoid_from_7mm_json(self, examples_dir):
        """Test building globoid worm from 7mm.json example file."""
        example_file = examples_dir / "7mm.json"
        if not example_file.exists():
            pytest.skip("Example file not found")

        design = load_design_json(example_file)
        globoid_geo = GloboidWormGeometry(
            params=design.worm,
            assembly_params=design.assembly,
            wheel_pitch_diameter=design.wheel.pitch_diameter_mm,
            length=12.0,
            sections_per_turn=12
        )
        globoid = globoid_geo.build()

        assert globoid is not None
        assert globoid.volume > 0
        assert globoid.is_valid

    def test_globoid_export_step(self, examples_dir, tmp_path):
        """Test exporting globoid worm to STEP file."""
        example_file = examples_dir / "7mm.json"
        if not example_file.exists():
            pytest.skip("Example file not found")

        design = load_design_json(example_file)
        globoid_geo = GloboidWormGeometry(
            params=design.worm,
            assembly_params=design.assembly,
            wheel_pitch_diameter=design.wheel.pitch_diameter_mm,
            length=12.0,
            sections_per_turn=12
        )
        globoid = globoid_geo.build()

        # Export to temp file
        output_file = tmp_path / "test_globoid.step"
        globoid_geo.export_step(str(output_file))

        # Verify file was created and has content
        assert output_file.exists()
        assert output_file.stat().st_size > 1000  # Should be reasonably sized


class TestGloboidWormProfileTypes:
    """Tests for DIN 3975 profile types (ZA/ZK) on globoid worm."""

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

    @pytest.fixture
    def wheel_pitch_diameter(self, sample_design_7mm):
        """Get wheel pitch diameter from sample design."""
        return sample_design_7mm["wheel"]["pitch_diameter_mm"]

    def test_globoid_profile_za_default(self, worm_params, assembly_params, wheel_pitch_diameter):
        """Test that ZA profile is the default."""
        globoid_geo = GloboidWormGeometry(
            params=worm_params,
            assembly_params=assembly_params,
            wheel_pitch_diameter=wheel_pitch_diameter,
            length=10.0,
            sections_per_turn=12
        )
        assert globoid_geo.profile == "ZA"

    def test_globoid_profile_za_explicit(self, worm_params, assembly_params, wheel_pitch_diameter):
        """Test ZA profile can be explicitly set."""
        globoid_geo = GloboidWormGeometry(
            params=worm_params,
            assembly_params=assembly_params,
            wheel_pitch_diameter=wheel_pitch_diameter,
            length=10.0,
            sections_per_turn=12,
            profile="ZA"
        )
        assert globoid_geo.profile == "ZA"
        globoid = globoid_geo.build()
        assert globoid is not None
        assert globoid.volume > 0
        assert globoid.is_valid

    def test_globoid_profile_zk(self, worm_params, assembly_params, wheel_pitch_diameter):
        """Test ZK profile (convex flanks for 3D printing)."""
        globoid_geo = GloboidWormGeometry(
            params=worm_params,
            assembly_params=assembly_params,
            wheel_pitch_diameter=wheel_pitch_diameter,
            length=10.0,
            sections_per_turn=12,
            profile="ZK"
        )
        assert globoid_geo.profile == "ZK"
        globoid = globoid_geo.build()
        assert globoid is not None
        assert globoid.volume > 0
        assert globoid.is_valid

    def test_globoid_profile_case_insensitive(self, worm_params, assembly_params, wheel_pitch_diameter):
        """Test that profile parameter is case-insensitive."""
        for profile in ["za", "Za", "ZA", "zk", "Zk", "ZK"]:
            globoid_geo = GloboidWormGeometry(
                params=worm_params,
                assembly_params=assembly_params,
                wheel_pitch_diameter=wheel_pitch_diameter,
                length=10.0,
                sections_per_turn=12,
                profile=profile
            )
            assert globoid_geo.profile == profile.upper()

    def test_globoid_za_and_zk_both_valid(self, worm_params, assembly_params, wheel_pitch_diameter):
        """Test that both ZA and ZK profiles produce valid geometry."""
        globoid_za = GloboidWormGeometry(
            params=worm_params,
            assembly_params=assembly_params,
            wheel_pitch_diameter=wheel_pitch_diameter,
            length=10.0,
            sections_per_turn=12,
            profile="ZA"
        ).build()

        globoid_zk = GloboidWormGeometry(
            params=worm_params,
            assembly_params=assembly_params,
            wheel_pitch_diameter=wheel_pitch_diameter,
            length=10.0,
            sections_per_turn=12,
            profile="ZK"
        ).build()

        assert globoid_za.is_valid
        assert globoid_zk.is_valid
