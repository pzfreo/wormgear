# Wormgear - Architecture Documentation

**Version**: 1.0.0-alpha
**Last Updated**: 2026-01-25

## Overview

Wormgear is a unified Python package for worm gear design, combining engineering calculations with 3D geometry generation for CNC manufacturing.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     wormgear Package                         │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              Layer 1: Core (Geometry)                   │ │
│  │  • WormGeometry, WheelGeometry                         │ │
│  │  • GloboidWormGeometry                                 │ │
│  │  • VirtualHobbingWheelGeometry                         │ │
│  │  • Features (BoreFeature, KeywayFeature, etc.)         │ │
│  │  Pure geometry generation using build123d              │ │
│  └────────────────────────────────────────────────────────┘ │
│                           ▲                                  │
│                           │                                  │
│  ┌────────────────────────┼──────────────────────────────┐ │
│  │         Layer 2a: Calculator    Layer 2b: IO          │ │
│  │  • design_from_module()         • load_design_json()  │ │
│  │  • design_from_wheel()          • save_design_json()  │ │
│  │  • design_from_centre_distance  • JSON Schema v1.0    │ │
│  │  • validate_design()            • WormParams,         │ │
│  │  Engineering calculations         WheelParams, etc.   │ │
│  └────────────────────────┬──────────────────────────────┘ │
│                           │                                  │
│  ┌────────────────────────┴──────────────────────────────┐ │
│  │              Layer 3: CLI                              │ │
│  │  • wormgear-geometry (STEP file generation)           │ │
│  │  Command-line interface                               │ │
│  └────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    Web Calculator                            │
│  • Runs in browser using Pyodide                            │
│  • Same Python code as package                              │
│  • Exports JSON Schema v1.0                                 │
└───────────────────┬─────────────────────────────────────────┘
                    │ JSON
                    ▼
┌─────────────────────────────────────────────────────────────┐
│                    wormgear Package                          │
│  load_design_json() → Geometry Generation → STEP Export     │
└─────────────────────────────────────────────────────────────┘
```

## Layer Descriptions

### Layer 1: Core (Geometry)

**Purpose**: Pure 3D geometry generation using build123d

**Location**: `src/wormgear/core/`

**Components**:
- `worm.py` - Cylindrical worm threads (helical sweep)
- `wheel.py` - Helical wheel teeth
- `globoid_worm.py` - Hourglass-shaped worm for better contact
- `virtual_hobbing.py` - Simulated hobbing for accurate wheel teeth
- `features.py` - Bores, keyways, DD-cuts, set screws, hubs

**Key Design Decisions**:
- **No JSON dependencies** - Accepts dataclass parameters only
- **Exact geometry** - No approximations, CNC-ready
- **Watertight solids** - Valid STEP export guaranteed
- **Feature-rich** - Manufacturing features integrated

**API Example**:
```python
from wormgear.core import WormGeometry, BoreFeature, KeywayFeature
from wormgear.io import WormParams, AssemblyParams

worm = WormGeometry(
    params=WormParams(...),
    assembly_params=AssemblyParams(...),
    length=40.0,
    bore=BoreFeature(diameter=8.0),
    keyway=KeywayFeature()
)
part = worm.build()
part.export_step("worm.step")
```

### Layer 2a: Calculator

**Purpose**: Engineering calculations based on DIN 3975/DIN 3996

**Location**: `src/wormgear/calculator/`

**Components**:
- `core.py` - Calculation functions (design_from_module, etc.)
- `validation.py` - Engineering validation rules

**Key Design Decisions**:
- **Standards-based** - DIN 3975, ISO 54
- **Pure math** - No external dependencies beyond stdlib
- **Validation included** - Returns errors/warnings/infos
- **Field naming** - Consistent with geometry layer (_mm, _deg suffixes)

**API Example**:
```python
from wormgear.calculator import calculate_design_from_module, validate_design

design = calculate_design_from_module(module=2.0, ratio=30)
validation = validate_design(design)

if validation.valid:
    print(f"✓ Design valid, efficiency: {design.assembly.efficiency_percent}%")
```

### Layer 2b: IO

**Purpose**: JSON schema, serialization, deserialization

**Location**: `src/wormgear/io/`

**Components**:
- `loaders.py` - Dataclasses and JSON load/save functions
- `schema.py` - JSON Schema v1.0 definition and validation

**Key Design Decisions**:
- **Schema versioning** - "1.0" with upgrade path
- **Dataclass-based** - Type-safe, IDE-friendly
- **Simplified schema** - Only dimensional data, no UI hints
- **Backwards compatible** - Upgrade old schemas automatically

**JSON Schema v1.0**:
```json
{
  "schema_version": "1.0",
  "worm": { "module_mm": 2.0, "num_starts": 1, ... },
  "wheel": { "module_mm": 2.0, "num_teeth": 30, ... },
  "assembly": { "centre_distance_mm": 38.14, "ratio": 30, ... },
  "manufacturing": { "profile": "ZA", ... },
  "features": { "worm": {...}, "wheel": {...} }  // optional
}
```

### Layer 3: CLI

**Purpose**: Command-line interface for batch operations

**Location**: `src/wormgear/cli/`

**Components**:
- `generate.py` - Geometry generation CLI (`wormgear-geometry`)

**Key Design Decisions**:
- **JSON-driven** - Accepts JSON from calculator
- **Batch-friendly** - Scriptable, automatable
- **Feature support** - Bores, keyways via CLI flags
- **Backward compatible** - `wormgear-geometry` command maintained

**CLI Example**:
```bash
# Generate from JSON (web calculator output)
wormgear-geometry design.json

# With features
wormgear-geometry design.json --worm-bore 8 --wheel-bore 12

# Globoid worm
wormgear-geometry design.json --globoid
```

## Data Flow

### Design Workflow

```
1. Engineering Requirements
   ↓
2. Calculator (design_from_module/wheel/centre_distance)
   ↓
3. Validation (validate_design)
   ↓
4. JSON Export (save_design_json)
   ↓
5. JSON Import (load_design_json)
   ↓
6. Geometry Generation (WormGeometry, WheelGeometry)
   ↓
7. STEP Export (export_step)
   ↓
8. CAM Software (FreeCAD, Fusion 360, etc.)
```

### Web Calculator Workflow

```
User Input (browser)
   ↓
Pyodide (Python in browser)
   ↓
wormcalc Python code
   ↓
JSON Schema v1.0
   ↓
Download JSON
   ↓
wormgear-geometry CLI
   ↓
STEP files for CNC
```

## Key Dataclasses

### WormParams
Dimensional parameters for worm:
- `module_mm`, `num_starts`, `pitch_diameter_mm`
- `tip_diameter_mm`, `root_diameter_mm`
- `lead_mm`, `lead_angle_deg`
- `addendum_mm`, `dedendum_mm`, `thread_thickness_mm`
- `hand` ("right" or "left")
- `profile_shift` (dimensionless)

### WheelParams
Dimensional parameters for wheel:
- `module_mm`, `num_teeth`, `pitch_diameter_mm`
- `tip_diameter_mm`, `root_diameter_mm`, `throat_diameter_mm`
- `helix_angle_deg`
- `addendum_mm`, `dedendum_mm`
- `profile_shift` (dimensionless)

### AssemblyParams
Assembly configuration:
- `centre_distance_mm`, `pressure_angle_deg`
- `backlash_mm`, `hand` ("right" or "left")
- `ratio` (gear ratio)
- `efficiency_percent`, `self_locking` (calculated)

### ManufacturingParams
Manufacturing/generation parameters:
- `profile` ("ZA" or "ZK" per DIN 3975)
- `virtual_hobbing` (bool)
- `hobbing_steps` (int)
- `throated_wheel` (bool)
- `sections_per_turn` (int, smoothness)

## Standards Compliance

### DIN 3975
Worm gear geometry standard:
- Profile types: ZA (straight flanks), ZK (convex flanks)
- Module series per ISO 54
- Pressure angles: 20° (standard), 14.5°, 25°

### ISO 54 / DIN 780
Standard modules (37 values from 0.3mm to 25mm):
- 0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0...

### DIN 6885
Keyway dimensions:
- Standard keyway sizes for bores 6mm-95mm
- Automatic keyway sizing based on bore diameter

## Manufacturing Target Methods

### Worm
- **4-axis lathe** with live tooling
- **5-axis mill**
- Exact geometry (no hobbing assumptions)

### Wheel
- **5-axis mill** (true form cutting)
- **Indexed 4-axis** with ball-nose finishing
- **Virtual hobbing** option for accurate throated teeth

## Performance Considerations

### Geometry Generation
- **Worm**: ~0.5-2 seconds (36 sections/turn)
- **Wheel**: ~1-3 seconds (30 teeth, helical)
- **Globoid worm**: ~2-4 seconds (complex throat)
- **Virtual hobbing wheel**: ~10-60 seconds (depends on steps)

**Optimization**:
- Reduce `sections_per_turn` for faster generation (minimum: 12)
- Use helical wheel instead of virtual hobbing for speed
- Virtual hobbing: use presets ("fast", "balanced", "precise")

### STEP File Size
- **Worm**: ~50-200 KB
- **Wheel**: ~100-500 KB
- **Complex features**: +10-50 KB each

## Testing Strategy

### Unit Tests
- Calculator functions (22 tests)
- Geometry generation (40+ tests)
- Features (bore, keyway, DD-cut) (30+ tests)
- IO (JSON load/save) (22 tests)

### Integration Tests
- Full workflow (calc → JSON → geometry)
- Globoid end-to-end
- Feature combinations

### Validation
- STEP file validity (OCP validation)
- Volume checks (within expected bounds)
- Watertight solid verification

## Future Enhancements

### Planned
- **Calculator CLI** - Command-line calculator interface
- **More validation rules** - Strength calculations, stress analysis
- **Assembly generation** - Positioned worm+wheel in single STEP
- **WASM build** - Full calculator+geometry in browser

### Under Consideration
- **Envelope calculation** - Mathematical tooth surface generation
- **B-spline surfaces** - More accurate wheel teeth
- **Tolerance modeling** - Clearances and fits in geometry
- **Material properties** - Strength calculations

## Dependencies

### Core Dependencies
- **build123d** ≥0.6.0 - CAD operations, STEP export
- **click** ≥8.0 - CLI framework

### Optional Dependencies
- **pytest** ≥7.0 - Testing
- **pytest-cov** - Coverage reporting
- **black** - Code formatting
- **ruff** - Linting

## Version History

### 1.0.0-alpha (2026-01-25)
- Initial unified package release
- Calculator + geometry in one package
- JSON Schema v1.0
- Web calculator integration
- Globoid worm support
- Validation module

---

*This architecture supports the goal: **CNC-manufacturable worm gears from engineering constraints***
