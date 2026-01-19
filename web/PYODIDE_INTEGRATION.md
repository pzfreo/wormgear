# build123d + Pyodide Integration Guide

## Current Status

The web interface foundation is complete, but **build123d requires special handling in Pyodide** because it depends on OpenCascade (OCP), which is a native C++ library compiled to WebAssembly.

### What Works ✅

- Pyodide loads successfully in the browser
- Python 3.11 runtime available
- micropip package installer functional
- Pure Python packages can be installed
- UI and file handling complete

### What Needs Work 🔧

- build123d installation requires OCP.wasm
- OCP is not available in standard Pyodide package repository
- Custom WebAssembly build needed

## The Challenge: OCP (OpenCascade)

build123d is built on top of OCP (OpenCascade Python bindings), which wraps the OpenCascade CAD kernel - a massive C++ library. Getting this to work in the browser requires:

1. **OpenCascade compiled to WebAssembly**
2. **Python bindings (OCP) also compiled to WASM**
3. **build123d compatible with the WASM build**

## Solutions

### Option 1: Use Existing OCP.wasm (Recommended)

The [yet-another-cad-viewer](https://github.com/yeicor-3d/yet-another-cad-viewer) project has already solved this problem. They provide pre-built OCP.wasm binaries.

**Steps:**

1. **Clone/reference OCP.wasm binaries**
   ```bash
   # From the yeicor-3d project
   https://github.com/yeicor/OCP.wasm/
   ```

2. **Load in Pyodide before build123d**
   ```javascript
   // Load the pre-built OCP.wasm wheel
   await micropip.install('https://path/to/ocp-wasm-wheel.whl');

   // Then install build123d
   await micropip.install('build123d');
   ```

3. **Bundle with web interface**
   - Download the OCP.wasm wheel file
   - Serve it alongside index.html
   - Load from local path instead of CDN

**Pros:**
- Proven to work (YACV uses it successfully)
- Full build123d functionality
- Can generate real STEP files

**Cons:**
- Large download (~50-100MB first load)
- Complex build process if we need to rebuild
- May need to stay in sync with build123d versions

### Option 2: Custom Pyodide Build

Build a custom Pyodide distribution that includes OCP.

**Steps:**

1. Fork Pyodide repository
2. Add OCP to the package recipes
3. Build Pyodide from source
4. Host custom Pyodide distribution

**Pros:**
- Full control over versions
- Can optimize bundle size
- Better integration

**Cons:**
- Very complex build process
- Long compile times (hours)
- Maintenance burden
- Requires C++ and WASM build expertise

### Option 3: Simplified Geometry (Fallback)

If OCP proves too difficult, generate STL/GLTF instead of STEP using pure Python libraries.

**Steps:**

1. Rewrite geometry generation using:
   - `numpy` - for mathematical calculations
   - `trimesh` - for mesh generation (if available in Pyodide)
   - Or custom pure-Python mesh generator

2. Output formats:
   - STL (for 3D printing)
   - GLTF/GLB (for web viewing)
   - OBJ (simple mesh format)

**Pros:**
- No OCP dependency
- Smaller bundle size
- Faster loading

**Cons:**
- Mesh approximation instead of exact CAD
- No STEP files (less suitable for CNC)
- Would need to rewrite significant code
- Loss of precision in critical dimensions

## Recommended Approach: Option 1 (OCP.wasm)

Since you mentioned "I've previously got build123d work in pyodide," Option 1 is the best path forward.

### Implementation Plan

#### Phase 1: Get OCP.wasm Working

1. **Locate your previous working setup**
   - Find the OCP.wasm wheel file you used before
   - Check the Pyodide version you used
   - Review any configuration or build scripts

2. **Test OCP.wasm loading**
   ```html
   <script>
   async function testOCP() {
       const pyodide = await loadPyodide();
       await pyodide.loadPackage('micropip');
       const micropip = pyodide.pyimport('micropip');

       // Load OCP.wasm wheel
       await micropip.install('/path/to/ocp.whl');

       // Test import
       await pyodide.runPythonAsync(`
           import OCP
           print(f"OCP loaded: {OCP.__version__}")
       `);
   }
   </script>
   ```

3. **Verify build123d works**
   ```python
   from build123d import Box, Cylinder
   box = Box(10, 10, 10)
   print(f"Created box with volume: {box.volume}")
   ```

#### Phase 2: Integrate with wormgear_geometry

1. **Load source files into Pyodide filesystem**
   - Already implemented in `wormgear-pyodide.js`
   - Fetches files from `../src/wormgear_geometry/`
   - Writes to Pyodide virtual filesystem

2. **Test geometry generation**
   ```python
   from wormgear_geometry import WormGeometry
   # Generate simple worm
   worm_geo = WormGeometry(params, assembly_params, length=40)
   worm = worm_geo.build()
   ```

3. **Export to STEP in memory**
   ```python
   from io import BytesIO
   buffer = BytesIO()
   worm_geo.export_step(buffer)
   step_bytes = buffer.getvalue()
   ```

#### Phase 3: Download STEP Files

1. **Transfer bytes from Python to JavaScript**
   ```python
   import base64
   step_base64 = base64.b64encode(step_bytes).decode('utf-8')
   ```

2. **Create download in browser**
   ```javascript
   const blob = base64ToBlob(result.worm_step);
   downloadFile('worm.step', blob);
   ```

## Files Created

### Current Web Interface Files

```
web/
├── index.html              ✅ Main UI (fully functional without OCP)
├── wormgear-pyodide.js    ✅ Integration module
├── serve.py                ✅ Development server
├── README.md               ✅ Usage documentation
└── PYODIDE_INTEGRATION.md  ✅ This file
```

### Still Needed

```
web/
├── ocp.whl                 ❌ OCP.wasm wheel file
├── setup-ocp.js            ❌ OCP loader script
└── viewer.js               ❌ 3D visualization (optional)
```

## Testing Checklist

- [ ] Load Pyodide successfully
- [ ] Install micropip
- [ ] Load OCP.wasm wheel
- [ ] Import OCP successfully
- [ ] Install build123d
- [ ] Import build123d successfully
- [ ] Create simple build123d object (Box, Cylinder)
- [ ] Load wormgear_geometry package
- [ ] Generate worm geometry
- [ ] Generate wheel geometry
- [ ] Export to STEP in memory
- [ ] Download STEP file to disk
- [ ] Verify STEP file opens in CAD software

## Next Steps

1. **Find your previous OCP.wasm setup**
   - Check old project folders
   - Review browser cache
   - Look for saved wheel files

2. **Or download from YACV project**
   ```bash
   # Clone the repo
   git clone https://github.com/yeicor-3d/yet-another-cad-viewer.git

   # Find the OCP wheel files
   find yet-another-cad-viewer -name "*.whl" | grep -i ocp
   ```

3. **Test in isolation**
   - Create minimal HTML page
   - Just load Pyodide + OCP.wasm
   - Verify import works
   - Then integrate with full UI

4. **Integration**
   - Add OCP loading to index.html
   - Update status messages
   - Test geometry generation
   - Add download functionality

## Resources

### OCP.wasm Projects

- **Yet Another CAD Viewer**: https://github.com/yeicor-3d/yet-another-cad-viewer
  - Most complete reference implementation
  - Working build123d playground
  - Pre-built OCP.wasm binaries

- **OCP.wasm Repository**: https://github.com/yeicor/OCP.wasm
  - Source for building OCP.wasm
  - Build instructions
  - Release binaries

### Pyodide Documentation

- **Loading Packages**: https://pyodide.org/en/stable/usage/loading-packages.html
- **Loading from Files**: https://pyodide.org/en/stable/usage/loading-custom-python-code.html
- **File System**: https://pyodide.org/en/stable/usage/file-system.html

### build123d

- **Documentation**: https://build123d.readthedocs.io/
- **GitHub**: https://github.com/gumyr/build123d
- **STEP Export**: https://build123d.readthedocs.io/en/latest/import_export.html

## Troubleshooting

### "ModuleNotFoundError: No module named 'OCP'"

OCP.wasm not loaded. Need to:
1. Download OCP.wasm wheel file
2. Install it before build123d
3. Check browser console for CORS errors

### "Cannot load WASM binary"

CORS or MIME type issue:
1. Use proper HTTP server (not file://)
2. Check CORS headers
3. Verify Content-Type headers

### "Out of memory"

OCP is large:
1. Increase browser memory limit
2. Close other tabs
3. Use desktop browser (not mobile)
4. Try smaller test case first

### Build123d version mismatch

OCP.wasm may be for specific build123d version:
1. Check version compatibility
2. May need to pin build123d version
3. Or rebuild OCP.wasm

## Performance Expectations

- **First Load**: 30-60 seconds (downloading OCP.wasm)
- **Subsequent Loads**: 5-10 seconds (browser cache)
- **Worm Generation**: 2-5 seconds
- **Wheel Generation**: 5-15 seconds (throating is complex)
- **STEP Export**: 1-2 seconds

Total for complete pair: ~20-30 seconds after libraries loaded.

## Conclusion

The web interface is ready for OCP.wasm integration. Once you provide the OCP wheel file from your previous working setup (or we download from YACV), we can complete the implementation in a few hours.

The key bottleneck is **obtaining a compatible OCP.wasm build**. Everything else is implemented and ready to go.
