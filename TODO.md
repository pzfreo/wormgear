# TODO - Worm Gear 3D Generator

## Current Status

**Phase 2: Features - Bore & Keyway Complete ✅**

Completed features:
- ✅ Auto-calculated bore diameters (~25% of pitch diameter)
- ✅ DIN 6885 keyway support (for bores ≥6mm)
- ✅ Small gear support (bores down to 2mm, below DIN 6885 range)
- ✅ Thin rim warnings (when rim thickness <1.5mm)
- ✅ CLI defaults to bore+keyway with opt-out flags
- ✅ Rim thickness display in CLI output

---

## Next Steps

### 1. Web Tool Design (Next Immediate Task) 🎯

**Create detailed wireframes** for the integrated web tool:
- Landing page with three paths (Standard, Envelope, Import)
- Path A: Standard engineering design flow (module-based)
- Path B: Envelope constraint design flow (OD-based)
- Path C: JSON import flow
- Calculator results and validation screens
- Manufacturing parameters screen
- Quick preview (3D visualization) screen
- Production generation and download screen

**Reference:**
- Full specification: `docs/WEB_TOOL_SPEC_V2.md`
- Design decisions finalized (module dropdown, warnings display, always-visible mfg params, desktop-only)

**Deliverable:** Visual mockups showing user flow from inputs → validation → 3D preview → production files

---

### 2. Web Tool Phase 1 Implementation

After wireframes are approved, begin building:

**Phase 1 Core Features:**
- [ ] Integrate wormcalc code into web interface
- [ ] Implement Path A (standard/module-based)
- [ ] Implement Path B (envelope constraints)
- [ ] Implement Path C (JSON import)
- [ ] Connect calculator → 3D generator flow
- [ ] Validation UI (errors, warnings, info) with actionable messages
- [ ] Manufacturing parameter controls (bore, keyway, lengths)
- [ ] Quick preview generation (simplified geometry, 5-10 seconds)
- [ ] 3D visualization (WebGL viewer - Three.js)
- [ ] Interactive 3D controls (rotate, zoom, pan, toggle parts)
- [ ] Production generation (full detail STEP files, 30-60 seconds)
- [ ] PDF manufacturing spec (complete with drawings, tolerances, assembly)
- [ ] Expanded design.json export
- [ ] Zip package download (STEP + PDF + JSON)
- [ ] All validation rules including:
  - Diameter quotient (q) display and validation
  - Hunting teeth ratio (GCD check for multi-start worms)
  - All existing validations (lead angle, undercut, etc.)

**Architecture:**
- Single page application (HTML/JS)
- Pyodide 0.25+ (Python in WebAssembly)
- wormcalc + wormgear_geometry packages
- build123d + OCP for CAD
- Three.js for 3D rendering
- Desktop-only (CPU/GPU requirements)

---

## Phase 2: Remaining Features (After Web Tool)

### Set Screw Holes
- [ ] Define set screw placement (radial, through bore wall)
- [ ] Standard sizes (M3, M4, M5, etc.)
- [ ] Add to BoreFeature or separate SetScrewFeature class
- [ ] Update CLI and API

### Hub Options
- [ ] Flush hub (no extension)
- [ ] Extended hub (specify length)
- [ ] Flanged hub (specify flange diameter and thickness)
- [ ] Add to WheelGeometry parameters
- [ ] Update CLI and API

---

## Phase 3+: Future Enhancements

See `docs/WEB_TOOL_SPEC_V2.md` for full roadmap:
- Phase 2: Polish & usability (example gallery, share links, etc.)
- Phase 3: Advanced features (editable tolerances, batch generation)
- Phase 4: Educational & pro features (tooltips, optimization, cost estimation)

---

## Notes

- **Web tool will replace wormgearcalc** - unified product
- **Desktop-only** due to CPU/memory requirements (WebAssembly + 3D rendering)
- **Expanded JSON format** includes all manufacturing parameters for full reproducibility
- **Two-tier generation**: Quick preview (fast, simplified) → Production files (exact, slower)
- **PDF manufacturing spec** is key deliverable for CNC shops

---

**Status:** Ready to begin wireframe design
**Last Updated:** 2026-01-20
