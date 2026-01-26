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
from typing import List, Optional, Union, Any, Dict
from enum import Enum
from math import sin, radians

from .core import is_standard_module, nearest_standard_module


# Type alias for design input (dict or dataclass)
DesignInput = Union[Dict[str, Any], Any]  # Any covers WormGearDesign


def _get(obj: Any, *keys: str, default: Any = None) -> Any:
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


def validate_design(design: DesignInput) -> ValidationResult:
    """
    Validate a worm gear design against engineering rules.

    Accepts both dict (from calculator) and WormGearDesign dataclass
    (from load_design_json).

    Args:
        design: Design dict or WormGearDesign dataclass

    Returns:
        ValidationResult with all findings
    """
    messages: List[ValidationMessage] = []

    # Run all validation checks
    messages.extend(_validate_lead_angle(design))
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

    # Design is valid if no errors
    has_errors = any(m.severity == Severity.ERROR for m in messages)

    return ValidationResult(
        valid=not has_errors,
        messages=messages
    )


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
        module = _get(design, 'worm', 'module_mm', default=1.0)

        # Check throat parameters are present
        if throat_curvature is None:
            messages.append(ValidationMessage(
                severity=Severity.WARNING,
                code="GLOBOID_MISSING_THROAT",
                message="Globoid worm without throat curvature radius specified",
                suggestion="Ensure throat radii are calculated for proper geometry"
            ))
        else:
            # Validate throat reduction value if present
            if throat_reduction is not None and throat_reduction > 0:
                if throat_reduction < 0.02:
                    messages.append(ValidationMessage(
                        severity=Severity.WARNING,
                        code="THROAT_REDUCTION_VERY_SMALL",
                        message=f"Throat reduction {throat_reduction:.3f}mm is very small - minimal hourglass effect",
                        suggestion="Typical values: 0.05-0.1mm for small gears, 0.1-0.2mm for medium"
                    ))
                elif throat_reduction > module * 0.5:
                    messages.append(ValidationMessage(
                        severity=Severity.ERROR,
                        code="THROAT_REDUCTION_TOO_LARGE",
                        message=f"Throat reduction {throat_reduction:.3f}mm is too large (>{module * 0.5:.3f}mm = 50% of module)",
                        suggestion="Reduce throat reduction to less than 50% of module"
                    ))
                elif throat_reduction > module * 0.3:
                    messages.append(ValidationMessage(
                        severity=Severity.WARNING,
                        code="THROAT_REDUCTION_LARGE",
                        message=f"Throat reduction {throat_reduction:.3f}mm is large (>{module * 0.3:.3f}mm = 30% of module)",
                        suggestion="Consider reducing for better manufacturability"
                    ))

            # Info about globoid
            messages.append(ValidationMessage(
                severity=Severity.INFO,
                code="GLOBOID_WORM",
                message="Globoid worm provides better contact with wheel",
                suggestion=None
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
