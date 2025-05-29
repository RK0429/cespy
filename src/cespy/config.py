"""
Configuration management for cespy.

This module provides centralized configuration management with support for
environment variables, configuration files, and runtime updates.
"""

import os
import json
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Callable

from cespy.core.constants import Defaults, Encodings, Simulators
from cespy.exceptions import ConfigurationError, InvalidConfigurationError


@dataclass
class SimulatorConfig:
    """Configuration for individual simulators."""

    executable_path: Optional[str] = None
    library_paths: List[str] = field(default_factory=list)
    default_timeout: float = Defaults.SIMULATION_TIMEOUT
    wine_prefix: Optional[str] = None
    environment: Dict[str, str] = field(default_factory=dict)
    command_line_args: List[str] = field(default_factory=list)

    def merge(self, other: "SimulatorConfig") -> None:
        """Merge another configuration into this one."""
        if other.executable_path:
            self.executable_path = other.executable_path
        if other.library_paths:
            self.library_paths.extend(other.library_paths)
        if other.default_timeout != Defaults.SIMULATION_TIMEOUT:
            self.default_timeout = other.default_timeout
        if other.wine_prefix:
            self.wine_prefix = other.wine_prefix
        self.environment.update(other.environment)
        self.command_line_args.extend(other.command_line_args)


@dataclass
class ServerConfig:
    """Configuration for client-server operations."""

    host: str = Defaults.SERVER_HOST
    port: int = Defaults.SERVER_PORT
    timeout: float = Defaults.SERVER_TIMEOUT
    max_retries: int = 3
    retry_delay: float = 1.0
    max_parallel_jobs: int = Defaults.PARALLEL_SIMS
    output_folder: str = Defaults.OUTPUT_FOLDER


@dataclass
class CespyConfig:
    """Main configuration class for cespy."""

    # General settings
    default_encoding: str = Encodings.DEFAULT
    default_timeout: float = Defaults.SIMULATION_TIMEOUT
    parallel_sims: int = Defaults.PARALLEL_SIMS
    log_level: str = "INFO"
    debug_mode: bool = False

    # File handling
    output_folder: str = Defaults.OUTPUT_FOLDER
    temp_folder: Optional[str] = None
    auto_cleanup: bool = True
    max_output_size: int = Defaults.MAX_OUTPUT_SIZE

    # Platform-specific
    use_wine: bool = False
    wine_prefix: Optional[str] = None
    force_windows_paths: bool = False

    # Simulator configurations
    simulators: Dict[str, SimulatorConfig] = field(default_factory=dict)

    # Server configuration
    server: ServerConfig = field(default_factory=ServerConfig)

    # Advanced options
    process_poll_interval: float = Defaults.PROCESS_POLL_INTERVAL
    enable_profiling: bool = False
    cache_parsed_files: bool = True

    def __post_init__(self) -> None:
        """Initialize simulator configurations if not provided."""
        if not self.simulators:
            for sim in Simulators.ALL:
                self.simulators[sim] = SimulatorConfig()

    def get_simulator_config(self, simulator: str) -> SimulatorConfig:
        """
        Get configuration for a specific simulator.

        Args:
            simulator: Simulator name

        Returns:
            SimulatorConfig instance

        Raises:
            InvalidConfigurationError: If simulator is not recognized
        """
        if simulator not in self.simulators:
            raise InvalidConfigurationError(
                f"Unknown simulator: {simulator}. "
                f"Valid options: {', '.join(self.simulators.keys())}"
            )
        return self.simulators[simulator]

    def update_from_dict(self, config_dict: Dict[str, Any]) -> None:
        """
        Update configuration from a dictionary.

        Args:
            config_dict: Dictionary with configuration values
        """
        for key, value in config_dict.items():
            if key == "simulators" and isinstance(value, dict):
                for sim_name, sim_config in value.items():
                    if sim_name not in self.simulators:
                        self.simulators[sim_name] = SimulatorConfig()
                    if isinstance(sim_config, dict):
                        for attr, val in sim_config.items():
                            if hasattr(self.simulators[sim_name], attr):
                                setattr(self.simulators[sim_name], attr, val)
            elif key == "server" and isinstance(value, dict):
                for attr, val in value.items():
                    if hasattr(self.server, attr):
                        setattr(self.server, attr, val)
            elif hasattr(self, key):
                setattr(self, key, value)

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        result = asdict(self)
        # Convert simulator configs
        result["simulators"] = {
            name: asdict(config) for name, config in self.simulators.items()
        }
        return result

    @classmethod
    def from_file(cls, filepath: Union[str, Path]) -> "CespyConfig":
        """
        Load configuration from a JSON file.

        Args:
            filepath: Path to configuration file

        Returns:
            CespyConfig instance

        Raises:
            ConfigurationError: If file cannot be read or parsed
        """
        filepath = Path(filepath)
        if not filepath.exists():
            raise ConfigurationError(f"Configuration file not found: {filepath}")

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                config_dict = json.load(f)
        except json.JSONDecodeError as e:
            raise InvalidConfigurationError(f"Invalid JSON in configuration file: {e}")
        except Exception as e:
            raise ConfigurationError(f"Failed to read configuration file: {e}")

        config = cls()
        config.update_from_dict(config_dict)
        return config

    def save_to_file(self, filepath: Union[str, Path]) -> None:
        """
        Save configuration to a JSON file.

        Args:
            filepath: Path to save configuration
        """
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def from_environment(cls) -> "CespyConfig":
        """
        Create configuration from environment variables.

        Environment variables are prefixed with CESPY_, e.g.:
        - CESPY_DEFAULT_TIMEOUT=300
        - CESPY_LOG_LEVEL=DEBUG
        - CESPY_LTSPICE_PATH=/path/to/ltspice

        Returns:
            CespyConfig instance
        """
        config = cls()

        # Map environment variables to config attributes
        env_mapping: Dict[str, tuple[str, Callable[[str], Any]]] = {
            "CESPY_DEFAULT_ENCODING": ("default_encoding", str),
            "CESPY_DEFAULT_TIMEOUT": ("default_timeout", float),
            "CESPY_PARALLEL_SIMS": ("parallel_sims", int),
            "CESPY_LOG_LEVEL": ("log_level", str),
            "CESPY_DEBUG_MODE": ("debug_mode", lambda x: x.lower() == "true"),
            "CESPY_OUTPUT_FOLDER": ("output_folder", str),
            "CESPY_TEMP_FOLDER": ("temp_folder", str),
            "CESPY_USE_WINE": ("use_wine", lambda x: x.lower() == "true"),
            "CESPY_WINE_PREFIX": ("wine_prefix", str),
            "CESPY_SERVER_HOST": ("server.host", str),
            "CESPY_SERVER_PORT": ("server.port", int),
        }

        for env_var, (attr_path, converter) in env_mapping.items():
            value = os.environ.get(env_var)
            if value is not None:
                try:
                    converted_value = converter(value)
                    if "." in attr_path:
                        # Handle nested attributes
                        obj_name, attr_name = attr_path.split(".", 1)
                        obj = getattr(config, obj_name)
                        setattr(obj, attr_name, converted_value)
                    else:
                        setattr(config, attr_path, converted_value)
                except (ValueError, AttributeError) as e:
                    logging.warning(f"Failed to set {attr_path} from {env_var}: {e}")

        # Handle simulator-specific paths
        for sim in Simulators.ALL:
            env_var = f"CESPY_{sim.upper()}_PATH"
            path = os.environ.get(env_var)
            if path:
                config.simulators[sim].executable_path = path

        return config


# Global configuration instance
_global_config: Optional[CespyConfig] = None


def get_config() -> CespyConfig:
    """
    Get the global configuration instance.

    Returns:
        Global CespyConfig instance
    """
    global _global_config
    if _global_config is None:
        _global_config = CespyConfig.from_environment()
    return _global_config


def set_config(config: CespyConfig) -> None:
    """
    Set the global configuration instance.

    Args:
        config: CespyConfig instance to use globally
    """
    global _global_config
    _global_config = config


def load_config(filepath: Optional[Union[str, Path]] = None) -> CespyConfig:
    """
    Load configuration from file or environment.

    Args:
        filepath: Optional path to configuration file

    Returns:
        Loaded configuration
    """
    if filepath:
        config = CespyConfig.from_file(filepath)
    else:
        # Try default locations
        config_locations = [
            Path.home() / ".cespy" / "config.json",
            Path.cwd() / "cespy.json",
            Path.cwd() / ".cespy.json",
        ]

        loaded_config: Optional[CespyConfig] = None
        for location in config_locations:
            if location.exists():
                try:
                    loaded_config = CespyConfig.from_file(location)
                    break
                except ConfigurationError:
                    continue

        if loaded_config is None:
            loaded_config = CespyConfig.from_environment()
            config = loaded_config

    set_config(config)
    return config
