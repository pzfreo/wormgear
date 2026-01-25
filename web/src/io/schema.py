"""
JSON schema definition and validation for worm gear parameters.

This defines the contract between wormgearcalc (calculator) and
wormgear-geometry (3D generation).

Schema v1.0 uses Option B: Separate features section for clean separation
between dimensional data and manufacturing features.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime

SCHEMA_VERSION = "1.0"


def get_schema_v1() -> Dict:
    """
    Get JSON schema version 1.0 (Option B: Separate features section).

    This is the standard format for exchanging worm gear parameters
    between the calculator and geometry generator.
    """
    return {
        "schema_version": "1.0",
        "required_sections": [
            "worm",
            "wheel",
            "assembly"
        ],
        "optional_sections": [
            "features",
            "manufacturing"
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
                "profile_shift",  # Profile shift coefficient
                "type",  # "cylindrical" or "globoid"
                "throat_reduction_mm",  # Globoid only
                "throat_curvature_radius_mm",  # Globoid only
                "length_mm"  # Actual length to generate (if not specified, CLI provides default)
            ]
        },
        "wheel_fields": {
            "required": [
                "module_mm",
                "num_teeth",
                "pitch_diameter_mm",
                "tip_diameter_mm",
                "root_diameter_mm",
                "throat_diameter_mm",
                "helix_angle_deg",
                "addendum_mm",
                "dedendum_mm"
            ],
            "optional": [
                "profile_shift",  # Profile shift coefficient
                "width_mm"  # Actual width to generate (if not specified, auto-calculated)
            ]
        },
        "assembly_fields": {
            "required": [
                "centre_distance_mm",
                "pressure_angle_deg",
                "backlash_mm",
                "hand",
                "ratio"
            ],
            "optional": [
                "efficiency_percent",
                "self_locking"
            ]
        },
        "features_section": {
            "worm": {
                "bore_diameter_mm": "float",  # Bore diameter (None for solid)
                "anti_rotation": "string",  # "none" | "DIN6885" | "ddcut"
                "ddcut_depth_percent": "float",  # DD-cut depth % (default: 15, only if anti_rotation="ddcut")
                "set_screw": {
                    "size": "string",  # e.g., "M2", "M3", "M4"
                    "count": "int"  # Number of set screws (1-3)
                }
            },
            "wheel": {
                "bore_diameter_mm": "float",
                "anti_rotation": "string",  # "none" | "DIN6885" | "ddcut"
                "ddcut_depth_percent": "float",  # DD-cut depth % (default: 15, only if anti_rotation="ddcut")
                "set_screw": {
                    "size": "string",
                    "count": "int"
                },
                "hub": {
                    "type": "string",  # "flush", "extended", "flanged"
                    "length_mm": "float",  # For extended/flanged
                    "flange_diameter_mm": "float",  # For flanged only
                    "flange_thickness_mm": "float",  # For flanged only
                    "bolt_holes": "int",  # For flanged only
                    "bolt_diameter_mm": "float"  # For flanged only
                }
            }
        },
        "manufacturing_fields": {
            "profile": "string",  # "ZA", "ZK", or "ZI" per DIN 3975
            "virtual_hobbing": "bool",  # True to use virtual hobbing for wheel
            "hobbing_steps": "int",  # Number of hobbing steps (default: 18)
            "throated_wheel": "bool",  # True for throated/hobbed wheel style
            "sections_per_turn": "int"  # Smoothness parameter (default: 36)
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
        warnings.append("Missing 'schema_version' field (assuming legacy format)")
    elif schema_version != SCHEMA_VERSION:
        warnings.append(f"Schema version {schema_version} != current {SCHEMA_VERSION}")

    # Validate required sections
    for section in ["worm", "wheel", "assembly"]:
        if section not in data:
            errors.append(f"Missing required section: '{section}'")

    # Validate anti_rotation field if features section exists
    if "features" in data:
        for part_name in ["worm", "wheel"]:
            if part_name in data["features"]:
                part_features = data["features"][part_name]
                anti_rot = part_features.get("anti_rotation")
                if anti_rot is not None:
                    valid_values = ["none", "DIN6885", "ddcut"]
                    if anti_rot not in valid_values:
                        errors.append(
                            f"Invalid anti_rotation value '{anti_rot}' for {part_name}. "
                            f"Must be one of: {', '.join(valid_values)}"
                        )
                    # Check that ddcut_depth_percent is provided if using ddcut
                    if anti_rot == "ddcut" and "ddcut_depth_percent" not in part_features:
                        warnings.append(
                            f"{part_name}.anti_rotation='ddcut' but ddcut_depth_percent not specified "
                            "(will use default 15%)"
                        )

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
    Create an example JSON file with all fields documented (Option B format).

    This can be used as a template by the calculator.
    """
    return {
        "schema_version": "1.0",
        "_generator": "wormgearcalc v2.0.0",
        "_created": datetime.now().isoformat(),
        "_note": "Example globoid worm gear with features - Schema v1.0 Option B",

        "worm": {
            # Core dimensions (required)
            "module_mm": 0.4,
            "num_starts": 1,
            "pitch_diameter_mm": 6.8,
            "tip_diameter_mm": 7.6,
            "root_diameter_mm": 5.8,
            "lead_mm": 1.257,
            "lead_angle_deg": 3.35,
            "addendum_mm": 0.4,
            "dedendum_mm": 0.5,
            "thread_thickness_mm": 0.628,
            "hand": "right",
            "profile_shift": 0.0,

            # Worm type (optional)
            "type": "globoid",  # "cylindrical" or "globoid"

            # Globoid-specific (only if type="globoid")
            "throat_reduction_mm": 0.05,
            "throat_curvature_radius_mm": 3.0,

            # Geometry override (optional)
            "length_mm": 6.0  # If omitted, CLI uses default
        },

        "wheel": {
            # Core dimensions (required)
            "module_mm": 0.4,
            "num_teeth": 15,
            "pitch_diameter_mm": 6.0,
            "tip_diameter_mm": 6.8,
            "root_diameter_mm": 5.1,
            "throat_diameter_mm": 6.4,
            "helix_angle_deg": 86.65,
            "addendum_mm": 0.4,
            "dedendum_mm": 0.45,
            "profile_shift": 0.0,

            # Geometry override (optional)
            "width_mm": 1.5  # If omitted, auto-calculated
        },

        "assembly": {
            "centre_distance_mm": 6.35,
            "pressure_angle_deg": 20.0,
            "backlash_mm": 0.02,
            "hand": "right",
            "ratio": 15,
            "efficiency_percent": None,
            "self_locking": False
        },

        # Optional: Manufacturing features (separate section - Option B)
        "features": {
            "worm": {
                "bore_diameter_mm": 2.0,
                "anti_rotation": "ddcut",  # "none" | "DIN6885" | "ddcut"
                "ddcut_depth_percent": 15.0,  # Only if anti_rotation="ddcut"
                "set_screw": {
                    "size": "M2",
                    "count": 1
                }
            },
            "wheel": {
                "bore_diameter_mm": 2.0,
                "anti_rotation": "DIN6885",  # Standard keyway
                "set_screw": None,
                "hub": {
                    "type": "flush",  # "flush", "extended", "flanged"
                    "length_mm": None,
                    "flange_diameter_mm": None,
                    "flange_thickness_mm": None,
                    "bolt_holes": None,
                    "bolt_diameter_mm": None
                }
            }
        },

        # Optional: Manufacturing parameters
        "manufacturing": {
            "profile": "ZA",  # "ZA" (straight), "ZK" (circular arc), "ZI" (involute)
            "virtual_hobbing": False,  # Use virtual hobbing simulation
            "hobbing_steps": 18,  # Number of hobbing steps
            "throated_wheel": False,  # Throated/hobbed wheel style
            "sections_per_turn": 36  # Smoothness parameter
        }
    }
