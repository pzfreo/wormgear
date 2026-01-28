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
    elif lead_angle > 25.0:
        messages.append(ValidationMessage(
            severity=Severity.WARNING,
            code="LEAD_ANGLE_HIGH",
            message=f"Lead angle {lead_angle:.1f}° is high. Drive will not self-lock.",
            suggestion="This is fine if self-locking is not required"
        ))
    elif lead_angle > 45.0:
        messages.append(ValidationMessage(
            severity=Severity.ERROR,
            code="LEAD_ANGLE_TOO_HIGH",
            message=f"Lead angle {lead_angle:.1f}° exceeds practical limits",
            suggestion="Reduce worm pitch diameter or increase module"
        ))

    return messages


def _validate_contact_ratio(design: DesignInput) -> List[ValidationMessage]:
    """
    Check contact ratio is sufficient for smooth operation.

    Per DIN 3975 §7.4 and AGMA 6022, the contact ratio (epsilon) should be
    at least 1.2 for smooth, continuous power transmission.

    For worm gears, contact ratio is approximated as:
    epsilon = (wheel_teeth * tan(lead_angle)) / (pi * num_starts)

    A higher contact ratio means more teeth in mesh at any time,
    resulting in smoother operation and higher load capacity.
    """
    messages = []

    # Get required parameters
    wheel_teeth = _get(design, 'wheel', 'num_teeth', default=0)
    num_starts = _get(design, 'worm', 'num_starts', default=1)
    lead_angle_deg = _get(design, 'worm', 'lead_angle_deg', default=0)

    if wheel_teeth <= 0 or lead_angle_deg <= 0:
        return messages  # Skip if data is incomplete

    # Calculate approximate contact ratio for worm gears
    from math import tan, radians, pi
    lead_angle_rad = radians(lead_angle_deg)

    # Simplified contact ratio approximation for worm gears
    # More accurate calculation would require face width and addendum data
    contact_ratio = (wheel_teeth * tan(lead_angle_rad)) / (pi * num_starts)

    # Also consider the effective tooth overlap from geometry
    # Minimum acceptable per AGMA 6022
    MIN_CONTACT_RATIO = 1.2

    if contact_ratio < 1.0:
        messages.append(ValidationMessage(
            severity=Severity.ERROR,
            code="CONTACT_RATIO_TOO_LOW",
            message=f"Calculated contact ratio {contact_ratio:.2f} < 1.0. "
                    f"Teeth will not maintain continuous contact.",
            suggestion="Increase wheel teeth count or lead angle for smoother operation. "
                       "DIN 3975 §7.4 recommends contact ratio >= 1.2"
        ))
    elif contact_ratio < MIN_CONTACT_RATIO:
        messages.append(ValidationMessage(
            severity=Severity.WARNING,
            code="CONTACT_RATIO_LOW",
            message=f"Contact ratio {contact_ratio:.2f} is below recommended {MIN_CONTACT_RATIO}. "
                    f"Operation may be rough or noisy.",
            suggestion="For smoother operation, increase wheel teeth or lead angle"
        ))

    return messages


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
    if num_teeth < 12:
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
        elif efficiency < 50:
            messages.append(ValidationMessage(
                severity=Severity.INFO,
                code="EFFICIENCY_LOW",
                message=f"Efficiency {efficiency:.0f}% is low but typical for self-locking drives",
                suggestion=None
            ))

    self_locking = _get(design, 'assembly', 'self_locking', default=False)
    if self_locking:
        messages.append(ValidationMessage(
            severity=Severity.INFO,
            code="SELF_LOCKING",
            message="Drive is self-locking (backdrive prevented)",
            suggestion="Ensure adequate lubrication to minimize heat from friction"
        ))

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

    # At centre distance, worm tip should not reach wheel root
    clearance = centre_distance - worm_tip_radius - wheel_root_radius

    if clearance < 0:
        messages.append(ValidationMessage(
            severity=Severity.ERROR,
            code="GEOMETRIC_INTERFERENCE",
            message=f"Worm and wheel geometries interfere (clearance: {clearance:.2f}mm)",
            suggestion="Check calculator inputs - this geometry is impossible"
        ))
    elif clearance < 0.1:
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

    if cd < 5:
        messages.append(ValidationMessage(
            severity=Severity.WARNING,
            code="CENTRE_DISTANCE_SMALL",
            message=f"Centre distance {cd:.2f}mm is very small",
            suggestion="Verify assembly is practical"
        ))

    return messages


def _normalize_profile(profile) -> str:
    """Normalize profile to string for comparison."""
    if profile is None:
        return None
    # Handle enum values
    if hasattr(profile, 'value'):
        return profile.value.upper()
    return str(profile).upper()


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

    # Info about profile type
    if profile == 'ZK':
        messages.append(ValidationMessage(
            severity=Severity.INFO,
            code="PROFILE_ZK",
            message="ZK profile selected - optimized for 3D printing (FDM)",
            suggestion=None
        ))
    elif profile == 'ZI':
        messages.append(ValidationMessage(
            severity=Severity.INFO,
            code="PROFILE_ZI",
            message="ZI profile selected - involute helicoid for high precision hobbed gears",
            suggestion=None
        ))

    return messages


def _normalize_worm_type(worm_type) -> str:
    """Normalize worm type to string for comparison."""
    if worm_type is None:
        return 'cylindrical'  # Default
    # Handle enum values
    if hasattr(worm_type, 'value'):
        return worm_type.value.lower()
    return str(worm_type).lower()


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

    # Globoid-specific validations
    if worm_type == 'globoid':
        throat_reduction = _get(design, 'worm', 'throat_reduction_mm')
        throat_curvature = _get(design, 'worm', 'throat_curvature_radius_mm')
        worm_pitch_diameter = _get(design, 'worm', 'pitch_diameter_mm', default=16.0)
        wheel_pitch_diameter = _get(design, 'wheel', 'pitch_diameter_mm', default=60.0)
        centre_distance = _get(design, 'assembly', 'centre_distance_mm', default=38.0)

        # Check throat parameters are present
        if throat_curvature is None:
            messages.append(ValidationMessage(
                severity=Severity.WARNING,
                code="GLOBOID_MISSING_THROAT",
                message="Globoid worm without throat curvature radius specified",
                suggestion="Ensure throat radii are calculated for proper geometry"
            ))
        else:
            # Calculate geometrically correct throat reduction
            # throat_reduction = worm_pitch_radius - (center_distance - wheel_pitch_radius)
            worm_pitch_radius = worm_pitch_diameter / 2
            wheel_pitch_radius = wheel_pitch_diameter / 2
            geometric_reduction = worm_pitch_radius - (centre_distance - wheel_pitch_radius)
            if geometric_reduction <= 0:
                geometric_reduction = worm_pitch_diameter * 0.02  # fallback

            # Validate throat reduction value if present
            if throat_reduction is not None and throat_reduction > 0:
                hourglass_depth = throat_reduction * 2
                messages.append(ValidationMessage(
                    severity=Severity.INFO,
                    code="THROAT_REDUCTION_SET",
                    message=f"Throat reduction: {throat_reduction:.2f}mm (hourglass depth ~{hourglass_depth:.2f}mm)",
                    suggestion=f"Geometric value: {geometric_reduction:.2f}mm"
                ))

                # Warn if significantly different from geometric value
                if throat_reduction < geometric_reduction * 0.5:
                    messages.append(ValidationMessage(
                        severity=Severity.WARNING,
                        code="THROAT_REDUCTION_SMALL",
                        message=f"Throat reduction is smaller than geometric optimum ({geometric_reduction:.2f}mm)",
                        suggestion="May result in reduced wheel contact"
                    ))
                elif throat_reduction > geometric_reduction * 2:
                    messages.append(ValidationMessage(
                        severity=Severity.WARNING,
                        code="THROAT_REDUCTION_LARGE",
                        message=f"Throat reduction is larger than geometric optimum ({geometric_reduction:.2f}mm)",
                        suggestion="May cause interference or manufacturing difficulty"
                    ))
            else:
                # Using auto value
                messages.append(ValidationMessage(
                    severity=Severity.INFO,
                    code="THROAT_REDUCTION_AUTO",
                    message=f"Using geometric throat reduction: {geometric_reduction:.2f}mm",
                    suggestion=f"Formula: worm_r - (CD - wheel_r) = {worm_pitch_radius:.1f} - ({centre_distance:.1f} - {wheel_pitch_radius:.1f})"
                ))

            # Info about globoid benefits
            messages.append(ValidationMessage(
                severity=Severity.INFO,
                code="GLOBOID_WORM",
                message="Globoid worm provides better contact area with wheel",
                suggestion="Use with virtual hobbing for best wheel tooth fit"
            ))

    return messages


def _validate_wheel_throated(design: DesignInput) -> List[ValidationMessage]:
    """Check wheel throated setting is appropriate for worm type"""
    messages = []

    worm_type_raw = _get(design, 'worm', 'type')
    worm_type = _normalize_worm_type(worm_type_raw)

    wheel_throated = _get(design, 'manufacturing', 'throated_wheel', default=False)
    virtual_hobbing = _get(design, 'manufacturing', 'virtual_hobbing', default=False)

    # Info if globoid worm with non-throated wheel (unless using virtual hobbing)
    # Virtual hobbing automatically creates proper throating regardless of wheel_throated flag
    # This is INFO not WARNING because user may deliberately choose helical for manufacturing reasons
    if worm_type == 'globoid' and not wheel_throated and not virtual_hobbing:
        messages.append(ValidationMessage(
            severity=Severity.INFO,
            code="GLOBOID_NON_THROATED",
            message="Globoid worm with helical (non-throated) wheel - contact may be suboptimal",
            suggestion="Consider enabling throated wheel or using virtual hobbing for better mesh"
        ))

    # Info about throated wheel
    if wheel_throated:
        messages.append(ValidationMessage(
            severity=Severity.INFO,
            code="WHEEL_THROATED",
            message="Throated wheel teeth provide better contact area",
            suggestion=None
        ))

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

    # Info about recommendations
    messages.append(ValidationMessage(
        severity=Severity.INFO,
        code="MANUFACTURING_RECOMMENDATIONS",
        message=f"Recommended: wheel width {wheel_width:.2f}mm, worm length {worm_length:.2f}mm",
        suggestion="These are design guidelines based on contact ratio and engagement - adjust as needed"
    ))

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
    if bore_type is None:
        return None
    # Handle enum values
    if hasattr(bore_type, 'value'):
        return bore_type.value.lower()
    return str(bore_type).lower()


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


# Minimum rim thicknesses for safety
MIN_RIM_WORM = 0.5   # 0.5mm absolute minimum rim for worm (small gears)
MIN_RIM_WHEEL = 0.5  # 0.5mm absolute minimum rim for wheel (small gears)
WARN_RIM_WORM = 1.5  # Warning threshold for worm (practical)
WARN_RIM_WHEEL = 2.0  # Warning threshold for wheel (practical)

# Small bore threshold - below this, machining becomes impractical
SMALL_BORE_THRESHOLD = 2.0


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
    if worm_bore_type == 'custom' and worm_root > 0:
        # Get actual bore diameter (auto-calculate if null)
        if worm_bore_diameter is None:
            worm_bore, has_warning = calculate_default_bore(worm_pitch, worm_root)
            if worm_bore is None:
                messages.append(ValidationMessage(
                    severity=Severity.INFO,
                    code="WORM_TOO_SMALL_FOR_BORE",
                    message=f"Worm is too small for a bore (root: {worm_root:.1f}mm, min bore: 0.5mm)",
                    suggestion="Consider a larger worm design if a bore is required"
                ))
            else:
                worm_bore_diameter = worm_bore
        else:
            has_warning = False

        if worm_bore_diameter is not None and worm_bore_diameter > 0:
            # Calculate rim thickness
            rim_base = (worm_root - worm_bore_diameter) / 2
            keyway_depth = 0.0

            # Account for keyway if specified
            if worm_keyway and worm_keyway.upper() == 'DIN6885':
                keyway_depth = _get_keyway_depth(worm_bore_diameter, is_shaft=True)

            effective_rim = rim_base - keyway_depth

            # Validate
            if worm_bore_diameter >= worm_root:
                messages.append(ValidationMessage(
                    severity=Severity.ERROR,
                    code="WORM_BORE_TOO_LARGE",
                    message=f"Worm bore ({worm_bore_diameter:.1f}mm) exceeds root diameter ({worm_root:.1f}mm)",
                    suggestion=f"Maximum bore is less than {worm_root:.1f}mm"
                ))
            elif effective_rim < MIN_RIM_WORM:
                if keyway_depth > 0:
                    messages.append(ValidationMessage(
                        severity=Severity.ERROR,
                        code="WORM_BORE_KEYWAY_INTERFERENCE",
                        message=f"Worm bore {worm_bore_diameter:.1f}mm with keyway (depth {keyway_depth:.1f}mm) leaves only {effective_rim:.2f}mm rim",
                        suggestion=f"Reduce bore to allow at least {MIN_RIM_WORM}mm rim after keyway, or use DD-cut instead"
                    ))
                else:
                    messages.append(ValidationMessage(
                        severity=Severity.ERROR,
                        code="WORM_BORE_TOO_LARGE",
                        message=f"Worm bore ({worm_bore_diameter:.1f}mm) leaves insufficient rim ({rim_base:.2f}mm)",
                        suggestion=f"Reduce bore to allow at least {MIN_RIM_WORM}mm rim"
                    ))
            elif effective_rim < WARN_RIM_WORM:
                if keyway_depth > 0:
                    messages.append(ValidationMessage(
                        severity=Severity.WARNING,
                        code="WORM_BORE_THIN_RIM_KEYWAY",
                        message=f"Worm rim is thin ({effective_rim:.2f}mm after {keyway_depth:.1f}mm keyway)",
                        suggestion=f"Consider smaller bore or DD-cut for better strength"
                    ))
                else:
                    messages.append(ValidationMessage(
                        severity=Severity.WARNING,
                        code="WORM_BORE_THIN_RIM",
                        message=f"Worm rim is thin ({rim_base:.2f}mm) with bore {worm_bore_diameter:.1f}mm",
                        suggestion=f"Consider reducing bore for adequate strength"
                    ))

            # Additional warnings for small bores
            if worm_bore_diameter < SMALL_BORE_THRESHOLD:
                messages.append(ValidationMessage(
                    severity=Severity.WARNING,
                    code="WORM_BORE_VERY_SMALL",
                    message=f"Worm bore ({worm_bore_diameter:.1f}mm) is below {SMALL_BORE_THRESHOLD}mm",
                    suggestion="Very small bores may be difficult to machine. Consider reaming or EDM."
                ))
                # Check for DD-cut with small bore
                if worm_keyway and worm_keyway.upper() == 'DDCUT':
                    messages.append(ValidationMessage(
                        severity=Severity.WARNING,
                        code="WORM_DDCUT_SMALL_BORE",
                        message=f"DD-cut on small bore ({worm_bore_diameter:.1f}mm) may be impractical",
                        suggestion="Consider no anti-rotation feature or a custom keyway design"
                    ))

    # Validate wheel bore
    if wheel_bore_type == 'custom' and wheel_root > 0:
        # Get actual bore diameter (auto-calculate if null)
        if wheel_bore_diameter is None:
            wheel_bore, has_warning = calculate_default_bore(wheel_pitch, wheel_root)
            if wheel_bore is None:
                messages.append(ValidationMessage(
                    severity=Severity.INFO,
                    code="WHEEL_TOO_SMALL_FOR_BORE",
                    message=f"Wheel is too small for a bore (root: {wheel_root:.1f}mm, min bore: 0.5mm)",
                    suggestion="Consider a larger wheel design if a bore is required"
                ))
            else:
                wheel_bore_diameter = wheel_bore
        else:
            has_warning = False

        if wheel_bore_diameter is not None and wheel_bore_diameter > 0:
            # Calculate rim thickness
            rim_base = (wheel_root - wheel_bore_diameter) / 2
            keyway_depth = 0.0

            # Account for keyway if specified
            if wheel_keyway and wheel_keyway.upper() == 'DIN6885':
                keyway_depth = _get_keyway_depth(wheel_bore_diameter, is_shaft=False)

            effective_rim = rim_base - keyway_depth

            # Validate
            if wheel_bore_diameter >= wheel_root:
                messages.append(ValidationMessage(
                    severity=Severity.ERROR,
                    code="WHEEL_BORE_TOO_LARGE",
                    message=f"Wheel bore ({wheel_bore_diameter:.1f}mm) exceeds root diameter ({wheel_root:.1f}mm)",
                    suggestion=f"Maximum bore is less than {wheel_root:.1f}mm"
                ))
            elif effective_rim < MIN_RIM_WHEEL:
                if keyway_depth > 0:
                    messages.append(ValidationMessage(
                        severity=Severity.ERROR,
                        code="WHEEL_BORE_KEYWAY_INTERFERENCE",
                        message=f"Wheel bore {wheel_bore_diameter:.1f}mm with keyway (depth {keyway_depth:.1f}mm) leaves only {effective_rim:.2f}mm rim",
                        suggestion=f"Reduce bore to allow at least {MIN_RIM_WHEEL}mm rim after keyway, or use DD-cut instead"
                    ))
                else:
                    messages.append(ValidationMessage(
                        severity=Severity.ERROR,
                        code="WHEEL_BORE_TOO_LARGE",
                        message=f"Wheel bore ({wheel_bore_diameter:.1f}mm) leaves insufficient rim ({rim_base:.2f}mm)",
                        suggestion=f"Reduce bore to allow at least {MIN_RIM_WHEEL}mm rim"
                    ))
            elif effective_rim < WARN_RIM_WHEEL:
                if keyway_depth > 0:
                    messages.append(ValidationMessage(
                        severity=Severity.WARNING,
                        code="WHEEL_BORE_THIN_RIM_KEYWAY",
                        message=f"Wheel rim is thin ({effective_rim:.2f}mm after {keyway_depth:.1f}mm keyway)",
                        suggestion=f"Consider smaller bore or DD-cut for better strength"
                    ))
                else:
                    messages.append(ValidationMessage(
                        severity=Severity.WARNING,
                        code="WHEEL_BORE_THIN_RIM",
                        message=f"Wheel rim is thin ({rim_base:.2f}mm) with bore {wheel_bore_diameter:.1f}mm",
                        suggestion=f"Consider reducing bore for adequate strength"
                    ))

            # Additional warnings for small bores
            if wheel_bore_diameter < SMALL_BORE_THRESHOLD:
                messages.append(ValidationMessage(
                    severity=Severity.WARNING,
                    code="WHEEL_BORE_VERY_SMALL",
                    message=f"Wheel bore ({wheel_bore_diameter:.1f}mm) is below {SMALL_BORE_THRESHOLD}mm",
                    suggestion="Very small bores may be difficult to machine. Consider reaming or EDM."
                ))
                # Check for DD-cut with small bore
                if wheel_keyway and wheel_keyway.upper() == 'DDCUT':
                    messages.append(ValidationMessage(
                        severity=Severity.WARNING,
                        code="WHEEL_DDCUT_SMALL_BORE",
                        message=f"DD-cut on small bore ({wheel_bore_diameter:.1f}mm) may be impractical",
                        suggestion="Consider no anti-rotation feature or a custom keyway design"
                    ))

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

    # Get bore info from design.features OR from bore_settings
    # In calculator flow, features aren't populated yet, so use bore_settings
    worm_features = _get(design, 'features', 'worm')
    wheel_features = _get(design, 'features', 'wheel')

    # If no features in design but we have bore_settings, use those
    if bore_settings and worm_features is None and wheel_features is None:
        messages.extend(_validate_bore_from_settings(design, bore_settings))
        return messages

    # Otherwise validate from design.features (loaded JSON flow)
    if worm_features is not None:
        worm_bore_type = _normalize_bore_type(_get(design, 'features', 'worm', 'bore_type'))
        worm_bore = _get(design, 'features', 'worm', 'bore_diameter_mm')
        worm_root = _get(design, 'worm', 'root_diameter_mm', default=0)
        worm_anti_rot = _get(design, 'features', 'worm', 'anti_rotation')

        # Check bore_type is specified
        if worm_bore_type is None:
            messages.append(ValidationMessage(
                severity=Severity.ERROR,
                code="WORM_BORE_TYPE_MISSING",
                message="Worm features section exists but bore_type is not specified",
                suggestion="Set bore_type to 'none' for solid part or 'custom' with bore_diameter_mm"
            ))
        elif worm_bore_type == 'none':
            # Check if this is a fallback from auto-calculation
            # (gear too small for any bore)
            worm_pitch = _get(design, 'worm', 'pitch_diameter_mm', default=0)
            if worm_pitch > 0 and worm_root > 0:
                # Calculate if auto-bore would have been possible
                from ..core.bore_sizing import calculate_default_bore
                auto_bore, _ = calculate_default_bore(worm_pitch, worm_root)
                if auto_bore is None:
                    messages.append(ValidationMessage(
                        severity=Severity.INFO,
                        code="WORM_TOO_SMALL_FOR_BORE",
                        message=f"Worm is too small for a bore (root: {worm_root:.1f}mm, min bore: 0.5mm)",
                        suggestion="Consider a larger worm design if a bore is required"
                    ))
        elif worm_bore_type == 'custom':
            # Check bore_diameter_mm is present for custom
            if worm_bore is None:
                messages.append(ValidationMessage(
                    severity=Severity.ERROR,
                    code="WORM_BORE_DIAMETER_MISSING",
                    message="Worm bore_type is 'custom' but bore_diameter_mm is not specified",
                    suggestion="Specify bore_diameter_mm or set bore_type to 'none'"
                ))
            elif worm_bore > 0 and worm_root > 0:
                # Calculate rim thickness accounting for keyway
                rim_base = (worm_root - worm_bore) / 2
                keyway_depth = 0.0

                # Account for keyway depth if DIN6885 keyway is specified
                if worm_anti_rot and worm_anti_rot.upper() == 'DIN6885':
                    keyway_depth = _get_keyway_depth(worm_bore, is_shaft=True)

                effective_rim = rim_base - keyway_depth

                # Error if bore exceeds root
                if worm_bore >= worm_root:
                    messages.append(ValidationMessage(
                        severity=Severity.ERROR,
                        code="WORM_BORE_TOO_LARGE",
                        message=f"Worm bore ({worm_bore:.1f}mm) exceeds root diameter ({worm_root:.1f}mm)",
                        suggestion=f"Maximum bore is less than {worm_root:.1f}mm"
                    ))
                # Error if effective rim is negative or too thin
                elif effective_rim < MIN_RIM_WORM:
                    if keyway_depth > 0:
                        messages.append(ValidationMessage(
                            severity=Severity.ERROR,
                            code="WORM_BORE_KEYWAY_INTERFERENCE",
                            message=f"Worm bore {worm_bore:.1f}mm with keyway (depth {keyway_depth:.1f}mm) leaves only {effective_rim:.2f}mm rim",
                            suggestion=f"Reduce bore to allow at least {MIN_RIM_WORM}mm rim after keyway, or use DD-cut instead"
                        ))
                    else:
                        messages.append(ValidationMessage(
                            severity=Severity.ERROR,
                            code="WORM_BORE_TOO_LARGE",
                            message=f"Worm bore ({worm_bore:.1f}mm) leaves insufficient rim ({rim_base:.2f}mm)",
                            suggestion=f"Reduce bore to allow at least {MIN_RIM_WORM}mm rim"
                        ))
                # Warning if rim is thin
                elif effective_rim < WARN_RIM_WORM:
                    if keyway_depth > 0:
                        messages.append(ValidationMessage(
                            severity=Severity.WARNING,
                            code="WORM_BORE_THIN_RIM_KEYWAY",
                            message=f"Worm rim is thin ({effective_rim:.2f}mm after {keyway_depth:.1f}mm keyway)",
                            suggestion=f"Consider smaller bore or DD-cut for better strength"
                        ))
                    else:
                        messages.append(ValidationMessage(
                            severity=Severity.WARNING,
                            code="WORM_BORE_THIN_RIM",
                            message=f"Worm rim is thin ({rim_base:.2f}mm) with bore {worm_bore:.1f}mm",
                            suggestion=f"Consider reducing bore for adequate strength"
                        ))
                else:
                    # Info about bore configuration
                    if keyway_depth > 0:
                        messages.append(ValidationMessage(
                            severity=Severity.INFO,
                            code="WORM_BORE_OK",
                            message=f"Worm bore {worm_bore:.1f}mm with DIN6885 keyway: {effective_rim:.2f}mm effective rim",
                            suggestion=None
                        ))

    # Validate wheel bore (wheel_features already extracted above)
    if wheel_features is not None:
        wheel_bore_type = _normalize_bore_type(_get(design, 'features', 'wheel', 'bore_type'))
        wheel_bore = _get(design, 'features', 'wheel', 'bore_diameter_mm')
        wheel_root = _get(design, 'wheel', 'root_diameter_mm', default=0)
        wheel_anti_rot = _get(design, 'features', 'wheel', 'anti_rotation')

        # Check bore_type is specified
        if wheel_bore_type is None:
            messages.append(ValidationMessage(
                severity=Severity.ERROR,
                code="WHEEL_BORE_TYPE_MISSING",
                message="Wheel features section exists but bore_type is not specified",
                suggestion="Set bore_type to 'none' for solid part or 'custom' with bore_diameter_mm"
            ))
        elif wheel_bore_type == 'none':
            # Check if this is a fallback from auto-calculation
            wheel_pitch = _get(design, 'wheel', 'pitch_diameter_mm', default=0)
            if wheel_pitch > 0 and wheel_root > 0:
                from ..core.bore_sizing import calculate_default_bore
                auto_bore, _ = calculate_default_bore(wheel_pitch, wheel_root)
                if auto_bore is None:
                    messages.append(ValidationMessage(
                        severity=Severity.INFO,
                        code="WHEEL_TOO_SMALL_FOR_BORE",
                        message=f"Wheel is too small for a bore (root: {wheel_root:.1f}mm, min bore: 0.5mm)",
                        suggestion="Consider a larger wheel design if a bore is required"
                    ))
        elif wheel_bore_type == 'custom':
            # Check bore_diameter_mm is present for custom
            if wheel_bore is None:
                messages.append(ValidationMessage(
                    severity=Severity.ERROR,
                    code="WHEEL_BORE_DIAMETER_MISSING",
                    message="Wheel bore_type is 'custom' but bore_diameter_mm is not specified",
                    suggestion="Specify bore_diameter_mm or set bore_type to 'none'"
                ))
            elif wheel_bore > 0 and wheel_root > 0:
                # Calculate rim thickness accounting for keyway
                rim_base = (wheel_root - wheel_bore) / 2
                keyway_depth = 0.0

                # Account for keyway depth if DIN6885 keyway is specified
                if wheel_anti_rot and wheel_anti_rot.upper() == 'DIN6885':
                    keyway_depth = _get_keyway_depth(wheel_bore, is_shaft=False)

                effective_rim = rim_base - keyway_depth

                # Error if bore exceeds root
                if wheel_bore >= wheel_root:
                    messages.append(ValidationMessage(
                        severity=Severity.ERROR,
                        code="WHEEL_BORE_TOO_LARGE",
                        message=f"Wheel bore ({wheel_bore:.1f}mm) exceeds root diameter ({wheel_root:.1f}mm)",
                        suggestion=f"Maximum bore is less than {wheel_root:.1f}mm"
                    ))
                # Error if effective rim is negative or too thin
                elif effective_rim < MIN_RIM_WHEEL:
                    if keyway_depth > 0:
                        messages.append(ValidationMessage(
                            severity=Severity.ERROR,
                            code="WHEEL_BORE_KEYWAY_INTERFERENCE",
                            message=f"Wheel bore {wheel_bore:.1f}mm with keyway (depth {keyway_depth:.1f}mm) leaves only {effective_rim:.2f}mm rim",
                            suggestion=f"Reduce bore to allow at least {MIN_RIM_WHEEL}mm rim after keyway, or use DD-cut instead"
                        ))
                    else:
                        messages.append(ValidationMessage(
                            severity=Severity.ERROR,
                            code="WHEEL_BORE_TOO_LARGE",
                            message=f"Wheel bore ({wheel_bore:.1f}mm) leaves insufficient rim ({rim_base:.2f}mm)",
                            suggestion=f"Reduce bore to allow at least {MIN_RIM_WHEEL}mm rim"
                        ))
                # Warning if rim is thin
                elif effective_rim < WARN_RIM_WHEEL:
                    if keyway_depth > 0:
                        messages.append(ValidationMessage(
                            severity=Severity.WARNING,
                            code="WHEEL_BORE_THIN_RIM_KEYWAY",
                            message=f"Wheel rim is thin ({effective_rim:.2f}mm after {keyway_depth:.1f}mm keyway)",
                            suggestion=f"Consider smaller bore or DD-cut for better strength"
                        ))
                    else:
                        messages.append(ValidationMessage(
                            severity=Severity.WARNING,
                            code="WHEEL_BORE_THIN_RIM",
                            message=f"Wheel rim is thin ({rim_base:.2f}mm) with bore {wheel_bore:.1f}mm",
                            suggestion=f"Consider reducing bore for adequate strength"
                        ))
                else:
                    # Info about bore configuration
                    if keyway_depth > 0:
                        messages.append(ValidationMessage(
                            severity=Severity.INFO,
                            code="WHEEL_BORE_OK",
                            message=f"Wheel bore {wheel_bore:.1f}mm with DIN6885 keyway: {effective_rim:.2f}mm effective rim",
                            suggestion=None
                        ))

    return messages
