"""Validate that a built 3D model realises its engineering calculation (#230).

This is the customer-facing counterpart to the ``test_geometry_realizes_spec``
suite: given a *built* worm or wheel ``Part`` and the *spec* it should match
(the calculator's ``WormParams`` / ``WheelParams``), it measures the solid and
reports whether each dimension agrees with the calculation.

It answers the question *"does the geometry realise the calculation?"* — which
is distinct from *"is the calculation itself correct per DIN-3975?"* (that is
``validate_design`` / cross-validation, not this). A green report here means the
delivered model faithfully reproduces the computed design; it does **not**
certify the design against the standard.

Typical use::

    from wormgear import WormGear, check_worm_geometry

    worm = WormGear(module=2.0, num_starts=1, length=40)
    report = worm.validate()              # against its own computed spec
    assert report.ok

    # …or validate an imported/machined STEP against a saved design:
    from wormgear import load_design_json
    design = load_design_json("design.json")
    report = check_worm_geometry(imported_part, design.worm, length=40)

Measurement
-----------
Diameters are measured as twice the radial distance from the part axis (Z),
i.e. ``2 * max/min(hypot(x, y))`` over the solid's vertices — *not* the
axis-aligned bounding box, whose XY extent undershoots the tip diameter when no
tooth points along an axis. Length is the bbox Z extent.

The worm thread is additionally sectioned on its axial plane to recover the
realised **lead** (1-start worms; median tip-land spacing) and, for a ZA worm,
the **flank angle** (the slanted-edge angle = the axial pressure angle). See
:func:`_measure_worm_thread`.

What this does and does NOT verify
----------------------------------
Verified: tip (outside) diameter, root diameter, (worm) length, 1-start worm
thread **lead**, and ZA worm **flank angle**.

Not verified — always surfaced in ``report.warnings`` so a passing report is
never mistaken for full certification:

  * multi-start worm lead (the starts interleave on a single section plane;
    needs per-start analysis — #234),
  * wheel tooth flank profile fidelity (involute / ZA / ZK curve, not just size),
  * ZK / ZI worm flank shape (only the ZA straight-flank angle is checked),
  * throated-wheel throat diameter (follows the worm envelope, not nominal root),
  * that the calculation itself is correct per DIN-3975 (see ``validate_design``).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, List, Optional

from .mesh_alignment import find_optimal_mesh_rotation

__all__ = [
    "DimensionCheck",
    "GeometryReport",
    "check_worm_geometry",
    "check_wheel_geometry",
    "check_pair_geometry",
]

# Default tolerances (mm). Tip/length match to rounding; root to ~0.012 mm from
# facet discretisation. These bounds catch a real dimensional bug (the #231 root
# over-cut was 0.3 mm) while tolerating the facet noise floor, and sit one to two
# orders of magnitude below typical manufacturing tolerances (CNC ~0.01–0.05 mm,
# FDM ~0.1–0.3 mm).
DEFAULT_TIP_TOL_MM = 0.02
DEFAULT_ROOT_TOL_MM = 0.05
DEFAULT_LENGTH_TOL_MM = 0.02
# Lead is measured from the median tip-land spacing of the axial section (exact
# to rounding in testing); the bound catches a real lead error while tolerating
# facet noise.
DEFAULT_LEAD_TOL_MM = 0.05
# ZA flank angle in the axial section equals the axial pressure angle. Measured
# 20.0° for 1-start, ~20.07° for multi-start (helix effect), so 0.5° is ample.
DEFAULT_FLANK_TOL_DEG = 0.5

# Radial guard (mm) below the nominal root radius. A bore or keyway sits well
# inside the tooth root, separated from it by the rim (>= ~1 mm by construction),
# so if the smallest measured radius is more than this far below the nominal
# root, an internal feature is present and the naive min-radius would read the
# bore rather than the tooth root. The guard is larger than the root facet noise
# (~0.012 mm) and any tolerable root deviation, but well under the minimum rim,
# so it cleanly separates "deviant root" (still checked) from "bore present"
# (root check skipped). See #234 for measuring root through a bore.
_FEATURE_GUARD_MM = 0.3

# The one note added to every report: this verifies geometry against the
# calculation, not that the calculation itself is correct per DIN-3975 (#229).
_CALC_CAVEAT = (
    "this checks geometry-vs-calculation only, not that the calculation is "
    "correct per DIN-3975"
)


@dataclass(frozen=True)
class DimensionCheck:
    """One measured quantity compared against its spec value.

    ``unit`` is ``"mm"`` for diameters/length/lead and ``"deg"`` for the flank
    angle; the comparison and tolerance are unit-agnostic.
    """

    name: str
    measured: float
    expected: float
    tolerance: float
    unit: str = "mm"

    @property
    def deviation(self) -> float:
        return self.measured - self.expected

    @property
    def ok(self) -> bool:
        return abs(self.deviation) <= self.tolerance

    def __str__(self) -> str:
        flag = "OK " if self.ok else "FAIL"
        u = self.unit
        return (
            f"[{flag}] {self.name}: measured {self.measured:.4f} {u} vs "
            f"spec {self.expected:.4f} {u} "
            f"(Δ {self.deviation:+.4f} {u}, tol ±{self.tolerance} {u})"
        )


@dataclass(frozen=True)
class GeometryReport:
    """Verdict on whether a built part realises its calculated spec.

    ``ok`` is ``True`` iff every dimension check passed and (when a mesh check
    was run) the pair meshed within tolerance. ``warnings`` always lists what
    the report does *not* guarantee — never treat a pass as full certification.
    """

    ok: bool
    kind: str  # "worm" | "wheel" | "pair"
    checks: List[DimensionCheck] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def __str__(self) -> str:
        head = f"{self.kind} geometry: {'PASS' if self.ok else 'FAIL'}"
        lines = [head, *(f"  {c}" for c in self.checks)]
        for e in self.errors:
            lines.append(f"  ERROR: {e}")
        for w in self.warnings:
            lines.append(f"  note: {w}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Measurement
# ---------------------------------------------------------------------------


def _radii(part: Any) -> tuple[float, float]:
    """Return (min, max) radial distance from the Z axis in a single vertex pass.

    One traversal of ``part.vertices()`` (an OCC topology walk that is not free
    on a high-face-count gear) yields both the root and tip radii — callers
    must not re-traverse for each.
    """
    rs = [math.hypot(v.X, v.Y) for v in part.vertices()]
    if not rs:
        raise ValueError("part has no vertices to measure")
    return min(rs), max(rs)


def _axial_length(part: Any) -> float:
    return float(part.bounding_box().size.Z)


def _root_check(
    min_r: float, expected_root_mm: float, tol_mm: float
) -> tuple[Optional[DimensionCheck], Optional[str]]:
    """Build the root-diameter check, or skip it when a bore/keyway is present.

    Takes the already-measured minimum radius (see :func:`_radii`) so the
    vertices are walked once per part. Returns ``(check, None)`` for a solid
    part, or ``(None, warning)`` when an internal feature is detected — radial
    measurement cannot then isolate the tooth root from the bore wall, so the
    check is skipped rather than misread.
    """
    if min_r < expected_root_mm / 2 - _FEATURE_GUARD_MM:
        return None, (
            "root_diameter not checked: an internal feature (bore/keyway) is "
            "present, so the tooth root cannot be isolated from the bore by "
            "radial measurement"
        )
    return DimensionCheck("root_diameter", 2 * min_r, expected_root_mm, tol_mm), None


def _measure_worm_thread(
    part: Any, tip_r: float, root_r: float
) -> tuple[Optional[float], Optional[float]]:
    """Section the worm on its axial (XZ) plane and measure the thread.

    Returns ``(axial_pitch_mm, flank_angle_deg)`` (either may be ``None`` if it
    could not be recovered). Points are sampled *along the section edges* — not
    just their vertices — because a swept worm thread's B-rep can have very few
    vertices, but its edges always trace the full profile.

    * ``axial_pitch`` is the **median** spacing of the tip lands on the +X side.
      The median ignores the shorter truncated lands at the worm ends. For a
      1-start worm this equals the lead; multi-start lands interleave on a
      single section plane and do not give the lead cleanly (caller restricts
      the lead check to 1-start).
    * ``flank_angle`` is the median angle of the slanted flank edges from the
      radial axis — for a ZA worm this equals the axial pressure angle.
    """
    from build123d import Plane

    section = part.intersect(Plane.XZ)
    tip_z: List[float] = []
    flank_angles: List[float] = []
    span = tip_r - root_r
    for edge in section.edges():
        # Sample points along the edge for the tip-land detection (robust to a
        # vertex-poor B-rep).
        n = max(2, int(edge.length / 0.25))
        for i in range(n + 1):
            p = edge.position_at(i / n)
            if p.X > tip_r - 0.05:  # +X side, at the tip radius → a tip land
                tip_z.append(p.Z)
        # Flank angle from the straight ZA flank edges (endpoints suffice).
        vs = edge.vertices()
        if len(vs) == 2 and vs[0].X > 0 and vs[1].X > 0:
            dx = abs(vs[1].X - vs[0].X)
            dz = abs(vs[1].Z - vs[0].Z)
            if dx > 0.3 * span and dz > 0.01:  # spans a good part of root→tip
                flank_angles.append(math.degrees(math.atan2(dz, dx)))

    axial_pitch = None
    if tip_z:
        tip_z.sort()
        lands: List[List[float]] = []
        for z in tip_z:
            if not lands or z - lands[-1][-1] > 0.5:
                lands.append([z])
            else:
                lands[-1].append(z)
        centers = [sum(g) / len(g) for g in lands]
        if len(centers) >= 2:
            spacings = sorted(
                centers[i + 1] - centers[i] for i in range(len(centers) - 1)
            )
            axial_pitch = spacings[len(spacings) // 2]
    flank_angle = None
    if flank_angles:
        flank_angles.sort()
        flank_angle = flank_angles[len(flank_angles) // 2]
    return axial_pitch, flank_angle


def _finalise(
    kind: str, checks: List[DimensionCheck], warnings: List[str]
) -> GeometryReport:
    errors = [f"{c.name} out of tolerance: {c}" for c in checks if not c.ok]
    return GeometryReport(
        ok=not errors,
        kind=kind,
        checks=checks,
        errors=errors,
        warnings=[*warnings, _CALC_CAVEAT],
    )


# ---------------------------------------------------------------------------
# Public part-level checks
# ---------------------------------------------------------------------------


def check_worm_geometry(
    part: Any,
    params: Any,
    *,
    length: Optional[float] = None,
    pressure_angle_deg: Optional[float] = None,
    profile: Optional[str] = None,
    measure_thread: bool = True,
    tip_tol_mm: float = DEFAULT_TIP_TOL_MM,
    root_tol_mm: float = DEFAULT_ROOT_TOL_MM,
    length_tol_mm: float = DEFAULT_LENGTH_TOL_MM,
    lead_tol_mm: float = DEFAULT_LEAD_TOL_MM,
    flank_tol_deg: float = DEFAULT_FLANK_TOL_DEG,
) -> GeometryReport:
    """Check a built worm ``part`` against its ``params`` spec.

    ``params`` exposes ``tip_diameter_mm``, ``root_diameter_mm``, ``lead_mm``
    and ``num_starts`` (a calculator ``WormParams`` or a duck-typed equivalent).
    If ``length`` is given, the worm's axial length is also checked.

    When ``measure_thread`` is true the worm is sectioned on its axial plane to
    verify the realised **lead** (1-start worms only — multi-start lands
    interleave on a single section plane) and, for a ZA worm with a given
    ``pressure_angle_deg``, the **flank angle** (which equals the axial pressure
    angle). Sectioning is the costlier part, so pass ``measure_thread=False`` to
    skip it.
    """
    min_r, max_r = _radii(part)
    checks = [
        DimensionCheck("tip_diameter", 2 * max_r, params.tip_diameter_mm, tip_tol_mm),
    ]
    warnings: List[str] = []
    root_check, root_warning = _root_check(min_r, params.root_diameter_mm, root_tol_mm)
    if root_check is not None:
        checks.append(root_check)
    else:
        warnings.append(root_warning)  # type: ignore[arg-type]
    if length is not None:
        checks.append(
            DimensionCheck("length", _axial_length(part), length, length_tol_mm)
        )
    else:
        warnings.append("worm length not checked (no length provided)")

    if measure_thread:
        axial_pitch, flank_angle = _measure_worm_thread(part, max_r, min_r)
        num_starts = getattr(params, "num_starts", 1)
        if num_starts != 1:
            warnings.append(
                "lead not checked: multi-start lead measurement is not yet "
                "implemented (#234)"
            )
        elif axial_pitch is not None:
            checks.append(
                DimensionCheck("lead", axial_pitch, params.lead_mm, lead_tol_mm)
            )
        else:
            warnings.append(
                "lead not measured: could not section/identify thread crests"
            )
        _is_za = profile is not None and str(profile).upper() == "ZA"
        if _is_za and pressure_angle_deg is not None and flank_angle is not None:
            checks.append(
                DimensionCheck(
                    "flank_angle", flank_angle, pressure_angle_deg, flank_tol_deg,
                    unit="deg",
                )
            )
        elif pressure_angle_deg is None or profile is None:
            warnings.append(
                "flank angle not checked (needs pressure_angle_deg and profile)"
            )
        elif not _is_za:
            warnings.append(
                f"flank angle not checked: only implemented for ZA worms "
                f"(profile is {profile})"
            )
    else:
        warnings.append("thread lead / flank angle not measured (measure_thread=False)")

    return _finalise("worm", checks, warnings)


def check_wheel_geometry(
    part: Any,
    params: Any,
    *,
    throated: Optional[bool] = None,
    tip_tol_mm: float = DEFAULT_TIP_TOL_MM,
    root_tol_mm: float = DEFAULT_ROOT_TOL_MM,
) -> GeometryReport:
    """Check a built wheel ``part`` against its ``params`` spec.

    Checks tip diameter always, and root diameter for non-throated wheels.
    Throated wheels have a root that follows the worm envelope rather than the
    nominal root, so the nominal-root check is skipped and noted instead of
    asserted.

    ``throated`` says whether the *geometry* is throated. This is a build-time
    fact, not a spec field: the calculator always populates a notional
    ``throat_diameter_mm``, so it cannot be used to detect throating. When left
    as ``None`` it is read from ``part.throated`` if present (facade-built
    wheels expose it) and otherwise assumed ``False``; pass it explicitly for an
    imported throated wheel.
    """
    if throated is None:
        throated = bool(getattr(part, "throated", False))
    min_r, max_r = _radii(part)
    checks = [
        DimensionCheck("tip_diameter", 2 * max_r, params.tip_diameter_mm, tip_tol_mm)
    ]
    warnings: List[str] = []
    if throated:
        warnings.append(
            "throated wheel: nominal root_diameter not checked (root follows the "
            "worm envelope); throat diameter is not yet measured"
        )
    else:
        root_check, root_warning = _root_check(
            min_r, params.root_diameter_mm, root_tol_mm
        )
        if root_check is not None:
            checks.append(root_check)
        else:
            warnings.append(root_warning)  # type: ignore[arg-type]
    warnings.append(
        "wheel tooth flank profile (involute/ZA/ZK curve) is not measured"
    )
    return _finalise("wheel", checks, warnings)


def check_pair_geometry(
    worm_part: Any,
    wheel_part: Any,
    design: Any,
    *,
    worm_length: Optional[float] = None,
    wheel_throated: Optional[bool] = None,
    validate_mesh: bool = True,
    tip_tol_mm: float = DEFAULT_TIP_TOL_MM,
    root_tol_mm: float = DEFAULT_ROOT_TOL_MM,
    length_tol_mm: float = DEFAULT_LENGTH_TOL_MM,
) -> GeometryReport:
    """Validate a worm + wheel pair against ``design`` (worm, wheel, assembly).

    Runs the worm and wheel dimensional checks. By default it additionally
    builds a boolean intersection of the two solids at the design's centre
    distance and checks the pair meshes within a module-scaled tolerance (via
    :func:`find_optimal_mesh_rotation`). That mesh check is the slow part — it
    builds geometry boolean intersections — so pass ``validate_mesh=False`` to
    skip it when you only want the dimensional checks.
    """
    mfg = getattr(design, "manufacturing", None)
    worm_profile = getattr(mfg, "profile", None) if mfg is not None else None
    if worm_profile is not None and hasattr(worm_profile, "value"):
        worm_profile = worm_profile.value  # enum → "ZA"/"ZK"/...
    worm_report = check_worm_geometry(
        worm_part,
        design.worm,
        length=worm_length,
        pressure_angle_deg=design.assembly.pressure_angle_deg,
        profile=worm_profile,
        tip_tol_mm=tip_tol_mm,
        root_tol_mm=root_tol_mm,
        length_tol_mm=length_tol_mm,
    )
    wheel_report = check_wheel_geometry(
        wheel_part,
        design.wheel,
        throated=wheel_throated,
        tip_tol_mm=tip_tol_mm,
        root_tol_mm=root_tol_mm,
    )

    checks = [
        *(DimensionCheck(f"worm.{c.name}", c.measured, c.expected, c.tolerance, c.unit) for c in worm_report.checks),
        *(DimensionCheck(f"wheel.{c.name}", c.measured, c.expected, c.tolerance, c.unit) for c in wheel_report.checks),
    ]
    errors = list(worm_report.errors) + list(wheel_report.errors)
    # Sub-reports each carry the shared calc caveat; fold it in once below.
    warnings = ["worm: " + w for w in worm_report.warnings if w != _CALC_CAVEAT]
    warnings += ["wheel: " + w for w in wheel_report.warnings if w != _CALC_CAVEAT]

    if validate_mesh:
        centre_distance = design.assembly.centre_distance_mm
        result = find_optimal_mesh_rotation(
            wheel_part,
            worm_part,
            centre_distance,
            num_teeth=design.wheel.num_teeth,
            module_mm=design.worm.module_mm,
        )
        if not result.within_tolerance:
            errors.append(
                f"mesh interference {result.interference_volume_mm3:.3f} mm³ "
                f"exceeds tolerance {result.tolerance_mm3:.3f} mm³ "
                f"({result.mesh_quality}): {result.message}"
            )
        elif result.mesh_quality == "acceptable":
            warnings.append(
                f"mesh interference acceptable but non-zero "
                f"({result.interference_volume_mm3:.3f} mm³): {result.message}"
            )
    else:
        warnings.append("mesh interference not checked (pass validate_mesh=True)")

    return GeometryReport(
        ok=not errors,
        kind="pair",
        checks=checks,
        errors=errors,
        warnings=[*warnings, _CALC_CAVEAT],
    )
