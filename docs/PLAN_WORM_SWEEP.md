# Worm Sweep Implementation Plan

**Author:** Claude (with Paul Fremantle)
**Date:** 2026-02-10
**Status:** Draft for Review
**Branch:** `claude/review-docs-sweep-plan-H1xfL`

---

## 1. Goal

Replace the current lofted-sections worm generation with a helix sweep of a single
profile, while maintaining geometric correctness. The sweep approach should produce
faster generation, cleaner topology, and smaller STEP files.

**Approach:** Build sweep as an experimental alternative alongside loft. Iterate until
automated tests confirm the sweep output matches the loft reference within tolerance.
Then pause for manual CAD inspection before promoting sweep to default.

---

## 2. Phase 1: Improve Thread Profile Tests

**Problem:** The current test suite (`test_worm.py`) only verifies that geometry is
valid and roughly the right size. It would not catch incorrect thread profiles, wrong
flank angles, or lead errors. These tests are needed regardless of the sweep work -
they close a blind spot.

### 2.1 Cross-Section Sampling Utility

Create a test utility that slices worm geometry at a given Z position and measures
thread profile dimensions.

**File:** `tests/helpers/geometry_sampling.py`

```python
def slice_worm_at_z(solid, z: float) -> Wire:
    """Slice a worm solid with an XY plane at the given Z coordinate.
    Returns the cross-section wire(s)."""

def measure_thread_profile(solid, z: float, pitch_radius: float) -> dict:
    """Measure thread profile dimensions from a cross-section.
    Returns:
        thread_thickness_at_pitch_mm: float
        addendum_mm: float  (tip radius - pitch radius)
        dedendum_mm: float  (pitch radius - root radius)
        tip_radius_mm: float
        root_radius_mm: float
    """

def measure_lead(solid, pitch_radius: float) -> float:
    """Measure actual lead by finding the thread tip at angle 0 deg
    and angle 360 deg, returning the Z distance between them."""
```

**Implementation approach:**
- Use `BRepAlgoAPI_Section` to intersect solid with XY plane at Z offset
- Extract resulting edges/wires
- Measure radial distances from axis (0,0) to characterise the profile
- For lead measurement: intersect with a half-plane (XZ plane, X>0) to get
  the helical edge, then sample two points one pitch apart

### 2.2 New Dimensional Tests

**File:** `tests/test_worm_dimensions.py` (new, marked slow)

```
test_thread_thickness_at_pitch_diameter
    Build standard worm (m=2.0, ratio=30, ZA profile)
    Slice at z=0
    Measure thread thickness at pitch radius
    Assert within 5% of design.worm.thread_thickness_mm

test_addendum_matches_design
    Measure tip_radius - pitch_radius from cross-section
    Assert within 5% of design.worm.addendum_mm

test_dedendum_matches_design
    Measure pitch_radius - root_radius from cross-section
    Assert within 5% of design.worm.dedendum_mm

test_lead_matches_design
    Measure actual lead from geometry
    Assert within 2% of design.worm.lead_mm

test_tip_diameter_matches_design
    Measure max radial extent from cross-section
    Assert within 0.1mm of design.worm.tip_diameter_mm / 2

test_root_diameter_matches_design
    Measure min radial extent (in thread region) from cross-section
    Assert within 0.1mm of design.worm.root_diameter_mm / 2

test_flank_angle_matches_pressure_angle  [ZA profile only]
    Measure angle of flank line from cross-section
    Assert within 1 degree of design.assembly.pressure_angle_deg

test_dimensions_across_modules
    Parametrize over module = [0.5, 1.0, 2.0, 5.0]
    Run thread thickness + addendum + lead checks for each
    Ensures dimensional accuracy across scales

test_dimensions_multi_start
    Build 2-start and 4-start worms
    Verify thread thickness and lead for each start
```

**Tolerances rationale:**
- 5% for profile dimensions: lofting with 36 sections introduces some interpolation
  error. This is tight enough to catch "profile is wrong" but loose enough to pass
  with the ruled-surface approximation.
- 2% for lead: lead is defined by the helix path directly, should be very accurate.
- 0.1mm for diameters: absolute tolerance matches manufacturing precision.
- 1 degree for flank angle: reasonable for a ruled surface approximation of a plane.

### 2.3 Verify Existing Loft Passes New Tests

Run the new dimensional tests against the current loft implementation at
`sections_per_turn=36` (default) and `sections_per_turn=72` (high quality).

If the loft at 36 sections fails any tolerance, either:
- Loosen the tolerance (document why), or
- Note it as a known limitation of the loft approach (sweep may do better)

This establishes the baseline.

---

## 3. Phase 2: Implement Sweep-Based Worm Generation

### 3.1 New Method in WormGeometry

Add `_create_single_thread_sweep()` alongside the existing `_create_single_thread()`
(which uses lofting). Selected via a parameter.

**File:** `src/wormgear/core/worm.py`

```python
class WormGeometry:
    def __init__(self, ..., generation_method: str = "loft"):
        """
        generation_method: "loft" (default, proven) or "sweep" (experimental)
        """
        self.generation_method = generation_method

    def _create_single_thread(self, angle_offset: float):
        if self.generation_method == "sweep":
            return self._create_single_thread_sweep(angle_offset)
        else:
            return self._create_single_thread_loft(angle_offset)
```

### 3.2 Sweep Implementation

```python
def _create_single_thread_sweep(self, angle_offset: float):
    """Create a single thread by sweeping one profile along a helix.

    Uses build123d sweep() with binormal mode to lock profile
    orientation radially (perpendicular to worm axis).
    """
    # 1. Create helix path
    helix = Helix(
        pitch=lead,
        height=extended_length,
        radius=pitch_radius,
        ...
    )

    # 2. Create single 2D thread profile at helix start point
    #    Position perpendicular to helix tangent at t=0
    #    Profile is the same trapezoid (ZA) or arc (ZK) used in loft

    # 3. Sweep with binormal control
    #    Set binormal to worm axis (0,0,1) to prevent profile roll
    #    build123d wraps OCC BRepOffsetAPI_MakePipeShell
    thread = sweep(profile_face, helix, binormal=Axis.Z)

    # 4. Trim to exact length (same cutting boxes as loft approach)

    return thread
```

**Key technical decisions:**
- **Binormal = Z axis**: locks the profile's radial orientation. The profile always
  points outward from the worm axis, regardless of position along the helix.
- **No end tapering initially**: sweep the full-depth profile and rely on the existing
  trim-to-length cutting boxes. If this creates sharp thread terminations, add chamfers
  as a post-processing step.
- **Same profile creation code**: reuse `_create_profile_za()` / `_create_profile_zk()`.
  Only the assembly method changes (sweep vs loft), not the profile definition.

### 3.3 Handle Known Risks

| Risk | Mitigation |
|------|-----------|
| Self-intersection at tight lead angles | Test with lead angles from 3 deg to 25 deg. If sweep fails for tight angles, fall back to loft automatically. |
| Profile roll despite binormal | Verify with cross-section test at multiple Z positions. If roll detected, try `transition=Transition.TRANSFORMED` or manual frame control. |
| Multi-start union failures | Each start is swept independently and unioned (same as loft). If union fails, try `BRepAlgoAPI_Fuse` with fuzzy tolerance. |
| Thread termination quality | Compare end faces between sweep and loft. If sweep ends are worse, add explicit end chamfers. |

### 3.4 CLI / API Exposure

Add `--generation-method loft|sweep` flag to CLI (default: loft). Not exposed in web
UI at this stage.

```python
# cli/generate.py
parser.add_argument('--generation-method',
    choices=['loft', 'sweep'],
    default='loft',
    help='EXPERIMENTAL: Worm thread generation method')
```

---

## 4. Phase 3: Comparison Testing

### 4.1 Sweep vs Loft Comparison Tests

**File:** `tests/test_worm_sweep.py` (new, marked slow)

```
test_sweep_produces_valid_solid
    Build worm with generation_method="sweep"
    Assert is_valid

test_sweep_volume_matches_loft
    Build same worm with both methods
    Reference: loft at sections_per_turn=72 (high quality)
    Assert volumes within 1%

test_sweep_bounding_box_matches_loft
    Assert all 3 axes within 0.1mm

test_sweep_cross_section_matches_loft
    Slice both at z=0
    Assert cross-section areas within 2%

test_sweep_thread_thickness_matches_loft
    Measure thread thickness at pitch diameter for both
    Assert within 3%

test_sweep_lead_matches_loft
    Measure lead for both
    Assert within 1%

test_sweep_passes_dimensional_tests
    Run the same dimensional tests from Phase 1 against sweep
    Same tolerances - sweep must meet the same spec as loft

test_sweep_across_parameters
    Parametrize: module=[0.5, 1.0, 2.0, 5.0], starts=[1, 2, 4],
                 hand=[right, left], profile=[ZA, ZK]
    Build with sweep, assert is_valid and volume within 2% of loft
    This is the comprehensive compatibility matrix

test_sweep_performance
    Time both methods for a standard worm (m=2.0, ratio=30)
    Log times (not a pass/fail assertion, just data collection)
    Expected: sweep significantly faster than loft
```

### 4.2 Iteration Loop

```
while sweep tests fail:
    1. Read failure details (which dimension is off, by how much)
    2. Diagnose root cause (profile orientation, sweep path, trimming)
    3. Fix the sweep implementation
    4. Re-run tests
    5. Commit with descriptive message

when all automated tests pass:
    STOP - do not promote sweep to default
    Export STEP files from both methods
    Return to Paul for manual CAD inspection
```

### 4.3 Artifacts for Manual Inspection

When all automated tests pass, generate comparison STEP files:

```bash
# Generate comparison pairs
wormgear design_m2_r30.json --generation-method loft -o comparison/loft/
wormgear design_m2_r30.json --generation-method sweep -o comparison/sweep/
```

Provide to Paul:
- `comparison/loft/worm_m2_z1.step`
- `comparison/sweep/worm_m2_z1.step`
- Test results summary (all tolerances met, actual vs expected values)
- Performance comparison (generation time)

**Paul reviews in CAD software:**
- Visual comparison of thread surfaces
- Cross-section overlay at multiple Z positions
- Thread termination quality at ends
- Surface continuity / smoothness
- STEP import quality in FreeCAD / Fusion 360

---

## 5. Phase 4: Promotion (After Manual Review)

Only after Paul confirms the sweep geometry looks correct:

1. Make sweep the default (`generation_method="sweep"`)
2. Keep loft as fallback (`generation_method="loft"`)
3. Add automatic fallback: if sweep raises an exception (self-intersection),
   retry with loft and log a warning
4. Remove `--generation-method` from CLI (or keep as hidden debug flag)
5. Update `sections_per_turn` documentation (no longer relevant for sweep,
   only for loft fallback)

---

## 6. Files Changed

### New Files
| File | Purpose |
|------|---------|
| `tests/helpers/geometry_sampling.py` | Cross-section slicing and measurement utilities |
| `tests/test_worm_dimensions.py` | Dimensional verification tests (Phase 1) |
| `tests/test_worm_sweep.py` | Sweep vs loft comparison tests (Phase 3) |

### Modified Files
| File | Change |
|------|--------|
| `src/wormgear/core/worm.py` | Add `_create_single_thread_sweep()`, `generation_method` parameter |
| `src/wormgear/cli/generate.py` | Add `--generation-method` flag |
| `tests/helpers/__init__.py` | New package init |

### Unchanged Files
- All calculator code (sweep is geometry-only)
- All web code (sweep not exposed in UI)
- All IO / schema code (no model changes)
- `globoid_worm.py` (globoid stays loft-only for now)

---

## 7. Success Criteria

### Phase 1 Complete When:
- [ ] Cross-section sampling utility works and is tested
- [ ] All dimensional tests pass against current loft implementation
- [ ] Baseline tolerances documented

### Phase 2 Complete When:
- [ ] Sweep generates a valid solid for the standard case (m=2.0, ratio=30, ZA, 1 start)
- [ ] CLI flag works

### Phase 3 Complete When:
- [ ] All comparison tests pass (volume, bbox, cross-section, thread thickness, lead)
- [ ] All dimensional tests pass for sweep (same tolerances as loft)
- [ ] Parameter matrix passes (multiple modules, starts, hands, profiles)
- [ ] STEP files generated for manual inspection
- [ ] **STOP and return to Paul for CAD review**

### Phase 4 Complete When:
- [ ] Paul confirms sweep geometry is correct via CAD inspection
- [ ] Sweep promoted to default with loft fallback
- [ ] Performance improvement documented

---

## 8. Open Questions

1. **Globoid worms** - should sweep be attempted for globoid too? The varying radius
   makes it harder. Recommend: leave globoid as loft-only for now, revisit later.

2. **ZK profile with sweep** - the convex flanks may interact differently with sweep
   vs loft. Need to test specifically. If ZK sweep is problematic, could default to
   loft for ZK only.

3. **Thread termination** - the current loft approach tapers thread depth to zero at
   the ends. With sweep, the thread ends abruptly at the cutting plane. Is this
   acceptable for manufacturing, or do we need explicit thread run-out geometry?

4. **Tolerance tightening** - if sweep produces more accurate geometry than loft
   (likely, since it's a continuous surface), should we tighten the dimensional test
   tolerances after promotion? This would prevent regression if someone switches back
   to loft.
