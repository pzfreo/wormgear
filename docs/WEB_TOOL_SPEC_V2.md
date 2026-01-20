# Worm Gear Design Tool - Unified Web Interface Specification

**Version:** 2.0 (Integrated Calculator + 3D Generator)
**Status:** Design specification for implementation
**Goal:** Single integrated tool that replaces wormgearcalc and provides 3D CAD generation

---

## Vision

A complete worm gear design solution in the browser:
- **Engineers** design using standard parameters (module, angles)
- **Makers** design from envelope constraints (what fits)
- **Everyone** gets validated parameters + CNC-ready STEP files
- **No installation** required - runs entirely in browser via WebAssembly

---

## Core Principle

**Guide users from design intent → validated parameters → manufacturing-ready CAD files with clear feedback at every step.**

---

## Two Main Design Paths

### Path A: Standard Engineering Approach ⚙️

**For:** Engineers familiar with standard gear terminology
**Starting Point:** Module, ratio, pressure angle
**Use Case:** "I want an M2, 30:1 worm gear with 20° pressure angle"

**Flow:**
```
1. Select "Standard Design (Module-Based)"
   ↓
2. Enter standard parameters:
   • Module (ISO 54 standard)
   • Ratio
   • Pressure angle
   • Optional: Number of starts, backlash, hand
   ↓
3. Calculator computes:
   • All derived dimensions (ODs, pitch diameters, etc.)
   • Efficiency estimate
   • Self-locking analysis
   • Validation warnings
   ↓
4. Manufacturing options:
   • Worm length
   • Wheel face width
   • Wheel type (helical vs hobbed)
   • Bore diameter
   • Keyway (DIN 6885)
   ↓
5. Generate STEP files + design JSON
```

**Minimum Required Inputs:**
- Module (mm)
- Ratio (integer)

**Optional Inputs:**
- Pressure angle (default: 20°)
- Number of starts (default: 1)
- Backlash (default: 0mm)
- Hand (default: right)
- Profile shift coefficient (default: 0)

---

### Path B: Envelope Constraint Approach 📐

**For:** Makers/luthiers/designers with space constraints
**Starting Point:** Maximum ODs, ratio
**Use Case:** "I need 30:1 that fits in a 20mm worm × 65mm wheel envelope"

**Flow:**
```
1. Select "Design from Constraints (Envelope)"
   ↓
2. Enter constraints:
   • Worm max OD
   • Wheel max OD
   • Ratio
   • Optional: pressure angle, starts, backlash
   ↓
3. Calculator proposes:
   • Module that fits (may suggest rounding to ISO 54)
   • All computed dimensions
   • Efficiency estimate
   • Self-locking analysis
   • Warnings if constraints conflict
   ↓
4. User reviews/accepts or adjusts constraints
   ↓
5. Manufacturing options (same as Path A)
   ↓
6. Generate STEP files + design JSON
```

**Minimum Required Inputs:**
- Worm max OD (mm)
- Wheel max OD (mm)
- Ratio (integer)

**Optional Inputs:**
- Pressure angle (default: 20°)
- Number of starts (default: 1)
- Backlash (default: 0mm)
- Hand (default: right)
- Round to standard module (default: yes)

---

## Path C: Import Existing Design 📁

**For:** Reproducible builds, iteration, version control
**Use Case:** "I have a proven design JSON, just regenerate the CAD"

**Flow:**
```
1. Select "Import Design"
   ↓
2. Load JSON:
   • Drag-drop file
   • Paste JSON text
   • URL parameter (?design=...)
   ↓
3. Show design summary
   ↓
4. Optional: Override manufacturing params
   • Worm length, wheel width, bore, keyway
   ↓
5. Generate STEP files
```

---

## User Interface - Landing Page

```
┌─────────────────────────────────────────────────────────────────┐
│  🔩 Worm Gear Design Tool                                       │
│  Design → Validate → Generate CNC-Ready STEP Files             │
└─────────────────────────────────────────────────────────────────┘

Choose how to start:

┌─────────────────────────────────────────────┐
│ ⚙️  Standard Engineering Design             │
│                                              │
│ Start with module and standard parameters   │
│ Traditional gear engineering approach       │
│                                              │
│ Best for: Engineers, standard applications  │
│                                              │
│          [Start with Module] ────────────►  │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ 📐 Design from Envelope Constraints         │
│                                              │
│ I know what size it needs to be             │
│ Calculator proposes valid designs           │
│                                              │
│ Best for: Space-constrained applications    │
│                                              │
│          [Design from ODs] ──────────────►  │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ 📁 Import Existing Design                   │
│                                              │
│ Load JSON from previous design              │
│ Reproducible builds                         │
│                                              │
│ Best for: Regenerating proven designs       │
│                                              │
│          [Import JSON] ──────────────────►  │
└─────────────────────────────────────────────┘

───────────────────── or ─────────────────────

┌─────────────────────────────────────────────┐
│ 📚 Example Gallery                          │
│                                              │
│ Browse preset designs with descriptions     │
│                                              │
│ • Guitar tuning machine (7mm, 12:1)        │
│ • Light duty drive (M2, 30:1)              │
│ • High ratio reducer (M3, 60:1)            │
│                                              │
│          [Browse Examples] ──────────────►  │
└─────────────────────────────────────────────┘
```

---

## Detailed UI Flow - Path A (Standard)

### Step 1: Standard Parameters Input

```
┌────────────────────────────────────────────────────┐
│ Standard Engineering Design                        │
├────────────────────────────────────────────────────┤
│                                                     │
│ Required Parameters                                │
│                                                     │
│ Module (mm):      [_2.0__] ⓘ ISO 54 standard      │
│                   Common: 0.5, 1.0, 1.5, 2.0, 3.0  │
│                                                     │
│ Gear Ratio:       [__30__] : 1                     │
│                                                     │
│ ────────────────────────────────                   │
│                                                     │
│ Optional Parameters (click to expand)              │
│ ▼ Advanced Options                                 │
│                                                     │
│   Pressure Angle:  [_20°_] ⓘ Standard: 20° or 25°│
│   Number of Starts: [__1__]                        │
│   Backlash:        [_0.0_] mm                      │
│   Hand:            [Right ▼]                       │
│   Profile Shift:   [_0.0_]                         │
│                                                     │
│   [☐] Prefer standard diameter quotient (DIN 3975)│
│       ⓘ Adjusts design to use q = 8, 10, 12.5, etc.│
│                                                     │
│             [Calculate Design] ─────────►          │
│                                                     │
└────────────────────────────────────────────────────┘
```

**Input Validation (Real-time):**
- Module: Must be > 0.3mm (warn if non-standard ISO 54)
- Ratio: Must be integer ≥ 2
- Pressure angle: Typical 14.5°, 20°, 25°
- Starts: Integer 1-4 (more is unusual)

---

### Step 2: Calculation Results & Validation

```
┌────────────────────────────────────────────────────┐
│ Design Results                                      │
├────────────────────────────────────────────────────┤
│                                                     │
│ ✓ Design Valid                                     │
│                                                     │
│ ═══ Worm ═══                                       │
│ Tip diameter (OD):   20.00 mm                      │
│ Pitch diameter:      16.00 mm                      │
│ Root diameter:       11.00 mm                      │
│ Lead:                6.28 mm (1 start)             │
│ Lead angle:          7.1°                          │
│ Diameter quotient:   8.0 (q = d₁/m) ✓ DIN 3975    │
│                                                     │
│ ═══ Wheel ═══                                      │
│ Teeth:               30                            │
│ Hunting ratio:       ✓ Yes (GCD=1) - even wear    │
│ Tip diameter (OD):   64.00 mm                      │
│ Pitch diameter:      60.00 mm                      │
│ Root diameter:       55.00 mm                      │
│ Throat diameter:     62.00 mm                      │
│ Teeth:               30                            │
│ Helix angle:         82.9°                         │
│                                                     │
│ ═══ Assembly ═══                                   │
│ Centre distance:     38.00 mm                      │
│ Efficiency (est):    72%                           │
│ Self-locking:        No                            │
│                                                     │
│ ⚠️  1 Warning:                                     │
│ • Low lead angle (7.1°) - efficiency only 72%.    │
│   Consider increasing to 10-15° for better         │
│   efficiency, or accept for self-locking benefit.  │
│                                                     │
│         [Adjust Parameters]  [Continue to 3D] ──►  │
│                                                     │
└────────────────────────────────────────────────────┘
```

**Validation Display:**

- ✓ **Valid** (green) - No errors, safe to proceed
- ⚠️ **Warnings** (yellow) - Valid but suboptimal, show advice
- ❌ **Errors** (red) - Invalid, must fix before proceeding

**Common Warnings:**
- Lead angle < 3°: "Very inefficient, only ~50% efficiency"
- Lead angle > 25°: "Not self-locking - needs brake/lock"
- Module non-standard: "Module 2.3mm not ISO 54 - prefer 2.0mm or 2.5mm"
- Wheel teeth < 24: "Risk of undercut - verify with CAD"

**Common Errors:**
- Lead angle < 1°: "Impractical - too steep, increase module or starts"
- Worm pitch dia < 3×module: "Worm shaft too weak"
- Wheel teeth < 17: "Severe undercut - impossible to manufacture"

---

### Step 3: Manufacturing Parameters

```
┌────────────────────────────────────────────────────┐
│ Manufacturing Options                               │
├────────────────────────────────────────────────────┤
│                                                     │
│ Worm Dimensions                                    │
│                                                     │
│ Length:           [__40__] mm                      │
│                   ⓘ Minimum for full engagement:   │
│                     ~15mm (suggested: 30-50mm)     │
│                                                     │
│ Bore:             [Auto: 4.0mm ▼]                  │
│                   • Auto (~25% of pitch dia)       │
│                   • Custom diameter                │
│                   • No bore (solid)                │
│                                                     │
│ Keyway:           [☑] DIN 6885 (auto-sized)       │
│                   ⓘ 4mm bore: no keyway available  │
│                     (DIN 6885 requires ≥6mm)       │
│                                                     │
│ ─────────────────────────────────────              │
│                                                     │
│ Wheel Dimensions                                   │
│                                                     │
│ Face Width:       [Auto: 12mm ▼]                   │
│                   ⓘ Suggested: 0.7 × worm OD       │
│                     (calculated: 14mm)             │
│                                                     │
│ Tooth Type:       ( ) Helical (simple)             │
│                   (•) Hobbed (throated) [Recommended]│
│                   ⓘ Hobbed provides better contact │
│                                                     │
│ Bore:             [Auto: 15mm ▼]                   │
│ Keyway:           [☑] DIN 6885 (5×2.3mm)          │
│                                                     │
│         [Generate STEP Files] ─────────►           │
│                                                     │
└────────────────────────────────────────────────────┘
```

**Auto-Calculations (shown as defaults):**
- Worm length: 40mm (user should specify based on shaft needs)
- Worm bore: ~25% of pitch diameter, rounded to nice value
- Wheel bore: ~25% of pitch diameter
- Wheel face width: ~0.7 × worm OD (based on standard practice)
- Keyway: DIN 6885 auto-sized from bore (if bore ≥ 6mm)

**Thin Rim Warning:**
If auto-bore results in rim < 1.5mm:
```
⚠️ Thin rim on small bore - handle with care
Worm: 2.0mm bore, rim thickness 1.38mm
```

---

### Step 4: Quick Preview (3D Visualization)

```
┌────────────────────────────────────────────────────┐
│ Generating Preview...                               │
├────────────────────────────────────────────────────┤
│                                                     │
│ [████████████████████] 100%                       │
│                                                     │
│ Preview ready (5 seconds)                          │
│                                                     │
└────────────────────────────────────────────────────┘

↓ Preview displays ↓

┌────────────────────────────────────────────────────┐
│ 3D Preview                          [Fullscreen] □ │
├────────────────────────────────────────────────────┤
│                                                     │
│     ┌─────────────────────────────────────┐       │
│     │                                       │       │
│     │         [3D WebGL Viewer]            │       │
│     │                                       │       │
│     │    Interactive view of worm + wheel  │       │
│     │    • Rotate: drag                     │       │
│     │    • Zoom: scroll                     │       │
│     │    • Pan: right-drag                  │       │
│     │                                       │       │
│     │    [Show Worm] [Show Wheel] [Both]   │       │
│     │    [Mesh Aligned]                     │       │
│     │                                       │       │
│     └─────────────────────────────────────┘       │
│                                                     │
│ ⓘ This is a fast preview with simplified geometry │
│   Production STEP files will have exact detail     │
│                                                     │
│ Design Summary                                     │
│ Module: 2.0mm | Ratio: 30:1 | Center: 38.00mm     │
│ Worm: Ø20×40mm | Wheel: Ø64×12mm (hobbed)         │
│                                                     │
│    [← Adjust Parameters]  [Generate Production] ──►│
│                                                     │
└────────────────────────────────────────────────────┘
```

**Quick Preview Characteristics:**
- **Fast**: 5-10 seconds generation
- **Simplified geometry**: Fewer sections (12 per turn vs 36)
- **Approximate**: Simplified tooth profiles, basic throating
- **Purpose**: Visual validation, catch major errors

---

### Step 5: Production Generation & Downloads

```
┌────────────────────────────────────────────────────┐
│ Generating Production Files...                      │
├────────────────────────────────────────────────────┤
│                                                     │
│ [████████████████░░░░] 75%                        │
│                                                     │
│ Building wheel (hobbed, full detail, 30 teeth)...  │
│ Estimated time remaining: 15 seconds               │
│                                                     │
└────────────────────────────────────────────────────┘

↓ After completion (30-60 seconds) ↓

┌────────────────────────────────────────────────────┐
│ ✅ Production Files Ready!                         │
├────────────────────────────────────────────────────┤
│                                                     │
│ Download Files:                                    │
│                                                     │
│ 📥 [worm_m2_z1_r30.step]                (18 KB)   │
│    CNC-ready STEP file - exact geometry           │
│                                                     │
│ 📥 [wheel_m2_z30_r30_hobbed.step]      (1.2 MB)   │
│    CNC-ready STEP file - exact geometry           │
│                                                     │
│ 📄 [manufacturing_spec.pdf]             (125 KB)   │
│    Complete manufacturing specification            │
│    • Dimensional drawings with tolerances          │
│    • Material recommendations                      │
│    • Assembly instructions                         │
│    • Machining notes                               │
│                                                     │
│ 📥 [design.json]                        (2 KB)     │
│    Design parameters (for reproducibility)         │
│                                                     │
│ ─────────────────────────────────────              │
│                                                     │
│ ⓘ All files downloaded as: worm-gear-m2-r30.zip  │
│                                                     │
│      [View 3D Again]  [Design Another]             │
│                                                     │
└────────────────────────────────────────────────────┘
```

**Production Output Characteristics:**
- **Exact**: Full detail, exact geometry per spec
- **Slower**: 30-60 seconds generation
- **CNC-Ready**: STEP files with proper tolerances
- **Complete Package**: STEP + PDF + JSON

---

## Detailed UI Flow - Path B (Envelope Constraints)

### Step 1: Constraint Input

```
┌────────────────────────────────────────────────────┐
│ Design from Envelope Constraints                   │
├────────────────────────────────────────────────────┤
│                                                     │
│ What space do you have?                            │
│                                                     │
│ Worm Max OD:      [__20__] mm                      │
│                   ⓘ Outside diameter constraint    │
│                                                     │
│ Wheel Max OD:     [__65__] mm                      │
│                   ⓘ Outside diameter constraint    │
│                                                     │
│ Gear Ratio:       [__30__] : 1                     │
│                                                     │
│ ────────────────────────────────                   │
│                                                     │
│ ▼ Options                                          │
│                                                     │
│   Pressure Angle:  [_20°_]                         │
│   Number of Starts: [__1__]                        │
│   Backlash:        [_0.0_] mm                      │
│   Hand:            [Right ▼]                       │
│                                                     │
│   [☑] Round to standard module (ISO 54)           │
│       ⓘ Recommended for manufacturability          │
│                                                     │
│        [Calculate Proposed Design] ─────────►      │
│                                                     │
└────────────────────────────────────────────────────┘
```

---

### Step 2: Proposed Design with Constraint Feedback

**Scenario A: Design fits cleanly**

```
┌────────────────────────────────────────────────────┐
│ Proposed Design (fits constraints)                 │
├────────────────────────────────────────────────────┤
│                                                     │
│ ✓ Valid design found                               │
│                                                     │
│ Calculated Module: 2.05mm                          │
│ → Rounded to: 2.0mm (ISO 54 standard)             │
│                                                     │
│ ═══ Worm ═══                                       │
│ Tip diameter:   20.00 mm  (max: 20.00) ✓          │
│ Pitch diameter: 16.00 mm                           │
│ Root diameter:  11.00 mm                           │
│ Lead angle:     7.1°                               │
│                                                     │
│ ═══ Wheel ═══                                      │
│ Tip diameter:   64.00 mm  (max: 65.00) ✓          │
│ Pitch diameter: 60.00 mm                           │
│ Root diameter:  55.00 mm                           │
│ Teeth:          30                                 │
│                                                     │
│ ═══ Performance ═══                                │
│ Centre distance: 38.00 mm                          │
│ Efficiency:      72%                               │
│ Self-locking:    No                                │
│                                                     │
│ ⓘ Fits with margin:                                │
│   Worm: 0.0mm margin                               │
│   Wheel: 1.0mm margin                              │
│                                                     │
│    [Adjust Constraints]  [Accept & Continue] ──►   │
│                                                     │
└────────────────────────────────────────────────────┘
```

**Scenario B: Design requires tradeoffs**

```
┌────────────────────────────────────────────────────┐
│ ⚠️  Proposed Design (tight constraints)            │
├────────────────────────────────────────────────────┤
│                                                     │
│ Design found, but constraints conflict             │
│                                                     │
│ Problem:                                           │
│ • Worm OD 20mm is too small for 30:1 ratio        │
│ • Calculated module would be 1.8mm                │
│ • Rounded to 2.0mm ISO 54 → worm OD becomes 20mm  │
│ • This leaves NO margin for error                  │
│                                                     │
│ Suggestions:                                       │
│ → Increase worm OD to 22mm (gives 2mm margin)     │
│ → Reduce ratio to 25:1 (fits in 20mm)            │
│ → Use 1.5mm module (non-standard but fits)        │
│                                                     │
│ Current Calculated Design:                         │
│ Module: 2.0mm (ISO 54)                             │
│ Worm OD: 20.00mm (max: 20.00) ⚠️ at limit         │
│ Wheel OD: 64.00mm (max: 65.00) ✓                  │
│ Efficiency: 72%                                    │
│                                                     │
│    [Adjust Constraints]  [Accept Anyway] ──►       │
│                                                     │
└────────────────────────────────────────────────────┘
```

**Scenario C: Impossible constraints**

```
┌────────────────────────────────────────────────────┐
│ ❌ Cannot fit design in constraints                │
├────────────────────────────────────────────────────┤
│                                                     │
│ The specified constraints are impossible:          │
│                                                     │
│ Problem:                                           │
│ • 30:1 ratio requires module ≥ 1.5mm              │
│ • Module 1.5mm needs worm OD ≥ 18mm               │
│ • Module 1.5mm needs wheel OD ≥ 49.5mm            │
│ • Your wheel OD limit: 45mm ← TOO SMALL           │
│                                                     │
│ To fix, you must either:                           │
│ → Increase wheel OD to ≥ 50mm                     │
│ → Reduce ratio to ≤ 25:1                          │
│ → Accept very small module (weak, not recommended)│
│                                                     │
│           [Adjust Constraints]                      │
│                                                     │
└────────────────────────────────────────────────────┘
```

---

Then continues to Step 3 (Manufacturing) and Step 4 (Generation) same as Path A.

---

## Validation Rules & Messaging

### Validation Severity Levels

**❌ Error (Blocking):**
- Lead angle < 1°
- Module < 0.3mm
- Wheel teeth < 17 (severe undercut)
- Worm diameter quotient q < 3 (shaft too weak)

**⚠️ Warning (Proceed with caution):**
- Lead angle 1-3° (very inefficient)
- Lead angle > 25° (not self-locking, mention need for brake)
- Module non-standard (suggest nearest ISO 54)
- Wheel teeth 17-24 (some undercut risk)
- Worm diameter quotient q < 5 (verify shaft strength)
- Worm diameter quotient q > 20 (very thick, check efficiency)
- Worm diameter quotient q non-standard (suggest nearest DIN 3975: 8, 10, 12.5, 16, 20, 25)
- Non-hunting tooth ratio when multi-start (GCD(starts, teeth) > 1) - uneven wear
- Rim thickness < 1.5mm (thin rim)

**ℹ️ Info (Helpful context):**
- Efficiency estimate explanation
- Self-locking behavior
- Standard module benefits (ISO 54)
- Standard diameter quotient benefits (DIN 3975)
- Manufacturing notes

### Message Style

**Bad:** "Invalid parameter"

**Good:** "Lead angle 0.8° is too steep - impossible to manufacture. Increase module to 2.0mm or add more starts."

**Bad:** "Warning: low efficiency"

**Good:** "Low efficiency (52%) due to lead angle 3.2°. Increase to 10-15° for typical 70-85% efficiency. Alternatively, accept lower efficiency if self-locking is required."

**Example q validation messages:**

**Error (q < 3):**
"Worm shaft too weak - diameter quotient q=2.8 is below minimum. Increase worm diameter or reduce module to achieve q ≥ 3."

**Warning (q < 5):**
"Worm shaft may be weak - diameter quotient q=4.2 is below recommended minimum of 5. Verify strength calculations or increase worm diameter."

**Info (q non-standard):**
"Diameter quotient q=11.3 is not a DIN 3975 standard value. Nearest standards: q=10 or q=12.5. Check 'Prefer standard q' for automatic adjustment."

**Warning (non-hunting ratio with multi-start):**
"Non-hunting tooth ratio detected: 2-start worm with 30 teeth (GCD=2). Same threads will always contact same teeth, causing uneven wear. Consider 29 or 31 teeth for hunting ratio (even wear distribution)."

**Info (hunting ratio confirmed):**
"Hunting tooth ratio: GCD(starts=2, teeth=31) = 1. All worm threads will contact all wheel teeth over time, ensuring even wear."

---

## Technical Architecture

### Stack

```
┌─────────────────────────────────────────┐
│  Single Page Application (HTML/JS)     │
├─────────────────────────────────────────┤
│  Pyodide 0.25+ (Python in WASM)        │
│  ├─ wormcalc package (calculator)      │
│  ├─ wormgear_geometry (3D generation)  │
│  ├─ build123d + OCP (CAD kernel)       │
│  └─ micropip (package manager)         │
├─────────────────────────────────────────┤
│  UI Framework: Vanilla JS (keep simple)│
│  Styling: CSS (responsive)              │
│  Optional: Three.js for preview         │
└─────────────────────────────────────────┘
```

### Data Flow

```
User Input
    ↓
Calculator (wormcalc)
    ↓
Validation Results + Computed Parameters
    ↓
User confirms/adjusts
    ↓
Add Manufacturing Params
    ↓
3D Geometry Generator (wormgear_geometry)
    ↓
STEP Files + Design JSON
```

### Loading Strategy

1. **Initial page load:** Fast, shows UI immediately
2. **Pyodide init:** Load in background with progress indicator
3. **Package install:** Load wormcalc + wormgear_geometry on first use
4. **Caching:** Cache Pyodide/packages in browser (IndexedDB)
5. **Performance:** Show "Initializing..." only on first visit

---

## File Outputs

### Quick Preview Generation:
- **3D preview model** (in-browser only, not downloadable)
- Simplified geometry for fast rendering
- Interactive WebGL view

### Production Generation:

**Always:**
1. `worm_mX_zY_rZ.step` - Worm STEP file (exact, CNC-ready)
2. `wheel_mX_zY_rZ.step` - Wheel STEP file (exact, CNC-ready)
3. `manufacturing_spec.pdf` - Complete manufacturing specification
4. `design.json` - Complete design parameters (for reproducibility)

**Packaged as:**
- `worm-gear-mX-rY.zip` - All files in one download

---

## Manufacturing Specification PDF

The PDF should be a complete document suitable for CNC machining:

### Page 1: Design Summary
```
┌─────────────────────────────────────────────┐
│ WORM GEAR DESIGN SPECIFICATION              │
│ Module 2.0mm, Ratio 30:1                    │
├─────────────────────────────────────────────┤
│                                              │
│ Design Parameters                            │
│ • Module: 2.0mm (ISO 54)                    │
│ • Ratio: 30:1                               │
│ • Pressure Angle: 20°                       │
│ • Hand: Right                               │
│ • Centre Distance: 38.00mm (±0.05mm)        │
│                                              │
│ Performance                                  │
│ • Estimated Efficiency: 72%                 │
│ • Self-locking: No                          │
│ • Diameter Quotient (q): 8.0 ✓ DIN 3975    │
│                                              │
│ Files Included                               │
│ • worm_m2_z1_r30.step                       │
│ • wheel_m2_z30_r30_hobbed.step              │
│ • design.json                               │
│                                              │
│ Generated: 2026-01-20 14:32 UTC             │
│ Tool: Worm Gear Design Tool v2.0            │
└─────────────────────────────────────────────┘
```

### Page 2: Worm Specification

**Dimensional Drawing:**
- Side view with key dimensions labeled
- Cross-section showing thread profile
- All dimensions with tolerances

**Dimension Table:**
| Parameter | Nominal | Tolerance | Note |
|-----------|---------|-----------|------|
| Outside Diameter (OD) | 20.00mm | ±0.02mm | Finish ground |
| Pitch Diameter | 16.00mm | Reference | Measured over wires |
| Root Diameter | 11.00mm | +0.05/-0mm | - |
| Length | 40.00mm | ±0.1mm | Overall |
| Lead | 6.283mm | ±0.01mm | Per thread |
| Lead Angle | 7.1° | ±0.1° | Reference |
| Thread Hand | Right | - | - |
| Bore Diameter | 4.00mm | H7 | Through |

**Material Recommendations:**
- Steel: EN24 (heat treated), 41Cr4, or equivalent
- Bronze: PB2 or SAE 660 for higher loads
- Surface Finish: Ra 1.6μm on thread flanks

**Machining Notes:**
- Best practice: 4-axis lathe with live tooling
- Alternative: 5-axis mill
- Thread cutting: Single-point or whirl cutter
- Final finish: Grind thread flanks for precision

### Page 3: Wheel Specification

**Dimensional Drawing:**
- Front view showing teeth
- Side view showing face width and throat
- Section view showing tooth profile

**Dimension Table:**
| Parameter | Nominal | Tolerance | Note |
|-----------|---------|-----------|------|
| Outside Diameter (OD) | 64.00mm | ±0.05mm | - |
| Pitch Diameter | 60.00mm | Reference | - |
| Root Diameter | 55.00mm | +0.1/-0mm | - |
| Throat Diameter | 62.00mm | ±0.05mm | Hobbed type |
| Face Width | 12.00mm | ±0.1mm | - |
| Number of Teeth | 30 | - | - |
| Bore Diameter | 15.00mm | H7 | Through |
| Keyway | 5×2.3mm | DIN 6885 | Hub depth |

**Material Recommendations:**
- Phosphor Bronze: PB2, PB4 (preferred for wear)
- Aluminum Bronze: AB2
- Cast Iron: For low-speed, low-load applications
- Surface Finish: Ra 3.2μm

**Machining Notes:**
- Best practice: 5-axis mill for true tooth form
- Alternative: Indexed 4-axis with ball-nose finishing
- Throating: Match worm tip radius exactly
- Keyway: Standard broaching

### Page 4: Assembly Instructions

**Assembly Requirements:**
- Axes must be perpendicular: 90° ±0.05°
- Centre distance: 38.00mm ±0.05mm
- Axial alignment: ±0.1mm
- Angular alignment: ±0.1°

**Lubrication:**
- Required for all applications
- Recommended: ISO VG 220 gear oil
- Initial break-in: Run at 25% load for 1 hour
- Maintenance: Check oil level every 100 hours

**Quality Checks:**
- Backlash: Should be 0.05-0.15mm
- Contact pattern: Check with marking compound
- Smooth operation: No binding or excessive noise
- Temperature: Should not exceed 60°C under load

**Warnings:**
- Do not run dry - permanent damage will occur
- Verify alignment before full load operation
- Self-locking: This design is NOT self-locking
  (brake or lock mechanism required if needed)

### Page 5: Technical Drawings

**2D dimensional drawings with GD&T:**
- Worm profile view
- Wheel profile view
- Assembly view showing meshing
- Critical dimensions highlighted

### design.json structure (expanded)

Includes all calculator outputs PLUS manufacturing parameters for complete reproducibility:

```json
{
  "worm": {
    "module_mm": 2.0,
    "num_starts": 1,
    "pitch_diameter_mm": 16.0,
    "tip_diameter_mm": 20.0,
    "root_diameter_mm": 11.0,
    "lead_mm": 6.283,
    "lead_angle_deg": 7.1,
    "addendum_mm": 2.0,
    "dedendum_mm": 2.5,
    "thread_thickness_mm": 3.14,
    "hand": "right",
    "profile_shift": 0.0,
    "diameter_quotient": 8.0
  },
  "wheel": {
    "module_mm": 2.0,
    "num_teeth": 30,
    "pitch_diameter_mm": 60.0,
    "tip_diameter_mm": 64.0,
    "root_diameter_mm": 55.0,
    "throat_diameter_mm": 62.0,
    "helix_angle_deg": 82.9,
    "addendum_mm": 2.0,
    "dedendum_mm": 2.5,
    "profile_shift": 0.0
  },
  "assembly": {
    "centre_distance_mm": 38.0,
    "pressure_angle_deg": 20.0,
    "backlash_mm": 0.05,
    "hand": "right",
    "ratio": 30,
    "efficiency_estimate": 0.72,
    "self_locking": false,
    "hunting_ratio": true
  },
  "manufacturing": {
    "worm": {
      "length_mm": 40.0,
      "bore": {
        "enabled": true,
        "diameter_mm": 4.0,
        "tolerance": "H7",
        "through": true
      },
      "keyway": {
        "enabled": false,
        "reason": "bore_too_small"
      },
      "sections_per_turn": 36
    },
    "wheel": {
      "face_width_mm": 12.0,
      "throated": true,
      "bore": {
        "enabled": true,
        "diameter_mm": 15.0,
        "tolerance": "H7",
        "through": true
      },
      "keyway": {
        "enabled": true,
        "width_mm": 5.0,
        "depth_mm": 2.3,
        "standard": "DIN_6885",
        "is_shaft": false
      }
    }
  },
  "validation": {
    "valid": true,
    "errors": [],
    "warnings": [
      {
        "code": "LOW_LEAD_ANGLE",
        "message": "Low lead angle (7.1°) - efficiency only 72%. Consider increasing to 10-15° for better efficiency.",
        "severity": "warning"
      }
    ],
    "info": []
  },
  "metadata": {
    "design_mode": "from-module",
    "input_parameters": {
      "module": 2.0,
      "ratio": 30,
      "pressure_angle": 20,
      "num_starts": 1,
      "backlash": 0.05,
      "hand": "right",
      "profile_shift": 0.0,
      "use_standard_module": true,
      "use_standard_q": false
    },
    "generated_at": "2026-01-20T14:32:00Z",
    "tool_name": "Worm Gear Design Tool",
    "tool_version": "2.0.0",
    "calculator_version": "1.5.0",
    "generator_version": "2.1.0"
  }
}
```

**Key additions in manufacturing section:**
- Complete bore specifications (diameter, tolerance, through/blind)
- Complete keyway specifications (dimensions, standard, shaft/hub)
- Worm length and sections_per_turn
- Wheel face width and throated flag
- Reasons for disabled features (e.g., "bore_too_small" for no keyway)

---

## Implementation Phases

### Phase 1: Core Integration (MVP) 🎯
- [ ] Integrate wormcalc code into web interface
- [ ] Implement Path A (standard/module-based)
- [ ] Implement Path B (envelope constraints)
- [ ] Implement Path C (JSON import)
- [ ] Connect calculator → 3D generator flow
- [ ] Validation UI (errors, warnings, info) with actionable messages
- [ ] Manufacturing parameter controls (bore, keyway, lengths)
- [ ] **Quick preview generation** (simplified geometry, 5-10 seconds)
- [ ] **3D visualization** (WebGL viewer - Three.js or model-viewer)
- [ ] Interactive 3D controls (rotate, zoom, pan, toggle parts)
- [ ] **Production generation** (full detail STEP files, 30-60 seconds)
- [ ] **PDF manufacturing spec** (complete with drawings, tolerances, assembly)
- [ ] design.json export
- [ ] Zip package download (STEP + PDF + JSON)
- [ ] All validation rules including q, hunting teeth

### Phase 2: Polish & Usability
- [ ] Example gallery with presets
- [ ] Design summary panel (always visible)
- [ ] Mobile responsive design
- [ ] Loading states & progress indicators (estimated time)
- [ ] Error recovery (retry logic)
- [ ] Share links (URL params with encoded JSON)
- [ ] "Prefer standard q" checkbox implementation
- [ ] Fullscreen 3D viewer mode
- [ ] Assembly view (both parts meshed, animated rotation)

### Phase 3: Advanced Features
- [ ] 2D technical drawings in PDF (GD&T annotations)
- [ ] Editable tolerances in manufacturing options
- [ ] Custom material selection in UI
- [ ] Offline support (service worker)
- [ ] Batch generation (multiple designs)
- [ ] Design history (localStorage)
- [ ] Comparison mode (compare 2-3 designs side-by-side)

### Phase 4: Educational & Pro Features
- [ ] Inline help & tooltips for every parameter
- [ ] "What's this?" explanations with diagrams
- [ ] Efficiency calculator with interactive graphs
- [ ] Design optimization suggestions (AI-powered)
- [ ] Contact pattern visualization
- [ ] Stress analysis integration
- [ ] Cost estimation (material + machining time)
- [ ] Integration with CAM software (generate toolpaths)

---

## Open Design Questions

### 1. Module Input ✓ DECIDED: Dropdown

**Path A (Standard Design):**
```
Module: [2.0mm ▼]
        Options: 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, ...
        (ISO 54 standard values only)
```

**Path B (Envelope Constraints):**
- Calculator computes module from constraints
- Shows: "Calculated module: 2.05mm → Rounded to: 2.0mm (ISO 54)"
- Option to disable rounding (advanced users)

---

### 2. Warning Handling ✓ DECIDED: Just display

Show warnings prominently but don't block:

```
⚠️ 1 Warning

Low lead angle (7.1°) - efficiency only 72%.
Consider increasing to 10-15° for better efficiency.

    [← Adjust Parameters]  [Continue to Manufacturing] ──►
```

Users can see warnings, make informed decision, no friction.

---

### 3. Manufacturing Options ✓ DECIDED: Always visible

Show all manufacturing parameters with smart defaults:

```
┌────────────────────────────────────────────┐
│ Manufacturing Parameters                    │
├────────────────────────────────────────────┤
│                                             │
│ Worm:                                       │
│   Length:    [__40__] mm                   │
│   Bore:      [Auto: 4mm ▼] (H7 tolerance) │
│   Keyway:    [☐] Not available (bore < 6mm)│
│                                             │
│ Wheel:                                      │
│   Face Width: [Auto: 12mm ▼]               │
│   Type:       (•) Hobbed  ( ) Helical      │
│   Bore:       [Auto: 15mm ▼] (H7)         │
│   Keyway:     [☑] DIN 6885 (5×2.3mm)      │
│                                             │
└────────────────────────────────────────────┘
```

Transparent, educational, defaults are good enough for most users.

---

### 4. 3D Viewer Technology - Three.js or model-viewer?

**Three.js:**
- More control over rendering
- Custom interactions and animations
- Lightweight for preview geometry
- Community support

**model-viewer:**
- Simpler integration (web component)
- Built-in AR support
- Standard glTF/GLTF loading
- Less code to maintain

**Recommendation:** Three.js for flexibility, especially for quick preview rendering and assembly animations.

---

### 4. Mobile Support ✓ DECIDED: Desktop only

**Not supported due to:**
- WebAssembly + build123d too CPU/memory intensive
- 3D rendering requires significant GPU
- STEP generation takes 30-60 seconds even on desktop
- Complex forms need screen real estate

**Implementation:**
- Desktop-only (1024px minimum width)
- Show message on mobile: "This tool requires a desktop browser"
- Link to downloadable CLI version for power users
- Future: Could add mobile-friendly calculator-only mode (no 3D gen)

---

## Success Metrics

The tool succeeds when:

1. **95% of users** complete their first design without errors
2. **Engineers validate output** - STEP files import cleanly to CAD/CAM
3. **Fast iteration** - Tweak params → new STEP in <60 seconds
4. **Clear traceability** - Every STEP regenerable from design.json
5. **Useful feedback** - Validation messages help fix issues
6. **Replaces both tools** - wormgearcalc can be retired

---

## Migration from wormgearcalc

### Compatibility

- Accept existing wormgearcalc JSON without changes
- Support URL params from wormgearcalc links
- Provide redirect from old tool to new

### Deprecation Plan

1. **Month 1-2:** Build new integrated tool
2. **Month 3:** Soft launch, link from wormgearcalc
3. **Month 4:** Add banner to wormgearcalc: "Try the new version!"
4. **Month 5:** Default to new tool, old tool at /legacy
5. **Month 6+:** Redirect old tool to new, archive old code

---

## Next Steps

1. **Review this spec** - Validate approach with Paul
2. **Wireframe key screens** - Especially validation results, error states
3. **Start with Path A** - Standard design is simpler, build confidence
4. **Iterate on UX** - Get validation messaging right
5. **Add Path B** - Envelope constraints (reuse wormcalc logic)
6. **Polish & ship** - Example gallery, share links, etc.

---

**Ready to build when design is validated!**
