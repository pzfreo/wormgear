"""
JSON Schema validation for wormgear design format.

Validates the structure and types of wormgear JSON documents
according to schema v1.0.
"""
from typing import Dict, Any, List, Optional, Tuple


class ValidationError(Exception):
    """Raised when JSON structure validation fails."""
    pass


def validate_design_json(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate design JSON structure against wormgear schema v1.0.

    Args:
        data: Parsed JSON data to validate

    Returns:
        Tuple of (is_valid, list_of_error_messages)
    """
    errors = []

    # Check root structure
    if not isinstance(data, dict):
        return False, ["Root must be a JSON object/dict"]

    # Validate required top-level sections
    required_sections = ['worm', 'wheel', 'assembly']
    for section in required_sections:
        if section not in data:
            errors.append(f"Missing required section: '{section}'")
        elif not isinstance(data[section], dict):
            errors.append(f"Section '{section}' must be an object/dict")

    # If missing required sections, return early
    if errors:
        return False, errors

    # Validate worm section
    worm_errors = _validate_worm_section(data['worm'])
    errors.extend([f"worm.{e}" for e in worm_errors])

    # Validate wheel section
    wheel_errors = _validate_wheel_section(data['wheel'])
    errors.extend([f"wheel.{e}" for e in wheel_errors])

    # Validate assembly section
    assembly_errors = _validate_assembly_section(data['assembly'])
    errors.extend([f"assembly.{e}" for e in assembly_errors])

    # Validate optional sections
    if 'manufacturing' in data:
        if not isinstance(data['manufacturing'], dict):
            errors.append("manufacturing section must be an object/dict")
        else:
            mfg_errors = _validate_manufacturing_section(data['manufacturing'])
            errors.extend([f"manufacturing.{e}" for e in mfg_errors])

    if 'features' in data:
        if not isinstance(data['features'], dict):
            errors.append("features section must be an object/dict")
        else:
            feat_errors = _validate_features_section(data['features'])
            errors.extend([f"features.{e}" for e in feat_errors])

    return len(errors) == 0, errors


def _validate_worm_section(worm: Dict[str, Any]) -> List[str]:
    """Validate worm section structure."""
    errors = []

    # Required numeric fields
    required_numeric = [
        'module_mm', 'num_starts', 'pitch_diameter_mm', 'tip_diameter_mm',
        'root_diameter_mm', 'lead_mm', 'lead_angle_deg', 'addendum_mm',
        'dedendum_mm', 'thread_thickness_mm'
    ]
    for field in required_numeric:
        if field not in worm:
            errors.append(f"missing required field '{field}'")
        elif not isinstance(worm[field], (int, float)):
            errors.append(f"'{field}' must be numeric, got {type(worm[field]).__name__}")

    # Required string fields
    if 'hand' not in worm:
        errors.append("missing required field 'hand'")
    elif worm['hand'] not in ['right', 'left']:
        errors.append(f"'hand' must be 'right' or 'left', got '{worm['hand']}'")

    # Optional numeric fields
    optional_numeric = ['throat_curvature_radius_mm', 'profile_shift', 'length_mm']
    for field in optional_numeric:
        if field in worm and worm[field] is not None:
            if not isinstance(worm[field], (int, float)):
                errors.append(f"'{field}' must be numeric, got {type(worm[field]).__name__}")

    return errors


def _validate_wheel_section(wheel: Dict[str, Any]) -> List[str]:
    """Validate wheel section structure."""
    errors = []

    # Required numeric fields
    required_numeric = [
        'module_mm', 'num_teeth', 'pitch_diameter_mm', 'tip_diameter_mm',
        'root_diameter_mm', 'throat_diameter_mm', 'helix_angle_deg',
        'addendum_mm', 'dedendum_mm'
    ]
    for field in required_numeric:
        if field not in wheel:
            errors.append(f"missing required field '{field}'")
        elif not isinstance(wheel[field], (int, float)):
            errors.append(f"'{field}' must be numeric, got {type(wheel[field]).__name__}")

    # Optional numeric fields
    optional_numeric = ['profile_shift', 'width_mm']
    for field in optional_numeric:
        if field in wheel and wheel[field] is not None:
            if not isinstance(wheel[field], (int, float)):
                errors.append(f"'{field}' must be numeric, got {type(wheel[field]).__name__}")

    return errors


def _validate_assembly_section(assembly: Dict[str, Any]) -> List[str]:
    """Validate assembly section structure."""
    errors = []

    # Required numeric fields
    required_numeric = [
        'centre_distance_mm', 'pressure_angle_deg', 'backlash_mm', 'ratio'
    ]
    for field in required_numeric:
        if field not in assembly:
            errors.append(f"missing required field '{field}'")
        elif not isinstance(assembly[field], (int, float)):
            errors.append(f"'{field}' must be numeric, got {type(assembly[field]).__name__}")

    # Required string fields
    if 'hand' not in assembly:
        errors.append("missing required field 'hand'")
    elif assembly['hand'] not in ['right', 'left']:
        errors.append(f"'hand' must be 'right' or 'left', got '{assembly['hand']}'")

    # Optional string field
    if 'profile' in assembly:
        if assembly['profile'] not in ['ZA', 'ZK', 'ZI']:
            errors.append(f"'profile' must be 'ZA', 'ZK', or 'ZI', got '{assembly['profile']}'")

    # Optional numeric fields
    optional_numeric = ['efficiency', 'self_locking']
    for field in optional_numeric:
        if field in assembly and assembly[field] is not None:
            if not isinstance(assembly[field], (int, float, bool)):
                errors.append(f"'{field}' has invalid type {type(assembly[field]).__name__}")

    return errors


def _validate_manufacturing_section(manufacturing: Dict[str, Any]) -> List[str]:
    """Validate optional manufacturing section structure."""
    errors = []

    # All fields are optional, but if present must have correct types
    if 'worm_type' in manufacturing:
        if manufacturing['worm_type'] not in ['cylindrical', 'globoid']:
            errors.append(f"'worm_type' must be 'cylindrical' or 'globoid', got '{manufacturing['worm_type']}'")

    if 'profile' in manufacturing:
        if manufacturing['profile'] not in ['ZA', 'ZK', 'ZI']:
            errors.append(f"'profile' must be 'ZA', 'ZK', or 'ZI', got '{manufacturing['profile']}'")

    if 'wheel_throated' in manufacturing:
        if not isinstance(manufacturing['wheel_throated'], bool):
            errors.append(f"'wheel_throated' must be boolean, got {type(manufacturing['wheel_throated']).__name__}")

    optional_numeric = ['worm_length', 'wheel_width', 'hobbing_steps']
    for field in optional_numeric:
        if field in manufacturing and manufacturing[field] is not None:
            if not isinstance(manufacturing[field], (int, float)):
                errors.append(f"'{field}' must be numeric, got {type(manufacturing[field]).__name__}")

    if 'virtual_hobbing' in manufacturing:
        if not isinstance(manufacturing['virtual_hobbing'], bool):
            errors.append(f"'virtual_hobbing' must be boolean, got {type(manufacturing['virtual_hobbing']).__name__}")

    return errors


def _validate_features_section(features: Dict[str, Any]) -> List[str]:
    """Validate optional features section structure."""
    errors = []

    # Validate worm features if present
    if 'worm' in features:
        if not isinstance(features['worm'], dict):
            errors.append("'worm' must be an object/dict")
        else:
            worm_feat_errors = _validate_part_features(features['worm'], 'worm')
            errors.extend(worm_feat_errors)

    # Validate wheel features if present
    if 'wheel' in features:
        if not isinstance(features['wheel'], dict):
            errors.append("'wheel' must be an object/dict")
        else:
            wheel_feat_errors = _validate_part_features(features['wheel'], 'wheel')
            errors.extend(wheel_feat_errors)

    return errors


def _validate_part_features(part_features: Dict[str, Any], part_name: str) -> List[str]:
    """Validate features for a specific part (worm or wheel)."""
    errors = []

    # Check bore diameter if present
    if 'bore_diameter_mm' in part_features:
        if not isinstance(part_features['bore_diameter_mm'], (int, float)):
            errors.append(f"{part_name}.bore_diameter_mm must be numeric")
        elif part_features['bore_diameter_mm'] <= 0:
            errors.append(f"{part_name}.bore_diameter_mm must be positive")

    # Check auto_bore flag if present
    if 'auto_bore' in part_features:
        if not isinstance(part_features['auto_bore'], bool):
            errors.append(f"{part_name}.auto_bore must be boolean")

    # Check anti_rotation if present
    if 'anti_rotation' in part_features:
        valid_anti_rotation = ['none', 'DIN6885', 'DD-cut']
        if part_features['anti_rotation'] not in valid_anti_rotation:
            errors.append(f"{part_name}.anti_rotation must be one of {valid_anti_rotation}")

    return errors


def validate_and_raise(data: Dict[str, Any]) -> None:
    """
    Validate design JSON and raise ValidationError if invalid.

    Args:
        data: Parsed JSON data to validate

    Raises:
        ValidationError: If validation fails
    """
    is_valid, errors = validate_design_json(data)
    if not is_valid:
        error_msg = "JSON validation failed:\n  " + "\n  ".join(errors)
        raise ValidationError(error_msg)
