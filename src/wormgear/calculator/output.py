"""Output formatters for worm gear designs.

Converts typed WormGearDesign dataclasses to JSON and Markdown output.
All functions expect WormGearDesign - no dict handling for clean code.
"""

import json
from dataclasses import asdict
from enum import Enum
from typing import Optional, TYPE_CHECKING, Any

from ..io import WormGearDesign

if TYPE_CHECKING:
    from .validation import ValidationResult


def _serialize_enums(obj: Any) -> Any:
    """Recursively convert enum values to strings for JSON serialization."""
    if isinstance(obj, Enum):
        return obj.value
    elif isinstance(obj, dict):
        return {key: _serialize_enums(value) for key, value in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_serialize_enums(item) for item in obj]
    else:
        return obj


def to_json(
    design: WormGearDesign,
    validation: Optional["ValidationResult"] = None,
    indent: int = 2,
    bore_settings: Optional[dict] = None,
    manufacturing_settings: Optional[dict] = None
) -> str:
    """Convert WormGearDesign to JSON string.

    Args:
        design: WormGearDesign dataclass from design_from_*() functions
        validation: Optional validation results to include in output
        indent: JSON indentation level (default: 2)
        bore_settings: Optional bore configuration from UI
        manufacturing_settings: Optional manufacturing overrides from UI

    Returns:
        JSON string with schema version, design parameters, and optional extras
    """
    # Convert dataclass to dict and serialize enums
    design_dict = _serialize_enums(asdict(design))

    # Add schema version for compatibility
    if 'schema_version' not in design_dict:
        design_dict['schema_version'] = '1.0'

    # Transform bore settings into features section (format expected by generator)
    if bore_settings:
        features = {}

        # Worm bore/keyway features
        if bore_settings.get('worm_bore_type') == 'auto':
            features['worm'] = {'auto_bore': True}
        elif bore_settings.get('worm_bore_type') == 'custom' and bore_settings.get('worm_bore_diameter'):
            features['worm'] = {'bore_diameter_mm': bore_settings['worm_bore_diameter']}

        # Add worm anti-rotation if bore exists
        if 'worm' in features:
            worm_keyway = bore_settings.get('worm_keyway', 'none')
            if worm_keyway and worm_keyway != 'none':
                features['worm']['anti_rotation'] = worm_keyway

        # Wheel bore/keyway features
        if bore_settings.get('wheel_bore_type') == 'auto':
            features['wheel'] = {'auto_bore': True}
        elif bore_settings.get('wheel_bore_type') == 'custom' and bore_settings.get('wheel_bore_diameter'):
            features['wheel'] = {'bore_diameter_mm': bore_settings['wheel_bore_diameter']}

        # Add wheel anti-rotation if bore exists
        if 'wheel' in features:
            wheel_keyway = bore_settings.get('wheel_keyway', 'none')
            if wheel_keyway and wheel_keyway != 'none':
                features['wheel']['anti_rotation'] = wheel_keyway

        if features:
            design_dict['features'] = features

    # Merge in manufacturing settings if provided
    if manufacturing_settings:
        design_dict.setdefault('manufacturing', {}).update(manufacturing_settings)

    # Add validation results if provided
    if validation:
        design_dict['validation'] = {
            'valid': validation.valid,
            'errors': [
                {
                    'severity': msg.severity.value,
                    'code': msg.code,
                    'message': msg.message,
                    'suggestion': msg.suggestion
                }
                for msg in validation.errors
            ],
            'warnings': [
                {
                    'severity': msg.severity.value,
                    'code': msg.code,
                    'message': msg.message,
                    'suggestion': msg.suggestion
                }
                for msg in validation.warnings
            ],
            'infos': [
                {
                    'severity': msg.severity.value,
                    'code': msg.code,
                    'message': msg.message,
                    'suggestion': msg.suggestion
                }
                for msg in validation.infos
            ]
        }

    return json.dumps(design_dict, indent=indent)


def to_markdown(
    design: WormGearDesign,
    validation: Optional["ValidationResult"] = None,
    bore_settings: Optional[dict] = None,
    manufacturing_settings: Optional[dict] = None
) -> str:
    """Convert WormGearDesign to comprehensive markdown specification.

    Args:
        design: WormGearDesign dataclass from design_from_*() functions
        validation: Optional validation results to include
        bore_settings: Optional bore configuration from UI
        manufacturing_settings: Optional manufacturing config (unused)

    Returns:
        Detailed markdown specification string
    """
    # Convert to dict for easy field access
    design_dict = _serialize_enums(asdict(design))

    worm = design_dict["worm"]
    wheel = design_dict["wheel"]
    asm = design_dict["assembly"]
    mfg = design_dict.get("manufacturing") or {}

    # Get worm type
    worm_type = worm.get("type", "cylindrical")
    if hasattr(worm_type, 'value'):
        worm_type = worm_type.value

    md = "# Worm Gear Design Specification\n\n"

    # Overview section
    md += "## Overview\n\n"
    md += f"| Parameter | Value |\n"
    md += f"|-----------|-------|\n"
    md += f"| Gear Ratio | {asm['ratio']}:1 |\n"
    md += f"| Module | {worm['module_mm']:.3f} mm |\n"
    md += f"| Centre Distance | {asm['centre_distance_mm']:.3f} mm |\n"
    md += f"| Hand | {asm.get('hand', 'right')} |\n"
    md += f"| Profile | {mfg.get('profile', 'ZA')} |\n"
    md += f"| Worm Type | {worm_type} |\n"
    md += f"| Pressure Angle | {asm.get('pressure_angle_deg', 20.0):.1f}° |\n\n"

    # Worm section
    md += "## Worm Gear (Driving)\n\n"
    md += f"| Dimension | Value |\n"
    md += f"|-----------|-------|\n"
    md += f"| Number of Starts | {worm['num_starts']} |\n"
    md += f"| Tip Diameter (OD) | {worm['tip_diameter_mm']:.3f} mm |\n"
    md += f"| Pitch Diameter | {worm['pitch_diameter_mm']:.3f} mm |\n"
    md += f"| Root Diameter | {worm['root_diameter_mm']:.3f} mm |\n"
    md += f"| Lead | {worm['lead_mm']:.3f} mm |\n"
    md += f"| Lead Angle | {worm['lead_angle_deg']:.2f}° |\n"
    md += f"| Addendum | {worm['addendum_mm']:.3f} mm |\n"
    md += f"| Dedendum | {worm['dedendum_mm']:.3f} mm |\n"
    md += f"| Thread Thickness | {worm.get('thread_thickness_mm', worm['module_mm'] * 1.571):.3f} mm |\n"
    if worm.get('profile_shift'):
        md += f"| Profile Shift | {worm['profile_shift']:.3f} |\n"
    if worm_type == "globoid" and worm.get('throat_pitch_radius_mm'):
        md += f"| Throat Pitch Radius | {worm['throat_pitch_radius_mm']:.3f} mm |\n"
    md += "\n"

    # Recommended worm length
    if mfg.get('worm_length_mm'):
        md += f"**Recommended Length:** {mfg['worm_length_mm']:.1f} mm\n\n"

    # Wheel section
    md += "## Worm Wheel (Driven)\n\n"
    md += f"| Dimension | Value |\n"
    md += f"|-----------|-------|\n"
    md += f"| Number of Teeth | {wheel['num_teeth']} |\n"
    md += f"| Tip Diameter (OD) | {wheel['tip_diameter_mm']:.3f} mm |\n"
    md += f"| Pitch Diameter | {wheel['pitch_diameter_mm']:.3f} mm |\n"
    md += f"| Root Diameter | {wheel['root_diameter_mm']:.3f} mm |\n"
    if wheel.get('throat_diameter_mm'):
        md += f"| Throat Diameter | {wheel['throat_diameter_mm']:.3f} mm |\n"
    md += f"| Helix Angle | {wheel['helix_angle_deg']:.2f}° |\n"
    md += f"| Addendum | {wheel['addendum_mm']:.3f} mm |\n"
    md += f"| Dedendum | {wheel['dedendum_mm']:.3f} mm |\n"
    if wheel.get('profile_shift'):
        md += f"| Profile Shift | {wheel['profile_shift']:.3f} |\n"
    md += "\n"

    # Recommended wheel width
    if mfg.get('wheel_width_mm'):
        md += f"**Recommended Face Width:** {mfg['wheel_width_mm']:.1f} mm\n\n"

    # Assembly/Performance section
    md += "## Assembly & Performance\n\n"
    md += f"| Parameter | Value |\n"
    md += f"|-----------|-------|\n"
    md += f"| Centre Distance | {asm['centre_distance_mm']:.3f} mm |\n"
    md += f"| Backlash | {asm.get('backlash_mm', 0.05):.3f} mm |\n"
    if asm.get('efficiency_percent'):
        md += f"| Estimated Efficiency | {asm['efficiency_percent']:.1f}% |\n"
    md += f"| Self-Locking | {'Yes' if asm.get('self_locking', False) else 'No'} |\n"
    md += "\n"

    # Bore and features section
    if bore_settings:
        md += "## Bore & Anti-Rotation Features\n\n"

        # Worm bore
        worm_bore_type = bore_settings.get('worm_bore_type', 'none')
        if worm_bore_type != 'none':
            md += "### Worm\n\n"
            if worm_bore_type == 'auto':
                md += "- Bore: Auto-calculated\n"
            elif worm_bore_type == 'custom':
                md += f"- Bore Diameter: {bore_settings.get('worm_bore_diameter', 0):.1f} mm\n"
            worm_keyway = bore_settings.get('worm_keyway', 'none')
            if worm_keyway and worm_keyway != 'none':
                md += f"- Anti-Rotation: {worm_keyway}\n"
            md += "\n"

        # Wheel bore
        wheel_bore_type = bore_settings.get('wheel_bore_type', 'none')
        if wheel_bore_type != 'none':
            md += "### Wheel\n\n"
            if wheel_bore_type == 'auto':
                md += "- Bore: Auto-calculated\n"
            elif wheel_bore_type == 'custom':
                md += f"- Bore Diameter: {bore_settings.get('wheel_bore_diameter', 0):.1f} mm\n"
            wheel_keyway = bore_settings.get('wheel_keyway', 'none')
            if wheel_keyway and wheel_keyway != 'none':
                md += f"- Anti-Rotation: {wheel_keyway}\n"
            md += "\n"

    # Manufacturing section
    md += "## Manufacturing Notes\n\n"
    md += f"- **Profile Type:** {mfg.get('profile', 'ZA')}"
    if mfg.get('profile', 'ZA') == 'ZA':
        md += " (straight flanks - standard for CNC machining)\n"
    elif mfg.get('profile', 'ZA') == 'ZK':
        md += " (convex flanks - recommended for 3D printing)\n"
    else:
        md += "\n"

    if mfg.get('virtual_hobbing'):
        md += f"- **Wheel Generation:** Virtual hobbing ({mfg.get('hobbing_steps', 72)} steps)\n"
    else:
        md += "- **Wheel Generation:** Helical approximation\n"

    md += f"- **Worm Type:** {worm_type.title()}\n"

    # Validation section
    if validation:
        md += "\n## Validation\n\n"

        if validation.valid:
            md += "**Status:** ✅ Design is valid\n\n"
        else:
            md += "**Status:** ❌ Design has errors\n\n"

        if validation.errors:
            md += "### Errors\n\n"
            for msg in validation.errors:
                md += f"- **{msg.code}**: {msg.message}\n"
                if msg.suggestion:
                    md += f"  - *Suggestion*: {msg.suggestion}\n"
            md += "\n"

        if validation.warnings:
            md += "### Warnings\n\n"
            for msg in validation.warnings:
                md += f"- **{msg.code}**: {msg.message}\n"
                if msg.suggestion:
                    md += f"  - *Suggestion*: {msg.suggestion}\n"
            md += "\n"

        if validation.infos:
            md += "### Information\n\n"
            for msg in validation.infos:
                md += f"- {msg.message}\n"
            md += "\n"

    # Notes section
    md += "## Notes\n\n"
    md += "- All dimensions in millimeters unless otherwise noted\n"
    md += "- Efficiency estimate assumes steel worm on bronze wheel with lubrication\n"
    md += "- Self-locking determination is approximate - verify with actual materials\n"
    md += "- Throat diameter is for enveloping (throated) wheel design\n"
    if mfg.get('worm_length_mm') or mfg.get('wheel_width_mm'):
        md += "- Recommended dimensions are guidelines based on contact ratio requirements\n"
    md += "\n"

    # Footer
    md += "---\n"
    md += "*Generated by Wormgear Calculator*\n"

    return md


def to_summary(
    design: WormGearDesign,
    validation: Optional["ValidationResult"] = None,
    bore_settings: Optional[dict] = None,
    manufacturing_settings: Optional[dict] = None
) -> str:
    """Convert WormGearDesign to formatted text summary.

    Args:
        design: WormGearDesign dataclass from design_from_*() functions
        validation: Optional validation results (unused)
        bore_settings: Optional bore configuration (unused)
        manufacturing_settings: Optional manufacturing config (unused)

    Returns:
        Multi-line formatted summary string
    """
    # Convert to dict for easy field access
    design_dict = _serialize_enums(asdict(design))

    worm = design_dict["worm"]
    wheel = design_dict["wheel"]
    asm = design_dict["assembly"]
    mfg = design_dict.get("manufacturing") or {}

    # Get worm type for display
    worm_type_str = "cylindrical"
    if worm.get("type"):
        worm_type_str = worm["type"] if isinstance(worm["type"], str) else worm["type"]

    lines = [
        "═══ Worm Gear Design ═══",
        f"Ratio: {asm['ratio']}:1",
        f"Module: {worm['module_mm']:.3f} mm",
        f"Profile: {mfg.get('profile', 'ZA')} | Worm: {worm_type_str}",
        "",
        "Worm:",
        f"  Tip diameter (OD): {worm['tip_diameter_mm']:.2f} mm",
        f"  Pitch diameter:    {worm['pitch_diameter_mm']:.2f} mm",
        f"  Root diameter:     {worm['root_diameter_mm']:.2f} mm",
        f"  Lead angle:        {worm['lead_angle_deg']:.1f}°",
        f"  Starts:            {worm['num_starts']}",
    ]

    # Add globoid throat info if present
    if worm.get("throat_pitch_radius_mm"):
        lines.append(f"  Throat pitch rad:  {worm['throat_pitch_radius_mm']:.2f} mm")

    lines.extend([
        "",
        "Wheel:",
        f"  Tip diameter (OD): {wheel['tip_diameter_mm']:.2f} mm",
        f"  Pitch diameter:    {wheel['pitch_diameter_mm']:.2f} mm",
        f"  Root diameter:     {wheel['root_diameter_mm']:.2f} mm",
        f"  Teeth:             {wheel['num_teeth']}",
        f"  Helix angle:       {wheel['helix_angle_deg']:.1f}°",
        "",
        f"Centre distance: {asm['centre_distance_mm']:.2f} mm",
        f"Efficiency (est): {asm.get('efficiency_percent', 0):.0f}%",
        f"Self-locking: {'Yes' if asm.get('self_locking', False) else 'No'}",
    ])

    # Add manufacturing recommendations if present
    if mfg and ('worm_length_mm' in mfg or 'wheel_width_mm' in mfg):
        lines.extend([
            "",
            "Recommended Dimensions:",
        ])
        if 'worm_length_mm' in mfg:
            lines.append(f"  Worm length:  {mfg['worm_length_mm']:.2f} mm")
        if 'wheel_width_mm' in mfg:
            lines.append(f"  Wheel width:  {mfg['wheel_width_mm']:.2f} mm")

    return "\n".join(lines)
