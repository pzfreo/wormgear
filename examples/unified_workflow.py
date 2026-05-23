"""Unified Workflow Example — wormgear package (BD-style facade).

Demonstrates the four headline entry points:

  - ``WormGear`` / ``WormWheel``    — direct construction from engineering params
  - ``make_pair``                   — one-liner matched pair
  - ``WormGear.from_design``        — adapter for calculator output (or JSON)
  - ``check_mesh``                  — kinematic compatibility verification

For the calculator + validation + JSON IO workflow (which produces the
``WormGearDesign`` that ``from_design`` consumes), see the imports
from ``wormgear.calculator`` and ``wormgear.io``.
"""

from build123d import export_step

from wormgear import WormGear, WormWheel, check_mesh, make_pair
from wormgear.calculator import calculate_design_from_module, validate_design
from wormgear.core import BoreFeature, KeywayFeature
from wormgear.io import load_design_json, save_design_json


def headline_three_lines():
    """The fast path: three lines, no JSON, no calculator in sight."""
    print("=" * 60)
    print("1. Headline three-liner")
    print("=" * 60)

    worm = WormGear(module=2.0, num_starts=1, length=40)
    wheel = WormWheel(module=2.0, num_teeth=30)

    export_step(worm, "/tmp/worm.step")
    export_step(wheel, "/tmp/wheel.step")
    print(f"   ✓ worm:  {worm.volume:.2f} mm³ → /tmp/worm.step")
    print(f"   ✓ wheel: {wheel.volume:.2f} mm³ → /tmp/wheel.step")


def one_liner_pair():
    """make_pair builds a matched pair in one call."""
    print("\n" + "=" * 60)
    print("2. One-liner matched pair")
    print("=" * 60)

    worm, wheel = make_pair(module=2.0, ratio=30, length=40)

    report = check_mesh(worm._params, wheel._params, worm._assembly_params)
    print(f"   ✓ check_mesh.ok = {report.ok}")
    print(f"   ✓ ratio = {report.ratio}, centre distance = {report.centre_distance_mm:.2f} mm")


def calculator_then_facade():
    """When you want DIN-3975 analysis up front."""
    print("\n" + "=" * 60)
    print("3. Calculator → validate → from_design")
    print("=" * 60)

    design = calculate_design_from_module(
        module=2.0,
        ratio=30,
        target_lead_angle=7.0,
        pressure_angle=20.0,
        backlash=0.05,
        profile="ZA",
    )
    print(f"   ✓ Designed: {design.wheel.num_teeth}-tooth wheel at "
          f"{design.assembly.centre_distance_mm:.2f}mm centre distance, "
          f"{design.assembly.efficiency_percent:.1f}% efficiency")

    result = validate_design(design)
    print(f"   ✓ Validation: {len(result.errors)} errors, "
          f"{len(result.warnings)} warnings")

    # Save / load to demonstrate the JSON round-trip
    save_design_json(design, "/tmp/design.json")
    loaded = load_design_json("/tmp/design.json")

    worm = WormGear.from_design(loaded, length=40,
                                bore=BoreFeature(diameter=8.0),
                                keyway=KeywayFeature())
    wheel = WormWheel.from_design(loaded,
                                  bore=BoreFeature(diameter=12.0),
                                  keyway=KeywayFeature())
    print(f"   ✓ worm with bore + keyway: {worm.volume:.2f} mm³")
    print(f"   ✓ wheel with bore + keyway: {wheel.volume:.2f} mm³")


if __name__ == "__main__":
    headline_three_lines()
    one_liner_pair()
    calculator_then_facade()
    print("\n" + "=" * 60)
    print("✅ Examples complete.")
    print("=" * 60)
