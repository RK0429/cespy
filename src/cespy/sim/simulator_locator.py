#!/usr/bin/env python
# coding=utf-8
"""Simulator locator for finding and validating SPICE simulator installations.

This module provides functionality to locate simulators on different platforms,
handle Wine environments, and validate installations.
"""

import logging
import os
import platform
import re
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple

# Core imports
from ..core import constants as core_constants

_logger = logging.getLogger("cespy.SimulatorLocator")


class SimulatorLocator:
    """Handles locating and validating simulator installations across platforms."""

    # Default search paths for different simulators on different platforms
    SEARCH_PATHS = {
        core_constants.Simulators.LTSPICE: {
            "windows": [
                "C:/Program Files/LTC/LTspiceXVII/XVIIx64.exe",
                "C:/Program Files (x86)/LTC/LTspiceIV/scad3.exe",
                "C:/Program Files/ADI/LTspice/LTspice.exe",
            ],
            "darwin": [
                "/Applications/LTspice.app/Contents/MacOS/LTspice",
            ],
            "linux": [
                "~/.wine/drive_c/Program Files/LTC/LTspiceXVII/XVIIx64.exe",
                "~/.wine/drive_c/Program Files/ADI/LTspice/LTspice.exe",
            ],
        },
        core_constants.Simulators.QSPICE: {
            "windows": [
                "C:/Program Files/QSPICE/QSPICE64.exe",
                "C:/Program Files (x86)/QSPICE/QSPICE.exe",
            ],
            "darwin": [],
            "linux": [],
        },
        core_constants.Simulators.NGSPICE: {
            "windows": [
                "C:/Spice64/bin/ngspice.exe",
                "C:/Program Files/ngspice/bin/ngspice.exe",
            ],
            "darwin": [
                "/usr/local/bin/ngspice",
                "/opt/homebrew/bin/ngspice",
            ],
            "linux": [
                "/usr/bin/ngspice",
                "/usr/local/bin/ngspice",
            ],
        },
        core_constants.Simulators.XYCE: {
            "windows": [
                "C:/Program Files/Xyce/bin/Xyce.exe",
            ],
            "darwin": [
                "/usr/local/bin/Xyce",
            ],
            "linux": [
                "/usr/bin/Xyce",
                "/usr/local/bin/Xyce",
            ],
        },
    }

    def __init__(self, simulator_type: str):
        """Initialize locator for a specific simulator type.

        Args:
            simulator_type: Type of simulator from core_constants.Simulators
        """
        self.simulator_type = simulator_type
        self.platform = platform.system().lower()
        self._cached_location: Optional[Path] = None

    def find_simulator(
        self, custom_path: Optional[str] = None
    ) -> Tuple[Optional[Path], bool]:
        """Find the simulator executable.

        Args:
            custom_path: Optional custom path to check first

        Returns:
            Tuple of (path_to_executable, uses_wine)
        """
        # Check custom path first
        if custom_path:
            path, uses_wine = self._check_path(custom_path)
            if path:
                self._cached_location = path
                return path, uses_wine

        # Check cached location
        if self._cached_location and self._cached_location.exists():
            uses_wine = self._detect_wine_usage(str(self._cached_location))
            return self._cached_location, uses_wine

        # Search default paths
        search_paths = self.SEARCH_PATHS.get(self.simulator_type, {}).get(
            self.platform, []
        )
        for search_path in search_paths:
            path, uses_wine = self._check_path(search_path)
            if path:
                self._cached_location = path
                return path, uses_wine

        # Check system PATH
        if self.simulator_type == core_constants.Simulators.NGSPICE:
            exe_name = "ngspice"
        elif self.simulator_type == core_constants.Simulators.XYCE:
            exe_name = "Xyce"
        else:
            exe_name = None

        if exe_name:
            which_result = shutil.which(exe_name)
            if which_result:
                path = Path(which_result)
                self._cached_location = path
                return path, False

        return None, False

    def _check_path(self, path_str: str) -> Tuple[Optional[Path], bool]:
        """Check if a path exists and determine if it uses Wine.

        Args:
            path_str: Path string to check

        Returns:
            Tuple of (Path object if exists, uses_wine)
        """
        # Expand user and environment variables
        expanded = os.path.expanduser(os.path.expandvars(path_str))
        path = Path(expanded)

        # Check if it's a Wine path
        uses_wine = self._detect_wine_usage(expanded)

        # For Wine paths on non-Windows platforms, check wine availability
        if uses_wine and self.platform != "windows":
            if not self._is_wine_available():
                _logger.debug("Wine not available for path: %s", path)
                return None, False

        # Check if path exists
        if path.exists() and path.is_file():
            return path, uses_wine

        return None, False

    def _detect_wine_usage(self, path_str: str) -> bool:
        """Detect if a path requires Wine to run.

        Args:
            path_str: Path string to check

        Returns:
            True if Wine is needed
        """
        if self.platform == "windows":
            return False

        # Check for Wine indicators in path
        wine_indicators = [".wine", "drive_c", "Program Files"]
        return any(indicator in path_str for indicator in wine_indicators)

    def _is_wine_available(self) -> bool:
        """Check if Wine is available on the system.

        Returns:
            True if Wine is available
        """
        if self.platform == "windows":
            return False

        return shutil.which("wine") is not None

    def get_wine_command(self) -> List[str]:
        """Get the Wine command prefix for running Windows executables.

        Returns:
            List of command components for Wine
        """
        if self.platform == "darwin":
            # On macOS, we might need to use wine64
            if shutil.which("wine64"):
                return ["wine64"]
        return ["wine"]

    def get_library_paths(self, exe_path: Path) -> List[Path]:
        """Get default library paths for a simulator executable.

        Args:
            exe_path: Path to the simulator executable

        Returns:
            List of library directory paths
        """
        lib_paths = []
        exe_dir = exe_path.parent

        # Common library subdirectories
        lib_subdirs = ["lib", "libraries", "Library", "lib/sub", "lib/sym"]

        # Check relative to executable
        for subdir in lib_subdirs:
            lib_path = exe_dir / subdir
            if lib_path.exists() and lib_path.is_dir():
                lib_paths.append(lib_path)

        # Simulator-specific paths
        if self.simulator_type == core_constants.Simulators.LTSPICE:
            # LTspice specific library locations
            if self.platform == "windows":
                docs_path = Path.home() / "Documents" / "LTspiceXVII" / "lib"
                if docs_path.exists():
                    lib_paths.append(docs_path)
            elif self.platform == "darwin":
                app_support = (
                    Path.home() / "Library" / "Application Support" / "LTspice" / "lib"
                )
                if app_support.exists():
                    lib_paths.append(app_support)

        return lib_paths

    def validate_executable(
        self, exe_path: Path, uses_wine: bool = False
    ) -> Tuple[bool, str]:
        """Validate that an executable can be run and get version info.

        Args:
            exe_path: Path to the executable
            uses_wine: Whether Wine is needed

        Returns:
            Tuple of (is_valid, version_or_error_message)
        """
        try:
            # Build command to get version
            if uses_wine and self.platform != "windows":
                cmd = self.get_wine_command() + [str(exe_path)]
            else:
                cmd = [str(exe_path)]

            # Add version flag based on simulator
            if self.simulator_type == core_constants.Simulators.LTSPICE:
                cmd.append("-v")
            elif self.simulator_type == core_constants.Simulators.NGSPICE:
                cmd.append("--version")
            elif self.simulator_type == core_constants.Simulators.QSPICE:
                cmd.append("-v")
            elif self.simulator_type == core_constants.Simulators.XYCE:
                cmd.append("-v")

            # Run command with timeout
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5.0, check=False)

            # Parse version from output
            output = result.stdout + result.stderr
            version = self._parse_version(output)

            if version:
                return True, version
            return False, "Could not determine version"

        except subprocess.TimeoutExpired:
            return False, "Timeout while checking version"
        except (subprocess.CalledProcessError, FileNotFoundError, OSError) as e:
            return False, f"Error: {str(e)}"

    def _parse_version(self, output: str) -> Optional[str]:
        """Parse version string from simulator output.

        Args:
            output: Command output to parse

        Returns:
            Version string or None
        """
        # Patterns for different simulators
        patterns = {
            core_constants.Simulators.LTSPICE: (
                r"LTspice\s+(?:IV|XVII|64)?\s*(?:Version\s+)?([0-9.]+)"
            ),
            core_constants.Simulators.NGSPICE: r"ngspice-([0-9]+)",
            core_constants.Simulators.QSPICE: r"QSPICE\s+(?:Version\s+)?([0-9.]+)",
            core_constants.Simulators.XYCE: r"Xyce\s+(?:Version\s+)?([0-9.]+)",
        }

        pattern = patterns.get(self.simulator_type)
        if pattern:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                return match.group(1)

        return None
