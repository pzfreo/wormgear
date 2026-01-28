# Technical Debt Remediation Plan

## Overview

This document provides a detailed implementation plan for addressing technical debt items identified in the January 2026 architectural audit. Items are organized by priority (P0 = Critical, P1 = High, P2 = Medium).

**IMPORTANT**: Before implementing ANY changes, read and follow:
- `/CLAUDE.md` - Project guidelines, schema-first workflow, pre-push checklist
- `/docs/ARCHITECTURE.md` - Layer boundaries and dependencies

---

## Implementation Prompt

Use this prompt when working on technical debt remediation:

```
You are implementing technical debt fixes for the wormgear project. Follow these rules strictly:

MANDATORY WORKFLOW:
1. Read the specific task section below completely before starting
2. If modifying Pydantic models (loaders.py, enums.py, js_bridge.py):
   - Run: python scripts/generate_schemas.py
   - Run: bash scripts/generate_types.sh
   - Commit schemas/*.json and web/types/*.generated.d.ts together with model changes
3. After ANY code change:
   - Run: pytest tests/ -v (must pass)
   - Run: bash scripts/typecheck.sh (must pass)
4. Before pushing:
   - Complete the Pre-Push Checklist from CLAUDE.md
   - Test CLI locally: python -c "from wormgear.calculator import design_from_module; print(design_from_module(2.0, 30))"

ARCHITECTURAL RULES:
- Core layer (geometry) must NEVER import from calculator
- Calculator must NEVER import from core (geometry)
- IO layer coordinates between calculator and core
- All constants go in calculator/constants.py with source documentation
- All validation messages must cite their standard source

CODE QUALITY RULES:
- Functions must not exceed 100 lines (extract helpers if longer)
- All new functions require docstrings explaining WHY, not just WHAT
- Use type hints on all functions including return types
- Use explicit _mm/_deg suffixes on dimensional parameters
- Never use single-letter variables in functions >20 lines

TESTING RULES:
- Every fix requires a test that would have caught the original bug
- Every new function requires unit tests
- Negative tests (invalid input handling) required for all validators
- Tolerance for geometry tests: max 3% (not 5-20%)
```

---

## P0 - Critical Items (Fix Immediately)

### P0.1: Guard Against sqrt() of Negative Values

**Priority**: CRITICAL - Prevents runtime crash
**Location**: `src/wormgear/core/wheel.py:239`
**Effort**: 30 minutes

**Problem**:
```python
# CURRENT CODE (crashes when z_pos >= arc_radius):
if self.throated and abs(z_pos) < arc_radius:
    worm_surface_dist = centre_distance - math.sqrt(arc_radius**2 - z_pos**2)
```

**Fix**:
```python
# CORRECTED CODE:
if self.throated and abs(z_pos) < arc_radius:
    under_sqrt = arc_radius**2 - z_pos**2
    if under_sqrt >= 0:
        worm_surface_dist = centre_distance - math.sqrt(under_sqrt)
    else:
        # Fallback: use nominal distance when sqrt would be invalid
        # This can occur at throat boundaries due to floating-point precision
        worm_surface_dist = centre_distance
```

**Also check and fix similar patterns in**:
- `src/wormgear/core/globoid_worm.py` lines 391-406 (has check, verify it's complete)
- `src/wormgear/core/virtual_hobbing.py` (search for `math.sqrt`)

**Test to add** (`tests/test_wheel.py`):
```python
def test_throated_wheel_edge_case_z_position():
    """Verify throated wheel handles z_pos at boundary without crash."""
    # Create design where z_pos could approach arc_radius
    design = design_from_module(2.0, 30)
    wheel = WheelGeometry(
        params=design.wheel,
        worm_params=design.worm,
        assembly_params=design.assembly,
        throated=True
    )
    # Should not crash even at geometry boundaries
    result = wheel.build()
    assert result.is_valid
```

**Verification**:
- [ ] Code change made
- [ ] Test added and passes
- [ ] Similar patterns checked in other geometry files
- [ ] `pytest tests/test_wheel.py -v` passes

---

### P0.2: Guard Against Division by Zero in Section Count

**Priority**: CRITICAL - Prevents runtime crash
**Locations**:
- `src/wormgear/core/virtual_hobbing.py:309`
- `src/wormgear/core/worm.py:536` (approximate - search for `num_sections - 1`)
- `src/wormgear/core/globoid_worm.py` (search for similar pattern)

**Effort**: 30 minutes

**Problem**:
```python
# CURRENT CODE (crashes if num_sections=1):
for i in range(num_sections):
    t = i / (num_sections - 1)  # Division by zero when num_sections=1!
```

**Fix** (apply to ALL locations):
```python
# Add validation at start of function:
if num_sections < 2:
    raise ValueError(
        f"num_sections must be >= 2 for loft operations, got {num_sections}. "
        f"This can occur with very short worms or extreme lead angles."
    )

# Then the loop is safe:
for i in range(num_sections):
    t = i / (num_sections - 1)
```

**Test to add** (`tests/test_geometry_edge_cases.py` - new file):
```python
import pytest
from wormgear.core import WormGeometry, WheelGeometry
from wormgear.core.virtual_hobbing import VirtualHobbingWheelGeometry

class TestSectionCountValidation:
    """Tests for section count edge cases."""

    def test_worm_rejects_single_section(self):
        """Worm geometry must reject num_sections < 2."""
        # Create params that would result in very few sections
        # (This tests the guard, not that we can actually create such params)
        with pytest.raises(ValueError, match="num_sections must be >= 2"):
            # Force low section count through internal method if needed
            pass  # Implement based on actual code structure

    def test_virtual_hobbing_rejects_single_section(self):
        """Virtual hobbing must reject configurations with < 2 sections."""
        with pytest.raises(ValueError, match="num_sections must be >= 2"):
            pass  # Implement based on actual code structure
```

**Verification**:
- [ ] All three files checked and fixed
- [ ] Tests added for each location
- [ ] `pytest tests/test_geometry_edge_cases.py -v` passes

---

### P0.3: Add Upper Limit on Hobbing Steps

**Priority**: CRITICAL - Prevents memory exhaustion
**Location**: `src/wormgear/core/virtual_hobbing.py` (in `__init__` method)
**Effort**: 15 minutes

**Problem**: No upper limit on `hobbing_steps` parameter allows users to pass extreme values (e.g., 10000) causing memory exhaustion.

**Fix** (add to `__init__` after hobbing_steps is set):
```python
# In VirtualHobbingWheelGeometry.__init__:
MAX_HOBBING_STEPS = 1000  # Beyond this, memory usage becomes problematic

if self.hobbing_steps > MAX_HOBBING_STEPS:
    raise ValueError(
        f"hobbing_steps={self.hobbing_steps} exceeds maximum of {MAX_HOBBING_STEPS}. "
        f"Use 'ultra' preset (360 steps) for highest quality, or reduce for faster generation."
    )

if self.hobbing_steps < 6:
    raise ValueError(
        f"hobbing_steps={self.hobbing_steps} is too low for meaningful results. "
        f"Minimum recommended is 18 (preview preset)."
    )
```

**Test to add** (`tests/test_virtual_hobbing.py`):
```python
def test_hobbing_steps_upper_limit():
    """Hobbing steps must be limited to prevent memory exhaustion."""
    design = design_from_module(2.0, 30)
    with pytest.raises(ValueError, match="exceeds maximum"):
        VirtualHobbingWheelGeometry(
            params=design.wheel,
            worm_params=design.worm,
            assembly_params=design.assembly,
            hobbing_steps=5000  # Unreasonably high
        )

def test_hobbing_steps_lower_limit():
    """Hobbing steps must have minimum for meaningful results."""
    design = design_from_module(2.0, 30)
    with pytest.raises(ValueError, match="too low"):
        VirtualHobbingWheelGeometry(
            params=design.wheel,
            worm_params=design.worm,
            assembly_params=design.assembly,
            hobbing_steps=2  # Too few
        )
```

**Verification**:
- [ ] Limits added to `__init__`
- [ ] Tests added and pass
- [ ] Existing tests still pass

---

### P0.4: Add Missing Docstring to _simulate_hobbing

**Priority**: CRITICAL - Maintainability of complex 237-line function
**Location**: `src/wormgear/core/virtual_hobbing.py:471` (approximate line)
**Effort**: 2 hours

**Problem**: 237-line function with no docstring explaining algorithm, mathematical basis, or performance characteristics.

**Required docstring content**:
```python
def _simulate_hobbing(self) -> Part:
    """
    Simulate the hobbing manufacturing process to generate accurate wheel teeth.

    This method implements virtual hobbing per DIN 3975 §10, where a rotating
    hob (representing the worm) is brought into contact with a rotating wheel
    blank. The envelope of all hob positions defines the final tooth surface.

    Algorithm Overview:
    ------------------
    1. Create hob geometry matching the worm thread profile (_create_hob)
    2. For each hobbing step (default 72 steps = 5° increments):
       a. Calculate wheel rotation angle: wheel_angle = step × (360° / steps) × ratio
       b. Calculate hob rotation angle: hob_angle = step × (360° / steps)
       c. Position hob at centre_distance from wheel axis
       d. Either:
          - Envelope approach: Union hob position into cumulative envelope
          - Incremental approach: Subtract hob from wheel blank
    3. Final subtraction of envelope from wheel blank creates tooth spaces

    Mathematical Basis (DIN 3975 §10):
    ---------------------------------
    The kinematic relationship ensures conjugate tooth action:
    - Wheel angular velocity: ω₂ = ω₁ / ratio
    - Hob engagement: Maintains constant centre distance
    - Tooth profile: Generated as envelope of hob positions

    Performance Characteristics:
    ---------------------------
    - Time complexity: O(n²) where n = hobbing_steps (boolean operations compound)
    - Memory: Envelope grows with each union; ~1MB per 10 steps for complex hobs
    - Native execution: 30-60s for 72 steps with cylindrical hob
    - WASM execution: 3-6 minutes for 72 steps
    - Globoid hobs: 3-5x slower due to geometric complexity

    Optimization Notes:
    ------------------
    - Geometry simplification every N steps reduces face count accumulation
    - For globoid hobs, consider using ≤36 steps
    - Incremental approach uses less peak memory but same total time

    Args:
        None (uses instance attributes: hobbing_steps, hob_geometry, etc.)

    Returns:
        Part: Wheel geometry with accurately hobbed tooth surfaces.
              The result is a valid solid suitable for STEP export.

    Raises:
        RuntimeError: If boolean operations fail to produce valid geometry.
                     This can occur with extreme parameters or memory exhaustion.

    References:
        - DIN 3975:2017 §10 "Generation of worm wheel teeth"
        - Dudley's Handbook of Practical Gear Design, Chapter 8
        - ISO 21771:2007 "Gears - Cylindrical involute gears and gear pairs"

    See Also:
        _create_hob: Creates the hob geometry used in simulation
        _simplify_geometry: Reduces face count to improve boolean performance
        HOBBING_PRESETS: Recommended step counts for different quality levels
    """
```

**Also add inline comments** explaining key algorithm steps:
```python
# Example inline comments to add within the function:

# Phase 1: Build cumulative envelope of all hob positions
# This represents the material that will be removed from the wheel blank
for step in range(self.hobbing_steps):
    # Calculate synchronized rotation angles (DIN 3975 §10.2)
    # Wheel rotates ratio times faster than hob to maintain conjugate action
    wheel_angle = step * step_angle * self.ratio
    hob_angle = step * step_angle

    # Position hob at engagement point
    # Transform sequence: translate to centre_distance, rotate for engagement
    hob_positioned = (
        Pos(self.centre_distance, 0, 0) *  # Move to engagement distance
        Rot(X=90) *                          # Align hob axis perpendicular to wheel
        Rot(Z=hob_angle) *                   # Rotate hob for this step
        hob
    )
```

**Verification**:
- [ ] Comprehensive docstring added
- [ ] Inline comments added for key algorithm steps
- [ ] References to DIN standards included
- [ ] Performance characteristics documented
- [ ] `bash scripts/typecheck.sh` passes (docstrings don't break types)

---

## P1 - High Priority Items (Before v1.0 Stable)

### P1.1: Create Centralized Constants Module

**Priority**: HIGH - Eliminates magic numbers, improves maintainability
**Location**: Create new file `src/wormgear/calculator/constants.py`
**Effort**: 4 hours

**Task**: Extract ALL hardcoded constants from calculator and validation modules into a single, documented constants file.

**Create this file** (`src/wormgear/calculator/constants.py`):
```python
"""
Engineering constants for wormgear calculations.

This module centralizes all numerical constants used in the calculator and
validation modules. Each constant is documented with its source (DIN standard,
ISO standard, or engineering best practice).

MODIFICATION GUIDELINES:
- Never change DIN/ISO constants without updating the standard reference
- Engineering practice constants may be adjusted based on experience
- Add new constants here rather than hardcoding in functions
- Always include units in constant names (_MM, _DEG, _PERCENT)

Constants are grouped by category:
- DIN 3975: Worm gear geometry standards
- DIN 3996: Worm gear load capacity standards
- DIN 6885: Keyway dimensions
- ISO 54: Standard modules
- Engineering practice: Industry best practices (not standardized)
- Manufacturing: Practical manufacturing constraints
"""

from typing import Tuple, Dict

# =============================================================================
# DIN 3975 - Worm Gear Geometry Standards
# =============================================================================

# Standard pressure angles per DIN 3975 Table 1
STANDARD_PRESSURE_ANGLES_DEG: Tuple[float, ...] = (14.5, 20.0, 25.0)

# Default pressure angle - most common in industry
DEFAULT_PRESSURE_ANGLE_DEG: float = 20.0  # DIN 3975 recommends 20° for general use

# Standard clearance factor (bottom clearance = c × module)
# DIN 3975 §5.3: c = 0.2 to 0.3, with 0.25 as typical
CLEARANCE_FACTOR_DEFAULT: float = 0.25

# Lead angle limits per DIN 3975 §4.2
LEAD_ANGLE_MIN_DEG: float = 1.0    # Below this: manufacturing very difficult
LEAD_ANGLE_MAX_DEG: float = 45.0   # Above this: impractical geometry

# =============================================================================
# DIN 3996 - Worm Gear Load Capacity Standards
# =============================================================================

# Self-locking threshold per DIN 3996 §7.4
# Below this lead angle, friction prevents backdrive under typical conditions
SELF_LOCKING_THRESHOLD_DEG: float = 6.0

# Efficiency thresholds for warnings
# DIN 3996 notes that η < 30% causes significant heat generation
EFFICIENCY_WARNING_VERY_LOW_PERCENT: float = 30.0
EFFICIENCY_WARNING_LOW_PERCENT: float = 50.0

# Default friction coefficient for efficiency calculations
# DIN 3996 Table 5: Bronze on steel, oil lubricated
FRICTION_COEFFICIENT_DEFAULT: float = 0.05

# =============================================================================
# ISO 54 / DIN 780 - Standard Modules
# =============================================================================

# Standard module series per ISO 54 (subset commonly used for worm gears)
STANDARD_MODULES_MM: Tuple[float, ...] = (
    0.5, 0.6, 0.7, 0.8, 0.9, 1.0,
    1.25, 1.5, 1.75, 2.0, 2.25, 2.5, 2.75, 3.0,
    3.5, 4.0, 4.5, 5.0, 5.5, 6.0,
    7.0, 8.0, 9.0, 10.0
)

# Tolerance for "close to standard" module check
MODULE_STANDARD_TOLERANCE_PERCENT: float = 10.0

# =============================================================================
# Engineering Best Practice (Not Standardized)
# =============================================================================

# Wheel face width recommendations
# Source: Dudley's Handbook of Practical Gear Design, empirical guidelines
WHEEL_WIDTH_FACTOR_RECOMMENDED: float = 1.3    # width = 1.3 × worm_pitch_dia
WHEEL_WIDTH_FACTOR_MIN: float = 8.0            # width >= module × 8.0
WHEEL_WIDTH_FACTOR_MAX: float = 12.0           # width <= module × 12.0

# Worm length recommendations
# Source: Industry practice for ensuring full tooth engagement
WORM_LENGTH_SAFETY_MM: float = 1.0             # Additional length margin
WORM_LENGTH_FACTOR: float = 2.0                # length = face_width + 2×lead + safety

# Worm proportions (pitch_diameter / module ratio)
# Source: Machinery's Handbook, practical design guidelines
WORM_RATIO_MIN: float = 5.0    # Below: worm core too thin, weak
WORM_RATIO_MAX: float = 20.0   # Above: worm too thick, inefficient material use

# Lead angle warning thresholds (engineering judgment)
LEAD_ANGLE_WARNING_VERY_LOW_DEG: float = 3.0   # Very low efficiency expected
LEAD_ANGLE_WARNING_LOW_DEG: float = 5.0        # Low efficiency expected
LEAD_ANGLE_WARNING_HIGH_DEG: float = 25.0      # Self-locking unlikely

# Contact ratio minimum for smooth operation
# Source: AGMA 6022, gear design best practices
CONTACT_RATIO_MIN: float = 1.2

# =============================================================================
# Manufacturing Constraints
# =============================================================================

# Minimum rim thickness before structural concerns
# Source: Practical machining experience, material-dependent
MIN_RIM_THICKNESS_MM: float = 0.5              # Below: high failure risk
WARN_RIM_WORM_MM: float = 1.5                  # Worm warning threshold
WARN_RIM_WHEEL_MM: float = 2.0                 # Wheel warning threshold

# Minimum thread width for manufacturability
# Source: CNC machining practical limits
MIN_THREAD_WIDTH_MM: float = 0.1

# Small bore threshold (below which keyways aren't practical)
# Source: DIN 6885 doesn't define keyways below 6mm
SMALL_BORE_THRESHOLD_MM: float = 2.0
KEYWAY_MIN_BORE_MM: float = 6.0                # DIN 6885 minimum

# Bore sizing recommendations
# Source: Standard shaft/bore fitting practice
BORE_TARGET_FACTOR: float = 0.25               # bore ≈ 25% of pitch diameter
BORE_THIN_RIM_WARNING_MM: float = 1.5          # Warn if rim < this

# =============================================================================
# Globoid Worm Specific
# =============================================================================

# Throat reduction warning threshold
# Source: Engineering judgment - aggressive reduction affects strength
THROAT_REDUCTION_WARNING_PERCENT: float = 20.0

# Default worm length factor for globoid
GLOBOID_LENGTH_FACTOR: float = 1.3             # length = pitch_dia × 1.3

# =============================================================================
# Virtual Hobbing
# =============================================================================

# Hobbing step limits
HOBBING_STEPS_MIN: int = 6                     # Below: geometry too coarse
HOBBING_STEPS_MAX: int = 1000                  # Above: memory exhaustion risk

# Hobbing presets (steps, native_time_estimate, wasm_time_estimate)
HOBBING_PRESETS: Dict[str, Dict] = {
    "preview": {"steps": 36, "native_sec": "15-30", "wasm_min": "1-3"},
    "balanced": {"steps": 72, "native_sec": "30-60", "wasm_min": "3-6"},
    "high": {"steps": 144, "native_min": "1-2", "wasm_min": "6-12"},
    "ultra": {"steps": 360, "native_min": "3-5", "wasm_min": "15-30"},
}

# Globoid hob optimization - auto-reduce steps
GLOBOID_HOB_MAX_STEPS: int = 36                # Reduce for globoid hobs

# =============================================================================
# Geometry Generation
# =============================================================================

# Minimum sections for loft operations
MIN_LOFT_SECTIONS: int = 2

# Default sections per turn for helix generation
DEFAULT_SECTIONS_PER_TURN: int = 36

# Taper factor minimum (prevents degenerate thread profiles)
MIN_TAPER_FACTOR: float = 0.05
```

**Then update all source files** to import from constants:

```python
# In calculator/core.py, calculator/validation.py, etc.:
from wormgear.calculator.constants import (
    DEFAULT_PRESSURE_ANGLE_DEG,
    CLEARANCE_FACTOR_DEFAULT,
    SELF_LOCKING_THRESHOLD_DEG,
    # ... etc
)

# Replace hardcoded values:
# BEFORE:
if worm["lead_angle_deg"] < 6.0:
    self_locking = True

# AFTER:
if worm["lead_angle_deg"] < SELF_LOCKING_THRESHOLD_DEG:
    self_locking = True
```

**Files to update**:
- `src/wormgear/calculator/core.py` - Replace ~10 magic numbers
- `src/wormgear/calculator/validation.py` - Replace ~15 magic numbers
- `src/wormgear/calculator/bore_calculator.py` - Replace ~3 magic numbers
- `src/wormgear/core/worm.py` - Replace ~3 magic numbers
- `src/wormgear/core/wheel.py` - Replace ~5 magic numbers
- `src/wormgear/core/virtual_hobbing.py` - Replace ~5 magic numbers
- `src/wormgear/core/globoid_worm.py` - Replace ~3 magic numbers

**Test to add** (`tests/test_constants.py`):
```python
"""Tests for constants module to ensure values are reasonable."""
import pytest
from wormgear.calculator.constants import *

class TestConstantsValidity:
    """Verify constants have sensible values."""

    def test_pressure_angles_in_valid_range(self):
        for angle in STANDARD_PRESSURE_ANGLES_DEG:
            assert 10 <= angle <= 30, f"Pressure angle {angle} outside valid range"

    def test_lead_angle_limits_ordered(self):
        assert LEAD_ANGLE_MIN_DEG < LEAD_ANGLE_MAX_DEG
        assert LEAD_ANGLE_WARNING_VERY_LOW_DEG < LEAD_ANGLE_WARNING_LOW_DEG

    def test_hobbing_limits_reasonable(self):
        assert HOBBING_STEPS_MIN >= 2, "Need at least 2 steps for loft"
        assert HOBBING_STEPS_MAX <= 2000, "Max steps should prevent memory issues"

    def test_rim_thresholds_ordered(self):
        assert MIN_RIM_THICKNESS_MM < WARN_RIM_WORM_MM
        assert MIN_RIM_THICKNESS_MM < WARN_RIM_WHEEL_MM
```

**Verification**:
- [ ] constants.py created with all documented constants
- [ ] All source files updated to import from constants
- [ ] No hardcoded magic numbers remain in calculator/validation
- [ ] Tests for constants validity pass
- [ ] All existing tests still pass
- [ ] `grep -r "< 6.0\|< 5.0\|< 3.0\|> 25.0\|> 45.0" src/` returns no results

---

### P1.2: Add Contact Ratio Validation

**Priority**: HIGH - Missing DIN 3975 §7.4 compliance
**Location**: `src/wormgear/calculator/core.py` and `src/wormgear/calculator/validation.py`
**Effort**: 2 hours

**Task**: Implement contact ratio calculation and validation per DIN 3975 §7.4.

**Add to `calculator/core.py`**:
```python
def calculate_contact_ratio(
    wheel_face_width_mm: float,
    worm_lead_mm: float
) -> float:
    """
    Calculate the contact ratio (overlap ratio) for a worm gear pair.

    The contact ratio indicates how many teeth are in contact at any instant.
    A ratio >= 1.2 ensures smooth, continuous power transmission.

    Formula (DIN 3975 §7.4):
        ε = wheel_face_width / worm_lead

    Args:
        wheel_face_width_mm: Wheel face width in millimeters
        worm_lead_mm: Worm lead (axial pitch × number of starts) in millimeters

    Returns:
        Contact ratio (dimensionless). Values:
        - < 1.0: Discontinuous contact (impact, noise)
        - 1.0-1.2: Marginal (acceptable for low-speed)
        - >= 1.2: Good (smooth operation)
        - >= 2.0: Excellent (high-load applications)

    References:
        DIN 3975:2017 §7.4 "Contact ratio"
        AGMA 6022-C93 "Design Manual for Cylindrical Wormgearing"
    """
    if worm_lead_mm <= 0:
        raise ValueError(f"worm_lead_mm must be positive, got {worm_lead_mm}")

    return wheel_face_width_mm / worm_lead_mm
```

**Add to `calculator/validation.py`** (in `validate_design` function):
```python
from wormgear.calculator.constants import CONTACT_RATIO_MIN

# Add after existing validations:
def _validate_contact_ratio(design: WormGearDesign, messages: List[ValidationMessage]) -> None:
    """Validate contact ratio per DIN 3975 §7.4."""
    wheel_width = design.wheel.width_mm or design.manufacturing.wheel_width_mm
    worm_lead = design.worm.lead_mm

    if wheel_width is None or worm_lead is None or worm_lead <= 0:
        return  # Can't calculate without these values

    contact_ratio = wheel_width / worm_lead

    if contact_ratio < 1.0:
        messages.append(ValidationMessage(
            severity=Severity.WARNING,
            code="CONTACT_RATIO_DISCONTINUOUS",
            message=f"Contact ratio {contact_ratio:.2f} < 1.0 causes discontinuous tooth contact",
            suggestion=f"Increase wheel face width to at least {worm_lead * 1.2:.1f}mm for smooth operation",
            standard="DIN 3975 §7.4"
        ))
    elif contact_ratio < CONTACT_RATIO_MIN:
        messages.append(ValidationMessage(
            severity=Severity.INFO,
            code="CONTACT_RATIO_MARGINAL",
            message=f"Contact ratio {contact_ratio:.2f} is marginal (recommended >= {CONTACT_RATIO_MIN})",
            suggestion="Consider increasing wheel face width for smoother operation",
            standard="DIN 3975 §7.4"
        ))
```

**Add ValidationMessage.standard field** if not already present:
```python
@dataclass
class ValidationMessage:
    """A single validation finding."""
    severity: Severity
    code: str
    message: str
    suggestion: Optional[str] = None
    standard: Optional[str] = None  # e.g., "DIN 3975 §7.4"
```

**Test to add** (`tests/test_validation.py`):
```python
def test_contact_ratio_warning():
    """Low contact ratio should generate warning."""
    # Create design with narrow wheel (low contact ratio)
    design = design_from_module(2.0, 30)
    # Manually set narrow wheel width
    design.wheel.width_mm = design.worm.lead_mm * 0.8  # < 1.0 ratio

    result = validate_design(design)

    assert any(
        m.code == "CONTACT_RATIO_DISCONTINUOUS"
        for m in result.messages
    ), "Should warn about discontinuous contact"

def test_contact_ratio_adequate():
    """Adequate contact ratio should not generate warning."""
    design = design_from_module(2.0, 30)
    # Ensure adequate width
    design.wheel.width_mm = design.worm.lead_mm * 1.5  # > 1.2 ratio

    result = validate_design(design)

    assert not any(
        "CONTACT_RATIO" in m.code
        for m in result.messages
    ), "Should not warn about adequate contact ratio"
```

**Verification**:
- [ ] `calculate_contact_ratio` function added
- [ ] `_validate_contact_ratio` called in `validate_design`
- [ ] `ValidationMessage.standard` field added if missing
- [ ] Tests pass
- [ ] Schema regenerated if ValidationMessage changed

---

### P1.3: Add Set Screw Feature Tests

**Priority**: HIGH - Only 2 tests exist for set screw feature
**Location**: `tests/test_features.py` (expand existing or create `tests/test_set_screw.py`)
**Effort**: 4 hours

**Task**: Comprehensive test coverage for SetScrewFeature including edge cases.

**Create `tests/test_set_screw.py`**:
```python
"""
Comprehensive tests for SetScrewFeature.

Tests cover:
- Basic functionality (1, 2, 4, 6 screws)
- Angular positioning
- Size variations (M2-M8)
- Edge cases (small bores, interference)
- Error handling (invalid configurations)
"""
import pytest
import math
from wormgear.calculator import design_from_module
from wormgear.core import WormGeometry, WheelGeometry
from wormgear.core.features import SetScrewFeature, BoreFeature


class TestSetScrewBasicFunctionality:
    """Test basic set screw creation."""

    @pytest.fixture
    def basic_design(self):
        return design_from_module(2.0, 30)

    @pytest.mark.parametrize("screw_count", [1, 2, 4, 6])
    def test_set_screw_count_variations(self, basic_design, screw_count):
        """Verify different screw counts create valid geometry."""
        worm = WormGeometry(
            params=basic_design.worm,
            assembly_params=basic_design.assembly,
            length=40,
            bore=BoreFeature(diameter=8.0),
            set_screw=SetScrewFeature(count=screw_count, size="M3")
        )
        result = worm.build()

        assert result.is_valid, f"Geometry invalid with {screw_count} set screws"
        # Verify volume is less than without set screws (material removed)
        worm_no_screw = WormGeometry(
            params=basic_design.worm,
            assembly_params=basic_design.assembly,
            length=40,
            bore=BoreFeature(diameter=8.0)
        ).build()
        assert result.volume < worm_no_screw.volume, "Set screw should remove material"

    @pytest.mark.parametrize("size", ["M2", "M2.5", "M3", "M4", "M5", "M6", "M8"])
    def test_set_screw_size_variations(self, basic_design, size):
        """Verify different screw sizes create valid geometry."""
        worm = WormGeometry(
            params=basic_design.worm,
            assembly_params=basic_design.assembly,
            length=40,
            bore=BoreFeature(diameter=12.0),  # Large enough for M8
            set_screw=SetScrewFeature(count=2, size=size)
        )
        result = worm.build()
        assert result.is_valid, f"Geometry invalid with {size} set screws"


class TestSetScrewAngularPositioning:
    """Test set screw angular placement."""

    @pytest.fixture
    def basic_design(self):
        return design_from_module(2.0, 30)

    def test_set_screw_at_specific_angle(self, basic_design):
        """Verify set screw placed at specified angle."""
        angle = 45.0
        worm = WormGeometry(
            params=basic_design.worm,
            assembly_params=basic_design.assembly,
            length=40,
            bore=BoreFeature(diameter=8.0),
            set_screw=SetScrewFeature(count=1, size="M3", angle_deg=angle)
        )
        result = worm.build()
        assert result.is_valid

    def test_multiple_screws_evenly_spaced(self, basic_design):
        """Verify multiple screws are evenly distributed."""
        worm = WormGeometry(
            params=basic_design.worm,
            assembly_params=basic_design.assembly,
            length=40,
            bore=BoreFeature(diameter=8.0),
            set_screw=SetScrewFeature(count=4, size="M3")  # Should be 90° apart
        )
        result = worm.build()
        assert result.is_valid
        # Could add geometric verification that holes are 90° apart


class TestSetScrewEdgeCases:
    """Test set screw edge cases and boundary conditions."""

    @pytest.fixture
    def basic_design(self):
        return design_from_module(2.0, 30)

    def test_set_screw_small_bore(self, basic_design):
        """Set screw on small bore should warn or fail gracefully."""
        # 3mm bore with M3 screw - very tight
        worm = WormGeometry(
            params=basic_design.worm,
            assembly_params=basic_design.assembly,
            length=40,
            bore=BoreFeature(diameter=3.0),
            set_screw=SetScrewFeature(count=1, size="M2")
        )
        # Should either work or raise meaningful error
        try:
            result = worm.build()
            assert result.is_valid
        except ValueError as e:
            assert "bore" in str(e).lower() or "small" in str(e).lower()

    def test_set_screw_oversized_for_bore(self, basic_design):
        """Screw larger than bore should fail with clear error."""
        with pytest.raises(ValueError, match="[Ss]crew.*[Bb]ore|[Bb]ore.*[Ss]crew"):
            WormGeometry(
                params=basic_design.worm,
                assembly_params=basic_design.assembly,
                length=40,
                bore=BoreFeature(diameter=4.0),
                set_screw=SetScrewFeature(count=1, size="M8")  # M8 > 4mm bore
            )

    def test_set_screw_without_bore(self, basic_design):
        """Set screw without bore should fail with clear error."""
        with pytest.raises(ValueError, match="[Bb]ore.*required|requires.*[Bb]ore"):
            WormGeometry(
                params=basic_design.worm,
                assembly_params=basic_design.assembly,
                length=40,
                # No bore specified
                set_screw=SetScrewFeature(count=1, size="M3")
            )


class TestSetScrewOnWheel:
    """Test set screws on wheel geometry."""

    @pytest.fixture
    def basic_design(self):
        return design_from_module(2.0, 30)

    def test_wheel_with_set_screw(self, basic_design):
        """Verify set screw works on wheel."""
        wheel = WheelGeometry(
            params=basic_design.wheel,
            worm_params=basic_design.worm,
            assembly_params=basic_design.assembly,
            bore=BoreFeature(diameter=15.0),
            set_screw=SetScrewFeature(count=2, size="M4")
        )
        result = wheel.build()
        assert result.is_valid


class TestSetScrewISO4026Compliance:
    """Test ISO 4026 (set screw dimensions) compliance."""

    # ISO 4026 dimensions for socket set screws (cone point)
    ISO_4026_DIMENSIONS = {
        "M2": {"thread_dia": 2.0, "socket_depth": 1.0},
        "M3": {"thread_dia": 3.0, "socket_depth": 1.5},
        "M4": {"thread_dia": 4.0, "socket_depth": 2.0},
        "M5": {"thread_dia": 5.0, "socket_depth": 2.5},
        "M6": {"thread_dia": 6.0, "socket_depth": 3.0},
        "M8": {"thread_dia": 8.0, "socket_depth": 4.0},
    }

    @pytest.mark.parametrize("size,dims", ISO_4026_DIMENSIONS.items())
    def test_set_screw_uses_standard_dimensions(self, size, dims):
        """Verify set screw dimensions match ISO 4026."""
        design = design_from_module(2.0, 30)
        worm = WormGeometry(
            params=design.worm,
            assembly_params=design.assembly,
            length=40,
            bore=BoreFeature(diameter=15.0),
            set_screw=SetScrewFeature(count=1, size=size)
        )
        result = worm.build()

        # Verify volume reduction is consistent with expected hole size
        worm_no_screw = WormGeometry(
            params=design.worm,
            assembly_params=design.assembly,
            length=40,
            bore=BoreFeature(diameter=15.0)
        ).build()

        volume_diff = worm_no_screw.volume - result.volume
        # Approximate expected volume: cylinder of thread diameter
        expected_min = math.pi * (dims["thread_dia"]/2)**2 * dims["socket_depth"]

        assert volume_diff > expected_min * 0.8, \
            f"Set screw hole volume {volume_diff:.2f}mm³ seems too small for {size}"
```

**Verification**:
- [ ] Test file created with all test classes
- [ ] All tests pass (or skip with `@pytest.mark.skip` if feature not implemented)
- [ ] Coverage for set screw feature > 80%
- [ ] Edge cases documented in test docstrings

---

### P1.4: Add Hub Feature Tests

**Priority**: HIGH - No tests exist for hub feature
**Location**: Create `tests/test_hub.py`
**Effort**: 4 hours

**Task**: Create comprehensive tests for HubFeature on wheel geometry.

**Create `tests/test_hub.py`**:
```python
"""
Comprehensive tests for HubFeature on wheel geometry.

Tests cover:
- Hub types (flush, extended, flanged)
- Hub dimensions (length, diameter)
- Hub with bore and keyway interactions
- Edge cases (very short hub, very long hub)
"""
import pytest
from wormgear.calculator import design_from_module
from wormgear.core import WheelGeometry
from wormgear.core.features import HubFeature, BoreFeature, KeywayFeature


class TestHubTypes:
    """Test different hub type configurations."""

    @pytest.fixture
    def basic_design(self):
        return design_from_module(2.0, 30)

    @pytest.mark.parametrize("hub_type", ["flush", "extended", "flanged"])
    def test_hub_type_creates_valid_geometry(self, basic_design, hub_type):
        """Each hub type should create valid geometry."""
        wheel = WheelGeometry(
            params=basic_design.wheel,
            worm_params=basic_design.worm,
            assembly_params=basic_design.assembly,
            bore=BoreFeature(diameter=15.0),
            hub=HubFeature(type=hub_type)
        )
        result = wheel.build()
        assert result.is_valid, f"Hub type '{hub_type}' produced invalid geometry"

    def test_flush_hub_same_as_no_hub(self, basic_design):
        """Flush hub should be equivalent to no hub (no extension)."""
        wheel_flush = WheelGeometry(
            params=basic_design.wheel,
            worm_params=basic_design.worm,
            assembly_params=basic_design.assembly,
            bore=BoreFeature(diameter=15.0),
            hub=HubFeature(type="flush")
        ).build()

        wheel_no_hub = WheelGeometry(
            params=basic_design.wheel,
            worm_params=basic_design.worm,
            assembly_params=basic_design.assembly,
            bore=BoreFeature(diameter=15.0)
        ).build()

        # Volumes should be very close (within 1%)
        assert abs(wheel_flush.volume - wheel_no_hub.volume) / wheel_no_hub.volume < 0.01

    def test_extended_hub_adds_material(self, basic_design):
        """Extended hub should add material beyond wheel face."""
        wheel_extended = WheelGeometry(
            params=basic_design.wheel,
            worm_params=basic_design.worm,
            assembly_params=basic_design.assembly,
            bore=BoreFeature(diameter=15.0),
            hub=HubFeature(type="extended", length=20.0, diameter=30.0)
        ).build()

        wheel_no_hub = WheelGeometry(
            params=basic_design.wheel,
            worm_params=basic_design.worm,
            assembly_params=basic_design.assembly,
            bore=BoreFeature(diameter=15.0)
        ).build()

        assert wheel_extended.volume > wheel_no_hub.volume, \
            "Extended hub should add material"


class TestHubDimensions:
    """Test hub dimension variations."""

    @pytest.fixture
    def basic_design(self):
        return design_from_module(2.0, 30)

    @pytest.mark.parametrize("length", [5.0, 10.0, 20.0, 50.0])
    def test_hub_length_variations(self, basic_design, length):
        """Different hub lengths should create valid geometry."""
        wheel = WheelGeometry(
            params=basic_design.wheel,
            worm_params=basic_design.worm,
            assembly_params=basic_design.assembly,
            bore=BoreFeature(diameter=15.0),
            hub=HubFeature(type="extended", length=length)
        )
        result = wheel.build()
        assert result.is_valid, f"Hub length {length}mm produced invalid geometry"

    @pytest.mark.parametrize("diameter", [20.0, 30.0, 40.0])
    def test_hub_diameter_variations(self, basic_design, diameter):
        """Different hub diameters should create valid geometry."""
        wheel = WheelGeometry(
            params=basic_design.wheel,
            worm_params=basic_design.worm,
            assembly_params=basic_design.assembly,
            bore=BoreFeature(diameter=15.0),
            hub=HubFeature(type="extended", diameter=diameter, length=15.0)
        )
        result = wheel.build()
        assert result.is_valid, f"Hub diameter {diameter}mm produced invalid geometry"


class TestHubWithFeatures:
    """Test hub interaction with other features."""

    @pytest.fixture
    def basic_design(self):
        return design_from_module(2.0, 30)

    def test_hub_with_keyway(self, basic_design):
        """Hub should work with keyway."""
        wheel = WheelGeometry(
            params=basic_design.wheel,
            worm_params=basic_design.worm,
            assembly_params=basic_design.assembly,
            bore=BoreFeature(diameter=15.0),
            keyway=KeywayFeature(),
            hub=HubFeature(type="extended", length=20.0)
        )
        result = wheel.build()
        assert result.is_valid

    def test_hub_with_set_screw(self, basic_design):
        """Hub should work with set screws."""
        from wormgear.core.features import SetScrewFeature

        wheel = WheelGeometry(
            params=basic_design.wheel,
            worm_params=basic_design.worm,
            assembly_params=basic_design.assembly,
            bore=BoreFeature(diameter=15.0),
            set_screw=SetScrewFeature(count=2, size="M4"),
            hub=HubFeature(type="extended", length=20.0)
        )
        result = wheel.build()
        assert result.is_valid


class TestHubEdgeCases:
    """Test hub edge cases."""

    @pytest.fixture
    def basic_design(self):
        return design_from_module(2.0, 30)

    def test_hub_diameter_smaller_than_bore(self, basic_design):
        """Hub diameter smaller than bore should fail."""
        with pytest.raises(ValueError, match="[Hh]ub.*diameter|diameter.*bore"):
            WheelGeometry(
                params=basic_design.wheel,
                worm_params=basic_design.worm,
                assembly_params=basic_design.assembly,
                bore=BoreFeature(diameter=20.0),
                hub=HubFeature(type="extended", diameter=15.0)  # < bore
            )

    def test_hub_very_short(self, basic_design):
        """Very short hub should work or warn."""
        wheel = WheelGeometry(
            params=basic_design.wheel,
            worm_params=basic_design.worm,
            assembly_params=basic_design.assembly,
            bore=BoreFeature(diameter=15.0),
            hub=HubFeature(type="extended", length=1.0)  # Very short
        )
        result = wheel.build()
        assert result.is_valid
```

**Verification**:
- [ ] Test file created
- [ ] Tests pass (or skip if hub feature not fully implemented)
- [ ] Coverage for hub feature > 80%

---

### P1.5: Fix Feature Duplication in Schema

**Priority**: HIGH - Data consistency risk
**Location**: `src/wormgear/io/loaders.py`
**Effort**: 3 hours

**Problem**: Features exist in both `WormGearDesign.features` and `WormGearDesign.manufacturing.worm_features`/`wheel_features`.

**Task**: Remove duplication, keep features in `features` section only.

**Steps**:

1. **Update ManufacturingParams** to remove feature fields:
```python
# In loaders.py, ManufacturingParams class:
# REMOVE these fields:
# worm_features: Optional[WormFeatures] = None  # DELETE
# wheel_features: Optional[WheelFeatures] = None  # DELETE
```

2. **Add migration in upgrade_schema**:
```python
def upgrade_schema(data: Dict, target_version: str = SCHEMA_VERSION) -> Dict:
    """Upgrade schema to target version."""
    current = data.get('schema_version', '1.0')

    # Migration: Move features from manufacturing to features section
    if 'manufacturing' in data:
        mfg = data['manufacturing']
        if 'worm_features' in mfg and mfg['worm_features']:
            if 'features' not in data:
                data['features'] = {}
            if 'worm' not in data['features']:
                data['features']['worm'] = mfg['worm_features']
            del mfg['worm_features']

        if 'wheel_features' in mfg and mfg['wheel_features']:
            if 'features' not in data:
                data['features'] = {}
            if 'wheel' not in data['features']:
                data['features']['wheel'] = mfg['wheel_features']
            del mfg['wheel_features']

    data['schema_version'] = target_version
    return data
```

3. **Update all code** that references `manufacturing.worm_features` or `manufacturing.wheel_features`

4. **Regenerate schemas**:
```bash
python scripts/generate_schemas.py
bash scripts/generate_types.sh
```

**Test to add**:
```python
def test_schema_migration_features():
    """Old schema with features in manufacturing should migrate."""
    old_data = {
        "schema_version": "1.0",
        "worm": {...},
        "wheel": {...},
        "assembly": {...},
        "manufacturing": {
            "worm_features": {"bore_type": "custom", "bore_diameter_mm": 8.0}
        }
    }

    migrated = upgrade_schema(old_data, "2.0")

    assert "worm_features" not in migrated.get("manufacturing", {})
    assert migrated["features"]["worm"]["bore_type"] == "custom"
```

**Verification**:
- [ ] Fields removed from ManufacturingParams
- [ ] Migration logic added
- [ ] All references updated
- [ ] Schemas regenerated
- [ ] Migration test passes
- [ ] All existing tests pass

---

### P1.6: Complete BoreType Enum

**Priority**: HIGH - Type safety gap
**Location**: `src/wormgear/enums.py`
**Effort**: 2 hours

**Task**: Expand BoreType enum to include all anti-rotation options currently stored as strings.

**Update enums.py**:
```python
class BoreType(str, Enum):
    """
    Bore type options for worm and wheel geometry.

    Defines how the central bore is configured, including
    anti-rotation features per DIN 6885 and other standards.
    """
    NONE = "none"                    # No bore (solid shaft)
    CUSTOM = "custom"                # Custom diameter bore only
    DIN6885_KEYWAY = "din6885"       # Bore with DIN 6885 keyway
    DDCUT = "ddcut"                  # Bore with DD-cut (double-D)
    CUSTOM_KEYWAY = "custom_keyway"  # Bore with custom keyway dimensions
```

**Update WormFeatures/WheelFeatures**:
```python
class WormFeatures(BaseModel):
    """Features for worm geometry."""
    bore_type: BoreType  # Now uses expanded enum
    bore_diameter_mm: Optional[float] = None
    # REMOVE: anti_rotation: Optional[str] = None  # Moved to BoreType
    ddcut_depth_percent: float = Field(default=15.0, ge=5.0, le=40.0)
    keyway: Optional[KeywaySpec] = None  # For custom keyway dimensions
    set_screw: Optional[SetScrewSpec] = None
```

**Update js_bridge.py** to handle new enum values:
```python
@field_validator('bore_type', mode='before')
@classmethod
def normalize_bore_type(cls, v):
    """Normalize bore type from various input formats."""
    if isinstance(v, str):
        v = v.lower()
        # Handle legacy anti_rotation values
        if v == "din6885":
            return BoreType.DIN6885_KEYWAY
        if v == "ddcut":
            return BoreType.DDCUT
    return v
```

**Regenerate schemas**:
```bash
python scripts/generate_schemas.py
bash scripts/generate_types.sh
```

**Verification**:
- [ ] Enum updated with all bore types
- [ ] WormFeatures/WheelFeatures updated
- [ ] js_bridge normalization updated
- [ ] Schemas regenerated
- [ ] All tests pass
- [ ] TypeScript types include new enum values

---

## P2 - Medium Priority Items (Next Quarter)

### P2.1: Optimize Virtual Hobbing Performance

**Priority**: MEDIUM - 5-10× performance improvement possible
**Location**: `src/wormgear/core/virtual_hobbing.py`
**Effort**: 8 hours

**Task**: Reduce virtual hobbing time from minutes to seconds through algorithmic optimizations.

**Optimization 1: Auto-reduce steps for globoid hobs**
```python
# In __init__, after setting hobbing_steps:
from wormgear.calculator.constants import GLOBOID_HOB_MAX_STEPS

if self.hob_geometry is not None:
    if self.hobbing_steps > GLOBOID_HOB_MAX_STEPS:
        original = self.hobbing_steps
        self.hobbing_steps = GLOBOID_HOB_MAX_STEPS
        if self.progress_callback:
            self.progress_callback(
                f"Reduced hobbing steps from {original} to {self.hobbing_steps} for globoid hob",
                0.0
            )
```

**Optimization 2: Pre-simplify hob geometry**
```python
# In _simulate_hobbing, before main loop:
hob = self._create_hob()

# Simplify hob ONCE before loop (not during each iteration)
if self.hob_geometry is not None:
    hob = self._simplify_geometry(hob)
    self._report_progress(f"Simplified hob to {len(hob.faces())} faces", 5.0)
```

**Optimization 3: More aggressive envelope simplification**
```python
# Calculate simplification interval based on complexity
if self.hob_geometry is not None:
    # Globoid: simplify every step to prevent exponential growth
    simplification_interval = 1
else:
    # Cylindrical: simplify every N steps
    simplification_interval = max(3, self.hobbing_steps // 12)

# In main loop:
if step > 0 and step % simplification_interval == 0:
    envelope = self._simplify_geometry(envelope)
```

**Optimization 4: Use parallel boolean operations (if supported by build123d)**
```python
# Check if build123d supports parallel operations
# If so, batch multiple hob positions before union
BATCH_SIZE = 4

for batch_start in range(0, self.hobbing_steps, BATCH_SIZE):
    batch_end = min(batch_start + BATCH_SIZE, self.hobbing_steps)
    batch_positions = []

    for step in range(batch_start, batch_end):
        # Calculate position
        hob_positioned = self._position_hob(step)
        batch_positions.append(hob_positioned)

    # Union batch at once (if supported)
    if len(batch_positions) > 1:
        batch_union = batch_positions[0]
        for pos in batch_positions[1:]:
            batch_union = batch_union + pos
        envelope = envelope + batch_union if envelope else batch_union
```

**Test performance improvement**:
```python
@pytest.mark.slow
def test_virtual_hobbing_performance():
    """Virtual hobbing should complete within time budget."""
    import time

    design = design_from_module(2.0, 30)

    start = time.time()
    wheel = VirtualHobbingWheelGeometry(
        params=design.wheel,
        worm_params=design.worm,
        assembly_params=design.assembly,
        hobbing_steps=72
    ).build()
    elapsed = time.time() - start

    assert wheel.is_valid
    assert elapsed < 120, f"Hobbing took {elapsed:.1f}s, should be < 120s"
```

**Verification**:
- [ ] Auto-reduction for globoid implemented
- [ ] Pre-simplification of hob added
- [ ] Aggressive simplification interval for complex hobs
- [ ] Performance test added
- [ ] 2-5× improvement measured

---

### P2.2: Decompose Large Functions

**Priority**: MEDIUM - Maintainability improvement
**Locations**: Multiple files with 150+ line functions
**Effort**: 8 hours

**Target functions** (decompose each to <100 lines):

1. **`validation.py:_validate_bore()`** (229 lines)
   - Extract: `_calculate_effective_rim()`
   - Extract: `_lookup_din6885_keyway()`
   - Extract: `_validate_rim_thickness()`
   - Extract: `_validate_keyway_compatibility()`

2. **`validation.py:_validate_bore_from_settings()`** (200 lines)
   - Share helpers with `_validate_bore()`
   - Extract: `_calculate_bore_recommendation()`

3. **`worm.py:_create_single_thread()`** (215 lines)
   - Extract: `_create_thread_profile_section()`
   - Extract: `_calculate_taper_factor()`
   - Extract: `_generate_helix_sections()`

4. **`wheel.py:_create_helical_gear()`** (196 lines)
   - Extract: `_create_tooth_space_profile()`
   - Extract: `_calculate_twist_sections()`

5. **`virtual_hobbing.py:_simulate_hobbing()`** (237 lines)
   - Extract: `_create_envelope()`
   - Extract: `_position_hob_at_step()`
   - Extract: `_apply_envelope_to_blank()`

**Pattern for extraction**:
```python
# BEFORE (in one large function):
def _validate_bore(design, messages):
    # ... 50 lines calculating rim ...
    # ... 50 lines looking up DIN 6885 ...
    # ... 50 lines validating rim thickness ...
    # ... 80 lines validating keyway ...

# AFTER (decomposed):
def _calculate_effective_rim(bore_diameter: float, root_diameter: float,
                             keyway_depth: float = 0) -> float:
    """
    Calculate effective rim thickness accounting for features.

    The effective rim is the thinnest point of material between the bore
    and the outer surface, reduced by any keyway depth.

    Args:
        bore_diameter: Bore diameter in mm
        root_diameter: Root diameter (worm) or inner rim diameter (wheel) in mm
        keyway_depth: Depth of keyway cut into hub (mm), default 0

    Returns:
        Effective rim thickness in mm
    """
    return (root_diameter / 2) - (bore_diameter / 2) - keyway_depth

def _validate_bore(design, messages):
    """Validate bore dimensions and features. Now ~50 lines."""
    rim = _calculate_effective_rim(...)
    keyway_dims = _lookup_din6885_keyway(...)
    _validate_rim_thickness(rim, "worm", messages)
    _validate_keyway_compatibility(keyway_dims, bore_diameter, messages)
```

**Verification**:
- [ ] Each target function reduced to <100 lines
- [ ] Extracted helpers have comprehensive docstrings
- [ ] All extracted helpers have unit tests
- [ ] No behavior changes (existing tests pass)

---

### P2.3: Create Torture Test Suite

**Priority**: MEDIUM - Robustness validation
**Location**: Create `tests/test_torture.py`
**Effort**: 6 hours

**Task**: Create systematic tests of extreme parameter combinations.

**Create `tests/test_torture.py`**:
```python
"""
Torture tests for wormgear geometry generation.

These tests combine extreme parameters and multiple features to verify
robustness under challenging conditions. Tests are marked as slow and
may take several minutes to complete.
"""
import pytest
from itertools import product
from wormgear.calculator import design_from_module
from wormgear.core import WormGeometry, WheelGeometry, GloboidWormGeometry
from wormgear.core.virtual_hobbing import VirtualHobbingWheelGeometry
from wormgear.core.features import BoreFeature, KeywayFeature, SetScrewFeature


class TestExtremeParameters:
    """Test extreme parameter values."""

    EXTREME_MODULES = [0.5, 1.0, 2.0, 5.0]
    EXTREME_RATIOS = [10, 30, 60, 100]
    EXTREME_PROFILE_SHIFTS = [0.0, 0.3, 0.5]

    @pytest.mark.slow
    @pytest.mark.parametrize("module,ratio,profile_shift", [
        (0.5, 60, 0.3),   # Small module, high ratio
        (5.0, 10, 0.0),   # Large module, low ratio
        (1.0, 100, 0.5),  # High ratio with profile shift
        (0.5, 100, 0.5),  # Small + high ratio + shift (hardest)
    ])
    def test_extreme_parameter_combinations(self, module, ratio, profile_shift):
        """Extreme parameter combinations should produce valid geometry."""
        try:
            design = design_from_module(module, ratio, profile_shift=profile_shift)

            worm = WormGeometry(
                params=design.worm,
                assembly_params=design.assembly,
                length=40
            ).build()

            wheel = WheelGeometry(
                params=design.wheel,
                worm_params=design.worm,
                assembly_params=design.assembly
            ).build()

            assert worm.is_valid, f"Worm invalid for m={module}, r={ratio}, x={profile_shift}"
            assert wheel.is_valid, f"Wheel invalid for m={module}, r={ratio}, x={profile_shift}"

        except ValueError as e:
            # Acceptable if error is meaningful
            assert "impossible" in str(e).lower() or \
                   "invalid" in str(e).lower() or \
                   "cannot" in str(e).lower(), \
                   f"Error should be descriptive: {e}"


class TestFeatureCombinations:
    """Test multiple features combined."""

    @pytest.mark.slow
    def test_all_features_combined(self):
        """Worm with all features should produce valid geometry."""
        design = design_from_module(2.0, 30)

        worm = WormGeometry(
            params=design.worm,
            assembly_params=design.assembly,
            length=40,
            bore=BoreFeature(diameter=8.0),
            keyway=KeywayFeature(),
            set_screw=SetScrewFeature(count=2, size="M3")
        ).build()

        assert worm.is_valid
        # Verify material was removed (volume check)
        worm_basic = WormGeometry(
            params=design.worm,
            assembly_params=design.assembly,
            length=40
        ).build()
        assert worm.volume < worm_basic.volume * 0.95, "Features should remove material"

    @pytest.mark.slow
    def test_small_bore_with_features(self):
        """Small bore with keyway should work or fail gracefully."""
        design = design_from_module(2.0, 30)

        try:
            worm = WormGeometry(
                params=design.worm,
                assembly_params=design.assembly,
                length=40,
                bore=BoreFeature(diameter=6.0),  # Minimum for DIN 6885
                keyway=KeywayFeature()
            ).build()
            assert worm.is_valid
        except ValueError as e:
            # Acceptable if error explains the issue
            assert "keyway" in str(e).lower() or "bore" in str(e).lower()


class TestGloboidTortureScenarios:
    """Torture tests for globoid worm geometry."""

    @pytest.mark.slow
    def test_globoid_with_features(self):
        """Globoid worm with bore and keyway."""
        design = design_from_module(2.0, 30)

        globoid = GloboidWormGeometry(
            params=design.worm,
            assembly_params=design.assembly,
            wheel_pitch_diameter=design.wheel.pitch_diameter_mm,
            length=40,
            bore=BoreFeature(diameter=8.0),
            keyway=KeywayFeature()
        ).build()

        assert globoid.is_valid

    @pytest.mark.slow
    def test_globoid_extreme_throat(self):
        """Globoid with aggressive throat reduction."""
        design = design_from_module(2.0, 30)

        # Manually set aggressive throat reduction
        design.worm.throat_reduction_mm = design.worm.pitch_diameter_mm * 0.15

        try:
            globoid = GloboidWormGeometry(
                params=design.worm,
                assembly_params=design.assembly,
                wheel_pitch_diameter=design.wheel.pitch_diameter_mm,
                length=40
            ).build()
            assert globoid.is_valid
        except ValueError as e:
            assert "throat" in str(e).lower()


class TestVirtualHobbingTorture:
    """Torture tests for virtual hobbing."""

    @pytest.mark.slow
    def test_virtual_hobbing_high_steps(self):
        """Virtual hobbing with high step count."""
        design = design_from_module(2.0, 30)

        wheel = VirtualHobbingWheelGeometry(
            params=design.wheel,
            worm_params=design.worm,
            assembly_params=design.assembly,
            hobbing_steps=144  # High quality
        ).build()

        assert wheel.is_valid

    @pytest.mark.slow
    def test_virtual_hobbing_with_globoid_hob(self):
        """Virtual hobbing using globoid worm as hob."""
        design = design_from_module(2.0, 30)

        # Create globoid worm as hob
        globoid_hob = GloboidWormGeometry(
            params=design.worm,
            assembly_params=design.assembly,
            wheel_pitch_diameter=design.wheel.pitch_diameter_mm,
            length=30
        ).build()

        wheel = VirtualHobbingWheelGeometry(
            params=design.wheel,
            worm_params=design.worm,
            assembly_params=design.assembly,
            hob_geometry=globoid_hob,
            hobbing_steps=36  # Reduced for globoid
        ).build()

        assert wheel.is_valid


class TestScaleMismatch:
    """Test extreme scale differences."""

    @pytest.mark.slow
    def test_tiny_worm_large_wheel(self):
        """Very small worm with relatively large wheel."""
        design = design_from_module(0.5, 100)  # 0.5mm module, 100:1 ratio

        worm = WormGeometry(
            params=design.worm,
            assembly_params=design.assembly,
            length=20
        ).build()

        wheel = WheelGeometry(
            params=design.wheel,
            worm_params=design.worm,
            assembly_params=design.assembly
        ).build()

        assert worm.is_valid
        assert wheel.is_valid

        # Verify scale difference
        scale_ratio = wheel.bounding_box().diagonal_length / worm.bounding_box().diagonal_length
        assert scale_ratio > 5, "Wheel should be significantly larger than worm"


# Run torture tests with: pytest tests/test_torture.py -v --slow
```

**Verification**:
- [ ] Test file created with all scenarios
- [ ] Tests run (mark slow tests appropriately)
- [ ] Document any failures as known issues
- [ ] Add to CI with appropriate timeout

---

### P2.4: Implement Schema Migration Logic

**Priority**: MEDIUM - Backward compatibility for saved designs
**Location**: `src/wormgear/io/schema.py`
**Effort**: 4 hours

**Task**: Implement proper schema versioning and migration.

**Update `schema.py`**:
```python
"""
Schema versioning and migration for wormgear designs.

Handles:
- Version detection from JSON data
- Migration between schema versions
- Backward compatibility for old designs

Version History:
- 1.0 (2025-01): Initial schema
- 2.0 (2026-01): Added features section, Pydantic V2, schema-first workflow
"""

from typing import Dict, Any, Optional
from packaging.version import Version

SCHEMA_VERSION = "2.0"

# Minimum supported version for migration
MIN_SUPPORTED_VERSION = "1.0"


def detect_schema_version(data: Dict[str, Any]) -> str:
    """
    Detect schema version from JSON data.

    Args:
        data: Parsed JSON data

    Returns:
        Version string (e.g., "1.0", "2.0")
    """
    explicit_version = data.get('schema_version')
    if explicit_version:
        return str(explicit_version)

    # Heuristics for version detection
    if 'features' in data:
        return "2.0"  # features section added in 2.0
    if 'manufacturing' in data and 'worm_features' in data.get('manufacturing', {}):
        return "1.5"  # Transitional version

    return "1.0"  # Default to oldest


def upgrade_schema(data: Dict[str, Any],
                   target_version: str = SCHEMA_VERSION) -> Dict[str, Any]:
    """
    Upgrade schema data to target version.

    Applies migrations sequentially from current version to target.

    Args:
        data: JSON data to upgrade
        target_version: Target schema version

    Returns:
        Upgraded data (new dict, original not modified)

    Raises:
        ValueError: If current version is not supported or newer than target
    """
    import copy
    data = copy.deepcopy(data)  # Don't modify original

    current = detect_schema_version(data)
    target = target_version

    if Version(current) > Version(target):
        raise ValueError(
            f"Cannot downgrade schema from {current} to {target}. "
            f"Use an older version of wormgear to read this file."
        )

    if Version(current) < Version(MIN_SUPPORTED_VERSION):
        raise ValueError(
            f"Schema version {current} is too old. "
            f"Minimum supported version is {MIN_SUPPORTED_VERSION}."
        )

    # Apply migrations in order
    if Version(current) < Version("2.0") and Version(target) >= Version("2.0"):
        data = _migrate_1x_to_2x(data)

    data['schema_version'] = target
    return data


def _migrate_1x_to_2x(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Migrate from schema 1.x to 2.x.

    Changes:
    - Move worm_features/wheel_features from manufacturing to features section
    - Normalize enum values to lowercase
    - Add missing required fields with defaults
    """
    # 1. Move features from manufacturing to features section
    manufacturing = data.get('manufacturing', {})

    if 'worm_features' in manufacturing or 'wheel_features' in manufacturing:
        if 'features' not in data:
            data['features'] = {}

        if 'worm_features' in manufacturing:
            data['features']['worm'] = manufacturing.pop('worm_features')

        if 'wheel_features' in manufacturing:
            data['features']['wheel'] = manufacturing.pop('wheel_features')

    # 2. Normalize hand enum (was uppercase in some 1.x versions)
    for section in ['worm', 'assembly']:
        if section in data and 'hand' in data[section]:
            data[section]['hand'] = data[section]['hand'].lower()

    # 3. Normalize profile enum
    if 'manufacturing' in data and 'profile' in data['manufacturing']:
        data['manufacturing']['profile'] = data['manufacturing']['profile'].upper()

    # 4. Ensure features section exists with defaults
    if 'features' not in data:
        data['features'] = {
            'worm': {'bore_type': 'none'},
            'wheel': {'bore_type': 'none'}
        }

    return data


def validate_schema_version(data: Dict[str, Any]) -> bool:
    """
    Check if schema version is supported.

    Args:
        data: JSON data to check

    Returns:
        True if version is supported
    """
    version = detect_schema_version(data)
    return Version(MIN_SUPPORTED_VERSION) <= Version(version) <= Version(SCHEMA_VERSION)
```

**Test migrations**:
```python
def test_migration_1x_to_2x():
    """Schema 1.x should migrate to 2.x."""
    v1_data = {
        "schema_version": "1.0",
        "worm": {"hand": "RIGHT", "module_mm": 2.0},
        "wheel": {"num_teeth": 30},
        "assembly": {"hand": "RIGHT"},
        "manufacturing": {
            "profile": "za",
            "worm_features": {"bore_type": "custom", "bore_diameter_mm": 8.0}
        }
    }

    migrated = upgrade_schema(v1_data, "2.0")

    # Version updated
    assert migrated['schema_version'] == "2.0"

    # Features moved
    assert 'worm_features' not in migrated.get('manufacturing', {})
    assert migrated['features']['worm']['bore_type'] == "custom"

    # Hand normalized to lowercase
    assert migrated['worm']['hand'] == "right"

    # Profile normalized to uppercase
    assert migrated['manufacturing']['profile'] == "ZA"


def test_migration_preserves_data():
    """Migration should not lose any data."""
    v1_data = {...}  # Complete v1 design

    migrated = upgrade_schema(v1_data, "2.0")

    # All original sections present
    assert 'worm' in migrated
    assert 'wheel' in migrated
    assert 'assembly' in migrated

    # Original values preserved
    assert migrated['worm']['module_mm'] == v1_data['worm']['module_mm']
```

**Verification**:
- [ ] Migration logic implemented
- [ ] Tests for each migration path
- [ ] Old JSON files can be loaded
- [ ] Round-trip (load v1 → save v2 → load v2) preserves data

---

### P2.5: Optimize JSON Serialization

**Priority**: MEDIUM - 10-20% response size reduction
**Location**: `src/wormgear/calculator/output.py` and `src/wormgear/calculator/js_bridge.py`
**Effort**: 3 hours

**Task**: Eliminate redundant serialization and reduce payload size.

**Optimization 1: Use Pydantic's model_dump_json directly**
```python
# In output.py, replace:
def to_json(design: WormGearDesign, ...) -> str:
    data = design.model_dump(exclude_none=True)
    data['schema_version'] = SCHEMA_VERSION
    # ... manual enum conversion ...
    return json.dumps(data)

# With:
def to_json(design: WormGearDesign, ...) -> str:
    """Serialize design to JSON string."""
    # Create wrapper with version
    output_data = {
        'schema_version': SCHEMA_VERSION,
        **design.model_dump(mode='json', exclude_none=True)
    }
    return json.dumps(output_data, separators=(',', ':'))  # Compact
```

**Optimization 2: Optional response components**
```python
# In js_bridge.py, add option to exclude verbose components:
class CalculatorOptions(BaseModel):
    """Options for calculator response."""
    include_markdown: bool = True
    include_summary: bool = True
    include_design_json: bool = True
    compact_json: bool = False  # Use minimal whitespace

def calculate(input_json: str, options_json: Optional[str] = None) -> str:
    options = CalculatorOptions.model_validate_json(options_json) if options_json else CalculatorOptions()

    # ... calculation ...

    output = CalculatorOutput(
        success=True,
        design_json=to_json(design) if options.include_design_json else None,
        summary=to_summary(design) if options.include_summary else None,
        markdown=to_markdown(design, validation) if options.include_markdown else None,
        # ...
    )
```

**Optimization 3: Separate endpoints for different data needs**
```python
# For web UI that only needs validation messages:
def calculate_quick(input_json: str) -> str:
    """Fast calculation returning only validation results."""
    # ... calculation ...
    return CalculatorQuickOutput(
        success=True,
        valid=validation.valid,
        messages=[...],
        recommended_bores=(worm_bore, wheel_bore)
    ).model_dump_json()

# For full design export:
def calculate_full(input_json: str) -> str:
    """Full calculation with design JSON, markdown, etc."""
    # ... existing logic ...
```

**Test payload sizes**:
```python
def test_json_output_size():
    """JSON output should be reasonably compact."""
    design = design_from_module(2.0, 30)
    json_str = to_json(design)

    # Design JSON should be < 10KB
    assert len(json_str) < 10000, f"Design JSON too large: {len(json_str)} bytes"

    # Compact mode should be smaller
    json_compact = to_json(design, compact=True)
    assert len(json_compact) < len(json_str)
```

**Verification**:
- [ ] Redundant serialization eliminated
- [ ] Optional components implemented
- [ ] Payload size reduced by 10-20%
- [ ] All existing functionality preserved

---

## Pre-Implementation Checklist

Before starting ANY task in this plan:

- [ ] Read `/CLAUDE.md` completely (especially "What NOT To Do" and "Pre-Push Checklist")
- [ ] Read `/docs/ARCHITECTURE.md` to understand layer boundaries
- [ ] Identify which layer(s) your changes affect
- [ ] Plan the complete change before writing code

After completing ANY task:

- [ ] Run `pytest tests/ -v` - all tests pass
- [ ] Run `bash scripts/typecheck.sh` - no type errors
- [ ] If Pydantic models changed:
  - [ ] Run `python scripts/generate_schemas.py`
  - [ ] Run `bash scripts/generate_types.sh`
  - [ ] Stage schemas/*.json and web/types/*.generated.d.ts
- [ ] Test CLI locally:
  ```bash
  python -c "from wormgear.calculator import design_from_module, to_json; print(to_json(design_from_module(2.0, 30))[:200])"
  ```
- [ ] If web changes, test in browser:
  ```bash
  cd web && ./build.sh && python -m http.server 8000
  # Open localhost:8000, test calculator
  ```
- [ ] Commit with descriptive message citing this plan:
  ```
  fix: Add sqrt() guard in throated wheel calculation

  Prevents crash when z_pos approaches arc_radius boundary.
  Part of P0.1 from TECH_DEBT_REMEDIATION_PLAN.md

  Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
  ```

---

## Progress Tracking

Use this table to track completion:

| Item | Status | Date | Notes |
|------|--------|------|-------|
| P0.1 sqrt() guard | ⬜ | | |
| P0.2 Division guard | ⬜ | | |
| P0.3 Hobbing limit | ⬜ | | |
| P0.4 Docstring | ⬜ | | |
| P1.1 Constants | ⬜ | | |
| P1.2 Contact ratio | ⬜ | | |
| P1.3 Set screw tests | ⬜ | | |
| P1.4 Hub tests | ⬜ | | |
| P1.5 Feature fix | ⬜ | | |
| P1.6 BoreType enum | ⬜ | | |
| P2.1 Hobbing perf | ⬜ | | |
| P2.2 Decompose funcs | ⬜ | | |
| P2.3 Torture tests | ⬜ | | |
| P2.4 Schema migration | ⬜ | | |
| P2.5 JSON optimization | ⬜ | | |

Legend: ⬜ Not started | 🔄 In progress | ✅ Complete | ❌ Blocked
