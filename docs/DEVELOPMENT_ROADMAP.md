# Development Roadmap - Worm Gear 3D

**Status:** Strategic plan for next 8-10 months of development
**Last Updated:** 2026-01-21
**Current Position:** Phase 2 features (bore/keyway) complete, web tool experimental

---

## Overview

This roadmap outlines three strategic phases to take worm-gear-3d from a functional Python library to a production-ready web application that unifies calculation and CAD generation.

**Key Principles:**
- ✅ **User value first** - Prioritize features users need most
- ✅ **Complete before expanding** - Finish Phase 2 features before advanced math
- ✅ **Web tool is the killer feature** - Most users want browser-based workflow
- ✅ **Manufacturing focus** - CNC shops need specs, tolerances, assembly info

---

## Phase 1: Complete Core Product 🎯

**Duration:** 2-3 months
**Goal:** Finish all Python library features, add manufacturing outputs, establish quality baseline

**Status:** ~70% complete (bore/keyway done, specs/hub/testing remain)

### 1.1 Remaining Phase 2 Features

**Set Screw Holes** (1 week)
- [ ] Define placement strategy (radial through bore wall, 90° from keyway)
- [ ] Standard sizes (M3, M4, M5 based on bore diameter)
- [ ] `SetScrewFeature` class with auto-sizing from bore
- [ ] CLI flags: `--set-screw`, `--set-screw-size M4`
- [ ] Update Python API and examples
- [ ] Documentation and tests

**Hub Options** (2 weeks)
- [ ] Flush hub (default, no extension)
- [ ] Extended hub with custom length
- [ ] Flanged hub (diameter, thickness, bolt holes)
- [ ] `HubFeature` class or integrate into WheelGeometry
- [ ] CLI flags: `--hub-type flush|extended|flanged`, `--hub-length`, etc.
- [ ] Validate hub doesn't interfere with worm mesh
- [ ] Documentation and tests

### 1.2 Manufacturing Specifications Output (2-3 weeks)

**Critical deliverable for CNC shops**

- [ ] Generate markdown specs alongside STEP files
- [ ] Include all key dimensions with tolerances
- [ ] Assembly instructions (center distance, alignment)
- [ ] Material recommendations (hardness for worm/wheel)
- [ ] Surface finish requirements
- [ ] Tool path considerations (undercuts, clearances)
- [ ] Optional: Convert markdown to PDF via pandoc/weasyprint
- [ ] CLI flag: `--specs` (enabled by default)

**Example output:**
```markdown
# Worm Gear Manufacturing Specification

## Part 1: Worm (Drive)
| Parameter              | Nominal   | Tolerance | Notes            |
|------------------------|-----------|-----------|------------------|
| Outside Diameter       | 20.29 mm  | ±0.02     | Ground finish    |
| Pitch Diameter         | 16.29 mm  | Reference | -                |
| Root Diameter          | 11.29 mm  | +0.05/-0  | -                |
| Thread Lead            | 6.283 mm  | ±0.01     | Critical         |
| Overall Length         | 40.00 mm  | ±0.1      | -                |
| Bore Diameter          | 8.00 mm   | +0.015/0  | H7 fit           |
| Keyway (DIN 6885)      | 3×1.8 mm  | per std   | -                |

**Material:** EN 1.7131 (16MnCr5) case hardened to 58-62 HRC
**Surface Finish:** Ra 0.8 on thread flanks
...
```

### 1.3 Testing & Validation Suite (2 weeks)

**Establish quality baseline**

- [ ] Unit tests for all geometry functions
- [ ] Integration tests (full worm+wheel generation)
- [ ] STEP file validation (import/export round-trip)
- [ ] Volume/mass calculations (sanity checks)
- [ ] Mesh interference detection
- [ ] Performance benchmarks
- [ ] CI/CD pipeline (GitHub Actions)
- [ ] Test matrix: multiple modules, ratios, features

### 1.4 Python API Polish (1 week)

- [ ] Consistent error messages
- [ ] Better type hints (mypy validation)
- [ ] Docstring completeness
- [ ] Example scripts for all features
- [ ] API documentation generation (Sphinx)

### 1.5 Bug Fixes & Refinement (ongoing)

- [ ] Address any geometry issues discovered in testing
- [ ] Improve bore/keyway validation edge cases
- [ ] Optimize build123d operations for speed
- [ ] Memory usage profiling

### Phase 1 Deliverables ✅

1. **Complete Python library** - All planned features implemented
2. **Manufacturing specs** - CNC-ready documentation with tolerances
3. **Test suite** - Confidence in geometry quality
4. **API documentation** - Professional reference docs
5. **v1.0 release** - Tagged, documented, stable

**Success Criteria:**
- ✅ 100% of planned Phase 2 features complete
- ✅ Test coverage >80%
- ✅ All example designs generate without errors
- ✅ Manufacturing specs validated by CNC shop
- ✅ Performance: M2 30:1 pair generates in <10s on typical hardware

---

## Phase 2: Unified Web Tool 🌐

**Duration:** 3-4 months
**Goal:** Build production-ready web application that replaces wormgearcalc

**Status:** Experimental prototype exists, needs complete rebuild per WEB_TOOL_SPEC_V2

### 2.1 Architecture & Setup (1 week)

- [ ] Project structure (single-page app)
- [ ] Pyodide 0.26+ integration
- [ ] build123d + OCP.wasm loading strategy
- [ ] Development workflow (local server, hot reload)
- [ ] Build pipeline (minimize, bundle)
- [ ] Deployment strategy (GitHub Pages, Cloudflare Pages)

### 2.2 Calculator Integration (2-3 weeks)

**Integrate wormgearcalc logic into web UI**

- [ ] Port calculator functions to JavaScript/Python hybrid
- [ ] Implement Path A: Standard/Module-based design
- [ ] Implement Path B: Envelope constraint design
- [ ] Implement Path C: JSON import
- [ ] Real-time validation (errors, warnings, info)
- [ ] Efficiency and self-locking calculations
- [ ] Diameter quotient (q) display
- [ ] Hunting teeth ratio check (GCD validation)
- [ ] Profile shift support

### 2.3 User Interface - Input Screens (3 weeks)

**Desktop-optimized (required for CPU/GPU performance)**

- [ ] Landing page with three design paths
- [ ] Path A form: Module dropdown (ISO 54), ratio, pressure angle, etc.
- [ ] Path B form: Max ODs, ratio, constraint solver
- [ ] Path C form: JSON upload/paste/URL parameter
- [ ] Always-visible manufacturing parameters panel
- [ ] Real-time validation feedback with color-coding
- [ ] Responsive layout (desktop minimum 1280px width)
- [ ] Keyboard navigation and accessibility

### 2.4 3D Visualization (3-4 weeks)

**Critical for user confidence**

- [ ] Three.js scene setup (lights, camera, controls)
- [ ] STEP to mesh conversion (OCP → triangulation)
- [ ] Worm rendering with proper shading
- [ ] Wheel rendering with proper shading
- [ ] Assembly view (both parts positioned correctly)
- [ ] Interactive controls: rotate, pan, zoom
- [ ] Toggle parts visibility (worm only, wheel only, both)
- [ ] Camera presets (front, side, isometric)
- [ ] Material/color picker
- [ ] Screenshot export (PNG)
- [ ] Performance optimization (LOD, culling)

### 2.5 Two-Tier Generation (2 weeks)

**Balance speed vs quality**

**Quick Preview** (5-10 seconds):
- [ ] Reduced section count (18 sections instead of 36)
- [ ] Simplified features (bore only, no keyway)
- [ ] Immediate visual feedback
- [ ] Good enough for design validation

**Production Files** (30-60 seconds):
- [ ] Full detail (36+ sections)
- [ ] All features (bore, keyway, set screw, hub)
- [ ] Exact tolerances
- [ ] Manufacturing-ready STEP
- [ ] Progress indicator with stages

### 2.6 Output & Export (1 week)

- [ ] STEP file download (worm.step, wheel.step)
- [ ] PDF manufacturing specification
- [ ] Extended design.json (includes all manufacturing params)
- [ ] Zip package (STEP + PDF + JSON)
- [ ] Share link generation (design encoded in URL)
- [ ] Local storage (save designs to browser)

### 2.7 Example Gallery (1 week)

**Help users get started quickly**

- [ ] Curated preset designs with descriptions:
  - Guitar tuning machine (7mm bore, 12:1)
  - Light duty drive (M2, 30:1, self-locking)
  - High ratio reducer (M3, 60:1)
  - Compact precision (M1.5, 20:1)
  - Heavy duty (M4, 40:1, extended hub)
- [ ] Thumbnail images
- [ ] "Load Example" button
- [ ] Design story/use case descriptions

### 2.8 Error Handling & UX Polish (2 weeks)

- [ ] User-friendly error messages (not Python tracebacks)
- [ ] Loading states and progress bars
- [ ] Graceful Pyodide loading (with fallback messages)
- [ ] Browser compatibility checks (WebAssembly, WebGL)
- [ ] Tooltips and help text
- [ ] Undo/redo for inputs
- [ ] Form validation with inline feedback
- [ ] Mobile detection with "desktop required" message

### 2.9 Testing & Deployment (1 week)

- [ ] Cross-browser testing (Chrome, Firefox, Safari, Edge)
- [ ] Multiple design validation (all examples work)
- [ ] Performance profiling (identify bottlenecks)
- [ ] Documentation (user guide, FAQ)
- [ ] Deploy to production hosting
- [ ] Analytics setup (optional, privacy-respecting)

### Phase 2 Deliverables ✅

1. **Unified web application** - Calculator + CAD generator in one
2. **Three design paths** - Standard, Envelope, Import
3. **3D visualization** - Interactive WebGL preview
4. **Production-ready output** - STEP + PDF + JSON
5. **Example gallery** - Help users get started
6. **v2.0 release** - Web tool replaces wormgearcalc

**Success Criteria:**
- ✅ All three design paths functional
- ✅ 3D preview renders in <10 seconds
- ✅ Production files generate successfully
- ✅ Works in Chrome, Firefox, Safari, Edge (desktop)
- ✅ Positive user feedback from beta testing
- ✅ Documentation complete

**Launch Strategy:**
1. Beta release to limited users (GitHub community)
2. Gather feedback, fix critical issues
3. Public announcement and marketing
4. Deprecate old wormgearcalc site with migration guide

---

## Phase 3: Advanced Features & Optimization 🚀

**Duration:** 2-3 months
**Goal:** Mathematical accuracy, advanced features, community polish

**Status:** Future enhancements, after core product is solid

### 3.1 Accurate Wheel Geometry (3-4 weeks)

**Implement Option B: Envelope Calculation**

Currently using "integrated throating" (Option D) which is good but not mathematically exact.

- [ ] Research envelope calculation algorithms
- [ ] Implement analytical tooth surface calculation
- [ ] Generate B-spline surfaces (not just lofted sections)
- [ ] Compare accuracy with current approach
- [ ] Quantify improvement (measure deviation)
- [ ] Performance optimization (caching, parallelization)
- [ ] Make it optional: `--accurate-wheel` flag
- [ ] Documentation of mathematical approach

**Validation:**
- [ ] Contact pattern simulation
- [ ] Interference detection (true vs approximate)
- [ ] Load distribution analysis

### 3.2 Assembly Features (2 weeks)

**Correct positioning and interference checking**

- [ ] Position worm and wheel at correct center distance
- [ ] Align keyways if both parts have them
- [ ] Rotation phase alignment (mesh engagement)
- [ ] Assembly STEP file (both parts in correct position)
- [ ] Interference detection
- [ ] Clearance analysis
- [ ] Assembly instructions (orientation, alignment)

### 3.3 Advanced Manufacturing Features (2-3 weeks)

**User-requested enhancements**

- [ ] Multiple set screws (120° spacing)
- [ ] Dowel pin holes (for wheel assembly)
- [ ] Mounting holes in flanged hubs
- [ ] Lubrication grooves
- [ ] Chamfers and fillets (cosmetic/functional)
- [ ] Face grooving (wheel face pattern)
- [ ] Custom bore profiles (stepped, tapered)

### 3.4 Web Tool Phase 2 Features (3 weeks)

**Per WEB_TOOL_SPEC_V2 roadmap**

- [ ] Editable tolerance fields (let users adjust H7 to H8, etc.)
- [ ] Batch generation (multiple ratios from one module)
- [ ] Design comparison tool (side-by-side)
- [ ] Cost estimation (material, machining time)
- [ ] Optimization suggestions (efficiency, wear, noise)
- [ ] Educational tooltips (explain lead angle, q factor, etc.)
- [ ] Export to FreeCAD Python script
- [ ] Integration with CAM software (toolpath hints)

### 3.5 Performance Optimization (1-2 weeks)

- [ ] Profile geometry generation (identify bottlenecks)
- [ ] Optimize build123d operations
- [ ] Reduce section count where possible (adaptive detail)
- [ ] Parallel processing (worker threads in web tool)
- [ ] Caching frequently-used calculations
- [ ] Lazy loading in web UI (faster initial load)

### 3.6 Community & Ecosystem (ongoing)

**Build community around the tool**

- [ ] User showcase (share your designs)
- [ ] Community design library
- [ ] Plugin system (custom features)
- [ ] API for third-party integrations
- [ ] Tutorial videos
- [ ] Blog posts (use cases, case studies)
- [ ] Conference presentations

### 3.7 Advanced Validations (1 week)

- [ ] Finite element analysis integration (stress estimation)
- [ ] Wear prediction
- [ ] Noise estimation
- [ ] Thermal analysis (for high-speed applications)
- [ ] Lubrication regime recommendations

### Phase 3 Deliverables ✅

1. **Mathematically accurate wheel** - Envelope calculation implemented
2. **Assembly positioning** - Correctly aligned parts
3. **Advanced features** - Everything users requested
4. **Web tool enhancements** - Batch, comparison, optimization
5. **v3.0 release** - Professional-grade tool
6. **Community ecosystem** - Engaged users, shared designs

**Success Criteria:**
- ✅ Accurate wheel geometry validates better than current approach
- ✅ Advanced features work reliably
- ✅ Performance improvements measurable (>30% faster)
- ✅ Active community (>100 designs shared)
- ✅ Third-party integrations exist

---

## Risk Management

### Technical Risks

**Risk:** Pyodide + build123d + OCP in browser is slow/unstable
**Mitigation:** Two-tier generation (quick preview), progressive enhancement, fallback to server-side generation if needed

**Risk:** Envelope calculation is mathematically complex
**Mitigation:** Keep current approach as default, make accurate wheel optional, extensive testing

**Risk:** Users expect mobile support but it's not feasible
**Mitigation:** Clear messaging on landing page, detect mobile and show "desktop required" notice

### Schedule Risks

**Risk:** Phase 2 (web tool) takes longer than estimated
**Mitigation:** MVP first (Path A only), then expand. Release early, iterate.

**Risk:** Waiting for Phase 3 delays user value
**Mitigation:** Phase 1 & 2 already deliver massive value. Phase 3 is icing on cake.

### User Adoption Risks

**Risk:** Users don't discover the tool
**Mitigation:** SEO optimization, gear forums outreach, YouTube tutorials, open-source communities

**Risk:** Competing tools exist
**Mitigation:** Unique value prop is integrated calculator+CAD+specs in browser. No installation.

---

## Success Metrics

### Phase 1
- [ ] All planned features implemented and tested
- [ ] Test coverage >80%
- [ ] Manufacturing specs validated by real CNC shop
- [ ] Performance: typical design generates in <10s

### Phase 2
- [ ] Web tool functional in 4 major browsers
- [ ] 3D preview renders in <10s, production in <60s
- [ ] 100+ users try the tool in first month
- [ ] Positive feedback (NPS >30)
- [ ] At least 10 users report successful CNC manufacturing

### Phase 3
- [ ] Accurate wheel geometry demonstrably better
- [ ] Community library has >100 shared designs
- [ ] Third-party integration (at least one CAM tool)
- [ ] Performance improvement >30% from Phase 2

---

## Dependencies

### External
- **build123d** - Maintain compatibility with latest releases
- **OCP** - WebAssembly builds availability
- **Pyodide** - Keep up with new versions (0.26+)
- **Three.js** - Stable for 3D rendering

### Internal
- **wormgearcalc** - Calculator logic integration
- **Test hardware** - Need variety of systems for testing
- **CNC access** - Validate manufacturing specs with real parts

---

## Resource Requirements

### Development
- **Phase 1:** 1 developer, ~200 hours
- **Phase 2:** 1-2 developers, ~400 hours
- **Phase 3:** 1 developer, ~150 hours

### Infrastructure
- Static hosting (GitHub Pages or Cloudflare Pages) - Free
- Domain name (optional) - ~$15/year
- Analytics (optional) - Free tier

### Testing
- Multiple browsers/OS for web tool testing
- Access to CNC machine for validation (can partner with users)

---

## Versioning Strategy

**v1.0** - Phase 1 complete (Python library with all features)
**v1.x** - Bug fixes and minor improvements

**v2.0** - Phase 2 complete (unified web tool)
**v2.x** - Web tool improvements, new examples

**v3.0** - Phase 3 complete (accurate wheel, advanced features)
**v3.x** - Community features, optimizations

---

## Communication Plan

### During Development
- Weekly TODO.md updates
- Monthly blog posts on progress
- Demo videos for major milestones
- Open GitHub issues for community feedback

### At Releases
- Detailed release notes
- Migration guides (if breaking changes)
- Demo video showing new features
- Announcement on relevant forums/communities

### Community Engagement
- Respond to GitHub issues within 48 hours
- Monthly "show and tell" (user designs showcase)
- Quarterly roadmap reviews
- Annual user survey

---

## Conclusion

This roadmap takes worm-gear-3d from a solid Python library to a comprehensive web-based design tool that serves engineers, makers, and CNC shops.

**Key Milestones:**
- **Month 3:** v1.0 - Complete Python library with manufacturing specs
- **Month 7:** v2.0 - Unified web tool replaces wormgearcalc
- **Month 10:** v3.0 - Advanced features and community ecosystem

**Strategic Focus:**
1. **Complete before expanding** - Finish each phase fully
2. **User value drives priorities** - Web tool over mathematical perfection
3. **Quality over speed** - Test thoroughly, release when ready
4. **Community matters** - Build ecosystem around the tool

The end result will be the most comprehensive open-source worm gear design tool available, serving a global community of engineers and makers.

---

**Next Immediate Steps:**
1. Review and approve this roadmap
2. Begin Phase 1.1: Set screw holes implementation
3. Set up project tracking (GitHub Projects or similar)
4. Create detailed task breakdown for Phase 1

**Questions for Discussion:**
- Should we prioritize manufacturing specs over remaining features?
- Is Phase 2 timeline realistic given Pyodide complexity?
- Should we seek beta testers earlier in Phase 2?
- Any features missing from this roadmap?
