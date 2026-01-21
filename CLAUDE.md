# CLAUDE.md - Worm Gear Geometry Generator

## Project Summary

Worm gear geometry generator - Python library using build123d to create CNC-ready STEP files from validated worm gear parameters.

**Owner**: Paul Fremantle (pzfreo) - luthier and hobby programmer
**Use case**: Generating exact 3D CAD models for CNC machining custom worm gears

## Relationship to Calculator

This is **Tool 2** in the worm gear system. It works with **Tool 1** (calculator):

```
Tool 1: wormgearcalc          Tool 2: wormgear-geometry (this repo)
─────────────────────          ───────────────────────────────────
User constraints               JSON parameters
    ↓                              ↓
Engineering calc     ────►     3D geometry generation
    ↓                              ↓
JSON export                    STEP files (CNC-ready)
```

**Calculator repo**: https://github.com/pzfreo/wormgearcalc
**Live web calculator**: https://pzfreo.github.io/wormgearcalc/

## Current State

**Status: Phase 2 in progress - bore and keyway features complete**

The core geometry generator is functional with worm and wheel generation, STEP export, CLI, and feature support (bores, keyways).

## Target Manufacturing Methods

The geometry must be **exact and watertight** - no approximations:

- **Worm**: 4-axis lathe with live tooling, or 5-axis mill
- **Wheel**: 5-axis mill (true form), or indexed 4-axis with ball-nose finishing

## Key Design Decisions

1. **build123d for CAD** - Modern Python CAD library built on OpenCascade
2. **Exact geometry** - No hobbing assumptions, CNC will cut exactly what we model
3. **JSON input** - Accepts output from wormgearcalc (Tool 1)
4. **Two wheel types**:
   - **Helical** (default): Flat-bottomed trapezoidal teeth, simpler geometry
   - **Hobbed** (`--hobbed`): Throated teeth with depth varying to match worm curvature
5. **Feature-rich** - Support bores, keyways (ISO 6885), set screws, hubs (Phase 2)

## Implementation Status

See `docs/GEOMETRY.md` for full specification.

### Phase 1: Basic Geometry ✓ Complete
- [x] Worm thread generation (lofted sections along helix path)
- [x] Wheel generation with two options:
  - Helical: flat-bottomed trapezoidal teeth
  - Hobbed: integrated throating where tooth depth varies with Z to match worm curvature
- [x] STEP export with validation
- [x] Python API and CLI
- [x] OCP viewer integration
- [x] Multi-start worm support
- [x] Left/right hand support
- [x] Profile shift and backlash handling

### Phase 2: Features (In Progress)
- [x] Bore with auto-calculation and custom diameters
  - **Auto-calculation**: Approximately 25% of pitch diameter, constrained by rim thickness
  - **Constraints**: Leaves ≥1mm rim thickness (or ≥12.5% of root diameter)
  - **Rounding**: Results rounded to 0.5mm (small bores) or 1mm (large bores)
  - **Warnings**: Issues warning if rim thickness <1.5mm
- [x] Keyways (ISO 6885 / DIN 6885 standard sizes)
- [x] Small gear support (bores down to 2mm, below DIN 6885 range)
- [x] Thin rim warnings for structural integrity
- [ ] Set screw holes
- [ ] Hub options (flush/extended/flanged)

### Phase 3: Accurate Wheel (Future)
- [ ] Mathematical envelope calculation
- [ ] B-spline surface generation
- [ ] Compare accuracy with current approach

### Phase 4: Polish
- [ ] Assembly positioning (correctly oriented parts)
- [ ] Manufacturing specs markdown output

## JSON Input Format

The calculator outputs this format (example):

```json
{
  "worm": {
    "module_mm": 2.0,
    "num_starts": 1,
    "pitch_diameter_mm": 16.29,
    "tip_diameter_mm": 20.29,
    "root_diameter_mm": 11.29,
    "lead_mm": 6.283,
    "lead_angle_deg": 7.0,
    "addendum_mm": 2.0,
    "dedendum_mm": 2.5,
    "thread_thickness_mm": 3.14,
    "profile_shift": 0.0
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
    "pressure_angle_deg": 20.0,
    "backlash_mm": 0.05,
    "hand": "right"
  }
}
```

## Current API

```python
from wormgear_geometry import load_design_json, WormGeometry, WheelGeometry
from wormgear_geometry.features import BoreFeature, KeywayFeature

# Load parameters from calculator JSON
design = load_design_json("design.json")

# Build worm with bore and keyway
worm_geo = WormGeometry(
    params=design.worm,
    assembly_params=design.assembly,
    length=40,  # User specifies worm length
    sections_per_turn=36,  # Smoothness (default: 36)
    bore=BoreFeature(diameter=8.0),  # Optional: adds bore
    keyway=KeywayFeature()  # Optional: adds DIN 6885 keyway
)
worm = worm_geo.build()
worm_geo.export_step("worm_m2_z1.step")

# Build wheel (helical - default) with features
wheel_geo = WheelGeometry(
    params=design.wheel,
    worm_params=design.worm,
    assembly_params=design.assembly,
    face_width=None,  # Auto-calculated if None
    throated=False,    # Helical teeth (default)
    bore=BoreFeature(diameter=12.0),
    keyway=KeywayFeature()
)
wheel = wheel_geo.build()
wheel_geo.export_step("wheel_m2_z30.step")

# Build wheel (hobbed/throated)
wheel_geo_hobbed = WheelGeometry(
    params=design.wheel,
    worm_params=design.worm,
    assembly_params=design.assembly,
    throated=True  # Throated teeth for better worm contact
)
wheel_hobbed = wheel_geo_hobbed.build()
wheel_geo_hobbed.export_step("wheel_m2_z30_hobbed.step")
```

### CLI Usage

```bash
# Generate both worm and wheel (with auto-calculated bores and keyways by default)
wormgear-geometry design.json

# Generate solid parts without bores
wormgear-geometry design.json --no-bore

# With hobbed wheel
wormgear-geometry design.json --hobbed

# Custom bore sizes (keyways auto-sized to match)
wormgear-geometry design.json --worm-bore 8 --wheel-bore 15

# Bores but no keyways
wormgear-geometry design.json --no-keyway

# Custom dimensions
wormgear-geometry design.json --worm-length 50 --wheel-width 12

# View in OCP viewer
wormgear-geometry design.json --view --no-save --mesh-aligned
```

## Geometry Construction Approaches

### Worm (Straightforward)

Helical sweep of trapezoidal tooth profile:

1. Create tooth profile in axial plane (trapezoid based on pressure angle)
2. Create helix path at pitch radius
3. Position profile perpendicular to helix
4. Sweep along helix
5. Add core cylinder
6. Union and trim to length
7. Add features (bore, keyway)

### Wheel (Three Options)

**Option A: Simulated Hobbing**
- Most accurate - simulate manufacturing process
- Very slow (thousands of boolean operations)
- Good for validation/comparison

**Option B: Envelope Calculation**
- Mathematical calculation of contact surface
- Complex mathematics but fast and clean
- Future enhancement

**Option C: Hybrid (RECOMMENDED START)**
- Generate helical involute gear
- Apply throating cut (cylinder at worm radius)
- Fast, simple, produces functional geometry
- **Start here, iterate to B if accuracy issues arise**

## Engineering Context

### Standards
- **DIN 3975** - Worm geometry definitions
- **ISO 54 / DIN 780** - Standard modules
- **ISO 6885 / DIN 6885** - Keyway dimensions

### Keyway Sizes (DIN 6885)

**Common sizes** (full table in `docs/ENGINEERING_CONTEXT.md` and `src/wormgear_geometry/features.py`):

| Bore (mm) | Key Width | Key Height | Shaft Depth | Hub Depth |
|-----------|-----------|------------|-------------|-----------|
| 6-8       | 2         | 2          | 1.2         | 1.0       |
| 8-10      | 3         | 3          | 1.8         | 1.4       |
| 10-12     | 4         | 4          | 2.5         | 1.8       |
| 12-17     | 5         | 5          | 3.0         | 2.3       |
| 17-22     | 6         | 6          | 3.5         | 2.8       |
| ...       | ...       | ...        | ...         | ...       |
| 85-95     | 25        | 14         | 9.0         | 5.4       |

**Note:** Full implementation supports bores from 6mm to 95mm. For bores below 6mm (small gears), keyways are omitted or require custom dimensions.

### Profile Shift
- The calculator now supports profile shift coefficients
- This adjusts addendum/dedendum to prevent undercut on low tooth counts
- Geometry generator must respect the adjusted dimensions from JSON

## Output Requirements

### STEP Files
- Watertight solids (no gaps, overlaps)
- Clean topology (no degenerate faces)
- Appropriate precision (1e-6 tolerance)
- Named bodies/components for assembly

### Manufacturing Specs
Generate markdown alongside STEP with tolerances:

```markdown
# Worm - Manufacturing Specification

| Parameter | Value | Tolerance |
|-----------|-------|-----------|
| Outside Diameter | 20.00 mm | ±0.02 |
| Pitch Diameter | 16.00 mm | Reference |
| Root Diameter | 11.00 mm | +0.05/-0 |
| Length | 40.00 mm | ±0.1 |
| Lead | 6.283 mm | ±0.01 |
| Thread Hand | Right | - |

Material: [TBD by user]
Surface Finish: Ra 1.6 (thread flanks)
```

## Dependencies

- **build123d** - Core CAD operations (modern, Pythonic)
- **OCP** - OpenCascade bindings (via build123d)
- **py_gearworks** (optional) - Reference for API patterns

## Testing Strategy

1. **Geometry validation**
   - Export STEP, reimport, check volume matches
   - OCC validation for bad faces/edges

2. **Mesh compatibility**
   - Generate pair, check centre distance
   - Verify no interference at assembly

3. **Manufacturing validation**
   - Import to CAM software (FreeCAD, Fusion 360)
   - Verify toolpath generation succeeds
   - Check for unmachineable features

## File Structure (Proposed)

```
wormgear-geometry/
├── src/wormgear_geometry/
│   ├── __init__.py
│   ├── worm.py          # Worm generation
│   ├── wheel.py         # Wheel generation (hybrid approach)
│   ├── features.py      # Bores, keyways, set screws
│   ├── assembly.py      # Positioning parts
│   ├── io.py            # JSON input, STEP export
│   └── specs.py         # Manufacturing specs output
├── tests/
│   ├── test_worm.py
│   ├── test_wheel.py
│   └── test_assembly.py
├── examples/
│   ├── basic_pair.py
│   └── sample_designs/  # JSON files from calculator
├── docs/
│   └── GEOMETRY.md      # Full specification
├── pyproject.toml
├── README.md
└── CLAUDE.md            # This file
```

## Quick Start (When Implementing)

1. **Setup build123d**
   ```bash
   pip install build123d
   ```

2. **Test basic CAD operations**
   ```python
   from build123d import *

   # Simple worm core
   core = Cylinder(radius=8, height=40)
   core.export_step("test.step")
   ```

3. **Implement worm first** (simpler than wheel)
   - Start with straight cylinder
   - Add helical sweep
   - Validate STEP export

4. **Then implement hybrid wheel**
   - Helical gear generation
   - Throat cut
   - Test mesh with worm

5. **Add features incrementally**
   - Bore
   - Keyway
   - Set screw

## Key Challenges to Watch

1. **Helix orientation** - Ensuring profile perpendicular to helix path
2. **Thread hand** - Right vs left hand needs careful coordinate transform
3. **Wheel throat** - Getting the throating cylinder positioned exactly right
4. **Surface continuity** - Avoiding gaps at thread start/end
5. **Tolerance modeling** - Representing clearances and fits in STEP

## Reference Resources

- **build123d docs**: https://build123d.readthedocs.io/
- **py_gearworks**: https://github.com/gumyr/py_gearworks (for helical gear patterns)
- **DIN 3975**: Worm gear geometry standard
- **ISO 6885**: Parallel keys and keyways

## Next Steps

1. Initialize Python project structure
2. Install build123d and test basic operations
3. Implement simple worm generation (Phase 1)
4. Validate STEP export to CAD software
5. Implement hybrid wheel approach
6. Test worm-wheel mesh fit
7. Add feature support (bores, keyways)
8. Polish API and create examples

---

**Remember**: The goal is CNC-manufacturable parts. Every dimension must be exact and intentional. The calculator (Tool 1) has already validated the parameters - your job is to faithfully convert them to 3D geometry.
