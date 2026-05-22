"""Golden geometric values — Phase 0 regression net.

These tests pin the **exact** geometric output of the current geometry
constructors so that any future refactor (notably the #191 BD-friendly API
restructure) catches silent drift in derived geometry. The standard test
suite asserts ``is_valid``, ``volume > 0``, and a loose bounding-box check —
that lets two semantically different geometries pass undetected. Goldens
close that gap.

For each canonical design we pin:

  * ``volume``     — within 0.1 %  (catches dimensional drift)
  * ``bbox``       — within 0.01 mm on every axis (catches positioning drift)
  * ``face_count`` — exact match (cheap topology check; catches structural
                     changes that preserve volume)

Why this matters
----------------
A change to default rounding, profile derivation, or section count could
preserve "valid + roughly correct" while shifting the geometry by 0.5 %.
Users would notice over time as gears stop meshing; golden tests catch it
in CI on the same PR.

Why the values can drift
------------------------
Two legitimate sources of change:

  1. **Intentional geometry changes.** Caught at code-review time — anyone
     changing the goldens should justify the diff in the PR.
  2. **build123d version bump.** OCC computes volumes from B-rep, and minor
     OCC kernel changes can shift values by ~0.01 %. The face count is
     more stable but not immune.

Regenerating values
-------------------
When a change is justified, regenerate values:

    uv run --extra dev python scripts/record_golden_volumes.py

Then paste the output into ``GOLDEN_VALUES`` and review the diff line by
line. Any volume change > 0.1 % or any face-count change should be
explained in the commit message.

``sections_per_turn`` is pinned explicitly in every spec because the
discrete approximation of the helical thread is sensitive to it (see #189
investigation): two builds with different ``sections_per_turn`` values
produce visibly different volumes even though both are "valid".
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from wormgear.calculator import (
    calculate_design_from_module,
)
from wormgear.core import (
    BoreFeature,
    GloboidWormGeometry,
    KeywayFeature,
    WheelGeometry,
    WormGeometry,
)

pytestmark = pytest.mark.slow


# ---------------------------------------------------------------------------
# Tolerances
# ---------------------------------------------------------------------------

VOLUME_TOL = 0.001  # 0.1 % relative
BBOX_TOL_MM = 0.01  # 0.01 mm absolute on each axis

# ---------------------------------------------------------------------------
# Design matrix
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DesignSpec:
    """A canonical design + how to build worm and wheel from it."""

    module: float
    ratio: int
    num_starts: int = 1
    profile: str = "ZA"
    hand: str = "right"
    target_lead_angle: float | None = None
    globoid: bool = False
    throated_wheel: bool = False
    worm_length: float = 20.0
    wheel_face_width: float = 6.0
    sections_per_turn: int = 12  # pinned explicitly; see module docstring
    worm_bore: float | None = None
    wheel_bore: float | None = None
    keyways: bool = False


GOLDEN_DESIGNS: dict[str, DesignSpec] = {
    # Small-module cylindrical, ZA, right hand. The luthier baseline.
    "small_za_rh": DesignSpec(
        module=0.5,
        ratio=12,
        worm_length=8.0,
        wheel_face_width=2.5,
    ),
    # Medium-module cylindrical, ZA, right hand. The generic baseline.
    "medium_za_rh": DesignSpec(
        module=1.0,
        ratio=20,
        worm_length=20.0,
        wheel_face_width=6.0,
    ),
    # Medium-module cylindrical, ZK profile. The 3D-printing path.
    "medium_zk_rh": DesignSpec(
        module=1.0,
        ratio=20,
        profile="ZK",
        worm_length=20.0,
        wheel_face_width=6.0,
    ),
    # Large-module multi-start. Exercises non-default num_starts.
    "large_za_multistart": DesignSpec(
        module=2.0,
        ratio=30,
        num_starts=2,
        worm_length=30.0,
        wheel_face_width=10.0,
    ),
    # Left-hand variant. Catches sign-of-helix bugs.
    "medium_za_lh": DesignSpec(
        module=1.0,
        ratio=20,
        hand="left",
        worm_length=20.0,
        wheel_face_width=6.0,
    ),
    # Throated wheel (helical wheel with extra throat cut for worm engagement).
    "medium_za_throated": DesignSpec(
        module=1.0,
        ratio=20,
        throated_wheel=True,
        worm_length=20.0,
        wheel_face_width=6.0,
    ),
    # Globoid (hourglass) worm. Different worm geometry entirely.
    "medium_za_globoid": DesignSpec(
        module=1.0,
        ratio=20,
        globoid=True,
        worm_length=20.0,
        wheel_face_width=6.0,
    ),
    # With bore + keyway. Exercises the feature composition path.
    # worm_bore must be >= 6 mm for DIN 6885 keyways; 6 mm is the smallest
    # standard shaft + key combination.
    "medium_za_with_features": DesignSpec(
        module=1.0,
        ratio=20,
        worm_bore=6.0,
        wheel_bore=8.0,
        keyways=True,
        worm_length=20.0,
        wheel_face_width=6.0,
    ),
}


# ---------------------------------------------------------------------------
# Recorded values — see scripts/record_golden_volumes.py to regenerate
# ---------------------------------------------------------------------------

GOLDEN_VALUES: dict[str, dict[str, dict[str, Any]]] = {
    "small_za_rh": {
        "worm": {"volume": 105.9443, "bbox": (-2.5361, 2.5361, -2.5361, 2.5361, -4.0, 4.0), "face_count": 12},
        "wheel": {"volume": 67.9806, "bbox": (-3.4806, 3.4806, -3.4806, 3.4806, -1.25, 1.25), "face_count": 194},
    },
    "medium_za_rh": {
        "worm": {"volume": 1059.4515, "bbox": (-5.0722, 5.0722, -5.0722, 5.0722, -10.0, 10.0), "face_count": 13},
        "wheel": {"volume": 1858.6244, "bbox": (-10.9775, 10.9775, -10.9775, 10.9775, -3.0, 3.0), "face_count": 442},
    },
    "medium_zk_rh": {
        "worm": {"volume": 1093.6076, "bbox": (-5.0722, 5.0722, -5.0722, 5.0722, -10.0, 10.0), "face_count": 13},
        "wheel": {"volume": 1830.3195, "bbox": (-10.9759, 10.9759, -10.9759, 10.9759, -3.0, 3.0), "face_count": 442},
    },
    "large_za_multistart": {
        "worm": {"volume": 5649.3542, "bbox": (-18.7912, 18.7912, -18.7911, 18.7912, -15.0, 30.0286), "face_count": 15},
        "wheel": {"volume": 112550.7135, "bbox": (-61.979, 61.979, -61.979, 61.979, -5.0, 5.0), "face_count": 1322},
    },
    "medium_za_lh": {
        "worm": {"volume": 1059.4503, "bbox": (-5.0722, 5.0722, -5.0722, 5.0722, -10.0, 10.0), "face_count": 13},
        "wheel": {"volume": 1858.6244, "bbox": (-10.9775, 10.9775, -10.9775, 10.9775, -3.0, 3.0), "face_count": 442},
    },
    "medium_za_throated": {
        "worm": {"volume": 1059.4515, "bbox": (-5.0722, 5.0722, -5.0722, 5.0722, -10.0, 10.0), "face_count": 13},
        "wheel": {"volume": 1994.8995, "bbox": (-10.9835, 10.9835, -10.9835, 10.9835, -3.0, 3.0), "face_count": 442},
    },
    "medium_za_globoid": {
        "worm": {"volume": 988.5182, "bbox": (-5.0542, 5.0614, -5.047, 5.0603, -10.0, 10.0), "face_count": 261},
        "wheel": {"volume": 1818.8309, "bbox": (-10.9775, 10.9775, -10.9775, 10.9775, -3.0, 3.0), "face_count": 1062},
    },
    "medium_za_with_features": {
        "worm": {"volume": 478.3458, "bbox": (-5.0722, 5.0722, -5.0722, 5.0722, -10.0, 10.0), "face_count": 41},
        "wheel": {"volume": 1530.1065, "bbox": (-10.9775, 10.9775, -10.9775, 10.9775, -3.0, 3.0), "face_count": 446},
    },
}


# ---------------------------------------------------------------------------
# Build + measure helpers (used by both the tests and the recorder)
# ---------------------------------------------------------------------------


def build_pair(spec: DesignSpec):
    """Build the worm and wheel for a DesignSpec, returning (worm, wheel) parts."""
    extra: dict[str, Any] = {}
    if spec.target_lead_angle is not None:
        extra["target_lead_angle"] = spec.target_lead_angle
    design = calculate_design_from_module(
        module=spec.module,
        ratio=spec.ratio,
        num_starts=spec.num_starts,
        hand=spec.hand,
        profile=spec.profile,
        globoid=spec.globoid,
        **extra,
    )

    worm_bore = (
        BoreFeature(diameter=spec.worm_bore) if spec.worm_bore is not None else None
    )
    wheel_bore = (
        BoreFeature(diameter=spec.wheel_bore) if spec.wheel_bore is not None else None
    )
    worm_keyway = KeywayFeature() if spec.keyways and worm_bore is not None else None
    wheel_keyway = KeywayFeature() if spec.keyways and wheel_bore is not None else None

    if spec.globoid:
        worm_geo = GloboidWormGeometry(
            params=design.worm,
            assembly_params=design.assembly,
            wheel_pitch_diameter=design.wheel.pitch_diameter_mm,
            length=spec.worm_length,
            sections_per_turn=spec.sections_per_turn,
            profile=spec.profile,
            bore=worm_bore,
            keyway=worm_keyway,
        )
    else:
        worm_geo = WormGeometry(
            params=design.worm,
            assembly_params=design.assembly,
            length=spec.worm_length,
            sections_per_turn=spec.sections_per_turn,
            profile=spec.profile,
            bore=worm_bore,
            keyway=worm_keyway,
        )
    worm = worm_geo.build()

    wheel_geo = WheelGeometry(
        params=design.wheel,
        worm_params=design.worm,
        assembly_params=design.assembly,
        face_width=spec.wheel_face_width,
        profile=spec.profile,
        throated=spec.throated_wheel,
        bore=wheel_bore,
        keyway=wheel_keyway,
    )
    wheel = wheel_geo.build()
    return worm, wheel


def measure(part) -> dict[str, Any]:
    """Return ``{volume, bbox, face_count}`` for a built Part.

    ``bbox`` is a tuple of (min_x, max_x, min_y, max_y, min_z, max_z) in mm,
    rounded to 4 decimal places to keep the recorded literal readable while
    still being well below the 0.01 mm tolerance the tests assert against.
    """
    bbox = part.bounding_box()
    return {
        "volume": round(float(part.volume), 4),
        "bbox": (
            round(float(bbox.min.X), 4),
            round(float(bbox.max.X), 4),
            round(float(bbox.min.Y), 4),
            round(float(bbox.max.Y), 4),
            round(float(bbox.min.Z), 4),
            round(float(bbox.max.Z), 4),
        ),
        "face_count": len(part.faces()),
    }


# ---------------------------------------------------------------------------
# Assertions used in the tests
# ---------------------------------------------------------------------------


def _assert_matches(name: str, side: str, actual: dict[str, Any], golden: dict[str, Any]) -> None:
    """Assert measured values are within tolerance of the golden values."""
    actual_vol = actual["volume"]
    golden_vol = golden["volume"]
    rel = abs(actual_vol - golden_vol) / golden_vol
    assert rel < VOLUME_TOL, (
        f"{name}/{side}: volume drifted {rel:.4%} "
        f"(actual={actual_vol:.4f}, golden={golden_vol:.4f}). "
        f"If intentional, regenerate via scripts/record_golden_volumes.py "
        f"and document the change."
    )

    for i, axis in enumerate(("min_x", "max_x", "min_y", "max_y", "min_z", "max_z")):
        actual_v = actual["bbox"][i]
        golden_v = golden["bbox"][i]
        assert abs(actual_v - golden_v) < BBOX_TOL_MM, (
            f"{name}/{side}: bbox {axis} drifted "
            f"(actual={actual_v:.4f}, golden={golden_v:.4f})"
        )

    assert actual["face_count"] == golden["face_count"], (
        f"{name}/{side}: face count changed "
        f"(actual={actual['face_count']}, golden={golden['face_count']}). "
        f"Topology changed; investigate before regenerating."
    )


# ---------------------------------------------------------------------------
# The tests themselves — one per design, generated from GOLDEN_DESIGNS
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name,spec",
    list(GOLDEN_DESIGNS.items()),
    ids=list(GOLDEN_DESIGNS.keys()),
)
def test_golden_design(name: str, spec: DesignSpec) -> None:
    """Build the design and assert its measurements match the recorded goldens."""
    if name not in GOLDEN_VALUES:
        pytest.skip(
            f"No recorded golden values for {name!r}. "
            f"Run scripts/record_golden_volumes.py to capture initial values."
        )

    worm, wheel = build_pair(spec)
    worm_meas = measure(worm)
    wheel_meas = measure(wheel)

    _assert_matches(name, "worm", worm_meas, GOLDEN_VALUES[name]["worm"])
    _assert_matches(name, "wheel", wheel_meas, GOLDEN_VALUES[name]["wheel"])
