# Wormgear - Complete Worm Gear Design System

**Version:** 1.0.0-alpha
**Status:** Unified package - calculator + geometry in one

Complete worm gear design system from engineering calculations to CNC-ready STEP files, supporting both traditional CNC manufacturing and 3D printing.

## Overview

Wormgear is a unified Python package combining:
- **Engineering calculations** (DIN 3975/DIN 3996 standards)
- **3D geometry generation** (exact, watertight solids)
- **Web calculator** (browser-based design tool)
- **CLI tools** (batch processing and automation)

**Design → Calculate → Validate → Generate → Manufacture**

## Quick Start

### Web Interface (No Installation Required)

**🌐 Live at:** https://wormgear.studio

Design your worm gear pair in the browser:
- Calculate parameters from engineering constraints
- Real-time validation with DIN 3975/DIN 3996
- Export JSON for geometry generation
- No installation required!

### Installation (For Geometry Generation)

```bash
pip install build123d
pip install -e .

# Optional: For visualization in VS Code
pip install ocp-vscode
```

### Local Web Calculator (Optional)

```bash
cd web
python3 -m http.server 8000
# Open http://localhost:8000
```

Or use the live version at https://wormgear.studio

### Command Line Geometry Generation

```bash
# Generate both worm and wheel with auto-sized bores and keyways
wormgear-geometry design.json

# For 3D printing: use ZK profile (convex flanks)
wormgear-geometry design.json --profile ZK

# For CNC machining: use ZA profile (straight flanks, default)
wormgear-geometry design.json --profile ZA

# Globoid worm (hourglass shape for better contact)
wormgear-geometry design.json --globoid
```

### Python API

```python
from wormgear.calculator import calculate_design_from_module, validate_design
from wormgear.core import WormGeometry, BoreFeature, KeywayFeature
from wormgear.io import save_design_json

# Calculate parameters
design = calculate_design_from_module(module=2.0, ratio=30)
validation = validate_design(design)

if validation.valid:
    # Save design
    save_design_json(design, "design.json")

    # Generate 3D models
    worm = WormGeometry(
        params=design.worm,
        assembly_params=design.assembly,
        length=40.0,
        bore=BoreFeature(diameter=8.0),
        keyway=KeywayFeature()
    )
    worm.build().export_step("worm.step")
```

## Architecture

The package uses a 4-layer architecture:

```
┌─────────────────────────────────────────────────────────────┐
│                     wormgear Package                         │
│                                                              │
│  Layer 1: Core (Geometry) - WormGeometry, WheelGeometry    │
│  Layer 2a: Calculator - design_from_module, validate       │
│  Layer 2b: IO - JSON Schema v1.0, load/save functions      │
│  Layer 3: CLI - wormgear-geometry command                  │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    Web Calculator                            │
│  Runs in browser using Pyodide (Python in WASM)            │
│  Same calculation code, exports JSON Schema v1.0           │
└─────────────────────────────────────────────────────────────┘
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed architecture documentation.

## Manufacturing Support

### CNC Machining (ZA Profile - Default)

**Target Methods:**
- **Worm**: 4-axis lathe with live tooling, or 5-axis mill
- **Wheel**: 5-axis mill (true form), or indexed 4-axis with ball-nose finishing

**Tooth Profile:** Straight trapezoidal flanks (ZA per DIN 3975)

**Features:**
- Exact geometry - no approximations
- Watertight solids for reliable CAM toolpath generation
- Bores and keyways (ISO 6885 / DIN 6885)
- Set screws and hubs (coming soon)

**Example:**
```bash
wormgear-geometry design.json --profile ZA
```

### 3D Printing (ZK Profile Recommended)

**Target Methods:**
- FDM (PLA, PETG, Nylon)
- SLA/DLP resin printing
- SLS (nylon powder)

**Tooth Profile:** Slightly convex flanks (ZK per DIN 3975)

**Benefits:**
- Reduces stress concentrations
- Better layer adhesion in FDM
- Smoother surfaces for resin printing

**Example:**
```bash
wormgear-geometry design.json --profile ZK
```

**3D Printing Tips:**
- Use high infill (80-100%) for strength
- Orient parts to minimize support material
- Consider nylon or PETG for better wear resistance
- Add lubrication for smoother operation

## Features

### Phase 1: Basic Geometry ✓ Complete
- [x] Engineering calculations (DIN 3975/DIN 3996)
- [x] Validation with errors/warnings
- [x] JSON Schema v1.0 (calculator ↔ geometry)
- [x] Worm thread generation (helical sweep)
- [x] Wheel generation (helical or virtual hobbing)
- [x] Globoid worm support (hourglass shape)
- [x] STEP export
- [x] Python API and CLI
- [x] OCP viewer support
- [x] Multi-start worm support
- [x] Profile shift support
- [x] Backlash handling
- [x] Web calculator UI

### Phase 2: Features ✓ Complete
- [x] Bore with auto-calculation and custom diameters
- [x] Keyways (ISO 6885 / DIN 6885 standard sizes)
- [x] Small gear support (bores down to 2mm)
- [x] Thin rim warnings for structural integrity

### Phase 3: Advanced (Future)
- [ ] Set screw holes
- [ ] Hub options (flush/extended/flanged)
- [ ] Envelope calculation for wheel (mathematical accuracy)
- [ ] Assembly positioning with correct orientation
- [ ] Manufacturing specs output (markdown with tolerances)
- [ ] WASM build (full calculator + geometry in browser)

## Web Calculator

Browser-based design tool using Pyodide (Python in WebAssembly):

**Features:**
- Calculate worm gear parameters from engineering constraints
- Real-time validation with DIN 3975/DIN 3996 standards
- Multiple design modes:
  - Envelope (fit within worm OD and wheel OD)
  - From wheel OD (reverse-calculate from wheel size)
  - From module (standard module-based design)
  - From centre distance (fit specific spacing)
- Export JSON Schema v1.0 for geometry generation
- Download markdown specifications
- Share designs via URL

**Quick Start:**
```bash
cd web
python3 -m http.server 8000
# Open http://localhost:8000
```

**Live Demo:** (Deploy to GitHub Pages for public access)

See [web/README.md](web/README.md) for web calculator documentation.

## Command Line Interface

### Basic Usage

```bash
# Generate both worm and wheel (auto-sized bores and keyways)
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
```

### Advanced Options

```bash
# Globoid worm (hourglass shape for better contact)
wormgear-geometry design.json --globoid

# Virtual hobbing for wheel (accurate throated teeth)
wormgear-geometry design.json --virtual-hobbing

# Use hobbing preset for speed/quality tradeoff
wormgear-geometry design.json --virtual-hobbing --hobbing-preset balanced
# Presets: fast (6 steps), balanced (18 steps), precise (36 steps)

# Tooth profile selection
wormgear-geometry design.json --profile ZA  # CNC machining (default)
wormgear-geometry design.json --profile ZK  # 3D printing

# View in OCP viewer without saving files
wormgear-geometry design.json --view --no-save

# View with mesh alignment (rotate wheel for visual mesh)
wormgear-geometry design.json --view --mesh-aligned
```

## Python API

### Calculator

```python
from wormgear.calculator import (
    calculate_design_from_module,
    calculate_design_from_centre_distance,
    calculate_design_from_wheel,
    validate_design,
    STANDARD_MODULES
)

# Design from standard module and ratio
design = calculate_design_from_module(module=2.0, ratio=30)

# Design from centre distance
design = calculate_design_from_centre_distance(
    centre_distance=40.0,
    ratio=30
)

# Design from wheel outside diameter
design = calculate_design_from_wheel(
    wheel_od=65.0,
    ratio=30,
    target_lead_angle=8.0
)

# Validate design
validation = validate_design(design)
if not validation.valid:
    for error in validation.errors:
        print(f"ERROR: {error.message}")
    for warning in validation.warnings:
        print(f"WARNING: {warning.message}")
```

### Geometry Generation

```python
from wormgear.core import (
    WormGeometry,
    WheelGeometry,
    GloboidWormGeometry,
    VirtualHobbingWheelGeometry,
    BoreFeature,
    KeywayFeature,
    get_hobbing_preset
)
from wormgear.io import load_design_json, save_design_json

# Load parameters
design = load_design_json("design.json")

# Build cylindrical worm with bore and keyway
worm_geo = WormGeometry(
    params=design.worm,
    assembly_params=design.assembly,
    length=40,
    bore=BoreFeature(diameter=8.0),
    keyway=KeywayFeature()
)
worm_geo.export_step("worm.step")

# Build globoid worm (hourglass shape)
globoid_worm_geo = GloboidWormGeometry(
    params=design.worm,
    assembly_params=design.assembly,
    wheel_pitch_diameter=design.wheel.pitch_diameter_mm,
    length=40
)
globoid_worm_geo.export_step("globoid_worm.step")

# Build helical wheel (default, simple)
wheel_geo = WheelGeometry(
    params=design.wheel,
    worm_params=design.worm,
    assembly_params=design.assembly,
    bore=BoreFeature(diameter=12.0),
    keyway=KeywayFeature()
)
wheel_geo.export_step("wheel.step")

# Build virtual hobbing wheel (accurate throated teeth)
hobbed_wheel_geo = VirtualHobbingWheelGeometry(
    params=design.wheel,
    worm_params=design.worm,
    assembly_params=design.assembly,
    wheel_pitch_diameter=design.wheel.pitch_diameter_mm,
    hobbing_steps=18  # Or use get_hobbing_preset("balanced")
)
hobbed_wheel_geo.export_step("hobbed_wheel.step")

# Save design to JSON
save_design_json(design, "design.json")
```

### Visualization

```python
# Display in VS Code with OCP CAD Viewer extension
worm_geo.show()
wheel_geo.show()

# Or use the viewer script
# python examples/view_design.py design.json
```

## Documentation

- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - System architecture and design decisions
- **[CLAUDE.md](CLAUDE.md)** - Development best practices and project context
- **[docs/GEOMETRY.md](docs/GEOMETRY.md)** - Full technical specification
- **[docs/ENGINEERING_CONTEXT.md](docs/ENGINEERING_CONTEXT.md)** - Standards and formulas
- **[web/README.md](web/README.md)** - Web calculator documentation

## Standards Compliance

### DIN 3975
Worm gear geometry standard:
- Profile types: ZA (straight flanks), ZK (convex flanks)
- Module series per ISO 54
- Pressure angles: 20° (standard), 14.5°, 25°

### ISO 54 / DIN 780
Standard modules (37 values from 0.3mm to 25mm):
- 0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0...

### DIN 6885
Keyway dimensions for bores 6mm-95mm:
- Automatic keyway sizing based on bore diameter
- Standard key sizes for common bore ranges

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
- Auto-calculated bores leave ≥1mm rim thickness
- Thin rims (<1.5mm) generate warnings but still work

**Problem:** "Bore outside DIN 6885 range" when using keyways

**Solutions:**
- For bores <6mm or >95mm, keyways cannot be auto-sized
- Use `--no-keyway` for small/large gears
- Small gears (<6mm bore) typically don't need keyways

**Problem:** STEP file won't import to CAD/CAM software

**Solutions:**
- Verify the STEP file is not empty (should be >100KB)
- Try a different CAD program (FreeCAD is free)
- Check for generation errors in console output
- Reduce complexity: `--no-bore --no-keyway` to test

### Virtual Hobbing Performance

**Problem:** Virtual hobbing is very slow

**Solutions:**
- Use presets: `--hobbing-preset fast` (6 steps, ~10s)
- Default: `--hobbing-preset balanced` (18 steps, ~20s)
- High quality: `--hobbing-preset precise` (36 steps, ~60s)
- For testing, use helical wheel instead (no virtual hobbing)

### 3D Printing Issues

**Problem:** Parts don't mesh smoothly after printing

**Solutions:**
- Use ZK profile for 3D printing: `--profile ZK`
- Increase printer resolution (smaller layer height)
- Add backlash in calculator (0.1-0.2mm recommended)
- Post-process with fine sanding on contact surfaces
- Apply dry lubricant (graphite powder or PTFE spray)

**Problem:** Parts break under load

**Solutions:**
- Use 100% infill for gear teeth area
- Choose stronger materials (nylon, PETG, or resin)
- Scale up the design (larger module)
- Reduce load or speed in application
- Consider hybrid design (metal worm, printed wheel)

### Getting Help

If you encounter issues not covered here:
1. Check the [GitHub Issues](https://github.com/pzfreo/worm-gear-3d/issues)
2. Review [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and [docs/GEOMETRY.md](docs/GEOMETRY.md)
3. For calculation questions, see [docs/ENGINEERING_CONTEXT.md](docs/ENGINEERING_CONTEXT.md)

## Performance

### Geometry Generation Times

- **Worm (cylindrical)**: ~0.5-2 seconds (36 sections/turn)
- **Worm (globoid)**: ~2-4 seconds (complex throat)
- **Wheel (helical)**: ~1-3 seconds (30 teeth)
- **Wheel (virtual hobbing)**: ~10-60 seconds (depends on steps)
  - Fast preset (6 steps): ~10 seconds
  - Balanced preset (18 steps): ~20 seconds
  - Precise preset (36 steps): ~60 seconds

### STEP File Sizes

- **Worm**: ~50-200 KB
- **Wheel**: ~100-500 KB
- **Complex features**: +10-50 KB each

## Background

Created for custom worm gear design in luthier (violin making) applications, where standard gears often don't fit unusual envelope constraints. Extended to support both CNC machining and 3D printing for makers, hobbyists, and professional engineers.

The calculator determines if a design is feasible; the geometry generator makes it manufacturable.

## Author

Paul Fremantle (pzfreo)
Luthier and hobby programmer

## License

MIT (to be added)
