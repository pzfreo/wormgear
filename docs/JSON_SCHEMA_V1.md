# JSON Schema v1.0 - Complete Parameter Specification

## Overview

JSON Schema v1.0 is the contract between the calculator (wormgearcalc) and the 3D geometry generator (wormgear-geometry).

**Key principle**: The JSON file should contain **ALL** parameters needed to generate the geometry. No CLI flags required (though they can override).

## Why This Matters

### Before (Incomplete):
```bash
# Calculator exports basic parameters
wormgearcalc -> design.json  # Only worm/wheel/assembly dimensions

# User must manually specify everything else via CLI
wormgear-geometry design.json \
  --profile ZK \
  --worm-length 6 \
  --wheel-width 1.5 \
  --globoid \
  --virtual-hobbing \
  --hobbing-steps 18 \
  --worm-bore auto \
  --wheel-bore auto
```

### After (Complete):
```bash
# Calculator exports COMPLETE design specification
wormgearcalc -> design.json  # Includes ALL parameters

# Just run it - no flags needed
wormgear-geometry design.json
```

## Schema Structure

### Required Sections
```json
{
  "schema_version": "1.0",
  "worm": { ... },
  "wheel": { ... },
  "assembly": { ... }
}
```

### Optional Sections
```json
{
  "manufacturing": { ... },
  "validation": { ... }
}
```

## Worm Section

### Required Fields (Dimensions)
```json
{
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
  "hand": "right"
}
```

### Optional Fields (Geometry & Features)
```json
{
  // Worm type
  "type": "cylindrical",  // or "globoid"
  "profile_shift": 0.0,

  // Globoid-specific (only if type="globoid")
  "throat_reduction_mm": 0.05,
  "throat_curvature_radius_mm": 3.0,

  // Length recommendations from calculator
  "recommended_length_mm": 6.0,
  "min_length_mm": 5.0,

  // Actual geometry to generate
  "length_mm": 6.0,  // If omitted, uses recommended_length_mm

  // Bore and keyway features
  "bore_diameter_mm": null,  // null for solid, or specific diameter
  "bore_auto": true,  // Auto-calculate bore size (~25% of pitch diameter)
  "keyway_standard": "DIN6885",  // "DIN6885" or "none"
  "keyway_auto": true,  // Auto-size keyway to match bore

  // Set screws (optional)
  "set_screw_diameter_mm": null,
  "set_screw_count": 0
}
```

## Wheel Section

### Required Fields (Dimensions)
```json
{
  "module_mm": 0.4,
  "num_teeth": 15,
  "pitch_diameter_mm": 6.0,
  "tip_diameter_mm": 6.8,
  "root_diameter_mm": 5.1,
  "throat_diameter_mm": 6.4,
  "helix_angle_deg": 86.33,
  "addendum_mm": 0.4,
  "dedendum_mm": 0.45
}
```

### Optional Fields (Geometry & Features)
```json
{
  "profile_shift": 0.0,

  // Width recommendations from calculator
  "recommended_width_mm": 1.5,
  "max_width_mm": 1.5,  // Optional constraint from geometry
  "min_width_mm": 0.8,  // Optional constraint from strength

  // Actual geometry to generate
  "width_mm": 1.5,  // If omitted, auto-calculates based on ratio

  // Bore and keyway features
  "bore_diameter_mm": null,
  "bore_auto": true,
  "keyway_standard": "DIN6885",
  "keyway_auto": true,

  // Set screws (optional)
  "set_screw_diameter_mm": null,
  "set_screw_count": 0,

  // Hub features (wheel only)
  "hub_type": "flush",  // "flush", "extended", "flanged", or "none"
  "hub_length_mm": null,  // For "extended" or "flanged"
  "hub_flange_diameter_mm": null,  // For "flanged" only
  "hub_bolt_holes": 0  // Number of bolt holes (flanged only)
}
```

## Assembly Section

### Required Fields
```json
{
  "centre_distance_mm": 6.1,
  "pressure_angle_deg": 20.0,
  "backlash_mm": 0.02,
  "hand": "right",
  "ratio": 15
}
```

### Optional Fields
```json
{
  "efficiency_percent": 85.0,
  "self_locking": false
}
```

## Manufacturing Section (Optional)

This section specifies how to generate the geometry.

```json
{
  "manufacturing": {
    // Tooth profile per DIN 3975
    "profile": "ZA",  // "ZA" (straight), "ZK" (circular arc), "ZI" (involute)

    // Virtual hobbing simulation
    "virtual_hobbing": false,  // true to simulate hobbing process
    "hobbing_steps": 18,  // Number of hobbing rotation steps (if enabled)

    // Wheel style
    "throated_wheel": false,  // true for throated/hobbed wheel teeth

    // Quality settings
    "sections_per_turn": 36  // Loft sections per helix turn (smoothness)
  }
}
```

## Validation Section (Optional)

Calculator can include validation results:

```json
{
  "validation": {
    "valid": true,
    "errors": [],
    "warnings": [
      "Throat reduction 0mm - nearly cylindrical"
    ],
    "clearance_mm": 0.05  // centre_distance - worm_tip - wheel_root
  }
}
```

## Complete Example - Globoid Worm with Features

```json
{
  "schema_version": "1.0",
  "_generator": "wormgearcalc v2.0.0",
  "_created": "2026-01-24T10:30:00",
  "_note": "7mm globoid worm gear - fully specified",

  "worm": {
    "type": "globoid",
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

    "throat_reduction_mm": 0.05,
    "throat_curvature_radius_mm": 3.0,

    "recommended_length_mm": 6.0,
    "min_length_mm": 5.0,
    "length_mm": 6.0,

    "bore_diameter_mm": null,
    "bore_auto": true,
    "keyway_standard": "DIN6885",
    "keyway_auto": true,
    "set_screw_diameter_mm": null,
    "set_screw_count": 0
  },

  "wheel": {
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

    "recommended_width_mm": 1.5,
    "max_width_mm": null,
    "min_width_mm": 0.8,
    "width_mm": 1.5,

    "bore_diameter_mm": null,
    "bore_auto": true,
    "keyway_standard": "DIN6885",
    "keyway_auto": true,
    "set_screw_diameter_mm": null,
    "set_screw_count": 0,

    "hub_type": "flush",
    "hub_length_mm": null,
    "hub_flange_diameter_mm": null,
    "hub_bolt_holes": 0
  },

  "assembly": {
    "centre_distance_mm": 6.35,
    "pressure_angle_deg": 20.0,
    "backlash_mm": 0.02,
    "hand": "right",
    "ratio": 15,
    "efficiency_percent": null,
    "self_locking": false
  },

  "manufacturing": {
    "profile": "ZA",
    "virtual_hobbing": true,
    "hobbing_steps": 18,
    "throated_wheel": false,
    "sections_per_turn": 36
  },

  "validation": {
    "valid": true,
    "errors": [],
    "warnings": [
      "Throat reduction 0.05mm - minimal globoid benefit"
    ],
    "clearance_mm": 0.05
  }
}
```

## Migration from Old Format

### Old Format (Pre-v1.0)
Only had basic dimensions, no manufacturing parameters:

```json
{
  "worm": {
    "module_mm": 0.4,
    "pitch_diameter_mm": 6.2,
    // ... basic dimensions only
  },
  "wheel": { /* ... */ },
  "assembly": { /* ... */ }
}
```

### New Format (v1.0)
Includes everything needed for generation:

```json
{
  "schema_version": "1.0",  // NEW: Version tracking
  "worm": {
    "module_mm": 0.4,
    "pitch_diameter_mm": 6.2,
    // ... basic dimensions
    "type": "globoid",  // NEW: Worm type
    "length_mm": 6.0,  // NEW: Actual length
    "bore_auto": true,  // NEW: Feature specs
    // ...
  },
  "wheel": { /* ... with new fields */ },
  "assembly": { /* ... */ },
  "manufacturing": {  // NEW: Manufacturing section
    "profile": "ZA",
    "virtual_hobbing": false,
    // ...
  }
}
```

## CLI Override Behavior

Even with complete JSON, CLI flags can override:

```bash
# JSON specifies profile="ZA", but override to ZK
wormgear-geometry design.json --profile ZK

# JSON specifies length_mm=6.0, but override to 8.0
wormgear-geometry design.json --worm-length 8.0

# JSON specifies virtual_hobbing=false, but enable it
wormgear-geometry design.json --virtual-hobbing
```

**Priority**: CLI flags > JSON values > Defaults

## Backward Compatibility

The loader handles both old and new formats:

1. **No `schema_version`**: Assumes pre-v1.0, loads basic fields only
2. **`schema_version: "1.0"`**: Loads all new optional fields
3. **Future versions**: `upgrade_schema()` will handle migrations

## Implementation Reference

- **Schema definition**: `src/wormgear_geometry/calculations/schema.py`
- **JSON loader**: `src/wormgear_geometry/io.py`
- **Validation**: `validate_json_schema()` (TODO: implement)
- **Schema upgrade**: `upgrade_schema()` (TODO: implement for v1.1+)

## Calculator Implementation Checklist

When updating the calculator to export schema v1.0:

- [ ] Add `schema_version: "1.0"` to exports
- [ ] Add `worm.type` ("cylindrical" or "globoid")
- [ ] Add `worm.length_mm` recommendation
- [ ] Add `worm.bore_auto` and `worm.keyway_auto` (usually `true`)
- [ ] Add `wheel.width_mm` recommendation
- [ ] Add `wheel.bore_auto` and `wheel.keyway_auto` (usually `true`)
- [ ] Add `manufacturing.profile` (default "ZA")
- [ ] Add `manufacturing.virtual_hobbing` (default `false`)
- [ ] Add `validation.clearance_mm` check
- [ ] Remove complex wheel width calculations (see CALCULATOR_CORRECTIONS.md)
- [ ] Test round-trip: export JSON → load in wormgear-geometry → verify

## Benefits

1. **Single source of truth**: Calculator fully specifies the design
2. **Reproducibility**: Same JSON always produces same geometry
3. **Portability**: Share complete designs as single file
4. **Version tracking**: Schema version enables future migrations
5. **Validation**: Calculator can validate before export
6. **Simplicity**: No need to remember CLI flags

---

**Next step**: Update wormgearcalc to export schema v1.0 format with all fields.
