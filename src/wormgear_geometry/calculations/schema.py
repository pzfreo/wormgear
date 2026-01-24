"""
JSON schema definition and validation for worm gear parameters.

This defines the contract between wormgearcalc (calculator) and
wormgear-geometry (3D generation).
"""

from typing import Dict, List, Optional, Any
from datetime import datetime

SCHEMA_VERSION = "1.0"


def get_schema_v1() -> Dict:
    """
    Get JSON schema version 1.0.

    This is the standard format for exchanging worm gear parameters
    between the calculator and geometry generator.
    """
    return {
        "schema_version": "1.0",
        "required_fields": [
            "schema_version",
            "worm",
            "wheel",
            "assembly"
        ],
        "worm_fields": {
            "required": [
                "module_mm",
                "num_starts",
                "pitch_diameter_mm",
                "tip_diameter_mm",
                "root_diameter_mm",
                "lead_mm",
                "lead_angle_deg",
                "addendum_mm",
                "dedendum_mm",
                "thread_thickness_mm",
                "hand"
            ],
            "optional": [
                "type",  # "cylindrical" or "globoid"
                "profile_shift",
                "throat_reduction_mm",  # Globoid only
                "throat_curvature_radius_mm",  # Globoid only
                "recommended_length_mm",  # Calculator suggestion
                "min_length_mm",  # Calculator constraint
                "length_mm",  # Actual length to generate
                "bore_diameter_mm",  # Bore diameter (None for solid)
                "bore_auto",  # True to auto-calculate bore
                "keyway_standard",  # "DIN6885" or "none"
                "keyway_auto",  # True to auto-size keyway to bore
                "set_screw_diameter_mm",  # Set screw size
                "set_screw_count"  # Number of set screws
            ]
        },
        "wheel_fields": {
            "required": [
                "module_mm",
                "num_teeth",
                "pitch_diameter_mm",
                "tip_diameter_mm",
                "root_diameter_mm",
                "addendum_mm",
                "dedendum_mm"
            ],
            "optional": [
                "throat_diameter_mm",
                "helix_angle_deg",
                "profile_shift",
                "recommended_width_mm",  # Calculator suggestion
                "max_width_mm",  # Calculator constraint
                "min_width_mm",  # Calculator constraint
                "width_mm",  # Actual width to generate
                "bore_diameter_mm",  # Bore diameter (None for solid)
                "bore_auto",  # True to auto-calculate bore
                "keyway_standard",  # "DIN6885" or "none"
                "keyway_auto",  # True to auto-size keyway to bore
                "set_screw_diameter_mm",  # Set screw size
                "set_screw_count",  # Number of set screws
                "hub_type",  # "flush", "extended", "flanged", or "none"
                "hub_length_mm",  # Hub extension length
                "hub_flange_diameter_mm",  # Flange diameter (flanged only)
                "hub_bolt_holes"  # Number of bolt holes (flanged only)
            ]
        },
        "assembly_fields": {
            "required": [
                "centre_distance_mm",
                "pressure_angle_deg",
                "hand",
                "ratio"
            ],
            "optional": [
                "backlash_mm"
            ]
        },
        "manufacturing_fields": {
            "required": [],
            "optional": [
                "profile",  # "ZA", "ZK", or "ZI" per DIN 3975
                "virtual_hobbing",  # True to use virtual hobbing for wheel
                "hobbing_steps",  # Number of hobbing steps (default 18)
                "throated_wheel",  # True for throated/hobbed wheel style
                "sections_per_turn"  # Smoothness parameter (default 36)
            ]
        }
    }


def validate_json_schema(data: Dict) -> Dict[str, Any]:
    """
    Validate JSON data against schema.

    Args:
        data: Parsed JSON data

    Returns:
        {
            "valid": bool,
            "errors": List[str],
            "warnings": List[str],
            "schema_version": str
        }

    Example:
        >>> data = load_json("design.json")
        >>> result = validate_json_schema(data)
        >>> if not result["valid"]:
        ...     print(f"Errors: {result['errors']}")
    """
    errors = []
    warnings = []

    # Check schema version
    schema_version = data.get("schema_version", "unknown")
    if schema_version == "unknown":
        errors.append("Missing 'schema_version' field")
    elif schema_version != SCHEMA_VERSION:
        warnings.append(f"Schema version {schema_version} != current {SCHEMA_VERSION}")

    # TODO: Validate required fields
    # TODO: Validate field types
    # TODO: Validate value ranges

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "schema_version": schema_version
    }


def upgrade_schema(data: Dict, target_version: str = SCHEMA_VERSION) -> Dict:
    """
    Upgrade JSON data from older schema version to target version.

    Args:
        data: JSON data with old schema
        target_version: Target schema version (default: latest)

    Returns:
        Upgraded JSON data

    Example:
        >>> old_data = {"worm": {...}}  # No schema_version
        >>> new_data = upgrade_schema(old_data, "1.0")
        >>> assert new_data["schema_version"] == "1.0"
    """
    current_version = data.get("schema_version", "0.0")

    if current_version == target_version:
        return data

    # TODO: Implement version upgrades when we have v1.1, v2.0, etc.
    # For now, just add schema_version if missing
    if "schema_version" not in data:
        data["schema_version"] = "1.0"
        data["_upgraded_from"] = "pre-v1.0"

    return data


def create_example_schema_v1() -> Dict:
    """
    Create an example JSON file with all fields documented.

    This can be used as a template by the calculator.
    """
    return {
        "schema_version": "1.0",
        "_generator": "wormgearcalc v2.0.0",
        "_created": datetime.now().isoformat(),
        "_note": "Example globoid worm gear parameters",

        "worm": {
            "type": "globoid",  # "cylindrical" or "globoid"
            "module_mm": 0.4,
            "num_starts": 1,
            "pitch_diameter_mm": 6.2,
            "tip_diameter_mm": 7.0,
            "root_diameter_mm": 5.2,
            "lead_mm": 1.257,
            "lead_angle_deg": 3.67,
            "addendum_mm": 0.4,
            "dedendum_mm": 0.5,
            "thread_thickness_mm": 0.628,
            "hand": "right",
            "profile_shift": 0.0,

            # Globoid-specific (only if type="globoid")
            "throat_reduction_mm": 0.0,
            "throat_curvature_radius_mm": 3.0,

            # Recommendations from calculator
            "recommended_length_mm": 6.0,
            "min_length_mm": 5.0,

            # Geometry parameters (optional, can override on CLI)
            "length_mm": 6.0,  # Actual length to generate
            "bore_diameter_mm": null,  # null for solid, or diameter
            "bore_auto": true,  # Auto-calculate bore size
            "keyway_standard": "DIN6885",  # "DIN6885" or "none"
            "keyway_auto": true,  # Auto-size keyway to bore
            "set_screw_diameter_mm": null,  # Set screw size (optional)
            "set_screw_count": 0  # Number of set screws
        },

        "wheel": {
            "module_mm": 0.4,
            "num_teeth": 15,
            "pitch_diameter_mm": 6.0,
            "tip_diameter_mm": 6.8,
            "root_diameter_mm": 5.1,
            "throat_diameter_mm": 6.4,
            "helix_angle_deg": 86.33,
            "addendum_mm": 0.4,
            "dedendum_mm": 0.45,
            "profile_shift": 0.0,

            # Recommendations from calculator
            "recommended_width_mm": 1.5,
            "max_width_mm": 1.5,
            "min_width_mm": 0.8,

            # Geometry parameters (optional, can override on CLI)
            "width_mm": 1.5,  # Actual width to generate
            "bore_diameter_mm": null,  # null for solid, or diameter
            "bore_auto": true,  # Auto-calculate bore size
            "keyway_standard": "DIN6885",  # "DIN6885" or "none"
            "keyway_auto": true,  # Auto-size keyway to bore
            "set_screw_diameter_mm": null,  # Set screw size (optional)
            "set_screw_count": 0,  # Number of set screws
            "hub_type": "flush",  # "flush", "extended", "flanged", or "none"
            "hub_length_mm": null,  # Hub extension length (extended/flanged)
            "hub_flange_diameter_mm": null,  # Flange diameter (flanged only)
            "hub_bolt_holes": 0  # Number of bolt holes (flanged only)
        },

        "assembly": {
            "centre_distance_mm": 6.1,
            "pressure_angle_deg": 20.0,
            "backlash_mm": 0.02,
            "hand": "right",
            "ratio": 15
        },

        "manufacturing": {
            "profile": "ZA",  # Tooth profile: "ZA" (straight), "ZK" (circular arc), "ZI" (involute)
            "virtual_hobbing": false,  # Use virtual hobbing simulation for wheel
            "hobbing_steps": 18,  # Number of steps for virtual hobbing (if enabled)
            "throated_wheel": false,  # True for throated/hobbed wheel style
            "sections_per_turn": 36  # Loft sections per helix turn (smoothness)
        },

        "validation": {
            "valid": true,
            "warnings": [
                "Throat reduction 0mm - nearly cylindrical"
            ],
            "errors": [],
            "clearance_mm": 0.05  # centre_distance - worm_tip - wheel_root
        }
    }
