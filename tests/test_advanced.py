"""Tests for ``wormgear.advanced.virtual_hobbing`` (#203).

The helper produces a kinematically-simulated wheel — different code path
from ``WormWheel(throated=True)``, which is a simpler throat-cut
approximation.

These tests use small designs and low step counts to keep runtime
manageable. ``test_virtual_hobbing.py`` continues to exercise the
underlying ``_VirtualHobbingWheelGeometry`` with a fuller matrix.
"""

from __future__ import annotations

import pytest
from build123d import Part

from wormgear import WormGear, WormWheel
from wormgear.advanced import virtual_hobbing

pytestmark = pytest.mark.slow


# Match the existing test_virtual_hobbing.py fixture sizes.
SMALL_MODULE = 0.5
SMALL_NUM_TEETH = 12
SMALL_FACE_WIDTH = 4.0
SMALL_WORM_LENGTH = 10.0
TEST_STEPS = 18


@pytest.fixture(scope="module")
def worm():
    return WormGear(
        module=SMALL_MODULE,
        num_starts=1,
        length=SMALL_WORM_LENGTH,
        sections_per_turn=12,
    )


@pytest.fixture(scope="module")
def baseline_wheel():
    return WormWheel(
        module=SMALL_MODULE,
        num_teeth=SMALL_NUM_TEETH,
        face_width=SMALL_FACE_WIDTH,
    )


@pytest.fixture(scope="module")
def hobbed(worm, baseline_wheel):
    """Module-scoped — built once for all tests in this file."""
    return virtual_hobbing(worm, baseline_wheel, steps=TEST_STEPS)


class TestReturnType:
    def test_returns_worm_wheel(self, hobbed):
        assert isinstance(hobbed, WormWheel)

    def test_is_build123d_part(self, hobbed):
        assert isinstance(hobbed, Part)

    def test_is_valid_solid(self, hobbed):
        assert hobbed.is_valid
        assert hobbed.volume > 0


class TestEngineeringParamsPreserved:
    """The returned wheel carries the same engineering inputs as the source."""

    def test_module(self, hobbed):
        assert hobbed.module == SMALL_MODULE

    def test_num_teeth(self, hobbed):
        assert hobbed.num_teeth == SMALL_NUM_TEETH

    def test_face_width(self, hobbed):
        assert hobbed.face_width == SMALL_FACE_WIDTH

    def test_throated_is_false(self, hobbed):
        """The simulation does not produce a throat cut — that's a different approach."""
        assert hobbed.throated is False

    def test_introspection_attrs(self, hobbed):
        assert hasattr(hobbed, "_params")
        assert hasattr(hobbed, "_worm_params")
        assert hasattr(hobbed, "_assembly_params")
        assert hobbed._params.num_teeth == SMALL_NUM_TEETH


class TestDifferentFromBaseline:
    """virtual_hobbing must produce geometry distinct from a plain WormWheel."""

    def test_differs_from_simple_wheel(self, baseline_wheel, hobbed):
        """The simulation removes additional material at tooth flanks."""
        rel = abs(hobbed.volume - baseline_wheel.volume) / baseline_wheel.volume
        assert rel > 1e-3, (
            f"virtual_hobbing should produce visibly different geometry "
            f"from a simple WormWheel; volumes were nearly identical "
            f"(rel diff {rel:.2e})"
        )
