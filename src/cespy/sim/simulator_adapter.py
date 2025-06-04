#!/usr/bin/env python
# coding=utf-8
"""Adapter to bridge the new simulator interface with existing implementations.

This module provides an adapter class that allows existing Simulator subclasses
to work with the new ISimulator interface, ensuring backward compatibility while
enabling the use of enhanced features.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Type

from .simulator import Simulator
from .simulator_interface import (
    ISimulator,
    SimulatorInfo,
    SimulatorStatus,
    SimulationCommand,
)
from .simulator_locator import SimulatorLocator
from ..core import constants as core_constants
from ..exceptions import SimulatorNotInstalledError

_logger = logging.getLogger("cespy.SimulatorAdapter")


class SimulatorAdapter(ISimulator):
    """Adapter that bridges the existing Simulator classes with the new interface.

    This adapter allows gradual migration to the new interface while maintaining
    backward compatibility with existing code.
    """

    def __init__(self, simulator_class: Type[Simulator], simulator_type: str):
        """Initialize adapter with an existing simulator class.

        Args:
            simulator_class: The existing Simulator subclass
            simulator_type: Type identifier from core_constants.Simulators
        """
        self.simulator_class = simulator_class
        self.simulator_name = simulator_type
        self.supported_analyses = ["dc", "ac", "tran", "op", "noise", "tf"]

        # Determine supported platforms based on simulator
        if simulator_type == core_constants.Simulators.QSPICE:
            self.supported_platforms = ["windows"]
        else:
            self.supported_platforms = ["windows", "linux", "darwin"]

    def validate_installation(self) -> SimulatorInfo:
        """Verify simulator is properly installed and return its information."""
        # Check if simulator is available
        if not self.simulator_class.is_available():
            raise SimulatorNotInstalledError(
                f"{self.simulator_name} is not installed or not found in PATH"
            )

        # Get executable path
        if self.simulator_class.spice_exe:
            exe_path = Path(self.simulator_class.spice_exe[-1])
        else:
            raise SimulatorNotInstalledError(
                f"No executable path set for {self.simulator_name}"
            )

        # Get version using locator
        locator = SimulatorLocator(self.simulator_name)
        is_valid, version = locator.validate_executable(exe_path)

        # Get library paths
        lib_paths = [Path(p) for p in self.simulator_class.get_default_library_paths()]

        # Determine status
        if is_valid:
            status = SimulatorStatus.AVAILABLE
        else:
            status = SimulatorStatus.INVALID_VERSION

        return SimulatorInfo(
            name=self.simulator_name,
            version=version if is_valid else "unknown",
            executable_path=exe_path,
            status=status,
            library_paths=lib_paths,
            supported_analyses=self.supported_analyses,
            max_threads=self._get_max_threads(),
        )

    def get_version(self) -> str:
        """Get simulator version information."""
        info = self.validate_installation()
        return info.version

    def prepare_command(
        self,
        netlist: Path,
        options: Optional[Dict[str, Any]] = None,
        raw_switches: Optional[List[str]] = None,
    ) -> SimulationCommand:
        """Prepare command line for execution."""
        # Get base executable
        executable = self.simulator_class.spice_exe.copy()

        # Build arguments based on simulator type
        arguments = []

        # Add simulator-specific flags
        if self.simulator_name == core_constants.Simulators.LTSPICE:
            arguments.extend(["-Run", "-b", str(netlist)])
        elif self.simulator_name == core_constants.Simulators.NGSPICE:
            arguments.extend(["-b", str(netlist)])
        elif self.simulator_name == core_constants.Simulators.QSPICE:
            arguments.extend(["-b", str(netlist)])
        elif self.simulator_name == core_constants.Simulators.XYCE:
            arguments.append(str(netlist))

        # Add options
        if options:
            for key, value in options.items():
                validated_switches = self.simulator_class.valid_switch(key, value)
                arguments.extend(validated_switches)

        # Add raw switches
        if raw_switches:
            arguments.extend(raw_switches)

        # Prepare environment
        environment: Dict[str, str] = {}

        return SimulationCommand(
            executable=executable,
            arguments=arguments,
            environment=environment,
            working_directory=netlist.parent,
            timeout=options.get("timeout") if options else None,
        )

    def parse_arguments(self, args: List[str]) -> Dict[str, Any]:
        """Parse command-line arguments into structured options."""
        options: Dict[str, Any] = {}

        # Simple parsing for common flags
        i = 0
        while i < len(args):
            arg = args[i]

            if arg in ["-Run", "-b", "-r"]:
                # Skip these as they're standard
                i += 1
            elif arg.startswith("-"):
                # Check if next arg is a value
                if i + 1 < len(args) and not args[i + 1].startswith("-"):
                    options[arg] = args[i + 1]
                    i += 2
                else:
                    options[arg] = True
                    i += 1
            else:
                i += 1

        return options

    def create_netlist(
        self,
        schematic: Path,
        output_path: Optional[Path] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> Path:
        """Create a netlist from a schematic file."""
        if hasattr(self.simulator_class, "create_netlist"):
            return self.simulator_class.create_netlist(
                schematic,
                cmd_line_switches=options.get("switches", []) if options else None,
                timeout=options.get("timeout") if options else None,
            )
        raise NotImplementedError(
            f"{self.simulator_name} does not support netlist creation from schematics"
        )

    def get_default_options(self) -> Dict[str, Any]:
        """Get default simulation options for this simulator."""
        defaults = {
            "timeout": 300.0,
            "ascii": False,
        }

        # Simulator-specific defaults
        if self.simulator_name == core_constants.Simulators.LTSPICE:
            defaults.update(
                {
                    "fastaccess": False,
                    "threads": 1,
                }
            )

        return defaults

    def validate_options(self, options: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate simulation options."""
        errors = []

        # Validate timeout
        if "timeout" in options:
            if (
                not isinstance(options["timeout"], (int, float))
                or options["timeout"] <= 0
            ):
                errors.append("timeout must be a positive number")

        # Validate threads
        if "threads" in options:
            max_threads = self._get_max_threads()
            if not isinstance(options["threads"], int) or options["threads"] < 1:
                errors.append("threads must be a positive integer")
            elif options["threads"] > max_threads:
                errors.append(
                    f"threads cannot exceed {max_threads} for {self.simulator_name}"
                )

        # Use simulator's valid_switch for other options
        for key, value in options.items():
            if key not in ["timeout", "threads"]:
                try:
                    self.simulator_class.valid_switch(key, value)
                except (ValueError, TypeError, AttributeError) as e:
                    errors.append(f"Invalid option {key}: {str(e)}")

        return len(errors) == 0, errors

    def _get_max_threads(self) -> int:
        """Get maximum thread count for this simulator."""
        thread_limits = {
            core_constants.Simulators.LTSPICE: 4,
            core_constants.Simulators.NGSPICE: 1,
            core_constants.Simulators.QSPICE: 8,
            core_constants.Simulators.XYCE: 16,
        }
        return thread_limits.get(self.simulator_name, 1)
