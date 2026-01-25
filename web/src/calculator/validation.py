"""
Worm Gear Calculator - Validation Rules

Engineering validation based on:
- DIN 3975 / DIN 3996 standards
- Common engineering practice
- Manufacturing constraints

Ported from wormgearcalc with field naming adapted for wormgear.
"""

from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum
from math import sin, radians

from .core import is_standard_module, nearest_standard_module
from ..io import WormGearDesign


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


def validate_design(design: WormGearDesign) -> ValidationResult:
    """
    Validate a worm gear design against engineering rules.

    Returns ValidationResult with all findings.
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

    # Design is valid if no errors
    has_errors = any(m.severity == Severity.ERROR for m in messages)

    return ValidationResult(
        valid=not has_errors,
        messages=messages
    )


def _validate_lead_angle(design: WormGearDesign) -> List[ValidationMessage]:
    """Check lead angle is within practical range"""
    messages = []
    lead_angle = design.worm.lead_angle_deg

    if lead_angle < 1.0:
        messages.append(ValidationMessage(
            severity=Severity.ERROR,
            code="LEAD_ANGLE_TOO_LOW",
            message=f"Lead angle {lead_angle:.1f}° is too low for practical manufacture",
            suggestion="Increase worm pitch diameter or reduce module"
        ))
    elif lead_angle < 3.0:
        efficiency = design.assembly.efficiency_percent if design.assembly.efficiency_percent else 0
        messages.append(ValidationMessage(
            severity=Severity.WARNING,
            code="LEAD_ANGLE_VERY_LOW",
            message=f"Lead angle {lead_angle:.1f}° is very low. Efficiency ~{efficiency:.0f}%",
            suggestion="Consider increasing worm diameter for better efficiency"
        ))
    elif lead_angle < 5.0:
        efficiency = design.assembly.efficiency_percent if design.assembly.efficiency_percent else 0
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


def _validate_module(design: WormGearDesign) -> List[ValidationMessage]:
    """Check module is standard or flag non-standard"""
    messages = []
    module = design.worm.module_mm

    if not is_standard_module(module):
        nearest = nearest_standard_module(module)
        deviation = abs(module - nearest) / nearest * 100

        if deviation > 10:
            messages.append(ValidationMessage(
                severity=Severity.WARNING,
                code="MODULE_NON_STANDARD",
                message=f"Module {module:.3f}mm is non-standard (ISO 54)",
                suggestion=f"Nearest standard module: {nearest}mm. Consider adjusting envelope constraints."
            ))
        else:
            messages.append(ValidationMessage(
                severity=Severity.INFO,
                code="MODULE_NEAR_STANDARD",
                message=f"Module {module:.3f}mm is close to standard {nearest}mm",
                suggestion=f"Could round to {nearest}mm with minor OD changes"
            ))

    return messages


def _validate_teeth_count(design: WormGearDesign) -> List[ValidationMessage]:
    """Check wheel teeth count is adequate"""
    messages = []
    num_teeth = design.wheel.num_teeth
    pressure_angle = design.assembly.pressure_angle_deg

    # Check for undercut risk
    z_min = calculate_minimum_teeth(pressure_angle)

    if num_teeth < z_min:
        recommended_shift = calculate_recommended_profile_shift(num_teeth, pressure_angle)
        current_shift = design.wheel.profile_shift

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


def _validate_worm_proportions(design: WormGearDesign) -> List[ValidationMessage]:
    """Check worm proportions are reasonable"""
    messages = []

    pitch_dia = design.worm.pitch_diameter_mm
    module = design.worm.module_mm

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


def _validate_pressure_angle(design: WormGearDesign) -> List[ValidationMessage]:
    """Check pressure angle is standard"""
    messages = []
    alpha = design.assembly.pressure_angle_deg

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


def _validate_efficiency(design: WormGearDesign) -> List[ValidationMessage]:
    """Check efficiency and self-locking behavior"""
    messages = []

    if design.assembly.efficiency_percent is not None:
        efficiency = design.assembly.efficiency_percent

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

    if design.assembly.self_locking:
        messages.append(ValidationMessage(
            severity=Severity.INFO,
            code="SELF_LOCKING",
            message="Drive is self-locking (backdrive prevented)",
            suggestion="Ensure adequate lubrication to minimize heat from friction"
        ))

    return messages


def _validate_clearance(design: WormGearDesign) -> List[ValidationMessage]:
    """Basic geometric clearance check"""
    messages = []

    # Check that worm and wheel don't interfere
    worm_tip_radius = design.worm.tip_diameter_mm / 2
    wheel_root_radius = design.wheel.root_diameter_mm / 2
    centre_distance = design.assembly.centre_distance_mm

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
