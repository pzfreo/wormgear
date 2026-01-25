"""
Worm Gear Calculator - Core Calculations

Pure mathematical functions for worm gear design.
Ported from wormgearcalc with field naming conventions adapted for wormgear.

Reference standards:
- DIN 3975 (worm geometry)
- DIN 3996 (worm gear load capacity)
- ISO 54 (standard modules)
"""

from math import pi, tan, atan, degrees, radians, cos, sin, sqrt
from typing import Optional, Tuple

# ISO 54 / DIN 780 standard modules (mm)
STANDARD_MODULES = [
    0.3, 0.4, 0.5, 0.6, 0.7, 0.75, 0.8, 0.9, 1.0,
    1.125, 1.25, 1.375, 1.5, 1.75, 2.0, 2.25, 2.5, 2.75,
    3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0, 7.0, 8.0, 9.0, 10.0,
    11.0, 12.0, 14.0, 16.0, 18.0, 20.0, 22.0, 25.0
]


def nearest_standard_module(module: float) -> float:
    """Find nearest ISO standard module"""
    return min(STANDARD_MODULES, key=lambda m: abs(m - module))


def is_standard_module(module: float, tolerance: float = 0.001) -> bool:
    """Check if module is a standard value"""
    nearest = nearest_standard_module(module)
    return abs(module - nearest) < tolerance


def estimate_efficiency(
    lead_angle_deg: float,
    pressure_angle_deg: float = 20.0,
    friction_coefficient: float = 0.05
) -> float:
    """
    Estimate worm drive efficiency.

    Based on simplified formula:
    η = tan(γ) / tan(γ + ρ)

    Where:
    - γ = lead angle
    - ρ = friction angle = atan(μ / cos(α))
    - μ = friction coefficient
    - α = pressure angle

    Typical friction coefficients:
    - Steel on bronze, lubricated: 0.03-0.05
    - Steel on cast iron: 0.05-0.08
    - Steel on steel: 0.08-0.12
    """
    gamma = radians(lead_angle_deg)
    alpha = radians(pressure_angle_deg)

    # Friction angle
    rho = atan(friction_coefficient / cos(alpha))

    # Efficiency
    if gamma + rho >= pi / 2:
        return 0.0

    efficiency = tan(gamma) / tan(gamma + rho)
    return max(0.0, min(1.0, efficiency))


def calculate_worm(
    module_mm: float,
    num_starts: int,
    pitch_diameter_mm: float,
    pressure_angle_deg: float = 20.0,
    clearance_factor: float = 0.25,
    backlash_mm: float = 0.0,
    hand: str = "right",
    profile_shift: float = 0.0
) -> dict:
    """
    Calculate worm dimensions from basic parameters.

    Args:
        module_mm: Axial module (mm)
        num_starts: Number of thread starts (typically 1-4)
        pitch_diameter_mm: Pitch diameter (mm)
        pressure_angle_deg: Pressure angle (degrees)
        clearance_factor: Bottom clearance as fraction of module
        backlash_mm: Backlash allowance (mm) - reduces thread thickness
        hand: Thread hand ("right" or "left")
        profile_shift: Profile shift coefficient (dimensionless, default 0.0)

    Returns:
        Dict with worm parameters matching WormParams schema
    """
    # Axial pitch
    axial_pitch = module_mm * pi

    # Lead
    lead_mm = axial_pitch * num_starts

    # Lead angle
    lead_angle_rad = atan(lead_mm / (pi * pitch_diameter_mm))
    lead_angle_deg = degrees(lead_angle_rad)

    # Tooth proportions
    addendum_mm = module_mm
    dedendum_mm = module_mm * (1 + clearance_factor)

    # Diameters
    tip_diameter_mm = pitch_diameter_mm + 2 * addendum_mm
    root_diameter_mm = pitch_diameter_mm - 2 * dedendum_mm

    # Thread thickness at pitch line (nominal is half axial pitch)
    # Reduce by backlash allowance
    thread_thickness_mm = (axial_pitch / 2) - backlash_mm

    return {
        "module_mm": module_mm,
        "num_starts": num_starts,
        "pitch_diameter_mm": pitch_diameter_mm,
        "tip_diameter_mm": tip_diameter_mm,
        "root_diameter_mm": root_diameter_mm,
        "lead_mm": lead_mm,
        "lead_angle_deg": lead_angle_deg,
        "addendum_mm": addendum_mm,
        "dedendum_mm": dedendum_mm,
        "thread_thickness_mm": thread_thickness_mm,
        "hand": hand,
        "profile_shift": profile_shift
    }


def calculate_wheel(
    module_mm: float,
    num_teeth: int,
    worm_pitch_diameter_mm: float,
    worm_lead_angle_deg: float,
    pressure_angle_deg: float = 20.0,
    clearance_factor: float = 0.25,
    profile_shift: float = 0.0
) -> dict:
    """
    Calculate worm wheel dimensions.

    Args:
        module_mm: Transverse module (= worm axial module) (mm)
        num_teeth: Number of teeth
        worm_pitch_diameter_mm: Pitch diameter of mating worm (mm)
        worm_lead_angle_deg: Lead angle of mating worm (degrees)
        pressure_angle_deg: Pressure angle (degrees)
        clearance_factor: Bottom clearance as fraction of module
        profile_shift: Profile shift coefficient (dimensionless, default 0.0)
                      Positive shift increases addendum, decreases dedendum

    Returns:
        Dict with wheel parameters matching WheelParams schema
    """
    # Pitch diameter (unaffected by profile shift)
    pitch_diameter_mm = module_mm * num_teeth

    # Tooth proportions with profile shift
    # Profile shift moves the reference line relative to the pitch circle
    addendum_mm = module_mm * (1.0 + profile_shift)
    dedendum_mm = module_mm * (1.0 + clearance_factor - profile_shift)

    # Diameters
    tip_diameter_mm = pitch_diameter_mm + 2 * addendum_mm
    root_diameter_mm = pitch_diameter_mm - 2 * dedendum_mm

    # Throat diameter (for enveloping geometry)
    # This is the diameter at the deepest point of the throat
    throat_diameter_mm = pitch_diameter_mm + module_mm  # Simplified

    # Helix angle = 90° - lead angle (for perpendicular axes)
    helix_angle_deg = 90.0 - worm_lead_angle_deg

    return {
        "module_mm": module_mm,
        "num_teeth": num_teeth,
        "pitch_diameter_mm": pitch_diameter_mm,
        "tip_diameter_mm": tip_diameter_mm,
        "root_diameter_mm": root_diameter_mm,
        "throat_diameter_mm": throat_diameter_mm,
        "helix_angle_deg": helix_angle_deg,
        "addendum_mm": addendum_mm,
        "dedendum_mm": dedendum_mm,
        "profile_shift": profile_shift
    }


def calculate_centre_distance(
    worm_pitch_diameter_mm: float,
    wheel_pitch_diameter_mm: float
) -> float:
    """Calculate centre distance between worm and wheel axes"""
    return (worm_pitch_diameter_mm + wheel_pitch_diameter_mm) / 2


def calculate_globoid_throat_radii(
    centre_distance_mm: float,
    wheel_pitch_diameter_mm: float,
    addendum_mm: float,
    dedendum_mm: float
) -> Tuple[float, float, float]:
    """
    Calculate throat radii for a globoid (hourglass) worm.

    For a globoid worm, the throat (waist) radius is sized to contact
    the wheel at the correct center distance.

    Args:
        centre_distance_mm: Center distance between axes (mm)
        wheel_pitch_diameter_mm: Wheel pitch diameter (mm)
        addendum_mm: Tooth addendum (mm)
        dedendum_mm: Tooth dedendum (mm)

    Returns:
        Tuple of (throat_pitch_radius, throat_tip_radius, throat_root_radius)
    """
    wheel_pitch_radius = wheel_pitch_diameter_mm / 2
    throat_pitch_radius = centre_distance_mm - wheel_pitch_radius
    throat_tip_radius = throat_pitch_radius + addendum_mm
    throat_root_radius = throat_pitch_radius - dedendum_mm
    return throat_pitch_radius, throat_tip_radius, throat_root_radius


def calculate_recommended_wheel_width(
    worm_pitch_diameter_mm: float,
    module_mm: float
) -> float:
    """
    Calculate recommended wheel width based on design guidelines.

    Wheel width is a design choice based on contact ratio and strength,
    NOT a geometric constraint from the hourglass shape. The hourglass
    varies along the worm axis (Y after rotation for hobbing), while
    wheel width is along Z axis - these are perpendicular, so the same
    cross-section cuts at all Z positions.

    Args:
        worm_pitch_diameter_mm: Worm pitch diameter (mm)
        module_mm: Module (mm)

    Returns:
        Recommended wheel width (mm)
    """
    # Standard guideline: 1.2-1.5× worm diameter
    # Based on contact ratio, strength, and practical considerations
    recommended = worm_pitch_diameter_mm * 1.3

    # Also ensure it's reasonable relative to module
    min_by_module = module_mm * 8.0
    max_by_module = module_mm * 12.0

    # Use the module-based range if worm diameter gives unreasonable values
    if recommended < min_by_module:
        recommended = min_by_module
    elif recommended > max_by_module:
        recommended = max_by_module

    return recommended


def calculate_recommended_worm_length(
    wheel_width_mm: float,
    lead_mm: float
) -> float:
    """
    Calculate recommended worm length based on engagement requirements.

    The worm should extend beyond the wheel edges for proper engagement,
    plus allow for end tapers and transitions.

    Args:
        wheel_width_mm: Wheel face width (mm)
        lead_mm: Worm lead (mm)

    Returns:
        Recommended worm length (mm)
    """
    # Worm should extend beyond wheel edges
    # Add 2× lead for end tapers and transitions
    # Add 1mm margin for safety
    recommended = wheel_width_mm + 2 * lead_mm + 1.0

    return recommended


def design_from_module(
    module: float,
    ratio: int,
    worm_pitch_diameter: Optional[float] = None,
    target_lead_angle: float = 7.0,
    pressure_angle: float = 20.0,
    backlash: float = 0.0,
    num_starts: int = 1,
    clearance_factor: float = 0.25,
    hand: str = "right",
    profile_shift: float = 0.0,
    profile: str = "ZA",
    globoid: bool = False,
    throat_reduction: float = 0.0,
    wheel_throated: bool = False
) -> dict:
    """
    Design worm gear pair from module specification.

    Args:
        module: Module (mm) - typically a standard value
        ratio: Gear ratio
        worm_pitch_diameter: Worm pitch diameter (mm), or None to calculate from lead angle
        target_lead_angle: Target lead angle if worm_pitch_diameter not specified (degrees)
        pressure_angle: Pressure angle (degrees)
        backlash: Backlash allowance (mm)
        num_starts: Number of worm starts
        clearance_factor: Bottom clearance factor
        hand: Thread hand ("right" or "left")
        profile_shift: Profile shift coefficient for wheel (dimensionless, default 0.0)
        profile: Tooth profile type ("ZA" or "ZK")
        globoid: True for globoid worm, False for cylindrical
        throat_reduction: Throat reduction for globoid worms (mm, default 0.0)
        wheel_throated: Whether wheel has throated teeth (hobbed)

    Returns:
        Dict with complete design matching WormGearDesign schema
    """
    # Number of teeth on wheel
    num_teeth = ratio * num_starts

    # Worm pitch diameter
    if worm_pitch_diameter is None:
        # Calculate for target lead angle
        lead = pi * module * num_starts
        target_rad = radians(target_lead_angle)
        worm_pitch_diameter_cylindrical = lead / (pi * tan(target_rad))

        # For globoid, increase pitch diameter to create hourglass effect
        if globoid:
            worm_pitch_diameter = worm_pitch_diameter_cylindrical + 2 * throat_reduction
        else:
            worm_pitch_diameter = worm_pitch_diameter_cylindrical

    # Calculate worm parameters
    worm = calculate_worm(
        module_mm=module,
        num_starts=num_starts,
        pitch_diameter_mm=worm_pitch_diameter,
        pressure_angle_deg=pressure_angle,
        clearance_factor=clearance_factor,
        backlash_mm=backlash,
        hand=hand,
        profile_shift=0.0  # Worm doesn't use profile shift
    )

    # Calculate wheel parameters
    wheel = calculate_wheel(
        module_mm=module,
        num_teeth=num_teeth,
        worm_pitch_diameter_mm=worm_pitch_diameter,
        worm_lead_angle_deg=worm["lead_angle_deg"],
        pressure_angle_deg=pressure_angle,
        clearance_factor=clearance_factor,
        profile_shift=profile_shift
    )

    # Calculate centre distance
    # For cylindrical: standard calculation
    # For globoid: reduce by throat_reduction to create hourglass effect
    standard_centre_distance = calculate_centre_distance(
        worm["pitch_diameter_mm"],
        wheel["pitch_diameter_mm"]
    )

    if globoid:
        centre_distance = standard_centre_distance - throat_reduction
    else:
        centre_distance = standard_centre_distance

    # Calculate efficiency and self-locking
    efficiency_percent = estimate_efficiency(
        worm["lead_angle_deg"],
        pressure_angle
    ) * 100.0
    self_locking = worm["lead_angle_deg"] < 6.0

    return {
        "worm": worm,
        "wheel": wheel,
        "assembly": {
            "centre_distance_mm": centre_distance,
            "pressure_angle_deg": pressure_angle,
            "backlash_mm": backlash,
            "hand": hand,
            "ratio": ratio,
            "efficiency_percent": efficiency_percent,
            "self_locking": self_locking
        },
        "manufacturing": {
            "profile": profile,
            "virtual_hobbing": False,
            "hobbing_steps": 18,
            "throated_wheel": wheel_throated,
            "sections_per_turn": 36
        }
    }


def design_from_centre_distance(
    centre_distance: float,
    ratio: int,
    worm_to_wheel_ratio: float = 0.3,
    pressure_angle: float = 20.0,
    backlash: float = 0.0,
    num_starts: int = 1,
    clearance_factor: float = 0.25,
    hand: str = "right",
    profile_shift: float = 0.0,
    profile: str = "ZA",
    globoid: bool = False,
    throat_reduction: float = 0.0,
    wheel_throated: bool = False
) -> dict:
    """
    Design worm gear pair from centre distance constraint.

    Args:
        centre_distance: Required centre distance (mm)
        ratio: Gear ratio
        worm_to_wheel_ratio: Ratio of worm pitch dia to wheel pitch dia (affects lead angle)
        pressure_angle: Pressure angle (degrees)
        backlash: Backlash allowance (mm)
        num_starts: Number of worm starts
        clearance_factor: Bottom clearance factor
        hand: Thread hand ("right" or "left")
        profile_shift: Profile shift coefficient for wheel (dimensionless, default 0.0)
        profile: Tooth profile type ("ZA" or "ZK")
        globoid: True for globoid worm, False for cylindrical
        throat_reduction: Throat reduction for globoid worms (mm, default 0.0)
        wheel_throated: Whether wheel has throated teeth (hobbed)

    Returns:
        Dict with complete design matching WormGearDesign schema
    """
    # Number of teeth on wheel
    num_teeth = ratio * num_starts

    # For globoid, the given centre_distance is the actual distance
    # We need to calculate what the standard centre would be
    if globoid:
        standard_centre_distance = centre_distance + throat_reduction
    else:
        standard_centre_distance = centre_distance

    # Solve for diameters
    # standard_centre_distance = (worm_pd + wheel_pd) / 2
    # wheel_pd = module × num_teeth
    # worm_pd = k × wheel_pd (where k = worm_to_wheel_ratio)
    #
    # 2 × cd = k × wheel_pd + wheel_pd = wheel_pd × (k + 1)
    # wheel_pd = 2 × cd / (k + 1)

    wheel_pitch_diameter = 2 * standard_centre_distance / (worm_to_wheel_ratio + 1)
    worm_pitch_diameter = standard_centre_distance * 2 - wheel_pitch_diameter

    # Module from wheel
    module = wheel_pitch_diameter / num_teeth

    return design_from_module(
        module=module,
        ratio=ratio,
        worm_pitch_diameter=worm_pitch_diameter,
        pressure_angle=pressure_angle,
        backlash=backlash,
        num_starts=num_starts,
        clearance_factor=clearance_factor,
        hand=hand,
        profile_shift=profile_shift,
        profile=profile,
        globoid=globoid,
        throat_reduction=throat_reduction,
        wheel_throated=wheel_throated
    )


def design_from_wheel(
    wheel_od: float,
    ratio: int,
    target_lead_angle: float = 7.0,
    pressure_angle: float = 20.0,
    backlash: float = 0.0,
    num_starts: int = 1,
    clearance_factor: float = 0.25,
    hand: str = "right",
    profile_shift: float = 0.0,
    profile: str = "ZA",
    globoid: bool = False,
    throat_reduction: float = 0.0,
    wheel_throated: bool = False
) -> dict:
    """
    Design worm gear pair from wheel OD constraint.
    Worm sized to achieve target lead angle.

    Args:
        wheel_od: Wheel outside/tip diameter (mm)
        ratio: Gear ratio
        target_lead_angle: Desired lead angle (degrees)
        pressure_angle: Pressure angle (degrees)
        backlash: Backlash allowance (mm)
        num_starts: Number of worm starts
        clearance_factor: Bottom clearance factor
        hand: Thread hand ("right" or "left")
        profile_shift: Profile shift coefficient for wheel (dimensionless, default 0.0)
        profile: Tooth profile type ("ZA" or "ZK")
        globoid: True for globoid worm, False for cylindrical
        throat_reduction: Throat reduction for globoid worms (mm, default 0.0)
        wheel_throated: Whether wheel has throated teeth (hobbed)

    Returns:
        Dict with complete design matching WormGearDesign schema
    """
    # Number of teeth on wheel
    num_teeth = ratio * num_starts

    # Calculate module from wheel OD
    module = wheel_od / (num_teeth + 2)

    # Calculate worm pitch diameter for target lead angle
    lead = pi * module * num_starts
    target_rad = radians(target_lead_angle)
    worm_pitch_diameter_cylindrical = lead / (pi * tan(target_rad))

    # For globoid, increase pitch diameter to create hourglass effect
    if globoid:
        worm_pitch_diameter = worm_pitch_diameter_cylindrical + 2 * throat_reduction
    else:
        worm_pitch_diameter = worm_pitch_diameter_cylindrical

    return design_from_module(
        module=module,
        ratio=ratio,
        worm_pitch_diameter=worm_pitch_diameter,
        pressure_angle=pressure_angle,
        backlash=backlash,
        num_starts=num_starts,
        clearance_factor=clearance_factor,
        hand=hand,
        profile_shift=profile_shift,
        profile=profile,
        globoid=globoid,
        throat_reduction=throat_reduction,
        wheel_throated=wheel_throated
    )
