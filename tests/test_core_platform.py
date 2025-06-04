#!/usr/bin/env python
# coding=utf-8
"""Tests for core platform management functionality."""

import platform
import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from cespy.core.platform import (
    Architecture,
    OSType,
    PlatformInfo,
    PlatformManager,
    get_platform_info,
    get_optimal_workers,
    is_simulator_available,
    get_simulator_path,
)
from cespy.core.constants import Simulators


class TestPlatformInfo:
    """Test PlatformInfo dataclass."""

    def test_platform_info_creation(self):
        """Test PlatformInfo creation and properties."""
        info = PlatformInfo(
            os_type=OSType.LINUX,
            architecture=Architecture.X86_64,
            os_version="5.4.0",
            python_version="3.9.0",
            is_wine_available=True,
            wine_prefix=Path("/home/user/.wine"),
            cpu_count=8,
            total_memory_gb=16.0,
        )

        assert info.is_linux
        assert not info.is_windows
        assert not info.is_macos
        assert info.is_unix_like
        assert info.supports_wine
        assert info.recommended_workers == 6  # 75% of 8 cores
        assert info.memory_per_worker_gb == pytest.approx(2.33, rel=0.1)  # (16-2)/6

    def test_windows_platform_info(self):
        """Test Windows-specific platform info."""
        info = PlatformInfo(
            os_type=OSType.WINDOWS,
            architecture=Architecture.X86_64,
            os_version="10.0.19041",
            python_version="3.9.0",
            is_wine_available=False,
            wine_prefix=None,
            cpu_count=4,
            total_memory_gb=8.0,
        )

        assert info.is_windows
        assert not info.is_unix_like
        assert not info.supports_wine
        assert info.recommended_workers == 3

    def test_macos_platform_info(self):
        """Test macOS-specific platform info."""
        info = PlatformInfo(
            os_type=OSType.MACOS,
            architecture=Architecture.ARM64,
            os_version="12.0",
            python_version="3.9.0",
            is_wine_available=False,
            wine_prefix=None,
            cpu_count=10,
            total_memory_gb=32.0,
        )

        assert info.is_macos
        assert info.is_unix_like
        assert not info.supports_wine  # Wine not available on ARM64 macOS typically
        assert info.recommended_workers == 7  # 75% of 10 cores


class TestPlatformManager:
    """Test PlatformManager singleton."""

    def test_singleton_behavior(self):
        """Test that PlatformManager is a singleton."""
        manager1 = PlatformManager()
        manager2 = PlatformManager()
        assert manager1 is manager2

    def test_platform_detection(self):
        """Test platform detection functionality."""
        manager = PlatformManager()
        info = manager.info

        # Basic sanity checks
        assert isinstance(info.os_type, OSType)
        assert isinstance(info.architecture, Architecture)
        assert info.cpu_count > 0
        assert info.total_memory_gb > 0
        assert isinstance(info.python_version, str)

    @patch("platform.system")
    @patch("platform.machine")
    def test_os_type_detection(self, mock_machine, mock_system):
        """Test OS type detection logic."""
        # Reset singleton for testing
        PlatformManager._instance = None
        PlatformManager._platform_info = None

        mock_system.return_value = "Linux"
        mock_machine.return_value = "x86_64"

        manager = PlatformManager()
        assert manager.info.os_type == OSType.LINUX
        assert manager.info.architecture == Architecture.X86_64

        # Cleanup
        PlatformManager._instance = None
        PlatformManager._platform_info = None

    def test_simulator_search_paths(self):
        """Test simulator search path generation."""
        manager = PlatformManager()

        # Test LTSpice paths
        ltspice_paths = manager.get_simulator_search_paths(Simulators.LTSPICE)
        assert len(ltspice_paths) > 0
        assert all(isinstance(path, Path) for path in ltspice_paths)

        # Test NGSpice paths
        ngspice_paths = manager.get_simulator_search_paths(Simulators.NGSPICE)
        assert len(ngspice_paths) > 0

    def test_temp_directory_creation(self):
        """Test temporary directory creation."""
        manager = PlatformManager()
        temp_dir = manager.get_temp_directory()

        assert temp_dir.exists()
        assert temp_dir.is_dir()
        assert "cespy" in str(temp_dir)

        # Cleanup
        temp_dir.rmdir()

    def test_config_directory_creation(self):
        """Test configuration directory creation."""
        manager = PlatformManager()
        config_dir = manager.get_config_directory()

        assert config_dir.exists()
        assert config_dir.is_dir()
        assert "cespy" in str(config_dir)

    def test_cache_directory_creation(self):
        """Test cache directory creation."""
        manager = PlatformManager()
        cache_dir = manager.get_cache_directory()

        assert cache_dir.exists()
        assert cache_dir.is_dir()
        assert "cespy" in str(cache_dir)

    def test_optimal_process_count(self):
        """Test optimal process count calculation."""
        manager = PlatformManager()

        # Normal processes
        normal_count = manager.get_optimal_process_count(memory_intensive=False)
        assert normal_count > 0
        assert normal_count <= manager.info.cpu_count

        # Memory-intensive processes
        memory_count = manager.get_optimal_process_count(memory_intensive=True)
        assert memory_count > 0
        assert memory_count <= normal_count  # Should be same or fewer

    def test_process_environment_setup(self):
        """Test process environment setup."""
        manager = PlatformManager()

        # Normal environment
        env = manager.setup_process_environment(wine_mode=False)
        assert isinstance(env, dict)
        assert "PATH" in env  # Should inherit system PATH

        # Wine environment (if supported)
        wine_env = manager.setup_process_environment(wine_mode=True)
        assert isinstance(wine_env, dict)
        if manager.info.supports_wine:
            assert "WINEDEBUG" in wine_env

    def test_executable_extensions(self):
        """Test executable extension detection."""
        manager = PlatformManager()
        extensions = manager.get_executable_extensions()

        assert isinstance(extensions, list)
        assert len(extensions) > 0

        if manager.info.is_windows:
            assert ".exe" in extensions
        else:
            assert "" in extensions  # Unix systems use no extension

    @patch("shutil.which")
    def test_find_executable(self, mock_which):
        """Test executable finding functionality."""
        manager = PlatformManager()

        # Test system PATH search
        mock_which.return_value = "/usr/bin/test_exe"
        result = manager.find_executable("test_exe")
        assert result == Path("/usr/bin/test_exe")

        # Test custom search paths
        mock_which.return_value = None
        search_paths = [Path("/custom/path")]
        result = manager.find_executable("nonexistent", search_paths)
        assert result is None

    def test_performance_hints(self):
        """Test performance optimization hints."""
        manager = PlatformManager()
        hints = manager.get_performance_hints()

        assert isinstance(hints, dict)
        assert "recommended_workers" in hints
        assert "memory_per_worker_gb" in hints
        assert "use_memory_mapping" in hints

        # Platform-specific hints
        if manager.info.is_windows:
            assert "use_job_objects" in hints

        if manager.info.supports_wine:
            assert "wine_available" in hints


class TestPlatformFunctions:
    """Test module-level platform functions."""

    def test_get_platform_info(self):
        """Test get_platform_info function."""
        info = get_platform_info()
        assert isinstance(info, PlatformInfo)
        assert info.os_type in [
            OSType.WINDOWS,
            OSType.LINUX,
            OSType.MACOS,
            OSType.UNKNOWN,
        ]

    def test_get_optimal_workers(self):
        """Test get_optimal_workers function."""
        workers = get_optimal_workers()
        assert isinstance(workers, int)
        assert workers > 0

        memory_workers = get_optimal_workers(memory_intensive=True)
        assert isinstance(memory_workers, int)
        assert memory_workers > 0
        assert memory_workers <= workers

    @patch("cespy.core.platform.PlatformManager")
    def test_is_simulator_available(self, mock_manager_class):
        """Test is_simulator_available function."""
        mock_manager = Mock()
        mock_manager.get_simulator_search_paths.return_value = [Path("/fake/path")]
        mock_manager.find_executable.return_value = Path("/fake/simulator")
        mock_manager_class.return_value = mock_manager

        # Mock the module-level manager
        with patch("cespy.core.platform.platform_manager", mock_manager):
            result = is_simulator_available(Simulators.LTSPICE)
            assert isinstance(result, bool)

    @patch("cespy.core.platform.PlatformManager")
    def test_get_simulator_path(self, mock_manager_class):
        """Test get_simulator_path function."""
        mock_manager = Mock()
        mock_manager.get_simulator_search_paths.return_value = [Path("/fake/path")]
        mock_manager.find_executable.return_value = Path("/fake/simulator")
        mock_manager_class.return_value = mock_manager

        # Mock the module-level manager
        with patch("cespy.core.platform.platform_manager", mock_manager):
            result = get_simulator_path(Simulators.LTSPICE)
            assert result == Path("/fake/simulator") or result is None


@pytest.mark.integration
class TestPlatformIntegration:
    """Integration tests for platform functionality."""

    def test_real_platform_detection(self):
        """Test detection on real platform."""
        info = get_platform_info()

        # Verify detection matches actual platform
        system = platform.system().lower()
        if system == "windows":
            assert info.is_windows
        elif system == "linux":
            assert info.is_linux
        elif system == "darwin":
            assert info.is_macos

    def test_directory_operations(self):
        """Test directory operations on real filesystem."""
        manager = PlatformManager()

        # Test all directory types
        temp_dir = manager.get_temp_directory()
        config_dir = manager.get_config_directory()
        cache_dir = manager.get_cache_directory()

        assert temp_dir.exists() and temp_dir.is_dir()
        assert config_dir.exists() and config_dir.is_dir()
        assert cache_dir.exists() and cache_dir.is_dir()

        # Test that directories are different
        assert temp_dir != config_dir
        assert config_dir != cache_dir
        assert temp_dir != cache_dir

    def test_resource_detection(self):
        """Test system resource detection."""
        info = get_platform_info()

        # Verify reasonable values
        assert 1 <= info.cpu_count <= 256  # Reasonable CPU count range
        assert 0.5 <= info.total_memory_gb <= 2048  # Reasonable memory range
        assert 1 <= info.recommended_workers <= info.cpu_count


class TestErrorHandling:
    """Test error handling in platform management."""

    @patch("subprocess.run")
    def test_memory_detection_failure(self, mock_run):
        """Test graceful handling of memory detection failure."""
        mock_run.side_effect = Exception("Command failed")

        # Reset singleton for testing
        PlatformManager._instance = None
        PlatformManager._platform_info = None

        manager = PlatformManager()
        # Should use default fallback value
        assert manager.info.total_memory_gb == 4.0

        # Cleanup
        PlatformManager._instance = None
        PlatformManager._platform_info = None

    def test_invalid_simulator_name(self):
        """Test handling of invalid simulator names."""
        manager = PlatformManager()

        # Should return empty list for unknown simulator
        paths = manager.get_simulator_search_paths("invalid_simulator")
        assert paths == []

    def test_nonexistent_executable_search(self):
        """Test searching for nonexistent executable."""
        manager = PlatformManager()

        result = manager.find_executable("definitely_nonexistent_executable_12345")
        assert result is None


if __name__ == "__main__":
    pytest.main([__file__])
