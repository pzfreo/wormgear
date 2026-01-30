# Plan: Post-Build Rim Thickness Measurement

**Status**: Planning
**Author**: Claude (with Paul Fremantle)
**Date**: 2026-01-30
**Target Version**: 2.1 (minor schema update)

---

## 1. Overview

### 1.1 Problem Statement

Current rim thickness calculation uses a mathematical formula:

```python
rim = (root_diameter - bore_diameter) / 2 - keyway_depth
```

This works for simple helical wheels but **does not account for**:

1. **Virtual hobbing effects** - The hobbing process creates a throated tooth form where the root may be deeper than calculated at certain points along the face width
2. **Actual keyway geometry** - The keyway slot extends outward from the bore, reducing effective rim at that location
3. **DD-cut bore effects** - The flat portions of a DD-cut may have different rim thickness than the cylindrical portions
4. **Globoid worm as hob** - Creates different root geometry than cylindrical worm

### 1.2 Proposed Solution

Add post-build measurement capability that:

1. Builds the wheel/worm geometry (including all features)
2. Uses OpenCascade's `BRepExtrema_DistShapeShape` to measure **actual minimum distance** from bore surface to outer surface
3. Reports the true minimum rim thickness in JSON output and CLI

### 1.3 Scope

| In Scope | Out of Scope |
|----------|--------------|
| Wheel rim measurement (bore to tooth root) | Pre-build estimation |
| Worm rim measurement (bore to thread root) | Stress/strength analysis |
| Keyway effects on rim | Material properties |
| DD-cut bore effects | Fatigue calculations |
| Virtual hobbing effects | Assembly interference |
| JSON output of measurements | Web UI changes (future) |
| CLI display of measurements | |

---

## 2. Technical Design

### 2.1 Architecture Fit

Per CLAUDE.md architecture rules:

```
┌─────────────────────────────────────────────────────────────┐
│                     wormgear Package                         │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              Layer 1: Core (Geometry)                   │ │
│  │  • WormGeometry, WheelGeometry                         │ │
│  │  • NEW: rim_thickness.py (measurement module)          │ │  ← Lives here
│  │  Pure geometry operations using build123d/OCP          │ │
│  └────────────────────────────────────────────────────────┘ │
│                           ▲                                  │
│                           │                                  │
│  ┌────────────────────────┼──────────────────────────────┐ │
│  │         Layer 2a: Calculator    Layer 2b: IO          │ │
│  │  (no changes)                   • MeasuredGeometry    │ │  ← New model
│  │                                   Pydantic model       │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              Layer 3: CLI                              │ │
│  │  • generate.py - calls measurement, displays results  │ │  ← Integration
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

**Why this is correct:**
- Measurement is a **geometry operation** (analyzing 3D solid) → Lives in Core layer
- Measurement does NOT import from Calculator → No layer violation
- IO layer gets new Pydantic model for output schema → Follows schema-first workflow
- CLI coordinates between Core measurement and IO output → Proper layer usage

### 2.2 Measurement Algorithm

#### 2.2.1 The Challenge with Keyways

A naive approach using a reference cylinder fails for keyways:

```
        ┌─────────────────────┐  ← Tooth tip
        │                     │
        │   ╔═══════════════╗ │  ← Tooth root surface
        │   ║               ║ │
        │   ║    ┌─────┐    ║ │  ← Keyway slot bottom
        │   ║    │ KEY │    ║ │     (THIS is closest to tooth root)
        │   ║    │     │    ║ │
        │   ║    └─────┘    ║ │
        │   ║               ║ │
        │   ║   (bore)      ║ │  ← Bore cylinder surface
        │   ╚═══════════════╝ │     (naive approach measures from here)
        └─────────────────────┘

WRONG: Reference cylinder measures from bore surface = 21.5mm
RIGHT: Actual geometry measures from keyway bottom = 19.2mm
```

#### 2.2.2 Correct Approach: Extract Actual Bore Surfaces

```python
def measure_rim_thickness(part: Part, bore_diameter_mm: float, ...) -> RimThicknessResult:
    """
    Measure minimum rim from actual bore surfaces to outer boundary.

    Algorithm:
    1. Extract all faces that form the bore cavity:
       - Cylindrical faces at bore radius
       - Keyway slot faces (bottom and walls)
       - DD-cut flat faces
    2. Extract all outer faces (teeth, tips, roots, end faces)
    3. Use BRepExtrema_DistShapeShape to find minimum distance
    4. Return result with location information
    """
```

#### 2.2.3 Face Classification Rules

| Face Type | Classification Rule | Belongs To |
|-----------|---------------------|------------|
| Cylindrical, radius ≈ bore_radius | Bore surface | Bore faces |
| Planar, inside bore region, normal pointing outward | Keyway bottom/DD-cut | Bore faces |
| Planar, inside bore region, normal tangent to radius | Keyway wall | Bore faces |
| Cylindrical, radius > bore_radius | Tooth flank/root | Outer faces |
| Planar, at Z extremes | End faces | Outer faces |
| All other faces | Tooth geometry | Outer faces |

#### 2.2.4 OCP Implementation

```python
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_FACE
from OCP.BRep import BRep_Tool
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Cylinder, GeomAbs_Plane
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeCompound

def _extract_bore_faces(part: Part, bore_diameter_mm: float) -> TopoDS_Compound:
    """Extract faces forming the bore cavity."""
    bore_radius = bore_diameter_mm / 2
    tolerance = 0.1  # mm

    bore_faces = []
    explorer = TopExp_Explorer(part.wrapped, TopAbs_FACE)

    while explorer.More():
        face = TopoDS.Face_s(explorer.Current())
        surface = BRepAdaptor_Surface(face)
        surf_type = surface.GetType()

        if surf_type == GeomAbs_Cylinder:
            # Check if it's the bore cylinder
            cylinder = surface.Cylinder()
            radius = cylinder.Radius()
            if abs(radius - bore_radius) < tolerance:
                bore_faces.append(face)

        elif surf_type == GeomAbs_Plane:
            # Check if it's inside bore region (keyway or DD-cut)
            # Get face centroid and check radial distance
            props = GProp_GProps()
            brepgprop_SurfaceProperties(face, props)
            centroid = props.CentreOfMass()
            radial_dist = sqrt(centroid.X()**2 + centroid.Y()**2)

            if radial_dist < bore_radius + tolerance:
                # Face is in bore region - likely keyway or DD-cut
                bore_faces.append(face)

        explorer.Next()

    # Build compound from bore faces
    builder = BRepBuilderAPI_MakeCompound()
    for face in bore_faces:
        builder.Add(face)
    return builder.Compound()

def _measure_minimum_distance(bore_compound: TopoDS_Compound,
                               part: Part) -> Tuple[float, gp_Pnt, gp_Pnt]:
    """Use BRepExtrema to find minimum distance."""
    extrema = BRepExtrema_DistShapeShape(bore_compound, part.wrapped)

    if not extrema.IsDone():
        raise RuntimeError("BRepExtrema calculation failed")

    if extrema.NbSolution() == 0:
        raise RuntimeError("No solution found - geometry may be invalid")

    min_distance = extrema.Value()
    point_on_bore = extrema.PointOnShape1(1)
    point_on_outer = extrema.PointOnShape2(1)

    return min_distance, point_on_bore, point_on_outer
```

### 2.3 Data Model

#### 2.3.1 Core Result Dataclass

```python
# src/wormgear/core/rim_thickness.py

from dataclasses import dataclass
from typing import Optional, Tuple

@dataclass
class RimThicknessResult:
    """Result of post-build rim thickness measurement.

    Attributes:
        minimum_thickness_mm: True minimum distance from bore surface to outer boundary.
            For wheels, this is typically bore→tooth root.
            For worms, this is typically bore→thread root.
        measurement_point_bore: (x, y, z) coordinates on bore surface at minimum.
        measurement_point_outer: (x, y, z) coordinates on outer surface at minimum.
        bore_diameter_mm: Bore diameter that was used.
        is_valid: Whether the measurement succeeded.
        has_warning: True if minimum_thickness_mm < warning_threshold_mm.
        warning_threshold_mm: Threshold below which warning is issued (default 1.5mm).
        message: Human-readable status message.
    """
    minimum_thickness_mm: float
    measurement_point_bore: Optional[Tuple[float, float, float]] = None
    measurement_point_outer: Optional[Tuple[float, float, float]] = None
    bore_diameter_mm: float = 0.0
    is_valid: bool = True
    has_warning: bool = False
    warning_threshold_mm: float = 1.5
    message: str = ""
```

#### 2.3.2 Pydantic Model for JSON Output

```python
# src/wormgear/io/loaders.py

class MeasurementPoint(BaseModel):
    """3D point where measurement was taken."""
    x_mm: float
    y_mm: float
    z_mm: float

class MeasuredGeometry(BaseModel):
    """Post-build geometry measurements from actual 3D solids.

    These values are measured from the built geometry after all features
    (bore, keyway, DD-cut, hobbing) have been applied. They may differ
    from theoretical calculations, especially for virtual-hobbed wheels.
    """
    model_config = ConfigDict(extra='ignore')

    wheel_rim_thickness_mm: Optional[float] = Field(
        default=None,
        description="Minimum rim thickness from wheel bore surface to tooth root (mm)"
    )
    wheel_measurement_point: Optional[MeasurementPoint] = Field(
        default=None,
        description="Location on bore surface where minimum rim was measured"
    )
    worm_rim_thickness_mm: Optional[float] = Field(
        default=None,
        description="Minimum rim thickness from worm bore surface to thread root (mm)"
    )
    worm_measurement_point: Optional[MeasurementPoint] = Field(
        default=None,
        description="Location on bore surface where minimum rim was measured"
    )
    measurement_timestamp: Optional[str] = Field(
        default=None,
        description="ISO 8601 timestamp when measurements were taken"
    )

class WormGearDesign(BaseModel):
    """Complete worm gear design."""
    # ... existing fields ...

    measured_geometry: Optional[MeasuredGeometry] = Field(
        default=None,
        description="Post-build measurements from actual 3D geometry"
    )
```

### 2.4 API Design

#### 2.4.1 Core Module API

```python
# src/wormgear/core/rim_thickness.py

def measure_rim_thickness(
    part: Part,
    bore_diameter_mm: float,
    part_length_mm: Optional[float] = None,
    warning_threshold_mm: float = 1.5
) -> RimThicknessResult:
    """
    Measure minimum rim thickness from bore surface to outer boundary.

    This function analyzes the actual 3D geometry to find the true minimum
    distance from any bore surface (including keyway slots and DD-cut flats)
    to the outer boundary (tooth roots for wheels, thread roots for worms).

    Args:
        part: Built Part with all features applied (bore, keyway, etc.)
        bore_diameter_mm: Nominal bore diameter for face classification.
        part_length_mm: Part length for validation (optional).
        warning_threshold_mm: Threshold for thin rim warning (default 1.5mm).

    Returns:
        RimThicknessResult with measurement details and warning status.

    Raises:
        ValueError: If part has no bore or measurement fails.

    Example:
        >>> wheel = WheelGeometry(..., bore=BoreFeature(12.0), keyway=KeywayFeature())
        >>> wheel.build()
        >>> result = measure_rim_thickness(wheel.solid, bore_diameter_mm=12.0)
        >>> print(f"Minimum rim: {result.minimum_thickness_mm:.2f}mm")
        Minimum rim: 8.45mm
    """
```

#### 2.4.2 CLI Integration

```python
# src/wormgear/cli/generate.py

# After building wheel:
if wheel_bore_diameter is not None:
    from wormgear.core import measure_rim_thickness

    rim_result = measure_rim_thickness(
        wheel_geo.solid,
        bore_diameter_mm=wheel_bore_diameter
    )

    click.echo(f"  Measured rim thickness: {rim_result.minimum_thickness_mm:.2f} mm")

    if rim_result.has_warning:
        click.secho(
            f"  WARNING: Rim thickness ({rim_result.minimum_thickness_mm:.2f}mm) "
            f"is below recommended minimum ({rim_result.warning_threshold_mm}mm)",
            fg='yellow'
        )
```

#### 2.4.3 JSON Output

```json
{
  "schema_version": "2.1",
  "worm": { "..." },
  "wheel": { "..." },
  "assembly": { "..." },
  "features": {
    "wheel": {
      "bore_type": "custom",
      "bore_diameter_mm": 12.0,
      "anti_rotation": "DIN6885"
    },
    "worm": {
      "bore_type": "custom",
      "bore_diameter_mm": 8.0,
      "anti_rotation": "DIN6885"
    }
  },
  "measured_geometry": {
    "wheel_rim_thickness_mm": 8.45,
    "wheel_measurement_point": {
      "x_mm": 6.0,
      "y_mm": 0.0,
      "z_mm": 2.3
    },
    "worm_rim_thickness_mm": 3.65,
    "worm_measurement_point": {
      "x_mm": 4.0,
      "y_mm": 0.0,
      "z_mm": 1.8
    },
    "measurement_timestamp": "2026-01-30T14:32:15Z"
  }
}
```

---

## 3. Implementation Plan

### 3.1 Phase 1: Core Measurement Module

**Files:**
- `src/wormgear/core/rim_thickness.py` (NEW)
- `src/wormgear/core/__init__.py` (modify exports)

**Tasks:**
1. Create `RimThicknessResult` dataclass
2. Implement `_extract_bore_faces()` helper
3. Implement `_classify_face()` helper
4. Implement `measure_rim_thickness()` main function
5. Add exports to `__init__.py`

**Testing:**
- Test with simple cylinder (known geometry)
- Test with wheel without bore (should return appropriate error)
- Test with wheel + cylindrical bore
- Test with wheel + bore + keyway
- Test with wheel + bore + DD-cut
- Test with worm + bore + keyway
- Test with virtual hobbing wheel

### 3.2 Phase 2: Schema Updates

**Files:**
- `src/wormgear/io/loaders.py` (modify)

**Tasks:**
1. Add `MeasurementPoint` model
2. Add `MeasuredGeometry` model
3. Add `measured_geometry` field to `WormGearDesign`

**Schema Workflow (MANDATORY per CLAUDE.md):**
```bash
# 1. Edit loaders.py
# 2. Regenerate JSON schemas
python scripts/generate_schemas.py
# 3. Regenerate TypeScript types
bash scripts/generate_types.sh
# 4. Run type checking
bash scripts/typecheck.sh
# 5. Run tests
pytest tests/
# 6. Commit ALL together
```

### 3.3 Phase 3: CLI Integration

**Files:**
- `src/wormgear/cli/generate.py` (modify)

**Tasks:**
1. Import `measure_rim_thickness` from core
2. Call measurement after wheel build (if bore present)
3. Call measurement after worm build (if bore present)
4. Display results in CLI output
5. Include measurements in JSON output when `--save-json` used

### 3.4 Phase 4: Testing & Documentation

**Files:**
- `tests/test_rim_thickness.py` (NEW)
- `docs/ARCHITECTURE.md` (update)
- `CLAUDE.md` (update Current State section)

**Tasks:**
1. Write comprehensive unit tests
2. Write integration tests (full workflow)
3. Performance benchmarking
4. Update documentation

---

## 4. Test Plan

### 4.1 Unit Tests

```python
# tests/test_rim_thickness.py

class TestRimThicknessMeasurement:
    """Tests for post-build rim thickness measurement."""

    def test_simple_cylinder_known_geometry(self):
        """Verify measurement on cylinder with known dimensions.

        Create cylinder OD=50mm with bore ID=20mm.
        Expected rim = (50-20)/2 = 15mm.
        """

    def test_no_bore_returns_error(self):
        """Solid part without bore should indicate not applicable."""

    def test_wheel_with_cylindrical_bore(self):
        """Standard wheel with simple bore."""

    def test_wheel_with_keyway_reduces_rim(self):
        """Keyway should reduce measured rim by hub depth.

        For 12mm bore: DIN 6885 hub depth = 2.3mm
        Measured rim should be ~2.3mm less than without keyway.
        """

    def test_wheel_with_ddcut_bore(self):
        """DD-cut creates two flat surfaces - measure from both."""

    def test_worm_with_bore_and_keyway(self):
        """Worm thread root should be measurement target."""

    def test_virtual_hobbing_wheel(self):
        """Virtual hobbing may create different root geometry."""

    def test_globoid_worm_varying_root(self):
        """Globoid worm has varying root diameter along length."""

    def test_warning_threshold(self):
        """Verify has_warning flag when below threshold."""

    def test_measurement_point_location(self):
        """Measurement point should be at actual minimum location."""
```

### 4.2 Integration Tests

```python
class TestRimThicknessIntegration:
    """End-to-end tests with full workflow."""

    def test_cli_displays_rim_thickness(self):
        """CLI should show measured rim in output."""

    def test_json_output_includes_measurements(self):
        """JSON export should include measured_geometry section."""

    def test_virtual_hobbing_vs_helical_comparison(self):
        """Compare measured rim between wheel types."""
```

### 4.3 Performance Tests

| Scenario | Target Time |
|----------|-------------|
| Simple wheel measurement | < 1 second |
| Wheel with keyway | < 1 second |
| Virtual hobbing wheel (72 steps) | < 2 seconds |
| Virtual hobbing wheel (144 steps) | < 3 seconds |

### 4.4 Edge Cases

| Case | Expected Behavior |
|------|-------------------|
| No bore (solid wheel) | `is_valid=False`, `message="No bore present"` |
| Bore > root diameter | `has_warning=True`, rim may be 0 or negative |
| Very small rim (< 0.5mm) | Error-level warning |
| Complex keyway geometry | Should find true minimum |
| Multiple keyways | Should find global minimum |

---

## 5. Risk Assessment

### 5.1 Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| BRepExtrema performance on complex geometry | Medium | Medium | Test with various hobbing steps; document performance |
| Face classification errors (wrong faces as bore) | Medium | High | Comprehensive testing; tolerance tuning |
| OCP API differences between versions | Low | Medium | Pin OCP version; test on CI |
| Measurement precision issues | Low | Low | Document tolerance; round appropriately |

### 5.2 Architecture Risks

| Risk | Mitigation |
|------|------------|
| Layer violation (importing geometry in calculator) | Measurement stays in Core layer; only result data flows to IO |
| Schema drift | Follow schema-first workflow exactly |
| Breaking change to JSON output | New `measured_geometry` field is optional; existing parsers unaffected |

---

## 6. Checklist (from CLAUDE.md)

### Pre-Implementation
- [ ] Architecture alignment verified (Core layer for measurement)
- [ ] No calculator→geometry imports
- [ ] Schema changes identified (MeasuredGeometry model)
- [ ] Test plan created

### During Implementation
- [ ] Type safety maintained (no string enums, proper types)
- [ ] Unit suffixes used (_mm for all dimensions)
- [ ] Error handling for edge cases
- [ ] No over-engineering (minimal API surface)

### Pre-Push (MANDATORY)
- [ ] Changes compile/import without errors
- [ ] Pydantic models changed → schemas regenerated
  ```bash
  python scripts/generate_schemas.py
  bash scripts/generate_types.sh
  git add schemas/ web/types/
  ```
- [ ] CLI tested locally and works
- [ ] pytest passes locally: `pytest tests/ -v`
- [ ] No type safety regressions
- [ ] Changes batched (not micro-commits)

### Post-Implementation
- [ ] Documentation updated (ARCHITECTURE.md)
- [ ] CLAUDE.md Current State updated
- [ ] Integration tests pass
- [ ] Performance acceptable (< 3s for complex cases)

---

## 7. Success Criteria

1. **Functional**: Measurement accurately reports minimum rim thickness including keyway/DD-cut effects
2. **Performance**: Measurement completes in < 3 seconds for typical geometry
3. **Integration**: CLI displays measurements; JSON includes `measured_geometry` section
4. **Testing**: >90% code coverage on new module; all edge cases handled
5. **Architecture**: No layer violations; schema-first workflow followed
6. **Documentation**: Updated docs reflect new capability

---

## 8. Open Questions

1. **Web UI**: Should measurements be displayed in web calculator? (Deferred to future)
2. **Warnings in validation**: Should thin rim measurements trigger validation warnings? (Probably yes)
3. **Multiple measurement points**: Should we report all local minima or just global minimum? (Start with global)

---

## 9. References

- [CLAUDE.md](/CLAUDE.md) - Project conventions and best practices
- [ARCHITECTURE.md](/docs/ARCHITECTURE.md) - Layer structure and dependencies
- [OpenCascade BRepExtrema](https://dev.opencascade.org/doc/refman/html/class_b_rep_extrema___dist_shape_shape.html) - OCP distance calculation
- [DIN 6885](https://www.din.de/) - Keyway dimensions standard
