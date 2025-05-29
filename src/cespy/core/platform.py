#!/usr/bin/env python
# coding=utf-8
"""Cross-platform compatibility and platform-specific optimizations.

This module provides a centralized platform management system that handles
OS-specific logic, path operations, process management, and performance
optimizations across Windows, Linux, and macOS platforms.
"""

import logging
import os
import platform
import shutil
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Union

from .constants import Simulators
from .paths import get_wine_prefix, is_wine_available

_logger = logging.getLogger("cespy.Platform")


class OSType(Enum):
    """Operating system types."""

    WINDOWS = "windows"
    LINUX = "linux"
    MACOS = "macos"
    UNKNOWN = "unknown"


class Architecture(Enum):
    """CPU architectures."""

    X86_64 = "x86_64"
    ARM64 = "arm64"
    X86 = "x86"
    UNKNOWN = "unknown"


@dataclass
class PlatformInfo:
    """Information about the current platform."""

    os_type: OSType
    architecture: Architecture
    os_version: str
    python_version: str
    is_wine_available: bool
    wine_prefix: Optional[Path]
    cpu_count: int
    total_memory_gb: float

    @property
    def is_windows(self) -> bool:
        """Check if running on Windows."""
        return self.os_type == OSType.WINDOWS

    @property
    def is_linux(self) -> bool:
        """Check if running on Linux."""
        return self.os_type == OSType.LINUX

    @property
    def is_macos(self) -> bool:
        """Check if running on macOS."""
        return self.os_type == OSType.MACOS

    @property
    def is_unix_like(self) -> bool:
        """Check if running on Unix-like system (Linux/macOS)."""
        return self.os_type in (OSType.LINUX, OSType.MACOS)

    @property
    def supports_wine(self) -> bool:
        """Check if Wine is available for Windows app execution."""
        return self.is_unix_like and self.is_wine_available

    @property
    def recommended_workers(self) -> int:
        """Get recommended number of worker processes/threads."""
        # Conservative approach: use 75% of available cores
        return max(1, int(self.cpu_count * 0.75))

    @property
    def memory_per_worker_gb(self) -> float:
        """Get recommended memory allocation per worker."""
        # Reserve 2GB for system, distribute rest among workers
        available_memory = max(1.0, self.total_memory_gb - 2.0)
        return available_memory / self.recommended_workers


class PlatformManager:
    """Centralized platform management for cross-platform compatibility."""

    _instance: Optional["PlatformManager"] = None
    _platform_info: Optional[PlatformInfo] = None

    def __new__(cls) -> "PlatformManager":
        """Singleton pattern for platform manager."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize platform manager."""
        if not hasattr(self, "_initialized"):
            self._initialized = True
            self._detect_platform()

    @property
    def info(self) -> PlatformInfo:
        """Get platform information."""
        if self._platform_info is None:
            self._detect_platform()
        assert self._platform_info is not None
        return self._platform_info

    def _detect_platform(self) -> None:
        """Detect current platform characteristics."""
        # Detect OS type
        system = platform.system().lower()
        if system == "windows":
            os_type = OSType.WINDOWS
        elif system == "linux":
            os_type = OSType.LINUX
        elif system == "darwin":
            os_type = OSType.MACOS
        else:
            os_type = OSType.UNKNOWN
            _logger.warning("Unknown operating system: %s", system)

        # Detect architecture
        machine = platform.machine().lower()
        if machine in ("x86_64", "amd64"):
            architecture = Architecture.X86_64
        elif machine in ("arm64", "aarch64"):
            architecture = Architecture.ARM64
        elif machine in ("i386", "i686", "x86"):
            architecture = Architecture.X86
        else:
            architecture = Architecture.UNKNOWN
            _logger.warning("Unknown architecture: %s", machine)

        # Get system information
        os_version = platform.release()
        python_version = platform.python_version()
        cpu_count = os.cpu_count() or 1

        # Estimate total memory (GB)
        total_memory_gb = 4.0  # Default fallback
        try:
            if os_type == OSType.LINUX:
                # Read from /proc/meminfo
                with open("/proc/meminfo", "r", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("MemTotal:"):
                            kb = int(line.split()[1])
                            total_memory_gb = kb / (1024 * 1024)
                            break
            elif os_type == OSType.MACOS:
                # Use sysctl
                result = subprocess.run(
                    ["sysctl", "-n", "hw.memsize"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=False,
                )
                if result.returncode == 0:
                    bytes_mem = int(result.stdout.strip())
                    total_memory_gb = bytes_mem / (1024**3)
            elif os_type == OSType.WINDOWS:
                # Use wmic
                result = subprocess.run(
                    ["wmic", "computersystem", "get", "TotalPhysicalMemory", "/value"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=False,
                )
                if result.returncode == 0:
                    for line in result.stdout.split("\n"):
                        if line.startswith("TotalPhysicalMemory="):
                            bytes_mem = int(line.split("=")[1])
                            total_memory_gb = bytes_mem / (1024**3)
                            break
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, 
                FileNotFoundError, ValueError, OSError) as e:
            _logger.debug("Failed to detect memory size: %s", e)

        # Check Wine availability
        wine_available = is_wine_available()
        wine_prefix = get_wine_prefix() if wine_available else None

        self._platform_info = PlatformInfo(
            os_type=os_type,
            architecture=architecture,
            os_version=os_version,
            python_version=python_version,
            is_wine_available=wine_available,
            wine_prefix=wine_prefix,
            cpu_count=cpu_count,
            total_memory_gb=total_memory_gb,
        )

        _logger.info(
            "Platform detected: %s %s (%s, %d cores, %.1f GB RAM)",
            os_type.value,
            architecture.value,
            os_version,
            cpu_count,
            total_memory_gb,
        )

    def get_simulator_search_paths(self, simulator: str) -> List[Path]:
        """Get platform-specific search paths for simulators.

        Args:
            simulator: Simulator name (from Simulators constants)

        Returns:
            List of paths to search for simulator executable
        """
        paths = []

        if simulator == Simulators.LTSPICE:
            if self.info.is_windows:
                paths.extend(
                    [
                        Path("C:/Program Files/LTC/LTspiceXVII/XVIIx64.exe"),
                        Path("C:/Program Files/LTC/LTspiceXVII/XVIIx86.exe"),
                        Path("C:/Program Files (x86)/LTC/LTspiceXVII/XVIIx86.exe"),
                        Path("C:/Program Files/ADI/LTspice/LTspice.exe"),
                        Path("C:/Program Files (x86)/ADI/LTspice/LTspice.exe"),
                    ]
                )
            elif self.info.supports_wine:
                wine_prefix = self.info.wine_prefix or Path.home() / ".wine"
                drive_c = wine_prefix / "drive_c"
                paths.extend(
                    [
                        drive_c / "Program Files/LTC/LTspiceXVII/XVIIx64.exe",
                        drive_c / "Program Files/LTC/LTspiceXVII/XVIIx86.exe",
                        drive_c / "Program Files (x86)/LTC/LTspiceXVII/XVIIx86.exe",
                        drive_c / "Program Files/ADI/LTspice/LTspice.exe",
                        drive_c / "Program Files (x86)/ADI/LTspice/LTspice.exe",
                    ]
                )

        elif simulator == Simulators.QSPICE:
            if self.info.is_windows:
                paths.extend(
                    [
                        Path("C:/Program Files/QSPICE/QSPICE64.exe"),
                        Path("C:/Program Files (x86)/QSPICE/QSPICE.exe"),
                    ]
                )
            elif self.info.supports_wine:
                wine_prefix = self.info.wine_prefix or Path.home() / ".wine"
                drive_c = wine_prefix / "drive_c"
                paths.extend(
                    [
                        drive_c / "Program Files/QSPICE/QSPICE64.exe",
                        drive_c / "Program Files (x86)/QSPICE/QSPICE.exe",
                    ]
                )

        elif simulator == Simulators.NGSPICE:
            if self.info.is_windows:
                paths.extend(
                    [
                        Path("C:/Program Files/ngspice/bin/ngspice.exe"),
                        Path("C:/Program Files (x86)/ngspice/bin/ngspice.exe"),
                    ]
                )
            else:
                # Unix-like systems
                paths.extend(
                    [
                        Path("/usr/bin/ngspice"),
                        Path("/usr/local/bin/ngspice"),
                        Path("/opt/homebrew/bin/ngspice"),  # macOS Homebrew
                        Path(
                            "/home/linuxbrew/.linuxbrew/bin/ngspice"
                        ),  # Linux Homebrew
                    ]
                )

        elif simulator == Simulators.XYCE:
            if self.info.is_windows:
                paths.extend(
                    [
                        Path("C:/Program Files/Xyce/bin/Xyce.exe"),
                        Path("C:/Program Files (x86)/Xyce/bin/Xyce.exe"),
                    ]
                )
            else:
                # Unix-like systems
                paths.extend(
                    [
                        Path("/usr/bin/Xyce"),
                        Path("/usr/local/bin/Xyce"),
                        Path("/opt/homebrew/bin/Xyce"),  # macOS Homebrew
                        Path("/home/linuxbrew/.linuxbrew/bin/Xyce"),  # Linux Homebrew
                    ]
                )

        return paths

    def get_temp_directory(self) -> Path:
        """Get platform-appropriate temporary directory.

        Returns:
            Path to temporary directory
        """
        if self.info.is_windows:
            temp_dir = Path(os.environ.get("TEMP", "C:/temp"))
        else:
            temp_dir = Path("/tmp")

        # Create cespy-specific subdirectory
        cespy_temp = temp_dir / f"cespy_{os.getpid()}"
        cespy_temp.mkdir(parents=True, exist_ok=True)

        return cespy_temp

    def get_config_directory(self) -> Path:
        """Get platform-appropriate configuration directory.

        Returns:
            Path to configuration directory
        """
        if self.info.is_windows:
            config_dir = Path(os.environ.get("APPDATA", "~")).expanduser() / "cespy"
        elif self.info.is_macos:
            config_dir = Path.home() / "Library" / "Application Support" / "cespy"
        else:  # Linux and other Unix-like
            config_dir = (
                Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
                / "cespy"
            )

        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir

    def get_cache_directory(self) -> Path:
        """Get platform-appropriate cache directory.

        Returns:
            Path to cache directory
        """
        if self.info.is_windows:
            cache_dir = (
                Path(os.environ.get("LOCALAPPDATA", "~")).expanduser()
                / "cespy"
                / "cache"
            )
        elif self.info.is_macos:
            cache_dir = Path.home() / "Library" / "Caches" / "cespy"
        else:  # Linux and other Unix-like
            cache_dir = (
                Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "cespy"
            )

        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir

    def get_optimal_process_count(self, memory_intensive: bool = False) -> int:
        """Get optimal number of processes for parallel execution.

        Args:
            memory_intensive: Whether the processes are memory-intensive

        Returns:
            Recommended number of processes
        """
        if memory_intensive:
            # Limit based on memory (assume 1GB per process minimum)
            max_by_memory = max(1, int(self.info.total_memory_gb))
            return min(self.info.recommended_workers, max_by_memory)
        return self.info.recommended_workers

    def setup_process_environment(self, wine_mode: bool = False) -> Dict[str, str]:
        """Setup environment variables for subprocess execution.

        Args:
            wine_mode: Whether to setup environment for Wine execution

        Returns:
            Dictionary of environment variables
        """
        env = os.environ.copy()

        if wine_mode and self.info.supports_wine:
            # Wine-specific environment setup
            if self.info.wine_prefix:
                env["WINEPREFIX"] = str(self.info.wine_prefix)

            # Disable Wine debug output for cleaner logs
            env["WINEDEBUG"] = "-all"

            # Set Wine to run in virtual desktop mode to avoid GUI issues
            env["WINEDLLOVERRIDES"] = "mscoree=d"

        # Platform-specific optimizations
        if self.info.is_linux:
            # Use memory mapping for better performance
            env["MALLOC_MMAP_THRESHOLD_"] = "65536"
            env["MALLOC_TRIM_THRESHOLD_"] = "131072"

        return env

    def get_executable_extensions(self) -> List[str]:
        """Get platform-specific executable file extensions.

        Returns:
            List of executable extensions (including dot)
        """
        if self.info.is_windows:
            return [".exe", ".bat", ".cmd"]
        return [""]  # No extension on Unix-like systems

    def find_executable(
        self, name: str, search_paths: Optional[List[Path]] = None
    ) -> Optional[Path]:
        """Find executable in system PATH or provided search paths.

        Args:
            name: Executable name
            search_paths: Additional paths to search

        Returns:
            Path to executable if found, None otherwise
        """
        # Use shutil.which for standard PATH search
        system_path = shutil.which(name)
        if system_path:
            return Path(system_path)

        # Search in provided paths
        if search_paths:
            extensions = self.get_executable_extensions()

            for search_path in search_paths:
                if search_path.is_file():
                    # Direct path to file
                    return search_path
                if search_path.is_dir():
                    # Directory - search for executable
                    for ext in extensions:
                        exe_path = search_path / f"{name}{ext}"
                        if exe_path.is_file():
                            return exe_path

        return None

    def is_process_running(self, process_name: str) -> bool:
        """Check if a process with given name is running.

        Args:
            process_name: Name of the process to check

        Returns:
            True if process is running, False otherwise
        """
        try:
            if self.info.is_windows:
                result = subprocess.run(
                    ["tasklist", "/FI", f"IMAGENAME eq {process_name}"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=False,
                )
                return process_name.lower() in result.stdout.lower()
            
            result = subprocess.run(
                ["pgrep", "-f", process_name],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, 
                FileNotFoundError, OSError) as e:
            _logger.debug("Failed to check process status: %s", e)
            return False

    def get_performance_hints(self) -> Dict[str, Union[str, int, bool, float]]:
        """Get platform-specific performance optimization hints.

        Returns:
            Dictionary of performance hints
        """
        hints: Dict[str, Union[str, int, bool, float]] = {
            "recommended_workers": self.info.recommended_workers,
            "memory_per_worker_gb": self.info.memory_per_worker_gb,
            "use_memory_mapping": self.info.is_unix_like,
            "preferred_temp_fs": "tmpfs" if self.info.is_linux else "default",
        }

        # Platform-specific hints
        if self.info.is_macos and self.info.architecture == Architecture.ARM64:
            hints["rosetta_mode"] = True  # For x86_64 simulators on Apple Silicon

        if self.info.is_windows:
            hints["use_job_objects"] = True  # For better process management

        if self.info.supports_wine:
            hints["wine_available"] = True
            hints["wine_prefix"] = (
                str(self.info.wine_prefix) if self.info.wine_prefix else ""
            )

        return hints


# Global platform manager instance
platform_manager = PlatformManager()


def get_platform_info() -> PlatformInfo:
    """Get current platform information.

    Returns:
        Platform information object
    """
    return platform_manager.info


def get_optimal_workers(memory_intensive: bool = False) -> int:
    """Get optimal number of worker processes/threads.

    Args:
        memory_intensive: Whether workers will be memory-intensive

    Returns:
        Recommended number of workers
    """
    return platform_manager.get_optimal_process_count(memory_intensive)


def is_simulator_available(simulator: str) -> bool:
    """Check if a simulator is available on the current platform.

    Args:
        simulator: Simulator name

    Returns:
        True if simulator is available
    """
    search_paths = platform_manager.get_simulator_search_paths(simulator)
    return platform_manager.find_executable(simulator.lower(), search_paths) is not None


def get_simulator_path(simulator: str) -> Optional[Path]:
    """Get path to simulator executable.

    Args:
        simulator: Simulator name

    Returns:
        Path to simulator if found, None otherwise
    """
    search_paths = platform_manager.get_simulator_search_paths(simulator)
    return platform_manager.find_executable(simulator.lower(), search_paths)
