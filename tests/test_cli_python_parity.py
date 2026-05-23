"""STEP roundtrip via the BD-style facade.

Prior to the 0.1.0 drop-legacy work, this file held parity tests
between the facade and the legacy ``WormGeometry`` / ``WheelGeometry``
constructors. With legacy slated for removal (#202), those tests
become meaningless — the equivalence they verified is now pinned
directly by ``test_golden_volumes.py`` which goes through the facade.

The remaining valuable test here is the STEP export roundtrip: build
a Part via the facade, export to STEP, re-import, verify the volume
is preserved. This catches OCC serialization issues that aren't
visible to in-memory volume checks.
"""

from __future__ import annotations

import pytest

from wormgear import WormGear

pytestmark = pytest.mark.slow


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
