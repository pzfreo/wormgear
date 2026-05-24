# Changelog

All notable changes to wormgear will be documented here.

The format is loosely based on [Keep a Changelog](https://keepachangelog.com/),
and the project uses [semantic versioning](https://semver.org/) — with the
caveat that **0.x.y is pre-1.0**, so minor-version bumps may include
breaking changes.

## 0.1.1 — unreleased

### Fixed

- **Centre-distance bug in `WormGear` / `make_pair`** ([#221](https://github.com/pzfreo/wormgear/pull/221)). `WormGear.__init__` used a hardcoded placeholder ratio (=10) when computing the worm's pitch diameter — fine for the worm geometry itself, but the same placeholder leaked into the stored `_assembly_params.centre_distance_mm`, so a `make_pair(module=2.0, ratio=30)` reported a centre distance of 18.14 mm instead of the correct 38.14 mm. Any consumer that positions the worm against the wheel using the stored CD — notably `find_optimal_mesh_rotation` — would place them ~20 mm too close, producing kilo-mm³ interference instead of a clean mesh. The worm and wheel **Parts themselves are unaffected** (their geometry never used CD); only the stored metadata was wrong.

  Fixes:
  - `WormGear.__init__` now accepts an optional `ratio=` keyword. When provided, the stored `_assembly_params` carries the correct centre distance. When omitted (standalone worm with no wheel context), `_assembly_params` is set to `None` so downstream code raises a clear `AttributeError` instead of silently using a wrong value.
  - `WormGear.from_design(...)` and therefore `make_pair(...)` now pass the real ratio through.
  - `check_mesh` promotes "centre distance drift" from a warning to an **error** for cylindrical worms (globoid worms continue to allow `drift = -worm.throat_reduction_mm`).
  - New regression tests assert that `make_pair(...)`'s stored CD matches the geometric mean of pitch diameters across multiple module/ratio combinations, and that standalone `WormGear` has `_assembly_params is None`.

## 0.1.0 — 2026-05-23

### Breaking changes

The legacy geometry constructors are removed. Use the BD-style facade instead.

| Was (≤ 0.0.51) | Now (0.1.0) |
|---|---|
| `from wormgear import WormGeometry` | `from wormgear import WormGear` |
| `from wormgear import WheelGeometry` | `from wormgear import WormWheel` |
| `from wormgear import GloboidWormGeometry` | `from wormgear import make_pair; worm, wheel = make_pair(..., globoid=True)` |
| `from wormgear import VirtualHobbingWheelGeometry` | `from wormgear.advanced import virtual_hobbing` *(planned, #203)* |
| `WormGeometry(params, assembly_params, ...).build()` | `WormGear(module=..., num_starts=..., length=...)` (already a `build123d.Part`) |

Importing the old names now raises a helpful `ImportError` pointing at the migration.

### Added

- `WormGear` and `WormWheel` — `build123d.BasePartObject` subclasses; the new public API
- `make_pair(module, ratio, length, ...)` — guaranteed-matched pair in one call; supports `globoid=True`
- `check_mesh(worm, wheel, assembly)` — kinematic compatibility check, returns `MeshReport`
- `WormGear.from_design(design, length, ...)` and `WormWheel.from_design(design, ...)` — adapters for calculator output / loaded JSON
- Feature kwargs on the facade: `bore`, `keyway`, `ddcut`, `set_screw`, `hub`, `relief_groove`, `trim_to_min_engagement`

### Changed

- `wormgear-geometry` CLI internally uses the facade. Flag surface unchanged.
- README leads with the BD-style three-liner; calculator / CLI / web sections demoted to "Beyond the basics"
- PyPI metadata enriched: added `Topic :: Scientific/Engineering :: Mechanical`, `Topic :: Multimedia :: Graphics :: 3D Modeling`, additional keywords (`3d printing`, `helical`, `DIN 3975`, `mechanical engineering`, `mechanism`)
- Development status bumped from Alpha to Beta

### Removed

- Public `WormGeometry`, `WheelGeometry`, `GloboidWormGeometry`,
  `VirtualHobbingWheelGeometry` classes (replaced by the facade above)
- `DeprecationWarning` infrastructure that nudged users toward the facade in 0.0.51
- Tests that exclusively exercised the removed public surface (their coverage is replicated by `test_facade.py` and `test_golden_volumes.py`)

### Internal

- Phase 0 regression net (golden volumes, layering, determinism) re-pinned through the facade. Numeric pins unchanged — facade produces bit-identical geometry to the removed constructors.
- The four underlying geometry classes still exist with leading-underscore names (`_WormGeometry`, etc.) and are used internally by the facade. They are not part of the public API.

### Migration

See [#200](https://github.com/pzfreo/wormgear/issues/200) for the full migration discussion and rationale.

---

## 0.0.51 — earlier 2026

Final release of the legacy API. See `git log` for the full 0.0.x history.

Highlights of the 0.0.x line:
- DIN-3975 / DIN-3996 calculator with validation, efficiency, self-locking analysis
- Cylindrical and globoid worm geometry generation
- Helical and throated wheel generation
- Virtual hobbing for high-accuracy conjugate tooth profiles
- DIN-6885 keyways, set screws, bores, hubs
- ZA / ZK tooth profiles (CNC / 3D-printing)
- STEP / 3MF / STL export
- Web calculator at [wormgear.studio](https://wormgear.studio)
- Phase 0 regression net (`#192`) with golden volume tests
- BD-style facade (`WormGear`, `WormWheel`, `make_pair`, `check_mesh`) — initially added as additive surface in `#191`, became the only public API in 0.1.0
