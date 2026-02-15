# DRY Remediation Plan

## Context

Codebase audit revealed significant DRY violations across Python geometry code, JavaScript web UI, and test fixtures. These cause maintenance burden (fixes needed in multiple places), inconsistencies (slightly different text/behavior between copies), and increased risk of bugs when one copy is updated but others aren't.

Prioritized by impact (how many duplicates × how often the code changes).

---

## Phase 1: Python Geometry Utilities (HIGH impact)

Extract repeated patterns from `core/worm.py`, `core/globoid_worm.py`, `core/wheel.py` into shared utilities.

### 1a. Create `src/wormgear/core/profile.py` — Profile sketch generation

The ZA/ZK/ZI profile creation code (BuildSketch + BuildLine + make_face) is duplicated ~15 times across worm.py (thread loft, thread sweep, groove sweep), wheel.py (tooth space), and globoid_worm.py. Extract into:

```python
def create_tooth_profile(
    profile_plane: Plane,
    inner_r: float, outer_r: float,
    half_width_inner: float, half_width_outer: float,
    profile: WormProfile,
    module_mm: float,
) -> Face:
    """Create a tooth/groove cross-section face on the given plane."""

def create_zk_flanks(
    inner_r: float, outer_r: float,
    half_width_inner: float, half_width_outer: float,
    module_mm: float, num_points: int = 9,
) -> tuple[list, list]:
    """Generate ZK arc flank point lists. Returns (left_flank, right_flank)."""
```

Also define: `ZK_ARC_RADIUS_FACTOR = 0.45` (currently hardcoded 5 times).

**Files to modify**: `core/worm.py`, `core/wheel.py`, `core/globoid_worm.py`

### 1b. Add taper utility to `core/geometry_base.py`

Cosine-ramped taper calculation duplicated 7+ times:

```python
@staticmethod
def calculate_taper_factor(z: float, half_width: float, taper_length: float) -> float:
    """Cosine-ramped taper factor for thread end tapering."""
```

**Files to modify**: `core/worm.py`, `core/globoid_worm.py`

### 1c. Add OCC boolean helpers to `core/geometry_repair.py`

The wrap-unwrap-fuse/cut-check-fallback pattern appears 5+ times:

```python
def occ_fuse(shape1: Part, shape2: Part) -> Part:
    """OCC boolean fuse with build123d fallback."""

def occ_cut(shape1: Part, shape2: Part) -> Part:
    """OCC boolean cut with error logging."""
```

**Files to modify**: `core/worm.py`, `core/globoid_worm.py`, `core/features.py`

### 1d. Move `_extract_single_solid` and `_create_profile_plane` to `BaseGeometry`

Currently only in `WormGeometry` but needed by `GloboidWormGeometry` too.

**Files to modify**: `core/geometry_base.py`, `core/worm.py`, `core/globoid_worm.py`

---

## Phase 2: JavaScript Shared Utilities (MEDIUM-HIGH impact)

### 2a. Create `web/modules/format-utils.js`

Extract from `app.js` (×2) and `generator-ui.js`:

```javascript
export const fmt = (val, d = 2) => val != null ? Number(val).toFixed(d) : '—';
export const fmtMm = (val, d = 2) => val != null ? `${Number(val).toFixed(d)} mm` : '—';
export const fmtDeg = (val, d = 1) => val != null ? `${Number(val).toFixed(d)}°` : '—';

export const PROFILE_LABELS = {
    'ZA': 'ZA (straight flanks)',
    'ZK': 'ZK (convex flanks)',
    'ZI': 'ZI (involute)'
};

export function base64ToUint8Array(base64) { ... }

export function formatBoreFeature(features, partName, fmtFn = fmt) { ... }
```

**Files to modify**: `web/app.js`, `web/modules/generator-ui.js`, `web/modules/viewer-3d.js`

### 2b. Extract spec sheet data builder

`app.js` builds spec sheet data rows identically for HTML rendering and PDF export. Extract the row-building logic (which rows to include based on design params) into a shared function, leaving only the rendering (HTML vs PDF) as separate code.

**Files to modify**: `web/app.js`

---

## Phase 3: Test Fixture Consolidation (MEDIUM impact)

### 3a. Consolidate parameter fixtures in `tests/conftest.py`

`worm_params`, `wheel_params`, and `assembly_params` are copy-pasted into 5-7 test files (9+ total copies). All create identical objects from `sample_design_7mm`.

**Fix**: Add properly-scoped shared fixtures to `conftest.py` and delete the copies from individual test files. Use `"class"` scope for geometry tests (which need fresh objects per class).

**Files to modify**: `tests/conftest.py`, `tests/test_worm.py`, `tests/test_wheel.py`, `tests/test_globoid_worm.py`, `tests/test_virtual_hobbing.py`, `tests/test_features.py`

### 3b. Share test helpers from `test_full_pipeline.py`

Move `_assert_valid_part()` and `_assert_step_roundtrip()` to `conftest.py` for use by `test_integration.py` and other geometry test files.

### 3c. Add CLI subprocess helper

```python
# conftest.py
def run_wormgear_cli(*args, timeout=120):
    return subprocess.run(
        [sys.executable, "-m", "wormgear.cli.generate"] + list(args),
        capture_output=True, text=True, timeout=timeout
    )
```

Replace 10+ copies in `test_cli.py`.

---

## Files Summary

| File | Action |
|------|--------|
| `src/wormgear/core/profile.py` | **CREATE** — shared profile sketch generation |
| `src/wormgear/core/geometry_base.py` | **MODIFY** — add taper, extract_solid, profile_plane |
| `src/wormgear/core/geometry_repair.py` | **MODIFY** — add occ_fuse/occ_cut helpers |
| `src/wormgear/core/worm.py` | **MODIFY** — use shared utilities |
| `src/wormgear/core/wheel.py` | **MODIFY** — use shared profile |
| `src/wormgear/core/globoid_worm.py` | **MODIFY** — use shared utilities |
| `src/wormgear/core/features.py` | **MODIFY** — use occ_cut helper |
| `web/modules/format-utils.js` | **CREATE** — shared JS formatting |
| `web/app.js` | **MODIFY** — use format-utils |
| `web/modules/generator-ui.js` | **MODIFY** — use format-utils |
| `web/modules/viewer-3d.js` | **MODIFY** — use base64ToUint8Array |
| `tests/conftest.py` | **MODIFY** — add shared fixtures + helpers |
| `tests/test_worm.py` | **MODIFY** — remove local fixtures |
| `tests/test_wheel.py` | **MODIFY** — remove local fixtures |
| `tests/test_globoid_worm.py` | **MODIFY** — remove local fixtures |
| `tests/test_virtual_hobbing.py` | **MODIFY** — remove local fixtures |
| `tests/test_features.py` | **MODIFY** — remove local fixtures |
| `tests/test_cli.py` | **MODIFY** — use CLI helper |

---

## Verification

```bash
# All tests must pass (geometry tests exercise the refactored code)
pytest -m "not slow" -q    # Fast tests (~7s)
pytest tests/test_worm.py tests/test_wheel.py tests/test_features.py -q  # Geometry tests

# Web: visual check that spec sheet, PDF export, ZIP download still work
# No functional changes — only code organization
```

## What's NOT included (and why)

- **Hourglass radius calculation** (globoid_worm.py only) — 4 copies but all in one file, low change frequency, extraction would add indirection for little benefit
- **Enum generation from schema for JS** — already has schema-first workflow; the JS constants in schema-validator.js are a conscious validation layer, not accidental duplication
- **Temp file pattern abstraction** — already addressed by `normalize_geometry()` and `export_part_*()` in package.py; remaining uses are one-liners
