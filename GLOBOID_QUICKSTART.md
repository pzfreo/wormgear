# Globoid Worm Gears - Quick Start Guide

## Generate a Globoid Pair in 3 Steps

### 1. Run the Generator
```bash
python examples/globoid_pair.py
```

### 2. Load in CAD
- Import `globoid_pair_worm.step`
- Import `globoid_pair_wheel.step`

### 3. Position for Meshing
```
Worm:  (0, 0, 0), axis along Z
Wheel: (28.5, 0, 0), rotate 90° so axis is along Y
```

Rotate wheel around its axis to find mesh position.

## What You Get

- **Worm**: Hourglass shape, 3.3 helical thread wraps
- **Wheel**: Deep throat for 75° wrap angle (industry standard)
- **Mesh**: ~1.7 teeth in contact, minimal gap
- **Ready for**: 5-axis CNC machining

## Key Parameters

All calculated from module and ratio:
- Module: 1.5mm
- Ratio: 1:30 (1-start worm, 30-tooth wheel)
- Centre distance: 28.5mm (auto-calculated)
- Throat depth: 9.45mm radius (for 75° wrap)

## Different Sizes

Edit these values in `examples/globoid_pair.py`:
```python
module = 1.5        # Change this (0.5 to 8mm typical)
num_teeth = 30      # Wheel teeth (15-100 typical)
num_starts = 1      # Worm starts (1-4 typical)
```

The script auto-calculates everything else including proper throat depth!

---

**For full details**: See `GLOBOID_COMPLETE.md`
