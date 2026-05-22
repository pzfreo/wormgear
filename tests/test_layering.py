"""Layer-import enforcement tests (Phase 0 regression net).

These tests enforce the architectural layering rules documented in CLAUDE.md.
Without them, the rules are documentation only — easy to violate by accident,
and the consequences (calculator no longer runs in Pyodide / browser) only
surface when the web calculator breaks.

Rules enforced:

  1. ``wormgear.calculator`` MUST NOT import from ``wormgear.core`` (geometry)
     at module scope, except for the documented ``core.bore_sizing`` exception
     (pure-Python helper colocated with core but has no build123d dependency).
  2. ``wormgear.core`` MUST NOT import from ``wormgear.calculator`` at module
     scope.
  3. ``wormgear.io`` MUST NOT import from ``wormgear.core`` at module scope
     (same ``bore_sizing`` exception applies).
  4. ``wormgear.calculator`` MUST work without ``build123d`` installed
     (the Pyodide story for wormgear.studio).
  5. ``wormgear.calculator.js_bridge`` MUST work without ``build123d``.

The static checks deliberately allow function-level (lazy) imports — those
are the architecturally correct pattern for optional/conditional features,
and they don't break the Pyodide story because the function is never called
in environments where the imported module is unavailable.

Subsumes the earlier tests/test_calculator_standalone.py.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).parent.parent
SRC_ROOT = REPO_ROOT / "src" / "wormgear"


def _python_files(*subdirs: str) -> list[Path]:
    """Return all .py files in src/wormgear/<subdir>/ (recursively)."""
    files: list[Path] = []
    for sub in subdirs:
        root = SRC_ROOT / sub
        if root.is_dir():
            files.extend(root.rglob("*.py"))
    return files


def _strip_strings_and_comments(source: str) -> str:
    """Remove triple-quoted strings and # comments before grepping for imports.

    Docstrings sometimes contain example imports that would otherwise create
    false positives. Single-line ``#`` comments are also stripped because a
    forbidden import inside a comment is not a real violation.
    """
    # Strip triple-quoted strings (both forms)
    source = re.sub(r'"""[\s\S]*?"""', "", source)
    source = re.sub(r"'''[\s\S]*?'''", "", source)
    # Strip line comments
    source = re.sub(r"#[^\n]*", "", source)
    return source


def _assert_no_module_level_imports(
    files: list[Path],
    forbidden_patterns: list[str],
    target: str,
    allowed_submodules: tuple[str, ...] = (),
) -> None:
    """Assert that none of ``files`` has module-level imports matching ``forbidden_patterns``.

    Patterns are matched with ``re.MULTILINE`` against the start of a line so
    that function-level (indented) imports — the correct pattern for lazy /
    conditional dependencies — are not flagged.

    ``allowed_submodules`` lists submodule names (e.g. ``"bore_sizing"``) that
    are documented exceptions and may be imported despite the layer rule.
    """
    violations: list[str] = []
    for py_file in files:
        cleaned = _strip_strings_and_comments(py_file.read_text())
        for pattern in forbidden_patterns:
            for match in re.finditer(pattern, cleaned, flags=re.MULTILINE):
                # Skip the documented exceptions
                line_start = match.start()
                line_end = cleaned.find("\n", line_start)
                if line_end == -1:
                    line_end = len(cleaned)
                line = cleaned[line_start:line_end]
                if any(allowed in line for allowed in allowed_submodules):
                    continue
                rel = py_file.relative_to(REPO_ROOT)
                violations.append(f"  {rel}: {line.strip()}")
    if violations:
        pytest.fail(
            f"Layer violation: code in this layer must not import {target} "
            f"at module scope.\n" + "\n".join(violations)
        )


def _run_python_without_build123d(code: str) -> subprocess.CompletedProcess:
    """Run ``code`` in a subprocess that cannot import ``build123d``.

    Uses a meta-path import hook to simulate the Pyodide environment where
    only pure-Python wheels are available. Runs in a fresh interpreter so
    nothing from this test process leaks in.
    """
    bootstrap = """
import sys

class _BlockBuild123d:
    def find_spec(self, name, path=None, target=None):
        if name == 'build123d' or name.startswith('build123d.'):
            raise ImportError(
                f"Simulated Pyodide environment: {name} unavailable"
            )
        return None

sys.meta_path.insert(0, _BlockBuild123d())
"""
    return subprocess.run(
        [sys.executable, "-c", bootstrap + code],
        capture_output=True,
        text=True,
        timeout=30,
    )


# ---------------------------------------------------------------------------
# Rule 1: calculator does not import geometry
# ---------------------------------------------------------------------------


# Documented architectural exception:
#
#   ``wormgear.core.bore_sizing`` is a pure-Python helper (no build123d
#   dependency) that happens to live under ``core/`` for historical reasons.
#   It is the single sanctioned cross-layer import. Both calculator and io
#   may import from it at module scope.
#
# If you find yourself wanting to add a second exception, that is a signal
# to either (a) move the helper out of the layer it logically belongs to,
# or (b) reconsider the layer boundary.
BORE_SIZING_EXCEPTION = ("bore_sizing",)


class TestCalculatorDoesNotImportGeometry:
    """The calculator must remain independent of the geometry layer."""

    FORBIDDEN = [
        r"^from\s+\.\.core\s+import",
        r"^from\s+\.\.core(\.|\s)",
        r"^from\s+wormgear\.core\s+import",
        r"^from\s+wormgear\.core\.",
        r"^import\s+wormgear\.core\b",
    ]

    def test_calculator_modules_have_no_core_imports(self):
        """Static check: no calculator file imports core at module scope."""
        _assert_no_module_level_imports(
            _python_files("calculator"),
            self.FORBIDDEN,
            target="wormgear.core (geometry)",
            allowed_submodules=BORE_SIZING_EXCEPTION,
        )


# ---------------------------------------------------------------------------
# Rule 2: geometry does not import calculator
# ---------------------------------------------------------------------------


class TestGeometryDoesNotImportCalculator:
    """The geometry layer must remain independent of the calculator."""

    FORBIDDEN = [
        r"^from\s+\.\.calculator\s+import",
        r"^from\s+\.\.calculator(\.|\s)",
        r"^from\s+wormgear\.calculator\s+import",
        r"^from\s+wormgear\.calculator\.",
        r"^import\s+wormgear\.calculator\b",
    ]

    def test_geometry_modules_have_no_calculator_imports(self):
        """Static check: no core/geometry file imports calculator at module scope."""
        _assert_no_module_level_imports(
            _python_files("core"),
            self.FORBIDDEN,
            target="wormgear.calculator",
        )


# ---------------------------------------------------------------------------
# Rule 3: io does not import geometry
# ---------------------------------------------------------------------------


class TestIoDoesNotImportGeometry:
    """The IO layer (Pydantic models + JSON) must not pull in geometry."""

    FORBIDDEN = [
        r"^from\s+\.\.core\s+import",
        r"^from\s+\.\.core(\.|\s)",
        r"^from\s+wormgear\.core\s+import",
        r"^from\s+wormgear\.core\.",
        r"^import\s+wormgear\.core\b",
    ]

    def test_io_modules_have_no_core_imports(self):
        """Static check: no io file imports core at module scope."""
        _assert_no_module_level_imports(
            _python_files("io"),
            self.FORBIDDEN,
            target="wormgear.core (geometry)",
            allowed_submodules=BORE_SIZING_EXCEPTION,
        )


# ---------------------------------------------------------------------------
# Rule 4 & 5: calculator + js_bridge work without build123d (Pyodide story)
# ---------------------------------------------------------------------------


class TestCalculatorRunsWithoutBuild123d:
    """The calculator MUST be importable and usable without build123d.

    This is the load-bearing contract for the web calculator at
    wormgear.studio, which runs in Pyodide where build123d is unavailable.
    """

    def test_calculator_imports_without_build123d(self):
        """Calculator package + IO + enums all import cleanly."""
        result = _run_python_without_build123d(
            "from wormgear.calculator import (\n"
            "    design_from_module, validate_design, to_json,\n"
            "    calculate_default_bore,\n"
            ")\n"
            "from wormgear.io import WormGearDesign, WormParams\n"
            "from wormgear.enums import Hand, WormProfile\n"
            "print('OK')\n"
        )
        assert result.returncode == 0, (
            f"Calculator failed to import without build123d.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
        assert "OK" in result.stdout

    def test_calculate_function_works_without_build123d(self):
        """End-to-end: calculate, validate, serialize, all without build123d."""
        result = _run_python_without_build123d(
            "from wormgear.calculator import (\n"
            "    design_from_module, validate_design, to_json,\n"
            ")\n"
            "design = design_from_module(module=2.0, ratio=30)\n"
            "assert design.worm.module_mm == 2.0\n"
            "v = validate_design(design)\n"
            "assert v is not None\n"
            "j = to_json(design)\n"
            "assert '\"module_mm\": 2.0' in j\n"
            "print('OK')\n"
        )
        assert result.returncode == 0, (
            f"Calculator pipeline failed without build123d.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
        assert "OK" in result.stdout

    def test_bore_sizing_available_without_build123d(self):
        """``calculate_default_bore`` is in core but build123d-free; verify it works."""
        result = _run_python_without_build123d(
            "from wormgear.calculator import calculate_default_bore\n"
            "bore, warning = calculate_default_bore(16.0, 11.0)\n"
            "assert bore == 4.0\n"
            "print('OK')\n"
        )
        assert result.returncode == 0, (
            f"calculate_default_bore failed without build123d.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
        assert "OK" in result.stdout

    def test_js_bridge_calculate_works_without_build123d(self):
        """JS bridge handles a from-module call without build123d."""
        result = _run_python_without_build123d(
            "import json\n"
            "from wormgear.calculator.js_bridge import calculate\n"
            "payload = json.dumps({\n"
            "    'mode': 'from-module',\n"
            "    'module': 2.0,\n"
            "    'ratio': 30,\n"
            "    'pressure_angle': 20.0,\n"
            "    'backlash': 0.0,\n"
            "    'profile': 'ZA',\n"
            "})\n"
            "out = json.loads(calculate(payload))\n"
            "assert out.get('success') is True, out.get('error')\n"
            "print('OK')\n"
        )
        assert result.returncode == 0, (
            f"JS bridge failed without build123d.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
        assert "OK" in result.stdout
