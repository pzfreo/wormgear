"""
Shared export and packaging logic for worm gear geometry.

Used by both CLI (generate.py) and web (generator-worker.js) to produce
identical output packages: STEP, 3MF, STL, assembly 3MF, design.json,
and design.md.

CLI writes files to a directory (with optional ZIP); web always ZIPs.
"""

import io
import json
import logging
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from build123d import Mesher, Part, Unit, export_step, export_stl

from ..enums import WormType
from .loaders import WormGearDesign

logger = logging.getLogger(__name__)

# Mesh settings matching web's fine quality
LINEAR_DEFLECTION = 0.0005
ANGULAR_DEFLECTION = 0.05


def _repair_for_export(part: Part, name: str) -> Part:
    """Apply geometry repair before STEP export.

    Uses ShapeUpgrade_UnifySameDomain + ShapeFix_Shape to merge adjacent
    faces on the same surface and fix remaining issues.
    """
    try:
        from OCP.ShapeFix import ShapeFix_Shape
        from OCP.ShapeUpgrade import ShapeUpgrade_UnifySameDomain

        unifier = ShapeUpgrade_UnifySameDomain(part.wrapped, True, True, True)
        unifier.Build()
        unified = unifier.Shape()

        fixer = ShapeFix_Shape(unified)
        fixer.Perform()
        fixed = fixer.Shape()

        return Part(fixed)
    except Exception as e:
        logger.warning(f"Geometry repair failed for {name}: {e}")
        return part


def export_part_step(part: Part, name: str = "part") -> bytes:
    """Export Part to STEP bytes with geometry repair.

    Args:
        part: build123d Part to export.
        name: Label for log messages.

    Returns:
        STEP file contents as bytes.
    """
    repaired = _repair_for_export(part, name)

    with tempfile.NamedTemporaryFile(suffix=".step", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        export_step(repaired, str(tmp_path))
        return tmp_path.read_bytes()
    finally:
        tmp_path.unlink(missing_ok=True)


def export_part_3mf(part: Part) -> Optional[bytes]:
    """Export Part to 3MF bytes.

    Returns None if meshing fails (non-fatal — matches web behaviour).
    """
    try:
        with tempfile.NamedTemporaryFile(suffix=".3mf", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        mesher = Mesher(unit=Unit.MM)
        mesher.add_shape(
            part,
            linear_deflection=LINEAR_DEFLECTION,
            angular_deflection=ANGULAR_DEFLECTION,
        )
        mesher.write(str(tmp_path))

        data = tmp_path.read_bytes()
        return data
    except Exception as e:
        logger.warning(f"3MF export failed (non-fatal): {e}")
        return None
    finally:
        tmp_path.unlink(missing_ok=True)


def export_part_stl(part: Part) -> bytes:
    """Export Part to STL bytes."""
    with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        export_stl(
            part,
            str(tmp_path),
            tolerance=LINEAR_DEFLECTION,
            angular_tolerance=ANGULAR_DEFLECTION,
        )
        return tmp_path.read_bytes()
    finally:
        tmp_path.unlink(missing_ok=True)


def export_assembly_3mf(
    wheel: Part,
    worm: Part,
    centre_distance_mm: float,
    rotation_deg: float,
) -> Optional[bytes]:
    """Position parts with position_for_mesh() and export combined 3MF.

    Returns None if export fails (non-fatal).
    """
    try:
        from ..core.mesh_alignment import position_for_mesh

        wheel_pos, worm_pos = position_for_mesh(
            wheel, worm, centre_distance_mm, rotation_deg
        )

        with tempfile.NamedTemporaryFile(suffix=".3mf", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        mesher = Mesher(unit=Unit.MM)
        mesher.add_shape(
            wheel_pos,
            linear_deflection=LINEAR_DEFLECTION,
            angular_deflection=ANGULAR_DEFLECTION,
        )
        mesher.add_shape(
            worm_pos,
            linear_deflection=LINEAR_DEFLECTION,
            angular_deflection=ANGULAR_DEFLECTION,
        )
        mesher.write(str(tmp_path))

        data = tmp_path.read_bytes()
        return data
    except Exception as e:
        logger.warning(f"Assembly 3MF export failed (non-fatal): {e}")
        return None
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except NameError:
            pass


@dataclass
class PackageFiles:
    """Container for all output files from geometry generation."""

    worm_step: Optional[bytes] = None
    wheel_step: Optional[bytes] = None
    worm_3mf: Optional[bytes] = None
    wheel_3mf: Optional[bytes] = None
    worm_stl: Optional[bytes] = None
    wheel_stl: Optional[bytes] = None
    assembly_3mf: Optional[bytes] = None
    design_json: Optional[str] = None
    design_md: Optional[str] = None
    mesh_rotation_deg: float = 0.0


def generate_package(
    design: WormGearDesign,
    worm: Optional[Part] = None,
    wheel: Optional[Part] = None,
    mesh_rotation_deg: Optional[float] = None,
    virtual_hobbing: bool = False,
    include_3mf: bool = True,
    include_stl: bool = True,
    include_assembly: bool = True,
    validation=None,
    log: Optional[Callable[[str], None]] = None,
) -> PackageFiles:
    """Generate all output files for a worm gear design.

    Single entry point used by both CLI and web generator.

    Args:
        design: WormGearDesign with all parameters.
        worm: Built worm Part (or None to skip worm exports).
        wheel: Built wheel Part (or None to skip wheel exports).
        mesh_rotation_deg: Explicit mesh rotation. None = auto-calculate
            when both parts present (0.0 for virtual hobbing).
        virtual_hobbing: If True and mesh_rotation_deg is None, uses 0.0
            instead of auto-calculating.
        include_3mf: Generate 3MF files (default True).
        include_stl: Generate STL files (default True).
        include_assembly: Generate assembly 3MF (default True).
        validation: Optional ValidationResult for design.json/md output.
        log: Optional logging callback (e.g. print).

    Returns:
        PackageFiles with all generated file data.
    """
    files = PackageFiles()

    def _log(msg: str):
        if log:
            log(msg)

    # --- Mesh rotation ---
    if mesh_rotation_deg is not None:
        files.mesh_rotation_deg = mesh_rotation_deg
    elif virtual_hobbing:
        files.mesh_rotation_deg = 0.0
    elif worm is not None and wheel is not None:
        _log("Calculating mesh alignment...")
        from ..core.mesh_alignment import find_optimal_mesh_rotation

        result = find_optimal_mesh_rotation(
            wheel=wheel,
            worm=worm,
            centre_distance_mm=design.assembly.centre_distance_mm,
            num_teeth=design.wheel.num_teeth,
            module_mm=design.worm.module_mm,
        )
        files.mesh_rotation_deg = result.optimal_rotation_deg
        _log(f"  Optimal rotation: {result.optimal_rotation_deg:.2f} deg")

    # --- Worm exports ---
    if worm is not None:
        _log("Exporting worm STEP...")
        files.worm_step = export_part_step(worm, "worm")
        _log(f"  STEP: {len(files.worm_step) / 1024:.1f} KB")

        if include_3mf:
            _log("Exporting worm 3MF...")
            files.worm_3mf = export_part_3mf(worm)
            if files.worm_3mf:
                _log(f"  3MF: {len(files.worm_3mf) / 1024:.1f} KB")

        if include_stl:
            _log("Exporting worm STL...")
            files.worm_stl = export_part_stl(worm)
            _log(f"  STL: {len(files.worm_stl) / 1024:.1f} KB")

    # --- Wheel exports ---
    if wheel is not None:
        _log("Exporting wheel STEP...")
        files.wheel_step = export_part_step(wheel, "wheel")
        _log(f"  STEP: {len(files.wheel_step) / 1024:.1f} KB")

        if include_3mf:
            _log("Exporting wheel 3MF...")
            files.wheel_3mf = export_part_3mf(wheel)
            if files.wheel_3mf:
                _log(f"  3MF: {len(files.wheel_3mf) / 1024:.1f} KB")

        if include_stl:
            _log("Exporting wheel STL...")
            files.wheel_stl = export_part_stl(wheel)
            _log(f"  STL: {len(files.wheel_stl) / 1024:.1f} KB")

    # --- Assembly 3MF ---
    if include_assembly and include_3mf and worm is not None and wheel is not None:
        _log("Exporting assembly 3MF...")
        files.assembly_3mf = export_assembly_3mf(
            wheel=wheel,
            worm=worm,
            centre_distance_mm=design.assembly.centre_distance_mm,
            rotation_deg=files.mesh_rotation_deg,
        )
        if files.assembly_3mf:
            _log(f"  Assembly 3MF: {len(files.assembly_3mf) / 1024:.1f} KB")

    # --- Design JSON and Markdown ---
    # Lazy import to avoid circular dependency (io -> calculator -> io)
    from ..calculator.output import to_json, to_markdown

    _log("Generating design.json and design.md...")
    files.design_json = to_json(design, validation=validation)
    files.design_md = to_markdown(design, validation=validation)

    return files


def _package_filename(design: WormGearDesign) -> str:
    """Generate base filename from design parameters.

    Format: wormgear_m{module}_{teeth}-{starts}_{type}
    Matches existing web convention.
    """
    module_str = f"{design.worm.module_mm:.1f}".replace(".", "_")
    teeth = design.wheel.num_teeth
    starts = design.worm.num_starts

    worm_type = design.worm.type
    if worm_type == WormType.GLOBOID:
        type_str = "glob"
    else:
        type_str = "cyl"

    return f"wormgear_m{module_str}_{teeth}-{starts}_{type_str}"


def save_package_to_dir(
    files: PackageFiles,
    output_dir: Path,
    design: WormGearDesign,
) -> list[Path]:
    """Write all PackageFiles to a directory with standard naming.

    Args:
        files: PackageFiles from generate_package().
        output_dir: Directory to write files into (created if needed).
        design: WormGearDesign for context (currently unused but available
            for future filename customisation).

    Returns:
        List of Paths written.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    file_map = {
        "worm.step": files.worm_step,
        "wheel.step": files.wheel_step,
        "worm.3mf": files.worm_3mf,
        "wheel.3mf": files.wheel_3mf,
        "worm.stl": files.worm_stl,
        "wheel.stl": files.wheel_stl,
        "assembly.3mf": files.assembly_3mf,
    }

    for name, data in file_map.items():
        if data is not None:
            path = output_dir / name
            path.write_bytes(data)
            written.append(path)

    if files.design_json is not None:
        path = output_dir / "design.json"
        path.write_text(files.design_json, encoding="utf-8")
        written.append(path)

    if files.design_md is not None:
        path = output_dir / "design.md"
        path.write_text(files.design_md, encoding="utf-8")
        written.append(path)

    return written


def create_package_zip(files: PackageFiles, design: WormGearDesign) -> bytes:
    """Create ZIP archive from PackageFiles.

    ZIP filename base follows the web convention:
    wormgear_m{module}_{teeth}-{starts}_{type}

    Args:
        files: PackageFiles from generate_package().
        design: WormGearDesign for filename generation.

    Returns:
        ZIP file contents as bytes.
    """
    buf = io.BytesIO()

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        file_map = {
            "worm.step": files.worm_step,
            "wheel.step": files.wheel_step,
            "worm.3mf": files.worm_3mf,
            "wheel.3mf": files.wheel_3mf,
            "worm.stl": files.worm_stl,
            "wheel.stl": files.wheel_stl,
            "assembly.3mf": files.assembly_3mf,
        }

        for name, data in file_map.items():
            if data is not None:
                zf.writestr(name, data)

        if files.design_json is not None:
            zf.writestr("design.json", files.design_json)

        if files.design_md is not None:
            zf.writestr("design.md", files.design_md)

    return buf.getvalue()
