"""
Tests for virtual hobbing wheel geometry generation (experimental).

These tests verify that the VirtualHobbingWheelGeometry class produces
valid geometry through kinematic simulation of the hobbing process.
"""

import math
import pytest

from wormgear import (
    VirtualHobbingWheelGeometry, WheelGeometry,
)

pytestmark = pytest.mark.slow


class TestVirtualHobbingWheelGeometry:
    """Tests for VirtualHobbingWheelGeometry class."""

    def test_virtual_hobbing_creation(self, wheel_params, worm_params, assembly_params):
        """Test creating a VirtualHobbingWheelGeometry instance."""
        wheel_geo = VirtualHobbingWheelGeometry(
            params=wheel_params,
            worm_params=worm_params,
            assembly_params=assembly_params,
            face_width=4.0,
            hobbing_steps=36
        )

        assert wheel_geo.params == wheel_params
        assert wheel_geo.worm_params == worm_params
        assert wheel_geo.face_width == 4.0
        assert wheel_geo.hobbing_steps == 36

    def test_virtual_hobbing_default_steps(self, wheel_params, worm_params, assembly_params):
        """Test default hobbing steps value."""
        wheel_geo = VirtualHobbingWheelGeometry(
            params=wheel_params,
            worm_params=worm_params,
            assembly_params=assembly_params,
            face_width=4.0
        )

        assert wheel_geo.hobbing_steps == 72  # Default value

    def test_virtual_hobbing_build_returns_solid(self, wheel_params, worm_params, assembly_params):
        """Test that build() returns a valid solid."""
        # Use fewer steps for faster test
        wheel_geo = VirtualHobbingWheelGeometry(
            params=wheel_params,
            worm_params=worm_params,
            assembly_params=assembly_params,
            face_width=4.0,
            hobbing_steps=18  # Reduced for speed
        )
        wheel = wheel_geo.build()

        assert wheel is not None
        assert hasattr(wheel, 'volume')
        assert wheel.volume > 0

    def test_virtual_hobbing_volume_reasonable(self, wheel_params, worm_params, assembly_params):
        """Test that virtual hobbing wheel volume is within reasonable bounds."""
        face_width = 4.0
        wheel_geo = VirtualHobbingWheelGeometry(
            params=wheel_params,
            worm_params=worm_params,
            assembly_params=assembly_params,
            face_width=face_width,
            hobbing_steps=18
        )
        wheel = wheel_geo.build()

        # Volume should be less than solid cylinder at tip diameter
        tip_radius = wheel_params.tip_diameter_mm / 2
        max_volume = math.pi * tip_radius**2 * face_width

        # And more than a small fraction (teeth take up space)
        min_volume = max_volume * 0.3

        assert wheel.volume > min_volume
        assert wheel.volume < max_volume

    def test_virtual_hobbing_is_watertight(self, wheel_params, worm_params, assembly_params):
        """Test that virtual hobbing wheel geometry is watertight."""
        wheel_geo = VirtualHobbingWheelGeometry(
            params=wheel_params,
            worm_params=worm_params,
            assembly_params=assembly_params,
            face_width=4.0,
            hobbing_steps=18
        )
        wheel = wheel_geo.build()

        assert wheel.is_valid

    def test_virtual_hobbing_auto_face_width(self, wheel_params, worm_params, assembly_params):
        """Test that face width is auto-calculated when not specified."""
        wheel_geo = VirtualHobbingWheelGeometry(
            params=wheel_params,
            worm_params=worm_params,
            assembly_params=assembly_params,
            face_width=None,
            hobbing_steps=18
        )

        # Auto face width should be positive and reasonable
        assert wheel_geo.face_width > 0
        assert wheel_geo.face_width < worm_params.tip_diameter_mm * 1.5


class TestVirtualHobbingProfileTypes:
    """Tests for DIN 3975 profile types (ZA/ZK) with virtual hobbing."""

    def test_virtual_hobbing_profile_za_default(self, wheel_params, worm_params, assembly_params):
        """Test that ZA profile is the default for virtual hobbing."""
        wheel_geo = VirtualHobbingWheelGeometry(
            params=wheel_params,
            worm_params=worm_params,
            assembly_params=assembly_params,
            face_width=4.0,
            hobbing_steps=18
        )
        assert wheel_geo.profile == "ZA"

    def test_virtual_hobbing_profile_zk(self, wheel_params, worm_params, assembly_params):
        """Test ZK profile with virtual hobbing."""
        wheel_geo = VirtualHobbingWheelGeometry(
            params=wheel_params,
            worm_params=worm_params,
            assembly_params=assembly_params,
            face_width=4.0,
            hobbing_steps=18,
            profile="ZK"
        )
        assert wheel_geo.profile == "ZK"
        wheel = wheel_geo.build()
        assert wheel is not None
        assert wheel.volume > 0

    def test_virtual_hobbing_profile_case_insensitive(self, wheel_params, worm_params, assembly_params):
        """Test that profile parameter is case-insensitive."""
        for profile in ["za", "ZA", "zk", "ZK"]:
            wheel_geo = VirtualHobbingWheelGeometry(
                params=wheel_params,
                worm_params=worm_params,
                assembly_params=assembly_params,
                face_width=4.0,
                hobbing_steps=18,
                profile=profile
            )
            assert wheel_geo.profile == profile.upper()


class TestVirtualHobbingVsStandardWheel:
    """Comparison tests between virtual hobbing and standard wheel generation."""

    def test_virtual_hobbing_produces_similar_volume_to_throated(
        self, wheel_params, worm_params, assembly_params
    ):
        """Test that virtual hobbing produces volume similar to throated wheel."""
        face_width = 4.0

        # Build throated wheel (existing method)
        throated_geo = WheelGeometry(
            params=wheel_params,
            worm_params=worm_params,
            assembly_params=assembly_params,
            face_width=face_width,
            throated=True
        )
        throated_wheel = throated_geo.build()

        # Build virtual hobbing wheel
        hobbing_geo = VirtualHobbingWheelGeometry(
            params=wheel_params,
            worm_params=worm_params,
            assembly_params=assembly_params,
            face_width=face_width,
            hobbing_steps=36  # Moderate accuracy
        )
        hobbing_wheel = hobbing_geo.build()

        # Volumes should be within 20% of each other
        # (virtual hobbing may be slightly different due to true conjugate profile)
        volume_ratio = hobbing_wheel.volume / throated_wheel.volume
        assert 0.8 < volume_ratio < 1.2, f"Volume ratio {volume_ratio} outside expected range"

    def test_both_methods_produce_valid_geometry(
        self, wheel_params, worm_params, assembly_params
    ):
        """Test that both methods produce valid, watertight geometry."""
        face_width = 4.0

        # Standard throated
        throated = WheelGeometry(
            params=wheel_params,
            worm_params=worm_params,
            assembly_params=assembly_params,
            face_width=face_width,
            throated=True
        ).build()

        # Virtual hobbing
        hobbing = VirtualHobbingWheelGeometry(
            params=wheel_params,
            worm_params=worm_params,
            assembly_params=assembly_params,
            face_width=face_width,
            hobbing_steps=18
        ).build()

        assert throated.is_valid
        assert hobbing.is_valid


class TestVirtualHobbingWithFeatures:
    """Tests for virtual hobbing with bore, keyway, and hub features."""

    def test_virtual_hobbing_with_bore(self, wheel_params, worm_params, assembly_params):
        """Test virtual hobbing wheel with bore feature."""
        from wormgear.core.features import BoreFeature

        wheel_geo = VirtualHobbingWheelGeometry(
            params=wheel_params,
            worm_params=worm_params,
            assembly_params=assembly_params,
            face_width=4.0,
            hobbing_steps=18,
            bore=BoreFeature(diameter=2.0)
        )
        wheel = wheel_geo.build()

        # Wheel with bore should have less volume
        wheel_solid = VirtualHobbingWheelGeometry(
            params=wheel_params,
            worm_params=worm_params,
            assembly_params=assembly_params,
            face_width=4.0,
            hobbing_steps=18
        ).build()

        assert wheel.volume < wheel_solid.volume
        assert wheel.is_valid

    def test_virtual_hobbing_with_keyway(self, wheel_params, worm_params, assembly_params):
        """Test virtual hobbing wheel with bore and keyway."""
        from wormgear.core.features import BoreFeature, KeywayFeature

        wheel_geo = VirtualHobbingWheelGeometry(
            params=wheel_params,
            worm_params=worm_params,
            assembly_params=assembly_params,
            face_width=4.0,
            hobbing_steps=18,
            bore=BoreFeature(diameter=6.0),
            keyway=KeywayFeature()
        )
        wheel = wheel_geo.build()

        assert wheel is not None
        assert wheel.volume > 0
        assert wheel.is_valid
