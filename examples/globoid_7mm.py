"""
Generate globoid worm pair from 7mm.json example.

This is a tiny module 0.5mm design with self-locking characteristics.
"""

import sys
import os
import math
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from wormgear_geometry.globoid_worm import GloboidWormGeometry
from wormgear_geometry.wheel import WheelGeometry
from wormgear_geometry.io import load_design_json, WormParams

print("="*70)
print("GLOBOID PAIR FROM 7MM.JSON")
print("="*70)
print()

# Load design from JSON
design = load_design_json("examples/7mm.json")

print("Design parameters:")
print(f"  Module: {design.worm.module_mm}mm")
print(f"  Worm starts: {design.worm.num_starts}")
print(f"  Wheel teeth: {design.wheel.num_teeth}")
print(f"  Ratio: 1:{design.assembly.ratio}")
print(f"  Centre distance: {design.assembly.centre_distance_mm}mm")
print(f"  Self-locking: {design.assembly.self_locking}")
print()

# Generate globoid worm
print("-"*70)
print("1. GLOBOID WORM (7mm tip diameter)")
print("-"*70)
print()

globoid_worm = GloboidWormGeometry(
    params=design.worm,
    assembly_params=design.assembly,
    wheel_pitch_diameter=design.wheel.pitch_diameter_mm,
)

print(f"Throat pitch radius: {globoid_worm.throat_pitch_radius:.2f}mm")
print(f"Nominal pitch radius: {globoid_worm.nominal_pitch_radius:.2f}mm")
print(f"Hourglass taper: {globoid_worm.nominal_pitch_radius / globoid_worm.throat_pitch_radius:.3f}×")
print(f"Face width: {globoid_worm.face_width:.2f}mm")
print()

worm_part = globoid_worm.build()
globoid_worm.export_step("globoid_7mm_worm.step")
print(f"✓ Worm volume: {worm_part.volume:.2f} mm³")
print()

# Calculate proper throat depth using wrap angle
print("-"*70)
print("2. WHEEL WITH INDUSTRY-STANDARD THROAT DEPTH")
print("-"*70)
print()

# For this tiny gear, use 75° wrap angle (industry standard)
wrap_angle_deg = 75
wrap_angle_rad = math.radians(wrap_angle_deg)
worm_tip_radius_nominal = design.worm.tip_diameter_mm / 2
throat_cut_radius = worm_tip_radius_nominal / math.cos(wrap_angle_rad / 2)

print(f"Throat depth calculation:")
print(f"  Target wrap angle: {wrap_angle_deg}°")
print(f"  Worm tip radius: {worm_tip_radius_nominal:.2f}mm")
print(f"  Required throat cut radius: {throat_cut_radius:.2f}mm")
print()

# Create worm params with adjusted tip diameter for throating
worm_params_throated = WormParams(
    module_mm=design.worm.module_mm,
    num_starts=design.worm.num_starts,
    pitch_diameter_mm=design.worm.pitch_diameter_mm,
    tip_diameter_mm=throat_cut_radius * 2,  # Use calculated throat cut radius
    root_diameter_mm=design.worm.root_diameter_mm,
    lead_mm=design.worm.lead_mm,
    lead_angle_deg=design.worm.lead_angle_deg,
    addendum_mm=design.worm.addendum_mm,
    dedendum_mm=design.worm.dedendum_mm,
    thread_thickness_mm=design.worm.thread_thickness_mm,
    hand=design.worm.hand,
    profile_shift=design.worm.profile_shift
)

wheel_geo = WheelGeometry(
    params=design.wheel,
    worm_params=worm_params_throated,
    assembly_params=design.assembly,
    face_width=None,
    throated=True,
)

print(f"Wheel specifications:")
print(f"  Teeth: {design.wheel.num_teeth}")
print(f"  Pitch diameter: {design.wheel.pitch_diameter_mm:.2f}mm")
print(f"  Face width: {wheel_geo.face_width:.2f}mm")
print()

wheel_part = wheel_geo.build()
wheel_geo.export_step("globoid_7mm_wheel.step")
print(f"✓ Wheel volume: {wheel_part.volume:.2f} mm³")
print()

# Calculate contact characteristics
print("="*70)
print("MESH CHARACTERISTICS")
print("="*70)
print()

worm_circumference = math.pi * design.worm.pitch_diameter_mm
contact_arc_length = worm_circumference * (wrap_angle_deg / 360)
teeth_in_contact = contact_arc_length / design.worm.lead_mm

print(f"Centre distance: {design.assembly.centre_distance_mm:.2f}mm")
print(f"Wrap angle: {wrap_angle_deg}°")
print(f"Contact arc length: {contact_arc_length:.2f}mm")
print(f"Approximate teeth in contact: {teeth_in_contact:.1f}")
print()

print(f"Design notes:")
print(f"  - Self-locking: {design.assembly.self_locking}")
print(f"  - Lead angle: {design.worm.lead_angle_deg:.1f}° (very low = high self-locking)")
print(f"  - Efficiency: {design.assembly.efficiency_percent:.1f}% (low due to self-locking)")
print(f"  - Module: {design.worm.module_mm}mm (very small - precision machining required)")
print()

print("="*70)
print("GENERATED FILES")
print("="*70)
print()
print("1. globoid_7mm_worm.step")
print("   - Tiny hourglass worm (7mm tip diameter)")
print("   - Self-locking design (low lead angle)")
print()
print("2. globoid_7mm_wheel.step")
print("   - 12-tooth wheel with proper throat depth")
print("   - Compact design (6mm pitch diameter)")
print()
print("NOTES:")
print("  - This is a VERY small gear set (module 0.5mm)")
print("  - Precision 5-axis machining essential")
print("  - Self-locking characteristic (backdriving prevented)")
print("  - Low efficiency (~60%) is expected for self-locking")
print("  - Ideal for precision instruments, clockwork, etc.")
print()
