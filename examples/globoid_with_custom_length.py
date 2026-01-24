"""
Demonstrate globoid worm with custom length and smooth thread ends.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from wormgear_geometry.globoid_worm import GloboidWormGeometry
from wormgear_geometry.io import load_design_json

print("="*70)
print("GLOBOID WORM - CUSTOM LENGTH & SMOOTH THREAD ENDS")
print("="*70)
print()

# Load 7mm design
design = load_design_json("examples/7mm.json")

print("Original auto-calculated length:")
globoid_auto = GloboidWormGeometry(
    params=design.worm,
    assembly_params=design.assembly,
    wheel_pitch_diameter=design.wheel.pitch_diameter_mm,
)
print(f"  Auto-calculated: {globoid_auto.length:.2f}mm")
print()

# Create with custom length
custom_length = 12.0  # mm - specify exact length

print(f"Creating globoid worm with custom length: {custom_length}mm")
print()

globoid_custom = GloboidWormGeometry(
    params=design.worm,
    assembly_params=design.assembly,
    wheel_pitch_diameter=design.wheel.pitch_diameter_mm,
    length=custom_length,  # SPECIFY EXACT LENGTH
)

print(f"Specified length: {custom_length}mm")
print(f"Throat pitch radius: {globoid_custom.throat_pitch_radius:.2f}mm")
print(f"Nominal pitch radius: {globoid_custom.nominal_pitch_radius:.2f}mm")
print()

# Build and export
worm_part = globoid_custom.build()
globoid_custom.export_step("globoid_custom_length_12mm.step")

print()
print("="*70)
print("THREAD END TAPERING")
print("="*70)
print()

lead = design.worm.lead_mm
num_turns = custom_length / lead

print(f"Worm specifications:")
print(f"  Total length: {custom_length:.2f}mm")
print(f"  Lead (pitch): {lead:.3f}mm")
print(f"  Number of turns: {num_turns:.2f}")
print()

print(f"Thread end tapering:")
print(f"  Taper zone length: {lead:.3f}mm (one lead at each end)")
print(f"  Full depth zone: {custom_length - 2*lead:.2f}mm")
print(f"  Taper method: Cosine curve (smooth)")
print()

print("="*70)
print("IMPROVEMENTS")
print("="*70)
print()

print("✓ CUSTOM LENGTH:")
print("  You can now specify the exact worm length you need")
print(f"  Example: length={custom_length}mm creates a {custom_length}mm worm")
print()

print("✓ SMOOTH THREAD ENDS:")
print("  Threads now taper smoothly at both ends instead of ending blockily")
print(f"  Taper zone: {lead:.2f}mm at each end")
print("  Taper function: Cosine curve for smooth appearance")
print("  This is standard practice for worm gears")
print()

print("GENERATED FILE:")
print("  globoid_custom_length_12mm.step")
print()
print("INSPECTION IN CAD:")
print("  - Overall length should be exactly 12.0mm")
print("  - Thread depth should smoothly ramp down at each end")
print("  - Thread should blend smoothly into shaft at ends")
print("  - No blocky/abrupt thread termination")
print()
