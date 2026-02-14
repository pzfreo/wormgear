"""
Shared geometry repair and simplification utilities.

Extracted from WormGeometry._repair_geometry() and
VirtualHobbingWheelGeometry._simplify_geometry() so the logic is reusable
and independently testable.
"""

import logging
import time

from OCP.ShapeFix import ShapeFix_Shape, ShapeFix_Solid
from OCP.ShapeUpgrade import ShapeUpgrade_UnifySameDomain
from OCP.BRepBuilderAPI import BRepBuilderAPI_Sewing, BRepBuilderAPI_MakeSolid
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_SHELL, TopAbs_FACE

from OCP.TopoDS import TopoDS

from build123d import Part, export_step, import_step

logger = logging.getLogger(__name__)


def repair_geometry(part: Part) -> Part:
    """
    Multi-strategy repair for invalid topology after boolean operations.

    Tries four strategies in order, returning as soon as one produces a
    valid solid:

    1. UnifySameDomain — merge coincident faces sharing the same surface.
    2. Sew + MakeSolid — stitch all faces into a shell then build a solid,
       followed by ShapeFix_Solid cleanup.
    3. ShapeFix_Shape — general-purpose shape repair on the unified result.
    4. STEP roundtrip — export then re-import to let the STEP writer/reader
       normalise the topology.

    If all strategies fail the original *part* is returned unchanged.

    Args:
        part: Part to repair.

    Returns:
        Repaired Part (or original if repair fails or is unnecessary).
    """
    if part.is_valid:
        return part

    try:
        shape = part.wrapped if hasattr(part, "wrapped") else part

        # Strategy 1: Unify faces that share the same underlying surface
        unifier = ShapeUpgrade_UnifySameDomain(shape, True, True, True)
        unifier.Build()
        unified = unifier.Shape()

        result = Part(unified)
        if result.is_valid:
            logger.debug("Geometry repair successful (unify)")
            return result

        # Strategy 2: Sew all faces together into a single shell
        sewer = BRepBuilderAPI_Sewing(1e-6)

        explorer = TopExp_Explorer(unified, TopAbs_FACE)
        face_count = 0
        while explorer.More():
            sewer.Add(explorer.Current())
            face_count += 1
            explorer.Next()

        if face_count > 0:
            sewer.Perform()
            sewn = sewer.SewedShape()

            shell_explorer = TopExp_Explorer(sewn, TopAbs_SHELL)
            if shell_explorer.More():
                shell = TopoDS.Shell_s(shell_explorer.Current())
                solid_maker = BRepBuilderAPI_MakeSolid(shell)
                if solid_maker.IsDone():
                    solid = solid_maker.Solid()

                    solid_fixer = ShapeFix_Solid(solid)
                    solid_fixer.Perform()
                    fixed_solid = solid_fixer.Solid()

                    result = Part(fixed_solid)
                    if result.is_valid:
                        logger.debug("Geometry repair successful (sew + solid)")
                        return result

        # Strategy 3: ShapeFix_Shape on the unified shape
        fixer = ShapeFix_Shape(unified)
        fixer.Perform()
        fixed = fixer.Shape()

        result = Part(fixed)
        if result.is_valid:
            logger.debug("Geometry repair successful (ShapeFix)")
            return result

        # Strategy 4: STEP export/reimport roundtrip
        import tempfile
        from pathlib import Path

        with tempfile.NamedTemporaryFile(suffix=".step", delete=False) as f:
            step_path = Path(f.name)

        try:
            export_step(part, str(step_path))
            reimported = import_step(str(step_path))

            if reimported.is_valid:
                logger.debug("Geometry repair successful (STEP roundtrip)")
                return reimported
        finally:
            step_path.unlink(missing_ok=True)

        logger.debug("Geometry repair did not achieve valid solid, using original")
        return part

    except Exception as e:
        logger.debug(f"Geometry repair skipped: {e}")
        return part


def simplify_geometry(part: Part, description: str = "") -> Part:
    """
    Preventive simplification before complex boolean operations.

    Merges coplanar faces (UnifySameDomain) then applies ShapeFix to
    clean up any remaining topology issues.  This reduces the face count
    and makes subsequent boolean operations faster and more reliable.

    Args:
        part: The part to simplify.
        description: Optional label for log messages.

    Returns:
        Simplified Part (or original if simplification fails).
    """
    if description:
        logger.debug(f"Simplifying {description}...")

    simplify_start = time.time()

    try:
        if not isinstance(part, Part):
            if hasattr(part, "wrapped"):
                part = Part(part.wrapped)
            else:
                raise ValueError(f"Cannot simplify object of type {type(part)}")

        unifier = ShapeUpgrade_UnifySameDomain(part.wrapped, True, True, True)
        unifier.Build()
        unified_shape = unifier.Shape()

        fixer = ShapeFix_Shape(unified_shape)
        fixer.Perform()
        fixed_shape = fixer.Shape()

        simplified = Part(fixed_shape)

        simplify_time = time.time() - simplify_start
        if description:
            logger.debug(f"done in {simplify_time:.1f}s")

        return simplified
    except Exception as e:
        simplify_time = time.time() - simplify_start
        logger.warning(f"failed after {simplify_time:.1f}s: {e}, using original")
        return part
