#!/usr/bin/env python
# coding=utf-8
"""Factory for creating simulator instances with automatic detection and configuration.

This module provides a factory pattern implementation for creating simulator
instances, with support for automatic detection, custom paths, and validation.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Type, Union

# Core imports
from ..core import constants as core_constants
from ..exceptions import SimulatorNotFoundError, InvalidSimulatorError

# Import simulator implementations
from ..simulators.ltspice_simulator import LTspice
from ..simulators.ngspice_simulator import NGspiceSimulator
from ..simulators.qspice_simulator import Qspice
from ..simulators.xyce_simulator import XyceSimulator

from .simulator_interface import SimulatorInfo, SimulatorStatus
from .simulator_locator import SimulatorLocator
from .simulator import Simulator

_logger = logging.getLogger("cespy.SimulatorFactory")


class SimulatorFactory:
    """Factory for creating and configuring simulator instances."""

    # Registry of simulator implementations
    SIMULATOR_REGISTRY: Dict[str, Type[Simulator]] = {
        core_constants.Simulators.LTSPICE: LTspice,
        core_constants.Simulators.NGSPICE: NGspiceSimulator,
        core_constants.Simulators.QSPICE: Qspice,
        core_constants.Simulators.XYCE: XyceSimulator,
    }

    # Cache for created simulator instances
    _simulator_cache: Dict[str, Simulator] = {}

    @classmethod
    def create(
        cls,
        simulator_type: str,
        custom_path: Optional[Union[str, Path]] = None,
        validate: bool = True,
        use_cache: bool = True,
    ) -> Simulator:
        """Create a simulator instance with automatic detection and configuration.

        Args:
            simulator_type: Type of simulator from core_constants.Simulators
            custom_path: Optional custom path to simulator executable
            validate: Whether to validate the installation
            use_cache: Whether to use cached instances

        Returns:
            Configured simulator instance

        Raises:
            SimulatorNotFoundError: If simulator cannot be found
            InvalidSimulatorError: If simulator is found but invalid
        """
        # Normalize simulator type
        simulator_type = simulator_type.lower()

        # Check cache
        cache_key = f"{simulator_type}:{custom_path or 'default'}"
        if use_cache and cache_key in cls._simulator_cache:
            _logger.debug("Using cached simulator for %s", cache_key)
            return cls._simulator_cache[cache_key]

        # Get simulator class
        simulator_class = cls.SIMULATOR_REGISTRY.get(simulator_type)
        if not simulator_class:
            raise InvalidSimulatorError(
                f"Unknown simulator type: {simulator_type}. "
                f"Available types: {list(cls.SIMULATOR_REGISTRY.keys())}"
            )

        # Locate simulator
        locator = SimulatorLocator(simulator_type)
        exe_path, uses_wine = locator.find_simulator(
            str(custom_path) if custom_path else None
        )

        if not exe_path:
            raise SimulatorNotFoundError(
                f"Could not find {simulator_type} simulator. "
                f"Please install it or provide a custom path."
            )

        # Create simulator instance
        _logger.info("Found %s at %s (wine=%s)", simulator_type, exe_path, uses_wine)

        # Build command list
        if uses_wine:
            spice_exe = locator.get_wine_command() + [str(exe_path)]
        else:
            spice_exe = [str(exe_path)]

        # Create instance
        simulator_instance = simulator_class()
        # Configure the simulator instance
        simulator_instance.spice_exe = spice_exe
        simulator_instance.process_name = exe_path.name

        # Get library paths
        lib_paths = locator.get_library_paths(exe_path)
        simulator_instance._default_lib_paths = [str(p) for p in lib_paths]

        # Validate if requested
        if validate:
            is_valid, version_or_error = locator.validate_executable(
                exe_path, uses_wine
            )
            if not is_valid:
                raise InvalidSimulatorError(
                    f"{simulator_type} found but validation failed: {version_or_error}"
                )
            _logger.info("%s version: %s", simulator_type, version_or_error)
        # Cache the instance
        if use_cache:
            cls._simulator_cache[cache_key] = simulator_instance

        return simulator_instance

    @classmethod
    def detect_all(cls) -> Dict[str, SimulatorInfo]:
        """Detect all available simulators on the system.

        Returns:
            Dictionary mapping simulator types to their info
        """
        available = {}

        for sim_type in cls.SIMULATOR_REGISTRY:
            try:
                simulator = cls.create(sim_type, validate=True, use_cache=False)
                locator = SimulatorLocator(sim_type)
                exe_path, _ = locator.find_simulator()

                if exe_path:
                    # Get version info
                    is_valid, version = locator.validate_executable(exe_path)

                    info = SimulatorInfo(
                        name=sim_type,
                        version=version if is_valid else "unknown",
                        executable_path=exe_path,
                        status=SimulatorStatus.AVAILABLE
                        if is_valid
                        else SimulatorStatus.INVALID_VERSION,
                        library_paths=[
                            Path(p) for p in simulator.get_default_library_paths()
                        ],
                        supported_analyses=cls._get_supported_analyses(sim_type),
                        max_threads=cls._get_max_threads(sim_type),
                    )
                    available[sim_type] = info

            except (SimulatorNotFoundError, InvalidSimulatorError) as e:
                _logger.debug("Simulator %s not available: %s", sim_type, e)
                continue

        return available

    @classmethod
    def create_from_path(
        cls, executable_path: Union[str, Path], simulator_type: Optional[str] = None
    ) -> Simulator:
        """Create a simulator from a specific executable path.

        Args:
            executable_path: Path to the simulator executable
            simulator_type: Optional type hint (will be auto-detected if not provided)

        Returns:
            Configured simulator instance

        Raises:
            InvalidSimulatorError: If simulator type cannot be determined
        """
        path = Path(executable_path)

        # Auto-detect simulator type if not provided
        if not simulator_type:
            simulator_type = cls._detect_type_from_path(path)
            if not simulator_type:
                raise InvalidSimulatorError(
                    f"Could not determine simulator type from path: {path}"
                )

        return cls.create(simulator_type, custom_path=path, validate=True)

    @classmethod
    def _detect_type_from_path(cls, path: Path) -> Optional[str]:
        """Detect simulator type from executable path.

        Args:
            path: Path to executable

        Returns:
            Simulator type or None
        """
        name_lower = path.name.lower()

        # Check for known patterns
        patterns = {
            core_constants.Simulators.LTSPICE: ["ltspice", "scad3", "xviix64"],
            core_constants.Simulators.NGSPICE: ["ngspice"],
            core_constants.Simulators.QSPICE: ["qspice"],
            core_constants.Simulators.XYCE: ["xyce"],
        }

        for sim_type, patterns_list in patterns.items():
            if any(pattern in name_lower for pattern in patterns_list):
                return sim_type

        return None

    @classmethod
    def _get_supported_analyses(cls, simulator_type: str) -> List[str]:
        """Get supported analysis types for a simulator.

        Args:
            simulator_type: Type of simulator

        Returns:
            List of supported analysis types
        """
        # Common analyses supported by most SPICE simulators
        common = ["dc", "ac", "tran", "op", "noise", "tf"]

        # Simulator-specific additions
        specific = {
            core_constants.Simulators.LTSPICE: common + ["four", "step"],
            core_constants.Simulators.NGSPICE: common + ["pz", "sens", "disto"],
            core_constants.Simulators.QSPICE: common + ["four"],
            core_constants.Simulators.XYCE: common + ["hb", "mpde", "step"],
        }

        return specific.get(simulator_type, common)

    @classmethod
    def _get_max_threads(cls, simulator_type: str) -> int:
        """Get maximum thread count for a simulator.

        Args:
            simulator_type: Type of simulator

        Returns:
            Maximum number of threads
        """
        # Some simulators support multi-threading
        thread_support = {
            core_constants.Simulators.LTSPICE: 4,  # LTspice can use up to 4 threads
            core_constants.Simulators.NGSPICE: 1,  # Single-threaded
            core_constants.Simulators.QSPICE: 8,  # QSpice has good parallelization
            core_constants.Simulators.XYCE: 16,  # Xyce supports MPI parallelization
        }

        return thread_support.get(simulator_type, 1)

    @classmethod
    def clear_cache(cls) -> None:
        """Clear the simulator cache."""
        cls._simulator_cache.clear()
        _logger.debug("Simulator cache cleared")
