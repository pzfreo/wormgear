#!/usr/bin/env python3
"""
Comparison test: Legacy wormcalc vs Unified wormgear.calculator

Purpose: Identify CRITICAL missing functionality before removing legacy code.
"""

import sys
sys.path.insert(0, 'web')
sys.path.insert(0, 'src')

from wormcalc.core import design_from_module as legacy_design
from wormcalc.output import to_summary as legacy_summary, to_json as legacy_json
from wormgear.calculator import design_from_module as unified_design
from wormgear.calculator import to_summary as unified_summary, to_json as unified_json

def compare_designs():
    """Compare critical dimensions and outputs"""
    print("="*70)
    print("LEGACY vs UNIFIED CALCULATOR COMPARISON")
    print("="*70)

    # Test case: module 2.0, ratio 30
    params = {"module": 2.0, "ratio": 30}

    print(f"\nTest parameters: {params}")

    # Calculate both
    print("\n[1/2] Calculating with legacy wormcalc...")
    legacy = legacy_design(**params)

    print("[2/2] Calculating with unified wormgear.calculator...")
    unified = unified_design(**params)

    # Compare critical dimensions
    print("\n" + "="*70)
    print("CRITICAL DIMENSION COMPARISON")
    print("="*70)

    comparisons = [
        ("Worm Pitch Diameter", legacy.worm.pitch_diameter, unified["worm"]["pitch_diameter_mm"]),
        ("Worm Tip Diameter", legacy.worm.tip_diameter, unified["worm"]["tip_diameter_mm"]),
        ("Worm Root Diameter", legacy.worm.root_diameter, unified["worm"]["root_diameter_mm"]),
        ("Worm Lead", legacy.worm.lead, unified["worm"]["lead_mm"]),
        ("Worm Lead Angle", legacy.worm.lead_angle, unified["worm"]["lead_angle_deg"]),
        ("Wheel Pitch Diameter", legacy.wheel.pitch_diameter, unified["wheel"]["pitch_diameter_mm"]),
        ("Wheel Tip Diameter", legacy.wheel.tip_diameter, unified["wheel"]["tip_diameter_mm"]),
        ("Wheel Root Diameter", legacy.wheel.root_diameter, unified["wheel"]["root_diameter_mm"]),
        ("Wheel Throat Diameter", legacy.wheel.throat_diameter, unified["wheel"]["throat_diameter_mm"]),
        ("Centre Distance", legacy.centre_distance, unified["assembly"]["centre_distance_mm"]),
        ("Pressure Angle", legacy.pressure_angle, unified["assembly"]["pressure_angle_deg"]),
    ]

    all_match = True
    tolerance = 0.01  # 0.01mm tolerance

    for name, legacy_val, unified_val in comparisons:
        match = abs(legacy_val - unified_val) < tolerance
        status = "✓" if match else "✗"
        print(f"{status} {name:25s}: Legacy={legacy_val:8.3f}  Unified={unified_val:8.3f}  Diff={abs(legacy_val - unified_val):.4f}")
        if not match:
            all_match = False

    # Compare summaries
    print("\n" + "="*70)
    print("LEGACY SUMMARY OUTPUT")
    print("="*70)
    legacy_sum = legacy_summary(legacy)
    print(legacy_sum)

    print("\n" + "="*70)
    print("UNIFIED SUMMARY OUTPUT")
    print("="*70)
    unified_sum = unified_summary(unified)
    print(unified_sum)

    # Compare JSON structure
    print("\n" + "="*70)
    print("JSON STRUCTURE COMPARISON")
    print("="*70)

    import json

    legacy_j_str = legacy_json(legacy)
    unified_j_str = unified_json(unified)

    # Parse JSON strings to dicts
    legacy_j = json.loads(legacy_j_str)
    unified_j = json.loads(unified_j_str)

    print(f"Legacy JSON keys:  {list(legacy_j.keys())}")
    print(f"Unified JSON keys: {list(unified_j.keys())}")

    # Check if unified has all legacy top-level keys
    legacy_keys = set(legacy_j.keys())
    unified_keys = set(unified_j.keys())
    missing_keys = legacy_keys - unified_keys
    extra_keys = unified_keys - legacy_keys

    if missing_keys:
        print(f"\n⚠ Missing keys in unified: {missing_keys}")
    if extra_keys:
        print(f"\n✓ Extra keys in unified: {extra_keys}")

    # Final verdict
    print("\n" + "="*70)
    print("VERDICT")
    print("="*70)

    if all_match:
        print("✓ All critical dimensions MATCH (within 0.01mm tolerance)")
        print("✓ Unified calculator produces correct results")
    else:
        print("✗ MISMATCH detected in critical dimensions")
        print("✗ Unified calculator needs fixes before replacing legacy")

    # Summary length comparison
    print(f"\nLegacy summary:  {len(legacy_sum)} chars, JSON: {len(legacy_j_str)} chars")
    print(f"Unified summary: {len(unified_sum)} chars, JSON: {len(unified_j_str)} chars")

    return all_match

if __name__ == "__main__":
    try:
        match = compare_designs()
        sys.exit(0 if match else 1)
    except Exception as e:
        print(f"\n✗ ERROR during comparison: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
