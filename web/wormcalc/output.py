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
from .js_bridge import validate_manufacturing_settings, validate_bore_settings
from .json_schema import validate_design_json
from .validation import ValidationResult, ValidationMessage, Severity


def design_to_dict(design: WormGearDesign, bore_settings: dict = None, manufacturing_settings: dict = None) -> dict:
    """
    Convert design to a plain dictionary suitable for JSON serialization.

    Outputs wormgear JSON Schema v1.0 format for use with geometry generator.

    Args:
        design: The worm gear design
        bore_settings: Optional dict with bore configuration from UI
        manufacturing_settings: Optional dict with manufacturing/dimension settings from UI
    """
    # Validate inputs at JS→Python boundary (handles JavaScript null/undefined/JsNull)
    validated_mfg = validate_manufacturing_settings(manufacturing_settings) if manufacturing_settings else {}
    validated_bore = validate_bore_settings(bore_settings) if bore_settings else {}

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

    # Add custom worm length if specified
    worm_length = validated_mfg.get('worm_length')
    if worm_length is not None:
        worm_dict["length_mm"] = worm_length

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

    # Add custom wheel width if specified
    wheel_width = validated_mfg.get('wheel_width')
    if wheel_width is not None:
        wheel_dict["width_mm"] = wheel_width

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
        "worm_type": "cylindrical",  # Default, will be updated below
        "virtual_hobbing": False,  # Default, will be updated below
        "hobbing_steps": 18,  # Default value
        "throated_wheel": False,  # Default to helical
        "sections_per_turn": 36,  # Default smoothness
    }

    # Update from design manufacturing params if present
    if design.manufacturing is not None:
        manufacturing_dict["throated_wheel"] = design.manufacturing.wheel_throated
        manufacturing_dict["profile"] = design.manufacturing.profile.value
        manufacturing_dict["worm_type"] = design.manufacturing.worm_type.value  # Add worm type
        # Add recommended dimensions (always present, needed for UI defaults)
        manufacturing_dict["worm_length"] = design.manufacturing.worm_length
        manufacturing_dict["wheel_width"] = design.manufacturing.wheel_width
        # Add virtual hobbing settings if available
        if hasattr(design.manufacturing, 'virtual_hobbing'):
            manufacturing_dict["virtual_hobbing"] = design.manufacturing.virtual_hobbing
        if hasattr(design.manufacturing, 'hobbing_steps'):
            manufacturing_dict["hobbing_steps"] = design.manufacturing.hobbing_steps

    # Override with UI manufacturing settings if provided (takes precedence)
    if validated_mfg:
        if 'worm_type' in validated_mfg and validated_mfg['worm_type'] is not None:
            manufacturing_dict["worm_type"] = validated_mfg['worm_type']
        if 'virtual_hobbing' in validated_mfg and validated_mfg['virtual_hobbing'] is not None:
            manufacturing_dict["virtual_hobbing"] = validated_mfg['virtual_hobbing']
        if 'hobbing_steps' in validated_mfg and validated_mfg['hobbing_steps'] is not None:
            manufacturing_dict["hobbing_steps"] = validated_mfg['hobbing_steps']

    # Build result with schema version
    result = {
        "schema_version": "1.0",
        "worm": worm_dict,
        "wheel": wheel_dict,
        "assembly": assembly_dict,
        "manufacturing": manufacturing_dict,
    }

    # Add features section if bore settings provided (already validated at boundary)
    if validated_bore:
        features = {}

        # Worm features
        worm_bore_type = validated_bore.get('worm_bore_type')
        if worm_bore_type:
            worm_features = {}
            if worm_bore_type == 'custom':
                bore_diam = validated_bore.get('worm_bore_diameter')
                if bore_diam is not None:
                    worm_features['bore_diameter_mm'] = bore_diam
            elif worm_bore_type == 'auto':
                worm_features['auto_bore'] = True

            # Add anti-rotation if specified
            worm_keyway = validated_bore.get('worm_keyway')
            if worm_keyway:
                worm_features['anti_rotation'] = worm_keyway

            if worm_features:
                features['worm'] = worm_features

        # Wheel features
        wheel_bore_type = validated_bore.get('wheel_bore_type')
        if wheel_bore_type:
            wheel_features = {}
            if wheel_bore_type == 'custom':
                bore_diam = validated_bore.get('wheel_bore_diameter')
                if bore_diam is not None:
                    wheel_features['bore_diameter_mm'] = bore_diam
            elif wheel_bore_type == 'auto':
                wheel_features['auto_bore'] = True

            # Add anti-rotation if specified
            wheel_keyway = validated_bore.get('wheel_keyway')
            if wheel_keyway:
                wheel_features['anti_rotation'] = wheel_keyway

            if wheel_features:
                features['wheel'] = wheel_features

        if features:
            result['features'] = features

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
    indent: int = 2,
    bore_settings: Optional[dict] = None,
    manufacturing_settings: Optional[dict] = None
) -> str:
    """
    Export design to JSON string (wormgear schema v1.0).

    Args:
        design: The worm gear design
        validation: Optional validation result to include (deprecated - validation
                   should be in markdown output only, not in generator input JSON)
        indent: JSON indentation (default 2)
        bore_settings: Optional bore configuration from UI
        manufacturing_settings: Optional manufacturing/dimension settings from UI

    Returns:
        JSON string compatible with wormgear package (pure input parameters)
    """
    data = design_to_dict(design, bore_settings=bore_settings, manufacturing_settings=manufacturing_settings)

    # Validate JSON structure against schema v1.0
    is_valid, errors = validate_design_json(data)
    if not is_valid:
        # Log validation errors (don't fail - let caller decide)
        print(f"Warning: Generated JSON has {len(errors)} validation error(s):")
        for error in errors:
            print(f"  - {error}")

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
        lines.append(f"| Throat Pitch Radius | {design.worm.throat_pitch_radius:.3f} mm |")

    if design.worm.throat_tip_radius is not None:
        lines.append(f"| Throat Tip Radius | {design.worm.throat_tip_radius:.3f} mm |")

    if design.worm.throat_root_radius is not None:
        lines.append(f"| Throat Root Radius | {design.worm.throat_root_radius:.3f} mm |")

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
