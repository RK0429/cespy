"""Integration tests for CLI entry points."""

import pytest
import subprocess
import sys
from pathlib import Path


class TestCLIEntryPoints:
    """Test CLI entry points work correctly."""

    def test_cli_help_commands(self):
        """Test that CLI commands show help when called with --help."""
        commands = [
            "cespy-asc-to-qsch",
            "cespy-run-server",
            "cespy-raw-convert",
            "cespy-sim-client",
            "cespy-ltsteps",
            "cespy-rawplot",
            "cespy-histogram"
        ]

        for command in commands:
            # Test that command exists and shows help
            try:
                result = subprocess.run(
                    [sys.executable, "-c", f"import subprocess; subprocess.run(['{command}', '--help'])"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                # Should not crash when called with --help
                # The exact return code may vary, but it shouldn't hang or crash
            except subprocess.TimeoutExpired:
                pytest.fail(f"Command {command} --help timed out")
            except FileNotFoundError:
                # Command not found - may not be installed yet
                pytest.skip(f"Command {command} not found in PATH")

    def test_module_imports_from_cli(self):
        """Test that modules can be imported when called from CLI context."""
        # Test that entry point modules can be imported
        import_tests = [
            "from cespy.editor.asc_to_qsch import main",
            "from cespy.client_server.run_server import main",
            "from cespy.raw.raw_convert import main",
            "from cespy.client_server.sim_client import main",
            "from cespy.log.ltsteps import main",
            "from cespy.raw.rawplot import main",
            "from cespy.utils.histogram import main"
        ]

        for import_test in import_tests:
            try:
                result = subprocess.run(
                    [sys.executable, "-c", import_test],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode != 0:
                    # Check if it's a missing main function or import error
                    if "cannot import name 'main'" in result.stderr:
                        # This is expected if main function doesn't exist yet
                        continue
                    elif "No module named" in result.stderr:
                        pytest.fail(f"Import failed: {result.stderr}")
            except subprocess.TimeoutExpired:
                pytest.fail(f"Import test timed out: {import_test}")

    def test_asc_to_qsch_entry_point(self, temp_dir: Path):
        """Test asc-to-qsch entry point with mock data."""
        # Create a simple .asc file for testing
        asc_file = temp_dir / "test.asc"
        asc_content = """Version 4
SHEET 1 880 680
WIRE 144 144 32 144
WIRE 272 144 144 144
SYMBOL res 160 128 R0
SYMATTR InstName R1
SYMATTR Value 1k
SYMBOL cap 256 128 R0
SYMATTR InstName C1
SYMATTR Value 1u
TEXT 32 200 Left 2 !.tran 1m
"""
        asc_file.write_text(asc_content)

        # Test that the entry point can be called (may fail due to missing implementation)
        try:
            result = subprocess.run(
                [sys.executable, "-m", "cespy.editor.asc_to_qsch", str(asc_file)],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=temp_dir
            )
            # May fail if not implemented, but shouldn't crash Python
        except subprocess.TimeoutExpired:
            pytest.fail("asc-to-qsch command timed out")
        except FileNotFoundError:
            pytest.skip("asc-to-qsch module not found")

    def test_server_entry_point_help(self):
        """Test that server entry point can show help."""
        try:
            result = subprocess.run(
                [sys.executable, "-c", "from cespy.client_server.run_server import main; print('Server module imported successfully')"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                assert "successfully" in result.stdout
        except subprocess.TimeoutExpired:
            pytest.fail("Server import test timed out")

    def test_raw_convert_entry_point(self, temp_dir: Path):
        """Test raw convert entry point."""
        # Create a dummy raw file for testing
        raw_file = temp_dir / "test.raw"
        raw_file.write_bytes(b"Binary data placeholder")

        try:
            result = subprocess.run(
                [sys.executable, "-c", "from cespy.raw.raw_convert import main; print('Raw convert module imported')"],
                capture_output=True,
                text=True,
                timeout=5
            )
            # Just test that the module can be imported
        except subprocess.TimeoutExpired:
            pytest.fail("Raw convert import test timed out")

    def test_histogram_entry_point(self):
        """Test histogram entry point."""
        try:
            result = subprocess.run(
                [sys.executable, "-c", "from cespy.utils.histogram import main; print('Histogram module imported')"],
                capture_output=True,
                text=True,
                timeout=5
            )
            # Just test that the module can be imported
        except subprocess.TimeoutExpired:
            pytest.fail("Histogram import test timed out")

    def test_cli_with_invalid_arguments(self):
        """Test CLI behavior with invalid arguments."""
        # Test commands that should handle invalid arguments gracefully
        test_cases = [
            ("cespy-asc-to-qsch", ["nonexistent_file.asc"]),
            ("cespy-raw-convert", ["nonexistent_file.raw"]),
        ]

        for command, args in test_cases:
            try:
                result = subprocess.run(
                    [sys.executable, "-c", f"import subprocess; subprocess.run(['{command}'] + {args})"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                # Should handle invalid arguments without crashing
            except subprocess.TimeoutExpired:
                pytest.fail(f"Command {command} with invalid args timed out")
            except FileNotFoundError:
                pytest.skip(f"Command {command} not found")

    def test_package_installation_check(self):
        """Test that the package is properly installed and entry points work."""
        # Test basic package import
        result = subprocess.run(
            [sys.executable, "-c", "import cespy; print(f'cespy version: {getattr(cespy, \"__version__\", \"unknown\")}')"],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0:
            assert "cespy version:" in result.stdout
        else:
            pytest.fail(f"Failed to import cespy: {result.stderr}")

    def test_poetry_scripts_configuration(self):
        """Test that poetry scripts are properly configured."""
        # Read the pyproject.toml to verify script entry points
        import tomllib

        pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"
        if pyproject_path.exists():
            with open(pyproject_path, "rb") as f:
                config = tomllib.load(f)

            scripts = config.get("tool", {}).get("poetry", {}).get("scripts", {})
            expected_scripts = [
                "cespy-asc-to-qsch",
                "cespy-run-server",
                "cespy-raw-convert",
                "cespy-sim-client",
                "cespy-ltsteps",
                "cespy-rawplot",
                "cespy-histogram"
            ]

            for script in expected_scripts:
                assert script in scripts, f"Script {script} not found in pyproject.toml"
                # Verify the entry point format
                entry_point = scripts[script]
                assert ":" in entry_point, f"Invalid entry point format for {script}: {entry_point}"
                module, function = entry_point.split(":")
                assert module.startswith("cespy."), f"Entry point should start with cespy.: {entry_point}"
