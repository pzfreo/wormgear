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

What this does and does NOT verify
----------------------------------
Verified: tip (outside) diameter, root diameter, and (worm) length.

Not verified — always surfaced in ``report.warnings`` so a passing report is
never mistaken for full certification:

  * thread lead / lead angle (smooth swept surface; needs a cross-section),
  * tooth flank profile fidelity (involute / ZA / ZK curve, not just size),
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

# Notes appended to every report so callers know what a pass does NOT cover.
_UNVERIFIED_NOTES = (
    "thread lead / lead angle is not measured",
    "tooth flank profile fidelity (involute/ZA/ZK curve) is not measured",
    "this checks geometry-vs-calculation only, not that the calculation is "
    "correct per DIN-3975",
)


@dataclass(frozen=True)
class DimensionCheck:
    """One measured dimension compared against its spec value."""

    name: str
    measured_mm: float
    expected_mm: float
    tolerance_mm: float

    @property
    def deviation_mm(self) -> float:
        return self.measured_mm - self.expected_mm

    @property
    def ok(self) -> bool:
        return abs(self.deviation_mm) <= self.tolerance_mm

    def __str__(self) -> str:
        flag = "OK " if self.ok else "FAIL"
        return (
            f"[{flag}] {self.name}: measured {self.measured_mm:.4f} mm vs "
            f"spec {self.expected_mm:.4f} mm "
            f"(Δ {self.deviation_mm:+.4f} mm, tol ±{self.tolerance_mm} mm)"
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
    rs = [math.hypot(v.X, v.Y) for v in part.vertices()]
    if not rs:
        raise ValueError("part has no vertices to measure")
    return min(rs), max(rs)


def _outer_diameter(part: Any) -> float:
    return 2 * _radii(part)[1]


def _root_diameter(part: Any) -> float:
    return 2 * _radii(part)[0]


def _axial_length(part: Any) -> float:
    return float(part.bounding_box().size.Z)


def _finalise(
    kind: str, checks: List[DimensionCheck], warnings: List[str]
) -> GeometryReport:
    errors = [f"{c.name} out of tolerance: {c}" for c in checks if not c.ok]
    return GeometryReport(
        ok=not errors,
        kind=kind,
        checks=checks,
        errors=errors,
        warnings=[*warnings, *_UNVERIFIED_NOTES],
    )


# ---------------------------------------------------------------------------
# Public part-level checks
# ---------------------------------------------------------------------------


def check_worm_geometry(
    part: Any,
    params: Any,
    *,
    length: Optional[float] = None,
    tip_tol_mm: float = DEFAULT_TIP_TOL_MM,
    root_tol_mm: float = DEFAULT_ROOT_TOL_MM,
    length_tol_mm: float = DEFAULT_LENGTH_TOL_MM,
) -> GeometryReport:
    """Check a built worm ``part`` against its ``params`` spec.

    ``params`` is anything exposing ``tip_diameter_mm`` and ``root_diameter_mm``
    (a calculator ``WormParams`` or a duck-typed equivalent). If ``length`` is
    given, the worm's axial length is also checked; pass ``None`` to skip it
    (e.g. the spec does not carry a build length).
    """
    checks = [
        DimensionCheck(
            "tip_diameter", _outer_diameter(part), params.tip_diameter_mm, tip_tol_mm
        ),
        DimensionCheck(
            "root_diameter", _root_diameter(part), params.root_diameter_mm, root_tol_mm
        ),
    ]
    warnings: List[str] = []
    if length is not None:
        checks.append(
            DimensionCheck("length", _axial_length(part), length, length_tol_mm)
        )
    else:
        warnings.append("worm length not checked (no length provided)")
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
    checks = [
        DimensionCheck(
            "tip_diameter", _outer_diameter(part), params.tip_diameter_mm, tip_tol_mm
        )
    ]
    warnings: List[str] = []
    if throated:
        warnings.append(
            "throated wheel: nominal root_diameter not checked (root follows the "
            "worm envelope); throat diameter is not yet measured"
        )
    else:
        checks.append(
            DimensionCheck(
                "root_diameter",
                _root_diameter(part),
                params.root_diameter_mm,
                root_tol_mm,
            )
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
    worm_report = check_worm_geometry(
        worm_part,
        design.worm,
        length=worm_length,
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
        *(DimensionCheck(f"worm.{c.name}", c.measured_mm, c.expected_mm, c.tolerance_mm) for c in worm_report.checks),
        *(DimensionCheck(f"wheel.{c.name}", c.measured_mm, c.expected_mm, c.tolerance_mm) for c in wheel_report.checks),
    ]
    errors = list(worm_report.errors) + list(wheel_report.errors)
    warnings = ["worm: " + w for w in worm_report.warnings if not w.startswith(_UNVERIFIED_NOTES[0])]
    warnings += ["wheel: " + w for w in wheel_report.warnings if not w.startswith(_UNVERIFIED_NOTES[0])]

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
        warnings=[*warnings, *_UNVERIFIED_NOTES],
    )
