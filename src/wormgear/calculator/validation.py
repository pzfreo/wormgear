"""
Worm Gear Calculator - Validation Rules

Engineering validation based on:
- DIN 3975 / DIN 3996 standards
- Common engineering practice
- Manufacturing constraints

Ported from wormgearcalc with field naming adapted for wormgear.

This module accepts both dict and dataclass designs, providing
flexible validation for both calculator output (dicts) and
loaded JSON files (dataclasses).
"""

from dataclasses import dataclass, field
from typing import List, Optional, Union, Dict, Any, TYPE_CHECKING
from enum import Enum
from math import sin, radians

from .core import is_standard_module, nearest_standard_module
from ..enums import AntiRotation

# Import for type checking only (avoids circular imports at runtime)
if TYPE_CHECKING:
    from ..io.loaders import WormGearDesign

# Type alias for design input - accepts both dict and WormGearDesign
# Using string literal for forward reference to avoid circular import
DesignInput = Union[Dict[str, Union[Dict, str, float, int, None]], "WormGearDesign"]


def _get(obj: DesignInput, *keys: str, default: Optional[Union[str, float, int, bool]] = None) -> Optional[Union[str, float, int, bool, Dict]]:
    """
    Get nested value from dict or dataclass using dot-notation keys.

    Works with both:
    - Dicts: _get(design, 'worm', 'lead_angle_deg')
    - Dataclasses: _get(design, 'worm', 'lead_angle_deg')

    Args:
        obj: Root object (dict or dataclass)
        *keys: Sequence of keys/attributes to traverse
        default: Value to return if path not found

    Returns:
        Value at path, or default if not found
    """
    current = obj
    for key in keys:
        if current is None:
            return default
        if isinstance(current, dict):
            current = current.get(key, default)
        else:
            current = getattr(current, key, default)
    return current


def calculate_minimum_teeth(pressure_angle_deg: float) -> int:
    """
    Calculate minimum teeth without undercut for given pressure angle.

    Formula: z_min = 2 / sin²(α)

    Args:
        pressure_angle_deg: Pressure angle in degrees

    Returns:
        Minimum number of teeth (rounded up)
    """
    alpha_rad = radians(pressure_angle_deg)
    sin_alpha = sin(alpha_rad)
    z_min = 2.0 / (sin_alpha ** 2)
    return int(z_min) + 1  # Round up for safety


def calculate_recommended_profile_shift(num_teeth: int, pressure_angle_deg: float) -> Optional[float]:
    """
    Calculate recommended profile shift coefficient to avoid undercut.

    Profile shift (x) moves the tooth away from the blank to eliminate undercut.
    Positive shift increases addendum, decreases dedendum.

    Args:
        num_teeth: Number of teeth
        pressure_angle_deg: Pressure angle in degrees

    Returns:
        Recommended profile shift coefficient (dimensionless), or None if not needed
    """
    z_min = calculate_minimum_teeth(pressure_angle_deg)

    if num_teeth >= z_min:
        return None  # No shift needed

    # Formula for minimum profile shift to avoid undercut:
    # x_min = (z_min - z) / z_min
    # We add a small safety factor
    x_min = (z_min - num_teeth) / z_min * 1.1

    # Clamp to reasonable range
    return min(max(x_min, 0.0), 0.8)


class Severity(Enum):
    """Validation message severity"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class ValidationMessage:
    """A single validation finding"""
    severity: Severity
    code: str
    message: str
    suggestion: Optional[str] = None


@dataclass
class ValidationResult:
    """Complete validation result"""
    valid: bool  # True if no errors
    messages: List[ValidationMessage] = field(default_factory=list)

    @property
    def errors(self) -> List[ValidationMessage]:
        return [m for m in self.messages if m.severity == Severity.ERROR]

    @property
    def warnings(self) -> List[ValidationMessage]:
        return [m for m in self.messages if m.severity == Severity.WARNING]

    @property
    def infos(self) -> List[ValidationMessage]:
        return [m for m in self.messages if m.severity == Severity.INFO]


def validate_design(design: DesignInput, bore_settings: Optional[Dict[str, Any]] = None) -> ValidationResult:
    """
    Validate a worm gear design against engineering rules.

    Accepts both dict (from calculator) and WormGearDesign dataclass
    (from load_design_json).

    Args:
        design: Design dict or WormGearDesign dataclass
        bore_settings: Optional bore configuration from UI (for calculator flow)
                      If provided, validates bore against gear dimensions

    Returns:
        ValidationResult with all findings
    """
    messages: List[ValidationMessage] = []

    # Run all validation checks
    messages.extend(_validate_geometry_possible(design))  # Check impossible geometry first
    messages.extend(_validate_lead_angle(design))
    messages.extend(_validate_contact_ratio(design))  # P1.2: DIN 3975 §7.4 contact ratio check
    messages.extend(_validate_module(design))
    messages.extend(_validate_teeth_count(design))
    messages.extend(_validate_worm_proportions(design))
    messages.extend(_validate_pressure_angle(design))
    messages.extend(_validate_efficiency(design))
    messages.extend(_validate_clearance(design))
    messages.extend(_validate_centre_distance(design))
    messages.extend(_validate_profile(design))
    messages.extend(_validate_worm_type(design))
    messages.extend(_validate_wheel_throated(design))
    messages.extend(_validate_manufacturing_compatibility(design))
    messages.extend(_validate_bore(design, bore_settings))

    # Design is valid if no errors
    has_errors = any(m.severity == Severity.ERROR for m in messages)

    return ValidationResult(
        valid=not has_errors,
        messages=messages
    )


def _validate_geometry_possible(design: DesignInput) -> List[ValidationMessage]:
    """Check for impossible geometry (negative root diameters, etc.)"""
    messages = []

    worm_root = _get(design, 'worm', 'root_diameter_mm', default=0)
    wheel_root = _get(design, 'wheel', 'root_diameter_mm', default=0)
    worm_tip = _get(design, 'worm', 'tip_diameter_mm', default=0)
    wheel_tip = _get(design, 'wheel', 'tip_diameter_mm', default=0)

    # Check for negative root diameters (impossible geometry)
    if worm_root < 0:
        messages.append(ValidationMessage(
            severity=Severity.ERROR,
            code="WORM_IMPOSSIBLE_GEOMETRY",
            message=f"Worm has impossible geometry: root diameter ({worm_root:.2f}mm) is negative",
            suggestion="The worm is too small for the module. Increase worm OD or reduce module."
        ))
    elif worm_root == 0:
        messages.append(ValidationMessage(
            severity=Severity.ERROR,
            code="WORM_ZERO_ROOT",
            message="Worm root diameter is zero",
            suggestion="Check worm dimensions - this indicates a calculation error"
        ))

    if wheel_root < 0:
        messages.append(ValidationMessage(
            severity=Severity.ERROR,
            code="WHEEL_IMPOSSIBLE_GEOMETRY",
            message=f"Wheel has impossible geometry: root diameter ({wheel_root:.2f}mm) is negative",
            suggestion="The wheel is too small for the module. Increase wheel OD or reduce module."
        ))
    elif wheel_root == 0:
        messages.append(ValidationMessage(
            severity=Severity.ERROR,
            code="WHEEL_ZERO_ROOT",
            message="Wheel root diameter is zero",
            suggestion="Check wheel dimensions - this indicates a calculation error"
        ))

    # Check that root < tip (sanity check)
    if worm_root > 0 and worm_tip > 0 and worm_root >= worm_tip:
        messages.append(ValidationMessage(
            severity=Severity.ERROR,
            code="WORM_ROOT_EXCEEDS_TIP",
            message=f"Worm root diameter ({worm_root:.2f}mm) >= tip diameter ({worm_tip:.2f}mm)",
            suggestion="This indicates a calculation error - check worm dimensions"
        ))

    if wheel_root > 0 and wheel_tip > 0 and wheel_root >= wheel_tip:
        messages.append(ValidationMessage(
            severity=Severity.ERROR,
            code="WHEEL_ROOT_EXCEEDS_TIP",
            message=f"Wheel root diameter ({wheel_root:.2f}mm) >= tip diameter ({wheel_tip:.2f}mm)",
            suggestion="This indicates a calculation error - check wheel dimensions"
        ))

    # Check wheel tip reduction doesn't eliminate teeth
    wheel_addendum = _get(design, 'wheel', 'addendum_mm', default=0)
    wheel_tip_reduction = _get(design, 'wheel', 'tip_reduction_mm', default=0)
    if wheel_tip_reduction and wheel_addendum and wheel_tip_reduction >= wheel_addendum:
        messages.append(ValidationMessage(
            severity=Severity.ERROR,
            code="WHEEL_TIP_REDUCTION_EXCESSIVE",
            message=f"Wheel tip reduction ({wheel_tip_reduction:.2f}mm) eliminates tooth height (addendum: {wheel_addendum:.2f}mm)",
            suggestion="Reduce tip reduction to less than the wheel addendum"
        ))

    return messages


def _validate_lead_angle(design: DesignInput) -> List[ValidationMessage]:
    """Check lead angle is within practical range"""
    messages = []
    lead_angle = _get(design, 'worm', 'lead_angle_deg', default=0)

    if lead_angle < 1.0:
        messages.append(ValidationMessage(
            severity=Severity.ERROR,
            code="LEAD_ANGLE_TOO_LOW",
            message=f"Lead angle {lead_angle:.1f}° is too low for practical manufacture",
            suggestion="Increase worm pitch diameter or reduce module"
        ))
    elif lead_angle < 3.0:
        efficiency = _get(design, 'assembly', 'efficiency_percent', default=0) or 0
        messages.append(ValidationMessage(
            severity=Severity.WARNING,
            code="LEAD_ANGLE_VERY_LOW",
            message=f"Lead angle {lead_angle:.1f}° is very low. Efficiency ~{efficiency:.0f}%",
            suggestion="Consider increasing worm diameter for better efficiency"
        ))
    elif lead_angle < 5.0:
        efficiency = _get(design, 'assembly', 'efficiency_percent', default=0) or 0
        messages.append(ValidationMessage(
            severity=Severity.INFO,
            code="LEAD_ANGLE_LOW",
            message=f"Lead angle {lead_angle:.1f}° gives low efficiency (~{efficiency:.0f}%) but good self-locking",
            suggestion=None
        ))
    elif lead_angle > 45.0:
        messages.append(ValidationMessage(
            severity=Severity.ERROR,
            code="LEAD_ANGLE_TOO_HIGH",
            message=f"Lead angle {lead_angle:.1f}° exceeds practical limits",
            suggestion="Reduce worm pitch diameter or increase module"
        ))
    elif lead_angle > 25.0:
        messages.append(ValidationMessage(
            severity=Severity.WARNING,
            code="LEAD_ANGLE_HIGH",
            message=f"Lead angle {lead_angle:.1f}° is high. Drive will not self-lock.",
            suggestion="This is fine if self-locking is not required"
        ))

    return messages


def _validate_contact_ratio(design: DesignInput) -> List[ValidationMessage]:
    """
    Contact ratio check — currently disabled.

    The spur gear formula (z × tan(gamma) / (pi × n)) is inappropriate for
    worm gears, which have wrapping contact across multiple teeth. A proper
    worm gear contact ratio depends on face width and addendum geometry.
    Until a correct formula is implemented, this check is a no-op.
    """
    return []


def _validate_module(design: DesignInput) -> List[ValidationMessage]:
    """Check module is standard or flag non-standard"""
    messages = []
    module = _get(design, 'worm', 'module_mm', default=0)

    if module <= 0:
        return messages  # Skip if no module

    if not is_standard_module(module):
        nearest = nearest_standard_module(module)
        deviation = abs(module - nearest) / nearest * 100

        # Only show message if module differs significantly from nearest standard
        # If deviation < 0.1%, user likely already rounded to standard (avoid confusing message)
        if deviation >= 10:
            messages.append(ValidationMessage(
                severity=Severity.WARNING,
                code="MODULE_NON_STANDARD",
                message=f"Module {module:.3f}mm is non-standard (ISO 54)",
                suggestion=f"Nearest standard module: {nearest}mm. Consider adjusting envelope constraints."
            ))
        elif deviation >= 0.1:  # Between 0.1% and 10%
            messages.append(ValidationMessage(
                severity=Severity.INFO,
                code="MODULE_NEAR_STANDARD",
                message=f"Module {module:.3f}mm is close to standard {nearest}mm",
                suggestion=f"Could round to {nearest}mm with minor OD changes"
            ))
        # else: deviation < 0.1%, skip message (already at standard)

    return messages


def _validate_teeth_count(design: DesignInput) -> List[ValidationMessage]:
    """Check wheel teeth count is adequate"""
    messages = []
    num_teeth = _get(design, 'wheel', 'num_teeth', default=0)
    pressure_angle = _get(design, 'assembly', 'pressure_angle_deg', default=20.0)

    if num_teeth <= 0:
        return messages  # Skip if no teeth

    # Check for undercut risk
    z_min = calculate_minimum_teeth(pressure_angle)

    if num_teeth < z_min:
        recommended_shift = calculate_recommended_profile_shift(num_teeth, pressure_angle)
        current_shift = _get(design, 'wheel', 'profile_shift', default=0.0)

        if current_shift < recommended_shift:
            messages.append(ValidationMessage(
                severity=Severity.WARNING,
                code="TEETH_UNDERCUT_RISK",
                message=f"Wheel has {num_teeth} teeth, minimum is {z_min} for {pressure_angle}° pressure angle",
                suggestion=f"Use profile shift coefficient ≥ {recommended_shift:.2f} to avoid undercut (current: {current_shift:.2f})"
            ))
        else:
            messages.append(ValidationMessage(
                severity=Severity.INFO,
                code="TEETH_LOW_WITH_SHIFT",
                message=f"Wheel has {num_teeth} teeth with profile shift {current_shift:.2f} to avoid undercut",
                suggestion=None
            ))

    # Check for extremely low teeth
    if num_teeth < 10:
        messages.append(ValidationMessage(
            severity=Severity.WARNING,
            code="TEETH_VERY_LOW",
            message=f"Wheel has only {num_teeth} teeth. This is unusual for worm gears.",
            suggestion="Consider higher ratio or multi-start worm for better contact ratio"
        ))

    return messages


def _validate_worm_proportions(design: DesignInput) -> List[ValidationMessage]:
    """Check worm proportions are reasonable"""
    messages = []

    pitch_dia = _get(design, 'worm', 'pitch_diameter_mm', default=0)
    module = _get(design, 'worm', 'module_mm', default=0)

    if module <= 0 or pitch_dia <= 0:
        return messages  # Skip if missing values

    # Pitch diameter should be reasonable relative to module
    # Typical range: 8-12 × module (wider than standard gears)
    ratio = pitch_dia / module

    if ratio < 5:
        messages.append(ValidationMessage(
            severity=Severity.WARNING,
            code="WORM_TOO_THIN",
            message=f"Worm pitch diameter ({pitch_dia:.1f}mm) is very small relative to module ({module}mm)",
            suggestion="Increase worm diameter for better strength and contact ratio"
        ))
    elif ratio > 20:
        messages.append(ValidationMessage(
            severity=Severity.WARNING,
            code="WORM_TOO_THICK",
            message=f"Worm pitch diameter ({pitch_dia:.1f}mm) is very large relative to module ({module}mm)",
            suggestion="This is unusual but may be intentional for high lead angles"
        ))

    return messages


def _validate_pressure_angle(design: DesignInput) -> List[ValidationMessage]:
    """Check pressure angle is standard"""
    messages = []
    alpha = _get(design, 'assembly', 'pressure_angle_deg', default=20.0)

    if alpha not in [14.5, 20.0, 25.0]:
        messages.append(ValidationMessage(
            severity=Severity.INFO,
            code="PRESSURE_ANGLE_NON_STANDARD",
            message=f"Pressure angle {alpha}° is non-standard",
            suggestion="Standard values are 14.5°, 20° (most common), or 25°"
        ))

    if alpha < 10:
        messages.append(ValidationMessage(
            severity=Severity.ERROR,
            code="PRESSURE_ANGLE_TOO_LOW",
            message=f"Pressure angle {alpha}° is too low",
            suggestion="Use at least 14.5° for adequate tooth strength"
        ))
    elif alpha > 30:
        messages.append(ValidationMessage(
            severity=Severity.ERROR,
            code="PRESSURE_ANGLE_TOO_HIGH",
            message=f"Pressure angle {alpha}° is too high",
            suggestion="Use 25° or less for worm gears"
        ))

    return messages


def _validate_efficiency(design: DesignInput) -> List[ValidationMessage]:
    """Check efficiency and self-locking behavior"""
    messages = []

    efficiency = _get(design, 'assembly', 'efficiency_percent')
    if efficiency is not None:
        if efficiency < 30:
            messages.append(ValidationMessage(
                severity=Severity.WARNING,
                code="EFFICIENCY_VERY_LOW",
                message=f"Efficiency {efficiency:.0f}% is very low. Much power will be lost as heat.",
                suggestion="Increase lead angle for better efficiency if self-locking not required"
            ))
        # Efficiency 30-50% is normal for self-locking worm gears — no message needed

    return messages


def _validate_clearance(design: DesignInput) -> List[ValidationMessage]:
    """Basic geometric clearance check"""
    messages = []

    # Check that worm and wheel don't interfere
    worm_tip_dia = _get(design, 'worm', 'tip_diameter_mm', default=0)
    wheel_root_dia = _get(design, 'wheel', 'root_diameter_mm', default=0)
    centre_distance = _get(design, 'assembly', 'centre_distance_mm', default=0)

    if worm_tip_dia <= 0 or wheel_root_dia <= 0 or centre_distance <= 0:
        return messages  # Skip if missing values

    worm_tip_radius = worm_tip_dia / 2
    wheel_root_radius = wheel_root_dia / 2

    # For globoid worms, use the throat radius (smaller) for clearance check
    # The full tip_diameter is at the worm ends, not the engagement zone
    throat_reduction = _get(design, 'worm', 'throat_reduction_mm', default=0) or 0
    effective_worm_tip_radius = worm_tip_radius - throat_reduction

    # At centre distance, worm tip should not reach wheel root
    clearance = centre_distance - effective_worm_tip_radius - wheel_root_radius

    if clearance < -0.1:
        # Clearly impossible geometry - significant overlap
        messages.append(ValidationMessage(
            severity=Severity.ERROR,
            code="GEOMETRIC_INTERFERENCE",
            message=f"Worm and wheel geometries interfere (clearance: {clearance:.2f}mm)",
            suggestion="Reduce worm tip diameter, increase centre distance, or adjust profile shift"
        ))
    elif clearance < 0:
        # Marginal overlap - may be within tolerances, especially with profile shift
        messages.append(ValidationMessage(
            severity=Severity.WARNING,
            code="CLEARANCE_MARGINAL",
            message=f"Marginal clearance ({clearance:.2f}mm) between worm tip and wheel root",
            suggestion="Verify manufacturing tolerances can accommodate this fit"
        ))
    elif clearance < 0.05:
        messages.append(ValidationMessage(
            severity=Severity.WARNING,
            code="CLEARANCE_VERY_SMALL",
            message=f"Very tight clearance ({clearance:.2f}mm) between worm tip and wheel root",
            suggestion="Verify backlash and manufacturing tolerances"
        ))

    return messages


def _validate_centre_distance(design: DesignInput) -> List[ValidationMessage]:
    """Check centre distance is reasonable"""
    messages = []
    cd = _get(design, 'assembly', 'centre_distance_mm', default=0)

    if cd <= 0:
        return messages  # Skip if missing

    if cd < 2:
        messages.append(ValidationMessage(
            severity=Severity.WARNING,
            code="CENTRE_DISTANCE_SMALL",
            message=f"Centre distance {cd:.2f}mm is very small",
            suggestion="Verify assembly is practical"
        ))

    return messages


def _normalize_enum(value, case='lower', default=None) -> Optional[str]:
    """Normalize an enum or string value to a consistent case.

    Args:
        value: Enum instance, string, or None
        case: 'lower' or 'upper' for output case
        default: Value to return if input is None

    Returns:
        Normalized string or default
    """
    if value is None:
        return default
    if hasattr(value, 'value'):
        raw = value.value
    else:
        raw = str(value)
    return raw.upper() if case == 'upper' else raw.lower()


def _normalize_profile(profile) -> str:
    """Normalize profile to uppercase string for comparison."""
    return _normalize_enum(profile, case='upper')


def _validate_profile(design: DesignInput) -> List[ValidationMessage]:
    """Check profile type is valid"""
    messages = []

    # Profile is in manufacturing section
    profile_raw = _get(design, 'manufacturing', 'profile')
    profile = _normalize_profile(profile_raw)
    if profile is None:
        return messages  # Profile is optional

    valid_profiles = ['ZA', 'ZK', 'ZI']
    if profile not in valid_profiles:
        messages.append(ValidationMessage(
            severity=Severity.ERROR,
            code="PROFILE_INVALID",
            message=f"Invalid profile type: {profile}",
            suggestion="Use ZA (for CNC machining), ZK (for 3D printing), or ZI (for hobbing)"
        ))
        return messages

    return messages


def _normalize_worm_type(worm_type) -> str:
    """Normalize worm type to lowercase string, defaulting to 'cylindrical'."""
    return _normalize_enum(worm_type, default='cylindrical')


def _validate_worm_type(design: DesignInput) -> List[ValidationMessage]:
    """Check worm type and related parameters for globoid worms"""
    messages = []

    worm_type_raw = _get(design, 'worm', 'type')
    worm_type = _normalize_worm_type(worm_type_raw)

    valid_types = ['cylindrical', 'globoid']
    if worm_type not in valid_types:
        messages.append(ValidationMessage(
            severity=Severity.ERROR,
            code="WORM_TYPE_INVALID",
            message=f"Invalid worm type: {worm_type}",
            suggestion="Use cylindrical or globoid"
        ))
        return messages

    # Globoid-specific validations — only warn about out-of-range throat reduction
    if worm_type == 'globoid':
        throat_reduction = _get(design, 'worm', 'throat_reduction_mm')
        module_mm = _get(design, 'worm', 'module_mm', default=2.0)

        if throat_reduction is not None and throat_reduction > 0 and module_mm > 0:
            if throat_reduction < module_mm * 0.3:
                messages.append(ValidationMessage(
                    severity=Severity.WARNING,
                    code="THROAT_REDUCTION_SMALL",
                    message=f"Throat reduction ({throat_reduction:.2f}mm) is less than 0.3x module ({module_mm * 0.3:.2f}mm)",
                    suggestion="May result in minimal hourglass effect and reduced wheel contact"
                ))
            elif throat_reduction > module_mm * 2.5:
                messages.append(ValidationMessage(
                    severity=Severity.WARNING,
                    code="THROAT_REDUCTION_LARGE",
                    message=f"Throat reduction ({throat_reduction:.2f}mm) exceeds 2.5x module ({module_mm * 2.5:.2f}mm)",
                    suggestion="May cause interference or manufacturing difficulty"
                ))

        # Teeth-in-arc validation for user-specified arc angle
        arc_angle_deg = _get(design, 'worm', 'throat_arc_angle_deg')
        num_teeth = _get(design, 'wheel', 'num_teeth', default=0)
        if arc_angle_deg is not None and arc_angle_deg > 0 and num_teeth > 0:
            teeth_in_arc = num_teeth * arc_angle_deg / 360.0
            rounded_teeth = round(teeth_in_arc)
            if abs(teeth_in_arc - rounded_teeth) > 0.01:
                # Suggest nearest integer options
                lower_teeth = max(1, int(teeth_in_arc))
                upper_teeth = lower_teeth + 1
                lower_angle = round(360.0 * lower_teeth / num_teeth, 1)
                upper_angle = round(360.0 * upper_teeth / num_teeth, 1)
                messages.append(ValidationMessage(
                    severity=Severity.WARNING,
                    code="TEETH_IN_ARC_NON_INTEGER",
                    message=f"Teeth in arc ({teeth_in_arc:.2f}) is not a whole number",
                    suggestion=(
                        f"For optimal meshing, adjust arc angle to "
                        f"{lower_angle}\u00b0 ({lower_teeth} teeth) or "
                        f"{upper_angle}\u00b0 ({upper_teeth} teeth)"
                    )
                ))

    return messages


def _validate_wheel_throated(design: DesignInput) -> List[ValidationMessage]:
    """Check wheel throated setting is appropriate for worm type"""
    messages = []

    worm_type_raw = _get(design, 'worm', 'type')
    worm_type = _normalize_worm_type(worm_type_raw)

    wheel_throated = _get(design, 'manufacturing', 'throated_wheel', default=False)
    virtual_hobbing = _get(design, 'manufacturing', 'virtual_hobbing', default=False)

    return messages


def _validate_manufacturing_compatibility(design: DesignInput) -> List[ValidationMessage]:
    """Check manufacturing parameters are reasonable"""
    messages = []

    worm_length = _get(design, 'manufacturing', 'worm_length_mm')
    wheel_width = _get(design, 'manufacturing', 'wheel_width_mm')
    lead = _get(design, 'worm', 'lead_mm', default=0)

    # Skip if manufacturing dimensions not specified
    if worm_length is None or wheel_width is None:
        return messages

    # Check worm length provides adequate engagement
    if lead > 0 and worm_length < wheel_width + lead:
        messages.append(ValidationMessage(
            severity=Severity.WARNING,
            code="WORM_LENGTH_SHORT",
            message=f"Worm length {worm_length:.2f}mm may not provide full engagement with wheel width {wheel_width:.2f}mm",
            suggestion=f"Consider increasing to at least {wheel_width + lead + 1:.2f}mm (width + lead + margin)"
        ))

    return messages


def _normalize_bore_type(bore_type) -> Optional[str]:
    """Normalize bore_type to lowercase string for comparison."""
    return _normalize_enum(bore_type)


# DIN 6885 keyway depths (subset for validation)
# Format: bore_range: (shaft_depth, hub_depth) in mm
_KEYWAY_DEPTHS = {
    (6, 8): (1.2, 1.0),
    (8, 10): (1.8, 1.4),
    (10, 12): (2.5, 1.8),
    (12, 17): (3.0, 2.3),
    (17, 22): (3.5, 2.8),
    (22, 30): (4.0, 3.3),
    (30, 38): (5.0, 3.3),
    (38, 44): (5.0, 3.3),
    (44, 50): (5.5, 3.8),
    (50, 58): (6.0, 4.3),
    (58, 65): (7.0, 4.4),
    (65, 75): (7.5, 4.9),
    (75, 85): (9.0, 5.4),
    (85, 95): (9.0, 5.4),
}


def _get_keyway_depth(bore_diameter: float, is_shaft: bool) -> float:
    """Get keyway depth for a bore diameter. Returns 0 if bore is below DIN 6885 range."""
    for (min_d, max_d), (shaft_depth, hub_depth) in _KEYWAY_DEPTHS.items():
        if min_d <= bore_diameter < max_d:
            return shaft_depth if is_shaft else hub_depth
    return 0.0  # No keyway for bores outside standard range


# Import canonical constants from constants.py, map to names used locally
from .constants import (
    MIN_RIM_THICKNESS_MM,
    WARN_RIM_WORM_MM,
    WARN_RIM_WHEEL_MM,
    SMALL_BORE_THRESHOLD_MM,
)
MIN_RIM_WORM = MIN_RIM_THICKNESS_MM
MIN_RIM_WHEEL = MIN_RIM_THICKNESS_MM
WARN_RIM_WORM = WARN_RIM_WORM_MM
WARN_RIM_WHEEL = WARN_RIM_WHEEL_MM
SMALL_BORE_THRESHOLD = SMALL_BORE_THRESHOLD_MM


def _validate_single_bore(
    messages, part_name, bore_type, bore_diameter, keyway,
    pitch_diameter, root_diameter, min_rim, warn_rim, is_shaft
):
    """Validate bore configuration for a single part (worm or wheel).

    Appends ValidationMessages to the messages list. Part_name is 'WORM' or 'WHEEL'.
    """
    from ..core.bore_sizing import calculate_default_bore

    part_lower = part_name.lower()
    if bore_type != 'custom' or root_diameter <= 0:
        return

    # Get actual bore diameter (auto-calculate if null)
    if bore_diameter is None:
        bore_calc, has_warning = calculate_default_bore(pitch_diameter, root_diameter)
        if bore_calc is None:
            messages.append(ValidationMessage(
                severity=Severity.INFO,
                code=f"{part_name}_TOO_SMALL_FOR_BORE",
                message=f"{part_lower.title()} is too small for a bore (root: {root_diameter:.1f}mm, min bore: 0.5mm)",
                suggestion=f"Consider a larger {part_lower} design if a bore is required"
            ))
            return
        bore_diameter = bore_calc

    if bore_diameter is None or bore_diameter <= 0:
        return

    # Calculate rim thickness
    rim_base = (root_diameter - bore_diameter) / 2
    keyway_depth = 0.0

    # Account for keyway if specified
    if keyway and keyway.upper() == 'DIN6885':
        keyway_depth = _get_keyway_depth(bore_diameter, is_shaft=is_shaft)

    effective_rim = rim_base - keyway_depth

    # Validate
    if bore_diameter >= root_diameter:
        messages.append(ValidationMessage(
            severity=Severity.ERROR,
            code=f"{part_name}_BORE_TOO_LARGE",
            message=f"{part_lower.title()} bore ({bore_diameter:.1f}mm) exceeds root diameter ({root_diameter:.1f}mm)",
            suggestion=f"Maximum bore is less than {root_diameter:.1f}mm"
        ))
    elif effective_rim < min_rim:
        if keyway_depth > 0:
            messages.append(ValidationMessage(
                severity=Severity.ERROR,
                code=f"{part_name}_BORE_KEYWAY_INTERFERENCE",
                message=f"{part_lower.title()} bore {bore_diameter:.1f}mm with keyway (depth {keyway_depth:.1f}mm) leaves only {effective_rim:.2f}mm rim",
                suggestion=f"Reduce bore to allow at least {min_rim}mm rim after keyway, or use DD-cut instead"
            ))
        else:
            messages.append(ValidationMessage(
                severity=Severity.ERROR,
                code=f"{part_name}_BORE_TOO_LARGE",
                message=f"{part_lower.title()} bore ({bore_diameter:.1f}mm) leaves insufficient rim ({rim_base:.2f}mm)",
                suggestion=f"Reduce bore to allow at least {min_rim}mm rim"
            ))
    elif effective_rim < warn_rim:
        if keyway_depth > 0:
            messages.append(ValidationMessage(
                severity=Severity.WARNING,
                code=f"{part_name}_BORE_THIN_RIM_KEYWAY",
                message=f"{part_lower.title()} rim is thin ({effective_rim:.2f}mm after {keyway_depth:.1f}mm keyway)",
                suggestion=f"Consider smaller bore or DD-cut for better strength"
            ))
        else:
            messages.append(ValidationMessage(
                severity=Severity.WARNING,
                code=f"{part_name}_BORE_THIN_RIM",
                message=f"{part_lower.title()} rim is thin ({rim_base:.2f}mm) with bore {bore_diameter:.1f}mm",
                suggestion=f"Consider reducing bore for adequate strength"
            ))
    elif keyway_depth > 0:
        # Bore with keyway is OK — emit info message
        messages.append(ValidationMessage(
            severity=Severity.INFO,
            code=f"{part_name}_BORE_OK",
            message=f"{part_lower.title()} bore {bore_diameter:.1f}mm with DIN6885 keyway: {effective_rim:.2f}mm effective rim",
            suggestion=None
        ))

    # Additional warnings for small bores
    if bore_diameter < SMALL_BORE_THRESHOLD:
        messages.append(ValidationMessage(
            severity=Severity.WARNING,
            code=f"{part_name}_BORE_VERY_SMALL",
            message=f"{part_lower.title()} bore ({bore_diameter:.1f}mm) is below {SMALL_BORE_THRESHOLD}mm",
            suggestion="Very small bores may be difficult to machine. Consider reaming or EDM."
        ))
        if keyway and keyway.upper() == 'DDCUT':
            messages.append(ValidationMessage(
                severity=Severity.WARNING,
                code=f"{part_name}_DDCUT_SMALL_BORE",
                message=f"DD-cut on small bore ({bore_diameter:.1f}mm) may be impractical",
                suggestion="Consider no anti-rotation feature or a custom keyway design"
            ))


def _validate_bore_from_settings(design: DesignInput, bore_settings: Dict[str, Any]) -> List[ValidationMessage]:
    """Validate bore from UI settings (calculator flow).

    This is called when design.features isn't populated yet but we have
    bore_settings from the UI.
    """
    from ..core.bore_sizing import calculate_default_bore

    messages = []

    # Extract worm dimensions
    worm_pitch = _get(design, 'worm', 'pitch_diameter_mm', default=0)
    worm_root = _get(design, 'worm', 'root_diameter_mm', default=0)

    # Extract wheel dimensions
    wheel_pitch = _get(design, 'wheel', 'pitch_diameter_mm', default=0)
    wheel_root = _get(design, 'wheel', 'root_diameter_mm', default=0)

    # Note: Impossible geometry (negative root diameters) is already checked
    # by _validate_geometry_possible() which runs first

    # Extract bore settings
    worm_bore_type = bore_settings.get('worm_bore_type', 'none')
    worm_bore_diameter = bore_settings.get('worm_bore_diameter')
    worm_keyway = bore_settings.get('worm_keyway', 'none')

    wheel_bore_type = bore_settings.get('wheel_bore_type', 'none')
    wheel_bore_diameter = bore_settings.get('wheel_bore_diameter')
    wheel_keyway = bore_settings.get('wheel_keyway', 'none')

    # Validate worm bore
    _validate_single_bore(
        messages, "WORM", worm_bore_type, worm_bore_diameter, worm_keyway,
        worm_pitch, worm_root, MIN_RIM_WORM, WARN_RIM_WORM, is_shaft=True
    )

    # Validate wheel bore
    _validate_single_bore(
        messages, "WHEEL", wheel_bore_type, wheel_bore_diameter, wheel_keyway,
        wheel_pitch, wheel_root, MIN_RIM_WHEEL, WARN_RIM_WHEEL, is_shaft=False
    )

    return messages


def _validate_bore(design: DesignInput, bore_settings: Optional[Dict[str, Any]] = None) -> List[ValidationMessage]:
    """Validate bore configuration for worm and wheel.

    Checks:
    - bore_type is present when features section exists
    - bore_diameter_mm is present when bore_type is 'custom'
    - Bore doesn't exceed root diameter (impossible geometry)
    - Warns if rim is thin (accounting for keyway depth)
    - Warns if gear is too small for auto-calculated bore

    Args:
        design: Design dict or WormGearDesign dataclass
        bore_settings: Optional bore configuration from UI. If provided, used when
                      design.features is not yet populated (calculator flow).
                      Expected keys: worm_bore_type, worm_bore_diameter, worm_keyway,
                                    wheel_bore_type, wheel_bore_diameter, wheel_keyway
    """
    messages = []

    worm_features = _get(design, 'features', 'worm')
    wheel_features = _get(design, 'features', 'wheel')

    # Calculator flow: no features yet, use bore_settings
    if bore_settings and worm_features is None and wheel_features is None:
        messages.extend(_validate_bore_from_settings(design, bore_settings))
        return messages

    # Loaded JSON flow: validate each part via _validate_single_bore
    for part_name, features_key, min_rim, warn_rim, is_shaft in [
        ("WORM", "worm", MIN_RIM_WORM, WARN_RIM_WORM, True),
        ("WHEEL", "wheel", MIN_RIM_WHEEL, WARN_RIM_WHEEL, False),
    ]:
        features = _get(design, 'features', features_key)
        if features is None:
            continue

        bore_type = _normalize_bore_type(_get(design, 'features', features_key, 'bore_type'))
        bore_diameter = _get(design, 'features', features_key, 'bore_diameter_mm')
        root_diameter = _get(design, features_key, 'root_diameter_mm', default=0)
        anti_rot = _get(design, 'features', features_key, 'anti_rotation')
        part_lower = part_name.lower()

        # bore_type missing check
        if bore_type is None:
            messages.append(ValidationMessage(
                severity=Severity.ERROR,
                code=f"{part_name}_BORE_TYPE_MISSING",
                message=f"{part_lower.title()} features section exists but bore_type is not specified",
                suggestion="Set bore_type to 'none' for solid part or 'custom' with bore_diameter_mm"
            ))
            continue

        # bore_type == 'none': check if gear is too small for any bore
        if bore_type == 'none':
            pitch_diameter = _get(design, features_key, 'pitch_diameter_mm', default=0)
            if pitch_diameter > 0 and root_diameter > 0:
                from ..core.bore_sizing import calculate_default_bore
                auto_bore, _ = calculate_default_bore(pitch_diameter, root_diameter)
                if auto_bore is None:
                    messages.append(ValidationMessage(
                        severity=Severity.INFO,
                        code=f"{part_name}_TOO_SMALL_FOR_BORE",
                        message=f"{part_lower.title()} is too small for a bore (root: {root_diameter:.1f}mm, min bore: 0.5mm)",
                        suggestion=f"Consider a larger {part_lower} design if a bore is required"
                    ))
            continue

        if bore_type == 'custom' and bore_diameter is None:
            messages.append(ValidationMessage(
                severity=Severity.ERROR,
                code=f"{part_name}_BORE_DIAMETER_MISSING",
                message=f"{part_lower.title()} bore_type is 'custom' but bore_diameter_mm is not specified",
                suggestion="Specify bore_diameter_mm or set bore_type to 'none'"
            ))
            continue

        # Convert anti_rotation to keyway string for _validate_single_bore
        keyway = 'none'
        if anti_rot and (anti_rot == AntiRotation.DIN6885 or str(anti_rot).upper() == 'DIN6885'):
            keyway = 'DIN6885'

        pitch_diameter = _get(design, features_key, 'pitch_diameter_mm', default=0)

        # Delegate rim-thickness validation to shared helper
        _validate_single_bore(
            messages, part_name, bore_type, bore_diameter, keyway,
            pitch_diameter, root_diameter, min_rim, warn_rim, is_shaft
        )

    return messages
