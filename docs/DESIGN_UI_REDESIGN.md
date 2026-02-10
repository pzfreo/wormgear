# Web UI Redesign: Design Document

**Author:** Claude (with Paul Fremantle)
**Date:** 2026-02-10
**Status:** Draft for Review
**Branch:** `claude/redesign-ui-shapes-ASnNi`

---

## 1. Motivation

The current web UI was built around the developer's use cases and exposes all options
in a flat structure. This redesign addresses three problems:

1. **Cylindrical and globoid worm gears are mixed** - globoid-specific fields (throat
   reduction, trim-to-min-engagement) clutter the cylindrical workflow, and the two are
   fundamentally different design choices.

2. **The UI isn't structured for an engineering workflow** - options like bore size,
   keyway type, and virtual hobbing are interleaved with core gear parameters. An
   engineer thinks in stages: define the gear pair first, then refine, then specify
   the shaft interface.

3. **Design and 3D generation are conflated** - virtual hobbing parameters (step count,
   precision) are in the calculator tab, but they only affect how the 3D model is built,
   not the gear design itself.

---

## 2. Design Principles

### 2.1 Prioritise Normal Practice, Help the Beginner

- **Defaults produce a valid, manufacturable design with zero changes.** An engineer
  should be able to hit "Calculate" on first load and get something sensible.
- **Standard engineering workflow:** core dimensions first, refinements second, shaft
  interface third.
- **Inline help on every parameter** - not tooltips (hidden), but always-visible hint
  text that explains what the parameter means and what's standard. A beginner can learn
  gear design by reading the UI.

### 2.2 Design vs Generation

- The **calculator** defines *what the gear is* - the spec sheet you'd hand to a
  manufacturer. This includes throating as a design intent.
- The **3D generator** defines *how the model is built* - virtual hobbing vs helical
  approximation, hobbing step count, mesh smoothness. These are quality/speed tradeoffs
  for the CAD output.

### 2.3 Output is a Design Package

The output should look like something you'd send to a gear manufacturer: a clear
specification sheet with validation, not a debug console dump.

---

## 3. Proposed Layout

### 3.1 Top-Level Tab Structure

```
[ Cylindrical Worm Gear ]  [ Globoid Worm Gear ]    |    [ 3D Generator ]
         ^^^ DESIGN PHASE ^^^                             ^^^ BUILD PHASE ^^^
```

- The first two tabs are the **design phase**. They produce a complete gear specification.
- The third tab is the **build phase**. It consumes a design and produces 3D geometry.
- Visual separation (gap, divider, or different background) between design and build tabs.

### 3.2 Within Each Design Tab: Stepped Sections

Left column (inputs), right column (results). Same two-column layout as today, but the
left column is structured as a progression:

```
LEFT COLUMN                          RIGHT COLUMN
+----------------------------------+ +----------------------------------+
| Step 1: Core Design              | | Validation                       |
|   [always visible]               | |   [errors, warnings, info]       |
|                                  | |                                  |
+----------------------------------+ +----------------------------------+
| Step 2: Advanced Gear Options    | | Specification Sheet              |
|   [collapsed by default]         | |   [formatted table]              |
|                                  | |                                  |
+----------------------------------+ +----------------------------------+
| Step 3: Bore & Shaft Interface   | | Export                           |
|   [collapsed by default]         | |   [JSON, Markdown, Share, -> 3D] |
|                                  | |                                  |
+----------------------------------+ +----------------------------------+
```

A beginner fills in Step 1 and gets a valid design. An experienced engineer opens
Steps 2 and 3 to refine.

---

## 4. Step 1: Core Design

### 4.1 Design Mode

**Change from current:** reorder modes to put the most common first. Default to
**From Module**.

| Mode | Input Fields | When to Use |
|------|-------------|-------------|
| **From Module** (default) | module, ratio | "I know what module I need" - most common starting point |
| From Centre Distance | centre_distance, ratio | "I have a fixed shaft spacing" |
| From Wheel OD | wheel_od, ratio, target_lead_angle | "The wheel must fit in this space" |
| Envelope | worm_od, wheel_od, ratio | "Both parts must fit in this space" |

Each mode shows only its relevant input fields (same as today).

### 4.2 Common Parameters (All Modes)

| Parameter | Default | Input Type | Hint Text |
|-----------|---------|-----------|-----------|
| Ratio | 30 | integer | "Wheel teeth per worm start. Higher = more reduction." |
| Number of starts | 1 | integer (1-4) | "1 = self-locking at low lead angles. 2-4 = higher speed, no self-locking." |
| Pressure angle | 20 | degrees | "20 deg is standard (DIN 3975). 14.5 deg for legacy, 25 deg for high strength." |
| Hand | Right | select | "Right-hand is standard. Left-hand for special arrangements." |

### 4.3 Globoid Tab Additions

The **Globoid Worm Gear** tab includes all of Step 1 above, plus:

| Parameter | Default | Hint Text |
|-----------|---------|-----------|
| Throat reduction | Auto (geometric) | "Controls hourglass depth. Auto calculates from pitch geometry." |
| Throat reduction custom | (if custom) | "mm - Deeper throat = more contact area but harder to manufacture." |

The `worm_type` field is **not shown** - it's implicit from the tab choice. Cylindrical
tab sets `worm_type=cylindrical`, globoid tab sets `worm_type=globoid`.

---

## 5. Step 2: Advanced Gear Options

Collapsed by default. Header: **"Advanced Gear Options"**.

### 5.1 Common Parameters (Both Tabs)

| Parameter | Default | Hint Text |
|-----------|---------|-----------|
| Tooth profile | ZA | "**ZA** - Straight flanks, standard for CNC machining. **ZK** - Convex flanks, better for 3D printing (FDM stress, layer adhesion). **ZI** - Involute, high precision hobbing." |
| Backlash | 0.05 mm | "Clearance between meshing teeth. 0.05 mm typical for precision. 0.1-0.2 mm for 3D printed parts." |
| Profile shift | 0.0 | "Adjusts tooth depth to prevent undercut on low tooth counts. Positive = thicker teeth." |
| Standard module rounding | checked | "Round to nearest ISO 54 standard module for tooling availability." |
| Stub teeth | off | "Reduce wheel tip diameter for compact assemblies. Shortens teeth." |
| Wheel tip reduction | (if stub checked) | "mm - Amount to reduce wheel tip diameter." |
| Throated wheel | off | "Shape wheel teeth to match worm curvature. Better contact area, requires hobbing or 5-axis machining." |
| Worm length | Recommended | "Auto-calculated from contact geometry. Uncheck to specify custom length." |
| Wheel width | Recommended | "Auto-calculated face width. Uncheck to specify custom width." |

### 5.2 Globoid Tab Additions

| Parameter | Default | Hint Text |
|-----------|---------|-----------|
| Trim to min engagement | off | "Remove flared edges at wheel rim. Wheel OD becomes uniform at engagement zone diameter." |

### 5.3 Removed from Calculator (Moved to Generator)

The following are **not shown** in the calculator tabs. They move to the 3D Generator:

| Parameter | Why It's a Generation Concern |
|-----------|------------------------------|
| Wheel generation method (helical / virtual hobbing) | Affects how the 3D model is built, not the design spec |
| Hobbing precision (36/72/144 steps) | Quality/speed tradeoff for 3D model generation |
| Sections per turn | Worm mesh smoothness in the 3D model |

**Throating** remains a design concern (it's on the spec sheet: "this wheel should be
throated"). The *method* of achieving throating in the 3D model is a generation concern.

### 5.4 Default Changes from Current UI

| Parameter | Old Default | New Default | Rationale |
|-----------|------------|-------------|-----------|
| Design mode | Envelope | From Module | Most common engineering starting point |
| Backlash | 0.0 mm | 0.05 mm | Real gears need clearance; 0 is unrealistic |
| Worm anti-rotation | None | DIN 6885 | Engineers expect a keyed bore by default |
| Wheel anti-rotation | None | DIN 6885 | Same reasoning |

---

## 6. Step 3: Bore & Shaft Interface

Collapsed by default. Header: **"Bore & Shaft Interface"**.

This section defines how each gear mounts to its shaft. It's clearly separate from
gear geometry because it's about the shaft interface, not the tooth form.

### 6.1 Layout

Two side-by-side sub-sections: **Worm** and **Wheel**, each with identical structure:

```
+-- Worm Shaft ------------------+  +-- Wheel Shaft -----------------+
| Bore: [Auto-calculated v]      |  | Bore: [Auto-calculated v]      |
|   Recommended: 5.2 mm          |  |   Recommended: 12.0 mm         |
| Anti-rotation: [DIN 6885 v]    |  | Anti-rotation: [DIN 6885 v]    |
|   Keyway: 2x2mm (DIN 6885)     |  |   Keyway: 4x4mm (DIN 6885)    |
+--------------------------------+  +--------------------------------+
```

### 6.2 Parameters Per Part (Worm and Wheel)

| Parameter | Options | Default | Hint Text |
|-----------|---------|---------|-----------|
| Bore | None / Auto / Custom | Auto | "Auto sizes bore to ~25% of pitch diameter with standard rounding." |
| Custom bore diameter | (if custom) | from recommended | "mm - Must be smaller than root diameter." |
| Anti-rotation | None / DIN 6885 Keyway / DD-Cut | DIN 6885 | "**DIN 6885** - Standard parallel keyway (bores >= 6mm). **DD-Cut** - Double-D flat for small shafts (bores < 6mm)." |
| DD-cut depth | (if DD-cut) | 15% | "% of bore diameter." |

**Smart behaviour (same as today):**
- Anti-rotation options only shown when bore is not "None"
- DIN 6885 disabled when bore < 6mm (outside standard range), auto-selects DD-cut
- Recommended bore shown as reference even when custom is selected

### 6.3 Relief Grooves (Worm Only)

Shown below the worm/wheel bore sections:

| Parameter | Default | Hint Text |
|-----------|---------|-----------|
| Relief grooves | off | "Undercuts at worm thread ends for manufacturing clearance." |
| Groove type | DIN 76 | "**DIN 76** - Standard rectangular undercut. **Full radius** - Semicircular, lower stress concentration." |
| Width / Depth / Radius | auto | "Calculated from axial pitch per DIN 76." |

---

## 7. Right Column: Design Package Output

### 7.1 Validation (Top)

Same severity system as today (error/warning/info), but more prominent:

- **Errors** shown in a red banner at the top. Block export buttons until resolved.
- **Warnings** shown in amber. Allow export but require acknowledgement.
- **Info** shown in blue. Informational, no action needed.

Each message includes:
- The issue (e.g., "Lead angle is 2.3 deg, below 3 deg minimum for practical use")
- A suggestion (e.g., "Increase module or reduce number of starts")

### 7.2 Specification Sheet (Middle)

**Replace the current plain-text `<pre>` block** with a formatted HTML specification
sheet. This is the centrepiece of the output - the document you'd send to a manufacturer.

Structured as a series of compact tables:

```
OVERVIEW
  Ratio           30:1
  Module          2.000 mm
  Centre Distance 38.14 mm
  Hand            Right
  Profile         ZA (straight flanks)

WORM
  Tip Diameter    20.29 mm
  Pitch Diameter  16.29 mm
  Root Diameter   11.29 mm
  Lead            6.283 mm
  Lead Angle      7.0 deg
  Starts          1
  Length          42.5 mm (recommended)

WHEEL
  Tip Diameter    64.00 mm
  Pitch Diameter  60.00 mm
  Root Diameter   55.00 mm
  Teeth           30
  Face Width      12.8 mm (recommended)
  Throated        No

ASSEMBLY
  Pressure Angle  20.0 deg
  Backlash        0.05 mm
  Efficiency      ~75%
  Self-Locking    No

SHAFT INTERFACE
  Worm Bore       5.2 mm + DIN 6885 keyway (2x2 mm)
  Wheel Bore      12.0 mm + DIN 6885 keyway (4x4 mm)
```

For **globoid**, the worm section additionally shows:
- Throat reduction
- Throat curvature radius

For **throated wheels**, the wheel section additionally shows:
- Min OD at throat

This is rendered from Python's calculator output but formatted in HTML/CSS rather than
displayed as monospace text.

### 7.3 Export (Bottom)

| Button | Action |
|--------|--------|
| **Download Design (.json)** | Full design JSON for CLI / archival |
| **Download Spec Sheet (.md)** | Markdown specification for documentation |
| **Copy Share Link** | URL with parameters for collaboration |
| **Open in 3D Generator -->** | Switch to generator tab with design pre-loaded |

The "Open in 3D Generator" button replaces the current manual "Load from Calculator"
workflow. It switches tabs and auto-loads the design.

---

## 8. 3D Generator Tab

### 8.1 Structural Changes

The generator tab gains the generation-specific parameters that were removed from the
calculator:

```
+-- Generation Options ----------+  +-- Console Output ---------------+
| Design: m2.0 r30 cylindrical  |  | Ready to generate...            |
|                                |  |                                  |
| Wheel generation method:       |  |                                  |
|   [Helical (fast) v]          |  |                                  |
|                                |  |                                  |
| [Generate 3D Models]          |  |                                  |
| [Download Package (ZIP)]      |  |                                  |
+--------------------------------+  +----------------------------------+
```

### 8.2 Generation Parameters

These parameters live **only** in the generator tab:

| Parameter | Options | Default | Hint Text | Condition |
|-----------|---------|---------|-----------|-----------|
| Wheel generation method | Helical / Virtual Hobbing | Helical | "**Helical** - Fast, simple geometry. **Virtual Hobbing** - Simulates real hobbing process for accurate tooth throating. Much slower." | Always shown |
| Hobbing precision | Preview (36) / Balanced (72) / High (144) | Balanced | "Higher = more accurate but slower. Preview: 8-15 min, Balanced: 20-40 min, High: 1-2 hours." | Only when virtual hobbing selected |
| Sections per turn | 18 / 36 / 72 | 36 | "Worm thread smoothness. 36 = 10 deg per section, good for most uses." | Always shown (collapsed/advanced) |

### 8.3 Interaction with Throated Wheel Design Flag

When the design specifies `throated_wheel: true`:
- **Helical** generation: creates a throated blank (geometric approximation)
- **Virtual Hobbing** generation: simulates actual hobbing (kinematically accurate)

Both honour the design intent. The method is the user's choice of fidelity.

When `throated_wheel: false`:
- Virtual hobbing option is still available (it always produces throating)
- A note is shown: "Design specifies non-throated wheel. Virtual hobbing will produce
  throated geometry regardless."

### 8.4 Unchanged

Everything else about the generator tab stays the same:
- Design summary display
- Generate button + cancel
- Progress indicators with step tracking
- Console output
- ZIP download (STEP + 3MF + STL + JSON + Markdown)
- JSON input area (advanced, for loading external designs)

---

## 9. File Changes Required

### 9.1 HTML (`web/index.html`)

**Major restructure:**

- Replace single "Calculator" tab with two tabs: "Cylindrical Worm Gear" and
  "Globoid Worm Gear"
- Each tab contains the 3-step form structure
- Move virtual hobbing controls from calculator to generator tab
- Replace `<pre id="results-text">` with structured HTML specification sheet
- Add visual separator between design tabs and generator tab
- Add "Open in 3D Generator" button to export section

**New DOM elements:**
- `#cylindrical-tab`, `#globoid-tab` - Two design tab containers
- `#step-1-core`, `#step-2-advanced`, `#step-3-bore` - Section containers (per tab)
- `#spec-sheet` - Formatted specification output (replaces `#results-text`)
- `#open-generator` - Button to switch to generator with design loaded

**Removed DOM elements:**
- `#worm-type` select (implicit from tab choice)
- `#wheel-generation` select (moved to generator)
- `#hobbing-precision-group` (moved to generator)

### 9.2 JavaScript (`web/app.js`)

**Major changes:**

- Tab switching logic: 3 tabs instead of 2, with cylindrical/globoid both calling
  the same `calculate()` function but with different `worm_type` values
- `calculate()` reads `worm_type` from active tab context, not from a select element
- New `openInGenerator()` function: switches tab and auto-loads design
- Remove virtual hobbing event listeners from calculator section
- Spec sheet rendering: new function to render structured HTML from calculator output

**New functions:**
- `getActiveDesignTab()` - returns `'cylindrical'` or `'globoid'`
- `renderSpecSheet(design, output)` - builds HTML specification table
- `openInGenerator()` - switches to generator tab with current design

### 9.3 Parameter Handler (`web/modules/parameter-handler.js`)

**Changes:**

- `getInputs(mode)` gains a `wormType` parameter (from active tab) instead of
  reading `#worm-type` select
- Remove `wheel_generation` / `hobbing_precision` from collected inputs (moved to
  generator)
- The `manufacturing` section of inputs no longer includes `virtual_hobbing` or
  `hobbing_steps`

**New signature:**
```javascript
export function getInputs(mode, wormType = 'cylindrical')
```

### 9.4 Schema Validator (`web/modules/schema-validator.js`)

**Changes:**

- `validateManufacturingSettings()` no longer validates `virtual_hobbing` or
  `hobbing_steps` (those move to generator-only validation)
- Add validation for the new `wormType` parameter

### 9.5 Generator Worker (`web/generator-worker.js`)

**Changes:**

- `generateGeometry()` now receives `virtualHobbing`, `hobbingSteps`, and
  `sectionsPerTurn` from the generator tab UI rather than from the design JSON
- These parameters override whatever is in the design JSON's manufacturing section

### 9.6 Generator UI (`web/modules/generator-ui.js`)

**Changes:**

- Add UI for generation method selection and hobbing precision
- Wire up show/hide logic for hobbing precision based on method selection
- Read generation parameters from generator tab DOM, not from design JSON

### 9.7 Pyodide Init (`web/modules/pyodide-init.js`)

**No changes expected.** The calculator and generator initialization stay the same.

### 9.8 Bore Calculator (`web/modules/bore-calculator.js`)

**Minor changes:**

- Default anti-rotation changes from `"none"` to `"DIN6885"` for bores >= 6mm
- Otherwise unchanged

### 9.9 CSS (`web/style.css`)

**Additions:**

- Styling for 3-tab layout with visual separator
- Styling for stepped sections within design tabs
- Styling for specification sheet tables
- Styling for side-by-side bore configuration (worm / wheel columns)
- Active tab indicator distinguishes design tabs from generator tab

### 9.10 Python Changes

**`src/wormgear/calculator/js_bridge.py`:**

- `ManufacturingSettings` model: `virtual_hobbing` and `hobbing_steps` become optional
  (generator may or may not pass them; calculator doesn't need them)
- `CalculatorInputs`: remove `wheel_generation` if present (it was never a proper
  field, but ensure clean separation)

**`src/wormgear/calculator/output.py`:**

- `to_summary()`: possibly restructure output to match new spec sheet sections
  (Overview / Worm / Wheel / Assembly / Shaft Interface)
- No functional changes to calculations

**No changes to:**
- `src/wormgear/calculator/core.py` (calculation logic unchanged)
- `src/wormgear/calculator/validation.py` (validation rules unchanged)
- `src/wormgear/io/loaders.py` (Pydantic models unchanged)
- `src/wormgear/enums.py` (enums unchanged)

---

## 10. Migration Notes

### 10.1 Share Links

Current share links encode `mode=envelope&worm-od=20&...`. The new UI needs to handle:

- Existing links with `worm_type=cylindrical` or `worm_type=globoid` route to the
  correct tab
- Links without `worm_type` default to cylindrical tab
- All other parameters remain compatible

### 10.2 JSON Compatibility

The design JSON format does **not change**. A JSON file saved from the old UI loads
correctly in the new UI (and vice versa). The `manufacturing.virtual_hobbing` field
remains in the JSON schema - it's just not set by the calculator anymore. The generator
sets it based on its own UI.

### 10.3 Design JSON Still Contains Manufacturing

The `manufacturing` section of the design JSON keeps fields like `worm_length_mm`,
`wheel_width_mm`, `profile`, `throated_wheel`, `worm_type`. It loses `virtual_hobbing`
and `hobbing_steps` as calculator-set values (the generator may still write them into
the JSON for reproducibility when saving the complete package).

---

## 11. Scope and Phasing

### Phase 1: Tab Structure and Step Flow (This PR)

- [ ] Split into Cylindrical / Globoid / Generator tabs
- [ ] Implement 3-step form layout within design tabs
- [ ] Move virtual hobbing controls to generator tab
- [ ] Change defaults (From Module, backlash 0.05, DIN 6885 keyways)
- [ ] Add inline hint text to all parameters
- [ ] Ensure all existing functionality still works

### Phase 2: Specification Sheet (Follow-up)

- [ ] Replace `<pre>` results with formatted HTML specification table
- [ ] Structured sections: Overview, Worm, Wheel, Assembly, Shaft Interface
- [ ] Validation messages rendered inline with affected sections
- [ ] "Open in 3D Generator" button

### Phase 3: Polish (Follow-up)

- [ ] Responsive layout for mobile (steps stack vertically)
- [ ] Print-friendly specification sheet
- [ ] Share link compatibility with tab routing
- [ ] Help/educational mode with expanded explanations

---

## 12. Open Questions

1. **Envelope mode checkbox ("Treat ODs as maximum")** - this is specific to envelope
   mode and slightly confusing. Should it be a separate mode ("Fit Within Envelope")
   vs the current envelope ("Exact ODs")? Or is the checkbox sufficient?

2. **Bore layout** - side-by-side (worm | wheel) is cleaner but uses more horizontal
   space. Stacked (worm above wheel) is narrower. Which do we prefer?

3. **Globoid throat reduction** - currently in the "Manufacturing Options" section.
   Moving it to Step 1 (Core Design) in the Globoid tab makes sense because it's a
   fundamental geometric parameter for globoid worms. Confirm this placement.

4. **Sections per turn** - currently not exposed in the calculator UI at all (always
   36). In the generator tab, should it be an advanced/hidden option, or exposed
   as a simple quality slider?

5. **Spec sheet rendering** - should the HTML spec sheet be generated from the existing
   Python `to_summary()` / `to_markdown()` output (parsed and rendered), or should
   JavaScript build it directly from the design JSON? The latter is more flexible but
   duplicates formatting logic.

---

## 13. Rejected Alternatives

### 13.1 Single Tab with Worm Type Toggle

Instead of two separate tabs for cylindrical/globoid, use a single "Calculator" tab
with a toggle at the top.

**Rejected because:** The globoid-specific parameters (throat reduction, trim-to-min)
make the form longer and more confusing for the common case (cylindrical). Separate
tabs give each workflow a clean, focused form.

### 13.2 Wizard (Multi-Page) Flow

Instead of collapsed sections, use a true multi-step wizard where each step is a
separate page/view.

**Rejected because:** Engineers want to see all their parameters at once and iterate
quickly. A wizard forces linear navigation. Collapsed `<details>` sections give the
best of both worlds: beginners see a simple form, experts expand everything.

### 13.3 Move All Manufacturing to Generator

Move tooth profile (ZA/ZK/ZI), throating, and worm/wheel dimensions to the generator
tab along with virtual hobbing.

**Rejected because:** Tooth profile and throating are design decisions that appear on
a specification sheet. A manufacturer needs to know "ZA profile, throated wheel" to
quote the job. These belong in the design phase. Only the *3D model generation method*
belongs in the generator.
