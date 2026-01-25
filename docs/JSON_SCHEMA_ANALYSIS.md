# JSON Schema Analysis: Data Separation

## Goal
Simplify JSON Schema v1.0 to contain **only data needed for 3D model generation**, removing calculator UI hints and defaultable parameters.

## Current Problem

The schema v1.0 added many fields that are:
- ❌ Calculator UI hints (`recommended_length_mm`, `min_length_mm`, `max_width_mm`)
- ❌ Behavioral flags (`bore_auto`, `keyway_auto`) that just mean "use default calculation"
- ❌ Metadata that doesn't affect geometry

## What Geometry Classes Actually Use

### WormGeometry / GloboidWormGeometry Parameters

From `worm.py` and `globoid_worm.py`:

```python
WormGeometry(
    params: WormParams,              # ✅ Dimensional data
    assembly_params: AssemblyParams, # ✅ Hand, pressure angle
    length: float,                   # ✅ Actual length to generate
    sections_per_turn: int,          # ✅ Quality/smoothness
    bore: BoreFeature,               # ✅ Bore specification
    keyway: KeywayFeature,           # ✅ Keyway specification
    ddcut: DDCutFeature,             # ✅ DD-cut specification
    set_screw: SetScrewFeature,      # ✅ Set screw specification
    profile: ProfileType             # ✅ Tooth profile (ZA/ZK/ZI)
)

# GloboidWormGeometry adds:
    wheel_pitch_diameter: float      # ✅ For throat calculation
```

### WheelGeometry / VirtualHobbingWheelGeometry Parameters

From `wheel.py` and `virtual_hobbing.py`:

```python
WheelGeometry(
    params: WheelParams,              # ✅ Dimensional data
    worm_params: WormParams,          # ✅ For meshing calculations
    assembly_params: AssemblyParams,  # ✅ Hand, ratio
    face_width: float,                # ✅ Actual width to generate
    throated: bool,                   # ✅ Wheel style
    bore: BoreFeature,                # ✅ Bore specification
    keyway: KeywayFeature,            # ✅ Keyway specification
    ddcut: DDCutFeature,              # ✅ DD-cut specification
    set_screw: SetScrewFeature,       # ✅ Set screw specification
    hub: HubFeature,                  # ✅ Hub specification
    profile: ProfileType              # ✅ Tooth profile (ZA/ZK/ZI)
)

# VirtualHobbingWheelGeometry adds:
    hobbing_steps: int                # ✅ Virtual hobbing accuracy
    hob_geometry: Part                # ✅ Optional actual worm as hob
```

---

## Analysis: Schema v1.0 Fields

### WormParams - Schema v1.0 Additions

| Field | Needed? | Why / Alternative |
|-------|---------|-------------------|
| `type` | ✅ **YES** | Determines which geometry class (WormGeometry vs GloboidWormGeometry) |
| `throat_reduction_mm` | ⚠️ **MAYBE** | Only for globoid. Might be calculable from other params? |
| `throat_curvature_radius_mm` | ⚠️ **MAYBE** | Only for globoid. Often equals wheel pitch radius |
| `recommended_length_mm` | ❌ **NO** | Calculator UI hint - not used by geometry |
| `min_length_mm` | ❌ **NO** | Calculator UI hint - not used by geometry |
| `length_mm` | ✅ **YES** | Actual length to generate (alternative to CLI `--worm-length`) |
| `bore_diameter_mm` | ✅ **YES** | Bore feature spec (alternative to CLI `--worm-bore`) |
| `bore_auto` | ❌ **NO** | Just means "calculate default" - CLI already does this |
| `keyway_standard` | ❌ **NO** | Always DIN6885 or none - implied by presence of bore |
| `keyway_auto` | ❌ **NO** | Just means "add keyway with bore" - CLI default behavior |
| `set_screw_diameter_mm` | ✅ **YES** | Set screw spec (but could be in separate features section) |
| `set_screw_count` | ✅ **YES** | Set screw spec (but could be in separate features section) |

**Recommendation for WormParams:**
```python
@dataclass
class WormParams:
    # CORE DIMENSIONS (already exist, keep)
    module_mm: float
    num_starts: int
    pitch_diameter_mm: float
    tip_diameter_mm: float
    root_diameter_mm: float
    lead_mm: float
    lead_angle_deg: float
    addendum_mm: float
    dedendum_mm: float
    thread_thickness_mm: float
    hand: str
    profile_shift: float = 0.0

    # WORM TYPE (new, essential)
    type: Optional[str] = None  # "cylindrical" or "globoid"

    # GLOBOID-SPECIFIC (new, optional, for globoid only)
    throat_reduction_mm: Optional[float] = None
    throat_curvature_radius_mm: Optional[float] = None

    # GEOMETRY PARAMETERS (new, optional - can override CLI)
    length_mm: Optional[float] = None  # If None, use CLI default

    # REMOVE: recommended_length_mm, min_length_mm, bore_auto, keyway_auto
    # MOVE TO FEATURES SECTION: bore_diameter_mm, set_screw_*
```

### WheelParams - Schema v1.0 Additions

| Field | Needed? | Why / Alternative |
|-------|---------|-------------------|
| `recommended_width_mm` | ❌ **NO** | Calculator UI hint - not used by geometry |
| `max_width_mm` | ❌ **NO** | Calculator UI hint/constraint - not geometry data |
| `min_width_mm` | ❌ **NO** | Calculator UI hint/constraint - not geometry data |
| `width_mm` | ✅ **YES** | Actual width to generate (alternative to CLI `--wheel-width`) |
| `bore_diameter_mm` | ✅ **YES** | Bore feature spec (alternative to CLI `--wheel-bore`) |
| `bore_auto` | ❌ **NO** | Just means "calculate default" - CLI already does this |
| `keyway_standard` | ❌ **NO** | Always DIN6885 or none - implied by presence of bore |
| `keyway_auto` | ❌ **NO** | Just means "add keyway with bore" - CLI default behavior |
| `set_screw_diameter_mm` | ✅ **YES** | Set screw spec (but could be in features section) |
| `set_screw_count` | ✅ **YES** | Set screw spec (but could be in features section) |
| `hub_type` | ✅ **YES** | Hub feature spec (but could be in features section) |
| `hub_length_mm` | ✅ **YES** | Hub feature spec (but could be in features section) |
| `hub_flange_diameter_mm` | ✅ **YES** | Hub feature spec (but could be in features section) |
| `hub_bolt_holes` | ✅ **YES** | Hub feature spec (but could be in features section) |

**Recommendation for WheelParams:**
```python
@dataclass
class WheelParams:
    # CORE DIMENSIONS (already exist, keep)
    module_mm: float
    num_teeth: int
    pitch_diameter_mm: float
    tip_diameter_mm: float
    root_diameter_mm: float
    throat_diameter_mm: float
    helix_angle_deg: float
    addendum_mm: float
    dedendum_mm: float
    profile_shift: float = 0.0

    # GEOMETRY PARAMETERS (new, optional - can override CLI)
    width_mm: Optional[float] = None  # If None, use CLI default

    # REMOVE: recommended_width_mm, max_width_mm, min_width_mm
    # REMOVE: bore_auto, keyway_auto
    # MOVE TO FEATURES SECTION: bore_diameter_mm, set_screw_*, hub_*
```

### ManufacturingParams - Schema v1.0

Current schema v1.0:
```python
@dataclass
class ManufacturingParams:
    profile: str = "ZA"                    # ✅ YES - tooth profile type
    virtual_hobbing: bool = False          # ✅ YES - use virtual hobbing
    hobbing_steps: int = 18                # ✅ YES - virtual hobbing quality
    throated_wheel: bool = False           # ✅ YES - wheel style
    sections_per_turn: int = 36            # ✅ YES - worm smoothness
```

**Recommendation:** Keep as-is. All fields are geometry generation parameters.

---

## Proposed Simplified Schema

### Option A: Keep Features in Worm/Wheel Params (Simple)

Features (bore, keyway, set screw, hub) stay in WormParams/WheelParams:

```json
{
  "schema_version": "1.0",
  "worm": {
    // Core dimensions (existing fields)
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

    // NEW: Worm type
    "type": "globoid",  // or "cylindrical"

    // NEW: Globoid-specific (optional, only if type="globoid")
    "throat_reduction_mm": 0.05,
    "throat_curvature_radius_mm": 3.0,

    // NEW: Geometry overrides (optional)
    "length_mm": 6.0,  // If omitted, CLI uses default

    // NEW: Features (optional)
    "bore_diameter_mm": 2.0,  // If omitted, no bore OR use CLI default
    "set_screw_size": "M2",
    "set_screw_count": 1
  },

  "wheel": {
    // Core dimensions (existing fields)
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

    // NEW: Geometry overrides (optional)
    "width_mm": 1.5,  // If omitted, auto-calculated

    // NEW: Features (optional)
    "bore_diameter_mm": 2.0,
    "set_screw_size": "M2",
    "set_screw_count": 1,
    "hub_type": "flush",  // "flush", "extended", "flanged"
    "hub_length_mm": 5.0,
    "hub_flange_diameter_mm": 8.0,
    "hub_bolt_holes": 4
  },

  "assembly": {
    "centre_distance_mm": 6.35,
    "pressure_angle_deg": 20.0,
    "backlash_mm": 0.02,
    "hand": "right",
    "ratio": 15
  },

  "manufacturing": {
    "profile": "ZA",  // "ZA", "ZK", "ZI"
    "virtual_hobbing": false,
    "hobbing_steps": 18,
    "throated_wheel": false,
    "sections_per_turn": 36
  }
}
```

### Option B: Separate Features Section (Cleaner Separation)

Extract all features to separate section:

```json
{
  "schema_version": "1.0",
  "worm": {
    // Only dimensional data
    "module_mm": 0.4,
    "num_starts": 1,
    "pitch_diameter_mm": 6.8,
    // ... all existing dimensional fields
    "type": "globoid",
    "throat_reduction_mm": 0.05,
    "throat_curvature_radius_mm": 3.0,
    "length_mm": 6.0  // Geometry override
  },

  "wheel": {
    // Only dimensional data
    "module_mm": 0.4,
    "num_teeth": 15,
    // ... all existing dimensional fields
    "width_mm": 1.5  // Geometry override
  },

  "assembly": {
    "centre_distance_mm": 6.35,
    "pressure_angle_deg": 20.0,
    "backlash_mm": 0.02,
    "hand": "right",
    "ratio": 15
  },

  "features": {  // NEW SECTION
    "worm": {
      "bore_diameter_mm": 2.0,
      "keyway": true,  // or "DIN6885" or null
      "set_screw": {
        "size": "M2",
        "count": 1
      }
    },
    "wheel": {
      "bore_diameter_mm": 2.0,
      "keyway": true,
      "set_screw": {
        "size": "M2",
        "count": 1
      },
      "hub": {
        "type": "flush",
        "length_mm": 5.0,
        "flange_diameter_mm": 8.0,
        "bolt_holes": 4
      }
    }
  },

  "manufacturing": {
    "profile": "ZA",
    "virtual_hobbing": false,
    "hobbing_steps": 18,
    "throated_wheel": false,
    "sections_per_turn": 36
  }
}
```

---

## Fields to REMOVE from Schema v1.0

### From WormParams:
- ❌ `recommended_length_mm` - calculator UI hint
- ❌ `min_length_mm` - calculator UI hint
- ❌ `bore_auto` - just means "use default calculation"
- ❌ `keyway_standard` - implied (always DIN6885 or none)
- ❌ `keyway_auto` - just means "add keyway with bore"

### From WheelParams:
- ❌ `recommended_width_mm` - calculator UI hint
- ❌ `max_width_mm` - calculator constraint, not geometry data
- ❌ `min_width_mm` - calculator constraint, not geometry data
- ❌ `bore_auto` - just means "use default calculation"
- ❌ `keyway_standard` - implied (always DIN6885 or none)
- ❌ `keyway_auto` - just means "add keyway with bore"

---

## What Belongs in JSON vs CLI

### MUST be in JSON (calculator's job):
- ✅ All dimensional data (modules, diameters, angles)
- ✅ Worm type (cylindrical vs globoid)
- ✅ Globoid-specific parameters (if globoid)
- ✅ Tooth profile type (ZA/ZK/ZI) - manufacturing method
- ✅ Virtual hobbing settings (if calculator recommends it)

### OPTIONAL in JSON (can override CLI defaults):
- ⚠️ `worm.length_mm` - if specified, use it; else CLI default
- ⚠️ `wheel.width_mm` - if specified, use it; else auto-calculate
- ⚠️ Feature specifications (bore, keyway, set screw, hub)
- ⚠️ Quality settings (`sections_per_turn`, `hobbing_steps`)

### SHOULD stay CLI-only (user preferences):
- 🔧 `--view` - viewing preference
- 🔧 `--no-save` - output preference
- 🔧 `--output-dir` - output location
- 🔧 `--worm-only` / `--wheel-only` - generation selection
- 🔧 `--mesh-aligned` - viewer rotation
- 🔧 `--save-json` - export augmented JSON

### Can be EITHER JSON or CLI (CLI overrides):
Priority: **CLI flags > JSON values > Defaults**

- 🔀 `--worm-length` overrides `worm.length_mm`
- 🔀 `--wheel-width` overrides `wheel.width_mm`
- 🔀 `--worm-bore` overrides `worm.bore_diameter_mm`
- 🔀 `--profile` overrides `manufacturing.profile`
- 🔀 `--sections` overrides `manufacturing.sections_per_turn`

---

## Recommended Changes

### Immediate (Simplify Schema v1.0):

1. **Remove "hint" fields** from WormParams/WheelParams:
   - `recommended_length_mm`, `min_length_mm`
   - `recommended_width_mm`, `max_width_mm`, `min_width_mm`
   - `bore_auto`, `keyway_auto`, `keyway_standard`

2. **Keep essential geometry data**:
   - `type`, `length_mm`, `width_mm`
   - `throat_reduction_mm`, `throat_curvature_radius_mm` (globoid)
   - Feature specs (bore, set screw, hub)

3. **Decide on features organization**:
   - **Option A (simple)**: Keep in worm/wheel params
   - **Option B (clean)**: Separate `features` section

### Future (Schema v2.0):

Consider restructuring as:
```json
{
  "schema_version": "2.0",
  "dimensions": {
    "worm": { /* pure dimensional data */ },
    "wheel": { /* pure dimensional data */ },
    "assembly": { /* assembly data */ }
  },
  "geometry": {
    "worm_type": "globoid",
    "worm_length_mm": 6.0,
    "wheel_width_mm": 1.5,
    "throat_reduction_mm": 0.05
  },
  "features": {
    "worm": { /* bore, keyway, set screw */ },
    "wheel": { /* bore, keyway, set screw, hub */ }
  },
  "manufacturing": {
    "profile": "ZA",
    "virtual_hobbing": false,
    "sections_per_turn": 36
  }
}
```

---

## Summary

**REMOVE from schema v1.0:**
- All `recommended_*`, `min_*`, `max_*` fields (UI hints)
- All `*_auto` fields (just mean "use defaults")
- `keyway_standard` (always DIN6885 or none, implied)

**KEEP in schema v1.0:**
- All dimensional data (existing)
- `worm.type` (cylindrical/globoid)
- `worm.length_mm`, `wheel.width_mm` (geometry overrides)
- Globoid parameters
- Feature specifications (bore, set screw, hub)
- Manufacturing parameters (profile, virtual_hobbing, etc.)

**PRINCIPLE:**
> JSON should contain **actual values to use**, not **hints about how to calculate them**.
> The calculator does calculations; JSON stores results.
