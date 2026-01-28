"""
Tests for web build script and package deployment.

These tests ensure the web interface has all necessary files for
WASM geometry generation in the browser.
"""

import subprocess
import json
from pathlib import Path
import pytest


# Define the repository root
REPO_ROOT = Path(__file__).parent.parent
WEB_DIR = REPO_ROOT / "web"
BUILD_SCRIPT = WEB_DIR / "build.sh"
SRC_DIR = REPO_ROOT / "src" / "wormgear"
EXAMPLES_DIR = REPO_ROOT / "examples"
DIST_DIR = REPO_ROOT / "dist"  # Build output directory


# List of all files that MUST be present after build for WASM to work
REQUIRED_WASM_FILES = [
    # Root package
    "wormgear/__init__.py",
    "wormgear/enums.py",
    # Core geometry (for generator)
    "wormgear/core/__init__.py",
    "wormgear/core/worm.py",
    "wormgear/core/wheel.py",
    "wormgear/core/features.py",
    "wormgear/core/globoid_worm.py",
    "wormgear/core/virtual_hobbing.py",
    "wormgear/core/bore_sizing.py",
    # IO
    "wormgear/io/__init__.py",
    "wormgear/io/loaders.py",
    "wormgear/io/schema.py",
    # Calculator (for web calculator - must not depend on core)
    "wormgear/calculator/__init__.py",
    "wormgear/calculator/core.py",
    "wormgear/calculator/validation.py",
    "wormgear/calculator/output.py",
    "wormgear/calculator/constants.py",
    "wormgear/calculator/js_bridge.py",
    "wormgear/calculator/json_schema.py",
]


def test_build_script_exists():
    """Build script should exist and be executable."""
    assert BUILD_SCRIPT.exists(), f"Build script not found at {BUILD_SCRIPT}"
    assert BUILD_SCRIPT.stat().st_mode & 0o111, "Build script is not executable"


def test_build_script_runs_successfully():
    """Build script should run without errors."""
    result = subprocess.run(
        [str(BUILD_SCRIPT)],
        cwd=WEB_DIR,
        capture_output=True,
        text=True
    )

    assert result.returncode == 0, f"Build script failed:\n{result.stderr}"
    assert "✅ Build complete!" in result.stdout, "Build didn't complete successfully"


def test_all_required_files_copied():
    """All required Python files should be copied to dist/wormgear/."""
    # Run build first
    subprocess.run([str(BUILD_SCRIPT)], cwd=WEB_DIR, check=True, capture_output=True)

    for required_file in REQUIRED_WASM_FILES:
        file_path = DIST_DIR / required_file
        assert file_path.exists(), f"Required file missing after build: {required_file}"
        assert file_path.stat().st_size > 0, f"File is empty: {required_file}"


def test_app_lazy_js_has_all_files():
    """generator-worker.js should list all required files in packageFiles array."""
    worker_path = WEB_DIR / "generator-worker.js"
    assert worker_path.exists(), "generator-worker.js not found"

    content = worker_path.read_text()

    # Check that packageFiles array exists
    assert "packageFiles = [" in content, "packageFiles array not found in generator-worker.js"

    # Check each required file is listed
    for required_file in REQUIRED_WASM_FILES:
        # Convert path to the format used in generator-worker.js
        assert required_file in content, (
            f"Required file '{required_file}' not listed in generator-worker.js packageFiles array"
        )


def test_no_pycache_in_output():
    """Build should not include __pycache__ directories."""
    # Run build first
    subprocess.run([str(BUILD_SCRIPT)], cwd=WEB_DIR, check=True, capture_output=True)

    dist_wormgear = DIST_DIR / "wormgear"
    if dist_wormgear.exists():
        pycache_dirs = list(dist_wormgear.rglob("__pycache__"))
        assert len(pycache_dirs) == 0, f"Found {len(pycache_dirs)} __pycache__ directories in output"


def test_no_pyc_files_in_output():
    """Build should not include .pyc files."""
    # Run build first
    subprocess.run([str(BUILD_SCRIPT)], cwd=WEB_DIR, check=True, capture_output=True)

    dist_wormgear = DIST_DIR / "wormgear"
    if dist_wormgear.exists():
        pyc_files = list(dist_wormgear.rglob("*.pyc"))
        assert len(pyc_files) == 0, f"Found {len(pyc_files)} .pyc files in output"


def test_source_files_exist():
    """Source files in src/wormgear should exist (needed by build script)."""
    for required_file in REQUIRED_WASM_FILES:
        src_file = SRC_DIR / required_file.replace("wormgear/", "")
        assert src_file.exists(), f"Source file missing: {src_file}"


def test_build_script_validation_list_matches():
    """Build script REQUIRED array should validate critical files."""
    build_script_content = BUILD_SCRIPT.read_text()

    # Build script uses REQUIRED=( array for validation
    assert "REQUIRED=(" in build_script_content, "REQUIRED array not found in build.sh"

    # Build script checks for critical files (not all files, just critical ones)
    # Verify the critical files are checked
    assert "dist/wormgear/__init__.py" in build_script_content, (
        "dist/wormgear/__init__.py not in build.sh REQUIRED validation list"
    )
    assert "dist/wormgear/calculator/core.py" in build_script_content, (
        "dist/wormgear/calculator/core.py not in build.sh REQUIRED validation list"
    )


def test_vercel_json_has_build_command():
    """vercel.json should have buildCommand configured."""
    vercel_json = REPO_ROOT / "vercel.json"
    assert vercel_json.exists(), "vercel.json not found"

    config = json.loads(vercel_json.read_text())
    assert "buildCommand" in config, "vercel.json missing buildCommand"
    assert "build.sh" in config["buildCommand"], "buildCommand doesn't reference build.sh"


def test_vercel_json_has_output_directory():
    """vercel.json should have outputDirectory configured."""
    vercel_json = REPO_ROOT / "vercel.json"
    config = json.loads(vercel_json.read_text())

    assert "outputDirectory" in config, "vercel.json missing outputDirectory"
    assert config["outputDirectory"] == "dist", "outputDirectory should be 'dist'"


def test_gitignore_excludes_generated_files():
    """Generated dist/ directory should be in .gitignore."""
    gitignore = REPO_ROOT / ".gitignore"
    assert gitignore.exists(), ".gitignore not found"

    content = gitignore.read_text()
    # Check that dist/ or web/wormgear/ build artifacts are ignored
    assert "dist/" in content or "web/wormgear/" in content, (
        "Generated files not in .gitignore - they should not be committed"
    )


def test_vercelignore_does_not_exclude_src():
    """src/ directory should NOT be in .vercelignore (needed by build script)."""
    vercelignore = REPO_ROOT / ".vercelignore"
    assert vercelignore.exists(), ".vercelignore not found"

    content = vercelignore.read_text()

    # Check that src/ is not excluded (or is commented out)
    lines = [line.strip() for line in content.split("\n") if line.strip()]
    active_ignores = [line for line in lines if not line.startswith("#")]

    assert "src/" not in active_ignores, (
        "src/ is in .vercelignore - build script needs access to src/ directory"
    )


@pytest.mark.skipif(
    not (REPO_ROOT / "dist" / "wormgear" / "__init__.py").exists(),
    reason="Build not run yet"
)
def test_package_version_accessible():
    """Package should have __version__ accessible after build."""
    init_file = DIST_DIR / "wormgear" / "__init__.py"
    content = init_file.read_text()

    assert "__version__" in content, "Package __init__.py should define __version__"


def test_index_html_loads_pyodide():
    """index.html should load Pyodide from CDN."""
    index_html = WEB_DIR / "index.html"
    assert index_html.exists(), "index.html not found"

    content = index_html.read_text()
    assert "pyodide.js" in content, "index.html doesn't load Pyodide"
    assert "cdn.jsdelivr.net/pyodide" in content, "Pyodide should be loaded from CDN"


def test_pyodide_version_consistency():
    """Pyodide version should be consistent between HTML and JavaScript."""
    index_html = WEB_DIR / "index.html"
    # After refactoring, Pyodide init is in modules/pyodide-init.js
    pyodide_init = WEB_DIR / "modules" / "pyodide-init.js"

    html_content = index_html.read_text()

    # Check if pyodide-init.js exists (after refactoring) or fall back to app.js
    if pyodide_init.exists():
        js_content = pyodide_init.read_text()
        js_file = "modules/pyodide-init.js"
    else:
        # Fallback for non-refactored version
        app_js = WEB_DIR / "app.js"
        js_content = app_js.read_text()
        js_file = "app.js"

    # Extract version from HTML (e.g., v0.29.0)
    import re
    html_match = re.search(r'pyodide/v([0-9.]+)/', html_content)
    js_matches = re.findall(r'pyodide/v([0-9.]+)/', js_content)

    assert html_match, "Pyodide version not found in index.html"
    assert js_matches, f"Pyodide version not found in {js_file}"

    html_version = html_match.group(1)

    # All JS versions should match HTML version
    for js_version in js_matches:
        assert js_version == html_version, (
            f"Pyodide version mismatch: HTML has {html_version}, "
            f"but {js_file} has {js_version}"
        )


def test_json_field_names_match_dataclass_params():
    """
    JSON field names should match Python model parameter names exactly.

    This prevents errors like 'throat_pitch_radius_mm' vs 'throat_curvature_radius_mm'.
    Works with both dataclasses and Pydantic BaseModel classes.
    """
    # Read loaders.py source directly to extract field names without importing build123d
    loaders_file = SRC_DIR / "io" / "loaders.py"
    assert loaders_file.exists(), f"loaders.py not found at {loaders_file}"

    loaders_content = loaders_file.read_text()

    # Extract field names from class definitions using regex
    import re

    def extract_model_fields(content: str, class_name: str) -> set:
        """Extract field names from a dataclass or Pydantic BaseModel definition."""
        # Try Pydantic BaseModel pattern first: class ClassName(BaseModel):
        class_pattern = rf'class {class_name}\(BaseModel\):.*?(?=\nclass \w+|def \w+\(|$)'
        match = re.search(class_pattern, content, re.DOTALL)

        # Fall back to dataclass pattern: @dataclass\nclass ClassName:
        if not match:
            class_pattern = rf'@dataclass\s+class {class_name}:.*?(?=@dataclass|class \w+:|def \w+|$)'
            match = re.search(class_pattern, content, re.DOTALL)

        if not match:
            return set()

        class_body = match.group(0)

        # Extract field names (lines with "field_name: type")
        # Handles optional types, defaults, Field(), and inline comments
        # Skip lines that are method definitions (@validator, def, etc.)
        field_pattern = r'^\s+(\w+):\s+(?:Optional\[)?[\w\[\],\s]+(?:\])?\s*(?:=.*?)?(?:#.*)?$'
        field_names = set()
        for line in class_body.split('\n'):
            # Skip comment-only lines, decorators, and method definitions
            stripped = line.strip()
            if stripped.startswith('#') or stripped.startswith('@') or stripped.startswith('def '):
                continue
            # Skip class Config blocks
            if stripped.startswith('class Config'):
                continue
            field_match = re.match(field_pattern, line)
            if field_match:
                field_names.add(field_match.group(1))

        return field_names

    # Get field names from models (works with both dataclass and Pydantic)
    worm_fields = extract_model_fields(loaders_content, "WormParams")
    wheel_fields = extract_model_fields(loaders_content, "WheelParams")
    assembly_fields = extract_model_fields(loaders_content, "AssemblyParams")

    assert len(worm_fields) > 0, "Failed to extract WormParams fields"
    assert len(wheel_fields) > 0, "Failed to extract WheelParams fields"
    assert len(assembly_fields) > 0, "Failed to extract AssemblyParams fields"

    # Find and load example JSON files
    json_files = list(EXAMPLES_DIR.glob("*.json"))
    if len(json_files) == 0:
        pytest.skip("No example JSON files found - validation not needed")

    errors = []

    for json_file in json_files:
        with open(json_file) as f:
            data = json.load(f)

        # Check worm section
        if "worm" in data:
            for key in data["worm"].keys():
                if key not in worm_fields:
                    errors.append(
                        f"{json_file.name}: worm.{key} not in WormParams model. "
                        f"Available fields: {sorted(worm_fields)}"
                    )

        # Check wheel section
        if "wheel" in data:
            for key in data["wheel"].keys():
                if key not in wheel_fields:
                    errors.append(
                        f"{json_file.name}: wheel.{key} not in WheelParams model. "
                        f"Available fields: {sorted(wheel_fields)}"
                    )

        # Check assembly section
        if "assembly" in data:
            for key in data["assembly"].keys():
                if key not in assembly_fields:
                    errors.append(
                        f"{json_file.name}: assembly.{key} not in AssemblyParams model. "
                        f"Available fields: {sorted(assembly_fields)}"
                    )

    if errors:
        error_msg = "JSON field name mismatches found:\n" + "\n".join(f"  - {e}" for e in errors)
        pytest.fail(error_msg)


def test_app_js_field_names_match():
    """
    Field names in app.js should match Python dataclass parameters.

    Specifically checks for known issues like 'throat_pitch_radius_mm' which should be
    'throat_curvature_radius_mm'.
    """
    app_js = WEB_DIR / "app.js"
    content = app_js.read_text()

    # Known incorrect field names that should NOT appear
    incorrect_fields = [
        "throat_pitch_radius_mm",  # Should be throat_curvature_radius_mm
    ]

    errors = []
    for incorrect_field in incorrect_fields:
        if incorrect_field in content:
            errors.append(
                f"app.js contains incorrect field name '{incorrect_field}'. "
                f"This field does not exist in WormParams dataclass."
            )

    # Check that correct field name is used instead
    if "throat_pitch_radius_mm" in content and "throat_curvature_radius_mm" not in content:
        errors.append(
            "app.js should use 'throat_curvature_radius_mm' not 'throat_pitch_radius_mm'"
        )

    if errors:
        error_msg = "Field name errors in app.js:\n" + "\n".join(f"  - {e}" for e in errors)
        pytest.fail(error_msg)


def test_pyodide_init_loads_all_calculator_files():
    """
    pyodide-init.js must load all Python files from wormgear/calculator/.

    This test catches cases where a new .py file is added to the calculator
    but not included in the file list in pyodide-init.js.
    """
    import re

    # Get all Python files in calculator directory
    calculator_dir = SRC_DIR / "calculator"
    actual_files = {f.name for f in calculator_dir.glob("*.py")}

    # Read pyodide-init.js and extract the calcFiles array
    pyodide_init = WEB_DIR / "modules" / "pyodide-init.js"
    content = pyodide_init.read_text()

    # Extract calcFiles array: const calcFiles = ['__init__.py', 'core.py', ...]
    match = re.search(r"const calcFiles = \[([^\]]+)\]", content)
    assert match, "Could not find calcFiles array in pyodide-init.js"

    # Parse the array
    files_str = match.group(1)
    listed_files = set(re.findall(r"'([^']+)'", files_str))

    # Check for missing files (files that exist but aren't loaded)
    missing = actual_files - listed_files
    # Exclude __pycache__ marker files and test files
    missing = {f for f in missing if not f.startswith('__pycache__') and not f.startswith('test_')}

    if missing:
        pytest.fail(
            f"pyodide-init.js is missing calculator files: {sorted(missing)}\n"
            f"Add them to the calcFiles array in pyodide-init.js"
        )


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v"])
