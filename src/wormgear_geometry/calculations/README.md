# Calculations Module

This module contains pure mathematical calculations for worm gear design. It has **NO build123d dependency** and can be imported by the calculator (wormgearcalc) to provide a single source of truth for all worm gear mathematics.

## Purpose

Avoid code duplication between:
- **wormgear-geometry** (this project): 3D geometry generation
- **wormgearcalc** (calculator project): Parameter selection UI

All worm gear calculations live HERE, and the calculator imports them.

## Installation

For calculator (lightweight, no 3D dependencies):
```bash
pip install wormgear-geometry[calc]
```

## Usage by Calculator

```python
from wormgear_geometry.calculations import (
    # Globoid calculations
    calculate_max_wheel_width,
    calculate_recommended_worm_length,
    validate_globoid_constraints,
    calculate_throat_geometry,

    # Schema
    SCHEMA_VERSION,
    validate_json_schema,
    upgrade_schema,
)

# Example: Calculate max wheel width for globoid
max_width = calculate_max_wheel_width(
    throat_reduction_mm=0.05,
    worm_addendum_mm=0.4,
    wheel_dedendum_mm=0.5,
    centre_distance_mm=6.35,
    wheel_pitch_radius_mm=3.0,
    throat_pitch_radius_mm=3.35
)
# Returns: 1.5 (mm)

# Example: Validate parameters before export
validation = validate_globoid_constraints(
    throat_reduction_mm=0.05,
    wheel_width_mm=3.0,  # User's request
    worm_length_mm=6.0,
    worm_params={...},
    wheel_params={...},
    assembly_params={...}
)

if not validation['valid']:
    print(f"Errors: {validation['errors']}")
    # ["Wheel width 3.0mm exceeds maximum 1.5mm"]
```

## API Reference

### `calculate_max_wheel_width(...)`

Calculates the maximum wheel width that avoids gaps at edges for globoid worms.

**Parameters:**
- `throat_reduction_mm`: Hourglass reduction (nominal - throat pitch radius)
- `worm_addendum_mm`: Worm tooth addendum
- `wheel_dedendum_mm`: Wheel tooth dedendum
- `centre_distance_mm`: Assembly centre distance
- `wheel_pitch_radius_mm`: Wheel pitch circle radius
- `throat_pitch_radius_mm`: Worm throat pitch radius
- `safety_margin_mm`: Minimum clearance (default 0.05mm)

**Returns:** `float` - Maximum wheel width in mm

**Critical for:** Preventing gaps in globoid meshing

---

### `calculate_recommended_worm_length(...)`

Calculates recommended worm length based on wheel width and engagement requirements.

**Parameters:**
- `wheel_width_mm`: Wheel face width
- `throat_curvature_radius_mm`: R_c (usually = wheel pitch radius)
- `lead_mm`: Worm lead

**Returns:** `float` - Recommended worm length in mm (rounded to 0.5mm)

**Critical for:** Proper tooth engagement

---

### `validate_globoid_constraints(...)`

Validates that all globoid parameters are compatible.

**Parameters:**
- `throat_reduction_mm`: Hourglass reduction
- `wheel_width_mm`: Requested wheel width
- `worm_length_mm`: Requested worm length
- `worm_params`: Dict of worm parameters
- `wheel_params`: Dict of wheel parameters
- `assembly_params`: Dict of assembly parameters

**Returns:** `Dict` with:
```python
{
    "valid": bool,
    "errors": List[str],
    "warnings": List[str],
    "recommendations": {
        "max_wheel_width_mm": float,
        "recommended_wheel_width_mm": float,
        "recommended_worm_length_mm": float
    }
}
```

**Critical for:** Ensuring parameters will produce valid geometry

---

### `calculate_throat_geometry(...)`

Calculates throat-related geometry for globoid worm.

**Parameters:**
- `worm_pitch_diameter_mm`: Nominal worm pitch diameter
- `wheel_pitch_diameter_mm`: Wheel pitch diameter
- `throat_reduction_mm`: Desired throat reduction

**Returns:** `Dict` with throat geometry values

---

### `SCHEMA_VERSION`

Current JSON schema version (string). Use this when exporting JSON files.

```python
from wormgear_geometry.calculations import SCHEMA_VERSION

json_data = {
    "schema_version": SCHEMA_VERSION,  # "1.0"
    "worm": {...},
    ...
}
```

---

### `validate_json_schema(data)`

Validates JSON data against the schema.

**Parameters:**
- `data`: Dict (parsed JSON)

**Returns:** `Dict` with validation results

---

### `upgrade_schema(data, target_version)`

Upgrades JSON data from older schema version to newer version.

**Parameters:**
- `data`: Dict (old schema)
- `target_version`: Target schema version (default: latest)

**Returns:** Dict (upgraded schema)

## Implementation Status

**Current:** Skeleton/stubs with API documentation

**TODO (when integrating calculator):**
1. Implement calculation functions (move logic from JavaScript)
2. Add unit tests
3. Validate against real-world examples
4. Publish to PyPI

## Files

- `globoid.py` - Globoid worm calculations
- `schema.py` - JSON schema definition and validation
- `__init__.py` - Public API exports

## Design Principles

1. **Pure calculations** - no build123d, no 3D geometry
2. **Single source of truth** - calculator imports, doesn't duplicate
3. **Well-documented** - clear API for external use
4. **Versioned** - schema versions for backward compatibility
5. **Tested** - unit tests for all calculations

## When to Implement

Implement these functions when ready to integrate the calculator project from GitHub. Until then, the stubs provide the API contract.

## Questions?

See:
- `../../ARCHITECTURE.md` - Overall design
- `../../PACKAGING.md` - Publishing guide
- `../../GLOBOID_CALCULATOR_REQUIREMENTS.md` - What calculator needs
- `../../CALCULATOR_PROMPT.md` - Detailed implementation guide
