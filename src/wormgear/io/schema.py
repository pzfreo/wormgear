"""
JSON schema definition and validation for worm gear parameters.

This defines the contract between wormgearcalc (calculator) and
wormgear-geometry (3D generation).

Schema v2.0 uses Option B: Separate features section for clean separation
between dimensional data and manufacturing features.

Note: The primary schemas are now generated from Pydantic models via
scripts/generate_schemas.py. This module provides runtime validation helpers.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime

SCHEMA_VERSION = "2.1"


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


def detect_schema_version(data: Dict) -> str:
    """
    Detect schema version from JSON data using heuristics.

    Args:
        data: Parsed JSON data

    Returns:
        Version string (e.g., "1.0", "2.0")
    """
    # Explicit version takes precedence
    explicit_version = data.get('schema_version')
    if explicit_version:
        return str(explicit_version)

    # Heuristics for version detection
    if 'features' in data:
        # features section was added in 2.0
        return "2.0"
    if 'manufacturing' in data and 'worm_features' in data.get('manufacturing', {}):
        # Transitional version had features in manufacturing
        return "1.5"

    return "1.0"  # Default to oldest


def upgrade_schema(data: Dict, target_version: str = SCHEMA_VERSION) -> Dict:
    """
    Upgrade JSON data from older schema version to target version.

    Applies migrations sequentially from current version to target.
    Returns a new dict - original data is not modified.

    Args:
        data: JSON data with old schema
        target_version: Target schema version (default: latest)

    Returns:
        Upgraded JSON data (new dict)

    Raises:
        ValueError: If current version is newer than target or unsupported

    Example:
        >>> old_data = {"worm": {...}, "schema_version": "1.0"}
        >>> new_data = upgrade_schema(old_data, "2.0")
        >>> assert new_data["schema_version"] == "2.0"
    """
    import copy

    # Don't modify original
    data = copy.deepcopy(data)

    current_version = detect_schema_version(data)
    MIN_SUPPORTED_VERSION = "1.0"

    # Parse versions for comparison
    def version_tuple(v: str):
        return tuple(int(x) for x in v.split('.'))

    current = version_tuple(current_version)
    target = version_tuple(target_version)
    min_supported = version_tuple(MIN_SUPPORTED_VERSION)

    if current > target:
        raise ValueError(
            f"Cannot downgrade schema from {current_version} to {target_version}. "
            f"Use an older version of wormgear to read this file."
        )

    if current < min_supported:
        raise ValueError(
            f"Schema version {current_version} is too old. "
            f"Minimum supported version is {MIN_SUPPORTED_VERSION}."
        )

    # Apply migrations in sequence
    if current < (2, 0) and target >= (2, 0):
        data = _migrate_1x_to_2x(data)

    data['schema_version'] = target_version
    return data


def _migrate_1x_to_2x(data: Dict) -> Dict:
    """
    Migrate from schema 1.x to 2.x.

    Changes:
    - Move worm_features/wheel_features from manufacturing to features section
    - Normalize enum values (hand to lowercase, profile to uppercase)
    - Add missing required fields with defaults
    - Add _upgraded_from metadata
    """
    # Track upgrade
    data['_upgraded_from'] = data.get('schema_version', '1.0')

    # 1. Move features from manufacturing to features section
    manufacturing = data.get('manufacturing', {})

    if 'worm_features' in manufacturing or 'wheel_features' in manufacturing:
        if 'features' not in data:
            data['features'] = {}

        # Only migrate if target doesn't already exist (preserve existing features)
        if 'worm_features' in manufacturing:
            if 'worm' not in data['features']:
                data['features']['worm'] = manufacturing.pop('worm_features')
            else:
                manufacturing.pop('worm_features')  # Just remove, don't overwrite

        if 'wheel_features' in manufacturing:
            if 'wheel' not in data['features']:
                data['features']['wheel'] = manufacturing.pop('wheel_features')
            else:
                manufacturing.pop('wheel_features')  # Just remove, don't overwrite

    # 2. Normalize hand enum (was uppercase in some 1.x versions)
    for section in ['worm', 'assembly']:
        if section in data and 'hand' in data[section]:
            hand_value = data[section]['hand']
            if isinstance(hand_value, str):
                data[section]['hand'] = hand_value.lower()

    # 3. Normalize profile enum (should be uppercase)
    if 'manufacturing' in data and 'profile' in data['manufacturing']:
        profile_value = data['manufacturing']['profile']
        if isinstance(profile_value, str):
            data['manufacturing']['profile'] = profile_value.upper()

    # 4. Ensure features section exists with defaults
    if 'features' not in data:
        data['features'] = {
            'worm': {'bore_type': 'none'},
            'wheel': {'bore_type': 'none'}
        }

    return data


def validate_schema_version(data: Dict) -> bool:
    """
    Check if schema version is supported for loading.

    Args:
        data: JSON data to check

    Returns:
        True if version is supported
    """
    version = detect_schema_version(data)

    def version_tuple(v: str):
        return tuple(int(x) for x in v.split('.'))

    MIN_SUPPORTED = "1.0"
    current = version_tuple(version)
    min_supported = version_tuple(MIN_SUPPORTED)
    max_supported = version_tuple(SCHEMA_VERSION)

    return min_supported <= current <= max_supported


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
