"""
Demonstrate globoid advantage: Higher ratio with same outer dimensions.

Starting from 7mm.json (1:12 ratio), increase to higher ratio by taking
advantage of the globoid worm's narrower throat.
"""

import sys
import os
import math
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from wormgear_geometry.globoid_worm import GloboidWormGeometry
from wormgear_geometry.wheel import WheelGeometry
from wormgear_geometry.io import WormParams, WheelParams, AssemblyParams

print("="*70)
print("GLOBOID ADVANTAGE: HIGHER RATIO WITH SAME ODs")
print("="*70)
print()

# Original 7mm design parameters
module = 0.5
worm_starts = 1
original_wheel_teeth = 12
original_ratio = 12

# Worm parameters (keep worm the same)
worm_params = WormParams(
    module_mm=module,
    num_starts=worm_starts,
    pitch_diameter_mm=6.0,
    tip_diameter_mm=7.0,
    root_diameter_mm=4.75,
    lead_mm=1.571,
    lead_angle_deg=4.76,
    addendum_mm=0.5,
    dedendum_mm=0.625,
    thread_thickness_mm=0.685,
    hand="RIGHT",
    profile_shift=0.0
)

print("ORIGINAL DESIGN (from 7mm.json)")
print("-"*70)
print(f"Worm tip diameter: {worm_params.tip_diameter_mm}mm (FIXED)")
print(f"Worm nominal pitch diameter: {worm_params.pitch_diameter_mm}mm")
print(f"Wheel teeth: {original_wheel_teeth}")
print(f"Wheel pitch diameter: {original_wheel_teeth * module}mm")
print(f"Ratio: 1:{original_ratio}")
print(f"Centre distance: 6.0mm")
print()

# Create globoid worm to get throat dimensions
wheel_pitch_diameter_original = original_wheel_teeth * module
globoid_worm = GloboidWormGeometry(
    params=worm_params,
    assembly_params=AssemblyParams(
        centre_distance_mm=6.0,
        pressure_angle_deg=25,
        backlash_mm=0.1,
        hand="RIGHT",
        ratio=original_ratio
    ),
    wheel_pitch_diameter=wheel_pitch_diameter_original,
)

print("GLOBOID WORM CHARACTERISTICS")
print("-"*70)
print(f"Throat pitch radius: {globoid_worm.throat_pitch_radius:.2f}mm")
print(f"Nominal pitch radius: {globoid_worm.nominal_pitch_radius:.2f}mm")
print(f"Difference: {globoid_worm.nominal_pitch_radius - globoid_worm.throat_pitch_radius:.2f}mm")
print()
print("This narrower throat allows a larger wheel at the same centre distance!")
print()

# Calculate new wheel size using throat pitch radius
# Keep same centre distance (6.0mm) but use throat pitch instead of nominal
centre_distance = 6.0
new_wheel_pitch_radius = centre_distance - globoid_worm.throat_pitch_radius
new_wheel_pitch_diameter = new_wheel_pitch_radius * 2
new_wheel_teeth = int(new_wheel_pitch_diameter / module)
new_ratio = new_wheel_teeth / worm_starts

print("INCREASED RATIO DESIGN")
print("-"*70)
print(f"Using throat pitch radius for centre distance calculation:")
print(f"  Centre distance: {centre_distance}mm (SAME)")
print(f"  Throat pitch radius: {globoid_worm.throat_pitch_radius:.2f}mm")
print(f"  New wheel pitch radius: {new_wheel_pitch_radius:.2f}mm")
print(f"  New wheel pitch diameter: {new_wheel_pitch_diameter:.2f}mm")
print(f"  New wheel teeth: {new_wheel_teeth}")
print(f"  New ratio: 1:{new_ratio:.0f}")
print()
print(f"Ratio increase: {original_ratio}:1 → {new_ratio:.0f}:1 (+{((new_ratio/original_ratio - 1) * 100):.1f}%)")
print()

# Create wheel parameters for increased ratio design
wheel_params_new = WheelParams(
    module_mm=module,
    num_teeth=new_wheel_teeth,
    pitch_diameter_mm=new_wheel_pitch_diameter,
    tip_diameter_mm=new_wheel_pitch_diameter + 2 * 0.65,  # addendum
    root_diameter_mm=new_wheel_pitch_diameter - 2 * 0.475,  # dedendum
    throat_diameter_mm=new_wheel_pitch_diameter + 1.0,
    helix_angle_deg=85.24,
    addendum_mm=0.65,
    dedendum_mm=0.475,
    profile_shift=0.0
)

assembly_params_new = AssemblyParams(
    centre_distance_mm=centre_distance,
    pressure_angle_deg=25,
    backlash_mm=0.1,
    hand="RIGHT",
    ratio=new_ratio
)

# Generate the increased ratio pair
print("-"*70)
print("GENERATING INCREASED RATIO GLOBOID PAIR")
print("-"*70)
print()

# Worm (same as before)
globoid_worm_new = GloboidWormGeometry(
    params=worm_params,
    assembly_params=assembly_params_new,
    wheel_pitch_diameter=new_wheel_pitch_diameter,
)

worm_part = globoid_worm_new.build()
globoid_worm_new.export_step("globoid_7mm_higher_ratio_worm.step")
print(f"✓ Worm: {worm_part.volume:.2f} mm³")

# Wheel with proper throat depth
wrap_angle_deg = 75
wrap_angle_rad = math.radians(wrap_angle_deg)
worm_tip_radius = worm_params.tip_diameter_mm / 2
throat_cut_radius = worm_tip_radius / math.cos(wrap_angle_rad / 2)

worm_params_throated = WormParams(
    module_mm=worm_params.module_mm,
    num_starts=worm_params.num_starts,
    pitch_diameter_mm=worm_params.pitch_diameter_mm,
    tip_diameter_mm=throat_cut_radius * 2,
    root_diameter_mm=worm_params.root_diameter_mm,
    lead_mm=worm_params.lead_mm,
    lead_angle_deg=worm_params.lead_angle_deg,
    addendum_mm=worm_params.addendum_mm,
    dedendum_mm=worm_params.dedendum_mm,
    thread_thickness_mm=worm_params.thread_thickness_mm,
    hand=worm_params.hand,
    profile_shift=worm_params.profile_shift
)

wheel_geo = WheelGeometry(
    params=wheel_params_new,
    worm_params=worm_params_throated,
    assembly_params=assembly_params_new,
    throated=True,
)

wheel_part = wheel_geo.build()
wheel_geo.export_step("globoid_7mm_higher_ratio_wheel.step")
print(f"✓ Wheel: {wheel_part.volume:.2f} mm³")
print()

# Comparison
print("="*70)
print("COMPARISON: CYLINDRICAL vs GLOBOID")
print("="*70)
print()

print("With CYLINDRICAL worm (constant radius):")
print(f"  Centre distance: 6.0mm")
print(f"  Worm pitch radius: 3.0mm (constant)")
print(f"  Wheel pitch radius: 3.0mm")
print(f"  Wheel teeth: {original_wheel_teeth}")
print(f"  Ratio: 1:{original_ratio}")
print()

print("With GLOBOID worm (hourglass):")
print(f"  Centre distance: 6.0mm (SAME)")
print(f"  Worm throat pitch radius: {globoid_worm.throat_pitch_radius:.2f}mm (narrower!)")
print(f"  Wheel pitch radius: {new_wheel_pitch_radius:.2f}mm (larger!)")
print(f"  Wheel teeth: {new_wheel_teeth}")
print(f"  Ratio: 1:{new_ratio:.0f}")
print()

print(f"ADVANTAGE: {((new_ratio/original_ratio - 1) * 100):.1f}% higher ratio")
print(f"           Same outer dimensions, same centre distance!")
print()

# Outer diameter comparison
worm_od = worm_params.tip_diameter_mm
wheel_od_original = original_wheel_teeth * module + 2 * 0.65
wheel_od_new = wheel_params_new.tip_diameter_mm

print("Outer diameter comparison:")
print(f"  Worm OD: {worm_od}mm (SAME)")
print(f"  Wheel OD (original): {wheel_od_original:.2f}mm")
print(f"  Wheel OD (new): {wheel_od_new:.2f}mm")
print(f"  Wheel OD increase: {wheel_od_new - wheel_od_original:.2f}mm")
print()

print("="*70)
print("GENERATED FILES")
print("="*70)
print()
print("1. globoid_7mm_higher_ratio_worm.step")
print("   - Same 7mm worm as before")
print()
print("2. globoid_7mm_higher_ratio_wheel.step")
print(f"   - {new_wheel_teeth} teeth (vs {original_wheel_teeth} original)")
print(f"   - 1:{new_ratio:.0f} ratio (vs 1:{original_ratio} original)")
print("   - Slightly larger OD to accommodate extra teeth")
print()
print("KEY INSIGHT:")
print("  The globoid worm's narrow throat creates space for more wheel teeth")
print("  at the same centre distance, increasing the gear ratio without")
print("  significantly increasing the overall package size!")
print()
