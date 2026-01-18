"""
Pytest configuration and shared fixtures for wormgear-geometry tests.
"""

import json
import pytest
from pathlib import Path


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
