# Web Interface - Current Status

## Status: WORKING - Jojain's Approach Verified

**Last Updated:** January 24, 2026
**Status:** OCP.wasm installation works using Jojain's method
**Branch:** `claude/wasm-hobbing-feasibility-8zHg9`

## Working Installation Method

After extensive investigation, the following approach works for loading build123d in Pyodide:

```python
import micropip

# Step 1: Set package index URLs
micropip.set_index_urls([
    "https://yeicor.github.io/OCP.wasm",
    "https://pypi.org/simple"
])

# Step 2: Install lib3mf from OCP.wasm index
await micropip.install("lib3mf")

# Step 3: Install ssl
await micropip.install("ssl")

# Step 4: Install ocp_vscode from Jojain's fork (direct URL)
await micropip.install(
    "https://raw.githubusercontent.com/Jojain/vscode-ocp-cad-viewer/no_pyperclip/ocp_vscode-2.9.0-py3-none-any.whl"
)

# Step 5: Add compatibility mock for older build123d versions
micropip.add_mock_package(
    "py-lib3mf",
    "2.4.1",
    modules={"py_lib3mf": 'from lib3mf import *'}
)

# Step 6: Install build123d and sqlite3 from PyPI
await micropip.install(["build123d", "sqlite3"])
```

**Credit:** [Jojain's build123d-sandbox](https://github.com/Jojain/build123d-sandbox)

## WASM Performance Characteristics

### Estimated Timings (Browser vs Native)

| Feature | Native Python | Browser WASM | Slowdown |
|---------|--------------|--------------|----------|
| Standard worm | <1 sec | 2-5 sec | ~3-5x |
| Standard wheel | <1 sec | 2-5 sec | ~3-5x |
| Globoid worm | 2-5 sec | 10-25 sec | ~5x |
| Virtual hobbing (36 steps) | 15-30 sec | 1-3 min | ~5-6x |
| Virtual hobbing (72 steps) | 30-60 sec | 3-6 min | ~5-6x |
| Virtual hobbing (144 steps) | 1-2 min | 6-12 min | ~5-6x |

### Recommended Step Presets for Browser

| Preset | Steps | Browser Time | Use Case |
|--------|-------|--------------|----------|
| **Preview** | 36 | 1-3 min | Quick iteration, testing parameters |
| **Balanced** | 72 | 3-6 min | Good quality for most uses |
| **High Quality** | 144 | 6-12 min | Final output, not recommended in browser |

### Memory Considerations

- Typical geometry: 100-500 MB during construction
- Pyodide heap limit: ~2 GB (configurable)
- Virtual hobbing with 360+ steps may approach memory limits

## What Works

### Infrastructure (100% Complete)
- Beautiful responsive web UI with gradient styling
- Drag-drop and paste JSON file loading
- Parameter controls (worm length, wheel width, wheel type)
- Sample design loading with dual-path support
- Pyodide v0.29.0 integration (latest stable)
- Console output with color-coded logging
- Error handling and Python traceback display
- Progress callbacks for long operations
- GitHub Pages deployment workflow
- Netlify configuration

### Geometry Generation
- Standard cylindrical worms
- Standard helical wheels
- Throated wheels
- Globoid worms (with progress reporting)
- Virtual hobbing (with progress reporting and step presets)
- Bore and keyway features

## Browser Performance Test

A performance test is available at `web/performance-test.html` to measure actual WASM timings for your hardware.

Run the test to get accurate estimates for:
- Package loading time
- Standard geometry generation
- Globoid geometry generation
- Virtual hobbing at various step counts

## Recommendations

### For Quick Previews
Use the browser interface with "Preview" preset (36 steps). Acceptable quality with 1-3 minute generation time.

### For Production Quality
Use the Python CLI for best results:
```bash
wormgear-geometry design.json --virtual-hobbing --hobbing-steps 144
```

### For Globoid Worms
Browser is viable (10-25 seconds). Use Python for faster iteration.

## Credits

- **Jojain** - For the working OCP.wasm installation method via [build123d-sandbox](https://github.com/Jojain/build123d-sandbox)
- **Yeicor** - For [OCP.wasm](https://github.com/yeicor/OCP.wasm) project
- **gumyr** - For [build123d](https://github.com/gumyr/build123d)
