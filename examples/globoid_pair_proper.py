"""
Generate globoid worm with properly throated wheel.
Uses industry-standard wrap angle calculation for effective meshing.
"""

import sys
import os
import math
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from wormgear_geometry.globoid_worm import GloboidWormGeometry
from wormgear_geometry.wheel import WheelGeometry
from wormgear_geometry.io import WormParams, WheelParams, AssemblyParams

print("="*70)
print("GLOBOID PAIR - INDUSTRY STANDARD THROAT DEPTH")
print("="*70)
print()

# Parameters
module = 1.5
worm_params = WormParams(
    module_mm=module,
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

wheel_params = WheelParams(
    module_mm=module,
    num_teeth=30,
    pitch_diameter_mm=45.0,
    tip_diameter_mm=48.0,
    root_diameter_mm=41.5,
    throat_diameter_mm=47.0,
    helix_angle_deg=79.0,
    addendum_mm=1.5,
    dedendum_mm=1.75,
    profile_shift=0.0
)

assembly_params = AssemblyParams(
    centre_distance_mm=28.5,
    pressure_angle_deg=20.0,
    backlash_mm=0.05,
    hand="RIGHT",
    ratio=30
)

# Generate globoid worm
print("-"*70)
print("1. GLOBOID WORM")
print("-"*70)
print()

globoid_worm = GloboidWormGeometry(
    params=worm_params,
    assembly_params=assembly_params,
    wheel_pitch_diameter=wheel_params.pitch_diameter_mm,
)

print(f"Throat pitch radius: {globoid_worm.throat_pitch_radius:.2f}mm")
print(f"Nominal pitch radius: {globoid_worm.nominal_pitch_radius:.2f}mm")
print(f"Face width: {globoid_worm.face_width:.2f}mm")
print()

worm_part = globoid_worm.build()
globoid_worm.export_step("globoid_proper_worm.step")
print(f"✓ Worm volume: {worm_part.volume:.2f} mm³")
print()

# Calculate proper throat cutting radius based on wrap angle
print("-"*70)
print("2. WHEEL WITH PROPER THROAT DEPTH")
print("-"*70)
print()

# For effective meshing, aim for 75° wrap angle (good industry standard)
wrap_angle_deg = 75
wrap_angle_rad = math.radians(wrap_angle_deg)

worm_tip_radius_nominal = worm_params.tip_diameter_mm / 2
throat_cut_radius = worm_tip_radius_nominal / math.cos(wrap_angle_rad / 2)

print(f"Throat depth calculation:")
print(f"  Target wrap angle: {wrap_angle_deg}°")
print(f"  Worm tip radius: {worm_tip_radius_nominal:.2f}mm")
print(f"  Required throat cut radius: {throat_cut_radius:.2f}mm")
print()

# Create worm params with adjusted tip diameter for throating
worm_params_throated = WormParams(
    module_mm=worm_params.module_mm,
    num_starts=worm_params.num_starts,
    pitch_diameter_mm=worm_params.pitch_diameter_mm,
    tip_diameter_mm=throat_cut_radius * 2,  # Use calculated throat cut radius
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
    params=wheel_params,
    worm_params=worm_params_throated,
    assembly_params=assembly_params,
    face_width=None,
    throated=True,
)

print(f"Wheel specifications:")
print(f"  Teeth: {wheel_params.num_teeth}")
print(f"  Pitch diameter: {wheel_params.pitch_diameter_mm:.2f}mm")
print(f"  Face width: {wheel_geo.face_width:.2f}mm")
print()

wheel_part = wheel_geo.build()
wheel_geo.export_step("globoid_proper_wheel.step")
print(f"✓ Wheel volume: {wheel_part.volume:.2f} mm³")
print()

# Calculate expected contact characteristics
wheel_pitch_radius = wheel_params.pitch_diameter_mm / 2
distance_to_worm = assembly_params.centre_distance_mm - worm_tip_radius_nominal
throat_depth = wheel_pitch_radius - distance_to_worm

print("="*70)
print("THROAT CHARACTERISTICS")
print("="*70)
print()
print(f"Centre distance: {assembly_params.centre_distance_mm:.2f}mm")
print(f"Distance from wheel center to worm surface: {distance_to_worm:.2f}mm")
print(f"Throat depth below pitch circle: {throat_depth:.2f}mm")
print(f"Throat depth ratio (depth/module): {throat_depth/module:.2f}")
print()

# Estimate contact characteristics
# Contact arc on worm
worm_circumference = math.pi * worm_params.pitch_diameter_mm
contact_arc_length = worm_circumference * (wrap_angle_deg / 360)
teeth_in_contact = contact_arc_length / worm_params.lead_mm

print("Expected mesh characteristics:")
print(f"  Wrap angle: {wrap_angle_deg}°")
print(f"  Contact arc length: {contact_arc_length:.2f}mm")
print(f"  Approximate teeth in contact: {teeth_in_contact:.1f}")
print()

print("="*70)
print("GENERATED FILES")
print("="*70)
print()
print("1. globoid_proper_worm.step")
print("   - Hourglass globoid worm")
print()
print("2. globoid_proper_wheel.step")
print("   - Wheel with proper throat depth for {wrap_angle_deg}° wrap")
print("   - Should show ~{teeth_in_contact:.1f} teeth in potential contact")
print("   - Much deeper throat than previous versions")
print()
print("INSPECTION:")
print("  - Load both files in CAD")
print("  - Position at centre distance 28.5mm")
print("  - Should see minimal gap between worm and wheel")
print("  - Multiple teeth wrapping around worm")
print()
