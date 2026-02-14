"""
End-to-end pipeline integration tests.

Tests the full design_from_module() -> geometry builder -> .build() -> STEP
export pipeline that no other test file covers.
"""

import tempfile
from pathlib import Path

import pytest
from build123d import export_step

from wormgear.calculator.core import design_from_module
from wormgear.core import (
    WormGeometry,
    WheelGeometry,
    GloboidWormGeometry,
    VirtualHobbingWheelGeometry,
    BoreFeature,
    KeywayFeature,
)

pytestmark = pytest.mark.slow


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _assert_valid_part(part, min_volume: float = 1.0):
    """Assert a built Part is valid and has meaningful volume."""
    assert part.is_valid, "Part is not valid"
    assert part.volume > min_volume, f"Part volume {part.volume:.2f} too small"


def _assert_step_export(part):
    """Assert STEP export succeeds and produces a non-empty file."""
    with tempfile.NamedTemporaryFile(suffix=".step", delete=False) as f:
        step_path = Path(f.name)
    try:
        export_step(part, str(step_path))
        assert step_path.exists(), "STEP file not created"
        assert step_path.stat().st_size > 100, "STEP file is suspiciously small"
    finally:
        step_path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Calculator -> Geometry -> Build -> Export
# ---------------------------------------------------------------------------

class TestCalculatorToGeometryPipeline:
    """Full pipeline: design_from_module -> geometry class -> build -> export."""

    def test_cylindrical_worm_pipeline(self):
        """design_from_module -> WormGeometry.build() -> valid + STEP export."""
        design = design_from_module(module=2.0, ratio=30)

        worm_geo = WormGeometry(
            params=design.worm,
            assembly_params=design.assembly,
            length=30.0,
            sections_per_turn=12,
        )
        worm = worm_geo.build()

        _assert_valid_part(worm)
        _assert_step_export(worm)

    def test_cylindrical_wheel_pipeline(self):
        """design_from_module -> WheelGeometry.build() -> valid + STEP export."""
        design = design_from_module(module=2.0, ratio=30)

        wheel_geo = WheelGeometry(
            params=design.wheel,
            worm_params=design.worm,
            assembly_params=design.assembly,
            face_width=12.0,
        )
        wheel = wheel_geo.build()

        _assert_valid_part(wheel)
        _assert_step_export(wheel)

    def test_globoid_worm_pipeline(self):
        """design_from_module(globoid) -> GloboidWormGeometry.build() -> valid."""
        design = design_from_module(
            module=2.0,
            ratio=30,
            globoid=True,
            throat_reduction=2.0,
        )

        globoid_geo = GloboidWormGeometry(
            params=design.worm,
            assembly_params=design.assembly,
            wheel_pitch_diameter=design.wheel.pitch_diameter_mm,
            length=30.0,
            sections_per_turn=12,
        )
        globoid = globoid_geo.build()

        _assert_valid_part(globoid)
        _assert_step_export(globoid)

    def test_virtual_hobbing_wheel_pipeline(self):
        """design_from_module -> VirtualHobbingWheelGeometry.build(6 steps) -> valid."""
        design = design_from_module(module=2.0, ratio=20, num_starts=1)

        vhob_geo = VirtualHobbingWheelGeometry(
            params=design.wheel,
            worm_params=design.worm,
            assembly_params=design.assembly,
            face_width=10.0,
            hobbing_steps=6,
        )
        wheel = vhob_geo.build()

        _assert_valid_part(wheel)

    def test_left_hand_pair_pipeline(self):
        """design_from_module(hand='left') -> build worm + wheel -> both valid."""
        design = design_from_module(module=1.5, ratio=20, hand="left")

        worm_geo = WormGeometry(
            params=design.worm,
            assembly_params=design.assembly,
            length=20.0,
            sections_per_turn=12,
        )
        worm = worm_geo.build()
        _assert_valid_part(worm)

        wheel_geo = WheelGeometry(
            params=design.wheel,
            worm_params=design.worm,
            assembly_params=design.assembly,
            face_width=8.0,
        )
        wheel = wheel_geo.build()
        _assert_valid_part(wheel)


# ---------------------------------------------------------------------------
# Feature Combinations
# ---------------------------------------------------------------------------

class TestFeatureCombinations:
    """Test geometry with bore and keyway features applied."""

    def test_worm_with_bore_and_keyway(self):
        """WormGeometry + BoreFeature + KeywayFeature -> valid."""
        design = design_from_module(module=2.0, ratio=30)

        worm_geo = WormGeometry(
            params=design.worm,
            assembly_params=design.assembly,
            length=30.0,
            sections_per_turn=12,
            bore=BoreFeature(diameter=8.0),
            keyway=KeywayFeature(),
        )
        worm = worm_geo.build()

        _assert_valid_part(worm)
        _assert_step_export(worm)

    def test_wheel_with_bore_and_keyway(self):
        """WheelGeometry + BoreFeature + KeywayFeature -> valid."""
        design = design_from_module(module=2.0, ratio=30)

        wheel_geo = WheelGeometry(
            params=design.wheel,
            worm_params=design.worm,
            assembly_params=design.assembly,
            face_width=12.0,
            bore=BoreFeature(diameter=12.0),
            keyway=KeywayFeature(),
        )
        wheel = wheel_geo.build()

        _assert_valid_part(wheel)
        _assert_step_export(wheel)

    def test_globoid_with_bore(self):
        """GloboidWormGeometry + BoreFeature -> valid."""
        design = design_from_module(
            module=2.0,
            ratio=30,
            globoid=True,
            throat_reduction=2.0,
        )

        globoid_geo = GloboidWormGeometry(
            params=design.worm,
            assembly_params=design.assembly,
            wheel_pitch_diameter=design.wheel.pitch_diameter_mm,
            length=30.0,
            sections_per_turn=12,
            bore=BoreFeature(diameter=8.0),
        )
        globoid = globoid_geo.build()

        _assert_valid_part(globoid)
        _assert_step_export(globoid)
