# Web Application Refactoring

## Overview

The web application has been refactored from a monolithic 1047-line `app-lazy.js` into a modular architecture with 5 focused modules and a streamlined 395-line main file.

## Modular Architecture

### Module Structure

```
web/
├── modules/
│   ├── bore-calculator.js       (172 lines) - Bore sizing and anti-rotation
│   ├── generator-ui.js          (116 lines) - Generator console and progress
│   ├── parameter-handler.js     (128 lines) - UI input extraction and formatting
│   ├── pyodide-init.js          (177 lines) - Pyodide/worker initialization
│   └── validation-ui.js         ( 31 lines) - Validation message rendering
├── app-lazy.js                  (395 lines) - Main orchestration
└── index.html                   (updated to use type="module")
```

### Size Comparison

| File | Lines | Purpose |
|------|-------|---------|
| **Original** | | |
| app-lazy.js | 1047 | Everything in one file |
| **Refactored** | | |
| bore-calculator.js | 172 | Bore calculation logic |
| generator-ui.js | 116 | Generator UI functions |
| parameter-handler.js | 128 | Input handling |
| pyodide-init.js | 177 | Initialization |
| validation-ui.js | 31 | Validation display |
| app-lazy.js | 395 | Main app (62% reduction!) |
| **Total** | 1019 | All modular code |

## Module Responsibilities

### bore-calculator.js

**Exports:**
- `calculateBoreSize(pitchDiameter, rootDiameter)` - Calculate recommended bore
- `getCalculatedBores()` - Get current bore values
- `updateBoreDisplaysAndDefaults(design)` - Update UI with calculated bores
- `updateAntiRotationOptions()` - Update anti-rotation dropdowns
- `setupBoreEventListeners()` - Setup bore control event listeners

**Responsibilities:**
- Auto-calculate bore sizes (~25% of pitch diameter)
- Manage bore type selection (none/auto/custom)
- Handle anti-rotation method selection (DIN 6885 / DD-cut)
- Enable/disable options based on bore size (DIN 6885 requires ≥6mm)

### generator-ui.js

**Exports:**
- `appendToConsole(message)` - Add message to console output
- `updateDesignSummary(design)` - Update design summary display
- `handleProgress(message, percent)` - Handle progress updates
- `hideProgressIndicator()` - Hide progress bar
- `handleGenerateComplete(data)` - Handle generation completion

**Responsibilities:**
- Console output management
- Progress indicator updates
- Design summary display
- Download button management

### parameter-handler.js

**Exports:**
- `getDesignFunction(mode)` - Get Python function name for mode
- `getInputs(mode)` - Extract all parameters from UI
- `formatArgs(calculatorParams)` - Format parameters for Python call

**Responsibilities:**
- Extract calculator parameters from UI
- Extract manufacturing parameters
- Extract bore/keyway parameters
- Format for Python function calls (enum conversion, etc.)

### pyodide-init.js

**Exports:**
- `getCalculatorPyodide()` - Get calculator Pyodide instance
- `getGeneratorWorker()` - Get generator worker
- `initCalculator(onComplete)` - Initialize calculator Pyodide
- `initGenerator(showModal, setupMessageHandler)` - Initialize generator worker

**Responsibilities:**
- Load Pyodide runtime
- Load Python files into Pyodide filesystem
- Import Python modules
- Create and initialize Web Worker
- Handle initialization errors with helpful messages

### validation-ui.js

**Exports:**
- `updateValidationUI(valid, messages)` - Update validation display

**Responsibilities:**
- Display validation status (valid/error)
- Render validation messages with severity styling
- Show suggestions for issues

## Benefits of Refactoring

1. **Maintainability**: Each module has a single, clear responsibility
2. **Testability**: Modules can be tested independently
3. **Reusability**: Modules can be reused in other contexts
4. **Readability**: Main file reduced from 1047 to 395 lines (62% reduction)
5. **Modularity**: ES6 modules with explicit imports/exports
6. **Separation of Concerns**: UI, logic, and initialization clearly separated

## Migration Notes

### HTML Changes

```html
<!-- Old -->
<script src="app-lazy.js"></script>

<!-- New -->
<script type="module" src="app-lazy.js"></script>
```

The `type="module"` attribute enables ES6 module imports.

### Global Functions

Functions exposed to HTML onclick handlers are explicitly added to `window`:

```javascript
window.calculate = calculate;
window.copyJSON = copyJSON;
// ... etc
```

### Module Loading

Browser ES6 modules use relative paths:

```javascript
import { calculateBoreSize } from './modules/bore-calculator.js';
```

Note the `.js` extension is **required** for browser modules (unlike Node.js).

## Future Enhancements

Potential further refactoring:

1. **State Management Module**: Centralize currentDesign and currentValidation
2. **URL Handler Module**: Extract URL parameter parsing logic
3. **Event Handlers Module**: Separate event listener setup
4. **Constants Module**: Extract magic numbers and configuration
5. **Utilities Module**: Common helpers (safeParseFloat, etc.)

## Backward Compatibility

The original `app-lazy.js` is backed up as `app-lazy.js.bak` for reference.

## Testing Checklist

- [ ] Calculator tab loads and calculates
- [ ] Bore displays show recommended values
- [ ] Anti-rotation options update correctly
- [ ] Validation messages display properly
- [ ] JSON export works
- [ ] Markdown export works
- [ ] Generator tab loads
- [ ] Load from calculator works
- [ ] File upload works
- [ ] Geometry generation works
- [ ] Background generator loading works
