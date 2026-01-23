# TODO - Worm Gear 3D Generator

## Current Status

**Phase 1.1: Set Screws & Hubs Complete ✅**

Completed features:
- ✅ Auto-calculated bore diameters (~25% of pitch diameter, constrained by rim)
- ✅ DIN 6885 keyway support (for bores 6-95mm)
- ✅ Small gear support (bores down to 2mm, below DIN 6885 range)
- ✅ Thin rim warnings (when rim thickness <1.5mm)
- ✅ CLI defaults to bore+keyway with opt-out flags
- ✅ Rim thickness display in CLI output
- ✅ Set screw holes with auto-sizing (M2.5-M8, 1-3 screws)
- ✅ Hub options (flush/extended/flanged with bolt patterns)
- ✅ Extended JSON format for manufacturing features
- ✅ CLI --save-json flag for full design reproducibility
- ✅ Comprehensive documentation with troubleshooting
- ✅ Documentation power review complete

---

## Strategic Direction

**📋 See [docs/DEVELOPMENT_ROADMAP.md](docs/DEVELOPMENT_ROADMAP.md) for complete three-phase plan (8-10 months)**

### Roadmap Summary

**Phase 1 (2-3 months): Complete Core Product**
- Remaining features: set screws, hub options
- Manufacturing specifications output (markdown/PDF)
- Testing & validation suite
- Python API polish
- Target: v1.0 release

**Phase 2 (3-4 months): Unified Web Tool**
- Integrated calculator + 3D generator
- Three design paths: Standard, Envelope, Import
- 3D visualization with Three.js
- Two-tier generation (quick preview + production)
- Example gallery
- Target: v2.0 release (replaces wormgearcalc)

**Phase 3 (2-3 months): Advanced Features**
- Accurate wheel geometry (envelope calculation)
- Assembly positioning
- Advanced manufacturing features
- Web tool enhancements (optimization, batch, cost estimation)
- Community ecosystem
- Target: v3.0 release

---

## Next Immediate Tasks (Phase 1.2)

### 1. Manufacturing Specifications Output (2-3 weeks) 🎯

**Goal:** Generate CNC-ready documentation alongside STEP files

**Tasks:**
- [ ] Create `specs.py` module
- [ ] Define specification template (markdown format)
- [ ] Include for both worm and wheel:
  - All key dimensions with tolerances (OD, PD, root, length)
  - Bore dimensions and tolerance (H7, H8)
  - Keyway dimensions (per DIN 6885)
  - Set screw specifications
  - Hub specifications (if applicable)
- [ ] Assembly section:
  - Center distance (nominal ± tolerance)
  - Alignment instructions
  - Hand (left/right) and orientation
  - Backlash specification
- [ ] Material recommendations:
  - Worm: hardened steel (58-62 HRC suggested)
  - Wheel: bronze or acetal (for low friction)
- [ ] Manufacturing notes:
  - Surface finish (Ra 0.8-1.6 on contact surfaces)
  - Tool path considerations (undercuts, clearances)
  - Inspection requirements
- [ ] Optional PDF generation:
  - Use pandoc or weasyprint to convert markdown
  - Include technical drawing (optional, future enhancement)
- [ ] CLI integration:
  - `--specs` flag (default: enabled)
  - `--specs-format markdown|pdf` (default: markdown)
  - `--no-specs` to disable
- [ ] Validation:
  - Get feedback from real CNC machinist
  - Ensure all critical info is present
- [ ] Documentation and examples

**Success criteria:**
- ✅ Markdown spec generated alongside STEP files
- ✅ CNC machinist can manufacture part from spec alone
- ✅ PDF generation works (optional)
- ✅ All dimensions and tolerances clearly specified

**Example spec structure:**
```markdown
# Worm Gear Manufacturing Specification

Generated: 2026-01-21
Design: M2 30:1 Right-Hand

## Part 1: Worm (Drive Component)

### Critical Dimensions
| Parameter              | Nominal   | Tolerance | ISO Fit | Notes            |
|------------------------|-----------|-----------|---------|------------------|
| Outside Diameter       | 20.29 mm  | ±0.02     | h6      | Ground finish    |
| Pitch Diameter         | 16.29 mm  | Reference | -       | -                |
| Root Diameter          | 11.29 mm  | +0.05/-0  | -       | -                |
| Thread Lead            | 6.283 mm  | ±0.01     | -       | Critical         |
| Overall Length         | 40.00 mm  | ±0.1      | -       | -                |

### Features
| Feature                | Dimension | Tolerance | ISO Fit | Notes            |
|------------------------|-----------|-----------|---------|------------------|
| Bore Diameter          | 8.00 mm   | +0.015/0  | H7      | Sliding fit      |
| Keyway (DIN 6885)      | 3×1.8 mm  | per std   | -       | Width × depth    |
| Set Screw              | M4        | -         | -       | 90° from keyway  |

### Material Specification
- **Recommended:** EN 1.7131 (16MnCr5) case hardened
- **Hardness:** 58-62 HRC surface, 35-45 HRC core
- **Alternative:** EN 1.4305 (303 stainless) for corrosion resistance

### Surface Finish
- Thread flanks: Ra 0.8 µm (ground or hard-turned)
- Bore: Ra 1.6 µm (reamed)
- Faces: Ra 3.2 µm

### Manufacturing Notes
- Thread hand: RIGHT (right-hand helix)
- Lead angle: 7.0°
- Start threads at least 2mm from each end
- Deburr all edges, especially bore ends
...

## Part 2: Wheel (Driven Component)
...

## Assembly Instructions
- Center distance: 38.145 ± 0.05 mm
- Align keyways for synchronization (if required)
- Backlash: 0.05 mm (adjust with shims if needed)
...
```

**Estimated effort:** 2-3 weeks

---

## Phase 1: Additional Tasks

### 4. Testing & Validation Suite (2 weeks)

- [ ] Unit tests for all modules (>80% coverage)
- [ ] Integration tests (full generation workflows)
- [ ] STEP validation (import/export round-trip)
- [ ] Geometry validation (volume, mass calculations)
- [ ] Mesh interference detection
- [ ] Performance benchmarks
- [ ] CI/CD pipeline (GitHub Actions)

### 5. Python API Polish (1 week)

- [ ] Consistent error messages
- [ ] Complete type hints (mypy validation)
- [ ] Comprehensive docstrings
- [ ] Example scripts for all features
- [ ] API documentation (Sphinx)

### 6. Documentation Updates (ongoing)

- [ ] Update README with new features
- [ ] Update GEOMETRY.md technical spec
- [ ] Update CLAUDE.md context
- [ ] Create video tutorials (optional)

### 7. v1.0 Release (1 week)

- [ ] Version tagging and release notes
- [ ] PyPI package (optional)
- [ ] Announcement blog post
- [ ] Community outreach

---

## Phase 2: Web Tool (Future)

**See DEVELOPMENT_ROADMAP.md for detailed breakdown**

Key milestones:
- Calculator integration (Path A, B, C)
- 3D visualization with Three.js
- Two-tier generation (preview + production)
- Example gallery
- Deployment

---

## Phase 3: Advanced Features (Future)

**See DEVELOPMENT_ROADMAP.md for detailed breakdown**

Key milestones:
- Accurate wheel geometry (envelope calculation)
- Assembly positioning
- Advanced manufacturing features
- Community ecosystem

---

## Notes

### Current Focus
**We are in Phase 1.2** - Manufacturing specifications, testing, and documentation polish before v1.0.

**Phase 1.1 Complete ✅**: Set screws, hubs, and extended JSON format implemented.

Web tool development (Phase 2) will begin after Phase 1 is complete and v1.0 is released.

### Philosophy
- **Complete before expanding** - Finish each phase fully before moving on
- **User value first** - Prioritize features users need most
- **Quality over speed** - Test thoroughly, release when ready
- **Manufacturing focus** - CNC machinists are our primary users

### Success Metrics
- Phase 1: v1.0 released with all features, tests passing, specs validated
- Phase 2: v2.0 web tool replaces wormgearcalc, 100+ users in first month
- Phase 3: v3.0 with advanced features, active community

---

**Last Updated:** 2026-01-21
**Current Task:** Set screws ✅, Hubs ✅, JSON integration ✅ - Ready for manufacturing specs (Phase 1.2, Task 1)
