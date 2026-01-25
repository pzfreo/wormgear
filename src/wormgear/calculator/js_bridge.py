"""
JavaScript-Python boundary layer for Pyodide.

Handles type conversions and validation when passing data between
JavaScript and Python in the browser environment.
"""
from typing import Any, Dict, Optional, Union


def sanitize_js_value(value: Any) -> Any:
    """
    Convert JavaScript value to Python, handling Pyodide edge cases.

    Handles:
    - JsNull (JavaScript null) → None
    - JavaScript undefined → None
    - JavaScript true/false → Python True/False (already handled by Pyodide)
    - Empty strings → None
    - Invalid numeric types

    Args:
        value: Value from JavaScript (may be JsNull, JsProxy, or native Python)

    Returns:
        Sanitized Python value or None
    """
    # Handle JsNull (Pyodide's representation of JavaScript null)
    if value is None:
        return None

    # Check for JsNull by class name (can't import it directly)
    if hasattr(value, '__class__'):
        class_name = str(value.__class__)
        if 'JsNull' in class_name or 'JsUndefined' in class_name:
            return None

    # Empty string → None
    if value == '':
        return None

    # Boolean false is valid, but check for it explicitly
    if isinstance(value, bool):
        return value

    return value


def sanitize_numeric(value: Any, allow_none: bool = True) -> Optional[float]:
    """
    Convert value to float, handling JS edge cases.

    Args:
        value: Value that should be numeric
        allow_none: If True, None/null values return None; if False, raises ValueError

    Returns:
        Float value or None

    Raises:
        ValueError: If value is invalid and allow_none is False
    """
    sanitized = sanitize_js_value(value)

    if sanitized is None:
        if allow_none:
            return None
        raise ValueError(f"Expected numeric value, got None/null")

    try:
        return float(sanitized)
    except (TypeError, ValueError) as e:
        if allow_none:
            return None
        raise ValueError(f"Cannot convert {sanitized!r} to float: {e}")


def sanitize_boolean(value: Any, default: bool = False) -> bool:
    """
    Convert value to boolean, handling JS edge cases.

    Args:
        value: Value that should be boolean
        default: Default value if conversion fails

    Returns:
        Boolean value
    """
    sanitized = sanitize_js_value(value)

    if sanitized is None:
        return default

    if isinstance(sanitized, bool):
        return sanitized

    # Handle string booleans
    if isinstance(sanitized, str):
        return sanitized.lower() in ('true', '1', 'yes', 'on')

    # Truthy conversion
    return bool(sanitized)


def sanitize_string(value: Any, allow_none: bool = True) -> Optional[str]:
    """
    Convert value to string, handling JS edge cases.

    Args:
        value: Value that should be string
        allow_none: If True, None/null values return None; if False, raises ValueError

    Returns:
        String value or None

    Raises:
        ValueError: If value is invalid and allow_none is False
    """
    sanitized = sanitize_js_value(value)

    if sanitized is None:
        if allow_none:
            return None
        raise ValueError("Expected string value, got None/null")

    return str(sanitized)


def sanitize_dict(js_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively sanitize a dictionary from JavaScript.

    Converts all values using sanitize_js_value, removing entries that
    become None unless explicitly needed.

    Args:
        js_dict: Dictionary potentially containing JS types

    Returns:
        Dictionary with sanitized Python values
    """
    if js_dict is None:
        return {}

    result = {}
    for key, value in js_dict.items():
        # Recursively handle nested dicts
        if isinstance(value, dict):
            result[key] = sanitize_dict(value)
        # Recursively handle lists
        elif isinstance(value, list):
            result[key] = [sanitize_dict(v) if isinstance(v, dict) else sanitize_js_value(v)
                          for v in value]
        # Sanitize scalar values
        else:
            sanitized = sanitize_js_value(value)
            # Keep the value even if None (let calling code decide if it's valid)
            result[key] = sanitized

    return result


def validate_manufacturing_settings(settings: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validate and sanitize manufacturing settings from JavaScript.

    Args:
        settings: Manufacturing settings dict (or None)

    Returns:
        Validated and sanitized settings dict with all keys present
    """
    sanitized = sanitize_dict(settings) if settings else {}

    # Get hobbing_steps with proper fallback
    hobbing_steps_value = sanitize_numeric(sanitized.get('hobbing_steps'), allow_none=True)
    hobbing_steps = int(hobbing_steps_value) if hobbing_steps_value else 72

    return {
        'virtual_hobbing': sanitize_boolean(sanitized.get('virtual_hobbing'), default=False),
        'hobbing_steps': hobbing_steps,
        'use_recommended_dims': sanitize_boolean(sanitized.get('use_recommended_dims'), default=True),
        'worm_length': sanitize_numeric(sanitized.get('worm_length'), allow_none=True),
        'wheel_width': sanitize_numeric(sanitized.get('wheel_width'), allow_none=True),
    }


def validate_bore_settings(settings: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validate and sanitize bore settings from JavaScript.

    Args:
        settings: Bore settings dict (or None)

    Returns:
        Validated and sanitized settings dict
    """
    if not settings:
        return {}

    sanitized = sanitize_dict(settings)

    result = {}

    # Worm bore
    worm_bore_type = sanitize_string(sanitized.get('worm_bore_type'), allow_none=True)
    if worm_bore_type and worm_bore_type != 'none':
        result['worm_bore_type'] = worm_bore_type
        if worm_bore_type == 'custom':
            result['worm_bore_diameter'] = sanitize_numeric(sanitized.get('worm_bore_diameter'), allow_none=False)

    # Worm keyway
    worm_keyway = sanitize_string(sanitized.get('worm_keyway'), allow_none=True)
    if worm_keyway and worm_keyway != 'none':
        result['worm_keyway'] = worm_keyway

    # Wheel bore
    wheel_bore_type = sanitize_string(sanitized.get('wheel_bore_type'), allow_none=True)
    if wheel_bore_type and wheel_bore_type != 'none':
        result['wheel_bore_type'] = wheel_bore_type
        if wheel_bore_type == 'custom':
            result['wheel_bore_diameter'] = sanitize_numeric(sanitized.get('wheel_bore_diameter'), allow_none=False)

    # Wheel keyway
    wheel_keyway = sanitize_string(sanitized.get('wheel_keyway'), allow_none=True)
    if wheel_keyway and wheel_keyway != 'none':
        result['wheel_keyway'] = wheel_keyway

    return result
