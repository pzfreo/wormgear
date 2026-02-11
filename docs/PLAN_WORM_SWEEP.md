# Worm Sweep Implementation Plan

**Author:** Claude (with Paul Fremantle)
**Date:** 2026-02-10
**Status:** Phases 1-3 coded, needs iteration in 3.12+ environment
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

## 2. Current State (2026-02-10)

### What's been implemented

All code for Phases 1-3 has been written and committed on the branch. However, the
initial coding session ran on Python 3.11 (project requires 3.12+) so **no tests have
been run yet**. The sweep implementation is a first attempt that will almost certainly
need iteration.

### Files already created/modified

| File | Status | Description |
|------|--------|-------------|
| `tests/helpers/__init__.py` | **NEW** | Package init |
| `tests/helpers/geometry_sampling.py` | **NEW** | Cross-section slicing, radial profile measurement, lead measurement, flank angle measurement |
| `tests/test_worm_dimensions.py` | **NEW** | Dimensional verification tests (tip/root diameters, lead, flank angle, multi-module, multi-start) |
| `tests/test_worm_sweep.py` | **NEW** | Sweep validity, sweep-vs-loft comparison, parameter matrix, performance timing |
| `scripts/generate_comparison_steps.py` | **NEW** | Generates loft/sweep STEP file pairs for CAD inspection |
| `src/wormgear/core/worm.py` | **MODIFIED** | Added `generation_method` param, `_create_single_thread_sweep()`, renamed loft method, fixed docstring |
| `src/wormgear/cli/generate.py` | **MODIFIED** | Added `--generation-method loft\|sweep` CLI flag |
| `.gitignore` | **MODIFIED** | Added `comparison/` |

### What needs to happen next

**A Claude instance running in a Python 3.12+ environment with build123d installed
must iterate on this code until all tests pass.** See Section 9 below for detailed
step-by-step instructions.

---

## 3. Phase 1: Improve Thread Profile Tests

**Problem:** The current test suite (`test_worm.py`) only verifies that geometry is
valid and roughly the right size. It would not catch incorrect thread profiles, wrong
flank angles, or lead errors.

### 3.1 Cross-Section Sampling Utility

**File:** `tests/helpers/geometry_sampling.py` (already created)

Key functions:
- `_sample_edges_at_z(solid, z)` — slices solid with XY plane via `BRepAlgoAPI_Section`, samples 50 points along each resulting edge
- `measure_radial_profile(solid, z)` — returns `max_radius`, `min_radius` from cross-section
- `measure_lead(solid, pitch_radius, worm_length)` — tracks thread tip angle at 60 Z slices, unwraps angles, linear-fits to get `lead = 2π / |slope|`
- `measure_flank_angle(solid, z, pitch_radius, addendum, dedendum)` — finds a tooth, bins flank edge points by radius, fits line to extract pressure angle
- `measure_thread_at_angle(solid, z, angle_deg, pitch_radius)` — measures thread tip/root radius at a specific angular position
- `measure_thread_thickness_at_z(solid, z, pitch_radius, num_starts)` — clusters points near pitch radius by angle, measures angular extent of each thread

### 3.2 Dimensional Tests

**File:** `tests/test_worm_dimensions.py` (already created, marked slow)

| Test class | Tests |
|------------|-------|
| `TestTipAndRootDiameters` | tip at z=0, root at z=0, tip at multiple Z positions |
| `TestLeadMeasurement` | right-hand lead, left-hand lead, multi-start lead |
| `TestDimensionsAcrossModules` | parametrized tip diameter and lead for m=1.0, 2.0, 5.0 |
| `TestFlankAngle` | ZA flank angle vs pressure angle (3° tolerance) |
| `TestMultiStart` | 2-start and 4-start validity, 2-start tip diameter |

**Tolerances:**
- 0.15mm absolute for tip/root radii (looser than plan's 0.1mm — loft at 36 sections may need this)
- 3% relative for lead (single start), 5% for multi-start
- 3° for flank angle (measurement method is approximate)

Uses a `_build_worm()` helper that calls `design_from_module()` + `WormGeometry()`.

### 3.3 Verify Existing Loft Passes New Tests

Run dimensional tests against current loft. If loft fails some tolerances, either
loosen them (document why) or note as known loft limitation.

---

## 4. Phase 2: Sweep Implementation

### 4.1 Architecture

**File:** `src/wormgear/core/worm.py`

- `WormGeometry.__init__()` now accepts `generation_method: Literal["loft", "sweep"] = "loft"`
- `_create_single_thread()` dispatches to loft or sweep
- `_create_single_thread_loft()` — the original loft code, **unchanged**
- `_create_single_thread_sweep()` — the new sweep implementation
- The `build()` method is **shared** — core union, trimming, repair, and features work identically for both methods

### 4.2 Current Sweep Implementation

The sweep method (lines 627-737 of `worm.py`) does:

1. **Creates helix path** at pitch radius (same as loft)
2. **Positions profile** at helix start point (`helix @ 0`), perpendicular to tangent (`helix % 0`), x_dir = radial outward
3. **Draws full-depth profile** — same trapezoid (ZA/ZI) or arc (ZK) as loft, but with no taper
4. **Calls `sweep(profile_face, path=helix, normal=(0, 0, 1))`** — the `normal` parameter is intended to lock the Z direction in the profile frame

**Key unknowns (needs testing):**
- Whether `normal=(0,0,1)` correctly locks radial orientation in build123d's sweep
- Whether the profile is correctly positioned on the helix path
- Whether the helix Wire from build123d's Helix works as a sweep path

### 4.3 CLI Flag

`--generation-method loft|sweep` in `src/wormgear/cli/generate.py`. Default: `loft`.

---

## 5. Phase 3: Comparison Testing

### 5.1 Sweep Tests

**File:** `tests/test_worm_sweep.py` (already created, marked slow)

| Test class | Tests | Tolerance |
|------------|-------|-----------|
| `TestSweepProducesValidSolid` | valid solid, positive volume, left-hand, ZK | volume > 0 |
| `TestSweepMatchesLoft` | volume, bounding box, tip radius, lead | 3% vol, 0.3mm bbox, 0.2mm tip, 2% lead |
| `TestSweepDimensionalAccuracy` | tip/root diameter, lead, consistency | Same as Phase 1 |
| `TestSweepAcrossParameters` | modules, starts, hands, profiles, comprehensive comparison | 5% volume |
| `TestSweepPerformance` | timing (informational) | No assertions |

### 5.2 Comparison STEP Generation

**Script:** `scripts/generate_comparison_steps.py`

```bash
python scripts/generate_comparison_steps.py        # Single config (m=2.0, r=30)
python scripts/generate_comparison_steps.py --all   # Full matrix (6 configs)
```

Output: `comparison/loft/*.step` and `comparison/sweep/*.step` (gitignored)

---

## 6. Phase 4: Promotion (After Manual Review)

Only after Paul confirms the sweep geometry looks correct:

1. Make sweep the default (`generation_method="sweep"`)
2. Keep loft as fallback (`generation_method="loft"`)
3. Add automatic fallback: if sweep raises an exception, retry with loft and log a warning
4. Remove `--generation-method` from CLI (or keep as hidden debug flag)
5. Update `sections_per_turn` documentation (no longer relevant for sweep)

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

1. **Globoid worms** — leave as loft-only for now. Varying radius makes sweep fundamentally different.

2. **ZK profile with sweep** — the convex flanks may interact differently with sweep.
   If problematic, fall back to loft for ZK only.

3. **Thread termination** — sweep ends abruptly at cutting plane (no taper). This is
   fine for CNC and 3D printing. The loft's cosine taper is in the trim zone anyway.

4. **Tolerance tightening** — if sweep is more accurate than loft, tighten tolerances
   after promotion and document that loft fallback may not meet the tighter spec.

5. **`normal` vs `binormal` vs direct OCC** — the current implementation uses
   `sweep(..., normal=(0,0,1))`. Multiple fallback approaches are documented in
   Section 9 Step 2 if this doesn't work.

---

## 9. ITERATION INSTRUCTIONS (For next Claude instance)

**Context:** The code below was written without being able to run it (Python 3.11
environment, project needs 3.12+). You are now in a 3.12+ environment with build123d.
**Your job is to iterate until all tests pass.**

### Step 0: Verify environment and install

```bash
python --version                          # Must be 3.12+
pip install -e ".[dev]"                   # Install wormgear with dev deps
python -c "from build123d import sweep, Helix; print('OK')"
```

### Step 1: Run Phase 1 tests first (loft baseline)

```bash
pytest tests/test_worm_dimensions.py -v 2>&1 | head -80
```

**If geometry sampling tests fail:** The `tests/helpers/geometry_sampling.py` utilities
were written without running them. Common issues:

- **`_sample_edges_at_z` returns empty list** — `BRepAlgoAPI_Section` may need the
  shape unwrapped differently, or the plane construction needs adjustment. Debug:
  ```python
  from tests.helpers.geometry_sampling import _sample_edges_at_z
  from wormgear.calculator.core import design_from_module
  from wormgear import WormGeometry
  design = design_from_module(module=2.0, ratio=30)
  geo = WormGeometry(params=design.worm, assembly_params=design.assembly, length=40.0)
  solid = geo.build()
  pts = _sample_edges_at_z(solid, z=0.0)
  print(f"Points: {len(pts)}")  # Should be several hundred
  ```

- **`measure_lead` returns None** — the angle tracking and unwrapping may have bugs.
  Check that `measure_radial_profile` works first (simpler). Then debug lead by
  printing the raw z_values and peak_angles arrays.

- **`measure_flank_angle` returns None or wrong value** — this is the most complex
  measurement. It may need tuning. If consistently wrong, loosen tolerance to 5° or
  skip with `pytest.skip("flank angle measurement needs calibration")`.

- **Tolerances too tight for loft** — if loft at 36 sections fails, loosen the
  tolerance and add a comment like:
  ```python
  # Loosened to 0.25mm: loft at 36 sections has interpolation error at this scale
  assert profile["max_radius"] == pytest.approx(expected_tip_r, abs=0.25)
  ```

**Fix the sampling utilities and/or tolerances until all loft dimensional tests pass.**
This establishes the baseline. Commit: `fix: Phase 1 dimensional tests baseline for loft`

### Step 2: Run sweep basic test

```bash
pytest tests/test_worm_sweep.py::TestSweepProducesValidSolid::test_sweep_valid_solid -v -s
```

**The sweep will very likely fail on the first run.** Here are the probable causes and
fixes, in order of likelihood:

#### Problem A: `sweep()` doesn't accept `normal` parameter as expected

build123d's `sweep` signature is:
```python
sweep(sections, path, multisection=False, is_frenet=False,
      transition=Transition.TRANSFORMED, normal=None, binormal=None, clean=True, mode=Mode.ADD)
```

`normal: VectorLike | None` — a fixed direction. `binormal: Edge | Wire | None` — an auxiliary spine.

If `normal=(0,0,1)` doesn't work (wrong orientation, crash, etc.), try in order:

```python
# Alternative A: Frenet frame (simplest, may work for smooth helix)
thread = sweep(profile_face, path=helix, is_frenet=True)

# Alternative B: binormal edge (Z-axis line as auxiliary spine)
from build123d import Edge
z_line = Edge.make_line((0, 0, -extended_length), (0, 0, extended_length))
thread = sweep(profile_face, path=helix, binormal=z_line)

# Alternative C: Different transition mode
from build123d import Transition
thread = sweep(profile_face, path=helix, normal=(0, 0, 1),
               transition=Transition.ROUND)

# Alternative D: Direct OCC (most control, bypasses build123d wrapper)
from OCP.BRepOffsetAPI import BRepOffsetAPI_MakePipeShell
from OCP.gp import gp_Dir
from OCP.TopoDS import TopoDS

# Get the Wire from the helix
helix_wire = helix.wrapped  # or helix.edge().wrapped depending on type

pipe = BRepOffsetAPI_MakePipeShell(helix_wire)
pipe.SetMode(gp_Dir(0, 0, 1))  # Fixed binormal direction = Z axis
# Add the profile (must be a Wire, not Face)
profile_wire = profile_face.outer_wire().wrapped
pipe.Add(profile_wire)
pipe.Build()
if pipe.IsDone():
    pipe.MakeSolid()
    thread = Part(pipe.Shape())
```

#### Problem B: Profile not on the helix path

build123d requires the profile to lie on the sweep path. Verify:
```python
start_point = helix @ 0
print(f"Helix start: ({start_point.X:.3f}, {start_point.Y:.3f}, {start_point.Z:.3f})")
# Should be at (pitch_radius, 0, -extended_length/2) for start_angle=0
```

If the profile isn't coincident with the path start, the sweep will fail.

#### Problem C: Profile orientation wrong

The profile plane must be perpendicular to the helix tangent at t=0:
```python
tangent = helix % 0
print(f"Tangent: ({tangent.X:.3f}, {tangent.Y:.3f}, {tangent.Z:.3f})")
# For a right-hand helix starting on +X axis, tangent should be roughly
# (0, +Y_component, +Z_component) — pointing along the helix direction
```

If orientation is wrong, the swept solid will be inside-out or self-intersecting.
You may need to swap x_dir/z_dir or negate them.

#### Problem D: Self-intersection

For small modules or large lead angles, the swept profile may self-intersect.
Test first with a large, gentle case:
```python
# Easy case: large module, small lead angle
solid, design = _build_worm("sweep", module=5.0, ratio=30, length=100.0)
# If this works but smaller modules fail, the issue is profile-to-helix-radius ratio
```

### Step 3: Iterate on sweep

Once the basic sweep produces *something*, run comparison tests:

```bash
pytest tests/test_worm_sweep.py -v -s 2>&1 | head -120
```

**Common failure modes and fixes:**

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Volume way too large (2x+) | Profile oriented wrong, sweeping outward | Check profile plane x_dir/z_dir assignment |
| Volume way too small (<50%) | Profile facing inward toward axis | Negate radial_dir or swap inner_r/outer_r |
| Volume ~right but `is_valid=False` | Self-intersection at thread overlap | Try `clean=True` (default), or reduce extended_length |
| Lead measurement wrong | Profile rolling despite normal param | Try binormal edge approach (Alternative B) |
| Bounding box Z wrong | Trim-to-length not working on sweep solid | Check if `BRepAlgoAPI_Cut` works on sweep shape |
| Multi-start fails | Union of two sweep solids fails | Use `BRepAlgoAPI_Fuse` with fuzzy tolerance (already in `build()`) |
| ZK profile fails but ZA works | Spline tangency issues with sweep | Increase num_points to 15, or fall back to loft for ZK |
| Exception in `sweep()` | Many possible causes | Read the exception carefully; try Alternative D (direct OCC) |

### Step 4: Fix geometry sampling utilities if needed

The measurement utilities may also need debugging. Priority order:

1. **`measure_radial_profile`** — simplest, must work first. Returns max/min radius.
2. **`measure_lead`** — second priority. The linear regression approach should work but
   the angle unwrapping may have edge cases.
3. **`measure_flank_angle`** — least critical. If it can't be made reliable, add a
   generous tolerance or skip with a TODO comment.

### Step 5: When all tests pass

```bash
# Run all new tests
pytest tests/test_worm_dimensions.py tests/test_worm_sweep.py -v

# Verify no regressions in existing worm tests
pytest tests/test_worm.py -v

# Generate comparison STEP files
python scripts/generate_comparison_steps.py --all
```

Commit with descriptive message, push:
```bash
git add -A
git commit -m "fix: Iterate sweep implementation to pass all Phase 3 tests

[Describe what changed and why for each fix]"
git push -u origin claude/review-docs-sweep-plan-H1xfL
```

Then **STOP**. Do not promote sweep to default. Tell Paul:
- All automated tests pass (report pass/fail counts)
- Comparison STEP files are in `comparison/loft/` and `comparison/sweep/`
- Report any tolerance loosening with reasons
- Report performance numbers from `TestSweepPerformance`
- List any known issues or caveats

### Important constraints during iteration

- **Do NOT modify `_create_single_thread_loft()`** — proven code, must stay unchanged
- **Do NOT modify `build()`** — shared logic for core union, trimming, repair, features
- **Do NOT weaken test tolerances without a comment explaining why**
- **Do NOT promote sweep to default** — that's Phase 4 (Paul's decision after CAD review)
- **Do NOT change existing tests** in `test_worm.py`, `test_integration.py`, etc.
- **Keep commits descriptive** — each iteration should explain what failed and what changed
- **If sweep fundamentally can't work with build123d's `sweep()`**, try the direct OCC
  `BRepOffsetAPI_MakePipeShell` approach (Alternative D in Step 2). This gives full control
  over the pipe shell construction and is how production CAD kernels create helical sweeps.
