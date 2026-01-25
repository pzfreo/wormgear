# Migration Status - Unified Wormgear Package

**Started**: 2026-01-25
**Branch**: `feature/unified-package`
**Status**: 🟢 IN PROGRESS - Phase 1

---

## Decisions Made

✅ **Package name**: `wormgear` (was: wormgear-geometry)
✅ **Merge repos**: wormgearcalc → wormgear
✅ **Backwards compatibility**: Maintain with deprecation warnings in v1.x
✅ **Calculator scope**: Full port (all 4 design modes + globoid)
✅ **Web app**: Redirect old to new (no need to maintain both)
✅ **Timeline**: 12-15 days over 2-3 weeks

---

## Phase 1: Foundation (Days 1-2) - 🟢 IN PROGRESS

### 1.1 Create Directory Structure ✅ COMPLETE
- [x] Create `src/wormgear/core/`
- [x] Create `src/wormgear/calculator/`
- [x] Create `src/wormgear/io/`
- [x] Create `src/wormgear/cli/`
- [x] Create `__init__.py` files
- [x] Update `pyproject.toml` (package name, version, entry points)

### 1.2 Move Existing Code to core/ ✅ COMPLETE
- [x] Move `worm.py` → `core/worm.py`
- [x] Move `wheel.py` → `core/wheel.py`
- [x] Move `globoid_worm.py` → `core/globoid_worm.py`
- [x] Move `virtual_hobbing.py` → `core/virtual_hobbing.py`
- [x] Move `features.py` → `core/features.py`
- [x] Update all imports in moved files
- [x] Delete old `src/wormgear_geometry/` directory
- [ ] Create `core/parameters.py` (extract from io.py) - DEFERRED
- [ ] Create `core/validation.py` (new) - DEFERRED
- [ ] Create `core/profiles.py` (new) - DEFERRED

### 1.3 Reorganize io/ Module ✅ COMPLETE
- [x] Move `io.py` → `io/loaders.py`
- [x] Move `calculations/schema.py` → `io/schema.py`
- [x] Update imports in io/ files
- [ ] Create `io/exporters.py` (new) - DEFERRED
- [ ] Create `io/validators.py` (new) - DEFERRED

### 1.4 Update Tests ✅ COMPLETE
- [x] Update all test files to use new imports
- [x] Verify imports work correctly
- [ ] Fix failing ManufacturingParams tests (2 failures)

### 1.5 Reorganize CLI
- [x] Move `cli.py` → `cli/generate.py`
- [ ] Create `cli/calculate.py` (new - from wormgearcalc)
- [ ] Create `cli/main.py` (unified entry point)

---

## Phase 2: Port Calculator (Days 3-7) - 🟢 IN PROGRESS

### 2.1 Port Core Calculations ✅ COMPLETE
- [x] Port `calculate_worm()` from wormgearcalc
- [x] Port `calculate_wheel()` from wormgearcalc
- [x] Port `design_from_module()` - PRIORITY 1
- [x] Port `design_from_wheel()`
- [x] Port `design_from_centre_distance()`
- [x] Port `calculate_globoid_throat_radii()`
- [x] Port helper functions (efficiency, recommendations)
- [x] Create wrapper functions returning WormGearDesign
- [x] Test basic calculations work
- [x] Export from wormgear top-level

### 2.2 Port Additional Design Functions ✅ COMPLETE
(All functions ported in 2.1)

### 2.3 Port Globoid Support ✅ COMPLETE
(Globoid calculations included in 2.1)
- [x] Globoid throat radii calculation
- [x] Throat reduction support in all design functions

### 2.4 Port Validation
- [ ] Port all validation rules
- [ ] Test against test_validation.py cases

### 2.5 Port Tests
- [ ] Copy test cases from wormgearcalc
- [ ] Adapt to wormgear structure

---

## Phase 3: Integration (Days 8-11) - 🔴 NOT STARTED

### 3.1 Create Unified CLI
- [ ] Implement calculator CLI
- [ ] Update generator CLI
- [ ] Create main entry point
- [ ] Test end-to-end workflow

### 3.2 Update Documentation
- [ ] Update README.md
- [ ] Create migration guide
- [ ] Update API documentation
- [ ] Update examples

### 3.3 Testing & Polish
- [ ] Integration tests
- [ ] Backwards compatibility tests
- [ ] Update pyproject.toml
- [ ] Final code review

---

## Phase 4: Release (Days 12-15) - 🔴 NOT STARTED

### 4.1 Pre-Release
- [ ] All tests passing
- [ ] Documentation complete
- [ ] Version bump to 1.0.0
- [ ] CHANGELOG.md

### 4.2 Release
- [ ] Tag v1.0.0
- [ ] GitHub release
- [ ] PyPI upload
- [ ] Archive wormgearcalc repo

### 4.3 Post-Release
- [ ] Update wormgearcalc README (redirect)
- [ ] Update web app with redirect
- [ ] Announce on GitHub

---

## Progress Log

### 2026-01-25 - Day 1
- ✅ Created comprehensive migration plan
- ✅ Analyzed wormgearcalc repository
- ✅ Made key decisions with user
- ✅ Created feature branch: `feature/unified-package`
- ✅ Phase 1.1: Created new directory structure
- ✅ Phase 1.2: Moved all existing code to new structure
- ✅ Phase 1.3: Updated all test imports
- ✅ Phase 1.4: Fixed test failures (all tests passing)
- ✅ Phase 2.1: Ported core calculator functions
  - Created calculator/core.py with all design functions
  - Created wrapper functions returning WormGearDesign
  - Exported from top-level wormgear module
  - All calculations tested and working
  - Field naming adapted to wormgear conventions (_mm, _deg suffixes)
- 🟢 Ready for Phase 2.4: Port Validation or Phase 2.5: Port Tests

---

## Next Steps

1. Create `__init__.py` files for all new modules
2. Update `pyproject.toml` with new package structure
3. Move existing geometry code to `core/`
4. Create backwards compatibility shims

---

## Questions / Blockers

None currently.

---

## Notes

- Web app decision: Redirect old wormgearcalc web app to new unified wormgear web app (no need to maintain both)
- Timeline revised to 12-15 days based on wormgearcalc analysis
- Low risk migration - pure Python, well-tested, compatible dataclasses
