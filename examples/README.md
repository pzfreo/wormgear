# Examples

## Python API

### unified_workflow.py

Complete workflow demonstrating the wormgear package:

```bash
cd examples
python3 unified_workflow.py
```

This example shows:
1. Calculate design parameters from module and ratio
2. Validate the design
3. Save/load design JSON
4. Generate 3D geometry (worm and wheel)
5. Add features (bore, keyway)
6. Export STEP files

## Google Colab Notebooks

### wormgear_colab.ipynb

Calculator-only notebook for designing worm gears in the browser:
- No local installation required
- Calculate design parameters
- Export JSON for use with CLI

### wormgear_colab_geometry.ipynb

Full workflow notebook including 3D geometry generation:
- Calculate and validate designs
- Generate worm and wheel geometry
- Export STEP files
- Download directly from Colab

## CLI Usage

Generate geometry from a design JSON file:

```bash
# Generate both worm and wheel
wormgear-geometry design.json

# Custom dimensions
wormgear-geometry design.json --worm-length 50 --wheel-width 12

# Add bores (auto-sized keyways included)
wormgear-geometry design.json --worm-bore 8 --wheel-bore 12

# Solid parts without bores
wormgear-geometry design.json --no-bore

# Output to specific directory
wormgear-geometry design.json -o ~/my_gears/

# Generate only one part
wormgear-geometry design.json --worm-only
wormgear-geometry design.json --wheel-only
```

## Creating Design Files

Generate design JSON using either:

1. **Web Calculator**: https://pzfreo.github.io/wormgear/
2. **Python API**:
   ```python
   from wormgear import calculate_design_from_module, save_design_json

   design = calculate_design_from_module(module=2.0, ratio=30)
   save_design_json(design, "my_design.json")
   ```

## Visualization

### OCP Viewer (VS Code)

For interactive visualization during development:

1. Install VS Code extension: OCP CAD Viewer
2. Install Python package: `pip install ocp-vscode`
3. Use in code:
   ```python
   from wormgear import WormGeometry
   worm_geo = WormGeometry(params, assembly_params, length=40)
   worm_geo.show()  # Opens in OCP viewer
   ```

### CAD Software

Import generated STEP files into:
- FreeCAD (free, open-source)
- Fusion 360
- SolidWorks
- OnShape
- Any CAM software for CNC toolpath generation
