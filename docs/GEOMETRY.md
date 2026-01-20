# Worm Gear Geometry Generator - Specification

## Overview

Tool 2 in the worm gear system. Takes validated parameters from the calculator (Tool 1) and generates CNC-ready STEP geometry.

**Status: Phase 2 in progress - bore and keyway features complete**

## Target: CNC Manufacture

The geometry must be exact and watertight - no relying on hobbing to "fix" approximations. Target manufacturing methods:

- **Worm**: 4-axis lathe with live tooling, or 5-axis mill
- **Wheel**: 5-axis mill (true form), or indexed 4-axis with ball-nose finishing

## Relationship to Tool 1

```
Tool 1 (Calculator)          Tool 2 (Geometry)
─────────────────           ─────────────────
Constraints ──► Parameters ──► STEP files
              (JSON export)    
```

Tool 2 accepts JSON output from Tool 1:

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
    "pressure_angle_deg": 20.0,
    "backlash_mm": 0.05,
    "hand": "right"
  }
}
```

## Geometry Construction

### Worm

Relatively straightforward - helical sweep of trapezoidal profile.

```python
# Pseudocode
def build_worm(params):
    # 1. Create tooth profile in axial plane (trapezoidal)
    profile = trapezoidal_profile(
        pitch_half_thickness=params.axial_pitch / 4,
        addendum=params.addendum,
        dedendum=params.dedendum,
        pressure_angle=params.pressure_angle
    )
    
    # 2. Create helix path at pitch radius
    helix = Helix(
        pitch=params.lead,
        height=params.length + params.lead,  # Extra for trimming
        radius=params.pitch_radius
    )
    
    # 3. Position profile perpendicular to helix, Y-axis radial
    positioned_profile = orient_to_helix(profile, helix)
    
    # 4. Sweep
    thread = sweep(positioned_profile, helix)
    
    # 5. Add core cylinder
    core = Cylinder(radius=params.root_radius, height=params.length)
    
    # 6. Union and trim to length
    worm = (core + thread).intersect(trim_box)
    
    # 7. Add features (bore, keyway)
    worm = add_features(worm, params.features)
    
    return worm
```

### Worm Wheel - The Challenge

The wheel tooth is NOT a standard involute. It's the envelope of the worm thread surface as the worm rotates.

#### Option A: Simulated Hobbing (Most Accurate)

Simulate the manufacturing process:

```python
def build_wheel_hobbing(params, worm_params):
    # 1. Create blank cylinder
    blank = Cylinder(
        radius=params.tip_radius,
        height=params.face_width
    )
    
    # 2. Create worm cutter (slightly oversized worm)
    cutter = build_worm(worm_params, oversized=True)
    
    # 3. Position at centre distance
    cutter = cutter.translate(Y=centre_distance)
    
    # 4. Simulate hobbing - rotate both at gear ratio
    num_steps = 360 * params.num_teeth  # One step per degree of wheel
    for step in range(num_steps):
        wheel_angle = step / params.num_teeth
        worm_angle = step  # Worm rotates num_teeth times faster
        
        rotated_cutter = cutter.rotate(Z, worm_angle)
        rotated_blank = blank.rotate(wheel_axis, wheel_angle)
        
        blank = blank - rotated_cutter
    
    return blank
```

**Pros**: Geometrically exact
**Cons**: Very slow (thousands of boolean operations)

#### Option B: Envelope Calculation (Mathematical)

Calculate the tooth surface analytically:

```python
def build_wheel_envelope(params, worm_params):
    # 1. Parameterize worm thread surface as S(u, v)
    # u = along helix, v = across tooth flank
    
    # 2. For each wheel rotation angle θ:
    #    - Transform worm surface by rotation about wheel axis
    #    - Find contact curve where surface normal ⊥ relative velocity
    #    - Collect contact points
    
    # 3. Build B-spline surface through contact points
    
    # 4. Create solid from surfaces
```

**Pros**: Cleaner geometry, faster
**Cons**: Complex mathematics, potential for surface discontinuities

#### Option C: Practical Hybrid (Recommended Starting Point)

1. Generate helical gear with correct base parameters
2. Apply throating cut (cylinder at worm tip radius)
3. Document as approximation suitable for CNC

```python
def build_wheel_hybrid(params, worm_params):
    # 1. Build helical gear
    wheel = build_helical_gear(
        module=params.module,
        num_teeth=params.num_teeth,
        helix_angle=params.helix_angle,
        face_width=params.face_width,
        pressure_angle=params.pressure_angle
    )

    # 2. Throating cut - cylinder matching worm envelope
    throat_cutter = Cylinder(
        radius=worm_params.tip_radius + clearance,
        height=params.face_width * 2
    )
    throat_cutter = throat_cutter.rotate(X, 90)  # Perpendicular to wheel
    throat_cutter = throat_cutter.translate(Y=centre_distance)

    wheel = wheel - throat_cutter

    # 3. Add features
    wheel = add_features(wheel, params.features)

    return wheel
```

**Pros**: Much simpler, fast, produces functional geometry
**Cons**: Not mathematically exact (but CNC will cut what you give it)

**Recommendation**: Start with Option C, iterate to Option B if accuracy issues arise.

#### Option D: Integrated Throating (✓ Implemented)

Instead of a separate throat cut (which can incorrectly remove teeth), integrate the throating directly into the tooth profile generation:

```python
def build_wheel_integrated_throat(params, worm_params, throated=True):
    # For each Z position along face width:
    for z_pos in face_width_positions:
        if throated and abs(z_pos) < worm_tip_radius:
            # Calculate where worm surface is at this Z
            worm_surface_dist = centre_distance - sqrt(worm_radius² - z_pos²)
            # Use shallower root depth where worm doesn't reach
            actual_root = max(calculated_root, worm_surface_dist)
        else:
            actual_root = calculated_root

        # Create tooth profile with this root depth
        profile = trapezoidal_profile(root=actual_root, ...)

    # Loft profiles together - throat emerges naturally
    wheel = loft(profiles)
```

**How it works**:
- At the center of the face width (z=0), teeth can be deepest (worm cuts closest)
- At the edges of the face width, teeth are shallower (worm doesn't reach as deep)
- The varying depth across Z creates the characteristic concave throat shape
- Teeth remain intact because the throat is part of the tooth geometry, not a separate cut

**Pros**:
- Teeth never get incorrectly removed
- Natural throat shape emerges from geometry
- Single loft operation (fast)
- Produces functional, CNC-ready geometry

**Cons**:
- Not mathematically exact envelope (same as Option C)
- Tooth flanks are still helical involute, not true worm-generated

This is the current implementation, selected via `throated=True` or `--hobbed` CLI flag.

## Feature Options

### Bore

```python
@dataclass
class BoreFeatures:
    diameter: float
    through: bool = True
    counterbore_diameter: Optional[float] = None
    counterbore_depth: Optional[float] = None
```

### Keyway (ISO 6885 / DIN 6885)

```python
@dataclass  
class KeywayFeatures:
    width: Optional[float] = None   # Auto from bore if None
    depth: Optional[float] = None   # Auto from standard
    length: Optional[float] = None  # Through if None
```

Standard keyway sizes (DIN 6885):

| Bore (mm) | Key Width | Key Height | Shaft Depth | Hub Depth |
|-----------|-----------|------------|-------------|-----------|
| 6-8       | 2         | 2          | 1.2         | 1.0       |
| 8-10      | 3         | 3          | 1.8         | 1.4       |
| 10-12     | 4         | 4          | 2.5         | 1.8       |
| 12-17     | 5         | 5          | 3.0         | 2.3       |
| 17-22     | 6         | 6          | 3.5         | 2.8       |

### Set Screw

```python
@dataclass
class SetScrewFeatures:
    thread_size: str = "M4"  # e.g., "M3", "M4", "M5"
    angle_from_keyway: float = 90  # degrees
    depth: Optional[float] = None  # Auto based on thread
```

### Hub

```python
@dataclass
class HubFeatures:
    style: str = "flush"  # flush | extended | flanged
    extended_length: Optional[float] = None
    extended_diameter: Optional[float] = None
    flange_diameter: Optional[float] = None
    flange_thickness: Optional[float] = None
```

## Current API

```python
from wormgear_geometry import load_design_json, WormGeometry, WheelGeometry

# From JSON (Tool 1 output)
design = load_design_json("design.json")

# Build worm
worm_geo = WormGeometry(
    params=design.worm,
    assembly_params=design.assembly,
    length=40,
    sections_per_turn=36  # Smoothness (default: 36)
)
worm = worm_geo.build()
worm_geo.export_step("worm_m2_z1.step")

# Build wheel (helical - default)
wheel_geo = WheelGeometry(
    params=design.wheel,
    worm_params=design.worm,
    assembly_params=design.assembly,
    face_width=None,  # Auto-calculated if None
    throated=False    # Helical teeth (default)
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

### Command Line Interface

```bash
# Basic usage
wormgear-geometry design.json

# With options
wormgear-geometry design.json \
    --worm-length 50 \
    --wheel-width 12 \
    --hobbed \
    --sections 72 \
    -o output/

# View only (no save)
wormgear-geometry design.json --view --no-save --mesh-aligned
```

### CLI Options

| Option | Description | Default |
|--------|-------------|---------|
| `--worm-length` | Worm length in mm | 40 |
| `--wheel-width` | Wheel face width in mm | auto |
| `--sections` | Worm sections per turn (smoothness) | 36 |
| `--hobbed` | Generate throated wheel | false (helical) |
| `--worm-only` | Generate only worm | both |
| `--wheel-only` | Generate only wheel | both |
| `--view` | Display in OCP viewer | false |
| `--no-save` | Don't save STEP files | false |
| `--mesh-aligned` | Rotate wheel for visual mesh | false |
| `-o, --output-dir` | Output directory | current |

## Build123d Integration

The geometry generator should integrate with py_gearworks patterns where sensible:

```python
# Similar to py_gearworks
worm.mesh_to(wheel)  # Position at correct centre distance
worm.center_location_top  # For adding features
```

## Output Requirements

### STEP Export

- Watertight solids (no gaps, overlaps)
- Clean topology (no degenerate faces)
- Appropriate precision (suggest 1e-6 tolerance)
- Named bodies/components for assembly

### Manufacturing Specs Sheet

Generate alongside STEP:

```markdown
# Worm - Manufacturing Specification

| Parameter | Value | Tolerance |
|-----------|-------|-----------|
| Outside Diameter | 20.00 mm | ±0.02 |
| Pitch Diameter | 16.00 mm | Reference |
| Root Diameter | 11.00 mm | +0.05/-0 |
| Length | 40.00 mm | ±0.1 |
| Lead | 6.283 mm | ±0.01 |
| Lead Angle | 7.0° | Reference |
| Thread Hand | Right | - |

Material: [TBD by user]
Surface Finish: Ra 1.6 (thread flanks)
```

## Testing Strategy

1. **Geometry validation**
   - Export STEP, reimport, check volume matches
   - Check for bad faces/edges (OCC validation)
   
2. **Mesh compatibility**
   - Generate pair, check centre distance
   - Verify no interference at assembly

3. **Manufacturing validation**
   - Import to CAM software
   - Check toolpath generation succeeds

## Dependencies

- **build123d** - Core CAD operations
- **OCP** - OpenCascade Python bindings (via build123d)
- **py_gearworks** (optional) - Reference for API patterns

## Implementation Phases

### Phase 1: Basic Geometry ✓ Complete
- [x] Worm thread generation (lofted sections along helix)
- [x] Wheel generation with two options:
  - Helical: flat-bottomed trapezoidal teeth
  - Hobbed: throated teeth with depth varying to match worm curvature
- [x] STEP export validation
- [x] Python API and CLI
- [x] OCP viewer integration
- [x] Multi-start worm support
- [x] Left/right hand support

### Phase 2: Features (In Progress)
- [x] Bore with auto-calculation and custom diameters
- [x] Keyways (ISO 6885 / DIN 6885 standard sizes)
- [x] Small gear support (bores down to 2mm, below DIN 6885 range)
- [x] Thin rim warnings for structural integrity
- [ ] Set screw holes
- [ ] Hub options

### Phase 3: Accurate Wheel (Future)
- [ ] Envelope calculation (Option B)
- [ ] B-spline surface generation
- [ ] Comparison with integrated throating approach

### Phase 4: Polish
- [ ] Assembly positioning
- [ ] Manufacturing specs output (markdown)
- [ ] Integration improvements with Tool 1
