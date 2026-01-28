"""
Tests that simulate the Pyodide web environment.

These tests verify that:
1. The calculator can be loaded with only the files listed in pyodide-init.js
2. The generator can be loaded with only the files listed in generator-worker.js
3. All imports work correctly in these minimal environments
4. The calculate() function works end-to-end

This catches issues like:
- Missing imports (e.g., Box not imported in globoid_worm.py)
- Circular dependencies
- Module structure issues when geometry isn't available
"""

import sys
import json
import pytest
from pathlib import Path
from typing import List
import tempfile
import shutil


REPO_ROOT = Path(__file__).parent.parent
SRC_DIR = REPO_ROOT / "src" / "wormgear"


# Files loaded by pyodide-init.js for the CALCULATOR
# (no build123d required, only calculation modules)
CALCULATOR_FILES = [
    "enums.py",
    "calculator/__init__.py",
    "calculator/core.py",
    "calculator/validation.py",
    "calculator/output.py",
    "calculator/constants.py",
    "calculator/js_bridge.py",
    "calculator/json_schema.py",
    "core/__init__.py",  # Only for bore_sizing import
    "core/bore_sizing.py",
    "io/__init__.py",
    "io/loaders.py",
    "io/schema.py",
]

# Files loaded by generator-worker.js for the GENERATOR
# (requires build123d, loads geometry modules)
GENERATOR_FILES = CALCULATOR_FILES + [
    "core/worm.py",
    "core/wheel.py",
    "core/features.py",
    "core/globoid_worm.py",
    "core/virtual_hobbing.py",
]


def create_minimal_package(temp_dir: Path, files: List[str]) -> Path:
    """Create a minimal wormgear package with only specified files."""
    pkg_dir = temp_dir / "wormgear"

    # Create directory structure
    for subdir in ["calculator", "core", "io", "cli"]:
        (pkg_dir / subdir).mkdir(parents=True, exist_ok=True)

    # Create minimal __init__.py for wormgear package
    (pkg_dir / "__init__.py").write_text('"""Wormgear - minimal for testing."""\n__version__ = "test"\n')

    # Copy specified files
    for file_path in files:
        src = SRC_DIR / file_path
        dst = pkg_dir / file_path
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.exists():
            shutil.copy(src, dst)
        else:
            pytest.fail(f"Source file not found: {src}")

    return temp_dir


class TestCalculatorEnvironment:
    """Test calculator imports work with minimal file set (no build123d)."""

    @pytest.fixture
    def calculator_env(self, tmp_path):
        """Create minimal calculator environment."""
        env_dir = create_minimal_package(tmp_path, CALCULATOR_FILES)

        # Save original sys.path and modules
        original_path = sys.path.copy()
        original_modules = {k: v for k, v in sys.modules.items() if k.startswith("wormgear")}

        # Remove any existing wormgear imports
        for mod in list(sys.modules.keys()):
            if mod.startswith("wormgear"):
                del sys.modules[mod]

        # Add temp dir to path
        sys.path.insert(0, str(env_dir))

        yield env_dir

        # Restore original state
        sys.path = original_path
        for mod in list(sys.modules.keys()):
            if mod.startswith("wormgear"):
                del sys.modules[mod]
        sys.modules.update(original_modules)

    def test_calculator_imports_work(self, calculator_env):
        """Verify all calculator imports work without build123d."""
        # This should not raise ImportError
        from wormgear.calculator.js_bridge import calculate
        from wormgear.calculator import (
            calculate_design_from_module,
            validate_design,
            to_json,
        )
        from wormgear.enums import Hand, WormProfile, WormType
        from wormgear.core.bore_sizing import calculate_default_bore

        # Verify the functions exist
        assert callable(calculate)
        assert callable(calculate_design_from_module)
        assert callable(validate_design)
        assert callable(to_json)
        assert callable(calculate_default_bore)

    def test_calculate_function_works(self, calculator_env):
        """Verify the calculate() function returns valid output."""
        from wormgear.calculator.js_bridge import calculate

        input_data = {
            "mode": "from-module",
            "module": 2.0,
            "ratio": 30,
            "pressure_angle": 20.0,
            "num_starts": 1,
            "hand": "right",
            "profile": "ZA",
            "worm_type": "cylindrical",
        }

        result_json = calculate(json.dumps(input_data))
        result = json.loads(result_json)

        assert result["success"] is True
        assert result["error"] is None
        assert result["design_json"] is not None
        assert result["valid"] is True

    def test_bore_sizing_available_without_geometry(self, calculator_env):
        """Verify bore_sizing works without full geometry modules."""
        from wormgear.core.bore_sizing import calculate_default_bore

        # Calculate bore for a worm
        diameter, has_warning = calculate_default_bore(
            pitch_diameter=16.0,
            root_diameter=11.0
        )

        assert diameter is not None
        assert isinstance(diameter, float)
        assert isinstance(has_warning, bool)


@pytest.mark.slow
class TestGeneratorEnvironment:
    """Test generator imports work with full file set (requires build123d).

    These tests are marked slow because they involve importing build123d
    which takes significant time. Skip with: pytest -m "not slow"
    """

    @pytest.fixture
    def generator_env(self, tmp_path):
        """Create minimal generator environment."""
        # Skip if build123d not available
        try:
            import build123d
        except ImportError:
            pytest.skip("build123d not available")

        env_dir = create_minimal_package(tmp_path, GENERATOR_FILES)

        # Save original sys.path and modules
        original_path = sys.path.copy()
        original_modules = {k: v for k, v in sys.modules.items() if k.startswith("wormgear")}

        # Remove any existing wormgear imports
        for mod in list(sys.modules.keys()):
            if mod.startswith("wormgear"):
                del sys.modules[mod]

        # Add temp dir to path
        sys.path.insert(0, str(env_dir))

        yield env_dir

        # Restore original state
        sys.path = original_path
        for mod in list(sys.modules.keys()):
            if mod.startswith("wormgear"):
                del sys.modules[mod]
        sys.modules.update(original_modules)

    def test_geometry_imports_work(self, generator_env):
        """Verify all geometry imports work with build123d."""
        from wormgear.core import (
            WormGeometry,
            WheelGeometry,
            GloboidWormGeometry,
            VirtualHobbingWheelGeometry,
            BoreFeature,
            KeywayFeature,
            DDCutFeature,
            calculate_default_bore,
        )

        # Verify the classes/functions exist
        assert WormGeometry is not None
        assert WheelGeometry is not None
        assert GloboidWormGeometry is not None
        assert VirtualHobbingWheelGeometry is not None
        assert BoreFeature is not None
        assert KeywayFeature is not None
        assert DDCutFeature is not None
        assert callable(calculate_default_bore)

    def test_generator_worker_imports_match_python(self, generator_env):
        """Verify the imports in generator-worker.js can be satisfied."""
        # This is the import statement from generator-worker.js
        from wormgear.core import (
            WormGeometry,
            WheelGeometry,
            GloboidWormGeometry,
            VirtualHobbingWheelGeometry,
            BoreFeature,
            KeywayFeature,
            DDCutFeature,
            calculate_default_bore,
        )
        from wormgear.io import WormParams, WheelParams, AssemblyParams

        # These should all be importable
        assert WormGeometry is not None
        assert WormParams is not None


class TestFileListConsistency:
    """Test that file lists in JS match what Python needs."""

    def test_pyodide_init_files_exist(self):
        """All files listed in pyodide-init.js should exist."""
        for file_path in CALCULATOR_FILES:
            src = SRC_DIR / file_path
            assert src.exists(), f"File listed in pyodide-init.js not found: {file_path}"

    def test_generator_worker_files_exist(self):
        """All files listed in generator-worker.js should exist."""
        for file_path in GENERATOR_FILES:
            src = SRC_DIR / file_path
            assert src.exists(), f"File listed in generator-worker.js not found: {file_path}"

    def test_no_missing_imports_in_calculator(self):
        """Check that calculator modules don't import unavailable modules."""
        # Read all calculator files and check for problematic imports
        problematic_imports = []

        for file_path in CALCULATOR_FILES:
            if file_path.startswith("core/") and file_path != "core/__init__.py" and file_path != "core/bore_sizing.py":
                continue  # Skip core geometry files for calculator check

            src = SRC_DIR / file_path
            if src.exists():
                content = src.read_text()

                # Check for imports that would fail in calculator (no build123d)
                if "from build123d" in content or "import build123d" in content:
                    # Except for core modules which are expected to have this
                    if not file_path.startswith("core/"):
                        problematic_imports.append(f"{file_path}: imports build123d directly")

        assert len(problematic_imports) == 0, f"Problematic imports found:\n" + "\n".join(problematic_imports)
