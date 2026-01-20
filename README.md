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

## Web Interface 🆕

Browser-based version using Pyodide (Python in WebAssembly):

- **No installation required** - Run Python + build123d in your browser
- **Drag-drop JSON files** from the calculator
- **Generate STEP files** client-side (no server needed)
- **3D preview** (coming soon)

**Quick Start:**
```bash
cd web
python3 serve.py 8000
# Open http://localhost:8000
```

**Status:** ✅ Fully functional with OCP.wasm integration - ready to deploy!

**Try it now:**
```bash
cd web && python3 serve.py 8000
# Open http://localhost:8000
```

**Deploy to GitHub Pages:**
- Push to main branch
- Enable GitHub Pages in Settings
- Access at `https://your-username.github.io/worm-gear-3d/`

See [web/README.md](web/README.md) for usage and [web/DEPLOYMENT.md](web/DEPLOYMENT.md) for deployment to GitHub Pages, Netlify, Vercel, etc.

## Installation

```bash
pip install build123d
pip install -e .

# Optional: For visualization in VS Code
pip install ocp-vscode
```

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
