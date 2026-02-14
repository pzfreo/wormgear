"""
Base class for wormgear geometry classes.

Provides shared export and display methods used by WormGeometry,
WheelGeometry, GloboidWormGeometry, and VirtualHobbingWheelGeometry.
"""

import logging

logger = logging.getLogger(__name__)


class BaseGeometry:
    """Base class providing shared export/display methods for geometry classes.

    Subclasses must:
    - Set self._part = None in __init__
    - Implement build() -> Part
    - Set _part_name class attribute for log messages
    """

    _part_name: str = "part"

    def show(self):
        """Display in OCP viewer (requires ocp_vscode)."""
        part = self.build()
        try:
            from ocp_vscode import show as ocp_show
            ocp_show(part)
        except ImportError:
            pass
        return part

    def export_step(self, filepath: str):
        """Export to STEP file (builds if not already built)."""
        if self._part is None:
            self.build()

        logger.info(f"Exporting {self._part_name}: volume={self._part.volume:.2f} mm³")
        if hasattr(self._part, 'export_step'):
            self._part.export_step(filepath)
        else:
            from build123d import export_step as exp_step
            exp_step(self._part, filepath)

        logger.info(f"Exported {self._part_name} to {filepath}")

    def export_gltf(self, filepath: str, binary: bool = True):
        """Export to glTF file (builds if not already built).

        Args:
            filepath: Output path (.glb for binary, .gltf for text)
            binary: If True, export as binary .glb (default)
        """
        if self._part is None:
            self.build()

        from build123d import export_gltf as b3d_export_gltf
        b3d_export_gltf(
            self._part, filepath, binary=binary,
            linear_deflection=0.001, angular_deflection=0.1,
        )
        logger.info(f"Exported {self._part_name} to {filepath}")
