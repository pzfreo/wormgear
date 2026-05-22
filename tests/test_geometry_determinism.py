"""Geometry determinism — Phase 0 regression net.

These tests guard against silent non-determinism in geometry generation.
If two builds of the same design produce different volumes, golden-volume
tests would become flaky and trustworthy regression detection becomes
impossible.

Two scopes are checked:

  1. **In-process determinism**: build the same design twice within a single
     Python process. Catches issues with caching, mutable globals, or random
     seeds.
  2. **Cross-process determinism**: build the same design in two separate
     subprocesses. Catches issues with state that survives between calls
     within a process (e.g. lazily initialised OCC state).

Tolerance is 0.001 % (10× tighter than the golden-volume tolerance) — if
determinism drift is detectable above that floor, the golden tests aren't
worth pinning.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.slow

DETERMINISM_TOL = 1e-5  # 0.001 %

# Single representative design — we don't need every golden design here.
# The point is to verify the builder is deterministic, not to scan the matrix.
DESIGN_KWARGS = dict(module=1.0, ratio=20, num_starts=1, profile="ZA")
WORM_LENGTH = 20.0
WHEEL_FACE_WIDTH = 6.0
SECTIONS_PER_TURN = 12


def _build_and_measure() -> dict[str, float]:
    """Build worm + wheel for the canonical design; return volumes."""
    from wormgear.calculator import calculate_design_from_module
    from wormgear.core import WheelGeometry, WormGeometry

    design = calculate_design_from_module(**DESIGN_KWARGS)
    worm = WormGeometry(
        params=design.worm,
        assembly_params=design.assembly,
        length=WORM_LENGTH,
        sections_per_turn=SECTIONS_PER_TURN,
    ).build()
    wheel = WheelGeometry(
        params=design.wheel,
        worm_params=design.worm,
        assembly_params=design.assembly,
        face_width=WHEEL_FACE_WIDTH,
    ).build()
    return {"worm_volume": float(worm.volume), "wheel_volume": float(wheel.volume)}


def test_in_process_determinism():
    """Two builds of the same design in one process produce identical volumes."""
    first = _build_and_measure()
    second = _build_and_measure()

    for key in ("worm_volume", "wheel_volume"):
        a, b = first[key], second[key]
        rel = abs(a - b) / a
        assert rel < DETERMINISM_TOL, (
            f"In-process {key} not deterministic: "
            f"{a:.6f} vs {b:.6f} (rel diff {rel:.2e}). "
            f"Goldens cannot be trusted until this is fixed."
        )


def test_cross_process_determinism():
    """Building the same design in two subprocesses produces identical volumes."""
    code = (
        "import json, sys\n"
        "sys.path.insert(0, %r)\n"
        "from tests.test_geometry_determinism import _build_and_measure\n"
        "print(json.dumps(_build_and_measure()))\n"
    ) % str(Path(__file__).parent.parent)

    def run_subprocess() -> dict[str, float]:
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=300,
        )
        assert result.returncode == 0, (
            f"Subprocess build failed.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
        # Parse the last JSON line (build123d may emit warnings before it)
        lines = [line for line in result.stdout.strip().splitlines() if line.startswith("{")]
        assert lines, f"No JSON output from subprocess. stdout: {result.stdout}"
        return json.loads(lines[-1])

    first = run_subprocess()
    second = run_subprocess()

    for key in ("worm_volume", "wheel_volume"):
        a, b = first[key], second[key]
        rel = abs(a - b) / a
        assert rel < DETERMINISM_TOL, (
            f"Cross-process {key} not deterministic: "
            f"{a:.6f} vs {b:.6f} (rel diff {rel:.2e}). "
            f"State is leaking between builds; golden tests will be flaky."
        )
