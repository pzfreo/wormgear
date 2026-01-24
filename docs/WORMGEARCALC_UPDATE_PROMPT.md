# Prompt: Update wormgearcalc for Compatibility with worm-gear-3d

## Context

You are working on **wormgearcalc** (Tool 1), a worm gear calculator that outputs JSON parameters for the 3D geometry generator **worm-gear-3d** (Tool 2).

**Repository**: https://github.com/pzfreo/wormgearcalc

The geometry generator (worm-gear-3d) has been significantly enhanced with new features. The calculator needs to be updated to output parameters that take full advantage of these capabilities.

## Current State of wormgearcalc

### Architecture
- Pure Python + Pyodide for browser deployment
- Zero external dependencies in core (stdlib only)
- Web app at `https://pzfreo.github.io/wormgearcalc/`

### Key Files
- `src/wormcalc/core.py` - Calculations, dataclasses
- `src/wormcalc/output.py` - JSON/Markdown formatters
- `src/wormcalc/validation.py` - Engineering rules
- `src/wormcalc/cli.py` - Click CLI
- `web/` - Browser app (copies of core files)

### Current JSON Output Format
```json
{
  "worm": {
    "module_mm": 2.0,
    "num_starts": 1,
    "pitch_diameter_mm": 16.29,
    "tip_diameter_mm": 20.29,
    "root_diameter_mm": 11.29,
    "lead_mm": 6.283,
    "axial_pitch_mm": 6.283,
    "lead_angle_deg": 7.0,
    "addendum_mm": 2.0,
    "dedendum_mm": 2.5,
    "thread_thickness_mm": 3.14
  },
  "wheel": {
    "module_mm": 2.0,
    "num_teeth": 30,
    "pitch_diameter_mm": 60.0,
    "tip_diameter_mm": 64.0,
    "root_diameter_mm": 55.0,
    "throat_diameter_mm": 62.0,
    "helix_angle_deg": 83.0,
    "addendum_mm": 2.0,
    "dedendum_mm": 2.5
  },
  "assembly": {
    "centre_distance_mm": 38.14,
    "ratio": 30,
    "pressure_angle_deg": 20.0,
    "backlash_mm": 0.05,
    "hand": "right"
  },
  "performance": {
    "efficiency_estimate": 0.75,
    "self_locking": true
  }
}
```

## Required Updates

### 1. Add Profile Type (DIN 3975)

The geometry generator now supports two tooth profile types per DIN 3975:

| Profile | Flanks | Best For | Description |
|---------|--------|----------|-------------|
| `ZA` | Straight trapezoidal | CNC machining | Standard DIN 3975 Type A |
| `ZK` | Slightly convex | 3D printing | Better for FDM layer adhesion |

**Implementation**:
- Add `profile` field to assembly section (default: "ZA")
- Add UI selector in web app
- Add CLI option `--profile`

**JSON addition**:
```json
"assembly": {
  ...
  "profile": "ZA"
}
```

### 2. Add Manufacturing Section

The geometry generator accepts manufacturing parameters to control output geometry. The calculator should provide sensible defaults.

**New JSON section**:
```json
"manufacturing": {
  "worm_type": "cylindrical",
  "worm_length": 40.0,
  "wheel_width": null,
  "wheel_throated": false,
  "profile": "ZA"
}
```

**Fields**:
- `worm_type`: "cylindrical" (default) or "globoid"
- `worm_length`: Suggested worm length in mm (auto-calculate as ~4× lead for cylindrical, ~3× lead for globoid)
- `wheel_width`: Suggested wheel face width in mm (auto-calculate as ~10× module, or null for auto)
- `wheel_throated`: true for hobbed/throated teeth (better contact), false for helical (simpler)
- `profile`: "ZA" or "ZK" (mirrors assembly.profile for convenience)

### 3. Add Globoid Worm Support

The geometry generator now supports globoid (hourglass-shaped) worms. These provide better contact with the wheel.

**Globoid-specific parameters needed**:
- `throat_pitch_radius`: Pitch radius at the throat (waist) of the globoid
- `throat_tip_radius`: Outer radius at throat
- `throat_root_radius`: Inner radius at throat

**Calculation for globoid**:
```python
# The throat radius equals the pitch radius that would contact the wheel
# at the correct center distance
wheel_pitch_radius = wheel_pitch_diameter / 2
throat_pitch_radius = centre_distance - wheel_pitch_radius
throat_tip_radius = throat_pitch_radius + addendum
throat_root_radius = throat_pitch_radius - dedendum
```

**When worm_type="globoid"**:
- Add `throat_pitch_radius_mm`, `throat_tip_radius_mm`, `throat_root_radius_mm` to worm section
- Validation: warn if throat is very aggressive (>20% reduction from pitch radius)

### 4. Add Wheel Type Indicator

The geometry generator supports two wheel tooth types:

| Type | Flag | Description |
|------|------|-------------|
| Helical | `wheel_throated: false` | Flat-bottomed trapezoidal teeth, simpler geometry |
| Hobbed/Throated | `wheel_throated: true` | Teeth with depth varying to match worm curvature |

**Recommendation logic** for UI:
- Suggest `wheel_throated: true` for globoid worms (they need matching wheel)
- Default to `wheel_throated: false` for cylindrical worms (simpler)
- Let user override in advanced settings

### 5. Update Throat Diameter Calculation

Current calculation in `calculate_wheel()`:
```python
throat_diameter = pitch_diameter + module  # Simplified
```

More accurate formula:
```python
# Throat diameter for throated wheel should allow proper engagement
# with worm at pitch diameter
throat_diameter = pitch_diameter + 2 * addendum * 0.9  # ~90% of full addendum
```

Or optionally, just document that this is a reference value and the geometry generator calculates the actual throat.

### 6. Web App Updates

Add new UI controls:
- **Profile selector**: Radio buttons or dropdown for ZA/ZK
- **Worm type selector**: Dropdown for cylindrical/globoid
- **Wheel type selector**: Checkbox for "Throated teeth (better contact)"
- **Manufacturing section** in output panel showing suggested dimensions

### 7. CLI Updates

Add new options to relevant commands:
```bash
wormcalc envelope --worm-od 20 --wheel-od 65 --ratio 30 \
  --profile ZK \
  --worm-type globoid \
  --throated
```

## Updated JSON Output Format (Complete)

```json
{
  "worm": {
    "module_mm": 2.0,
    "num_starts": 1,
    "pitch_diameter_mm": 16.29,
    "tip_diameter_mm": 20.29,
    "root_diameter_mm": 11.29,
    "lead_mm": 6.283,
    "axial_pitch_mm": 6.283,
    "lead_angle_deg": 7.0,
    "addendum_mm": 2.0,
    "dedendum_mm": 2.5,
    "thread_thickness_mm": 3.14,
    "throat_pitch_radius_mm": 14.0,
    "throat_tip_radius_mm": 16.0,
    "throat_root_radius_mm": 11.5
  },
  "wheel": {
    "module_mm": 2.0,
    "num_teeth": 30,
    "pitch_diameter_mm": 60.0,
    "tip_diameter_mm": 64.0,
    "root_diameter_mm": 55.0,
    "throat_diameter_mm": 62.0,
    "helix_angle_deg": 83.0,
    "addendum_mm": 2.0,
    "dedendum_mm": 2.5,
    "profile_shift": 0.0
  },
  "assembly": {
    "centre_distance_mm": 38.14,
    "ratio": 30,
    "pressure_angle_deg": 20.0,
    "backlash_mm": 0.05,
    "hand": "right",
    "profile": "ZA"
  },
  "performance": {
    "efficiency_estimate": 0.75,
    "self_locking": true
  },
  "manufacturing": {
    "worm_type": "cylindrical",
    "worm_length": 25.1,
    "wheel_width": 20.0,
    "wheel_throated": false,
    "profile": "ZA"
  },
  "validation": {
    "valid": true,
    "messages": []
  }
}
```

**Notes**:
- `throat_pitch_radius_mm` etc. only present when `worm_type: "globoid"`
- `manufacturing` section is new
- `assembly.profile` is new
- `wheel.profile_shift` already exists but ensure it's always included

## Implementation Order

1. **core.py**: Add `worm_type` to design functions, add globoid calculations
2. **output.py**: Update `design_to_dict()` to include new fields
3. **validation.py**: Add validation for globoid parameters
4. **cli.py**: Add new command options
5. **web/app.js**: Add UI controls for new options
6. **web/index.html**: Add HTML for new controls
7. **tests/**: Update tests for new functionality
8. **web/wormcalc/**: Copy updated Python files

## Validation Rules to Add

1. **Globoid throat validation**: Warn if `throat_pitch_radius < 0.8 * pitch_radius` (aggressive reduction)
2. **Profile validation**: Error if profile not in ["ZA", "ZK"]
3. **Worm type validation**: Error if worm_type not in ["cylindrical", "globoid"]
4. **Combination warning**: Info message if globoid worm with non-throated wheel

## Testing Checklist

- [ ] Cylindrical worm with ZA profile generates valid JSON
- [ ] Cylindrical worm with ZK profile generates valid JSON
- [ ] Globoid worm includes throat radius fields
- [ ] Manufacturing section present with sensible defaults
- [ ] Web app shows new controls and options
- [ ] CLI accepts new options
- [ ] Generated JSON loads successfully in worm-gear-3d
- [ ] Round-trip test: calc → geometry → STEP file works

## Backward Compatibility

The geometry generator (worm-gear-3d) already handles missing fields gracefully:
- Missing `profile` → defaults to "ZA"
- Missing `manufacturing` section → uses internal defaults
- Missing throat radius fields → calculates from centre_distance

So updates can be incremental without breaking existing JSON files.

## Reference: worm-gear-3d io.py Expectations

The geometry generator expects this structure (from `src/wormgear_geometry/io.py`):

```python
@dataclass
class ManufacturingParams:
    worm_type: str = "cylindrical"  # "cylindrical" or "globoid"
    worm_length: float = 40.0
    wheel_width: Optional[float] = None
    wheel_throated: bool = False
    profile: str = "ZA"  # "ZA" or "ZK" per DIN 3975
```

Ensure JSON output matches these field names exactly.

---

## Summary

Update wormgearcalc to:
1. Add `profile` field (ZA/ZK) for DIN 3975 tooth profiles
2. Add `manufacturing` section with worm_type, dimensions, and options
3. Support globoid worm calculations with throat radius parameters
4. Add wheel_throated option for hobbed vs helical teeth
5. Update web UI and CLI with new controls
6. Maintain backward compatibility with existing JSON files

The goal is complete alignment between the calculator (Tool 1) and geometry generator (Tool 2) so users get a seamless workflow from design to 3D model.
