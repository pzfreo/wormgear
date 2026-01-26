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
    """Convert design to single-line summary.

    Args:
        design: WormGearDesign dataclass or dict
        validation: Optional validation results (unused, for API compatibility)
        bore_settings: Optional bore configuration (unused, for API compatibility)
        manufacturing_settings: Optional manufacturing config (unused, for API compatibility)

    Returns:
        Summary string
    """
    if isinstance(design, WormGearDesign):
        design_dict = asdict(design)
        design_dict = _serialize_enums(design_dict)
    else:
        design_dict = design

    worm = design_dict["worm"]
    wheel = design_dict["wheel"]
    asm = design_dict["assembly"]

    return f"Module {worm['module_mm']:.1f}mm, Ratio 1:{asm['ratio']}, CD={asm['centre_distance_mm']:.1f}mm"
