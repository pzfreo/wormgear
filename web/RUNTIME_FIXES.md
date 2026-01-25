# Runtime Error Fixes

## Issue: TypeError on Page Load

### Error Message
```
app-lazy.js:347 Uncaught TypeError: Cannot read properties of null (reading 'addEventListener')
    at HTMLDocument.<anonymous> (app-lazy.js:347:41)
```

### Root Cause

The refactored code was trying to add an event listener to a non-existent `calculate` button:

```javascript
document.getElementById('calculate').addEventListener('click', calculate);
```

However, the application **does not have an explicit calculate button**. Instead, calculations are triggered automatically whenever any input changes.

### Fixes Applied (Commit d52c12b)

**1. Removed non-existent button listener**
```diff
- document.getElementById('calculate').addEventListener('click', calculate);
+ // No explicit calculate button - auto-recalculates on input change
```

**2. Initialize calculator on page load**

The calculator tab is active by default in the HTML, so it must be initialized immediately:

```javascript
// Calculator tab is active by default, so initialize it
initCalculatorTab();
```

Previously, it only initialized when the tab was clicked, which meant:
- No Pyodide loaded on page load
- No auto-recalculation working
- Stale UI state

### How Calculator Works

**Auto-recalculation on input changes:**

```javascript
// Auto-recalculate on input changes
const inputs = document.querySelectorAll('input, select');
inputs.forEach(input => {
    input.addEventListener('change', () => {
        if (getCalculatorPyodide()) calculate();
    });
});
```

When any input or select element changes:
1. Check if Pyodide is loaded (`getCalculatorPyodide()`)
2. If loaded, automatically call `calculate()`
3. Results update in real-time

**No manual calculate button needed** - the UI is reactive.

### Testing Verification

After these fixes, the application should:
- ✅ Load without console errors
- ✅ Initialize Pyodide on page load
- ✅ Show "Waiting for calculation..." initially
- ✅ Auto-calculate when any input changes
- ✅ Display validation messages
- ✅ Enable export buttons after calculation

### Related Files

- `web/app-lazy.js` - Main application file
- `web/modules/pyodide-init.js` - Pyodide initialization module
- `web/index.html` - HTML structure (calculator tab active by default)

### Previous Fixes

This is the third iteration of runtime error fixes:

1. **ff47dab**: Fixed button ID mismatches (generate-worm-btn, etc.)
2. **4f9064c**: Added missing event listeners
3. **d52c12b**: Removed non-existent calculate button, added init on load

All runtime errors should now be resolved.
