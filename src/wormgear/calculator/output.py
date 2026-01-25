"""Output formatters for worm gear designs.

Simple JSON export for WormGearDesign dataclasses.
"""

import json
from dataclasses import asdict
from typing import Union

from ..io import WormGearDesign


def to_json(design: Union[WormGearDesign, dict]) -> str:
    """Convert design to JSON string.

    Args:
        design: WormGearDesign dataclass or dict from design_from_*() functions

    Returns:
        JSON string
    """
    if isinstance(design, dict):
        # Already a dict (from design_from_module etc)
        # Enums already serialized to strings (.value)
        return json.dumps(design, indent=2)

    # WormGearDesign dataclass - convert to dict and serialize enums
    design_dict = asdict(design)

    # Convert enum values to strings
    if "worm" in design_dict and "hand" in design_dict["worm"]:
        # Already a string from asdict if enum
        pass

    if "assembly" in design_dict and "hand" in design_dict["assembly"]:
        pass

    if "manufacturing" in design_dict and "profile" in design_dict["manufacturing"]:
        pass

    return json.dumps(design_dict, indent=2)


def to_markdown(design: Union[WormGearDesign, dict]) -> str:
    """Convert design to markdown summary.

    Args:
        design: WormGearDesign dataclass or dict

    Returns:
        Markdown string
    """
    if isinstance(design, WormGearDesign):
        # Convert dataclass to dict for easier access
        design = asdict(design)

    worm = design["worm"]
    wheel = design["wheel"]
    asm = design["assembly"]

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


def to_summary(design: Union[WormGearDesign, dict]) -> str:
    """Convert design to single-line summary.

    Args:
        design: WormGearDesign dataclass or dict

    Returns:
        Summary string
    """
    if isinstance(design, WormGearDesign):
        design = asdict(design)

    worm = design["worm"]
    wheel = design["wheel"]
    asm = design["assembly"]

    return f"Module {worm['module_mm']:.1f}mm, Ratio 1:{asm['ratio']}, CD={asm['centre_distance_mm']:.1f}mm"
