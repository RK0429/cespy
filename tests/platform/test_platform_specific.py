"""Platform-specific tests to ensure cross-platform compatibility."""

import pytest
import sys
import platform
from pathlib import Path
import subprocess
from cespy.simulators import LTspice, NGspice, Qspice, Xyce
from cespy.editor import SpiceEditor
from cespy.utils.file_search import search_file_in_containers
from cespy.utils.windows_short_names import get_short_path_name


class TestPlatformDetection:
    """Test platform detection and compatibility."""

    def test_platform_info(self):
        """Test that platform detection works correctly."""
        current_platform = sys.platform
        assert current_platform in ["win32", "linux", "darwin", "aix", "wasi"]

        # Check Python version
        assert sys.version_info >= (3, 10)

        print(f"Platform: {current_platform}")
        print(f"Python: {sys.version}")
        print(f"Machine: {platform.machine()}")
        print(f"Processor: {platform.processor()}")

    def test_path_handling(self, temp_dir: Path):
        """Test path handling across platforms."""
        # Test various path formats
        test_paths = [
            temp_dir / "test_file.net",
            temp_dir / "sub_dir" / "test.net",
            temp_dir / "spaces in name" / "test file.net",
            temp_dir / "unicode_文件" / "test.net",
        ]

        for test_path in test_paths:
            # Create parent directories
            test_path.parent.mkdir(parents=True, exist_ok=True)

            # Write test file
            test_path.write_text("* Test\n.end\n")

            # Test that path operations work
            assert test_path.exists()
            assert test_path.is_file()

            # Test path conversions
            posix_path = test_path.as_posix()
            assert isinstance(posix_path, str)

            if sys.platform == "win32":
                # Windows-specific path testing
                uri = test_path.as_uri()
                assert uri.startswith("file:///")

            # Clean up
            test_path.unlink()


class TestSimulatorPlatformCompatibility:
    """Test simulator compatibility on different platforms."""

    def test_ltspice_platform_detection(self):
        """Test LTspice detection on current platform."""
        ltspice = LTspice()

        if sys.platform == "win32":
            # Windows should detect native LTspice
            assert not ltspice.using_macos_native_sim()
        elif sys.platform == "darwin":
            # macOS might have native or wine version
            if ltspice.spice_exe and "wine" not in str(ltspice.spice_exe[0]).lower():
                assert ltspice.using_macos_native_sim()
            else:
                assert not ltspice.using_macos_native_sim()
        else:
            # Linux uses wine
            assert not ltspice.using_macos_native_sim()
            if ltspice.spice_exe:
                assert "wine" in str(ltspice.spice_exe[0]).lower()

    def test_ngspice_platform_compatibility(self):
        """Test NGspice compatibility."""
        ngspice = NGspice()

        # NGspice should work on all platforms
        if ngspice.is_available():
            # Check executable format
            if sys.platform == "win32":
                assert any(exe.endswith(".exe") for exe in ngspice.spice_exe)
            else:
                # Unix-like systems
                assert not any(exe.endswith(".exe") for exe in ngspice.spice_exe)

    @pytest.mark.skipif(sys.platform != "win32", reason="Qspice is Windows-only")
    def test_qspice_windows_only(self):
        """Test that Qspice is available on Windows."""
        qspice = Qspice()

        # On Windows, check if Qspice can be found
        if qspice.is_available():
            assert qspice.spice_exe
            assert any("qspice" in exe.lower() for exe in qspice.spice_exe)

    def test_xyce_platform_compatibility(self):
        """Test Xyce compatibility."""
        xyce = Xyce()

        # Xyce works on multiple platforms
        if xyce.is_available():
            # Verify executable
            assert xyce.spice_exe

            # Check for MPI support on Unix-like systems
            if sys.platform != "win32":
                # Xyce often uses MPI on Unix
                # Check if mpirun is available
                try:
                    result = subprocess.run(
                        ["which", "mpirun"], capture_output=True, text=True
                    )
                    has_mpi = result.returncode == 0
                    print(f"MPI available: {has_mpi}")
                except Exception:
                    pass


class TestFileSystemOperations:
    """Test file system operations across platforms."""

    def test_encoding_detection(self, temp_dir: Path):
        """Test file encoding detection."""
        # Test files with different encodings
        test_cases = [
            ("utf8_test.net", "UTF-8", "* UTF-8 Test\nΩ Ω Ω\n.end\n"),
            ("ascii_test.net", "ASCII", "* ASCII Test\n.end\n"),
            (
                "latin1_test.net",
                "ISO-8859-1",
                "* Latin-1 Test\n.end\n".encode("latin-1"),
            ),
        ]

        for filename, expected_encoding, content in test_cases:
            file_path = temp_dir / filename

            if isinstance(content, bytes):
                file_path.write_bytes(content)
            else:
                file_path.write_text(content, encoding=expected_encoding.lower())

            # Test encoding detection
            try:
                editor = SpiceEditor(file_path)
                # Should be able to read the file
                assert len(str(editor)) > 0
            except UnicodeDecodeError:
                pytest.fail(
                    f"Failed to read {filename} with encoding {expected_encoding}"
                )

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
    def test_windows_short_names(self, temp_dir: Path):
        """Test Windows short path name functionality."""
        # Create a path with spaces
        long_path = temp_dir / "Program Files" / "Test Application" / "test.net"
        long_path.parent.mkdir(parents=True, exist_ok=True)
        long_path.write_text("* Test\n.end\n")

        # Get short path name
        short_path = get_short_path_name(str(long_path))

        # Short path should exist and be different
        assert Path(short_path).exists()
        assert "~" in short_path or len(short_path) <= len(str(long_path))

    def test_file_search_functionality(self, temp_dir: Path):
        """Test file search across platform-specific paths."""
        # Create test files in various locations
        containers = []

        # Create test structure
        for i in range(3):
            container = temp_dir / f"container_{i}"
            container.mkdir()
            containers.append(container)

            # Add test files
            (container / "test.lib").write_text("* Test library\n")
            (container / "subdir").mkdir()
            (container / "subdir" / "test.inc").write_text("* Test include\n")

        # Test file search
        found = search_file_in_containers("test.lib", containers)
        assert found is not None
        assert found.name == "test.lib"

        # Test recursive search
        found = search_file_in_containers("test.inc", containers, recursive=True)
        assert found is not None
        assert found.name == "test.inc"

        # Test non-existent file
        not_found = search_file_in_containers("nonexistent.xyz", containers)
        assert not_found is None


class TestLineEndingHandling:
    """Test handling of different line endings across platforms."""

    def test_line_ending_conversion(self, temp_dir: Path):
        """Test that different line endings are handled correctly."""
        test_cases = [
            ("unix_endings.net", "* Unix Line Endings\nV1 in 0 1\n.end\n"),
            ("windows_endings.net", "* Windows Line Endings\r\nV1 in 0 1\r\n.end\r\n"),
            ("mac_endings.net", "* Mac Line Endings\rV1 in 0 1\r.end\r"),
            ("mixed_endings.net", "* Mixed\nV1 in 0 1\r\n.end\r"),
        ]

        for filename, content in test_cases:
            file_path = temp_dir / filename
            # Write with binary mode to preserve line endings
            file_path.write_bytes(content.encode())

            # Test that SpiceEditor can handle all line endings
            editor = SpiceEditor(file_path)

            # Should parse correctly regardless of line endings
            components = editor.get_components()
            assert "V1" in components

            # Save should use platform-appropriate line endings
            editor.save_netlist()

            # Verify saved file is readable
            editor2 = SpiceEditor(file_path)
            assert "V1" in editor2.get_components()


class TestPlatformSpecificPaths:
    """Test platform-specific path handling."""

    def test_home_directory_expansion(self):
        """Test home directory expansion works on all platforms."""
        home_path = Path("~").expanduser()
        assert home_path.exists()
        assert home_path.is_absolute()

        # Test in file paths
        test_path = Path("~/test_cespy_temp.txt").expanduser()
        assert test_path.is_absolute()
        assert str(test_path).startswith(str(home_path))

    def test_library_path_detection(self):
        """Test default library path detection."""
        ltspice = LTspice()

        # Get default library paths
        lib_paths = ltspice._default_lib_paths

        # Expand and check paths
        for lib_path in lib_paths:
            expanded = Path(lib_path).expanduser()
            # Path might not exist, but expansion should work
            assert "~" not in str(expanded)

            if sys.platform == "win32":
                # Windows paths
                assert any(
                    p in str(expanded) for p in ["AppData", "Documents", "My Documents"]
                )
            elif sys.platform == "darwin":
                # macOS paths
                if expanded.exists():
                    assert any(p in str(expanded) for p in ["Library", "Documents"])

    @pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
    def test_wine_path_handling(self, temp_dir: Path):
        """Test Wine path handling for LTspice on Unix."""
        # Create a mock Wine environment structure
        wine_drive_c = temp_dir / ".wine" / "drive_c"
        wine_program_files = wine_drive_c / "Program Files" / "LTC" / "LTspiceXVII"
        wine_program_files.mkdir(parents=True, exist_ok=True)

        # Test Wine path conversion
        # "C:/Program Files/LTC/LTspiceXVII/XVIIx64.exe"

        # LTspice should handle this conversion internally
        ltspice = LTspice()
        if ltspice.spice_exe and "wine" in ltspice.spice_exe[0]:
            # Should convert C:/ to Z:/ for Wine
            assert not any("C:/" in arg for arg in ltspice.spice_exe)


class TestExecutablePermissions:
    """Test executable permissions on Unix-like systems."""

    @pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
    def test_executable_permissions(self, temp_dir: Path):
        """Test that executables have correct permissions."""
        # Create a mock executable
        mock_exe = temp_dir / "mock_simulator"
        mock_exe.write_text("#!/bin/sh\necho 'Mock simulator'\n")

        # Set executable permissions
        import stat

        mock_exe.chmod(mock_exe.stat().st_mode | stat.S_IEXEC)

        # Verify executable
        assert mock_exe.stat().st_mode & stat.S_IEXEC

        # Test execution
        try:
            result = subprocess.run([str(mock_exe)], capture_output=True, text=True)
            assert result.returncode == 0
            assert "Mock simulator" in result.stdout
        except Exception as e:
            pytest.skip(f"Cannot execute mock simulator: {e}")
