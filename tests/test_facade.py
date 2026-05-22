"""Tests for the BD-style facade (Phase 2 of #191).

Verifies that ``WormGear`` and ``WormWheel``:
  1. Subclass ``build123d.BasePartObject`` so ``isinstance(x, Part)`` works
     (#187 — bd_warehouse convention)
  2. Produce **identical geometry** to the existing ``WormGeometry`` /
     ``WheelGeometry`` constructors for the same engineering inputs
     (Phase 0 goldens guarantee no drift if equivalence holds)
  3. Expose the engineering inputs as attributes for introspection
     (downstream ``check_mesh`` and Phase 3 ``from_design`` rely on this)

Layer rule: this test file builds geometry, so it's marked ``slow``.
"""

from __future__ import annotations

import pytest
from build123d import Part

from wormgear import WormGear, WormWheel
from wormgear.calculator import calculate_design_from_module
from wormgear.core import WheelGeometry, WormGeometry

pytestmark = pytest.mark.slow


# Equivalence tolerance — the facade should produce *identical* geometry
# to the underlying constructor; we allow a token amount of float wobble.
EQUIVALENCE_TOL = 1e-6


# ---------------------------------------------------------------------------
# isinstance / subclass invariants
# ---------------------------------------------------------------------------


class TestPartSubclassing:
    """WormGear / WormWheel must be usable wherever a build123d Part is."""

    def test_worm_gear_is_part(self):
        worm = WormGear(module=1.0, length=20.0, sections_per_turn=12)
        assert isinstance(worm, Part), (
            "WormGear must subclass build123d.Part for bd_warehouse compatibility"
        )

    def test_worm_wheel_is_part(self):
        wheel = WormWheel(module=1.0, num_teeth=20, face_width=6.0)
        assert isinstance(wheel, Part)

    def test_worm_gear_is_valid_solid(self):
        worm = WormGear(module=1.0, length=20.0, sections_per_turn=12)
        assert worm.is_valid
        assert worm.volume > 0

    def test_worm_wheel_is_valid_solid(self):
        wheel = WormWheel(module=1.0, num_teeth=20, face_width=6.0)
        assert wheel.is_valid
        assert wheel.volume > 0


# ---------------------------------------------------------------------------
# Equivalence to the underlying geometry classes
# ---------------------------------------------------------------------------


EQUIVALENCE_MATRIX = [
    # (label, kwargs for design_from_module, worm_length, wheel_face_width)
    ("medium_za_rh", {"module": 1.0, "ratio": 20}, 20.0, 6.0),
    ("medium_zk_rh", {"module": 1.0, "ratio": 20, "profile": "ZK"}, 20.0, 6.0),
    ("large_multi", {"module": 2.0, "ratio": 30, "num_starts": 2}, 30.0, 10.0),
    ("medium_lh", {"module": 1.0, "ratio": 20, "hand": "left"}, 20.0, 6.0),
]


@pytest.mark.parametrize(
    "label,design_kwargs,length,face_width",
    EQUIVALENCE_MATRIX,
    ids=[x[0] for x in EQUIVALENCE_MATRIX],
)
def test_worm_gear_equivalent_to_worm_geometry(label, design_kwargs, length, face_width):
    """WormGear(...) must produce identical geometry to WormGeometry(...).

    Mirrors the inputs through the calculator (which both paths use) to
    confirm no drift between the BD-style constructor and the existing one.
    """
    design = calculate_design_from_module(**design_kwargs)

    # The facade extracts what it needs from these kwargs
    new_worm = WormGear(
        module=design.worm.module_mm,
        num_starts=design.worm.num_starts,
        length=length,
        target_lead_angle=design.worm.lead_angle_deg,
        hand=design.worm.hand,
        profile=design_kwargs.get("profile", "ZA"),
        pressure_angle=design.assembly.pressure_angle_deg,
        sections_per_turn=12,
    )

    # The reference: existing WormGeometry built from the same design
    old_worm = WormGeometry(
        params=design.worm,
        assembly_params=design.assembly,
        length=length,
        sections_per_turn=12,
        profile=design_kwargs.get("profile", "ZA"),
    ).build()

    rel = abs(new_worm.volume - old_worm.volume) / old_worm.volume
    assert rel < EQUIVALENCE_TOL, (
        f"{label}: WormGear volume drifted from WormGeometry: "
        f"new={new_worm.volume:.4f}, old={old_worm.volume:.4f}, rel={rel:.2e}"
    )


@pytest.mark.parametrize(
    "label,design_kwargs,length,face_width",
    EQUIVALENCE_MATRIX,
    ids=[x[0] for x in EQUIVALENCE_MATRIX],
)
def test_worm_wheel_equivalent_to_wheel_geometry(label, design_kwargs, length, face_width):
    """WormWheel(...) must produce identical geometry to WheelGeometry(...)."""
    design = calculate_design_from_module(**design_kwargs)

    new_wheel = WormWheel(
        module=design.wheel.module_mm,
        num_teeth=design.wheel.num_teeth,
        face_width=face_width,
        worm_num_starts=design.worm.num_starts,
        worm_target_lead_angle=design.worm.lead_angle_deg,
        hand=design.assembly.hand,
        profile=design_kwargs.get("profile", "ZA"),
        pressure_angle=design.assembly.pressure_angle_deg,
    )

    old_wheel = WheelGeometry(
        params=design.wheel,
        worm_params=design.worm,
        assembly_params=design.assembly,
        face_width=face_width,
        profile=design_kwargs.get("profile", "ZA"),
    ).build()

    rel = abs(new_wheel.volume - old_wheel.volume) / old_wheel.volume
    assert rel < EQUIVALENCE_TOL, (
        f"{label}: WormWheel volume drifted from WheelGeometry: "
        f"new={new_wheel.volume:.4f}, old={old_wheel.volume:.4f}, rel={rel:.2e}"
    )


# ---------------------------------------------------------------------------
# Default-value pinning — capture defaults so future regressions are noisy
# ---------------------------------------------------------------------------


class TestDefaultValuePinning:
    """If defaults silently change, these will fail loudly."""

    def test_worm_gear_default_volume(self):
        """WormGear(module=1, length=20) at sections=12 has known volume."""
        worm = WormGear(module=1.0, length=20.0, sections_per_turn=12)
        # This matches medium_za_rh worm golden from Phase 0
        assert abs(worm.volume - 1059.4515) / 1059.4515 < 0.001, (
            f"Default-config WormGear volume drifted: {worm.volume:.4f}"
        )

    def test_worm_wheel_default_volume(self):
        """WormWheel(module=1, num_teeth=20, face_width=6) has known volume."""
        wheel = WormWheel(module=1.0, num_teeth=20, face_width=6.0)
        # This matches medium_za_rh wheel golden from Phase 0
        assert abs(wheel.volume - 1858.6244) / 1858.6244 < 0.001, (
            f"Default-config WormWheel volume drifted: {wheel.volume:.4f}"
        )


# ---------------------------------------------------------------------------
# Introspection attributes — required for Phase 3 from_design / check_mesh
# ---------------------------------------------------------------------------


class TestIntrospectionAttributes:
    """The facade must expose enough internal state for downstream tooling."""

    def test_worm_gear_exposes_module_and_starts(self):
        worm = WormGear(module=2.0, num_starts=3, length=20.0, sections_per_turn=12)
        assert worm.module == 2.0
        assert worm.num_starts == 3

    def test_worm_gear_exposes_params(self):
        """Internal Pydantic params accessible for check_mesh handoff."""
        worm = WormGear(module=1.0, length=20.0, sections_per_turn=12)
        assert hasattr(worm, "_params")
        assert worm._params.module_mm == 1.0

    def test_worm_wheel_exposes_module_and_num_teeth(self):
        wheel = WormWheel(module=1.5, num_teeth=25, face_width=6.0)
        assert wheel.module == 1.5
        assert wheel.num_teeth == 25

    def test_worm_wheel_exposes_params(self):
        wheel = WormWheel(module=1.0, num_teeth=20, face_width=6.0)
        assert hasattr(wheel, "_params")
        assert wheel._params.module_mm == 1.0
        assert wheel._params.num_teeth == 20
