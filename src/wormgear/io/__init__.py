"""
Wormgear IO - JSON schema, loaders, and exporters.

This module handles JSON serialization/deserialization and output generation.

Example:
    >>> from wormgear.io import load_design_json, save_design_json
    >>> from wormgear.calculator import design_from_module
    >>>
    >>> # Calculate design
    >>> design = design_from_module(module=2.0, ratio=30)
    >>>
    >>> # Save to JSON
    >>> save_design_json(design, "design.json")
    >>>
    >>> # Load back
    >>> loaded = load_design_json("design.json")
"""

# Temporarily import from parent (will be moved here)
from ..io import (
    load_design_json,
    save_design_json,
    WormParams,
    WheelParams,
    AssemblyParams,
    WormGearDesign,
    Features,
    WormFeatures,
    WheelFeatures,
    SetScrewSpec,
    HubSpec,
    ManufacturingParams,
)

__all__ = [
    "load_design_json",
    "save_design_json",
    "WormParams",
    "WheelParams",
    "AssemblyParams",
    "WormGearDesign",
    "Features",
    "WormFeatures",
    "WheelFeatures",
    "SetScrewSpec",
    "HubSpec",
    "ManufacturingParams",
]
