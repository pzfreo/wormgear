"""
Unit tests for geometry repair and simplification utilities.

These test the extracted functions from geometry_repair.py to ensure
they behave identically to the original instance methods.
"""

import logging
import pytest

from build123d import Part, Cylinder, Box, Align

from wormgear.core.geometry_repair import repair_geometry, simplify_geometry

pytestmark = pytest.mark.slow


class TestSimplifyGeometry:
    """Tests for simplify_geometry()."""

    def test_valid_part_unchanged(self):
        """A valid cylinder should pass through simplification with same volume."""
        cyl = Cylinder(radius=10, height=20, align=(Align.CENTER, Align.CENTER, Align.CENTER))
        original_volume = cyl.volume

        result = simplify_geometry(cyl)

        assert isinstance(result, Part)
        assert result.is_valid
        assert abs(result.volume - original_volume) / original_volume < 0.01

    def test_returns_part_type(self):
        """Result should always be a Part."""
        box = Box(10, 10, 10)
        result = simplify_geometry(box)
        assert isinstance(result, Part)

    def test_with_description_logs(self, caplog):
        """When description is provided, it should appear in logs."""
        cyl = Cylinder(radius=5, height=10)
        with caplog.at_level(logging.DEBUG):
            simplify_geometry(cyl, description="test cylinder")
        assert any("test cylinder" in r.message for r in caplog.records)

    def test_without_description_no_description_log(self, caplog):
        """When no description, no 'Simplifying' log should appear."""
        cyl = Cylinder(radius=5, height=10)
        with caplog.at_level(logging.DEBUG):
            simplify_geometry(cyl)
        assert not any("Simplifying" in r.message for r in caplog.records)

    def test_cylinder_volume_preserved(self):
        """Simplification should preserve volume of a valid solid."""
        cyl = Cylinder(radius=15, height=30)
        original_volume = cyl.volume
        result = simplify_geometry(cyl, "test cylinder")
        assert isinstance(result, Part)
        assert result.volume > 0
        assert abs(result.volume - original_volume) / original_volume < 0.01


class TestRepairGeometry:
    """Tests for repair_geometry()."""

    def test_valid_part_returns_quickly(self):
        """A valid Part should be returned immediately without repair."""
        cyl = Cylinder(radius=10, height=20)
        assert cyl.is_valid

        result = repair_geometry(cyl)
        assert result.is_valid
        assert abs(result.volume - cyl.volume) < 0.01

    def test_returns_part_on_any_input(self):
        """repair_geometry should always return a Part and never raise."""
        box = Box(5, 5, 5)
        result = repair_geometry(box)
        assert isinstance(result, Part)
        assert result.volume > 0

    def test_preserves_volume(self):
        """Volume should be preserved through repair."""
        cyl = Cylinder(radius=8, height=15)
        original_volume = cyl.volume

        result = repair_geometry(cyl)
        assert abs(result.volume - original_volume) / original_volume < 0.01

    def test_multiple_calls_idempotent(self):
        """Calling repair_geometry twice should produce the same result."""
        cyl = Cylinder(radius=10, height=20)
        result1 = repair_geometry(cyl)
        result2 = repair_geometry(result1)
        assert isinstance(result2, Part)
        assert abs(result2.volume - result1.volume) < 0.01
