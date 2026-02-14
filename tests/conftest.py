"""
Pytest configuration and shared fixtures for wormgear-geometry tests.
"""

import json
import math
import pytest
from pathlib import Path


# ─── Raw design dicts (module-scoped for sharing) ────────────────────────


@pytest.fixture(scope="module")
def sample_design_7mm_module():
    """Module-scoped 7mm design dict (for geometry fixtures that build once)."""
    return _design_7mm()


@pytest.fixture(scope="module")
def sample_design_large_module():
    """Module-scoped large design dict (for geometry fixtures that build once)."""
    return _design_large()


# ─── Module-scoped typed params ──────────────────────────────────────────


@pytest.fixture(scope="module")
def worm_params_7mm(sample_design_7mm_module):
    """Module-scoped WormParams from 7mm design."""
    return _make_worm_params(sample_design_7mm_module)


@pytest.fixture(scope="module")
def wheel_params_7mm(sample_design_7mm_module):
    """Module-scoped WheelParams from 7mm design."""
    return _make_wheel_params(sample_design_7mm_module)


@pytest.fixture(scope="module")
def assembly_params_7mm(sample_design_7mm_module):
    """Module-scoped AssemblyParams from 7mm design."""
    return _make_assembly_params(sample_design_7mm_module)


@pytest.fixture(scope="module")
def worm_params_large(sample_design_large_module):
    """Module-scoped WormParams from large design."""
    return _make_worm_params(sample_design_large_module)


@pytest.fixture(scope="module")
def wheel_params_large(sample_design_large_module):
    """Module-scoped WheelParams from large design."""
    return _make_wheel_params(sample_design_large_module)


@pytest.fixture(scope="module")
def assembly_params_large(sample_design_large_module):
    """Module-scoped AssemblyParams from large design."""
    return _make_assembly_params(sample_design_large_module)


# ─── Module-scoped built geometry ────────────────────────────────────────


@pytest.fixture(scope="module")
def built_worm_7mm(worm_params_7mm, assembly_params_7mm):
    """Module-scoped built worm geometry (7mm design, 10mm length)."""
    from wormgear import WormGeometry
    geo = WormGeometry(
        params=worm_params_7mm,
        assembly_params=assembly_params_7mm,
        length=10.0,
        sections_per_turn=12,
    )
    return geo.build()


@pytest.fixture(scope="module")
def built_wheel_7mm(wheel_params_7mm, worm_params_7mm, assembly_params_7mm):
    """Module-scoped built wheel geometry (7mm design, 4mm face width)."""
    from wormgear import WheelGeometry
    geo = WheelGeometry(
        params=wheel_params_7mm,
        worm_params=worm_params_7mm,
        assembly_params=assembly_params_7mm,
        face_width=4.0,
    )
    return geo.build()


@pytest.fixture(scope="module")
def built_worm_and_wheel_7mm(built_worm_7mm, built_wheel_7mm):
    """Module-scoped worm+wheel pair (7mm design)."""
    return built_worm_7mm, built_wheel_7mm


@pytest.fixture(scope="module")
def built_worm_large(worm_params_large, assembly_params_large):
    """Module-scoped built worm geometry (large design)."""
    from wormgear import WormGeometry
    geo = WormGeometry(
        params=worm_params_large,
        assembly_params=assembly_params_large,
        length=30.0,
        sections_per_turn=12,
    )
    return geo.build()


@pytest.fixture(scope="module")
def built_wheel_large(wheel_params_large, worm_params_large, assembly_params_large):
    """Module-scoped built wheel geometry (large design)."""
    from wormgear import WheelGeometry
    geo = WheelGeometry(
        params=wheel_params_large,
        worm_params=worm_params_large,
        assembly_params=assembly_params_large,
        face_width=15.0,
    )
    return geo.build()


# ─── Helper functions (no pytest dependency) ──────────────────────────────


def _design_7mm():
    """Return raw 7mm design dict."""
    return {
        "worm": {
            "module_mm": 0.5,
            "num_starts": 1,
            "pitch_diameter_mm": 6.0,
            "tip_diameter_mm": 7.0,
            "root_diameter_mm": 4.75,
            "lead_mm": 1.571,
            "axial_pitch_mm": 1.571,
            "lead_angle_deg": 4.76,
            "addendum_mm": 0.5,
            "dedendum_mm": 0.625,
            "thread_thickness_mm": 0.685
        },
        "wheel": {
            "module_mm": 0.5,
            "num_teeth": 12,
            "pitch_diameter_mm": 6.0,
            "tip_diameter_mm": 7.3,
            "root_diameter_mm": 5.05,
            "throat_diameter_mm": 6.5,
            "helix_angle_deg": 85.24,
            "addendum_mm": 0.65,
            "dedendum_mm": 0.475
        },
        "assembly": {
            "centre_distance_mm": 6.0,
            "ratio": 12,
            "pressure_angle_deg": 25,
            "backlash_mm": 0.1,
            "hand": "right"
        },
        "performance": {
            "efficiency_estimate": 0.599,
            "self_locking": True
        },
        "validation": {
            "valid": True,
            "messages": []
        }
    }


def _design_large():
    """Return raw large design dict."""
    return {
        "worm": {
            "module_mm": 2.0,
            "num_starts": 2,
            "pitch_diameter_mm": 20.0,
            "tip_diameter_mm": 24.0,
            "root_diameter_mm": 15.0,
            "lead_mm": 12.566,
            "axial_pitch_mm": 6.283,
            "lead_angle_deg": 17.66,
            "addendum_mm": 2.0,
            "dedendum_mm": 2.5,
            "thread_thickness_mm": 2.74
        },
        "wheel": {
            "module_mm": 2.0,
            "num_teeth": 30,
            "pitch_diameter_mm": 60.0,
            "tip_diameter_mm": 64.0,
            "root_diameter_mm": 55.0,
            "throat_diameter_mm": 62.0,
            "helix_angle_deg": 72.34,
            "addendum_mm": 2.0,
            "dedendum_mm": 2.5
        },
        "assembly": {
            "centre_distance_mm": 40.0,
            "ratio": 15,
            "pressure_angle_deg": 20,
            "backlash_mm": 0.1,
            "hand": "right"
        },
        "performance": {
            "efficiency_estimate": 0.85,
            "self_locking": False
        },
        "validation": {
            "valid": True,
            "messages": []
        }
    }


def _make_worm_params(design_data):
    """Create WormParams from design dict."""
    from wormgear import WormParams
    w = design_data["worm"]
    return WormParams(
        module_mm=w["module_mm"],
        num_starts=w["num_starts"],
        pitch_diameter_mm=w["pitch_diameter_mm"],
        tip_diameter_mm=w["tip_diameter_mm"],
        root_diameter_mm=w["root_diameter_mm"],
        lead_mm=w["lead_mm"],
        axial_pitch_mm=w["module_mm"] * math.pi,
        lead_angle_deg=w["lead_angle_deg"],
        addendum_mm=w["addendum_mm"],
        dedendum_mm=w["dedendum_mm"],
        thread_thickness_mm=w["thread_thickness_mm"],
        hand=design_data.get("worm", {}).get("hand", design_data["assembly"].get("hand", "right")),
        profile_shift=0.0,
    )


def _make_wheel_params(design_data):
    """Create WheelParams from design dict."""
    from wormgear import WheelParams
    wh = design_data["wheel"]
    return WheelParams(
        module_mm=wh["module_mm"],
        num_teeth=wh["num_teeth"],
        pitch_diameter_mm=wh["pitch_diameter_mm"],
        tip_diameter_mm=wh["tip_diameter_mm"],
        root_diameter_mm=wh["root_diameter_mm"],
        throat_diameter_mm=wh["throat_diameter_mm"],
        helix_angle_deg=wh["helix_angle_deg"],
        addendum_mm=wh["addendum_mm"],
        dedendum_mm=wh["dedendum_mm"],
        profile_shift=0.0,
    )


def _make_assembly_params(design_data):
    """Create AssemblyParams from design dict."""
    from wormgear import AssemblyParams
    a = design_data["assembly"]
    return AssemblyParams(
        centre_distance_mm=a["centre_distance_mm"],
        pressure_angle_deg=a["pressure_angle_deg"],
        backlash_mm=a["backlash_mm"],
        hand=a["hand"],
        ratio=a["ratio"],
    )


# ─── Function-scoped fixtures (for tests that mutate or need fresh copies) ─


@pytest.fixture
def sample_design_7mm():
    """Sample 7mm worm gear design parameters."""
    return {
        "worm": {
            "module_mm": 0.5,
            "num_starts": 1,
            "pitch_diameter_mm": 6.0,
            "tip_diameter_mm": 7.0,
            "root_diameter_mm": 4.75,
            "lead_mm": 1.571,
            "axial_pitch_mm": 1.571,
            "lead_angle_deg": 4.76,
            "addendum_mm": 0.5,
            "dedendum_mm": 0.625,
            "thread_thickness_mm": 0.685
        },
        "wheel": {
            "module_mm": 0.5,
            "num_teeth": 12,
            "pitch_diameter_mm": 6.0,
            "tip_diameter_mm": 7.3,
            "root_diameter_mm": 5.05,
            "throat_diameter_mm": 6.5,
            "helix_angle_deg": 85.24,
            "addendum_mm": 0.65,
            "dedendum_mm": 0.475
        },
        "assembly": {
            "centre_distance_mm": 6.0,
            "ratio": 12,
            "pressure_angle_deg": 25,
            "backlash_mm": 0.1,
            "hand": "right"
        },
        "performance": {
            "efficiency_estimate": 0.599,
            "self_locking": True
        },
        "validation": {
            "valid": True,
            "messages": []
        }
    }


@pytest.fixture
def sample_design_large():
    """Larger worm gear design for testing different scales."""
    return {
        "worm": {
            "module_mm": 2.0,
            "num_starts": 2,
            "pitch_diameter_mm": 20.0,
            "tip_diameter_mm": 24.0,
            "root_diameter_mm": 15.0,
            "lead_mm": 12.566,
            "axial_pitch_mm": 6.283,
            "lead_angle_deg": 17.66,
            "addendum_mm": 2.0,
            "dedendum_mm": 2.5,
            "thread_thickness_mm": 2.74
        },
        "wheel": {
            "module_mm": 2.0,
            "num_teeth": 30,
            "pitch_diameter_mm": 60.0,
            "tip_diameter_mm": 64.0,
            "root_diameter_mm": 55.0,
            "throat_diameter_mm": 62.0,
            "helix_angle_deg": 72.34,
            "addendum_mm": 2.0,
            "dedendum_mm": 2.5
        },
        "assembly": {
            "centre_distance_mm": 40.0,
            "ratio": 15,
            "pressure_angle_deg": 20,
            "backlash_mm": 0.1,
            "hand": "right"
        },
        "performance": {
            "efficiency_estimate": 0.85,
            "self_locking": False
        },
        "validation": {
            "valid": True,
            "messages": []
        }
    }


@pytest.fixture
def sample_design_left_hand():
    """Left-hand worm gear design."""
    return {
        "worm": {
            "module_mm": 1.0,
            "num_starts": 1,
            "pitch_diameter_mm": 10.0,
            "tip_diameter_mm": 12.0,
            "root_diameter_mm": 7.5,
            "lead_mm": 3.142,
            "axial_pitch_mm": 3.142,
            "lead_angle_deg": 9.04,
            "addendum_mm": 1.0,
            "dedendum_mm": 1.25,
            "thread_thickness_mm": 1.37,
            "hand": "left"
        },
        "wheel": {
            "module_mm": 1.0,
            "num_teeth": 20,
            "pitch_diameter_mm": 20.0,
            "tip_diameter_mm": 22.0,
            "root_diameter_mm": 17.5,
            "throat_diameter_mm": 21.0,
            "helix_angle_deg": 80.96,
            "addendum_mm": 1.0,
            "dedendum_mm": 1.25
        },
        "assembly": {
            "centre_distance_mm": 15.0,
            "ratio": 20,
            "pressure_angle_deg": 20,
            "backlash_mm": 0.05,
            "hand": "left"
        },
        "performance": {
            "efficiency_estimate": 0.70,
            "self_locking": True
        },
        "validation": {
            "valid": True,
            "messages": []
        }
    }


@pytest.fixture
def temp_json_file(tmp_path, sample_design_7mm):
    """Create a temporary JSON file with sample design."""
    json_file = tmp_path / "test_design.json"
    with open(json_file, 'w') as f:
        json.dump(sample_design_7mm, f)
    return json_file


@pytest.fixture
def examples_dir():
    """Path to examples directory."""
    return Path(__file__).parent.parent / "examples"
