# Setting Up OCP.wasm

To complete the web interface, you need the OCP.wasm wheel file. This document explains how to obtain it.

## Option 1: From Your Previous Setup (Recommended)

You mentioned you previously had build123d working in Pyodide. If you can find that setup:

1. Look for `*.whl` files in your previous project
2. Specifically look for files like:
   - `OCP-*.whl`
   - `cadquery_ocp-*.whl`
   - Any file with "ocp" in the name

3. Copy it to this `web/` directory

4. Update `index.html` to load it:
   ```javascript
   await micropip.install('./OCP-7.7.2-cp311-cp311-emscripten_3_1_45_wasm32.whl');
   ```

## Option 2: Download from Yet Another CAD Viewer

The YACV project has pre-built OCP.wasm binaries:

### Quick Download

```bash
# Clone the YACV repository
cd /tmp
git clone --depth 1 https://github.com/yeicor-3d/yet-another-cad-viewer.git

# Find OCP wheel files
find yet-another-cad-viewer -name "*.whl" | grep -i ocp

# Copy to our web directory
cp yet-another-cad-viewer/path/to/ocp-*.whl /home/user/worm-gear-3d/web/
```

### Direct from Releases

1. Visit: https://github.com/yeicor-3d/yet-another-cad-viewer/releases
2. Download the latest release
3. Extract and find OCP wheel file
4. Place in `web/` directory

## Option 3: Use OCP.wasm Directly

The source repository for OCP.wasm:

```bash
# Clone OCP.wasm
git clone https://github.com/yeicor/OCP.wasm.git

# Check releases for pre-built wheels
cd OCP.wasm
ls -la releases/
```

## Option 4: Build from Source (Advanced)

If you need a specific version or want to customize:

### Prerequisites
- Docker (recommended) OR
- Emscripten SDK
- Python 3.11+
- CMake
- Lots of disk space (~20GB)
- Lots of time (2-4 hours compile time)

### Using Docker (Easier)

```bash
# Clone OCP.wasm
git clone https://github.com/yeicor/OCP.wasm.git
cd OCP.wasm

# Build using Docker
docker build -t ocp-wasm .

# Extract wheel file
docker cp ocp-wasm:/output/OCP-*.whl ./
```

### Manual Build

Follow the instructions in the OCP.wasm repository:
https://github.com/yeicor/OCP.wasm/blob/main/README.md

This is complex and not recommended unless you have WebAssembly experience.

## Verifying the Wheel

Once you have the wheel file:

1. **Check file size**: Should be 50-100 MB
   ```bash
   ls -lh web/*.whl
   ```

2. **Check filename**: Should match Pyodide version
   ```
   OCP-7.7.2-cp311-cp311-emscripten_3_1_45_wasm32.whl
             ^^^^^ Python 3.11
   ```

3. **Test loading**:
   ```bash
   cd web
   python3 serve.py
   ```
   Open browser to http://localhost:8000
   Click "Test build123d" button
   Check console for success message

## Integration Checklist

After obtaining the wheel file:

- [ ] Wheel file placed in `web/` directory
- [ ] File size is reasonable (50-100MB)
- [ ] Filename matches Python version in Pyodide
- [ ] Update `index.html` to load the wheel
- [ ] Test in browser
- [ ] Verify OCP imports successfully
- [ ] Verify build123d imports successfully
- [ ] Test simple geometry creation
- [ ] Test wormgear_geometry import
- [ ] Test full geometry generation
- [ ] Test STEP export

## Expected File Structure

```
web/
├── index.html
├── wormgear-pyodide.js
├── serve.py
├── README.md
├── PYODIDE_INTEGRATION.md
├── SETUP_OCP.md (this file)
└── OCP-7.7.2-cp311-cp311-emscripten_3_1_45_wasm32.whl  ← Place here
```

## Troubleshooting

### Wrong Python Version

If the wheel is for Python 3.10 but Pyodide uses 3.11:

- Update Pyodide version in `index.html` to match
- Or find a wheel built for the correct Python version

### CORS Errors

If loading from local file:

```
Access to XMLHttpRequest blocked by CORS policy
```

**Solution**: Use the development server:
```bash
python3 serve.py
```

Don't open `file:///path/to/index.html` directly.

### Out of Memory

If browser crashes or shows memory errors:

- Close other tabs
- Restart browser
- Use desktop Chrome/Firefox (not mobile)
- Increase browser memory limit if possible

### Version Mismatch

If OCP loads but build123d fails:

```
ImportError: OCP version 7.7.0 but build123d requires 7.7.2
```

**Solutions**:
1. Find matching OCP version for your build123d
2. Or pin build123d version to match OCP:
   ```javascript
   await micropip.install('build123d==0.6.0');  // Match OCP 7.7.0
   ```

## Next Steps After Setup

1. Test basic OCP/build123d functionality
2. Test wormgear_geometry loading
3. Generate test geometry
4. Add 3D visualization
5. Deploy to static hosting

## Need Help?

If you're stuck:

1. Check browser console for detailed errors
2. Look at the YACV source code for reference
3. Post issue on GitHub with:
   - Browser version
   - Pyodide version
   - OCP wheel filename
   - Console errors
