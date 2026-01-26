# Calculator Restoration Plan: Schema-First Architecture

## Executive Summary

Restore the proven legacy calculator code (from commit 720de75) with a modern schema-first architecture that ensures type safety across the Python/JavaScript boundary.

## Core Principles

1. **Python dataclass → JSON Schema** using library (pydantic or dataclasses-json)
2. **JSON Schema → TypeScript types** for compile-time safety in web UI
3. **Versioned schemas** for all JS↔Python interactions
4. **Load/save calculator inputs** (not just outputs)
5. **Type safety everywhere** - Python enums, TS enums, validated at boundaries

## Problem Statement

### Current Issues
1. **Type safety lost**: Refactor removed proper enums in favor of strings
2. **Validation reduced**: 637 lines → 364 lines (43% reduction in validation logic)
3. **Manual schema maintenance**: JSON Schema defined separately from dataclasses
4. **No TS types**: JavaScript has no type checking for Python data structures
5. **Output-only**: Can save design outputs but not calculator inputs
6. **Enum serialization broken**: `save_design_json()` crashes with TypeError

### Legacy Code Superiority (commit 720de75)
- **6 files, 2,479 lines** of proven code
- Type-safe enums (Hand, WormProfile, WormType)
- Comprehensive validation with severity levels
- Professional output formatting
- Explicit JS↔Python boundary handling (js_bridge.py)

## Architecture: Schema-First Approach

### Layer 1: Python Dataclasses (Source of Truth)

**Location:** `src/wormgear/calculator/models.py` (new consolidated file)

**Technology choice:**
- **Option A (Recommended): Pydantic v2** - Industry standard, excellent JSON Schema generation, validation built-in
- **Option B: dataclasses + dataclasses-json** - Lighter weight, stdlib-based

**What to define:**
```python
from pydantic import BaseModel, Field
from enum import Enum

# Enums (shared between input and output)
class Hand(str, Enum):
    RIGHT = "right"
    LEFT = "left"

class WormProfile(str, Enum):
    ZA = "ZA"
    ZK = "ZK"
    ZI = "ZI"

class WormType(str, Enum):
    CYLINDRICAL = "cylindrical"
    GLOBOID = "globoid"

# Calculator INPUTS (new - currently not saveable)
class CalculatorInputs(BaseModel):
    """User inputs to calculator - must be saveable/loadable"""

    # Design mode
    design_mode: str = Field(..., pattern="^(module|centre_distance|wheel|envelope)$")

    # Common inputs (depends on mode)
    module_mm: Optional[float] = Field(None, gt=0)
    ratio: int = Field(..., gt=0)
    num_starts: int = Field(1, ge=1, le=4)
    centre_distance_mm: Optional[float] = Field(None, gt=0)
    wheel_od_mm: Optional[float] = Field(None, gt=0)
    worm_od_mm: Optional[float] = Field(None, gt=0)

    # Configuration
    pressure_angle_deg: float = Field(20.0, ge=14.5, le=30)
    backlash_mm: float = Field(0.05, ge=0)
    hand: Hand = Hand.RIGHT
    lead_angle_deg: Optional[float] = Field(None, gt=0, lt=45)

    # Manufacturing
    profile: WormProfile = WormProfile.ZA
    worm_type: WormType = WormType.CYLINDRICAL
    throat_reduction_mm: Optional[float] = Field(None, ge=0)

    # Virtual hobbing
    virtual_hobbing: bool = False
    hobbing_steps: int = Field(18, ge=6, le=72)

    # Bore features
    worm_bore_mm: Optional[float] = None
    worm_bore_type: str = "none"  # "none", "auto", "custom"
    worm_anti_rotation: str = "none"  # "none", "keyway", "ddcut"
    wheel_bore_mm: Optional[float] = None
    wheel_bore_type: str = "none"
    wheel_anti_rotation: str = "none"

# Calculator OUTPUTS (existing WormGearDesign structure)
class WormParams(BaseModel):
    module_mm: float
    num_starts: int
    pitch_diameter_mm: float
    tip_diameter_mm: float
    root_diameter_mm: float
    lead_mm: float
    lead_angle_deg: float
    addendum_mm: float
    dedendum_mm: float
    thread_thickness_mm: float
    hand: Hand
    profile_shift: float = 0.0
    type: Optional[WormType] = None
    throat_reduction_mm: Optional[float] = None
    # ... etc

class WheelParams(BaseModel):
    # ... similar structure

class AssemblyParams(BaseModel):
    # ... similar structure

class ManufacturingParams(BaseModel):
    profile: WormProfile = WormProfile.ZA
    virtual_hobbing: bool = False
    hobbing_steps: int = 18
    throated_wheel: bool = False
    sections_per_turn: int = 36
    worm_length_mm: Optional[float] = None
    wheel_width_mm: Optional[float] = None

class WormGearDesign(BaseModel):
    """Complete design output from calculator"""
    schema_version: str = "2.0"  # Bump version for new schema system
    inputs: CalculatorInputs  # NEW: Include original inputs
    worm: WormParams
    wheel: WheelParams
    assembly: AssemblyParams
    manufacturing: ManufacturingParams
    features: Optional[ManufacturingFeatures] = None
    validation: Optional[ValidationResult] = None  # NEW: Include validation results
```

### Layer 2: JSON Schema Generation

**Location:** `scripts/generate_schemas.py` (new)

**Purpose:** Generate JSON Schema from Pydantic models

```python
#!/usr/bin/env python3
"""Generate JSON Schemas from Pydantic models."""

from pydantic.json_schema import GenerateJsonSchema
import json

from wormgear.calculator.models import (
    CalculatorInputs,
    WormGearDesign,
)

def generate_schemas():
    """Generate JSON Schemas for all public models."""

    # Generate input schema
    input_schema = CalculatorInputs.model_json_schema(
        mode='serialization',
        schema_generator=GenerateJsonSchema,
    )
    with open('schemas/calculator-inputs-v2.0.json', 'w') as f:
        json.dump(input_schema, f, indent=2)

    # Generate output schema
    output_schema = WormGearDesign.model_json_schema(
        mode='serialization',
        schema_generator=GenerateJsonSchema,
    )
    with open('schemas/design-output-v2.0.json', 'w') as f:
        json.dump(output_schema, f, indent=2)

    print("✓ Generated schemas/calculator-inputs-v2.0.json")
    print("✓ Generated schemas/design-output-v2.0.json")

if __name__ == '__main__':
    generate_schemas()
```

**Run during build:**
```bash
# In pyproject.toml or build script
python scripts/generate_schemas.py
```

### Layer 3: TypeScript Type Generation

**Location:** `scripts/generate_types.py` (new)

**Technology:** Use `json-schema-to-typescript` or `quicktype`

```bash
#!/bin/bash
# scripts/generate_types.sh

# Install json-schema-to-typescript if needed
npm install -g json-schema-to-typescript

# Generate TypeScript types from JSON Schemas
json2ts schemas/calculator-inputs-v2.0.json > web/types/calculator-inputs.d.ts
json2ts schemas/design-output-v2.0.json > web/types/design-output.d.ts

echo "✓ Generated web/types/calculator-inputs.d.ts"
echo "✓ Generated web/types/design-output.d.ts"
```

**Result:** TypeScript definitions like:
```typescript
// web/types/calculator-inputs.d.ts
export enum Hand {
  RIGHT = "right",
  LEFT = "left",
}

export enum WormProfile {
  ZA = "ZA",
  ZK = "ZK",
  ZI = "ZI",
}

export interface CalculatorInputs {
  design_mode: "module" | "centre_distance" | "wheel" | "envelope";
  module_mm?: number;
  ratio: number;
  num_starts?: number;
  pressure_angle_deg?: number;
  backlash_mm?: number;
  hand?: Hand;
  profile?: WormProfile;
  // ... etc
}

export interface WormGearDesign {
  schema_version: string;
  inputs: CalculatorInputs;
  worm: WormParams;
  wheel: WheelParams;
  assembly: AssemblyParams;
  manufacturing: ManufacturingParams;
}
```

### Layer 4: Web Integration

**Update web modules to use TypeScript types:**

```typescript
// web/modules/calculator-state.ts (new)
import { CalculatorInputs, WormGearDesign } from '../types/calculator-inputs';

export class CalculatorState {
  inputs: CalculatorInputs;
  lastDesign: WormGearDesign | null = null;

  constructor() {
    this.inputs = this.loadInputs() || this.defaultInputs();
  }

  defaultInputs(): CalculatorInputs {
    return {
      design_mode: "module",
      module_mm: 2.0,
      ratio: 30,
      num_starts: 1,
      pressure_angle_deg: 20.0,
      backlash_mm: 0.05,
      hand: "right",
      profile: "ZA",
      // ... defaults
    };
  }

  saveInputs(): void {
    localStorage.setItem('calculator-inputs-v2', JSON.stringify(this.inputs));
  }

  loadInputs(): CalculatorInputs | null {
    const stored = localStorage.getItem('calculator-inputs-v2');
    if (!stored) return null;

    try {
      const parsed = JSON.parse(stored);
      // TODO: Validate against schema
      return parsed as CalculatorInputs;
    } catch {
      return null;
    }
  }

  exportInputs(): string {
    return JSON.stringify(this.inputs, null, 2);
  }

  importInputs(json: string): void {
    const parsed = JSON.parse(json);
    // TODO: Validate against schema
    this.inputs = parsed as CalculatorInputs;
    this.saveInputs();
  }
}
```

## Implementation Phases

### Phase 0: Schema Infrastructure (FOUNDATION)

**Goal:** Set up schema generation pipeline

**Tasks:**
1. Add pydantic to `pyproject.toml`
2. Create `src/wormgear/calculator/models.py` with Pydantic models
3. Create `scripts/generate_schemas.py`
4. Create `scripts/generate_types.sh`
5. Create `schemas/` directory
6. Create `web/types/` directory
7. Update `web/build.sh` to run schema/type generation

**Deliverable:**
- Python models generate JSON Schemas
- JSON Schemas generate TypeScript types
- Build pipeline automates this

**Testing:**
```bash
python scripts/generate_schemas.py
bash scripts/generate_types.sh
ls schemas/*.json
ls web/types/*.d.ts
```

---

### Phase 1: Restore Calculator Core with Pydantic

**Goal:** Restore legacy calculator code, ported to Pydantic models

#### Step 1.1: Create Pydantic models
**File:** `src/wormgear/calculator/models.py` (new, ~800 lines)

**Source material:**
- Old dataclasses from commit 720de75
- Current `src/wormgear/io/loaders.py` dataclasses

**Changes from legacy:**
- Use Pydantic BaseModel instead of @dataclass
- Add Field() validators (gt=0, ge=0, pattern, etc.)
- All fields have explicit types and defaults
- Add `CalculatorInputs` model (new concept)

#### Step 1.2: Restore core.py
**File:** `src/wormgear/calculator/core.py`

**Source:** `git show 720de75:web/wormcalc/core.py`

**Adaptations:**
1. Import models from `.models` instead of defining inline
2. Update field names to `_mm`/`_deg` conventions
3. Return Pydantic models (they auto-serialize to JSON)
4. Add `inputs: CalculatorInputs` parameter to all `design_from_*` functions
5. Include inputs in returned WormGearDesign

**Example:**
```python
def design_from_module(
    inputs: CalculatorInputs,  # NEW: Include inputs
    module_mm: float,
    ratio: int,
    **kwargs
) -> WormGearDesign:
    """Calculate design from module and ratio."""
    # ... calculations ...

    return WormGearDesign(
        schema_version="2.0",
        inputs=inputs,  # NEW: Include inputs in output
        worm=worm_params,
        wheel=wheel_params,
        assembly=assembly_params,
        manufacturing=manufacturing_params,
    )
```

#### Step 1.3: Restore validation.py
**File:** `src/wormgear/calculator/validation.py`

**Source:** `git show 720de75:web/wormcalc/validation.py` (637 lines)

**Adaptations:**
1. Use Pydantic models instead of old dataclasses
2. Update field names
3. Return Pydantic ValidationResult model
4. Keep all 12+ validation checks with severity levels

#### Step 1.4: Restore output.py
**File:** `src/wormgear/calculator/output.py`

**Source:** `git show 720de75:web/wormcalc/output.py` (495 lines)

**Simplification:**
- Pydantic models have `.model_dump_json()` built-in
- Pydantic automatically serializes enums to strings
- No need for `_serialize_enums()` helper
- Keep markdown/summary formatters

**Example:**
```python
def to_json(design: WormGearDesign) -> str:
    """Convert design to JSON string."""
    return design.model_dump_json(indent=2, exclude_none=True)

def save_json(design: WormGearDesign, filepath: str) -> None:
    """Save design to JSON file."""
    with open(filepath, 'w') as f:
        f.write(to_json(design))

def load_json(filepath: str) -> WormGearDesign:
    """Load design from JSON file with validation."""
    with open(filepath, 'r') as f:
        data = json.load(f)
    return WormGearDesign.model_validate(data)  # Pydantic validation!
```

---

### Phase 2: Web Calculator with TypeScript Types

**Goal:** Type-safe web calculator with input save/load

#### Step 2.1: Generate schemas and types
```bash
python scripts/generate_schemas.py
bash scripts/generate_types.sh
```

#### Step 2.2: Create TypeScript calculator state manager
**File:** `web/modules/calculator-state.ts` (new, ~200 lines)

**Features:**
- Load/save inputs to localStorage
- Export/import inputs as JSON
- Type-checked with generated TS types
- Validates against schema before saving

#### Step 2.3: Update UI to use typed state
**Files:** `web/modules/parameter-handler.js` → `parameter-handler.ts`

**Changes:**
1. Convert to TypeScript
2. Use `CalculatorInputs` type
3. Remove manual enum handling (use generated enums)
4. Add "Save Inputs" / "Load Inputs" buttons

#### Step 2.4: Update Pyodide integration
**File:** `web/modules/pyodide-init.js`

**Changes:**
1. Pass `CalculatorInputs` JSON to Python
2. Python validates inputs with Pydantic
3. Returns `WormGearDesign` JSON with inputs included
4. Web can reload inputs from saved designs

---

### Phase 3: Remove Old IO Layer

**Goal:** Replace manual loaders with Pydantic

#### Step 3.1: Deprecate old loaders.py
**File:** `src/wormgear/io/loaders.py` (mark deprecated)

**Replacement:** Pydantic models handle everything
```python
# Old way (manual):
design = load_design_json("design.json")

# New way (Pydantic):
with open("design.json") as f:
    design = WormGearDesign.model_validate_json(f.read())
```

#### Step 3.2: Update CLI to use Pydantic models
**File:** `src/wormgear/cli/generate.py`

**Changes:**
- Use `WormGearDesign.model_validate_json()` instead of `load_design_json()`
- Pass through new validation

#### Step 3.3: Update geometry modules
**Files:** `src/wormgear/core/*.py`

**Changes:**
- Accept Pydantic models (WormParams, WheelParams, etc.)
- Pydantic models work exactly like dataclasses for attribute access
- No other changes needed

---

### Phase 4: Testing and Documentation

#### Step 4.1: Update test suite
**Files:** `tests/test_calculator.py`, `tests/test_io.py`

**Changes:**
1. Test Pydantic model validation
2. Test schema generation
3. Test TS type generation
4. Test input save/load roundtrip
5. Test enum serialization (should "just work" with Pydantic)

**Example test:**
```python
def test_input_output_roundtrip():
    """Test that inputs can be saved and loaded."""
    inputs = CalculatorInputs(
        design_mode="module",
        module_mm=2.0,
        ratio=30,
        hand=Hand.RIGHT,
        profile=WormProfile.ZA,
    )

    design = design_from_module(inputs, inputs.module_mm, inputs.ratio)

    # Save to JSON
    json_str = design.model_dump_json()

    # Reload from JSON
    reloaded = WormGearDesign.model_validate_json(json_str)

    # Check inputs preserved
    assert reloaded.inputs.module_mm == 2.0
    assert reloaded.inputs.ratio == 30
    assert reloaded.inputs.hand == Hand.RIGHT

    # Check outputs calculated
    assert reloaded.worm.pitch_diameter_mm > 0
```

#### Step 4.2: Update documentation
**Files:**
- `README.md` - Show new Pydantic API
- `docs/ARCHITECTURE.md` - Document schema-first approach
- `docs/WEB_API.md` (new) - Document JS↔Python schema contracts
- `CLAUDE.md` - Document restoration and schema approach

#### Step 4.3: Add schema validation to web
**Tool:** Use Ajv or similar for client-side JSON Schema validation

```typescript
import Ajv from 'ajv';
import inputSchema from '../schemas/calculator-inputs-v2.0.json';

const ajv = new Ajv();
const validateInputs = ajv.compile(inputSchema);

function loadInputs(json: string): CalculatorInputs {
  const parsed = JSON.parse(json);

  if (!validateInputs(parsed)) {
    throw new Error(`Invalid inputs: ${ajv.errorsText(validateInputs.errors)}`);
  }

  return parsed as CalculatorInputs;
}
```

---

## File Structure After Restoration

```
wormgear/
├── src/wormgear/
│   ├── calculator/
│   │   ├── models.py          # NEW: Pydantic models (inputs + outputs)
│   │   ├── core.py            # RESTORED: 840 lines, adapted for Pydantic
│   │   ├── validation.py      # RESTORED: 637 lines, comprehensive validation
│   │   ├── output.py          # RESTORED: 495 lines, formatters
│   │   └── __init__.py        # Public API
│   ├── io/
│   │   ├── loaders.py         # DEPRECATED: Replaced by Pydantic
│   │   └── schema.py          # DEPRECATED: Replaced by generated schemas
│   └── enums.py               # DEPRECATED: Moved to models.py
├── schemas/                   # NEW: Generated JSON Schemas
│   ├── calculator-inputs-v2.0.json
│   └── design-output-v2.0.json
├── scripts/                   # NEW: Build scripts
│   ├── generate_schemas.py
│   └── generate_types.sh
├── web/
│   ├── types/                 # NEW: Generated TypeScript types
│   │   ├── calculator-inputs.d.ts
│   │   └── design-output.d.ts
│   ├── modules/
│   │   ├── calculator-state.ts  # NEW: Typed state management
│   │   ├── parameter-handler.ts # CONVERTED: Was .js, now .ts
│   │   └── pyodide-init.js      # UPDATED: Use Pydantic validation
│   └── build.sh               # UPDATED: Run schema/type generation
```

---

## Benefits of Schema-First Approach

### 1. Single Source of Truth
- Python Pydantic models define everything
- JSON Schemas auto-generated (not hand-maintained)
- TypeScript types auto-generated (not hand-maintained)
- Zero schema drift between Python and JS

### 2. Type Safety Everywhere
```python
# Python (compile-time + runtime)
design = WormGearDesign(...)  # Type-checked by IDE
design.worm.hand  # Type: Hand enum

# TypeScript (compile-time)
const design: WormGearDesign = ...;
design.worm.hand  // Type: Hand enum

// JavaScript (runtime)
const validated = WormGearDesign.model_validate(json);  // Pydantic validates!
```

### 3. Validation Built-In
```python
# Pydantic validates on construction
inputs = CalculatorInputs(
    module_mm=-1.0  # ERROR: Must be > 0 (Field constraint)
)

# Pydantic validates on load
design = WormGearDesign.model_validate_json(bad_json)
# Raises ValidationError with detailed field-level errors
```

### 4. Input Save/Load
```typescript
// User can save their calculator inputs
const inputs = calculatorState.inputs;
download(JSON.stringify(inputs), 'my-design-inputs.json');

// Later: reload inputs
const loaded = JSON.parse(fileContents);
calculatorState.importInputs(loaded);  // Validates against schema!
```

### 5. Versioning
- Schema version in every JSON file
- Can support v1.0 and v2.0 simultaneously
- Migration path: `if schema_version == "1.0": upgrade_to_v2()`

---

## Migration Path from Current Code

### Step 1: Add Pydantic alongside current code
- Don't break existing code
- New models in `models.py`
- Old loaders still work

### Step 2: Port calculator functions to use Pydantic
- One function at a time
- Tests verify equivalence

### Step 3: Port web to use generated types
- Gradual TypeScript conversion
- Old JS still works during transition

### Step 4: Deprecate old IO layer
- Mark as deprecated in code
- Update documentation
- Remove in future release

---

## Success Criteria

### Phase 0 Complete:
- [ ] `python scripts/generate_schemas.py` produces JSON Schemas
- [ ] `bash scripts/generate_types.sh` produces TypeScript types
- [ ] Schemas match Pydantic models exactly

### Phase 1 Complete:
- [ ] Calculator returns Pydantic models
- [ ] All validation restored (637 lines)
- [ ] Enums serialize/deserialize correctly
- [ ] All calculator tests pass

### Phase 2 Complete:
- [ ] Web uses generated TS types
- [ ] Input save/load works in UI
- [ ] localStorage persistence works
- [ ] TypeScript compiler has zero errors

### Phase 3 Complete:
- [ ] Old loaders.py deprecated
- [ ] CLI uses Pydantic models
- [ ] Geometry modules accept Pydantic models
- [ ] All tests pass

### Phase 4 Complete:
- [ ] pytest tests/ -v → All pass
- [ ] tsc --noEmit → Zero errors
- [ ] Documentation updated
- [ ] Example JSON files validate against schemas

---

## Estimated Effort

- **Phase 0** (Schema infrastructure): 2-3 hours
- **Phase 1** (Restore calculator): 4-6 hours
- **Phase 2** (Web TypeScript): 4-5 hours
- **Phase 3** (Remove old IO): 2-3 hours
- **Phase 4** (Testing & docs): 3-4 hours

**Total: 15-21 hours** of focused work

---

## Next Steps

1. Review and approve this plan
2. Start with Phase 0 (schema infrastructure)
3. Validate schema generation works before proceeding
4. Port calculator to Pydantic incrementally
5. Convert web to TypeScript with generated types

---

## References

- **Pydantic docs**: https://docs.pydantic.dev/
- **JSON Schema**: https://json-schema.org/
- **json-schema-to-typescript**: https://github.com/bcherny/json-schema-to-typescript
- **Legacy code**: git commit 720de75 (web/wormcalc/ directory)
