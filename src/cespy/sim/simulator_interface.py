#!/usr/bin/env python
# coding=utf-8
"""Enhanced simulator interface for standardized SPICE simulator interactions.

This module provides an improved abstract base class for simulators with:
- Clearer separation of concerns
- Better validation and error handling
- Standardized parameter handling
- Version detection support
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class SimulatorStatus(Enum):
    """Simulator availability status."""

    AVAILABLE = "available"
    NOT_FOUND = "not_found"
    INVALID_VERSION = "invalid_version"
    MISSING_DEPENDENCIES = "missing_dependencies"


@dataclass
class SimulatorInfo:
    """Information about a simulator installation."""

    name: str
    version: str
    executable_path: Path
    status: SimulatorStatus
    library_paths: List[Path]
    supported_analyses: List[str]
    max_threads: int = 1

    def __str__(self) -> str:
        """Return string representation of simulator info."""
        return f"{self.name} v{self.version} at {self.executable_path}"


@dataclass
class SimulationCommand:
    """Encapsulates a simulation command with all necessary parameters."""

    executable: List[str]
    arguments: List[str]
    environment: Dict[str, str]
    working_directory: Path
    timeout: Optional[float] = None

    def to_command_list(self) -> List[str]:
        """Convert to a command list for subprocess execution."""
        return self.executable + self.arguments


class ISimulator(ABC):
    """Enhanced abstract interface for SPICE simulators.

    This interface provides a cleaner separation of concerns compared to the
    original Simulator class, with explicit methods for validation, version
    detection, and command preparation.
    """

    # Class attributes to be overridden by implementations
    simulator_name: str = ""
    supported_platforms: List[str] = ["windows", "linux", "darwin"]
    supported_analyses: List[str] = []
    default_timeout: float = 300.0

    @abstractmethod
    def validate_installation(self) -> SimulatorInfo:
        """Verify simulator is properly installed and return its information.

        This method should:
        1. Check if the executable exists
        2. Verify it can be executed
        3. Extract version information
        4. Determine library paths
        5. Check for required dependencies

        Returns:
            SimulatorInfo object with installation details

        Raises:
            SimulatorNotInstalledError: If simulator is not properly installed
            InvalidSimulatorError: If simulator is found but invalid
        """
        pass

    @abstractmethod
    def get_version(self) -> str:
        """Get simulator version information.

        Returns:
            Version string (e.g., "17.1.0")

        Raises:
            SimulatorNotInstalledError: If simulator is not available
        """
        pass

    @abstractmethod
    def prepare_command(
        self,
        netlist: Path,
        options: Optional[Dict[str, Any]] = None,
        raw_switches: Optional[List[str]] = None,
    ) -> SimulationCommand:
        """Prepare command line for execution.

        This method constructs the complete command needed to run a simulation,
        including all necessary arguments and environment setup.

        Args:
            netlist: Path to the netlist file
            options: Dictionary of simulator-specific options
            raw_switches: Additional command-line switches

        Returns:
            SimulationCommand object ready for execution

        Raises:
            ValueError: If invalid options are provided
        """
        pass

    @abstractmethod
    def parse_arguments(self, args: List[str]) -> Dict[str, Any]:
        """Parse command-line arguments into structured options.

        This method provides the reverse of prepare_command, allowing
        existing command lines to be parsed and understood.

        Args:
            args: List of command-line arguments

        Returns:
            Dictionary of parsed options
        """
        pass

    @abstractmethod
    def create_netlist(
        self,
        schematic: Path,
        output_path: Optional[Path] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> Path:
        """Create a netlist from a schematic file.

        Args:
            schematic: Path to the schematic file
            output_path: Optional path for the netlist output
            options: Netlist generation options

        Returns:
            Path to the generated netlist

        Raises:
            FileNotFoundError: If schematic file doesn't exist
            RuntimeError: If netlist generation fails
        """
        pass

    @abstractmethod
    def get_default_options(self) -> Dict[str, Any]:
        """Get default simulation options for this simulator.

        Returns:
            Dictionary of default options with their values
        """
        pass

    @abstractmethod
    def validate_options(self, options: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate simulation options.

        Args:
            options: Dictionary of options to validate

        Returns:
            Tuple of (is_valid, list_of_error_messages)
        """
        pass

    def is_analysis_supported(self, analysis_type: str) -> bool:
        """Check if a specific analysis type is supported.

        Args:
            analysis_type: Type of analysis (e.g., "tran", "ac", "dc")

        Returns:
            True if supported, False otherwise
        """
        return analysis_type.lower() in [a.lower() for a in self.supported_analyses]

    def get_library_paths(self) -> List[Path]:
        """Get default library search paths for this simulator.

        Returns:
            List of Path objects for library directories
        """
        info = self.validate_installation()
        return info.library_paths

    def get_process_name(self) -> str:
        """Get the process name for this simulator.

        This is used for process management and cleanup.

        Returns:
            Process name as it appears in system process list
        """
        info = self.validate_installation()
        return info.executable_path.name
