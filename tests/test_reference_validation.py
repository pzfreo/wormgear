"""Reference validation: is the *calculation* correct, independent of our code? (#229)

The other test suites check internal consistency (the calculator agrees with
itself) and that the geometry realises the calculation. This suite asks the
separate question: **are the calculator's numbers right against an outside
authority?** — so a transcription/implementation error in a DIN-3975 formula
can't pass merely because it is self-consistent.

Two tiers, labelled honestly:

* **Tier A — published worked examples.** Inputs and answers transcribed from a
  textbook where a human computed the result. Fully independent of our code.
  Currently one example (Norton); the value/version is cited inline. Adding more
  is the highest-leverage way to strengthen this suite (see the module TODO).

* **Tier B — independent re-derivation of the standard formulas.** The canonical
  worm-gear relationships (axial pitch, lead, lead angle, centre distance,
  efficiency, friction/self-locking boundary) written out *here* from first
  principles and compared to the calculator across a parameter matrix. These
  catch implementation bugs — a wrong constant, a transposed term, a
  radians/degrees slip. They do NOT prove conformance to DIN-3975 if the
  standard itself differs from these textbook formulas; that needs the standard
  document (paywalled) or an independent tool (e.g. MITcalc).

Calculation tests only — no geometry, so this runs in the fast suite.

TODO(#229): add more Tier-A published examples (Shigley / Dudley worked
problems, or one MITcalc run with the tool version recorded) to anchor more of
the parameter space against human/independent numbers rather than formulas.
"""

from __future__ import annotations

import math

import pytest

from wormgear.calculator.core import (
    calculate_centre_distance,
    calculate_wheel,
    calculate_worm,
    estimate_efficiency,
)

# ---------------------------------------------------------------------------
# Tier A — published worked examples (truly independent of our code)
# ---------------------------------------------------------------------------


def test_norton_machine_design_problem_11():
    """Norton, *Machine Design: An Integrated Approach* (4th ed.), Ch. 13, P-11.

    Given: a 1-start wormset with worm pitch diameter d = 40 mm, axial pitch
    p_x = 5 mm, ratio 82:1 (so the wheel has 82 teeth). The worked solution
    gives:

        lead        L  = 5 mm
        lead angle  λ  ≈ 2.29°
        wheel dia   d_G ≈ 130.5 mm
        centre dist a  ≈ 85.25 mm

    These were computed by hand in the text and re-verified here, so agreement
    is independent of our implementation.
    """
    module = 5.0 / math.pi  # module from the given 5 mm axial pitch
    worm = calculate_worm(module_mm=module, num_starts=1, pitch_diameter_mm=40.0)
    wheel = calculate_wheel(
        module_mm=module,
        num_teeth=82,
        worm_pitch_diameter_mm=40.0,
        worm_lead_angle_deg=worm["lead_angle_deg"],
    )
    cd = calculate_centre_distance(40.0, wheel["pitch_diameter_mm"])

    assert worm["lead_mm"] == pytest.approx(5.0, abs=0.01)
    assert worm["lead_angle_deg"] == pytest.approx(2.29, abs=0.02)
    assert wheel["pitch_diameter_mm"] == pytest.approx(130.5, abs=0.1)
    assert cd == pytest.approx(85.25, abs=0.1)


# ---------------------------------------------------------------------------
# Tier B — independent re-derivation of the standard worm-gear formulas
# ---------------------------------------------------------------------------
#
# References for the relationships used below (all mutually consistent):
#   axial pitch   p_x = π·m
#   lead          L   = z1·p_x = z1·π·m
#   lead angle    λ   = atan(L / (π·d1)) = atan(z1·m / d1)
#   wheel pitch   d2  = m·z2
#   centre dist   a   = (d1 + d2) / 2
#   addendum      h_a = m ;   dedendum h_f = (1 + c)·m   with clearance c = 0.25
#   efficiency    η   = tan(λ) / tan(λ + ρ),  ρ = atan(μ / cos α)
# (Shigley, *Mechanical Engineering Design*, worm-gearing chapter; DIN 3975.)

# (module, num_starts, worm_pitch_dia, num_teeth)
_MATRIX = [
    (2.0, 1, 28.0, 30),
    (1.0, 1, 16.0, 40),
    (2.0, 2, 36.0, 60),
    (1.5, 3, 30.0, 45),
    (0.5, 1, 8.0, 20),
    (3.0, 4, 60.0, 80),
]


@pytest.mark.parametrize("m, z1, d1, z2", _MATRIX)
def test_worm_dimensions_match_first_principles(m, z1, d1, z2):
    worm = calculate_worm(module_mm=m, num_starts=z1, pitch_diameter_mm=d1)

    expected_axial_pitch = math.pi * m
    expected_lead = z1 * math.pi * m
    expected_lead_angle = math.degrees(math.atan(expected_lead / (math.pi * d1)))
    expected_addendum = m
    expected_dedendum = 1.25 * m

    assert worm["axial_pitch_mm"] == pytest.approx(expected_axial_pitch, rel=1e-9)
    assert worm["lead_mm"] == pytest.approx(expected_lead, rel=1e-9)
    assert worm["lead_angle_deg"] == pytest.approx(expected_lead_angle, rel=1e-9)
    assert worm["addendum_mm"] == pytest.approx(expected_addendum, rel=1e-9)
    assert worm["dedendum_mm"] == pytest.approx(expected_dedendum, rel=1e-9)
    assert worm["tip_diameter_mm"] == pytest.approx(d1 + 2 * m, rel=1e-9)
    assert worm["root_diameter_mm"] == pytest.approx(d1 - 2.5 * m, rel=1e-9)


@pytest.mark.parametrize("m, z1, d1, z2", _MATRIX)
def test_wheel_and_centre_distance_match_first_principles(m, z1, d1, z2):
    worm = calculate_worm(module_mm=m, num_starts=z1, pitch_diameter_mm=d1)
    wheel = calculate_wheel(
        module_mm=m,
        num_teeth=z2,
        worm_pitch_diameter_mm=d1,
        worm_lead_angle_deg=worm["lead_angle_deg"],
    )
    cd = calculate_centre_distance(d1, wheel["pitch_diameter_mm"])

    assert wheel["pitch_diameter_mm"] == pytest.approx(m * z2, rel=1e-9)
    assert wheel["tip_diameter_mm"] == pytest.approx(m * z2 + 2 * m, rel=1e-9)
    assert wheel["root_diameter_mm"] == pytest.approx(m * z2 - 2.5 * m, rel=1e-9)
    # Worm lead angle + wheel helix angle are complementary for 90° shafts.
    assert worm["lead_angle_deg"] + wheel["helix_angle_deg"] == pytest.approx(90.0, abs=1e-9)
    assert cd == pytest.approx((d1 + m * z2) / 2, rel=1e-9)


@pytest.mark.parametrize(
    "lead_angle_deg, pressure_angle_deg, mu",
    [
        (5.0, 20.0, 0.05),
        (10.0, 20.0, 0.05),
        (20.0, 20.0, 0.03),
        (7.0, 14.5, 0.08),
        (30.0, 25.0, 0.10),
    ],
)
def test_efficiency_matches_textbook_formula(lead_angle_deg, pressure_angle_deg, mu):
    """η = tan(λ) / tan(λ + ρ), ρ = atan(μ / cos α) — re-derived independently."""
    gamma = math.radians(lead_angle_deg)
    alpha = math.radians(pressure_angle_deg)
    rho = math.atan(mu / math.cos(alpha))
    expected = math.tan(gamma) / math.tan(gamma + rho)

    got = estimate_efficiency(lead_angle_deg, pressure_angle_deg, friction_coefficient=mu)
    assert got == pytest.approx(expected, rel=1e-9)


def test_efficiency_is_monotonic_in_lead_angle_and_friction():
    """Physical sanity, independent of the exact formula: efficiency rises with
    lead angle and falls with friction."""
    base = estimate_efficiency(10.0, 20.0, friction_coefficient=0.05)
    assert estimate_efficiency(20.0, 20.0, friction_coefficient=0.05) > base
    assert estimate_efficiency(10.0, 20.0, friction_coefficient=0.10) < base
