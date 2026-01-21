# Worm Gear Geometry Generator

**Status: Phase 2 in progress - bore and keyway features complete**

Python library for generating CNC-ready STEP files from worm gear parameters using build123d.

## Overview

This is **Tool 2** in the worm gear design system. It takes validated parameters from the calculator (Tool 1) and produces exact 3D CAD models for CNC manufacturing.

**Calculator (Tool 1)**: https://github.com/pzfreo/wormgearcalc
**Web Calculator**: https://pzfreo.github.io/wormgearcalc/

## Workflow

### Option 1: Python Library (Full Features)

```
1. Design in calculator
   https://pzfreo.github.io/wormgearcalc/
   ↓
2. Export JSON parameters
   ↓
3. Generate geometry (this tool)
   python generate_pair.py design.json
   ↓
4. Get STEP files for CNC
   worm_m2_z1.step
   wheel_m2_z30.step
   assembly.step
```

### Option 2: Web Interface (Browser-Based) 🆕

```
1. Design in calculator
   https://pzfreo.github.io/wormgearcalc/
   ↓
2. Open web interface
   https://your-site.com/worm-gear-3d-web/
   ↓
3. Upload/paste JSON
   ↓
4. Generate in browser
   (No installation needed!)
   ↓
5. Download STEP files
```

See [web/README.md](web/README.md) for web interface documentation.

## Target Manufacturing

- **Worm**: 4-axis lathe with live tooling, or 5-axis mill
- **Wheel**: 5-axis mill (true form), or indexed 4-axis with ball-nose finishing

Geometry is exact and watertight - no approximations, no relying on manufacturing process to "fix" the model.

## Features

### Phase 1: Basic Geometry ✓ Complete
- [x] JSON input from wormgearcalc
- [x] Worm thread generation (helical sweep with trapezoidal profile)
- [x] Wheel generation with two options:
  - **Helical** (default): Pure helical gear teeth with flat root
  - **Hobbed** (`--hobbed`): Throated teeth matching worm curvature for better contact
- [x] STEP export
- [x] Python API
- [x] Command-line interface
- [x] OCP viewer support (VS Code / Jupyter)
- [x] Multi-start worm support
- [x] Profile shift support
- [x] Backlash handling

### Phase 2: Features (In Progress)
- [x] Bore with auto-calculation and custom diameters
- [x] Keyways (ISO 6885 / DIN 6885 standard sizes)
- [x] Small gear support (bores down to 2mm, below DIN 6885 range)
- [x] Thin rim warnings for structural integrity
- [ ] Set screw holes
- [ ] Hub options (flush/extended/flanged)

### Phase 3: Advanced (Future)
- [ ] Envelope calculation for wheel (mathematical accuracy)
- [ ] Assembly positioning
- [ ] Manufacturing specs output (markdown)

## Web Interface 🆕 (Experimental)

Browser-based prototype using Pyodide (Python in WebAssembly):

- **No installation required** - Run Python + build123d in your browser
- **Drag-drop JSON files** from the calculator
- **Generate STEP files** client-side (no server needed)
- **3D preview** (coming soon)

**Quick Start:**
```bash
cd web
python3 -m http.server 8000
# Open http://localhost:8000
```

**Status:** 🚧 **Experimental prototype** - Core generation works, but UI/UX improvements needed before production deployment.

**Current capabilities:**
- ✅ Pyodide + build123d + OCP.wasm integration
- ✅ STEP file generation and download
- 🚧 3D visualization (in progress)
- 🚧 Progress indicators (in progress)

**Try the prototype:**
```bash
cd web && python3 -m http.server 8000
# Open http://localhost:8000
```

See [web/README.md](web/README.md) for technical details. A fully integrated web tool with enhanced UI is planned (see [docs/WEB_TOOL_SPEC_V2.md](docs/WEB_TOOL_SPEC_V2.md)).

## Installation

### Requirements

- **Python 3.9+** (3.10 or 3.11 recommended)
- **build123d >= 0.5.0** - Modern Python CAD library
- **OCP** (OpenCascade bindings) - Installed automatically with build123d

### Install

```bash
pip install build123d
pip install -e .

# Optional: For visualization in VS Code
pip install ocp-vscode
```

**Note:** build123d has platform-specific builds. If you encounter installation issues, see the [build123d installation guide](https://build123d.readthedocs.io/en/latest/installation.html).

## Usage

### Command Line

```bash
# Generate both worm and wheel (with auto-calculated bores and keyways by default)
wormgear-geometry design.json

# Generate solid parts without bores
wormgear-geometry design.json --no-bore

# Custom bore sizes (keyways auto-sized to match)
wormgear-geometry design.json --worm-bore 8 --wheel-bore 15

# Bores but no keyways
wormgear-geometry design.json --no-keyway

# Specify output directory
wormgear-geometry design.json -o output/

# Custom dimensions
wormgear-geometry design.json --worm-length 50 --wheel-width 12

# Generate only worm or wheel
wormgear-geometry design.json --worm-only
wormgear-geometry design.json --wheel-only

# Generate hobbed wheel with throated teeth (better worm contact)
wormgear-geometry design.json --hobbed

# View in OCP viewer without saving files
wormgear-geometry design.json --view --no-save

# View with mesh alignment (rotate wheel for visual mesh)
wormgear-geometry design.json --view --mesh-aligned
```

### Python API

```python
from wormgear_geometry import load_design_json, WormGeometry, WheelGeometry
from wormgear_geometry.features import BoreFeature, KeywayFeature

# Load parameters from calculator
design = load_design_json("design.json")

# Build and export worm with bore and keyway
worm_geo = WormGeometry(
    params=design.worm,
    assembly_params=design.assembly,
    length=40,  # mm
    bore=BoreFeature(diameter=8.0),  # Optional
    keyway=KeywayFeature()  # Optional: DIN 6885 auto-sized
)
worm_geo.export_step("worm.step")

# Build and export wheel (helical - default) with features
wheel_geo = WheelGeometry(
    params=design.wheel,
    worm_params=design.worm,
    assembly_params=design.assembly,
    bore=BoreFeature(diameter=12.0),
    keyway=KeywayFeature()
)
wheel_geo.export_step("wheel.step")

# Build and export hobbed wheel (throated for better contact)
wheel_geo_hobbed = WheelGeometry(
    params=design.wheel,
    worm_params=design.worm,
    assembly_params=design.assembly,
    throated=True  # Enable throating
)
wheel_geo_hobbed.export_step("wheel_hobbed.step")
```

### Visualization (OCP Viewer)

```python
# Display in VS Code with OCP CAD Viewer extension
worm_geo.show()  # Opens worm in viewer
wheel_geo.show()  # Opens wheel in viewer

# Or use the viewer script
python examples/view_design.py design.json
```

See `examples/` directory for more usage patterns.

## Documentation

- **CLAUDE.md** - Context for Claude Code (AI assistant)
- **docs/GEOMETRY.md** - Full technical specification
- **docs/ENGINEERING_CONTEXT.md** - Standards and formulas

## Troubleshooting

### Installation Issues

**Problem:** `pip install build123d` fails or imports don't work

**Solutions:**
- Ensure Python 3.9+ is installed: `python --version`
- Try upgrading pip: `pip install --upgrade pip`
- Check platform-specific instructions: [build123d installation guide](https://build123d.readthedocs.io/en/latest/installation.html)
- On Windows, you may need Visual C++ build tools

### Generation Errors

**Problem:** "Bore diameter too large" or thin rim warnings

**Solutions:**
- Use `--no-bore` to generate solid parts
- Specify smaller custom bore: `--worm-bore 4 --wheel-bore 6`
- Note: Auto-calculated bores leave ≥1mm rim thickness. Thin rims (<1.5mm) generate warnings but still work.

**Problem:** "Bore outside DIN 6885 range" when using keyways

**Solutions:**
- For bores <6mm or >95mm, keyways cannot be auto-sized from DIN 6885
- Either use `--no-keyway` or upgrade to custom keyway dimensions (Python API)
- Small gears (<6mm bore) are typically used without keyways

**Problem:** STEP file won't import to CAD/CAM software

**Solutions:**
- Verify the STEP file is not empty (should be >100KB for typical gears)
- Try a different CAD program (FreeCAD is free and handles most STEP files)
- Check for generation errors in console output
- Reduce geometry complexity: use `--no-bore --no-keyway` to test

### Visualization Issues

**Problem:** OCP viewer not working in VS Code

**Solutions:**
- Install the VS Code extension: "OCP CAD Viewer" from the marketplace
- Install Python package: `pip install ocp-vscode`
- Restart VS Code after installation
- Alternative: Use `--no-view` and open STEP files in FreeCAD or other CAD software

**Problem:** `--view` option shows nothing or crashes

**Solutions:**
- OCP viewer requires significant memory. Close other applications.
- Try viewing worm and wheel separately: `--worm-only --view` or `--wheel-only --view`
- Use external CAD software instead

### Parameter Issues

**Problem:** Generated gear dimensions don't match expectations

**Solutions:**
- Verify the input JSON is from the calculator (not hand-edited)
- Check that worm length and wheel width are appropriate for your application
- Default wheel width is auto-calculated. Override with `--wheel-width` if needed
- Use `--hobbed` flag if you want throated wheel teeth instead of helical

### Getting Help

If you encounter issues not covered here:
1. Check the [GitHub Issues](https://github.com/pzfreo/worm-gear-3d/issues) for similar problems
2. Review the detailed technical docs in [docs/GEOMETRY.md](docs/GEOMETRY.md)
3. For calculator-related issues, see [wormgearcalc](https://github.com/pzfreo/wormgearcalc)

## Dependencies

- **build123d** - Modern Python CAD library
- **OCP** - OpenCascade bindings (via build123d)

## Background

Created for custom worm gear design in luthier (violin making) applications, where standard gears often don't fit unusual envelope constraints. The calculator determines if a design is feasible; this tool makes it manufacturable.

## Author

Paul Fremantle (pzfreo)
Luthier and hobby programmer

## License

MIT (to be added)
