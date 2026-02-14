"""Tests for exception handling in CLI and core modules.

Phase 2 of tech debt cleanup: verify narrowed exception handlers
behave correctly for specific error types.
"""

import subprocess
from unittest.mock import patch, MagicMock


class TestGetVersionString:
    """Tests for cli.generate.get_version_string exception handling."""

    def test_package_not_found(self):
        """PackageNotFoundError returns '0.0.0' fallback."""
        from importlib.metadata import PackageNotFoundError

        with patch(
            "importlib.metadata.version",
            side_effect=PackageNotFoundError("wormgear"),
        ):
            from wormgear.cli.generate import get_version_string

            version = get_version_string()
            assert version == "0.0.0" or version.startswith("0.0.0")

    def test_git_not_available(self):
        """FileNotFoundError (git not installed) doesn't crash."""
        with patch(
            "subprocess.run", side_effect=FileNotFoundError("git not found")
        ):
            from wormgear.cli.generate import get_version_string

            # Should return a version string without crashing
            version = get_version_string()
            assert isinstance(version, str)
            assert len(version) > 0

    def test_git_timeout(self):
        """subprocess.TimeoutExpired doesn't crash."""
        with patch(
            "subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="git", timeout=5),
        ):
            from wormgear.cli.generate import get_version_string

            version = get_version_string()
            assert isinstance(version, str)
            assert len(version) > 0

    def test_on_main_branch(self):
        """Main branch returns clean version string."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "main\n"

        # First call: git rev-parse (branch), second call: git status
        status_result = MagicMock()
        status_result.returncode = 0
        status_result.stdout = ""

        with patch("subprocess.run", side_effect=[mock_result, status_result]):
            from wormgear.cli.generate import get_version_string

            version = get_version_string()
            # Should not contain branch name or PR info
            assert "(" not in version
            assert "-dev" not in version

    def test_dirty_tree(self):
        """Dirty working tree on main appends '-dev'."""
        branch_result = MagicMock()
        branch_result.returncode = 0
        branch_result.stdout = "main\n"

        status_result = MagicMock()
        status_result.returncode = 0
        status_result.stdout = " M src/wormgear/cli/generate.py\n"

        with patch(
            "subprocess.run", side_effect=[branch_result, status_result]
        ):
            from wormgear.cli.generate import get_version_string

            version = get_version_string()
            assert version.endswith("-dev")
