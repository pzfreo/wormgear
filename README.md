# Wormgear

**Worm gear design: engineering calculations to CNC-ready STEP files.**

[![PyPI version](https://badge.fury.io/py/wormgear.svg)](https://pypi.org/project/wormgear/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Two Ways to Use

### 1. Web Calculator (No Installation)

**https://wormgear.studio**

Design worm gear pairs in your browser:
- Calculate parameters from engineering constraints
- Real-time validation (DIN 3975/DIN 3996)
- Export JSON for geometry generation
- Works on any device

### 2. Python Package (For 3D Geometry)

```bash
pip install wormgear
```

Generate CNC-ready STEP files:

```bash
# Design in browser at wormgear.studio, download JSON, then:
wormgear-geometry design.json

# Or generate with specific options:
wormgear-geometry design.json --profile ZK --globoid --worm-bore 8
```

## Quick Examples

### Command Line

```bash
# Basic generation (auto-sized bores and keyways)
wormgear-geometry design.json

# For 3D printing (convex tooth flanks)
wormgear-geometry design.json --profile ZK

# For CNC machining (straight flanks, default)
wormgear-geometry design.json --profile ZA

# Globoid worm (hourglass shape, better contact)
wormgear-geometry design.json --globoid

# Custom bore sizes
wormgear-geometry design.json --worm-bore 8 --wheel-bore 12

# View in VS Code (requires ocp-vscode extension)
wormgear-geometry design.json --view --no-save
```

### Python API

```python
from wormgear.calculator import design_from_module, validate_design
from wormgear.core import WormGeometry, WheelGeometry, BoreFeature, KeywayFeature
from wormgear.io import save_design_json

# Calculate parameters
design = design_from_module(module=2.0, ratio=30)
validation = validate_design(design)

if validation.valid:
    save_design_json(design, "design.json")

    # Generate 3D geometry
    worm = WormGeometry(
        params=design.worm,
        assembly_params=design.assembly,
        length=40.0,
        bore=BoreFeature(diameter=8.0),
        keyway=KeywayFeature()
    )
    worm.build()
    worm.export_step("worm.step")
```

## Features

- **Engineering calculations** per DIN 3975/DIN 3996
- **Validation** with errors and warnings
- **Tooth profiles**: ZA (CNC), ZK (3D printing), ZI (hobbing)
- **Worm types**: Cylindrical, Globoid (hourglass)
- **Wheel generation**: Helical or virtual hobbing
- **Features**: Bores, keyways (DIN 6885), set screws, hubs
- **Output**: Watertight STEP files for CAM/slicers

## Requirements

- Python 3.9+
- [build123d](https://build123d.readthedocs.io/) (installed automatically)

**Note**: build123d requires OpenCascade. Most platforms handle this automatically via pip, but see [build123d installation](https://build123d.readthedocs.io/en/latest/installation.html) if you encounter issues.

## Design Workflow

1. **Design** at [wormgear.studio](https://wormgear.studio)
2. **Download** the JSON file
3. **Generate** geometry: `wormgear-geometry design.json`
4. **Import** STEP files into CAD/CAM software
5. **Manufacture** via CNC or 3D printing

## CLI Reference

```
wormgear-geometry design.json [OPTIONS]

Options:
  --profile {ZA,ZK,ZI}    Tooth profile (default: ZA)
  --globoid               Generate globoid (hourglass) worm
  --virtual-hobbing       Use virtual hobbing for wheel
  --worm-bore MM          Override worm bore diameter
  --wheel-bore MM         Override wheel bore diameter
  --no-bore               Generate solid parts (no bores)
  --no-keyway             Omit keyways
  --worm-length MM        Worm length (default: 40)
  --wheel-width MM        Wheel width (default: auto)
  -o, --output-dir DIR    Output directory
  --view                  View in OCP viewer
  --no-save               Don't save STEP files
  -h, --help              Show all options
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md) - System design
- [Geometry](docs/GEOMETRY.md) - Technical specification
- [Engineering Context](docs/ENGINEERING_CONTEXT.md) - Standards and formulas

## Background

Created for custom worm gear design in luthier (violin making) applications, where standard gears don't fit unusual envelope constraints. Extended to support CNC machining and 3D printing for makers and engineers.

## License

MIT

## Author

Paul Fremantle ([@pzfreo](https://github.com/pzfreo))
