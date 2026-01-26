"""Output formatters for worm gear designs.

Simple JSON export for WormGearDesign dataclasses.
"""

import json
from dataclasses import asdict
from enum import Enum
from typing import Union, Optional, TYPE_CHECKING, Any

from ..io import WormGearDesign

if TYPE_CHECKING:
    from .validation import ValidationResult


def _serialize_enums(obj: Any) -> Any:
    """Recursively convert enum values to strings for JSON serialization.

    Args:
        obj: Object to serialize (dict, list, enum, or primitive)

    Returns:
        JSON-serializable version of obj
    """
    if isinstance(obj, Enum):
        return obj.value
    elif isinstance(obj, dict):
        return {key: _serialize_enums(value) for key, value in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_serialize_enums(item) for item in obj]
    else:
        return obj


def to_json(
    design: Union[WormGearDesign, dict],
    validation: Optional["ValidationResult"] = None,
    indent: int = 2,
    bore_settings: Optional[dict] = None,
    manufacturing_settings: Optional[dict] = None
) -> str:
    """Convert design to JSON string.

    Args:
        design: WormGearDesign dataclass or dict from design_from_*() functions
        validation: Optional validation results to include in output
        indent: JSON indentation level (default: 2)
        bore_settings: Optional bore configuration (for backward compatibility)
        manufacturing_settings: Optional manufacturing config (for backward compatibility)

    Returns:
        JSON string with optional validation, bore, and manufacturing data
    """
    # Convert dataclass to dict if needed
    if isinstance(design, WormGearDesign):
        design_dict = asdict(design)
        # Serialize enums to their string values
        design_dict = _serialize_enums(design_dict)
    else:
        # Already a dict (from design_from_module etc)
        design_dict = design.copy()

    # Add schema version for compatibility
    if 'schema_version' not in design_dict:
        design_dict['schema_version'] = '1.0'

    # Merge in bore settings if provided
    if bore_settings:
        design_dict.setdefault('bore', {}).update(bore_settings)

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
    design: Union[WormGearDesign, dict],
    validation: Optional["ValidationResult"] = None,
    bore_settings: Optional[dict] = None,
    manufacturing_settings: Optional[dict] = None
) -> str:
    """Convert design to markdown summary.

    Args:
        design: WormGearDesign dataclass or dict
        validation: Optional validation results (unused, for API compatibility)
        bore_settings: Optional bore configuration (unused, for API compatibility)
        manufacturing_settings: Optional manufacturing config (unused, for API compatibility)

    Returns:
        Markdown string
    """
    if isinstance(design, WormGearDesign):
        # Convert dataclass to dict for easier access
        design_dict = asdict(design)
        design_dict = _serialize_enums(design_dict)
    else:
        design_dict = design

    worm = design_dict["worm"]
    wheel = design_dict["wheel"]
    asm = design_dict["assembly"]

    md = "# Worm Gear Design\n\n"
    md += "## Worm\n"
    md += f"- Module: {worm['module_mm']:.3f} mm\n"
    md += f"- Starts: {worm['num_starts']}\n"
    md += f"- Pitch Diameter: {worm['pitch_diameter_mm']:.3f} mm\n"
    md += f"- Lead: {worm['lead_mm']:.3f} mm\n"
    md += f"- Lead Angle: {worm['lead_angle_deg']:.2f}°\n\n"

    md += "## Wheel\n"
    md += f"- Teeth: {wheel['num_teeth']}\n"
    md += f"- Pitch Diameter: {wheel['pitch_diameter_mm']:.3f} mm\n"
    md += f"- Tip Diameter: {wheel['tip_diameter_mm']:.3f} mm\n\n"

    md += "## Assembly\n"
    md += f"- Centre Distance: {asm['centre_distance_mm']:.3f} mm\n"
    md += f"- Ratio: 1:{asm['ratio']}\n"
    md += f"- Hand: {asm['hand']}\n"

    return md


def to_summary(
    design: Union[WormGearDesign, dict],
    validation: Optional["ValidationResult"] = None,
    bore_settings: Optional[dict] = None,
    manufacturing_settings: Optional[dict] = None
) -> str:
    """Convert design to formatted text summary.

    Args:
        design: WormGearDesign dataclass or dict
        validation: Optional validation results (unused, for API compatibility)
        bore_settings: Optional bore configuration (unused, for API compatibility)
        manufacturing_settings: Optional manufacturing config (unused, for API compatibility)

    Returns:
        Multi-line formatted summary string
    """
    if isinstance(design, WormGearDesign):
        design_dict = asdict(design)
        design_dict = _serialize_enums(design_dict)
    else:
        design_dict = design

    worm = design_dict["worm"]
    wheel = design_dict["wheel"]
    asm = design_dict["assembly"]
    mfg = design_dict.get("manufacturing", {})

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
