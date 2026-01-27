"""Tests to verify calculator works without geometry dependencies.

These tests ensure the calculator can be loaded and used in the web interface
(Pyodide) where build123d is not available. The calculator should never import
from wormgear.core which depends on build123d.
"""

import sys
import pytest


def test_calculator_imports_without_build123d():
    """Calculator should import without build123d installed.

    This simulates the web (Pyodide) environment where only the calculator
    is loaded, not the geometry modules.
    """
    # Save current module state
    saved_modules = dict(sys.modules)

    # Remove any cached imports of wormgear modules
    to_remove = [k for k in sys.modules if k.startswith('wormgear')]
    for key in to_remove:
        del sys.modules[key]

    # Block build123d import to simulate Pyodide environment
    class BlockBuild123d:
        def find_module(self, name, path=None):
            if name == 'build123d' or name.startswith('build123d.'):
                return self
            return None

        def load_module(self, name):
            raise ImportError(f"Simulating Pyodide: {name} not available")

    blocker = BlockBuild123d()
    sys.meta_path.insert(0, blocker)

    try:
        # These imports should work without build123d
        from wormgear.calculator import (
            design_from_module,
            validate_design,
            to_json,
            calculate_default_bore,
        )
        from wormgear.io import WormGearDesign, WormParams
        from wormgear.enums import Hand, WormProfile

        # Test basic calculation
        design = design_from_module(module=2.0, ratio=30)
        assert design is not None
        assert design.worm.module_mm == 2.0

        # Test validation
        result = validate_design(design)
        assert result is not None

        # Test JSON output
        json_str = to_json(design)
        assert '"module_mm": 2.0' in json_str

        # Test bore calculation
        bore, warning = calculate_default_bore(16.0, 11.0)
        assert bore == 4.0

    finally:
        # Restore module state
        sys.meta_path.remove(blocker)

        # Clean up and restore
        to_remove = [k for k in sys.modules if k.startswith('wormgear')]
        for key in to_remove:
            del sys.modules[key]

        # Restore previously loaded modules
        for key, mod in saved_modules.items():
            if key.startswith('wormgear'):
                sys.modules[key] = mod


def test_calculator_no_core_imports():
    """Verify calculator modules don't import from core.

    The calculator package should be completely independent of the core
    geometry package to work in the web interface.
    """
    from pathlib import Path
    import re

    calculator_dir = Path(__file__).parent.parent / "src" / "wormgear" / "calculator"

    forbidden_imports = [
        r'from\s+\.\.core\s+import',
        r'from\s+wormgear\.core\s+import',
        r'import\s+wormgear\.core',
    ]

    errors = []

    for py_file in calculator_dir.glob("*.py"):
        content = py_file.read_text()

        # Remove docstrings before checking (they may contain example imports)
        # Simple regex to remove triple-quoted strings
        content_no_docstrings = re.sub(r'"""[\s\S]*?"""', '', content)
        content_no_docstrings = re.sub(r"'''[\s\S]*?'''", '', content_no_docstrings)

        for pattern in forbidden_imports:
            if re.search(pattern, content_no_docstrings):
                errors.append(f"{py_file.name} contains forbidden import: {pattern}")

    if errors:
        pytest.fail("Calculator imports from core (breaks web interface):\n" + "\n".join(errors))


def test_js_bridge_standalone():
    """JS bridge should work without build123d.

    The js_bridge module is used in the web interface and must not
    depend on geometry modules.
    """
    # Same blocking technique as above
    saved_modules = dict(sys.modules)
    to_remove = [k for k in sys.modules if k.startswith('wormgear')]
    for key in to_remove:
        del sys.modules[key]

    class BlockBuild123d:
        def find_module(self, name, path=None):
            if name == 'build123d' or name.startswith('build123d.'):
                return self
            return None

        def load_module(self, name):
            raise ImportError(f"Simulating Pyodide: {name} not available")

    blocker = BlockBuild123d()
    sys.meta_path.insert(0, blocker)

    try:
        from wormgear.calculator.js_bridge import calculate

        # Test calculate function with valid input
        import json
        input_data = {
            "mode": "from-module",  # Note: hyphen, not underscore
            "module": 2.0,
            "ratio": 30,
            "pressure_angle": 20.0,
            "backlash": 0.0,
            "profile": "ZA",
        }

        result_json = calculate(json.dumps(input_data))
        result = json.loads(result_json)

        assert result.get("success") == True, f"JS bridge failed: {result.get('error')}"

    finally:
        sys.meta_path.remove(blocker)
        to_remove = [k for k in sys.modules if k.startswith('wormgear')]
        for key in to_remove:
            del sys.modules[key]
        for key, mod in saved_modules.items():
            if key.startswith('wormgear'):
                sys.modules[key] = mod
