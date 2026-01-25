# Maintaining the Web Interface

## When Adding New Python Modules

If you add new Python files to `src/wormgear/`, you **must** update the web build:

### 1. Update `web/app-lazy.js`

Add new files to the `packageFiles` array in `loadWormGearPackage()`:

```javascript
const packageFiles = [
    // ... existing files ...
    { path: 'wormgear/your_module/new_file.py', pyPath: '/home/pyodide/wormgear/your_module/new_file.py' },
];
```

### 2. Update `web/build.sh`

Add new files to the `REQUIRED_FILES` validation array:

```bash
REQUIRED_FILES=(
    # ... existing files ...
    "src/wormgear/your_module/new_file.py"
)
```

### 3. Run Tests

```bash
# Run web build tests
pytest tests/test_web_build.py -v

# Or run all tests
pytest tests/ -v
```

### 4. Manual Test

```bash
# Build and test locally
cd web
./build.sh
python -m http.server 8000

# Open http://localhost:8000
# Try loading the generator tab
```

## Common Issues

### "ModuleNotFoundError" in Browser Console

**Symptom**: Generator tab shows error like:
```
ModuleNotFoundError: No module named 'wormgear.foo.bar'
```

**Cause**: Missing file in `packageFiles` array

**Fix**: Add the missing file to both `app-lazy.js` and `build.sh`

### Build Script Fails Validation

**Symptom**: Build script exits with error:
```
❌ Missing required file: src/wormgear/foo.py
```

**Cause**: File doesn't exist or path is wrong

**Fix**:
1. Check file exists in `src/wormgear/`
2. Check path in `REQUIRED_FILES` array matches actual location

### Tests Failing

**Symptom**: `pytest tests/test_web_build.py` fails

**Fix**: Read the test output - it tells you exactly what's missing:
```
AssertionError: Required file 'wormgear/foo.py' not listed in app-lazy.js packageFiles array
```

## File Checklist

When adding/moving Python files, update these locations:

- [ ] `src/wormgear/` - The actual source files
- [ ] `web/app-lazy.js` - `packageFiles` array
- [ ] `web/build.sh` - `REQUIRED_FILES` array
- [ ] Run `pytest tests/test_web_build.py`
- [ ] Test locally in browser

## Field Name Validation

Two tests ensure JSON field names match Python dataclass parameters:

### `test_json_field_names_match_dataclass_params`
- Validates all example JSON files against WormParams, WheelParams, AssemblyParams
- Catches typos like `throat_pitch_radius_mm` (wrong) vs `throat_curvature_radius_mm` (correct)
- Prevents TypeError when loading designs in browser

### `test_app_lazy_js_field_names_match`
- Checks app-lazy.js doesn't use known incorrect field names
- Specifically looks for deprecated/wrong names

**When adding new fields to dataclasses:**
1. Update `src/wormgear/io/loaders.py` dataclass definitions
2. Update JSON Schema in `src/wormgear/io/schema.py`
3. Update example JSON files if needed
4. Tests will catch any mismatches automatically

## CI/CD

GitHub Actions automatically runs `test-web-build.yml` on PRs that touch:
- `web/**` files
- `src/wormgear/**` files

This catches missing files **before** they break production.

## Why This Matters

The web interface loads Python files individually from the server into Pyodide's virtual filesystem. If **any** file is missing, imports fail and geometry generation doesn't work.

The tests ensure:
1. ✅ All required files are copied during build
2. ✅ `app-lazy.js` lists all files correctly
3. ✅ Build script validation is accurate
4. ✅ No accidental commits of generated files
5. ✅ Pyodide versions are consistent

## Future Improvement

Consider switching to wheel-based deployment (see `web/build-wheel.sh`) for:
- Single file download instead of ~13 HTTP requests
- Better caching
- Faster load times

But current approach works and is easier to debug during development.
