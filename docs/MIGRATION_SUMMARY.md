# Migration Plan - Executive Summary

## Goal
Transform worm-gear-3d into unified `wormgear` package by merging calculator (from wormgearcalc) and geometry generator.

## Timeline
**2-3 weeks** (can be done incrementally)

---

## Key Decisions Needed

### 1. Package Name
**Recommended**: `wormgear` (shorter, cleaner)
- Old: `pip install wormgear-geometry`
- New: `pip install wormgear`

### 2. Backwards Compatibility
**Recommended**: Maintain with deprecation warnings
- Old imports still work in v1.x
- Warnings guide users to new imports
- Clean break in v2.0

### 3. Calculator Port Scope
**Recommended**: Start minimal, expand later
- **v1.0**: Basic ratio calculator (module, ratio → JSON)
- **v1.1**: Advanced features (globoid optimization, etc.)

### 4. Merge Repos
**Recommended**: Yes, merge wormgearcalc into this repo
- Single source of truth
- Easier maintenance
- No version coordination issues

**Alternative**: Keep separate, improve integration
- Less migration work
- More coordination overhead

---

## Architecture Overview

```
wormgear/
  core/          # Pure geometry (existing code, reorganized)
  calculator/    # New: ported from wormgearcalc JS → Python
  io/            # JSON schema, loaders (existing, enhanced)
  cli/           # Two commands: calculate, generate
```

**Layer 1**: Core (pure geometry, no JSON)
**Layer 2**: Calculator + IO (JSON handling)
**Layer 3**: CLI (user interfaces)

---

## Critical Risks

### Risk 1: JavaScript → Python Translation Errors
**Probability**: Medium | **Impact**: HIGH

**Issue**: Calculator logic might be ported incorrectly

**Mitigation**:
- Port unit tests from wormgearcalc
- Test against known good designs
- Cross-validate with DIN 3975 standards
- Manual review by you

**Validation**: Need wormgearcalc test suite or reference outputs

### Risk 2: Breaking Changes for Users
**Probability**: HIGH | **Impact**: Medium

**Issue**: Existing users' code breaks

**Mitigation**:
- Backwards compatibility shims (v1.x)
- Clear migration guide
- Deprecation warnings (not errors)
- Version bump to 1.0.0

### Risk 3: Import Circular Dependencies
**Probability**: Medium | **Impact**: HIGH

**Issue**: New structure creates circular imports

**Mitigation**:
- Strict dependency ordering
- Careful testing
- TYPE_CHECKING for type hints

---

## What Gets Ported from wormgearcalc

### Must Port
- [ ] Core calculation functions (pitch diameter, centre distance, etc.)
- [ ] DIN 3975 constraints (module ranges, tooth counts)
- [ ] Input validation
- [ ] Basic cylindrical worm calculator

### Should Port
- [ ] Globoid throat calculations
- [ ] Recommended dimensions (length, width)
- [ ] Engineering documentation

### Nice to Have (v1.1+)
- [ ] Interactive mode
- [ ] Preset configurations
- [ ] Advanced optimizations

---

## New Directory Structure

```
wormgear/                        # Renamed from wormgear_geometry
├── core/                        # Layer 1: Pure geometry
│   ├── worm.py                  # Existing (moved)
│   ├── wheel.py                 # Existing (moved)
│   ├── parameters.py            # Extracted from io.py
│   └── features.py              # Existing (moved)
│
├── calculator/                  # Layer 2a: NEW (from wormgearcalc)
│   ├── solver.py                # Calculate params from inputs
│   ├── constraints.py           # DIN 3975 standards
│   ├── validation.py            # Input validation
│   └── recommendations.py       # Auto-calculate lengths, etc.
│
├── io/                          # Layer 2b: Enhanced existing
│   ├── loaders.py               # load_design_json (existing)
│   ├── schema.py                # JSON schema (existing)
│   └── exporters.py             # NEW: specs, reports
│
└── cli/                         # Layer 3: NEW structure
    ├── calculate.py             # NEW: Calculator CLI
    ├── generate.py              # OLD cli.py (renamed)
    └── main.py                  # Unified entry point
```

---

## New CLI Commands

### Old (still works)
```bash
wormgear-geometry design.json
```

### New (preferred)
```bash
# Calculate parameters
wormgear calculate --module 2.0 --ratio 30 --output design.json

# Generate 3D models
wormgear generate design.json

# Validate design
wormgear validate design.json
```

---

## Migration Phases

### Week 1: Foundation
- Create new directory structure
- Move existing code to core/
- Update import paths (with backwards compat)
- No new functionality yet

**Risk**: Low (reorganization only)

### Week 2: Port Calculator
- Clone wormgearcalc
- Port JS → Python (solver, constraints, validation)
- Port tests
- Create calculator CLI

**Risk**: HIGH (translation errors)

### Week 3: Integration & Polish
- Unified CLI
- Documentation updates
- Integration tests
- Migration guide

**Risk**: Medium (compatibility issues)

---

## Testing Strategy

### During Port
```bash
# Unit test each module as ported
pytest tests/calculator/test_solver.py -v
```

### Before Release
```bash
# Full test suite
pytest tests/ --cov=wormgear --cov-report=html
# Goal: >85% coverage

# Test all examples
./scripts/test_examples.sh

# Test backwards compatibility
python -c "from wormgear_geometry import WormGeometry"
```

### Validation Against wormgearcalc
```python
# Test against known good designs
REFERENCE_DESIGNS = [
    {
        "input": {"module": 2.0, "ratio": 30},
        "expected": {"worm_pitch_diameter": 16.29, ...}
    },
    # ... from wormgearcalc examples
]
```

---

## Success Criteria

### Must Have (v1.0 Launch)
- [ ] All existing geometry features working
- [ ] Basic calculator working (module + ratio → JSON)
- [ ] Both CLI commands working
- [ ] Test coverage >80%
- [ ] Zero errors on fresh install
- [ ] Migration guide

### Should Have
- [ ] Calculator with globoid support
- [ ] Test coverage >90%
- [ ] Backwards compatibility shims
- [ ] Engineering docs ported

### Can Defer to v1.1
- [ ] Interactive calculator mode
- [ ] Advanced optimizations
- [ ] Web interface (WASM)

---

## Questions for You

### 1. Access to wormgearcalc
Do you have:
- [ ] Test suite with expected outputs?
- [ ] Reference designs we can validate against?
- [ ] List of must-have features?

### 2. Users
- [ ] Are there existing users we should notify?
- [ ] Any critical use cases we must not break?
- [ ] Preferred migration timeline?

### 3. Calculator Features
Which to prioritize?
- [ ] Basic cylindrical calculator (module, ratio, centre distance)
- [ ] Globoid calculations (throat geometry)
- [ ] Recommendations (length, width auto-calculation)
- [ ] Interactive mode
- [ ] Preset configurations

### 4. Breaking Changes
Preference?
- **Option A**: Maintain backwards compat with deprecation warnings (recommended)
- **Option B**: Clean break, no legacy support

### 5. Repository
- [ ] Archive wormgearcalc after merge?
- [ ] Keep wormgearcalc for web UI only?
- [ ] Deprecate wormgearcalc entirely?

---

## Contingency Plans

### If Calculator Port Too Complex
**Fallback**: Keep wormgearcalc separate
- Improve JSON integration
- Document workflow: wormgearcalc → JSON → wormgear
- Less work, more coordination

### If Timeline Slips
**Phased Rollout**:
- v0.9: Just reorganization (no calculator)
- v1.0: Add calculator
- v1.1: Web interface

---

## Next Steps (After Your Approval)

1. Answer questions above
2. Review/modify migration plan
3. Approve to proceed
4. I'll create branch: `feature/unified-package`
5. Start Phase 1 (foundation setup)

---

## Approval Checklist

- [ ] Package name approved: `wormgear`
- [ ] Backwards compatibility approach approved
- [ ] Calculator port scope defined
- [ ] Repository merge approved
- [ ] Timeline acceptable (2-3 weeks)
- [ ] Risk mitigations acceptable
- [ ] Questions answered
- [ ] Ready to begin implementation

**Approve?** Reply with any modifications or concerns.
