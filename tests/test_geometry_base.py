"""
Tests for BaseGeometry export methods.

These tests require geometry building (slow).
"""

import pytest
import tempfile
from pathlib import Path

from wormgear import WormGeometry

pytestmark = pytest.mark.slow


class TestExportStep:
    """Tests for BaseGeometry.export_step()."""

    def test_export_step_writes_file(
        self, worm_params_7mm, assembly_params_7mm, tmp_path
    ):
        """export_step writes a non-empty STEP file."""
        geo = WormGeometry(
            params=worm_params_7mm,
            assembly_params=assembly_params_7mm,
            length=10.0,
            sections_per_turn=12,
        )

        step_path = tmp_path / "worm.step"
        geo.export_step(str(step_path))

        assert step_path.exists()
        assert step_path.stat().st_size > 0

    def test_export_step_auto_builds(
        self, worm_params_7mm, assembly_params_7mm, tmp_path
    ):
        """export_step builds geometry if not already built."""
        geo = WormGeometry(
            params=worm_params_7mm,
            assembly_params=assembly_params_7mm,
            length=10.0,
            sections_per_turn=12,
        )
        # Don't call build() first
        assert geo._part is None

        step_path = tmp_path / "worm_auto.step"
        geo.export_step(str(step_path))

        assert step_path.exists()
        assert geo._part is not None

    def test_export_step_uses_existing_build(
        self, worm_params_7mm, assembly_params_7mm, tmp_path
    ):
        """export_step reuses existing build rather than rebuilding."""
        geo = WormGeometry(
            params=worm_params_7mm,
            assembly_params=assembly_params_7mm,
            length=10.0,
            sections_per_turn=12,
        )
        part = geo.build()

        step_path = tmp_path / "worm_reuse.step"
        geo.export_step(str(step_path))

        assert step_path.exists()
        # _part should be the same object
        assert geo._part is part


class TestExportGltf:
    """Tests for BaseGeometry.export_gltf()."""

    def test_export_gltf_binary(
        self, worm_params_7mm, assembly_params_7mm, tmp_path
    ):
        """export_gltf writes a binary .glb file."""
        geo = WormGeometry(
            params=worm_params_7mm,
            assembly_params=assembly_params_7mm,
            length=10.0,
            sections_per_turn=12,
        )
        geo.build()

        glb_path = tmp_path / "worm.glb"
        geo.export_gltf(str(glb_path), binary=True)

        assert glb_path.exists()
        assert glb_path.stat().st_size > 0

    def test_export_gltf_auto_builds(
        self, worm_params_7mm, assembly_params_7mm, tmp_path
    ):
        """export_gltf builds geometry if not already built."""
        geo = WormGeometry(
            params=worm_params_7mm,
            assembly_params=assembly_params_7mm,
            length=10.0,
            sections_per_turn=12,
        )
        assert geo._part is None

        glb_path = tmp_path / "worm_auto.glb"
        geo.export_gltf(str(glb_path))

        assert glb_path.exists()
        assert geo._part is not None


class TestPartName:
    """Tests for _part_name class attribute."""

    def test_worm_part_name(self):
        """WormGeometry has a descriptive part name."""
        assert hasattr(WormGeometry, "_part_name")
        assert isinstance(WormGeometry._part_name, str)
        assert len(WormGeometry._part_name) > 0
