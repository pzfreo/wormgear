# TODO - Wormgear

## Current Status: v0.0.46

**Complete:**
- Engineering calculations (DIN 3975/DIN 3996)
- Validation system with errors/warnings (82+ validation tests)
- Worm and wheel geometry generation (cylindrical + sweep)
- Globoid worm support
- Virtual hobbing wheel generation
- STEP export
- Python API and CLI
- Web calculator UI (redesigned with unified Design tab)
- Bores and keyways (DIN 6885)
- JSON Schema v2.0
- 3D preview in browser with animated assembly
- CI/CD pipeline (GitHub Actions, PyPI publish)
- Version tagging + PyPI package
- Integration test suite (697 tests, full pipeline coverage)
- Tech debt remediation (Phases 1-4 complete)

## Next Tasks

### Tech Debt (Phase 5 — remaining)
- [ ] Add dev dependencies (pytest-timeout, pytest-xdist for parallel testing)
- [ ] Enable strict mypy on core modules (worm.py, wheel.py)

### Manufacturing Specifications
- [ ] Generate CNC-ready documentation alongside STEP files
- [ ] Include all dimensions with tolerances
- [ ] Material recommendations
- [ ] Surface finish specifications
- [ ] CLI `--specs` flag

### Python API Polish
- [ ] Complete type hints (mypy clean)
- [ ] Comprehensive docstrings
- [ ] API documentation (Sphinx)

## Future

### Web Tool Enhancements
- [ ] Design gallery with examples
- [ ] Performance optimization (virtual hobbing in WASM)

### Advanced Features
- [ ] True envelope wheel geometry
- [ ] Assembly positioning
- [ ] Cost estimation

---

**Last Updated:** 2026-02-14
