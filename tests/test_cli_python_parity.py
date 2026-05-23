"""CLI ↔ Python facade parity (Phase 4 of #191).

Verifies that:
  1. The JSON-deserialization channel produces identical geometry through
     the Python facade vs the CLI's underlying ``WormGeometry`` path.
  2. STEP roundtrip preserves volume (already pinned in conftest but
     repeated here for the facade path).

A direct CLI subprocess test exists in ``tests/test_cli.py``; this file
verifies the geometric equivalence of the two code paths without
relying on subprocess overhead, which is environment-sensitive.
"""

from __future__ import annotations

import pytest

from wormgear import WormGear, WormWheel
from wormgear.core import WheelGeometry, WormGeometry
from wormgear.io import load_design_json

pytestmark = pytest.mark.slow


EQUIVALENCE_TOL = 1e-6


@pytest.fixture
def design_json(tmp_path):
    """Write a calculator-produced design JSON; return the path.

    Uses ``design_from_module`` + ``save_design_json`` to produce a JSON
    that is internally consistent with the calculator's derivation. Tests
    the realistic round-trip path: web/CLI calculator produces JSON, then
    the Python facade (or the CLI's internal geometry) consumes it.
    """
    from wormgear.calculator import design_from_module
    from wormgear.io import save_design_json

    design = design_from_module(module=1.0, ratio=20)
    json_path = tmp_path / "design.json"
    save_design_json(design, json_path)
    return json_path


# ---------------------------------------------------------------------------
# JSON load → facade.from_design parity with JSON load → WormGeometry
# ---------------------------------------------------------------------------


def test_worm_load_then_facade_matches_load_then_geometry(design_json):
    """``load_design_json() → WormGear.from_design()`` equals
    ``load_design_json() → WormGeometry()`` for the worm."""
    design = load_design_json(design_json)

    # Path A: Python facade adapter
    worm_facade = WormGear.from_design(
        design, length=15.0, sections_per_turn=12,
    )

    # Path B: direct (what the CLI actually does internally)
    worm_direct = WormGeometry(
        params=design.worm,
        assembly_params=design.assembly,
        length=15.0,
        sections_per_turn=12,
        profile="ZA",
    ).build()

    rel = abs(worm_facade.volume - worm_direct.volume) / worm_direct.volume
    assert rel < EQUIVALENCE_TOL, (
        f"Worm volume drift via facade vs direct: "
        f"facade={worm_facade.volume:.4f}, direct={worm_direct.volume:.4f}, "
        f"rel={rel:.2e}"
    )


def test_wheel_load_then_facade_matches_load_then_geometry(design_json):
    """Same parity check for the wheel."""
    design = load_design_json(design_json)

    wheel_facade = WormWheel.from_design(design, face_width=5.0)
    wheel_direct = WheelGeometry(
        params=design.wheel,
        worm_params=design.worm,
        assembly_params=design.assembly,
        face_width=5.0,
        profile="ZA",
    ).build()

    rel = abs(wheel_facade.volume - wheel_direct.volume) / wheel_direct.volume
    assert rel < EQUIVALENCE_TOL, (
        f"Wheel volume drift via facade vs direct: "
        f"facade={wheel_facade.volume:.4f}, direct={wheel_direct.volume:.4f}, "
        f"rel={rel:.2e}"
    )


# ---------------------------------------------------------------------------
# STEP roundtrip via the facade
# ---------------------------------------------------------------------------


def test_facade_step_roundtrip(tmp_path):
    """A facade-built part exports to STEP and reimports within 1% volume."""
    from build123d import export_step, import_step

    worm = WormGear(module=1.0, length=15.0, sections_per_turn=12)
    step_path = tmp_path / "worm.step"
    export_step(worm, str(step_path))
    assert step_path.exists()
    assert step_path.stat().st_size > 100

    reimported = import_step(str(step_path))
    rel = abs(reimported.volume - worm.volume) / worm.volume
    assert rel < 0.01, f"STEP roundtrip drift: {rel:.3%}"
