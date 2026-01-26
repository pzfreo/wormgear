"""
Worm Gear Calculator - Core Calculations

Pure mathematical functions for worm gear design.
Returns typed WormGearDesign dataclasses for type safety.

Reference standards:
- DIN 3975 (worm geometry)
- DIN 3996 (worm gear load capacity)
- ISO 54 (standard modules)
"""

from math import pi, tan, atan, degrees, radians, cos, sin, sqrt
from typing import Optional, Tuple, Union

from ..enums import Hand, WormProfile, WormType
from ..io import WormParams, WheelParams, AssemblyParams, ManufacturingParams, WormGearDesign

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
        "axial_pitch_mm": axial_pitch,  # Added for completeness
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


def calculate_manufacturing_params(
    worm_lead_mm: float,
    module_mm: float,
    worm_pitch_diameter_mm: Optional[float] = None,
    profile: Union[WormProfile, str] = "ZA",
    globoid: bool = False,
    wheel_throated: bool = False,
    virtual_hobbing: bool = False,
    hobbing_steps: int = 18
) -> dict:
    """
    Calculate recommended manufacturing parameters.

    These are design guidelines based on best practices, NOT geometric constraints.
    Wheel width and worm length can be adjusted based on specific requirements.

    Args:
        worm_lead_mm: Worm lead (mm)
        module_mm: Module (mm)
        worm_pitch_diameter_mm: Worm pitch diameter (mm) for wheel width calculation
        profile: Tooth profile type per DIN 3975 ("ZA", "ZK", "ZI")
        globoid: True for globoid worm, False for cylindrical
        wheel_throated: Whether wheel has throated teeth (hobbed)
        virtual_hobbing: True to use virtual hobbing for wheel generation
        hobbing_steps: Number of steps for virtual hobbing

    Returns:
        Dict with manufacturing parameters
    """
    # Convert string to enum if needed
    if isinstance(profile, str):
        profile = WormProfile(profile.upper())

    # Calculate recommended wheel width (design guideline, not constraint)
    if worm_pitch_diameter_mm is not None:
        wheel_width_mm = calculate_recommended_wheel_width(worm_pitch_diameter_mm, module_mm)
    else:
        # Fallback if no worm diameter provided
        wheel_width_mm = module_mm * 10.0

    # Calculate recommended worm length (design guideline, not constraint)
    worm_length_mm = calculate_recommended_worm_length(wheel_width_mm, worm_lead_mm)

    return {
        "profile": profile.value,
        "worm_type": "globoid" if globoid else "cylindrical",
        "virtual_hobbing": virtual_hobbing,
        "hobbing_steps": hobbing_steps,
        "throated_wheel": wheel_throated,
        "sections_per_turn": 36,
        "worm_length_mm": round(worm_length_mm, 2),
        "wheel_width_mm": round(wheel_width_mm, 2)
    }


def _build_design(
    worm_dict: dict,
    wheel_dict: dict,
    centre_distance_mm: float,
    pressure_angle_deg: float,
    backlash_mm: float,
    hand: Hand,
    ratio: int,
    efficiency_percent: float,
    self_locking: bool,
    profile: WormProfile,
    wheel_throated: bool,
    worm_length_mm: float,
    wheel_width_mm: float,
    globoid: bool = False,
    throat_reduction_mm: Optional[float] = None,
    throat_curvature_radius_mm: Optional[float] = None
) -> WormGearDesign:
    """
    Build a typed WormGearDesign from calculated parameters.

    This is the single point where we convert calculation dicts to typed dataclasses.
    """
    # Build WormParams
    worm_type = WormType.GLOBOID if globoid else WormType.CYLINDRICAL
    worm_params = WormParams(
        module_mm=worm_dict["module_mm"],
        num_starts=worm_dict["num_starts"],
        pitch_diameter_mm=worm_dict["pitch_diameter_mm"],
        tip_diameter_mm=worm_dict["tip_diameter_mm"],
        root_diameter_mm=worm_dict["root_diameter_mm"],
        lead_mm=worm_dict["lead_mm"],
        axial_pitch_mm=worm_dict["axial_pitch_mm"],
        lead_angle_deg=worm_dict["lead_angle_deg"],
        addendum_mm=worm_dict["addendum_mm"],
        dedendum_mm=worm_dict["dedendum_mm"],
        thread_thickness_mm=worm_dict["thread_thickness_mm"],
        hand=hand,
        profile_shift=worm_dict.get("profile_shift", 0.0),
        type=worm_type,
        throat_reduction_mm=throat_reduction_mm,
        throat_curvature_radius_mm=throat_curvature_radius_mm
    )

    # Build WheelParams
    wheel_params = WheelParams(
        module_mm=wheel_dict["module_mm"],
        num_teeth=wheel_dict["num_teeth"],
        pitch_diameter_mm=wheel_dict["pitch_diameter_mm"],
        tip_diameter_mm=wheel_dict["tip_diameter_mm"],
        root_diameter_mm=wheel_dict["root_diameter_mm"],
        throat_diameter_mm=wheel_dict["throat_diameter_mm"],
        helix_angle_deg=wheel_dict["helix_angle_deg"],
        addendum_mm=wheel_dict["addendum_mm"],
        dedendum_mm=wheel_dict["dedendum_mm"],
        profile_shift=wheel_dict.get("profile_shift", 0.0)
    )

    # Build AssemblyParams
    assembly_params = AssemblyParams(
        centre_distance_mm=centre_distance_mm,
        pressure_angle_deg=pressure_angle_deg,
        backlash_mm=backlash_mm,
        hand=hand,
        ratio=ratio,
        efficiency_percent=efficiency_percent,
        self_locking=self_locking
    )

    # Build ManufacturingParams
    manufacturing_params = ManufacturingParams(
        profile=profile,
        virtual_hobbing=False,
        hobbing_steps=18,
        throated_wheel=wheel_throated,
        sections_per_turn=36,
        worm_length_mm=round(worm_length_mm, 2),
        wheel_width_mm=round(wheel_width_mm, 2)
    )

    return WormGearDesign(
        worm=worm_params,
        wheel=wheel_params,
        assembly=assembly_params,
        manufacturing=manufacturing_params
    )


def design_from_module(
    module: float,
    ratio: int,
    worm_pitch_diameter: Optional[float] = None,
    target_lead_angle: float = 7.0,
    pressure_angle: float = 20.0,
    backlash: float = 0.0,
    num_starts: int = 1,
    clearance_factor: float = 0.25,
    hand: Union[Hand, str] = "right",
    profile_shift: float = 0.0,
    profile: Union[WormProfile, str] = "ZA",
    worm_type: Union[WormType, str, None] = None,
    globoid: bool = False,
    throat_reduction: float = 0.0,
    wheel_throated: bool = False
) -> WormGearDesign:
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
    # Convert string to enum if needed (for backward compatibility)
    if isinstance(hand, str):
        hand = Hand(hand.lower())
    if isinstance(profile, str):
        profile = WormProfile(profile.upper())

    # Handle worm_type parameter (converts to globoid boolean)
    if worm_type is not None:
        if isinstance(worm_type, str):
            worm_type = WormType(worm_type.lower())
        globoid = (worm_type == WormType.GLOBOID)

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
        hand=hand.value,  # Pass enum value (string) to helper function
        profile_shift=0.0  # Worm doesn't use profile shift
    )

    # Add worm type to output
    worm["type"] = "globoid" if globoid else "cylindrical"

    # Add globoid-specific parameters if applicable
    if globoid:
        worm["throat_reduction_mm"] = throat_reduction
        # Calculate throat curvature radius (related to wheel pitch radius)
        wheel_pitch_radius = (module * ratio * num_starts) / 2
        worm["throat_curvature_radius_mm"] = wheel_pitch_radius

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

    # Calculate recommended dimensions
    wheel_width_mm = calculate_recommended_wheel_width(
        worm_pitch_diameter_mm=worm["pitch_diameter_mm"],
        module_mm=module
    )
    worm_length_mm = calculate_recommended_worm_length(
        wheel_width_mm=wheel_width_mm,
        lead_mm=worm["lead_mm"]
    )

    # Globoid-specific parameters
    throat_reduction_mm = throat_reduction if globoid else None
    throat_curvature_radius_mm = (module * ratio * num_starts) / 2 if globoid else None

    return _build_design(
        worm_dict=worm,
        wheel_dict=wheel,
        centre_distance_mm=centre_distance,
        pressure_angle_deg=pressure_angle,
        backlash_mm=backlash,
        hand=hand,
        ratio=ratio,
        efficiency_percent=efficiency_percent,
        self_locking=self_locking,
        profile=profile,
        wheel_throated=wheel_throated,
        worm_length_mm=worm_length_mm,
        wheel_width_mm=wheel_width_mm,
        globoid=globoid,
        throat_reduction_mm=throat_reduction_mm,
        throat_curvature_radius_mm=throat_curvature_radius_mm
    )


def design_from_centre_distance(
    centre_distance: float,
    ratio: int,
    worm_to_wheel_ratio: float = 0.3,
    pressure_angle: float = 20.0,
    backlash: float = 0.0,
    num_starts: int = 1,
    clearance_factor: float = 0.25,
    hand: Union[Hand, str] = "right",
    profile_shift: float = 0.0,
    profile: Union[WormProfile, str] = "ZA",
    worm_type: Union[WormType, str, None] = None,
    globoid: bool = False,
    throat_reduction: float = 0.0,
    wheel_throated: bool = False
) -> WormGearDesign:
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
        WormGearDesign with typed parameters
    """
    # Convert string to enum if needed (for backward compatibility)
    if isinstance(hand, str):
        hand = Hand(hand.lower())
    if isinstance(profile, str):
        profile = WormProfile(profile.upper())

    # Handle worm_type parameter (converts to globoid boolean)
    if worm_type is not None:
        if isinstance(worm_type, str):
            worm_type = WormType(worm_type.lower())
        globoid = (worm_type == WormType.GLOBOID)

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
    hand: Union[Hand, str] = "right",
    profile_shift: float = 0.0,
    profile: Union[WormProfile, str] = "ZA",
    worm_type: Union[WormType, str, None] = None,
    globoid: bool = False,
    throat_reduction: float = 0.0,
    wheel_throated: bool = False
) -> WormGearDesign:
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
    # Convert string to enum if needed (for backward compatibility)
    if isinstance(hand, str):
        hand = Hand(hand.lower())
    if isinstance(profile, str):
        profile = WormProfile(profile.upper())

    # Handle worm_type parameter (converts to globoid boolean)
    if worm_type is not None:
        if isinstance(worm_type, str):
            worm_type = WormType(worm_type.lower())
        globoid = (worm_type == WormType.GLOBOID)

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


def design_from_envelope(
    worm_od: float,
    wheel_od: float,
    ratio: int,
    pressure_angle: float = 20.0,
    backlash: float = 0.0,
    num_starts: int = 1,
    clearance_factor: float = 0.25,
    hand: Union[Hand, str] = "right",
    profile_shift: float = 0.0,
    profile: Union[WormProfile, str] = "ZA",
    worm_type: Union[WormType, str, None] = None,
    throat_reduction: float = 0.0,
    wheel_throated: bool = False
) -> WormGearDesign:
    """
    Design worm gear pair from outside diameter constraints (envelope mode).

    Calculates module from wheel OD and worm pitch diameter from worm OD,
    then delegates to design_from_module().

    Args:
        worm_od: Worm outside/tip diameter (mm)
        wheel_od: Wheel outside/tip diameter (mm)
        ratio: Gear ratio (must be divisible by num_starts)
        pressure_angle: Pressure angle (degrees, default 20°)
        backlash: Backlash allowance (mm, default 0)
        num_starts: Number of worm starts (default 1)
        clearance_factor: Bottom clearance factor (default 0.25)
        hand: Thread hand (Hand enum or "right"/"left" string)
        profile_shift: Profile shift coefficient for wheel (default 0.0)
        profile: Tooth profile type (WormProfile enum or "ZA"/"ZK"/"ZI" string)
        worm_type: Worm geometry type (WormType enum or "cylindrical"/"globoid" string)
        throat_reduction: Throat reduction for globoid worms (mm, default 0.0)
        wheel_throated: Whether wheel has throated teeth (default False)

    Returns:
        Design dict with worm, wheel, assembly, and manufacturing sections
    """
    # Convert string to enum if needed
    if isinstance(hand, str):
        hand = Hand(hand.lower())
    if isinstance(profile, str):
        profile = WormProfile(profile.upper())

    # Handle worm_type parameter (converts to globoid boolean)
    globoid = False
    if worm_type is not None:
        if isinstance(worm_type, str):
            worm_type = WormType(worm_type.lower())
        globoid = (worm_type == WormType.GLOBOID)

    # Calculate module from wheel OD
    # tip_diameter = module × (num_teeth + 2)
    num_teeth = ratio * num_starts
    module = wheel_od / (num_teeth + 2)

    # Worm pitch diameter from worm OD
    # tip_diameter = pitch_diameter + 2 × addendum
    # addendum = module (standard)
    addendum = module
    worm_pitch_diameter = worm_od - 2 * addendum

    # Call design_from_module with calculated values
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
        worm_type=worm_type,
        throat_reduction=throat_reduction,
        wheel_throated=wheel_throated
    )
