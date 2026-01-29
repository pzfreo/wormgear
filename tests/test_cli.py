"""
Tests for the command-line interface.
"""

import json
import subprocess
import sys
import pytest
from pathlib import Path


class TestCLIEntryPoints:
    """Test that CLI entry points defined in pyproject.toml are importable."""

    def test_entry_point_importable(self):
        """Test that the CLI entry point module and function exist.

        This catches issues like pyproject.toml referencing non-existent modules.
        """
        from wormgear.cli.generate import main
        assert callable(main)

    def test_entry_point_via_subprocess(self):
        """Test entry point works when invoked as module."""
        result = subprocess.run(
            [sys.executable, "-m", "wormgear.cli.generate", "--help"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0


class TestCLIBasic:
    """Basic CLI tests."""

    def test_cli_help(self):
        """Test that --help works."""
        result = subprocess.run(
            [sys.executable, "-m", "wormgear.cli.generate", "--help"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert "wormgear-geometry" in result.stdout.lower() or "usage" in result.stdout.lower()

    def test_cli_missing_file(self):
        """Test error handling for missing input file."""
        result = subprocess.run(
            [sys.executable, "-m", "wormgear.cli.generate", "nonexistent.json", "--no-save"],
            capture_output=True,
            text=True
        )
        assert result.returncode != 0

    def test_cli_invalid_json(self, tmp_path):
        """Test error handling for invalid JSON."""
        invalid_file = tmp_path / "invalid.json"
        invalid_file.write_text("not valid json {")

        result = subprocess.run(
            [sys.executable, "-m", "wormgear.cli.generate", str(invalid_file), "--no-save"],
            capture_output=True,
            text=True
        )
        assert result.returncode != 0


class TestCLIGeneration:
    """Tests for geometry generation via CLI."""

    def test_cli_generate_both(self, temp_json_file, tmp_path):
        """Test generating both worm and wheel."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = subprocess.run(
            [
                sys.executable, "-m", "wormgear.cli.generate",
                str(temp_json_file),
                "-o", str(output_dir),
                "--worm-length", "10",
                "--sections", "12"
            ],
            capture_output=True,
            text=True,
            timeout=120
        )

        assert result.returncode == 0
        assert "Generating worm" in result.stdout
        assert "Generating wheel" in result.stdout

        # Check output files were created
        step_files = list(output_dir.glob("*.step"))
        assert len(step_files) == 2

    def test_cli_worm_only(self, temp_json_file, tmp_path):
        """Test generating only the worm."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = subprocess.run(
            [
                sys.executable, "-m", "wormgear.cli.generate",
                str(temp_json_file),
                "-o", str(output_dir),
                "--worm-only",
                "--worm-length", "10",
                "--sections", "12"
            ],
            capture_output=True,
            text=True,
            timeout=120
        )

        assert result.returncode == 0
        assert "Generating worm" in result.stdout
        assert "Generating wheel" not in result.stdout

        step_files = list(output_dir.glob("*.step"))
        assert len(step_files) == 1
        assert "worm" in step_files[0].name.lower()

    def test_cli_wheel_only(self, temp_json_file, tmp_path):
        """Test generating only the wheel."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = subprocess.run(
            [
                sys.executable, "-m", "wormgear.cli.generate",
                str(temp_json_file),
                "-o", str(output_dir),
                "--wheel-only"
            ],
            capture_output=True,
            text=True,
            timeout=120
        )

        assert result.returncode == 0
        assert "Generating wheel" in result.stdout
        assert "Generating worm" not in result.stdout

        step_files = list(output_dir.glob("*.step"))
        assert len(step_files) == 1
        assert "wheel" in step_files[0].name.lower()

    def test_cli_no_save(self, temp_json_file):
        """Test --no-save option doesn't create files."""
        result = subprocess.run(
            [
                sys.executable, "-m", "wormgear.cli.generate",
                str(temp_json_file),
                "--no-save",
                "--worm-length", "10",
                "--sections", "12"
            ],
            capture_output=True,
            text=True,
            timeout=120
        )

        assert result.returncode == 0
        # No STEP files should be created in current directory
        # (This is a weak test but validates the flag is accepted)

    def test_cli_custom_worm_length(self, temp_json_file, tmp_path):
        """Test custom worm length option."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = subprocess.run(
            [
                sys.executable, "-m", "wormgear.cli.generate",
                str(temp_json_file),
                "-o", str(output_dir),
                "--worm-only",
                "--worm-length", "25",
                "--sections", "12"
            ],
            capture_output=True,
            text=True,
            timeout=120
        )

        assert result.returncode == 0

    def test_cli_custom_wheel_width(self, temp_json_file, tmp_path):
        """Test custom wheel width option."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = subprocess.run(
            [
                sys.executable, "-m", "wormgear.cli.generate",
                str(temp_json_file),
                "-o", str(output_dir),
                "--wheel-only",
                "--wheel-width", "6"
            ],
            capture_output=True,
            text=True,
            timeout=120
        )

        assert result.returncode == 0

    @pytest.mark.slow
    def test_cli_custom_sections(self, temp_json_file, tmp_path):
        """Test custom sections per turn option.

        Marked as slow because high section counts (72) take >2 minutes.
        """
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        for sections in [8, 24, 72]:
            result = subprocess.run(
                [
                    sys.executable, "-m", "wormgear.cli.generate",
                    str(temp_json_file),
                    "-o", str(output_dir),
                    "--worm-only",
                    "--worm-length", "10",
                    "--sections", str(sections)
                ],
                capture_output=True,
                text=True,
                timeout=120
            )

            assert result.returncode == 0, f"Failed with sections={sections}"


class TestCLIOutput:
    """Tests for CLI output and reporting."""

    def test_cli_design_summary(self, temp_json_file):
        """Test that design summary is printed."""
        result = subprocess.run(
            [
                sys.executable, "-m", "wormgear.cli.generate",
                str(temp_json_file),
                "--no-save",
                "--worm-length", "10",
                "--sections", "12"
            ],
            capture_output=True,
            text=True,
            timeout=120
        )

        assert result.returncode == 0
        assert "Design summary" in result.stdout
        assert "Ratio" in result.stdout
        assert "Centre distance" in result.stdout
        assert "Pressure angle" in result.stdout

    def test_cli_volume_reported(self, temp_json_file):
        """Test that volumes are reported."""
        result = subprocess.run(
            [
                sys.executable, "-m", "wormgear.cli.generate",
                str(temp_json_file),
                "--no-save",
                "--worm-length", "10",
                "--sections", "12"
            ],
            capture_output=True,
            text=True,
            timeout=120
        )

        assert result.returncode == 0
        assert "Volume" in result.stdout
        assert "mm³" in result.stdout


class TestCLIWithExamples:
    """Tests using example JSON files."""

    def test_cli_with_7mm_example(self, examples_dir, tmp_path):
        """Test CLI with 7mm.json example."""
        example_file = examples_dir / "7mm.json"
        if not example_file.exists():
            pytest.skip("Example file not found")

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = subprocess.run(
            [
                sys.executable, "-m", "wormgear.cli.generate",
                str(example_file),
                "-o", str(output_dir),
                "--worm-length", "7",
                "--sections", "12"
            ],
            capture_output=True,
            text=True,
            timeout=120
        )

        assert result.returncode == 0
        step_files = list(output_dir.glob("*.step"))
        assert len(step_files) == 2


class TestCLIMeshAligned:
    """Tests for the --mesh-aligned option."""

    def test_cli_mesh_aligned_accepted(self, temp_json_file):
        """Test that --mesh-aligned option is accepted."""
        result = subprocess.run(
            [
                sys.executable, "-m", "wormgear.cli.generate",
                str(temp_json_file),
                "--no-save",
                "--mesh-aligned",
                "--worm-length", "10",
                "--sections", "12"
            ],
            capture_output=True,
            text=True,
            timeout=120
        )

        # Should succeed (view won't work without ocp_vscode but flag should be accepted)
        assert result.returncode == 0


class TestCLIGloboid:
    """Tests for globoid worm generation via CLI."""

    def test_cli_globoid_flag_accepted(self, temp_json_file):
        """Test that --globoid flag is accepted."""
        result = subprocess.run(
            [
                sys.executable, "-m", "wormgear.cli.generate",
                str(temp_json_file),
                "--no-save",
                "--globoid",
                "--worm-length", "10",
                "--sections", "12"
            ],
            capture_output=True,
            text=True,
            timeout=120
        )

        assert result.returncode == 0
        assert "globoid" in result.stdout.lower() or "hourglass" in result.stdout.lower()

    def test_cli_globoid_generates_files(self, temp_json_file, tmp_path):
        """Test that globoid flag generates STEP files."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = subprocess.run(
            [
                sys.executable, "-m", "wormgear.cli.generate",
                str(temp_json_file),
                "-o", str(output_dir),
                "--globoid",
                "--worm-length", "10",
                "--sections", "12"
            ],
            capture_output=True,
            text=True,
            timeout=120
        )

        assert result.returncode == 0
        step_files = list(output_dir.glob("*.step"))
        assert len(step_files) == 2  # Both worm and wheel

    def test_cli_globoid_worm_only(self, temp_json_file, tmp_path):
        """Test globoid worm generation with --worm-only."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = subprocess.run(
            [
                sys.executable, "-m", "wormgear.cli.generate",
                str(temp_json_file),
                "-o", str(output_dir),
                "--globoid",
                "--worm-only",
                "--worm-length", "10",
                "--sections", "12"
            ],
            capture_output=True,
            text=True,
            timeout=120
        )

        assert result.returncode == 0
        assert "Generating worm" in result.stdout
        assert "globoid" in result.stdout.lower() or "hourglass" in result.stdout.lower()

        step_files = list(output_dir.glob("*.step"))
        assert len(step_files) == 1

    def test_cli_globoid_with_features(self, temp_json_file, tmp_path):
        """Test globoid worm with bore and keyway features."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = subprocess.run(
            [
                sys.executable, "-m", "wormgear.cli.generate",
                str(temp_json_file),
                "-o", str(output_dir),
                "--globoid",
                "--worm-only",
                "--worm-bore", "6",
                "--worm-length", "10",
                "--sections", "12"
            ],
            capture_output=True,
            text=True,
            timeout=120
        )

        assert result.returncode == 0
        assert "bore" in result.stdout.lower()

    def test_cli_globoid_save_json(self, temp_json_file, tmp_path):
        """Test saving extended JSON with globoid worm type."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        json_output = tmp_path / "complete_design.json"

        result = subprocess.run(
            [
                sys.executable, "-m", "wormgear.cli.generate",
                str(temp_json_file),
                "-o", str(output_dir),
                "--globoid",
                "--worm-length", "12",
                "--save-json", str(json_output),
                "--sections", "12"
            ],
            capture_output=True,
            text=True,
            timeout=120
        )

        assert result.returncode == 0
        assert json_output.exists()

        # Check that worm_type is "globoid" in saved JSON
        with open(json_output, 'r') as f:
            data = json.load(f)

        assert "manufacturing" in data
        assert data["manufacturing"]["worm_type"] == "globoid"
        assert data["manufacturing"]["worm_length_mm"] == 12.0

    def test_cli_globoid_with_7mm_example(self, examples_dir, tmp_path):
        """Test globoid generation with 7mm.json example."""
        example_file = examples_dir / "7mm.json"
        if not example_file.exists():
            pytest.skip("Example file not found")

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = subprocess.run(
            [
                sys.executable, "-m", "wormgear.cli.generate",
                str(example_file),
                "-o", str(output_dir),
                "--globoid",
                "--worm-length", "12",
                "--sections", "12"
            ],
            capture_output=True,
            text=True,
            timeout=120
        )

        assert result.returncode == 0
        step_files = list(output_dir.glob("*.step"))
        assert len(step_files) == 2
