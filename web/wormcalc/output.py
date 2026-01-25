"""
Worm Gear Calculator - Output Formatters

JSON and Markdown output for designs.
Outputs JSON Schema v1.0 compatible with wormgear package.
"""

import json
from dataclasses import asdict
from typing import Optional

from .core import (
    WormGearDesign, WormParameters, WheelParameters, Hand,
    WormProfile, WormType, ManufacturingParams
)
from .validation import ValidationResult, ValidationMessage, Severity


def design_to_dict(design: WormGearDesign) -> dict:
    """
    Convert design to a plain dictionary suitable for JSON serialization.

    Outputs wormgear JSON Schema v1.0 format for use with geometry generator.
    """
    # Build worm section
    worm_dict = {
        "module_mm": round(design.worm.module, 4),
        "num_starts": design.worm.num_starts,
        "pitch_diameter_mm": round(design.worm.pitch_diameter, 3),
        "tip_diameter_mm": round(design.worm.tip_diameter, 3),
        "root_diameter_mm": round(design.worm.root_diameter, 3),
        "lead_mm": round(design.worm.lead, 3),
        "lead_angle_deg": round(design.worm.lead_angle, 2),
        "addendum_mm": round(design.worm.addendum, 3),
        "dedendum_mm": round(design.worm.dedendum, 3),
        "thread_thickness_mm": round(design.worm.thread_thickness, 3),
        "hand": design.hand.value.lower(),  # "right" or "left"
        "profile_shift": 0.0,  # Worm doesn't use profile shift
    }

    # Determine worm type from manufacturing params if available
    is_globoid = False
    if design.manufacturing and hasattr(design.manufacturing, 'worm_type'):
        is_globoid = design.manufacturing.worm_type.value == "globoid"
    elif design.worm.throat_reduction is not None:
        is_globoid = True

    worm_dict["type"] = "globoid" if is_globoid else "cylindrical"

    # Add globoid parameters if present (for information only)
    if design.worm.throat_reduction is not None:
        worm_dict["throat_reduction_mm"] = round(design.worm.throat_reduction, 3)

    if design.worm.throat_pitch_radius is not None:
        # Use throat_curvature_radius_mm to match WormParams dataclass
        worm_dict["throat_curvature_radius_mm"] = round(design.worm.throat_pitch_radius, 3)
        # Note: throat_tip_radius and throat_root_radius are not in WormParams schema v1.0

    # Build wheel section
    wheel_dict = {
        "module_mm": round(design.wheel.module, 4),
        "num_teeth": design.wheel.num_teeth,
        "pitch_diameter_mm": round(design.wheel.pitch_diameter, 3),
        "tip_diameter_mm": round(design.wheel.tip_diameter, 3),
        "root_diameter_mm": round(design.wheel.root_diameter, 3),
        "throat_diameter_mm": round(design.wheel.throat_diameter, 3),
        "helix_angle_deg": round(design.wheel.helix_angle, 2),
        "addendum_mm": round(design.wheel.addendum, 3),
        "dedendum_mm": round(design.wheel.dedendum, 3),
        "profile_shift": round(design.wheel.profile_shift, 4),
    }

    # Build assembly section (includes efficiency and self-locking)
    assembly_dict = {
        "centre_distance_mm": round(design.centre_distance, 3),
        "pressure_angle_deg": design.pressure_angle,
        "backlash_mm": round(design.backlash, 3),
        "hand": design.hand.value.lower(),  # "right" or "left"
        "ratio": design.ratio,
        "efficiency_percent": round(design.efficiency_estimate * 100, 2),
        "self_locking": design.self_locking,
    }

    # Build manufacturing section (wormgear schema v1.0 format)
    manufacturing_dict = {
        "profile": design.profile.value,  # "ZA", "ZK", or "ZI"
        "virtual_hobbing": False,  # Default, will be updated below
        "hobbing_steps": 18,  # Default value
        "throated_wheel": False,  # Default to helical
        "sections_per_turn": 36,  # Default smoothness
    }

    # Update from design manufacturing params if present
    if design.manufacturing is not None:
        manufacturing_dict["throated_wheel"] = design.manufacturing.wheel_throated
        manufacturing_dict["profile"] = design.manufacturing.profile.value
        # Add virtual hobbing settings if available
        if hasattr(design.manufacturing, 'virtual_hobbing'):
            manufacturing_dict["virtual_hobbing"] = design.manufacturing.virtual_hobbing
        if hasattr(design.manufacturing, 'hobbing_steps'):
            manufacturing_dict["hobbing_steps"] = design.manufacturing.hobbing_steps

    # Build result with schema version
    result = {
        "schema_version": "1.0",
        "worm": worm_dict,
        "wheel": wheel_dict,
        "assembly": assembly_dict,
        "manufacturing": manufacturing_dict,
    }

    return result


def validation_to_dict(validation: ValidationResult) -> dict:
    """Convert validation result to dictionary"""
    return {
        "valid": validation.valid,
        "messages": [
            {
                "severity": msg.severity.value,
                "code": msg.code,
                "message": msg.message,
                "suggestion": msg.suggestion
            }
            for msg in validation.messages
        ]
    }


def to_json(
    design: WormGearDesign,
    validation: Optional[ValidationResult] = None,
    indent: int = 2
) -> str:
    """
    Export design to JSON string (wormgear schema v1.0).

    Args:
        design: The worm gear design
        validation: Optional validation result to include
        indent: JSON indentation (default 2)

    Returns:
        JSON string compatible with wormgear package
    """
    data = design_to_dict(design)

    if validation:
        data["validation"] = validation_to_dict(validation)

    return json.dumps(data, indent=indent)


def to_markdown(
    design: WormGearDesign,
    validation: Optional[ValidationResult] = None,
    title: str = "Worm Gear Design"
) -> str:
    """
    Export design to Markdown format.

    Args:
        design: The worm gear design
        validation: Optional validation result to include
        title: Document title

    Returns:
        Markdown string
    """
    # Get worm type for display
    worm_type_str = "Cylindrical"
    wheel_type_str = "Helical"
    if design.manufacturing:
        worm_type_str = design.manufacturing.worm_type.value.title()
        wheel_type_str = "Throated (Hobbed)" if design.manufacturing.wheel_throated else "Helical"

    lines = [
        f"# {title}",
        "",
        "## Summary",
        "",
        f"| Parameter | Value |",
        f"|-----------|-------|",
        f"| Ratio | {design.ratio}:1 |",
        f"| Module | {design.worm.module:.3f} mm |",
        f"| Centre Distance | {design.centre_distance:.2f} mm |",
        f"| Pressure Angle | {design.pressure_angle}° |",
        f"| Hand | {design.hand.value.title()} |",
        f"| Profile | {design.profile.value} (DIN 3975) |",
        f"| Worm Type | {worm_type_str} |",
        f"| Wheel Type | {wheel_type_str} |",
        f"| Efficiency (est.) | {design.efficiency_estimate*100:.0f}% |",
        f"| Self-Locking | {'Yes' if design.self_locking else 'No'} |",
    ]

    # Add manufacturing dimensions to summary if available
    if design.manufacturing:
        lines.extend([
            f"| **Worm Length** | **{design.manufacturing.worm_length:.2f} mm** |",
            f"| **Wheel Width** | **{design.manufacturing.wheel_width:.2f} mm** |",
        ])

    lines.extend([
        "",
        "## Worm",
        "",
        f"| Parameter | Value |",
        f"|-----------|-------|",
        f"| Number of Starts | {design.worm.num_starts} |",
        f"| Pitch Diameter | {design.worm.pitch_diameter:.2f} mm |",
        f"| Tip Diameter (OD) | {design.worm.tip_diameter:.2f} mm |",
        f"| Root Diameter | {design.worm.root_diameter:.2f} mm |",
        f"| Lead | {design.worm.lead:.3f} mm |",
        f"| Axial Pitch | {design.worm.axial_pitch:.3f} mm |",
        f"| Lead Angle | {design.worm.lead_angle:.2f}° |",
        f"| Addendum | {design.worm.addendum:.3f} mm |",
        f"| Dedendum | {design.worm.dedendum:.3f} mm |",
        f"| Thread Thickness | {design.worm.thread_thickness:.3f} mm |",
    ])

    # Add globoid throat radii if present
    if design.worm.throat_pitch_radius is not None:
        lines.extend([
            f"| Throat Pitch Radius | {design.worm.throat_pitch_radius:.3f} mm |",
            f"| Throat Tip Radius | {design.worm.throat_tip_radius:.3f} mm |",
            f"| Throat Root Radius | {design.worm.throat_root_radius:.3f} mm |",
        ])

    lines.extend([
        "",
        "## Wheel",
        "",
        f"| Parameter | Value |",
        f"|-----------|-------|",
        f"| Number of Teeth | {design.wheel.num_teeth} |",
        f"| Pitch Diameter | {design.wheel.pitch_diameter:.2f} mm |",
        f"| Tip Diameter (OD) | {design.wheel.tip_diameter:.2f} mm |",
        f"| Root Diameter | {design.wheel.root_diameter:.2f} mm |",
        f"| Throat Diameter | {design.wheel.throat_diameter:.2f} mm |",
        f"| Helix Angle | {design.wheel.helix_angle:.2f}° |",
        f"| Addendum | {design.wheel.addendum:.3f} mm |",
        f"| Dedendum | {design.wheel.dedendum:.3f} mm |",
        f"| Profile Shift | {design.wheel.profile_shift:.3f} |",
        "",
    ])

    # Add manufacturing section if present
    if design.manufacturing:
        lines.extend([
            "## Manufacturing",
            "",
            f"| Parameter | Value |",
            f"|-----------|-------|",
            f"| Worm Type | {design.manufacturing.worm_type.value.title()} |",
            f"| Profile | {design.manufacturing.profile.value} |",
            f"| Recommended Worm Length | {design.manufacturing.worm_length:.2f} mm |",
            f"| Recommended Wheel Width | {design.manufacturing.wheel_width:.2f} mm |",
            f"| Wheel Throated | {'Yes' if design.manufacturing.wheel_throated else 'No'} |",
            "",
        ])

        # Add note about recommendations
        lines.extend([
            "*Note: Worm length and wheel width are design guidelines based on contact ratio",
            "and engagement requirements. Adjust as needed for specific applications.*",
            "",
        ])

    # Add validation if provided
    if validation:
        lines.extend([
            "## Validation",
            "",
        ])

        if validation.valid:
            lines.append("✅ Design is valid")
        else:
            lines.append("❌ Design has errors")

        lines.append("")

        if validation.errors:
            lines.append("### Errors")
            lines.append("")
            for msg in validation.errors:
                lines.append(f"- **{msg.code}**: {msg.message}")
                if msg.suggestion:
                    lines.append(f"  - *Suggestion*: {msg.suggestion}")
            lines.append("")

        if validation.warnings:
            lines.append("### Warnings")
            lines.append("")
            for msg in validation.warnings:
                lines.append(f"- **{msg.code}**: {msg.message}")
                if msg.suggestion:
                    lines.append(f"  - *Suggestion*: {msg.suggestion}")
            lines.append("")

        if validation.infos:
            lines.append("### Information")
            lines.append("")
            for msg in validation.infos:
                lines.append(f"- {msg.message}")
            lines.append("")

    # Add notes
    lines.extend([
        "## Notes",
        "",
        "- All dimensions in millimeters unless otherwise noted",
        "- Efficiency estimate assumes steel worm on bronze wheel with lubrication",
        "- Self-locking determination is approximate - verify with actual materials",
        "- Throat diameter is for enveloping (throated) wheel design",
        "",
        "---",
        "*Generated by wormgear calculator*",
    ])

    return "\n".join(lines)


def to_summary(design: WormGearDesign) -> str:
    """
    Generate a brief text summary for terminal output.
    """
    # Get worm type for display
    worm_type_str = "cylindrical"
    if design.manufacturing:
        worm_type_str = design.manufacturing.worm_type.value

    lines = [
        "═══ Worm Gear Design ═══",
        f"Ratio: {design.ratio}:1",
        f"Module: {design.worm.module:.3f} mm",
        f"Profile: {design.profile.value} | Worm: {worm_type_str}",
        "",
        "Worm:",
        f"  Tip diameter (OD): {design.worm.tip_diameter:.2f} mm",
        f"  Pitch diameter:    {design.worm.pitch_diameter:.2f} mm",
        f"  Root diameter:     {design.worm.root_diameter:.2f} mm",
        f"  Lead angle:        {design.worm.lead_angle:.1f}°",
        f"  Starts:            {design.worm.num_starts}",
    ]

    # Add globoid throat info if present
    if design.worm.throat_pitch_radius is not None:
        lines.extend([
            f"  Throat pitch rad:  {design.worm.throat_pitch_radius:.2f} mm",
        ])

    lines.extend([
        "",
        "Wheel:",
        f"  Tip diameter (OD): {design.wheel.tip_diameter:.2f} mm",
        f"  Pitch diameter:    {design.wheel.pitch_diameter:.2f} mm",
        f"  Root diameter:     {design.wheel.root_diameter:.2f} mm",
        f"  Teeth:             {design.wheel.num_teeth}",
        f"  Helix angle:       {design.wheel.helix_angle:.1f}°",
        "",
        f"Centre distance: {design.centre_distance:.2f} mm",
        f"Efficiency (est): {design.efficiency_estimate*100:.0f}%",
        f"Self-locking: {'Yes' if design.self_locking else 'No'}",
    ])

    # Add manufacturing recommendations if present
    if design.manufacturing:
        lines.extend([
            "",
            "Recommended Dimensions:",
            f"  Worm length:  {design.manufacturing.worm_length:.2f} mm",
            f"  Wheel width:  {design.manufacturing.wheel_width:.2f} mm",
        ])

    return "\n".join(lines)


def validation_summary(validation: ValidationResult) -> str:
    """
    Generate a brief validation summary for terminal output.
    """
    lines = []

    if validation.valid:
        lines.append("✓ Design valid")
    else:
        lines.append("✗ Design has errors")

    for msg in validation.errors:
        lines.append(f"  ERROR: {msg.message}")

    for msg in validation.warnings:
        lines.append(f"  WARN:  {msg.message}")

    for msg in validation.infos:
        lines.append(f"  INFO:  {msg.message}")

    return "\n".join(lines)
