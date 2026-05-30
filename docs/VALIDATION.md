# Validation & Accuracy

This document explains how far wormgear's outputs are checked, *and where they
are not* — so a green result is never mistaken for a guarantee it doesn't make.

There are **three independent questions**, and they need different evidence:

1. **Does the geometry realise the calculation?** — the built 3D model's
   measurable dimensions match the calculator's numbers.
2. **Is the calculation itself correct?** — the calculator's DIN-3975 numbers
   match an outside authority, not just themselves.
3. **Is the geometry stable?** — a refactor or dependency bump doesn't silently
   change the shape.

Passing one says nothing about the others. The honest one-line summary:

> The geometry faithfully realises the computed design to well within machining
> tolerance, and the core calculation agrees with an external authority — but
> "fully certified against DIN-3975" is **not** claimed.

---

## 1. Geometry realises the calculation

Each built part can be measured and compared to the spec it was built from.

```python
from wormgear import make_pair, check_pair_geometry
from wormgear.calculator import design_from_module

worm, wheel = make_pair(module=2.0, ratio=30, length=40)
print(worm.validate())     # GeometryReport
print(wheel.validate())

design = design_from_module(module=2.0, ratio=30)
report = check_pair_geometry(worm, wheel, design, worm_length=40)   # incl. mesh
print("pass" if report.ok else "FAIL")
```

The CLI runs this by default and exits non-zero on a mismatch
(`wormgear design.json`; opt out with `--skip-validate`).

### What is verified

| Part | Checked | How |
|------|---------|-----|
| Worm | tip (outside) diameter | max radial distance from the axis (not bbox) |
| Worm | root diameter | min radial distance — skipped if a bore/keyway is present, or if the swept-thread topology doesn't expose the root |
| Worm | length | bounding-box Z extent |
| Worm | **thread lead** (1-start) | median tip-land spacing on the axial section |
| Worm | **flank angle** (ZA) | slanted-edge angle on the axial section = axial pressure angle |
| Wheel | tip (outside) diameter | max radial distance |
| Wheel | root diameter | min radial distance — skipped if a bore/keyway is present, or for throated wheels (root follows the worm envelope) |
| Pair | mesh interference | boolean-intersection at the design centre distance (on by default) |

Diameters are measured **radially from the axis**, not from the axis-aligned
bounding box, because a gear's bbox undershoots the tip diameter when no tooth
points along an axis.

Default tolerances are a few hundredths of a millimetre — one to two orders of
magnitude below typical manufacturing tolerances (CNC ~0.01–0.05 mm, FDM
~0.1–0.3 mm) — and are adjustable per call.

### What is NOT verified (and why)

Every report lists these in `report.warnings`, so a pass never reads as full
certification:

- **Multi-start worm lead** — the starts interleave on a single section plane,
  so the simple spacing math doesn't give the lead. Needs single-thread
  tracking; deferred ([#234]).
- **Wheel tooth flank profile** (involute / ZK curve) — we check the tooth
  *size* (tip/root) and count, not that the flank lies on the analytic curve.
- **ZK / ZI worm flank shape** — only the ZA straight-flank *angle* is checked.
- **Throated-wheel throat diameter** — the throat follows the worm envelope, not
  the nominal root.
- **Even-multi-start geometry near the symmetry plane** — measurements there are
  unreliable with planar sectioning; under review with mesh tools ([#240]).
- **Globoid / throated clearance constants** — a few fixed-mm clearances in
  those paths are unaudited ([#232]).

This catches *geometry vs calculation*. It does **not** certify the calculation
against DIN-3975 — that's question 2, and the design rules are a separate check
(`validate_design`).

### Bugs this layer caught

Building the suite found and fixed real geometry-generation bugs that volume
baselines alone had missed: a wheel root cut 0.3 mm deeper than spec
([#231](https://github.com/pzfreo/wormgear/issues/231)), and **1-start worms at
certain lengths generated as a smooth threadless cylinder**
([#239](https://github.com/pzfreo/wormgear/issues/239)) — which now either build
correctly or fail loudly.

---

## 2. Calculation correctness ([#229])

`tests/test_reference_validation.py` checks the calculator against outside
authorities, so a transcription/implementation error can't pass merely by being
self-consistent. Two tiers:

**Tier A — independent references.**
- A **textbook worked example** (Norton, *Machine Design*, Ch. 13 P-11):
  the calculator reproduces the hand-computed lead, lead angle, wheel diameter
  and centre distance.
- An **independent calculator** ([mechstream](https://www.mechstream.com/worm-gear-calculator/),
  a separate DIN-3975 implementation): reproduces our wheel geometry exactly,
  and confirms the same `0.25·m` bottom-clearance convention.

**Tier B — independent re-derivation.** The canonical worm-gear relationships
(axial pitch, lead, lead angle, wheel diameter, centre distance, addendum/
dedendum, efficiency `η = tanλ/tan(λ+ρ)`, and the self-locking boundary) written
out from first principles and compared across a parameter matrix. These catch
implementation bugs (wrong constant, transposed term, deg/rad slip).

### What is confirmed
Core worm + wheel geometry, lead angle (`atan(z₁/q)`), efficiency model, and the
0.25·m clearance convention all agree with the external references.

### Honest limit
This rests on **one textbook example + one independent tool + the textbook
formulas**. It is *not* a full DIN-3975 conformance proof — that needs the
standard document itself or a reference like KISSsoft. Adding more published
worked examples is the highest-leverage way to strengthen it.

### A correctness fix it produced
Self-locking was judged by a fixed `lead_angle < 6°` that ignored friction,
inconsistent with the efficiency model. It now uses the friction angle
`atan(μ/cos α)` — the same model as efficiency — and responds to the friction
coefficient ([#242](https://github.com/pzfreo/wormgear/issues/242)). Note static
self-locking can still be broken by vibration; treat results near the boundary
with margin.

---

## 3. Geometry stability (regression net)

Three suites pin the geometry against silent drift (see the Phase 0 net in
`CLAUDE.md`):

- `test_golden_volumes.py` — exact volume / bbox / face count for canonical
  designs.
- `test_geometry_determinism.py` — two builds of the same design are identical.
- `test_layering.py` — architectural import rules.

These catch *change relative to a baseline*. They cannot catch a baseline that
was itself wrong — which is exactly why layers 1 and 2 exist (both #231 and #239
had their broken state encoded as "golden" until the spec-based checks were
added).

---

## Profile shift

**wormgear supports profile shift** as an input applied to the **wheel**:

```python
design_from_module(module=2.0, ratio=30, profile_shift=0.3)
```

It modifies the wheel's tooth proportions exactly per the DIN profile-shift
formulas:

```
addendum  hₐ = m·(1 + x)
dedendum  h_f = m·(1.25 − x)
tip       dₐ₂ = m·(z₂ + 2 + 2x)
root      d_f₂ = m·(z₂ − 2.5 + 2x)
```

So for `x = 0.5`, `m = 2`, `z₂ = 30`: tip 66 mm, root 57 mm — matching the
standard and an independent calculator.

### Important: profile shift does **not** move the centre distance

There are **two distinct, both-valid uses** of profile shift on a worm wheel:

1. **Addendum modification at a fixed centre distance** — adjust tooth
   proportions (undercut avoidance, tooth strength). The centre distance stays
   `a = m·(q + z₂)/2`.
2. **Profile shift to *achieve* a non-standard centre distance** — fit a
   standard-module worm to a chosen `a`, where `a = m·(q + z₂)/2 + x·m`.

**wormgear currently implements use #1.** `profile_shift` changes the wheel's
tip/root diameters but the reported **centre distance does not change with `x`**
(it stays `(d₁ + d₂)/2`). This matches the basic-form references (e.g. RoyMech);
the `+x·m` coupling is the *other* convention (DIN "shift-to-centre-distance").

**Practical guidance:**
- Use `profile_shift` to tune tooth proportions; the axes stay where the
  zero-shift centre distance puts them.
- It is **not** currently a way to hit an arbitrary standard centre distance — a
  large non-zero shift grows the teeth without moving the axes, which changes
  the mesh depth. If you need shift-to-centre-distance behaviour, that's a known
  open design decision: [#245](https://github.com/pzfreo/wormgear/issues/245).

---

## Open validation items

| Issue | What |
|-------|------|
| [#234](https://github.com/pzfreo/wormgear/issues/234) | Multi-start worm lead; wheel involute/ZK flank verification |
| [#240](https://github.com/pzfreo/wormgear/issues/240) | Even-multi-start worm geometry near the symmetry plane (mesh-based re-examination) |
| [#245](https://github.com/pzfreo/wormgear/issues/245) | Profile-shift semantics: should it also move the centre distance? |
| [#232](https://github.com/pzfreo/wormgear/issues/232) | Audit non-capped clearance constants in throated/globoid paths |

[#229]: https://github.com/pzfreo/wormgear/issues/229
[#234]: https://github.com/pzfreo/wormgear/issues/234
[#240]: https://github.com/pzfreo/wormgear/issues/240
[#232]: https://github.com/pzfreo/wormgear/issues/232
