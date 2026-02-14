# Technical Debt Remediation Plan
## High-Impact Issues - Incremental Approach

*Target: Address critical issues while maintaining 100% backward compatibility and zero regressions*

---

## Phase 1: Safety Net (Week 1) - **MANDATORY FIRST**

### 1.1 Enhance Test Coverage for Validation Logic
**Goal**: Ensure we can detect regressions before making changes

**Tasks**:
- [ ] Add integration tests for bore validation (all 3 paths)
- [ ] Add tests covering exception handling paths in geometry
- [ ] Add performance baseline tests (geometry generation times)
- [ ] Document current test coverage baseline

**Acceptance Criteria**:
```bash
# Must pass before any refactoring
pytest --cov=wormgear.calculator.validation --cov-report=term-missing
# Target: >90% coverage of validation.py
pytest -m "not slow" -x  # All fast tests pass
pytest tests/test_integration_*.py  # New integration tests pass
```

**Estimated Effort**: 6-8 hours

**Risk**: Low - only adding tests, no production code changes

---

## Phase 2: Exception Handling Cleanup (Week 2)

### 2.1 Audit and Categorize All Exception Handlers
**Goal**: Document why each broad exception exists before fixing

**Tasks**:
- [ ] Create exception audit report (`scripts/audit_exceptions.py`)
- [ ] Categorize each `except Exception` as:
  - **Type A**: Geometry repair fallback (expected)
  - **Type B**: Should catch specific exception (bug risk)
  - **Type C**: Unclear - needs investigation
- [ ] Add TODO comments with rationale for each Type A

**Deliverable**: `EXCEPTION_AUDIT.md` with categorized list

**Estimated Effort**: 3-4 hours

### 2.2 Fix Type B Exceptions (Safest First)
**Goal**: Replace obvious broad exceptions with specific ones

**Tasks**:
- [ ] Replace `except Exception` with specific exceptions where obvious:
  - File I/O operations → `OSError`, `FileNotFoundError`
  - JSON operations → `JSONDecodeError`
  - Math operations → `ValueError`, `ZeroDivisionError`
- [ ] Add tests for each specific exception path
- [ ] Keep Type A (geometry repair) unchanged for now

**Acceptance Criteria**:
- All existing tests still pass
- New specific exception tests pass
- No change in public API behavior

**Estimated Effort**: 4-6 hours

**Risk**: Low-Medium - only changing obviously wrong exceptions

---

## Phase 3: Validation Logic Consolidation (Week 3)

### 3.1 Extract Common Validation Patterns
**Goal**: Create reusable validation helpers without changing behavior

**Tasks**:
- [ ] Create `src/wormgear/calculator/validation_helpers.py`
- [ ] Extract `_normalize_enum()` generic helper
- [ ] Extract `_validate_rim_thickness()` generic helper
- [ ] Add comprehensive tests for extracted functions

**Implementation Strategy**:
```python
# New file: validation_helpers.py
def validate_rim_thickness(
    part_name: str,
    bore_diameter: float,
    root_diameter: float,
    keyway_depth: float = 0.0,
    min_rim: float = MIN_RIM_WHEEL,
    warn_rim: float = WARN_RIM_WHEEL
) -> List[ValidationMessage]:
    """Generic rim thickness validator - extracted from duplicate code."""
    # Implementation moved from _validate_single_bore
```

**Acceptance Criteria**:
- All validation tests still pass
- New helper functions have >95% test coverage
- Original functions still work (backward compatibility)

**Estimated Effort**: 6-8 hours

### 3.2 Refactor Bore Validation (High Risk - Careful)
**Goal**: Consolidate 3 bore validation paths into 1

**Strategy**: **Wrapper Pattern** - keep existing functions, make them call new unified logic

**Tasks**:
- [ ] Create `_unified_bore_validation()` with all logic
- [ ] Modify existing functions to be thin wrappers:
  ```python
  def _validate_single_bore(...):
      """LEGACY: Use _unified_bore_validation instead."""
      return _unified_bore_validation(...)

  def _validate_bore_from_settings(...):
      """LEGACY: Use _unified_bore_validation instead."""
      # Convert settings dict to unified format
      return _unified_bore_validation(...)
  ```
- [ ] Add deprecation warnings to legacy functions
- [ ] Extensive testing of all 3 entry points

**Regression Prevention**:
```bash
# MANDATORY before/after comparison
pytest tests/test_validation.py -v > before_refactor.log
# ... make changes ...
pytest tests/test_validation.py -v > after_refactor.log
diff before_refactor.log after_refactor.log  # Should be empty
```

**Estimated Effort**: 8-12 hours

**Risk**: High - core business logic change

---

## Phase 4: Architecture Improvements (Week 4)

### 4.1 Extract Geometry Repair Utility
**Goal**: Consolidate repair logic without changing behavior

**Tasks**:
- [ ] Create `src/wormgear/core/geometry_repair.py`
- [ ] Extract `GeometryRepair` class with methods:
  ```python
  class GeometryRepair:
      @staticmethod
      def unify_faces(part: Part) -> Optional[Part]
      @staticmethod
      def sew_faces(part: Part) -> Optional[Part]
      @staticmethod
      def shape_fix(part: Part) -> Optional[Part]
      @staticmethod
      def step_roundtrip(part: Part, temp_path: str) -> Optional[Part]

      @staticmethod
      def repair_geometry(part: Part) -> Part:
          """Try all repair methods in sequence - extracted from duplicated code."""
  ```
- [ ] Update existing repair methods to use utility (wrapper pattern)
- [ ] Add tests for repair utility

**Migration Strategy**:
```python
# In worm.py - change this:
def _repair_geometry(self, part: Part) -> Part:
    # 120 lines of repair logic...

# To this:
def _repair_geometry(self, part: Part) -> Part:
    """LEGACY: Wrapper around GeometryRepair.repair_geometry()"""
    return GeometryRepair.repair_geometry(part)
```

**Estimated Effort**: 10-12 hours

**Risk**: Medium - geometry operations are complex

### 4.2 Add Integration Test Suite
**Goal**: Catch regressions in full calculator→geometry→STEP pipeline

**Tasks**:
- [ ] Create `tests/test_integration_workflows.py`
- [ ] Add tests for key workflows:
  ```python
  def test_standard_workflow_m2_z30():
      """Test: module=2, ratio=30, with bore+keyway → STEP export"""

  def test_globoid_worm_workflow():
      """Test: globoid worm generation → STEP export"""

  def test_virtual_hobbing_workflow():
      """Test: virtual hobbing wheel → STEP export"""
  ```
- [ ] Each test validates:
  - No exceptions thrown
  - STEP file created and valid
  - Geometry volume within expected range
  - Feature presence (bore, keyway) detectable

**Estimated Effort**: 6-8 hours

**Risk**: Low - only adding tests

---

## Phase 5: Development Experience (Week 5)

### 5.1 Improve Development Dependencies
**Tasks**:
- [ ] Add missing dev dependencies to `pyproject.toml`:
  ```toml
  dev = [
      # ... existing ...
      "pytest-timeout>=2.0",      # Prevent hanging tests
      "pytest-xdist>=3.0",       # Parallel test execution
      "pytest-mock>=3.0",        # Mocking utilities
      "types-click>=7.0",        # Type stubs for click
  ]
  ```
- [ ] Configure parallel testing: `pytest -n auto -m "not slow"`
- [ ] Add timeout configuration for slow tests

### 5.2 Enable Phase 2 Mypy (Core Module Typing)
**Tasks**:
- [ ] Fix type annotations in `worm.py`, `wheel.py` (most critical)
- [ ] Enable Phase 2 mypy overrides in `pyproject.toml`
- [ ] Fix type issues incrementally, file by file

**Estimated Effort**: 4-6 hours

---

## Risk Mitigation Strategy

### Pre-Commit Checklist (MANDATORY)
Before **ANY** production code change:

```bash
# 1. Baseline test results
pytest -m "not slow" > baseline_fast.log
pytest -m slow --tb=short > baseline_slow.log  # If needed for geometry changes

# 2. Make changes

# 3. Verify no regressions
pytest -m "not slow" > after_fast.log
diff baseline_fast.log after_fast.log  # Should show only test additions

# 4. Code quality
black src/ tests/
ruff check src/ tests/
mypy src/wormgear

# 5. Integration test (for geometry changes)
python -c "
from wormgear.calculator import design_from_module
from wormgear.io import to_json
print('Calculator OK')
design = design_from_module(2.0, 30)
json_output = to_json(design)
print('JSON export OK')
"
```

### Rollback Plan
- Each phase delivered as separate PR
- Tag before each phase: `git tag debt-cleanup-phase-N`
- If issues found, immediate revert: `git revert <phase-commit>`

### Monitoring for Regressions
- Integration tests must pass on each commit
- Performance regression monitoring (geometry generation time)
- Web calculator functionality verified manually after geometry changes

---

## Success Metrics

**Phase 1**:
- ✅ Test coverage >90% on validation.py
- ✅ Integration test suite exists and passes

**Phase 2**:
- ✅ <5 broad `except Exception` blocks remain (only geometry repair)
- ✅ All specific exceptions have corresponding tests

**Phase 3**:
- ✅ Bore validation consolidated to single implementation
- ✅ Zero behavior changes (all tests pass)

**Phase 4**:
- ✅ Geometry repair logic consolidated into utility class
- ✅ All geometry classes use shared repair utility

**Phase 5**:
- ✅ Fast test suite runs in <3 seconds (parallel execution)
- ✅ Core module has strict type checking enabled

---

## Timeline Summary

| Phase | Duration | Risk Level | Key Deliverable |
|-------|----------|------------|-----------------|
| 1 - Safety Net | 1 week | **LOW** | Comprehensive test coverage |
| 2 - Exceptions | 1 week | **LOW-MED** | Specific exception handling |
| 3 - Validation | 1 week | **HIGH** | Unified bore validation |
| 4 - Architecture | 1 week | **MEDIUM** | Geometry repair utility |
| 5 - DevEx | 1 week | **LOW** | Better tooling/typing |

**Total Effort**: 5 weeks part-time (40-50 hours)

**Critical Success Factor**: Never merge a phase that breaks existing tests. Each phase must be independently valuable and safe to deploy.