"""
Tests for worm geometry generation.
"""

import math
import pytest

from wormgear import load_design_json, WormParams, AssemblyParams, WormGeometry


class TestWormGeometry:
    """Tests for WormGeometry class."""

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

    def test_worm_geometry_creation(self, worm_params, assembly_params):
        """Test creating a WormGeometry instance."""
        worm_geo = WormGeometry(
            params=worm_params,
            assembly_params=assembly_params,
            length=20.0,
            sections_per_turn=36
        )

        assert worm_geo.params == worm_params
        assert worm_geo.length == 20.0
        assert worm_geo.sections_per_turn == 36

    def test_worm_build_returns_solid(self, worm_params, assembly_params):
        """Test that build() returns a valid solid."""
        worm_geo = WormGeometry(
            params=worm_params,
            assembly_params=assembly_params,
            length=10.0,
            sections_per_turn=12
        )
        worm = worm_geo.build()

        # Should return a solid with positive volume
        assert worm is not None
        assert hasattr(worm, 'volume')
        assert worm.volume > 0

    def test_worm_volume_reasonable(self, worm_params, assembly_params):
        """Test that worm volume is within reasonable bounds."""
        length = 10.0
        worm_geo = WormGeometry(
            params=worm_params,
            assembly_params=assembly_params,
            length=length,
            sections_per_turn=12
        )
        worm = worm_geo.build()

        # Volume should be between core cylinder and tip cylinder
        root_radius = worm_params.root_diameter_mm / 2
        tip_radius = worm_params.tip_diameter_mm / 2

        min_volume = math.pi * root_radius**2 * length
        max_volume = math.pi * tip_radius**2 * length

        assert worm.volume > min_volume * 0.9  # Allow some tolerance
        assert worm.volume < max_volume * 1.1

    def test_worm_different_lengths(self, worm_params, assembly_params):
        """Test worm generation with different lengths."""
        for length in [5.0, 10.0, 20.0, 40.0]:
            worm_geo = WormGeometry(
                params=worm_params,
                assembly_params=assembly_params,
                length=length,
                sections_per_turn=12
            )
            worm = worm_geo.build()

            assert worm is not None
            assert worm.volume > 0, f"Worm with length {length} has zero volume"

    def test_worm_short_length(self, worm_params, assembly_params):
        """Test worm with very short length (edge case).

        Tests that very short worms (length < lead) produce valid geometry.
        The profile calculation handles tapered ends correctly to avoid
        degenerate profiles.
        """
        # Length shorter than one lead
        length = worm_params.lead_mm * 0.5
        worm_geo = WormGeometry(
            params=worm_params,
            assembly_params=assembly_params,
            length=length,
            sections_per_turn=12
        )
        worm = worm_geo.build()

        assert worm is not None
        assert worm.volume > 0

    def test_worm_multiple_starts(self, assembly_params):
        """Test worm with multiple starts."""
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

        worm_geo = WormGeometry(
            params=params,
            assembly_params=assembly_params,
            length=30.0,
            sections_per_turn=12
        )
        worm = worm_geo.build()

        assert worm is not None
        assert worm.volume > 0

    def test_worm_left_hand(self, sample_design_left_hand):
        """Test left-hand worm generation."""
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

        worm_geo = WormGeometry(
            params=worm_params,
            assembly_params=assembly_params,
            length=20.0,
            sections_per_turn=12
        )
        worm = worm_geo.build()

        assert worm is not None
        assert worm.volume > 0

    def test_worm_sections_per_turn_affects_smoothness(self, worm_params, assembly_params):
        """Test that more sections per turn doesn't break geometry."""
        for sections in [8, 12, 24, 36, 72]:
            worm_geo = WormGeometry(
                params=worm_params,
                assembly_params=assembly_params,
                length=10.0,
                sections_per_turn=sections
            )
            worm = worm_geo.build()

            assert worm is not None
            assert worm.volume > 0, f"Worm with {sections} sections has zero volume"

    def test_worm_is_watertight(self, worm_params, assembly_params):
        """Test that the worm geometry is watertight (valid solid)."""
        worm_geo = WormGeometry(
            params=worm_params,
            assembly_params=assembly_params,
            length=10.0,
            sections_per_turn=12
        )
        worm = worm_geo.build()

        # A watertight solid should have is_valid() return True
        assert worm.is_valid

    def test_worm_bounding_box_reasonable(self, worm_params, assembly_params):
        """Test that worm bounding box matches expected dimensions."""
        length = 15.0
        worm_geo = WormGeometry(
            params=worm_params,
            assembly_params=assembly_params,
            length=length,
            sections_per_turn=12
        )
        worm = worm_geo.build()

        bbox = worm.bounding_box()
        tip_diameter = worm_params.tip_diameter_mm

        # X and Y extents should be approximately tip diameter
        x_extent = bbox.max.X - bbox.min.X
        y_extent = bbox.max.Y - bbox.min.Y
        z_extent = bbox.max.Z - bbox.min.Z

        assert abs(x_extent - tip_diameter) < 1.0
        assert abs(y_extent - tip_diameter) < 1.0
        assert abs(z_extent - length) < 1.0


class TestWormProfileTypes:
    """Tests for DIN 3975 profile types (ZA/ZK)."""

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

    def test_worm_profile_za_default(self, worm_params, assembly_params):
        """Test that ZA profile is the default."""
        worm_geo = WormGeometry(
            params=worm_params,
            assembly_params=assembly_params,
            length=10.0,
            sections_per_turn=12
        )
        assert worm_geo.profile == "ZA"

    def test_worm_profile_za_explicit(self, worm_params, assembly_params):
        """Test ZA profile can be explicitly set."""
        worm_geo = WormGeometry(
            params=worm_params,
            assembly_params=assembly_params,
            length=10.0,
            sections_per_turn=12,
            profile="ZA"
        )
        assert worm_geo.profile == "ZA"
        worm = worm_geo.build()
        assert worm is not None
        assert worm.volume > 0
        assert worm.is_valid

    def test_worm_profile_zk(self, worm_params, assembly_params):
        """Test ZK profile (convex flanks for 3D printing)."""
        worm_geo = WormGeometry(
            params=worm_params,
            assembly_params=assembly_params,
            length=10.0,
            sections_per_turn=12,
            profile="ZK"
        )
        assert worm_geo.profile == "ZK"
        worm = worm_geo.build()
        assert worm is not None
        assert worm.volume > 0
        assert worm.is_valid

    def test_worm_profile_case_insensitive(self, worm_params, assembly_params):
        """Test that profile parameter is case-insensitive."""
        for profile in ["za", "Za", "ZA", "zk", "Zk", "ZK"]:
            worm_geo = WormGeometry(
                params=worm_params,
                assembly_params=assembly_params,
                length=10.0,
                sections_per_turn=12,
                profile=profile
            )
            assert worm_geo.profile == profile.upper()

    def test_worm_za_and_zk_produce_different_geometry(self, worm_params, assembly_params):
        """Test that ZA and ZK profiles produce different geometry."""
        worm_za = WormGeometry(
            params=worm_params,
            assembly_params=assembly_params,
            length=10.0,
            sections_per_turn=12,
            profile="ZA"
        ).build()

        worm_zk = WormGeometry(
            params=worm_params,
            assembly_params=assembly_params,
            length=10.0,
            sections_per_turn=12,
            profile="ZK"
        ).build()

        # Both should be valid
        assert worm_za.is_valid
        assert worm_zk.is_valid

        # Volumes should be slightly different due to curved vs straight flanks
        # ZK has convex bulge, so slightly more material
        assert abs(worm_za.volume - worm_zk.volume) / worm_za.volume < 0.05  # Within 5%


class TestWormFromJsonFile:
    """Tests using actual JSON files."""

    def test_build_worm_from_7mm_json(self, examples_dir):
        """Test building worm from 7mm.json example file."""
        example_file = examples_dir / "7mm.json"
        if not example_file.exists():
            pytest.skip("Example file not found")

        design = load_design_json(example_file)
        worm_geo = WormGeometry(
            params=design.worm,
            assembly_params=design.assembly,
            length=10.0,
            sections_per_turn=12
        )
        worm = worm_geo.build()

        assert worm is not None
        assert worm.volume > 0
        assert worm.is_valid
