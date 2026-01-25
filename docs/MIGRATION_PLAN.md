# Migration Plan: Unified Worm Gear Package

## Overview

Migrate from current architecture (split repos) to unified 4-layer architecture in single repository.

**Timeline Estimate**: 2-3 weeks (can be done incrementally)
**Risk Level**: Medium (breaking changes for existing users)
**Backwards Compatibility**: Can be maintained with deprecation warnings

---

## Current State

### Repository: worm-gear-3d (this repo)
```
worm-gear-3d/
├── src/wormgear_geometry/
│   ├── worm.py              # Geometry classes
│   ├── wheel.py
│   ├── globoid_worm.py
│   ├── virtual_hobbing.py
│   ├── features.py          # Bore, keyway, DD-cut, etc.
│   ├── io.py                # JSON loaders
│   ├── cli.py               # CLI interface
│   └── calculations/        # Stubs for calculator integration
│       ├── globoid.py
│       └── schema.py
├── tests/
└── examples/
```

**Lines of Code**: ~5,000
**Dependencies**: build123d, OCP

### Repository: wormgearcalc (external)
```
wormgearcalc/
├── src/
│   ├── calculations.js      # Core calculations
│   ├── constraints.js       # DIN 3975 constraints
│   ├── validation.js        # Input validation
│   └── ui/                  # Web UI components
├── docs/
│   └── engineering/         # Engineering documentation
└── examples/
```

**Lines of Code**: ~3,000 (estimated)
**Language**: JavaScript (needs Python port)
**Dependencies**: None (pure JS)

---

## Target State

### New Repository Structure: wormgear

```
wormgear/
├── src/wormgear/
│   ├── __init__.py
│   ├── core/                    # Layer 1: Pure geometry engine
│   │   ├── __init__.py
│   │   ├── parameters.py        # Dataclasses (WormParams, etc.)
│   │   ├── validation.py        # Parameter validation
│   │   ├── worm.py              # WormGeometry class
│   │   ├── wheel.py             # WheelGeometry class
│   │   ├── globoid_worm.py      # GloboidWormGeometry
│   │   ├── virtual_hobbing.py   # VirtualHobbingWheelGeometry
│   │   ├── features.py          # BoreFeature, KeywayFeature, etc.
│   │   └── profiles.py          # Tooth profiles (ZA, ZK, ZI)
│   │
│   ├── calculator/              # Layer 2a: Calculator (from wormgearcalc)
│   │   ├── __init__.py
│   │   ├── constraints.py       # DIN 3975, ISO constraints
│   │   ├── solver.py            # Calculate params from user inputs
│   │   ├── recommendations.py   # Auto-calculate lengths, widths
│   │   ├── globoid.py           # Globoid-specific calculations
│   │   ├── validation.py        # Input validation & warnings
│   │   └── presets.py           # Common gear configurations
│   │
│   ├── io/                      # Layer 2b: JSON & outputs
│   │   ├── __init__.py
│   │   ├── schema.py            # JSON schema v1.0 definition
│   │   ├── loaders.py           # load_design_json, save_design_json
│   │   ├── exporters.py         # Export specs, reports
│   │   └── validators.py        # JSON schema validation
│   │
│   └── cli/                     # Layer 3: Command-line interfaces
│       ├── __init__.py
│       ├── calculate.py         # Calculator CLI (inputs → JSON)
│       ├── generate.py          # Geometry CLI (JSON → STEP)
│       └── main.py              # Unified CLI entry point
│
├── tests/
│   ├── core/                    # Core geometry tests
│   ├── calculator/              # Calculator tests (ported from JS)
│   ├── io/                      # JSON tests
│   └── integration/             # End-to-end tests
│
├── docs/
│   ├── api/                     # API documentation
│   ├── engineering/             # Engineering docs (from wormgearcalc)
│   ├── tutorials/               # User guides
│   └── migration/               # Migration guides for existing users
│
├── examples/
│   ├── python_api/              # Core API usage
│   ├── json_designs/            # Example JSON files
│   └── cli_workflows/           # CLI examples
│
├── web/                         # Layer 3: Web interfaces (future)
│   ├── calculator/              # Lightweight WASM (no build123d)
│   └── viewer/                  # Heavy WASM (with build123d)
│
├── pyproject.toml
├── README.md
├── CLAUDE.md
└── MIGRATION.md                 # This file
```

**Lines of Code**: ~8,000 (combined + refactored)

---

## Migration Phases

### Phase 1: Prepare Foundation (Week 1)

**Objective**: Set up new structure without breaking existing code

#### 1.1 Create New Directory Structure
- [ ] Create `src/wormgear/core/` directory
- [ ] Create `src/wormgear/calculator/` directory
- [ ] Create `src/wormgear/io/` directory (rename from root)
- [ ] Create `src/wormgear/cli/` directory
- [ ] Update `pyproject.toml` package name: `wormgear_geometry` → `wormgear`

**Files to create:**
```
src/wormgear/
  core/__init__.py
  calculator/__init__.py
  io/__init__.py
  cli/__init__.py
```

**Risk**: Import paths change → **Mitigation**: Maintain old paths with deprecation warnings

#### 1.2 Move Existing Code to core/

**Move (no changes yet):**
```
worm.py → core/worm.py
wheel.py → core/wheel.py
globoid_worm.py → core/globoid_worm.py
virtual_hobbing.py → core/virtual_hobbing.py
features.py → core/features.py
```

**Create new files:**
```
core/parameters.py    # Extract dataclasses from io.py
core/validation.py    # Extract validation functions
core/profiles.py      # Extract DIN 3975 profile logic
```

**Risk**: Circular imports → **Mitigation**: Careful dependency ordering

#### 1.3 Update io/ Module

**Move:**
```
io.py → io/loaders.py           # load_design_json, save_design_json
calculations/schema.py → io/schema.py
```

**Create new:**
```
io/exporters.py      # Export specs, reports (new functionality)
io/validators.py     # JSON schema validation (new functionality)
```

**Risk**: Breaking existing imports → **Mitigation**: Keep old imports with deprecation

#### 1.4 Update CLI

**Move:**
```
cli.py → cli/generate.py        # Geometry generation CLI
```

**Create new:**
```
cli/calculate.py     # Calculator CLI (new, from wormgearcalc logic)
cli/main.py          # Unified CLI with subcommands
```

**Risk**: CLI interface changes → **Mitigation**: Keep old CLI as default, new as opt-in

---

### Phase 2: Port Calculator (Week 2)

**Objective**: Port wormgearcalc JavaScript to Python

#### 2.1 Clone wormgearcalc Repository

```bash
cd /tmp
git clone https://github.com/pzfreo/wormgearcalc.git
```

**Analyze code:**
- Identify core calculation functions
- Map JS functions to Python equivalents
- Extract engineering constants

#### 2.2 Port Core Calculations

**Priority order:**
1. **constraints.py** - DIN 3975 standards, module ranges, tooth counts
2. **solver.py** - Calculate parameters from user inputs
3. **recommendations.py** - Auto-calculate lengths, widths, bore sizes
4. **globoid.py** - Globoid-specific throat calculations
5. **validation.py** - Input validation, error messages

**JavaScript → Python Mapping:**
```javascript
// wormgearcalc/src/calculations.js
function calculatePitchDiameter(module, numStarts, profileShift) {
  return module * (numStarts + 2 * profileShift);
}
```

**Becomes:**
```python
# wormgear/calculator/solver.py
def calculate_pitch_diameter(
    module_mm: float,
    num_starts: int,
    profile_shift: float = 0.0
) -> float:
    """Calculate worm pitch diameter per DIN 3975."""
    return module_mm * (num_starts + 2 * profile_shift)
```

**Migration approach:**
- Copy JS logic verbatim first (as comments)
- Translate to Python below comments
- Add type hints
- Add docstrings with DIN references
- Write unit tests (port from JS tests if available)

**Risk**: Translation errors → **Mitigation**:
- Test against known good designs from wormgearcalc examples
- Cross-validate calculations with engineering handbooks

#### 2.3 Port Engineering Documentation

**Copy from wormgearcalc:**
```
docs/engineering/ → docs/engineering/
  - DIN_3975.md
  - globoid_theory.md
  - manufacturing.md
```

**Update references:**
- Update code examples to Python
- Update file paths to new structure

#### 2.4 Create Calculator CLI

**New file: `cli/calculate.py`**

```python
"""
Calculator CLI - Convert user inputs to validated JSON design.

Usage:
  wormgear calculate --module 2.0 --ratio 30 --output design.json
  wormgear calculate --interactive  # Interactive mode
"""

import typer
from typing import Optional
from pathlib import Path

from ..calculator import solver, validation
from ..io import save_design_json

app = typer.Typer()

@app.command()
def calculate(
    module: float = typer.Option(..., help="Module in mm"),
    ratio: int = typer.Option(..., help="Gear ratio (e.g., 30:1)"),
    centre_distance: Optional[float] = typer.Option(None, help="Centre distance in mm"),
    worm_type: str = typer.Option("cylindrical", help="cylindrical or globoid"),
    output: Path = typer.Option("design.json", help="Output JSON file"),
    # ... more options
):
    """Calculate worm gear parameters from user inputs."""

    # Validate inputs
    errors = validation.validate_inputs(
        module_mm=module,
        ratio=ratio,
        # ...
    )

    if errors:
        for error in errors:
            typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(1)

    # Calculate design
    design = solver.solve_design(
        module_mm=module,
        ratio=ratio,
        centre_distance_mm=centre_distance,
        worm_type=worm_type,
        # ...
    )

    # Save JSON
    save_design_json(design, output)
    typer.echo(f"Design saved to {output}")
```

**Risk**: Complex interactive mode → **Mitigation**: Start with simple CLI, add interactive later

#### 2.5 Port Tests

**From wormgearcalc:**
- Copy test cases (inputs + expected outputs)
- Translate assertions to pytest

**Example:**
```python
# tests/calculator/test_solver.py
def test_calculate_30_1_ratio():
    """Test 30:1 ratio calculation (from wormgearcalc test suite)."""
    design = solver.solve_design(
        module_mm=2.0,
        ratio=30,
        num_starts=1
    )

    assert design.worm.num_starts == 1
    assert design.wheel.num_teeth == 30
    assert design.worm.pitch_diameter_mm == pytest.approx(16.29, abs=0.01)
    # ... more assertions
```

**Risk**: Missing test cases → **Mitigation**: Extract from wormgearcalc examples

---

### Phase 3: Integration & Polish (Week 3)

**Objective**: Integrate all layers, update documentation, ensure quality

#### 3.1 Create Unified CLI

**New file: `cli/main.py`**

```python
"""
Wormgear - Unified CLI for worm gear design and generation.

Commands:
  calculate    Calculate parameters from inputs → JSON
  generate     Generate 3D models from JSON → STEP files
  validate     Validate JSON design file
  spec         Generate engineering specifications
"""

import typer

from . import calculate
from . import generate

app = typer.Typer(
    name="wormgear",
    help="Worm gear calculator and 3D geometry generator"
)

# Add subcommands
app.add_typer(calculate.app, name="calculate")
app.add_typer(generate.app, name="generate")

@app.command()
def validate(design_file: Path):
    """Validate JSON design file against schema."""
    # ...

@app.command()
def spec(design_file: Path, output: Path):
    """Generate engineering specification document."""
    # ...

if __name__ == "__main__":
    app()
```

**Entry points in pyproject.toml:**
```toml
[project.scripts]
wormgear = "wormgear.cli.main:app"
# Backwards compatibility
wormgear-geometry = "wormgear.cli.generate:app"  # Old CLI
```

#### 3.2 Update Core API

**Simplify imports in `core/__init__.py`:**
```python
"""
Wormgear Core - Pure geometry generation API.

Example:
    from wormgear.core import WormGeometry, WormParams, AssemblyParams

    worm_params = WormParams(
        module_mm=2.0,
        num_starts=1,
        pitch_diameter_mm=16.29,
        # ...
    )

    assembly_params = AssemblyParams(
        centre_distance_mm=38.14,
        pressure_angle_deg=20.0,
        # ...
    )

    worm = WormGeometry(worm_params, assembly_params, length=40.0)
    part = worm.build()
    part.export_step("worm.step")
"""

from .parameters import (
    WormParams,
    WheelParams,
    AssemblyParams,
    Features,
    WormFeatures,
    WheelFeatures,
)
from .worm import WormGeometry
from .wheel import WheelGeometry
from .globoid_worm import GloboidWormGeometry
from .virtual_hobbing import VirtualHobbingWheelGeometry
from .features import (
    BoreFeature,
    KeywayFeature,
    DDCutFeature,
    SetScrewFeature,
    HubFeature,
)

__all__ = [
    # Parameters
    "WormParams",
    "WheelParams",
    "AssemblyParams",
    "Features",
    "WormFeatures",
    "WheelFeatures",
    # Geometry classes
    "WormGeometry",
    "WheelGeometry",
    "GloboidWormGeometry",
    "VirtualHobbingWheelGeometry",
    # Features
    "BoreFeature",
    "KeywayFeature",
    "DDCutFeature",
    "SetScrewFeature",
    "HubFeature",
]
```

#### 3.3 Documentation Updates

**Update README.md:**
```markdown
# Wormgear

Complete worm gear calculator and 3D geometry generator for CNC manufacturing.

## Features

- **Calculator**: Calculate worm gear parameters from user inputs
- **3D Generator**: Generate CNC-ready STEP files
- **Standards Compliant**: DIN 3975, ISO 54, DIN 6885
- **Flexible**: Python API, JSON, or CLI

## Installation

```bash
pip install wormgear
```

## Quick Start

### Calculate Parameters
```bash
wormgear calculate --module 2.0 --ratio 30 --output design.json
```

### Generate 3D Models
```bash
wormgear generate design.json
```

### Python API
```python
from wormgear.calculator import solve_design
from wormgear.core import WormGeometry

# Calculate parameters
design = solve_design(module_mm=2.0, ratio=30)

# Generate 3D model
worm = WormGeometry(design.worm, design.assembly, length=40)
worm.build().export_step("worm.step")
```

## Documentation

- [API Reference](docs/api/)
- [Engineering Background](docs/engineering/)
- [Tutorials](docs/tutorials/)
```

**Create migration guide: `docs/migration/v1.0.md`**
```markdown
# Migration Guide: wormgear-geometry → wormgear v1.0

## Breaking Changes

### Package Name
- **Old**: `wormgear_geometry`
- **New**: `wormgear`

### Import Paths
```python
# Old
from wormgear_geometry import WormGeometry, load_design_json

# New
from wormgear.core import WormGeometry
from wormgear.io import load_design_json
```

### CLI Command
- **Old**: `wormgear-geometry design.json`
- **New**: `wormgear generate design.json`

## Backwards Compatibility

Old imports still work with deprecation warnings:
```python
# Still works but warns
from wormgear_geometry import WormGeometry
```

To disable warnings:
```python
import warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)
```

## New Features

### Calculator CLI
```bash
# New in v1.0
wormgear calculate --module 2.0 --ratio 30
```

### Unified Package
Calculator and geometry generator now in one package.
```

#### 3.4 Update Tests

**Reorganize test structure:**
```
tests/
  core/
    test_worm.py           # From tests/test_worm.py
    test_wheel.py          # From tests/test_wheel.py
    test_globoid_worm.py
    test_features.py
    test_virtual_hobbing.py

  calculator/
    test_solver.py         # New (ported from wormgearcalc)
    test_constraints.py
    test_validation.py
    test_recommendations.py

  io/
    test_loaders.py        # From tests/test_io.py
    test_schema.py
    test_exporters.py      # New

  integration/
    test_end_to_end.py     # Calculate → Generate → Export
    test_examples.py       # Test all example JSON files
```

**Add integration tests:**
```python
# tests/integration/test_end_to_end.py
def test_calculate_and_generate():
    """Test full workflow: inputs → JSON → STEP files."""
    # Calculate design
    design = solver.solve_design(
        module_mm=2.0,
        ratio=30,
        worm_type="cylindrical"
    )

    # Save to JSON
    json_file = tmp_path / "design.json"
    save_design_json(design, json_file)

    # Load and generate
    loaded = load_design_json(json_file)
    worm = WormGeometry(loaded.worm, loaded.assembly, length=40)
    part = worm.build()

    # Verify
    assert part.is_valid
    assert part.volume > 0
```

#### 3.5 Update pyproject.toml

**Key changes:**
```toml
[project]
name = "wormgear"  # Changed from "wormgear-geometry"
version = "1.0.0"  # Major version bump
description = "Worm gear calculator and 3D geometry generator for CNC manufacturing"

# New dependencies
dependencies = [
    "build123d>=0.5.0",
    "typer>=0.9.0",  # New: for CLI
    "rich>=13.0.0",  # New: for pretty CLI output
    # ... existing deps
]

[project.optional-dependencies]
# Backwards compatibility
legacy = ["wormgear-geometry"]

# Development tools
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "black>=23.0.0",
    "ruff>=0.1.0",
]

[project.scripts]
wormgear = "wormgear.cli.main:app"
wormgear-geometry = "wormgear.cli.generate:app"  # Backwards compat

[tool.setuptools.packages.find]
where = ["src"]
include = ["wormgear*"]
```

---

## Backwards Compatibility Strategy

### Deprecation Shims

**Create: `src/wormgear_geometry/__init__.py`**
```python
"""
Backwards compatibility shim for wormgear_geometry.

DEPRECATED: Use 'wormgear' package instead.
This module will be removed in v2.0.
"""

import warnings

warnings.warn(
    "The 'wormgear_geometry' package is deprecated. "
    "Use 'wormgear' instead:\n"
    "  from wormgear.core import WormGeometry\n"
    "  from wormgear.io import load_design_json\n"
    "This compatibility shim will be removed in v2.0.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export everything from new locations
from wormgear.core import *
from wormgear.io import *
from wormgear.calculator import *

__all__ = [
    # ... all exports
]
```

### CLI Compatibility

Keep `wormgear-geometry` command working:
```bash
# Old command (still works)
wormgear-geometry design.json

# New command (preferred)
wormgear generate design.json
```

Both point to same code, old one shows deprecation notice.

---

## Risks & Mitigation

### High Risk Items

#### 1. JavaScript to Python Translation Errors

**Risk**: Calculator logic ported incorrectly from JS
**Probability**: Medium
**Impact**: High (incorrect calculations)

**Mitigation**:
- [ ] Port unit tests from wormgearcalc
- [ ] Test against known good designs from wormgearcalc examples
- [ ] Cross-validate with engineering handbooks
- [ ] Add extensive docstrings with DIN 3975 references
- [ ] Manual review by domain expert (you)

**Validation approach:**
```python
# Test against wormgearcalc reference outputs
REFERENCE_DESIGNS = [
    {
        "input": {"module": 2.0, "ratio": 30, "type": "cylindrical"},
        "expected": {
            "worm_pitch_diameter": 16.29,
            "wheel_pitch_diameter": 60.0,
            # ... from wormgearcalc
        }
    },
    # ... more reference cases
]

def test_against_reference():
    for ref in REFERENCE_DESIGNS:
        design = solver.solve_design(**ref["input"])
        assert design.worm.pitch_diameter_mm == pytest.approx(ref["expected"]["worm_pitch_diameter"])
```

#### 2. Breaking Changes for Existing Users

**Risk**: Users' code breaks after upgrade
**Probability**: High
**Impact**: Medium (frustration, support burden)

**Mitigation**:
- [ ] Maintain backwards compatibility shims for v1.x
- [ ] Clear migration guide with examples
- [ ] Deprecation warnings (not errors)
- [ ] Version bump to 1.0.0 signals breaking changes
- [ ] GitHub release notes with migration steps

**Communication plan:**
- [ ] Update README with prominent migration notice
- [ ] Add deprecation warnings to old imports
- [ ] Create GitHub issue template for migration help
- [ ] Tag existing users in GitHub discussion

#### 3. Import Circular Dependencies

**Risk**: New module structure creates circular imports
**Probability**: Medium
**Impact**: High (package won't import)

**Mitigation**:
- [ ] Careful dependency ordering (core → calculator → io → cli)
- [ ] Use TYPE_CHECKING for type hints
- [ ] Lazy imports where needed
- [ ] Thorough import testing

**Dependency rules:**
```
core/         # Can import: nothing (pure)
calculator/   # Can import: core
io/           # Can import: core, calculator
cli/          # Can import: core, calculator, io
```

### Medium Risk Items

#### 4. Missing Calculator Features

**Risk**: wormgearcalc has features we don't port
**Probability**: Medium
**Impact**: Medium (missing functionality)

**Mitigation**:
- [ ] Complete feature inventory of wormgearcalc
- [ ] Prioritize core features first
- [ ] Mark advanced features as "TODO: v1.1"
- [ ] Document what's missing in CHANGELOG

#### 5. Performance Regression

**Risk**: Python slower than JavaScript for calculations
**Probability**: Low
**Impact**: Low (calculations are fast anyway)

**Mitigation**:
- [ ] Benchmark calculation times
- [ ] Optimize hot paths if needed
- [ ] Document performance characteristics

#### 6. Test Coverage Gaps

**Risk**: Missing edge cases in ported tests
**Probability**: Medium
**Impact**: Medium (bugs in production)

**Mitigation**:
- [ ] Aim for >90% code coverage
- [ ] Port all wormgearcalc test cases
- [ ] Add property-based tests (hypothesis)
- [ ] Test error paths explicitly

### Low Risk Items

#### 7. Documentation Outdated

**Risk**: Docs reference old structure
**Probability**: Medium
**Impact**: Low (confusing but not breaking)

**Mitigation**:
- [ ] Update all docs in same PR as code changes
- [ ] Automated link checking
- [ ] Review by second person

#### 8. Example Files Obsolete

**Risk**: Example JSON files don't work with new code
**Probability**: Low (JSON schema unchanged)
**Impact**: Low

**Mitigation**:
- [ ] Run all examples through test suite
- [ ] Update examples if needed

---

## Testing Strategy

### Test Phases

#### Phase 1: Unit Tests (during porting)
```bash
# Test each module as it's ported
pytest tests/calculator/test_solver.py -v
pytest tests/core/ -v
```

#### Phase 2: Integration Tests
```bash
# Test layer interactions
pytest tests/integration/ -v
```

#### Phase 3: Regression Tests
```bash
# Test against old behavior
pytest tests/ --cov=wormgear --cov-report=html
# Coverage goal: >85%
```

#### Phase 4: Example Validation
```bash
# All examples must work
for file in examples/json_designs/*.json; do
    wormgear generate "$file" --no-save || exit 1
done
```

### Test Environments

```bash
# Test on multiple Python versions
tox -e py39,py310,py311,py312

# Test on different platforms
# - macOS (your dev machine)
# - Linux (GitHub Actions)
# - Windows (GitHub Actions - if users request)
```

---

## Rollout Plan

### Pre-Release Checklist

- [ ] All phases complete
- [ ] Test coverage >85%
- [ ] All examples working
- [ ] Documentation updated
- [ ] Migration guide written
- [ ] CHANGELOG.md updated
- [ ] Version bumped to 1.0.0

### Release Process

#### 1. Create Release Branch
```bash
git checkout -b release/v1.0.0
```

#### 2. Final Testing
```bash
# Run full test suite
pytest tests/ -v --cov=wormgear --cov-report=term-missing

# Test examples
./scripts/test_examples.sh

# Test CLI
wormgear calculate --help
wormgear generate --help
```

#### 3. Build & Test Package
```bash
# Build package
python -m build

# Test install in clean environment
python -m venv test_env
source test_env/bin/activate
pip install dist/wormgear-1.0.0-py3-none-any.whl

# Verify imports
python -c "from wormgear.core import WormGeometry; print('OK')"
python -c "from wormgear.calculator import solve_design; print('OK')"

# Test backwards compat
python -c "from wormgear_geometry import WormGeometry; print('OK (with warning)')"
```

#### 4. Tag & Release
```bash
git tag -a v1.0.0 -m "Release v1.0.0: Unified calculator + geometry package"
git push origin v1.0.0
```

#### 5. GitHub Release
Create release on GitHub with:
- CHANGELOG excerpt
- Migration guide link
- Breaking changes highlighted
- Download links

#### 6. PyPI Upload
```bash
python -m twine upload dist/*
```

### Post-Release

- [ ] Update README badges (version, PyPI link)
- [ ] Announce on GitHub Discussions
- [ ] Monitor GitHub issues for migration problems
- [ ] Update wormgearcalc README to point to new package

---

## Contingency Plans

### If JavaScript Port is Too Complex

**Fallback**: Keep wormgearcalc separate, just improve integration

**Plan B Structure:**
```bash
# Keep separate but improve connection
pip install wormgearcalc wormgear

# wormgearcalc outputs JSON
wormgearcalc calculate --module 2.0 --ratio 30 > design.json

# wormgear consumes JSON
wormgear generate design.json
```

**Pros**: Less migration work
**Cons**: Two packages, version coordination

### If Backwards Compatibility is Critical

**Fallback**: Keep both packages, new as "wormgear-v2"

**Approach**:
- Publish new package as `wormgear` (no breaking changes)
- Keep `wormgear-geometry` frozen at current version
- Users opt-in to new package

### If Timeline Slips

**Phased Rollout**:
- **Phase 1**: Just reorganize (no calculator) - ship as v0.9
- **Phase 2**: Add calculator - ship as v1.0
- **Phase 3**: Add web interface - ship as v1.1

---

## Success Criteria

### Must Have (v1.0)
- [ ] All existing geometry features working
- [ ] Calculator ported (basic functionality)
- [ ] CLI working (both commands)
- [ ] Test coverage >80%
- [ ] Documentation complete
- [ ] Zero errors on fresh install

### Should Have (v1.0)
- [ ] Calculator ported (advanced features)
- [ ] Backwards compatibility shims
- [ ] Migration guide
- [ ] Example workflows
- [ ] Test coverage >90%

### Nice to Have (v1.1+)
- [ ] Interactive calculator mode
- [ ] Web interface (WASM)
- [ ] Performance optimizations
- [ ] Additional output formats

---

## Decision Points

### Need Your Approval On:

1. **Merge repos now or keep separate initially?**
   - Recommended: Merge now (cleaner, easier to maintain)
   - Alternative: Keep separate until calculator port proven

2. **Break backwards compatibility or maintain shims?**
   - Recommended: Maintain shims for v1.x (smoother migration)
   - Alternative: Clean break (simpler code)

3. **Port all calculator features or start minimal?**
   - Recommended: Start minimal (basic ratio calculator)
   - Alternative: Port everything (more complete but slower)

4. **Version number?**
   - Recommended: v1.0.0 (signals breaking changes)
   - Alternative: v0.9.0 (beta period)

5. **Package name?**
   - Recommended: `wormgear` (shorter, cleaner)
   - Alternative: `wormgear-unified`, `wormgears`

---

## Questions for You

1. Do you have access to wormgearcalc test suite/expected outputs?
2. Are there features in wormgearcalc you want to deprioritize?
3. Any users you need to notify about breaking changes?
4. Should we keep wormgearcalc repo alive or archive it?
5. Timeline constraints? (Can we take 2-3 weeks?)

---

## Next Steps (After Approval)

1. Create new branch: `feature/unified-package`
2. Start Phase 1 (foundation)
3. Daily commits with progress updates
4. Request review at end of each phase
5. Final review before merge to main

---

**Ready to proceed?** Please review and approve/modify this plan.
