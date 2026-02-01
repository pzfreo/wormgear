# CLAUDE.md - Wormgear Development Guide

## Project Summary

**Wormgear** - Unified Python package for complete worm gear design: engineering calculations to CNC-ready STEP files.

**Owner**: Paul Fremantle (pzfreo) - luthier and hobby programmer
**Use cases**:
- Custom worm gears for luthier (violin making) applications
- CNC machining of exact gear geometry
- 3D printing of functional gears (FDM, SLA, SLS)
- Educational and research applications

## 🛑 STOP - READ BEFORE EDITING DATA MODELS

**Before modifying ANY of these files, STOP and plan the full workflow:**

| File | Contains |
|------|----------|
| `src/wormgear/io/loaders.py` | Pydantic models (WormParams, WheelParams, Features, etc.) |
| `src/wormgear/enums.py` | Enums (Hand, WormType, WormProfile, BoreType) |
| `src/wormgear/calculator/js_bridge.py` | Bridge models (CalculatorInputs, CalculatorOutput, BoreSettings) |

**MANDATORY workflow for ANY change to these files:**

```bash
# 1. Edit the Pydantic model
# 2. Regenerate JSON schemas
python scripts/generate_schemas.py
# 3. Regenerate TypeScript types
bash scripts/generate_types.sh
# 4. Update JS code to use the new types (if structural change)
# 5. Run type checking
bash scripts/typecheck.sh
# 6. Run tests
pytest tests/
# 7. Commit ALL together: models + schemas/*.json + web/types/*.generated.d.ts
```

**If you skip steps 2-3, the JS code will be out of sync with Python and bugs WILL occur.**

---

## ⚠️ CRITICAL: Schema-First Architecture (MANDATORY)

**Rule**: ALL data structures crossing Python↔JavaScript boundaries MUST use the schema-first workflow.

### Schema Workflow (ALWAYS FOLLOW)

1. **Define in Python using Pydantic models** (`src/wormgear/io/loaders.py`)
   - Single source of truth for data structures
   - Type-safe with enums from `src/wormgear/enums.py`
   - Built-in validation with Pydantic validators

2. **Generate JSON Schema** (from Pydantic models)
   ```bash
   python scripts/generate_schemas.py
   # Outputs: schemas/wormgear-design-v2.0.json, schemas/enums-v2.0.json, etc.
   ```

3. **Generate TypeScript types** (from JSON schemas)
   ```bash
   cd web && npm install  # First time only
   bash scripts/generate_types.sh
   # Outputs: web/types/wormgear-design.generated.d.ts, web/types/enums.generated.d.ts
   ```

4. **Use generated types in web code**
   ```typescript
   import { WormGearDesign, WormParams } from './types/wormgear-design.generated';
   const design: WormGearDesign = { ... };  // Compile-time type checking
   ```

### When to Update Schemas

**ALWAYS update schemas when you:**
- Add a new field to any dataclass/model
- Change a field type
- Add or modify an enum
- Change validation constraints (Field min/max/pattern)
- Add a new API endpoint or data structure

**How to update:**
```bash
# 1. Edit Pydantic models in src/wormgear/io/loaders.py (or enums in src/wormgear/enums.py)
# 2. Regenerate schemas
python scripts/generate_schemas.py
# 3. Regenerate TypeScript types
bash scripts/generate_types.sh
# 4. Run type checking
bash scripts/typecheck.sh
# 5. Run tests
pytest tests/
# 6. Commit all: loaders.py + schemas/*.json + web/types/*.generated.d.ts
```

### Type Checking

**Python (mypy)**:
```bash
mypy src/wormgear                    # Check all Python code
bash scripts/typecheck.sh python     # Or use the helper script
```

**TypeScript (tsc)**:
```bash
cd web && npm run typecheck          # Check web code
bash scripts/typecheck.sh ts         # Or use the helper script
```

**Both**:
```bash
bash scripts/typecheck.sh            # Run both Python and TypeScript checks
```

Type checking catches:
- Enum/string mismatches
- Missing or extra fields
- Type coercion issues
- Incompatible function signatures

### Schema Versioning

**Current Version: 2.0** (as of January 2026)

**Version Format**: `MAJOR.MINOR` (e.g., "2.0", "2.1", "3.0")

**When to bump versions:**
- **MAJOR version** (2.0 → 3.0): Breaking changes
  - Remove a required field
  - Change a field's type (e.g., string → number)
  - Rename a field
  - Change enum values
  - Change field semantics (meaning changes even if type doesn't)

- **MINOR version** (2.0 → 2.1): Non-breaking additions
  - Add a new optional field
  - Add a new enum value (if consumers ignore unknown values)
  - Add new validation constraints that existing data satisfies
  - Add new optional sections

**Version bump checklist:**
```bash
# 1. Update SCHEMA_VERSION in src/wormgear/io/schema.py
SCHEMA_VERSION = "2.1"  # or "3.0" for breaking changes

# 2. Update version in Pydantic model docstrings if applicable

# 3. Regenerate all schemas (they include version in filename)
python scripts/generate_schemas.py
# Creates: schemas/wormgear-design-v2.1.json, etc.

# 4. Regenerate TypeScript types
bash scripts/generate_types.sh

# 5. Update any hardcoded version references in:
#    - web/modules/pyodide-init.js (if loading specific schema version)
#    - README.md (if documenting schema)
#    - tests (if asserting specific version)

# 6. For MAJOR versions: Add migration logic in upgrade_schema()
```

**Version history:**
| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-01 | Initial schema with worm/wheel/assembly sections |
| 2.0 | 2026-01 | Added features section, manufacturing params, Pydantic V2 |

**Files that contain version:**
- `src/wormgear/io/schema.py` - SCHEMA_VERSION constant
- `schemas/*-v{VERSION}.json` - Generated schema files (version in filename)
- JSON output - `schema_version` field in all exported designs

### What NOT to Do

❌ **Manual JSON Schema maintenance** - Schemas are GENERATED from Pydantic, never hand-edited
❌ **Manual TypeScript type definitions** - Types are GENERATED from schemas, never hand-written
❌ **Duplicate definitions** - Python models are the ONLY source of truth
❌ **Skip schema regeneration** - ALWAYS regenerate after model changes
❌ **Commit models without schemas** - Models, schemas, and types must stay in sync

## ⚠️ CRITICAL: Lessons Learned - What NOT To Do

**Context**: During January 2026 refactor attempt, several critical mistakes were made that wasted significant development time. These lessons MUST be remembered to avoid repeating them.

### 1. NEVER Remove Type Safety

**What happened**: During unified package creation (commit 3e9c311), proper Python enums were converted to plain strings:

```python
# BEFORE (web/wormcalc/ - GOOD):
class Hand(Enum):
    RIGHT = "right"
    LEFT = "left"

hand: Hand  # Type-safe, autocomplete, catches typos

# AFTER (unified package - BAD):
hand: str  # "RIGHT" or "LEFT" - no type safety!
```

**Why this is a critical error**:
- Lost IDE autocomplete and type checking
- Lost compile-time typo detection (Hand.RGIHT would error, "rgiht" won't)
- Lost self-documenting code
- Regression in code quality for no benefit

**Rule**: Regressions in type safety are BUGS. Challenge any suggestion to weaken typing.

**Correct pattern for enums**:
```python
# In unified package - use proper enums
from enum import Enum

class Hand(Enum):
    RIGHT = "right"
    LEFT = "left"

# Dataclasses use enum types
@dataclass
class WormParams:
    hand: Hand  # Type-safe

# JSON export serializes to string
def to_json(design):
    return {"hand": design.hand.value}  # "right"

# Functions accept both enum and string for flexibility
def design_from_module(hand: Union[Hand, str] = "right"):
    if isinstance(hand, str):
        hand = Hand(hand.lower())
```

### 2. NEVER Push Untested Code

**What happened**: Pushed 15+ commits during refactor, each requiring user to test in browser and report errors:
- Missing io module
- Wrong imports (importing from .core instead of ..io)
- Field name mismatches (missing _mm/_deg suffixes)
- Enum import errors
- CLI broken (AttributeError on field access)
- ManufacturingParams structure wrong

**Why this is unacceptable**:
- User had to "hit enter every minute for 30 minutes"
- EVERY error could have been caught with local testing
- Never tested CLI until user asked
- Never tested web in browser before pushing
- Wasted user's time repeatedly

**Rule**: Test EVERYTHING locally before pushing. No exceptions.

### 3. NEVER Claim Success Without User Testing

**What happened**: Repeatedly declared "this should work now" or "the fix is pushed" without user verification

**Why this fails**:
- Automated tests missed TENS of real issues
- Web calculator still broken after all "fixes"
- User had to correct assumptions multiple times
- Over-confidence without verification

**Rule**: ONLY the user can verify success. Never claim "it works" until user confirms.

### 4. Pre-Push Checklist (MANDATORY)

Before EVERY push, ALL items must pass:

```
[ ] Changes compile/import without errors
[ ] If Pydantic models changed: Schemas regenerated
    python scripts/generate_schemas.py
    bash scripts/generate_types.sh
    git add schemas/ web/types/
[ ] CLI tested locally and works:
    python -c "from wormgear.calculator import design_from_module, to_json
    print(to_json(design_from_module(2.0, 30)))"
[ ] Web tested in browser (if web changes):
    - Run web/build.sh
    - Open index.html in browser
    - Test calculator functionality
    - Check browser console for errors
[ ] TypeScript compiles (if .ts files changed):
    cd web && tsc --noEmit
[ ] pytest passes locally: pytest tests/ -v
[ ] No type safety regressions (enums still enums, types still typed)
[ ] Changes are batched (not micro-commits requiring repeated user testing)
```

**DO NOT PUSH** until all checkboxes are checked.

### 5. Pull Request Workflow (MANDATORY)

**Branch protection is enabled on `main`.** Direct pushes will be rejected.

**Workflow:**
1. Create a feature branch: `git checkout -b feat/my-feature`
2. Make changes and commit
3. Push branch: `git push -u origin feat/my-feature`
4. Create PR: `gh pr create --title "feat: Description" --body "..."`
5. **STOP** - Leave PR for user to review and merge

**NEVER use auto-merge:**
```bash
# ❌ WRONG - bypasses review
gh pr merge --auto
gh pr merge --squash --auto

# ✅ CORRECT - create PR and stop
gh pr create ...
# Then tell user the PR URL and wait
```

**Why:** The user wants to review changes before they are merged. Auto-merge bypasses this review process.

### 6. Pyodide + Pydantic Compatibility

**Key facts:**
- Pyodide 0.29.0 includes Pydantic 2.12.5 (bundled, pre-compiled for WASM)
- Pydantic v2 requires `pydantic-core` (Rust extension) - CANNOT install via micropip
- MUST use `pyodide.loadPackage('pydantic')` NOT `micropip.install('pydantic')`

**Correct loading order in Pyodide:**
```javascript
// In pyodide-init.js or generator-worker.js
await pyodide.loadPackage(['micropip', 'pydantic']);  // Load pydantic FIRST
// Then load wormgear modules that import from pydantic
```

### 7. Pyodide + Enum Compatibility

**Myth**: "Pyodide can't handle enums, must use strings"

**Reality**: Pyodide handles enums perfectly fine:

```javascript
// web/modules/pyodide-init.js
await calculatorPyodide.runPythonAsync(`
from wormgear.calculator.enums import Hand, WormProfile, WormType
# Enums work normally in Pyodide
design = design_from_module(2.0, 30, hand=Hand.RIGHT)
`);
```

JavaScript can pass strings, Python functions accept `Union[Enum, str]`:

```python
def design_from_module(hand: Union[Hand, str] = "right"):
    if isinstance(hand, str):
        hand = Hand(hand.lower())  # Convert string to enum
    # Now hand is guaranteed to be Hand enum
```

This gives best of both worlds: type safety in Python, flexibility for JavaScript.

### 8. Manual JSON Parsing is a Bug Factory

**What happened (Jan 2026)**: Chose dataclasses + manual parsing over Pydantic. Result: 6+ bugs from type mismatches over two days.

**The bugs**:
```python
# Bug 1-3: Called .upper() on enum (expected string)
is_right_hand = self.assembly_params.hand.upper() == "RIGHT"  # AttributeError

# Bug 4-5: Compared enum to string (always False)
if self.profile == "ZI":  # Never matches WormProfile.ZI

# Bug 6-7: Fields not parsed from JSON (forgot to add .get() calls)
worm_length_mm=mfg_data.get('worm_length_mm')  # Was missing entirely
```

**Root cause**: Every field and every enum requires manual handling:
- Manual `.get()` for each JSON field
- Manual `Enum(string)` conversion
- Manual comparisons that can mismatch types
- No validation at parse time - errors surface at runtime

**The tradeoff that was made**:
- Avoided Pydantic dependency
- Avoided Pyodide/Rust extension uncertainty
- Got: 6+ bugs, hours of debugging, user frustration

**Rule**: If you choose manual parsing, you MUST:
1. Test the full JSON→object→usage path, not just imports
2. After ANY type mismatch bug, add a test that would have caught it
3. If the same class of bug happens twice, STOP and reconsider the architecture

**Alternative**: Pydantic with `model_validate(json_data)` handles all of this automatically. The dependency cost may be worth it.

## Recent History: Calculator Restoration (Jan 2026)

**What happened**: The unified calculator refactor (Jan 2026) introduced multiple regressions:
- Type safety lost (enums → strings)
- Validation reduced by 43% (637 lines → 364 lines)
- Dict-based returns instead of typed dataclasses
- Manual JSON Schema maintenance caused drift
- 15+ iterative fixes required due to inadequate testing

**Decision**: Rather than continue piecemeal fixes, we **restored the proven legacy code** (commit 720de75: `web/wormcalc/`, 2,479 lines) and rebuilt it with a **schema-first architecture**:

1. **Pydantic models** as single source of truth (`src/wormgear/calculator/models.py`)
2. **Generated JSON Schemas** from Pydantic (no manual maintenance)
3. **Generated TypeScript types** from schemas (compile-time safety in web UI)
4. **Versioned schemas** for all Python↔JavaScript interactions
5. **Calculator inputs** are now saveable/loadable (not just outputs)

**Result**: Type safety restored, comprehensive validation preserved, zero schema drift between Python and TypeScript.

**Lesson**: When a refactor introduces multiple regressions, sometimes the best path forward is to restore proven code with better architecture rather than continue fixing a flawed approach.

---

## Development Best Practices

### 1. Always Align with Architecture

**Before making changes:**
- Read [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) to understand the 4-layer structure
- Identify which layer(s) your change affects
- Ensure changes respect layer boundaries and dependencies
- Core layer (geometry) must NEVER depend on calculator or IO layers
- Calculator must NEVER import from core (geometry generation)
- IO layer coordinates between calculator and core

**Layer dependencies (allowed):**
```
CLI → IO → Core
CLI → Calculator → (no geometry dependencies)
Web → Calculator → (no geometry dependencies)
```

**Examples:**
- ✅ **Good**: Add new feature to `core/features.py`, expose in `core/__init__.py`, use in `cli/generate.py`
- ❌ **Bad**: Import `WormGeometry` in `calculator/core.py` to validate dimensions
- ✅ **Good**: Add validation rule in `calculator/validation.py` using only dimensional data
- ❌ **Bad**: Add calculation logic to `core/worm.py` instead of `calculator/core.py`

### 2. Ensure Test Coverage

**Requirements:**
- All new functions must have corresponding tests
- Aim for >85% code coverage
- Test both success and failure cases
- Include edge cases and boundary conditions

**Test structure:**
```
tests/
├── test_calculator.py       # Engineering calculations
├── test_validation.py       # Validation rules
├── test_geometry_worm.py    # Worm geometry generation
├── test_geometry_wheel.py   # Wheel geometry generation
├── test_features.py         # Bores, keyways, etc.
├── test_io.py              # JSON load/save
└── test_integration.py     # End-to-end workflows
```

**Running tests:**
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=wormgear --cov-report=html

# Run specific test file
pytest tests/test_calculator.py

# Run specific test
pytest tests/test_calculator.py::test_design_from_module
```

**Before committing:**
```bash
# Ensure tests pass
pytest

# Check code formatting
black src/ tests/

# Lint code
ruff check src/ tests/
```

### 3. Perform Code Reviews

**Self-review checklist before committing:**
- [ ] Does this change align with the architecture?
- [ ] Are all new functions tested?
- [ ] Is the code readable and well-documented?
- [ ] Are variable names clear and consistent with conventions? (_mm, _deg suffixes)
- [ ] Have I checked for edge cases and error conditions?
- [ ] Does this break backward compatibility? (If yes, document in commit)
- [ ] Have I updated relevant documentation (README, ARCHITECTURE)?
- [ ] Does the commit message clearly explain WHY, not just WHAT?

**Commit message format:**
```
<type>: <subject>

<body explaining why this change is needed>

<optional footer with breaking changes or issue references>
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `perf`, `chore`

**Examples:**
```
feat: Add globoid worm geometry support

Implements hourglass-shaped worm for better contact area with wheel.
Uses throat radius calculation from DIN 3975 standard.

Closes #42

---

fix: Correct profile shift calculation for low tooth counts

Previous implementation didn't account for dedendum modification
when profile shift was applied, causing undercut in small wheels.
Now follows DIN 3975 equations 8.3.2 and 8.3.3.

Fixes #58
```

### 4. Challenge Decisions - Don't Just Agree

**When reviewing or discussing:**
- Question assumptions, especially about standards compliance
- Ask "why this approach?" even if it seems obvious
- Suggest alternatives when you see potential issues
- Point out edge cases and failure modes
- Don't assume the user is always right - provide technical reasoning

**Examples of good challenges:**

❌ **Bad (passive agreement):**
> "Sure, I'll add that feature to the calculator module."

✅ **Good (thoughtful challenge):**
> "I see you want to add geometry generation to the calculator module. However, this would violate our architecture - the calculator layer should only handle mathematical calculations. Instead, should we create a new utility in the CLI layer that calls both calculator and geometry? This keeps layers separated while achieving the same user-facing result."

❌ **Bad (passive agreement):**
> "OK, I'll set the default hobbing steps to 100 for maximum accuracy."

✅ **Good (technical challenge):**
> "100 hobbing steps would take ~5 minutes to generate and create massive STEP files (2-3 MB). Based on testing, 18 steps (20 seconds) gives 99% of the accuracy with 10x better performance. Should we make 18 the default and offer 100 as an optional `--hobbing-preset ultra` for users who specifically need that precision?"

### 5. Plan Before Coding

**For any non-trivial change:**

1. **Understand the requirement**
   - What problem are we solving?
   - Who is affected? (Python API users? CLI users? Web calculator users?)
   - What are the constraints? (Performance, backward compatibility, standards)

2. **Design the solution**
   - Which files/modules need changes?
   - What's the API surface? (function signatures, parameters)
   - How will this be tested?
   - What edge cases exist?

3. **Consider alternatives**
   - Are there simpler approaches?
   - What are the tradeoffs? (speed vs accuracy, simplicity vs flexibility)
   - Does this generalize well or is it too specific?

4. **Document the plan**
   - Create a brief design document for complex features
   - Get feedback before implementing
   - Update ARCHITECTURE.md if adding new concepts

5. **Implement incrementally**
   - Write tests first (TDD) when possible
   - Implement in small, reviewable commits
   - Run tests frequently during development

**Example planning process:**

*User request:* "Add set screw holes to gears"

**Planning questions:**
- Where should set screw functionality live? (core/features.py - yes, it's a physical feature)
- What parameters are needed? (position, diameter, depth, thread type)
- How many set screws? (1-4, configurable?)
- Standards compliance? (ISO 4026 for set screw dimensions)
- API design: `SetScrewFeature(diameter=3.0, depth=8.0, angle_deg=90.0)` or auto-sized?
- CLI integration: `--worm-set-screw 3x8` or `--worm-set-screw-auto`?
- Testing: How to verify the hole is correctly positioned and sized?
- Edge cases: What if bore diameter is too small for set screw clearance?

**After planning, outline implementation steps:**
1. Add `SetScrewFeature` class to `core/features.py` with ISO 4026 lookup
2. Add set screw support to `WormGeometry` and `WheelGeometry`
3. Write tests in `tests/test_features.py`
4. Add CLI flags to `cli/generate.py`
5. Update documentation and examples
6. Test end-to-end workflow

### 6. Critical Architecture Rules for Web/WASM Projects

**NEVER track build artifacts in git**

Build artifacts (copied files for deployment) must ALWAYS be gitignored:

✅ **Correct**:
```
src/wormgear/           # ← Source of truth (tracked)
web/wormgear/           # ← Build artifact (gitignored, created by build.sh)
```

❌ **Wrong**:
```
src/wormgear/           # ← Source
web/src/                # ← Duplicate tracked in git (WRONG!)
web/src/wormgear/       # ← Build artifact tracked (WRONG!)
```

**.gitignore must include**:
```
# Build artifacts
web/wormgear/           # Created by build.sh
web/src/                # If it exists, it's wrong and should be removed
```

**NEVER maintain duplicate implementations**

For Pyodide/WASM projects:
- ✅ **One calculator implementation**: `src/wormgear/calculator/`
- ✅ **Used by both**: Python package AND web via Pyodide
- ❌ **Never create**: `web/wormcalc/` as separate dict-based implementation

**Why this matters**:
- Violates DRY (Don't Repeat Yourself) principle
- Violates SSOT (Single Source of Truth) principle
- Bug fixes must be duplicated
- Features must be implemented twice
- Implementations WILL diverge over time
- Maintenance burden compounds

**Pyodide loading pattern**:
```javascript
// web/modules/pyodide-init.js
// Load from build artifact (created by build.sh)
const files = ['__init__.py', 'core.py', 'validation.py', 'output.py'];
calculatorPyodide.FS.mkdir('/home/pyodide/wormgear/calculator');

for (const file of files) {
    const response = await fetch(`wormgear/calculator/${file}`);  // ← From build artifact
    const content = await response.text();
    calculatorPyodide.FS.writeFile(`/home/pyodide/wormgear/calculator/${file}`, content);
}

// Import unified package
from wormgear.calculator.core import design_from_module
```

**Build script pattern**:
```bash
#!/bin/bash
# web/build.sh

# Copy source to build artifact location (gitignored)
cp -r ../src/wormgear web/

# Remove cache files
find web/wormgear -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
```

**Historical mistake (2025-01)**:
- Created `web/src/` as tracked directory duplicating `src/wormgear/`
- Maintained separate `web/wormcalc/` implementation (840 lines) vs `src/wormgear/calculator/` (556 lines)
- Build script created `web/src/wormgear/` but nothing used it
- Globoid worm bugs required THREE separate fixes
- Architecture cleanup required removing duplicates and unifying to single implementation

**Self-check before committing**:
- [ ] Am I tracking any build artifacts? (If yes, STOP and gitignore them)
- [ ] Am I creating a duplicate implementation? (If yes, STOP and use unified package)
- [ ] Do multiple directories contain "the same" code? (If yes, STOP and consolidate)
- [ ] Does documentation claim code reuse but reality is duplicates? (If yes, STOP and fix)

## Current State (2026-01-25)

**Status:** v1.0.0-alpha - Unified package complete

### Phase 1: Basic Geometry ✓ Complete
- Engineering calculations (DIN 3975/DIN 3996)
- Validation system with errors/warnings
- JSON Schema v1.0 (calculator ↔ geometry)
- Worm and wheel geometry generation
- Globoid worm support
- Virtual hobbing wheel generation
- STEP export
- Python API and CLI
- Web calculator UI

### Phase 2: Features ✓ Complete
- Bore auto-calculation and custom sizes
- Keyways (ISO 6885 / DIN 6885)
- Small gear support
- Thin rim warnings

### Phase 3: Advanced (Future)
- Set screw holes
- Hub options (flush/extended/flanged)
- Envelope calculation for wheel
- Assembly positioning
- Manufacturing specs output
- WASM build (calculator + geometry in browser)

## Key Design Decisions

### 1. Unified Package Structure

**Decision:** Merge calculator and geometry into one package
**Rationale:**
- Simpler installation (one `pip install`)
- Consistent API between calculation and generation
- Shared JSON schema eliminates version mismatches
- Easier maintenance and testing

**Alternative considered:** Keep as separate packages
**Why rejected:** User confusion, version coordination overhead, redundant IO code

### 2. build123d for CAD

**Decision:** Use build123d (not FreeCAD, not CadQuery)
**Rationale:**
- Modern, Pythonic API
- Clean OpenCascade bindings
- Active development
- Good documentation

**Tradeoff:** Smaller community than FreeCAD, but better developer experience

### 3. Exact Geometry (No Manufacturing Assumptions)

**Decision:** Generate exact intended geometry, don't rely on manufacturing to "fix" the model
**Rationale:**
- CNC machines cut exactly what we model
- 3D printers print exactly what we model
- No hobbing approximations (except when explicitly requested via virtual hobbing)

**Example:** We model the exact thread profile, not an approximation that "will be good enough after cutting"

### 4. Two Wheel Types

**Decision:** Offer both helical (simple) and virtual hobbing (accurate throated) wheels
**Rationale:**
- Helical: Fast, simple, works for many applications
- Virtual hobbing: Slower, but accurate tooth throating for high-load applications

**Tradeoff:** More code complexity, but gives users choice based on their needs

### 5. Two Tooth Profiles (ZA and ZK)

**Decision:** Support both DIN 3975 profiles
**Rationale:**
- ZA (straight flanks): Standard for CNC machining, easier to cut
- ZK (convex flanks): Better for 3D printing (stress distribution, layer adhesion)

**Implementation:** Minimal code difference, just affects the tooth profile shape calculation

### 6. JSON Schema v1.0

**Decision:** Create versioned JSON schema for calculator ↔ geometry communication
**Rationale:**
- Decouples web calculator from Python package
- Enables future schema evolution (v1.1, v2.0)
- Clear contract between tools
- Supports both Python API and web workflows

**Schema fields:** All dimensional data with _mm/_deg suffixes for clarity

### 7. Feature Classes (Bore, Keyway, etc.)

**Decision:** Use dedicated feature classes instead of adding parameters to geometry constructors
**Rationale:**
- Cleaner API: `bore=BoreFeature(diameter=8.0)` vs `bore_diameter=8.0, has_bore=True`
- Extensible: Easy to add HubFeature, SetScrewFeature, etc.
- Optional: Features are clearly opt-in via parameter

**Example:**
```python
# Clean feature composition
worm = WormGeometry(
    params=worm_params,
    assembly_params=assembly_params,
    length=40,
    bore=BoreFeature(diameter=8.0),
    keyway=KeywayFeature(),
    set_screw=SetScrewFeature(angle_deg=90.0)  # Future
)
```

## Target Manufacturing Methods

### CNC Machining (ZA Profile - Default)

The geometry must be **exact and watertight** - no approximations:

- **Worm**: 4-axis lathe with live tooling, or 5-axis mill
- **Wheel**: 5-axis mill (true form), or indexed 4-axis with ball-nose finishing
- **Materials**: Steel, brass, bronze, aluminum
- **Profile**: ZA (straight flanks)

### 3D Printing (ZK Profile Recommended)

**Methods:**
- FDM (PLA, PETG, Nylon)
- SLA/DLP resin printing
- SLS (nylon powder)

**Materials:**
- PLA: Prototyping only
- PETG/Nylon: Functional parts
- Resin: High precision

**Profile**: ZK (slightly convex flanks) recommended
- Reduces stress concentrations
- Better layer adhesion in FDM
- Smoother surfaces for resin printing

**Tips:**
- Use 80-100% infill for strength
- Orient parts to minimize support material
- Add backlash in calculator (0.1-0.2mm recommended)
- Apply dry lubricant (graphite powder or PTFE spray)

## Engineering Context

### Standards
- **DIN 3975** - Worm geometry definitions
- **DIN 3996** - Load capacity calculations
- **ISO 54 / DIN 780** - Standard modules
- **ISO 6885 / DIN 6885** - Keyway dimensions

### Field Naming Conventions

**All dimensional fields use explicit units:**
- `_mm` suffix for millimeter values
- `_deg` suffix for degree values
- No suffix for dimensionless values (ratio, profile_shift)

**Examples:**
```python
pitch_diameter_mm: 16.29
lead_angle_deg: 7.0
ratio: 30
profile_shift: 0.0
num_teeth: 30  # counts have no suffix
```

**Rationale:** Eliminates unit ambiguity, makes code self-documenting

### Keyway Sizes (DIN 6885)

**Common sizes** (full table in `src/wormgear/core/features.py`):

| Bore (mm) | Key Width | Key Height | Shaft Depth | Hub Depth |
|-----------|-----------|------------|-------------|-----------|
| 6-8       | 2         | 2          | 1.2         | 1.0       |
| 8-10      | 3         | 3          | 1.8         | 1.4       |
| 10-12     | 4         | 4          | 2.5         | 1.8       |
| 12-17     | 5         | 5          | 3.0         | 2.3       |
| 17-22     | 6         | 6          | 3.5         | 2.8       |
| ...       | ...       | ...        | ...         | ...       |
| 85-95     | 25        | 14         | 9.0         | 5.4       |

**Note:** For bores below 6mm (small gears), keyways are omitted or require custom dimensions.

### Profile Shift
- The calculator supports profile shift coefficients
- This adjusts addendum/dedendum to prevent undercut on low tooth counts
- Geometry generator must respect the adjusted dimensions from JSON

## JSON Input Format (Schema v1.0)

The web calculator and Python calculator output this format:

```json
{
  "schema_version": "1.0",
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
    "thread_thickness_mm": 3.14,
    "hand": "right",
    "profile_shift": 0.0
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
    "dedendum_mm": 2.5,
    "profile_shift": 0.0
  },
  "assembly": {
    "centre_distance_mm": 38.14,
    "pressure_angle_deg": 20.0,
    "backlash_mm": 0.05,
    "hand": "right",
    "ratio": 30,
    "efficiency_percent": 75.0,
    "self_locking": false
  },
  "manufacturing": {
    "profile": "ZA",
    "virtual_hobbing": false,
    "hobbing_steps": 18,
    "throated_wheel": false,
    "sections_per_turn": 36
  }
}
```

## Current API

### Python Calculator API
```python
from wormgear.calculator import calculate_design_from_module, validate_design
from wormgear.io import save_design_json

# Calculate parameters
design = calculate_design_from_module(module=2.0, ratio=30)
validation = validate_design(design)

if validation.valid:
    save_design_json(design, "design.json")
```

### Python Geometry API
```python
from wormgear.core import WormGeometry, WheelGeometry, GloboidWormGeometry
from wormgear.core import BoreFeature, KeywayFeature
from wormgear.io import load_design_json

# Load parameters from calculator JSON
design = load_design_json("design.json")

# Build worm with bore and keyway
worm_geo = WormGeometry(
    params=design.worm,
    assembly_params=design.assembly,
    length=40,  # User specifies worm length
    sections_per_turn=36,  # Smoothness (default: 36)
    bore=BoreFeature(diameter=8.0),  # Optional: adds bore
    keyway=KeywayFeature()  # Optional: adds DIN 6885 keyway
)
worm = worm_geo.build()
worm_geo.export_step("worm_m2_z1.step")

# Build wheel (helical - default) with features
wheel_geo = WheelGeometry(
    params=design.wheel,
    worm_params=design.worm,
    assembly_params=design.assembly,
    face_width=None,  # Auto-calculated if None
    bore=BoreFeature(diameter=12.0),
    keyway=KeywayFeature()
)
wheel = wheel_geo.build()
wheel_geo.export_step("wheel_m2_z30.step")

# Build globoid worm (hourglass shape)
globoid_worm_geo = GloboidWormGeometry(
    params=design.worm,
    assembly_params=design.assembly,
    wheel_pitch_diameter=design.wheel.pitch_diameter_mm,
    length=40
)
globoid_worm_geo.export_step("globoid_worm.step")
```

### CLI Usage

```bash
# Generate both worm and wheel (with auto-calculated bores and keyways by default)
wormgear-geometry design.json

# Generate solid parts without bores
wormgear-geometry design.json --no-bore

# Custom bore sizes (keyways auto-sized to match)
wormgear-geometry design.json --worm-bore 8 --wheel-bore 15

# For 3D printing: use ZK profile (slightly convex flanks)
wormgear-geometry design.json --profile ZK

# For CNC machining: use ZA profile (straight flanks, default)
wormgear-geometry design.json --profile ZA

# Globoid worm (hourglass shape for better contact)
wormgear-geometry design.json --globoid

# Virtual hobbing wheel (accurate throated teeth)
wormgear-geometry design.json --virtual-hobbing

# View in OCP viewer
wormgear-geometry design.json --view --no-save --mesh-aligned
```

## Geometry Construction Approaches

### Worm (Straightforward)

Helical sweep of trapezoidal tooth profile:

1. Create tooth profile in axial plane (trapezoid based on pressure angle)
2. Create helix path at pitch radius
3. Position profile perpendicular to helix
4. Sweep along helix
5. Add core cylinder
6. Union and trim to length
7. Add features (bore, keyway)

### Wheel (Two Options)

**Helical (Default - Fast)**
- Generate helical involute gear
- Fast, simple, produces functional geometry
- Works well for many applications

**Virtual Hobbing (Accurate - Slower)**
- Kinematically simulate hobbing process
- Accurate tooth throating matching worm curvature
- Better contact area for high-load applications
- Adjustable steps (6-36) for speed/quality tradeoff

**Future: Envelope Calculation**
- Mathematical calculation of contact surface
- Complex mathematics but fast and clean
- Most accurate theoretical approach

## JS<->Python Bridge Architecture

The web calculator uses a clean bridge pattern between JavaScript and Python (via Pyodide).

### Bridge Components

| File | Purpose |
|------|---------|
| `web/modules/parameter-handler.js` | Collects UI inputs into validated structure |
| `web/modules/schema-validator.js` | Runtime validation in JavaScript |
| `src/wormgear/calculator/js_bridge.py` | Single entry point for all JS→Python calls |

### Data Flow

```
JavaScript                          │ Python (Pyodide)
───────────────────────────────────│────────────────────────────
parameter-handler.js                │
  └─ getInputs(mode)               │
       └─ validateCalculatorInputs()│
            │                       │
            ▼ JSON.stringify()      │
            ├──────────────────────►│ js_bridge.calculate(json)
            │                       │   └─ CalculatorInputs.model_validate()
            │                       │   └─ _call_design_function()
            │                       │   └─ validate_design()
            │                       │   └─ CalculatorOutput.model_dump_json()
            │◄──────────────────────┤
            ▼ parseCalculatorResponse()
schema-validator.js                 │
  └─ validateCalculatorOutput()    │
  └─ validateWormGearDesign()      │
```

### Key Rules

1. **Single Entry Point**: All JS→Python calls go through `js_bridge.calculate(input_json: str) -> str`
2. **Validation at Both Boundaries**: JS validates before sending, Python (Pydantic) validates on receipt
3. **JSON Transport**: Simple strings, no Pyodide object proxies
4. **No Inline Python**: JavaScript never contains Python code strings (except the import call)

### Usage

```javascript
// JavaScript
import { getInputs } from './modules/parameter-handler.js';
import { parseCalculatorResponse } from './modules/schema-validator.js';

const inputs = getInputs(mode);
const inputJson = JSON.stringify(inputs);
calculatorPyodide.globals.set('input_json', inputJson);

const resultJson = calculatorPyodide.runPython(`calculate(input_json)`);
const { output, design } = parseCalculatorResponse(resultJson);
```

## File Structure

```
wormgear/
├── src/wormgear/
│   ├── __init__.py                    # Public API exports
│   ├── enums.py                       # Hand, WormProfile, WormType enums
│   ├── calculator/                    # Layer 2a: Engineering calculations
│   │   ├── __init__.py
│   │   ├── core.py                   # design_from_module, etc.
│   │   ├── validation.py             # validate_design, rules
│   │   ├── output.py                 # to_json, to_markdown, to_summary
│   │   └── js_bridge.py              # JS<->Python bridge (single entry point)
│   ├── core/                          # Layer 1: Geometry generation
│   │   ├── __init__.py
│   │   ├── worm.py                   # WormGeometry
│   │   ├── wheel.py                  # WheelGeometry
│   │   ├── globoid_worm.py           # GloboidWormGeometry
│   │   ├── virtual_hobbing.py        # VirtualHobbingWheelGeometry
│   │   └── features.py               # BoreFeature, KeywayFeature, etc.
│   ├── io/                            # Layer 2b: JSON schema and I/O
│   │   ├── __init__.py
│   │   ├── loaders.py                # Pydantic models + load/save JSON
│   │   └── schema.py                 # JSON Schema v1.0
│   └── cli/                           # Layer 3: Command-line interface
│       ├── __init__.py
│       └── generate.py               # wormgear-geometry command
├── web/                               # Web calculator (browser)
│   ├── index.html                    # Web UI
│   ├── app.js                        # Main application
│   ├── modules/
│   │   ├── pyodide-init.js          # Pyodide initialization
│   │   ├── parameter-handler.js     # UI input collection
│   │   └── schema-validator.js      # Runtime JS validation
│   ├── generator-worker.js          # Web Worker for geometry
│   ├── wormgear/                     # Python source (built from src/, gitignored)
│   └── types/                        # Generated TypeScript types
│       └── *.generated.d.ts
├── schemas/                           # Generated JSON schemas
│   └── *.json
├── scripts/
│   ├── generate_schemas.py          # Pydantic → JSON Schema
│   ├── generate_types.sh            # JSON Schema → TypeScript
│   └── typecheck.sh                 # Run mypy + tsc
├── tests/
├── examples/
├── docs/
│   ├── ARCHITECTURE.md
│   ├── GEOMETRY.md
│   └── ENGINEERING_CONTEXT.md
├── pyproject.toml
├── README.md
└── CLAUDE.md                          # This file
```

## Testing Strategy

1. **Geometry validation**
   - Export STEP, reimport, check volume matches
   - OCC validation for bad faces/edges
   - Watertight solid verification

2. **Mesh compatibility**
   - Generate pair, check centre distance
   - Verify no interference at assembly

3. **Manufacturing validation**
   - Import to CAM software (FreeCAD, Fusion 360)
   - Verify toolpath generation succeeds
   - Check for unmachineable features

## Quick Reference

### Running Tests
```bash
pytest                              # All tests
pytest --cov=wormgear              # With coverage
pytest tests/test_calculator.py    # Specific file
pytest -k "test_bore"              # Tests matching pattern
```

### Code Quality
```bash
black src/ tests/                  # Format code
ruff check src/ tests/             # Lint code
```

### Building and Installing
```bash
pip install -e .                   # Editable install
pip install -e ".[dev]"           # With dev dependencies
```

### Releasing

**ALWAYS use the publish script to cut releases. NEVER create tags or releases manually.**

```bash
./scripts/publish.sh              # Auto-increment patch version (0.0.15 -> 0.0.16)
./scripts/publish.sh 0.1.0        # Specify version explicitly
```

The script handles the full release workflow:
1. Creates a version bump PR
2. Auto-merges the PR
3. Creates and pushes the git tag
4. Creates GitHub Release with auto-generated notes
5. Triggers PyPI publish via GitHub Actions

## Key Challenges to Watch

1. **Helix orientation** - Ensuring profile perpendicular to helix path
2. **Thread hand** - Right vs left hand needs careful coordinate transform
3. **Wheel throat** - Getting the throating cylinder positioned exactly right
4. **Surface continuity** - Avoiding gaps at thread start/end
5. **Tolerance modeling** - Representing clearances and fits in STEP
6. **Layer separation** - Resist temptation to mix calculation and geometry logic

## Reference Resources

- **build123d docs**: https://build123d.readthedocs.io/
- **DIN 3975**: Worm gear geometry standard
- **ISO 6885**: Parallel keys and keyways
- **Architecture doc**: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- **Engineering context**: [docs/ENGINEERING_CONTEXT.md](docs/ENGINEERING_CONTEXT.md)

---

**Remember**: The goal is **CNC-manufacturable and 3D-printable parts**. Every dimension must be exact and intentional. Challenge assumptions, test thoroughly, and always align with the architecture.
