"""
Generate a globoid worm with matching wheel.

Creates both parts for visual inspection of mesh fit.
Uses industry-standard throat depth based on wrap angle calculation.
"""

import sys
import os
import math
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from wormgear_geometry.globoid_worm import GloboidWormGeometry
from wormgear_geometry.wheel import WheelGeometry
from wormgear_geometry.io import WormParams, WheelParams, AssemblyParams

print("="*70)
print("GLOBOID WORM GEAR PAIR GENERATION")
print("="*70)
print()

# Parameters for module 1.5, ratio 1:30
print("Parameters:")
print("  Module: 1.5mm")
print("  Worm starts: 1")
print("  Wheel teeth: 30")
print("  Ratio: 1:30")
print("  Pressure angle: 20°")
print()

# Worm parameters
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

# Wheel parameters
wheel_params = WheelParams(
    module_mm=1.5,
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

# Assembly parameters
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
globoid_worm.export_step("globoid_pair_worm.step")
print(f"✓ Worm volume: {worm_part.volume:.2f} mm³")
print()

# Generate matching wheel with proper throat depth
print("-"*70)
print("2. WHEEL WITH INDUSTRY-STANDARD THROAT DEPTH")
print("-"*70)
print()

# Calculate proper throat cutting radius based on wrap angle
# For effective meshing, aim for 75° wrap angle (industry standard)
wrap_angle_deg = 75
wrap_angle_rad = math.radians(wrap_angle_deg)
worm_tip_radius_nominal = worm_params.tip_diameter_mm / 2
throat_cut_radius = worm_tip_radius_nominal / math.cos(wrap_angle_rad / 2)

print(f"Throat depth calculation (industry standard):")
print(f"  Target wrap angle: {wrap_angle_deg}°")
print(f"  Worm tip radius: {worm_tip_radius_nominal:.2f}mm")
print(f"  Required throat cut radius: {throat_cut_radius:.2f}mm")
print()

# Create worm params with adjusted tip diameter for proper throating
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

# Use throated wheel which adds concave throating
wheel_geo = WheelGeometry(
    params=wheel_params,
    worm_params=worm_params_throated,  # Use throat-adjusted params
    assembly_params=assembly_params,
    face_width=None,  # Auto-calculate
    throated=True,    # CRITICAL: throated to match worm curvature
)

print(f"Wheel teeth: {wheel_params.num_teeth}")
print(f"Pitch diameter: {wheel_params.pitch_diameter_mm:.2f}mm")
print(f"Face width: {wheel_geo.face_width:.2f}mm (auto-calculated)")
print()

wheel_part = wheel_geo.build()
wheel_geo.export_step("globoid_pair_wheel.step")
print(f"✓ Wheel volume: {wheel_part.volume:.2f} mm³")
print()

# Summary
print("="*70)
print("PAIR GENERATION COMPLETE")
print("="*70)
print()
print("Generated files:")
print("  1. globoid_pair_worm.step  - Hourglass worm with helical threads")
print("  2. globoid_pair_wheel.step - Throated wheel to match worm")
print()
print("Visual Inspection in CAD:")
print()
print("WORM (side view):")
print("  - Hourglass shape (thinner at center)")
print("  - Helical threads wrapping around curved surface")
print("  - Face width: ~15.6mm")
print()
print("WHEEL (side view):")
print("  - Concave throat (curves inward)")
print("  - Teeth wrap around the rim")
print("  - Should complement worm's hourglass shape")
print()
print("MESH FIT:")
print("  To check mesh, position parts in CAD:")
print(f"  - Centre distance: {assembly_params.centre_distance_mm:.2f}mm")
print("  - Worm axis: along Z")
print("  - Wheel axis: along X or Y (perpendicular to worm)")
print("  - Rotate wheel to align teeth with worm threads")
print()
print("THROAT CHARACTERISTICS:")
print(f"  - Throat cut radius: {throat_cut_radius:.2f}mm")
print(f"  - Wrap angle: {wrap_angle_deg}° (industry standard)")
print(f"  - Effective meshing with multiple teeth in contact")
print()
print("NOTES:")
print("  - Throat depth calculated using wrap angle method")
print("  - This provides industry-standard meshing characteristics")
print("  - True globoid wheel (envelope surface) would be even better")
print("  - Current approximation suitable for most applications")
print()
