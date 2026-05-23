"""Verify the old geometry constructors emit DeprecationWarning (#191 Phase 5).

The four legacy classes — ``WormGeometry``, ``WheelGeometry``,
``GloboidWormGeometry``, ``VirtualHobbingWheelGeometry`` — remain
functional but emit ``DeprecationWarning`` to nudge users toward the
``WormGear`` / ``WormWheel`` facade.

These tests bypass the suite-wide ``filterwarnings`` configuration
(which silences the warnings for the rest of the suite) by using
``pytest.warns`` to capture them locally.
"""

from __future__ import annotations

import math

import pytest

from wormgear.calculator import calculate_design_from_module
from wormgear.core import (
    GloboidWormGeometry,
    VirtualHobbingWheelGeometry,
    WheelGeometry,
    WormGeometry,
)

pytestmark = pytest.mark.slow


@pytest.fixture
def design():
    return calculate_design_from_module(module=1.0, ratio=20)


@pytest.fixture
def globoid_design():
    return calculate_design_from_module(
        module=2.0, ratio=30, globoid=True,
    )


class TestDeprecationWarnings:
    """Each of the four old classes must emit a DeprecationWarning on construction."""

    def test_worm_geometry_warns(self, design):
        with pytest.warns(DeprecationWarning, match="WormGeometry is deprecated"):
            WormGeometry(
                params=design.worm,
                assembly_params=design.assembly,
                length=10.0,
                sections_per_turn=12,
            )

    def test_wheel_geometry_warns(self, design):
        with pytest.warns(DeprecationWarning, match="WheelGeometry is deprecated"):
            WheelGeometry(
                params=design.wheel,
                worm_params=design.worm,
                assembly_params=design.assembly,
                face_width=4.0,
            )

    def test_globoid_worm_geometry_warns(self, globoid_design):
        with pytest.warns(DeprecationWarning, match="GloboidWormGeometry is deprecated"):
            GloboidWormGeometry(
                params=globoid_design.worm,
                assembly_params=globoid_design.assembly,
                wheel_pitch_diameter=globoid_design.wheel.pitch_diameter_mm,
                length=20.0,
                sections_per_turn=12,
            )

    def test_virtual_hobbing_wheel_geometry_warns(self, design):
        with pytest.warns(
            DeprecationWarning,
            match="VirtualHobbingWheelGeometry is deprecated",
        ):
            VirtualHobbingWheelGeometry(
                params=design.wheel,
                worm_params=design.worm,
                assembly_params=design.assembly,
                face_width=4.0,
                hobbing_steps=12,
            )


class TestDeprecatedConstructorsStillWork:
    """Old constructors must still build geometry — deprecation is a nudge, not a break."""

    def test_worm_geometry_still_builds(self, design):
        with pytest.warns(DeprecationWarning):
            geo = WormGeometry(
                params=design.worm,
                assembly_params=design.assembly,
                length=10.0,
                sections_per_turn=12,
            )
        part = geo.build()
        assert part.volume > 0
        assert part.is_valid

    def test_wheel_geometry_still_builds(self, design):
        with pytest.warns(DeprecationWarning):
            geo = WheelGeometry(
                params=design.wheel,
                worm_params=design.worm,
                assembly_params=design.assembly,
                face_width=4.0,
            )
        part = geo.build()
        assert part.volume > 0
        assert part.is_valid
