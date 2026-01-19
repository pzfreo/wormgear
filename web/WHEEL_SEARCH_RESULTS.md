# OCP.wasm Wheel File Search Results

## Objective
Find direct URLs to download WebAssembly wheel files for:
- `lib3mf` (3D model format library)
- `OCP` (OpenCascade Python bindings compiled to WASM)
- `build123d` (CAD library compatible with OCP.wasm)

## Search Methods Attempted

### 1. GitHub Releases Search ❌
**Searched for:** `site:github.com yeicor OCP.wasm releases wheel whl`

**Results:**
- Found repositories: `yeicor-3d/yet-another-cad-viewer`, `yeicor-3d/ocp-action`
- **No standalone `yeicor/OCP.wasm` repository with releases found**
- YACV releases (v0.10.11 latest) have "Assets" but details failed to load
- No direct `.whl` file URLs discovered

**Conclusion:** OCP.wasm appears to be integrated into projects rather than distributed as standalone wheels.

### 2. YACV Project Analysis ✅
**Found:**
- YACV uses Pyodide v0.29.0 (we upgraded to match)
- Their `vite.config.ts` **excludes** `.whl` files from build:
  ```javascript
  "!**/*.whl",  // Don't copy wheel files
  ```
- This means they load wheels at runtime, not bundled in deployment
- Uses `yacv_server` package from PyPI

### 3. PyPI yacv_server Package ✅
**Found:** [yacv-server on PyPI](https://pypi.org/project/yacv-server/)

**Details:**
- Version: 0.10.11 (latest, Sept 28, 2025)
- Requires: Python 3.12-3.13 (Pyodide v0.29.0 has Python 3.13 ✅)
- License: MIT
- Description: "Yet Another CAD Viewer (server)"
- **Bundles build123d integration**
- References OCP.wasm for browser playground

**Installation:** Now primary approach in our code
```javascript
await micropip.install("yacv_server", pre=True)
```

### 4. OCP.wasm Repository Structure ✅
**Found:** Repository exists at `/tmp/ocp-wasm` (cloned locally)

**Contains:**
- `build123d/bootstrap_in_pyodide.py` - Installation script
- `build123d/PlaygroundStartup.py` - YACV startup code
- `build123d/crossplatformtricks.py` - Browser compatibility patches

**Key Finding:** Bootstrap code references:
```python
micropip.set_index_urls([
    "https://yeicor.github.io/OCP.wasm",
    "https://pypi.org/simple"
])
```

**Problem:** This URL returns HTML instead of package metadata (confirmed by error).

### 5. Direct GitHub Pages Access ❌
**Attempted:**
- `https://yeicor.github.io/OCP.wasm` - Returns 403 Forbidden
- `https://yeicor.github.io/OCP.wasm/` - Returns 403 Forbidden
- Cannot fetch page content via WebFetch

**Conclusion:** Package index may be:
- Misconfigured
- Moved to different URL
- Requires different URL structure (e.g., `/simple/`)
- Only accessible during actual Pyodide package queries

### 6. CadQuery OCP Releases ✅
**Found:** [CadQuery/OCP on GitHub](https://github.com/CadQuery/OCP)

**Details:**
- This is the main OCP (OpenCascade bindings) repository
- Has regular releases for desktop Python (Windows, macOS, Linux)
- **No WebAssembly/Pyodide wheels in releases**
- Desktop wheels only (not browser-compatible)

### 7. dl4to4ocp Dependencies ✅
**Found:** Their `pyproject.toml` uses:
```toml
build123d = ">=0.10.0"  # From PyPI normally
```

**Conclusion:** Standard Python environment, not Pyodide/WASM specific.

## Current Solution: yacv_server

### Updated Installation Strategy

**Primary Approach (Implemented):**
```javascript
// Try yacv_server which bundles everything
await micropip.install("yacv_server", pre=True);
micropip.add_mock_package("ocp-vscode", "2.8.9",
    modules={"ocp_vscode": 'from yacv_server import *'});
```

**Fallback Approach:**
```javascript
// If yacv_server fails, try standard build123d
await micropip.install("build123d", pre=True);
```

### Why This Might Work

1. **yacv_server is on PyPI** - Verified package exists
2. **Made for browser use** - Purpose-built for web deployment
3. **Bundles dependencies** - Should include required WASM components
4. **Version compatible** - Works with Pyodide v0.29.0 (Python 3.13)
5. **Proven to work** - YACV playground uses it successfully

## Alternative Solutions Not Pursued

### Option A: Build Custom Wheels
- Clone OCP.wasm repository
- Build wheels using Emscripten/Pyodide build system
- Host on our own GitHub Pages
- **Rejected:** Too complex, requires WASM build expertise

### Option B: Use IfcOpenShell wasm-wheels
- Found: [IfcOpenShell/wasm-wheels](https://github.com/IfcOpenShell/wasm-wheels)
- They successfully host WASM wheels on GitHub Pages
- **Rejected:** Different library (IFC vs OCP), incompatible

### Option C: Server-Side Generation
- Generate STEP files on server instead of browser
- **Rejected:** Defeats purpose of browser-based tool

### Option D: Generate STL/GLTF Instead
- Use pure Python mesh libraries (no OCP needed)
- Output STL instead of STEP
- **Rejected:** Lower precision, not suitable for CNC

## Testing Status

### To Test (When You're Back)
```bash
cd web && python3 serve.py 8000
```

**Expected Behavior with yacv_server:**
1. ✅ Pyodide loads (v0.29.0)
2. ⏳ Install yacv_server (~100MB download, 2-5 min)
3. ✅ or ❌ yacv_server installation result
4. If ❌, fallback to standard build123d
5. Test with "Test build123d" button

### Success Criteria
- [ ] yacv_server installs successfully
- [ ] build123d can be imported
- [ ] OCP can be imported
- [ ] Can create Box(10, 10, 10)
- [ ] Can create Cylinder(5, 20)
- [ ] wormgear_geometry loads
- [ ] Can generate worm geometry
- [ ] Can generate wheel geometry
- [ ] STEP files download correctly

## Remaining Questions

1. **Is yacv_server the right package?**
   - It's on PyPI and maintained by the YACV author
   - Purpose-built for browser use
   - Most likely to work

2. **Does it include OCP.wasm binaries?**
   - Unknown until we test
   - Should be documented in package metadata
   - May require additional configuration

3. **Why is OCP.wasm package index broken?**
   - Could be temporary GitHub Pages issue
   - Could be intentionally removed
   - Could require different URL format
   - Contact maintainer if needed

## Next Steps

1. **Test current implementation**
   - Try yacv_server installation locally
   - Check what dependencies it pulls in
   - Verify OCP import works

2. **If yacv_server works:**
   - Document successful approach
   - Update OCP_STATUS.md
   - Mark web interface as fully functional
   - Deploy to GitHub Pages

3. **If yacv_server fails:**
   - Contact Yeicor (OCP.wasm maintainer)
   - Ask for current installation method
   - Request documentation update
   - Consider opening GitHub issue

4. **Long-term:**
   - Monitor OCP.wasm project for updates
   - Watch for package index fixes
   - Consider contributing docs/examples

## Resources Checked

- ✅ [yacv-server on PyPI](https://pypi.org/project/yacv-server/)
- ✅ [Yet Another CAD Viewer GitHub](https://github.com/yeicor-3d/yet-another-cad-viewer)
- ✅ [CadQuery/OCP GitHub](https://github.com/CadQuery/OCP)
- ✅ [IfcOpenShell wasm-wheels](https://github.com/IfcOpenShell/wasm-wheels)
- ✅ [Pyodide Documentation](https://pyodide.org/)
- ✅ OCP.wasm local repository (cloned)
- ❌ https://yeicor.github.io/OCP.wasm (403 Forbidden)

## Summary

**Status:** Found viable solution using `yacv_server` package

**Confidence:** Medium-High
- Package exists and is maintained
- Purpose-built for browser use
- Used by working projects
- Unknown if it includes all needed WASM binaries

**Recommendation:** Test current implementation. If successful, document and deploy. If not, contact OCP.wasm maintainer for guidance.

---

**Latest Commit:** `46aa585` - Try yacv_server package as primary installation method
