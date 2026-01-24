"""
Compare cylindrical vs globoid worm geometry.
Generates both types with identical parameters for visual comparison.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from wormgear_geometry.worm import WormGeometry
from wormgear_geometry.globoid_worm import GloboidWormGeometry
from wormgear_geometry.io import WormParams, AssemblyParams

print("="*70)
print("CYLINDRICAL vs GLOBOID WORM COMPARISON")
print("="*70)
print()

# Shared parameters - module 1.5, single start
worm_params = WormParams(
    module_mm=1.5,
    num_starts=1,
    pitch_diameter_mm=12.0,
    tip_diameter_mm=15.0,
    root_diameter_mm=8.5,
    lead_mm=4.712,
    lead_angle_deg=11.0,
    addendum_mm=1.5,
    dedendum_mm=1.875,
    thread_thickness_mm=2.356,
    hand="RIGHT",
    profile_shift=0.0
)

assembly_params = AssemblyParams(
    centre_distance_mm=30.0,
    pressure_angle_deg=20.0,
    backlash_mm=0.05,
    hand="RIGHT",
    ratio=30
)

wheel_pitch_diameter = 45.0  # 30 teeth × 1.5mm module

print("Shared Parameters:")
print(f"  Module: {worm_params.module_mm}mm")
print(f"  Pitch diameter: {worm_params.pitch_diameter_mm}mm")
print(f"  Lead: {worm_params.lead_mm}mm")
print(f"  Wheel: 30 teeth, {wheel_pitch_diameter}mm pitch diameter")
print()

# Generate cylindrical worm
print("-"*70)
print("1. CYLINDRICAL WORM (Standard)")
print("-"*70)
cylindrical = WormGeometry(
    params=worm_params,
    assembly_params=assembly_params,
    length=20.0  # Explicit length for cylindrical
)
print("Building cylindrical worm...")
cyl_part = cylindrical.build()
cylindrical.export_step("comparison_cylindrical_m1.5.step")
print(f"✓ Volume: {cyl_part.volume:.2f} mm³")
print(f"✓ Length: 20.0mm (user-specified)")
print(f"✓ Core: straight cylinder at pitch radius")
print()

# Generate globoid worm
print("-"*70)
print("2. GLOBOID WORM (Double-Enveloping)")
print("-"*70)
globoid = GloboidWormGeometry(
    params=worm_params,
    assembly_params=assembly_params,
    wheel_pitch_diameter=wheel_pitch_diameter
)
print("Building globoid worm...")
glob_part = globoid.build()
globoid.export_step("comparison_globoid_m1.5.step")
print(f"✓ Volume: {glob_part.volume:.2f} mm³")
print(f"✓ Face width: {globoid.face_width:.2f}mm (auto-calculated)")
print(f"✓ Throat pitch radius: {globoid.throat_pitch_radius:.2f}mm")
print(f"✓ Core: hourglass shape (thinnest at center)")
print()

# Summary comparison
print("="*70)
print("COMPARISON SUMMARY")
print("="*70)
print()
print("Key Differences:")
print()
print("CYLINDRICAL:")
print("  - Straight cylinder core")
print("  - Constant helix radius")
print("  - Constant thread depth")
print("  - Can be any length")
print("  - Simpler to manufacture")
print("  - 1-2 teeth in contact")
print()
print("GLOBOID:")
print("  - Hourglass (concave) core")
print("  - Varying helix radius along axis")
print("  - Thread depth scales with local radius")
print("  - Fixed face width (related to wheel)")
print("  - Requires 5-axis machining")
print("  - 3-10 teeth in contact (expected)")
print()
print("Performance Advantages of Globoid:")
print("  • 30-50% higher load capacity")
print("  • 3-10× higher contact ratio")
print("  • 6-10% better efficiency")
print("  • Better for tight spaces with small modules")
print()
print("="*70)
print("NEXT STEPS")
print("="*70)
print()
print("1. Open both STEP files in your CAD software:")
print("   - comparison_cylindrical_m1.5.step")
print("   - comparison_globoid_m1.5.step")
print()
print("2. Compare visually:")
print("   - Side view: cylindrical is straight, globoid curves inward")
print("   - End view: both should have similar outer diameter")
print("   - Thread pattern: globoid threads follow curved surface")
print()
print("3. Measure dimensions:")
print("   - Cylindrical: constant 12mm pitch diameter along length")
print("   - Globoid: minimum ~6mm at throat, wider at ends")
print()
print("="*70)
