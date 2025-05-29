"""
Exception hierarchy for cespy.

This module defines a comprehensive exception hierarchy for all error
conditions that can occur in the cespy library.
"""

from typing import Any, Dict, List, Optional


class CespyError(Exception):
    """Base exception for all cespy errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialize CespyError.

        Args:
            message: Error message
            details: Optional dictionary with additional error details
        """
        super().__init__(message)
        self.message = message
        self.details: Dict[str, Any] = details or {}


# Simulator-related exceptions
class SimulatorError(CespyError):
    """Base class for errors related to simulator execution."""


class SimulatorNotFoundError(SimulatorError):
    """Raised when a simulator executable cannot be found."""

    def __init__(
        self, simulator_name: str, search_paths: Optional[List[str]] = None
    ) -> None:
        """
        Initialize SimulatorNotFoundError.

        Args:
            simulator_name: Name of the simulator
            search_paths: Paths that were searched
        """
        message = f"Simulator executable not found: {simulator_name}"
        details = {"simulator": simulator_name, "search_paths": search_paths}
        super().__init__(message, details)


class SimulatorNotInstalledError(SimulatorError):
    """Raised when a simulator is not properly installed."""


class SimulationTimeoutError(SimulatorError):
    """Raised when a simulation exceeds its timeout."""

    def __init__(self, timeout: float, netlist: Optional[str] = None) -> None:
        """
        Initialize SimulationTimeoutError.

        Args:
            timeout: Timeout value in seconds
            netlist: Optional netlist file that timed out
        """
        message = f"Simulation timed out after {timeout} seconds"
        details = {"timeout": timeout, "netlist": netlist}
        super().__init__(message, details)


class SimulationFailedError(SimulatorError):
    """Raised when a simulation fails to complete successfully."""

    def __init__(
        self,
        message: str,
        exit_code: Optional[int] = None,
        stderr: Optional[str] = None,
    ) -> None:
        """
        Initialize SimulationFailedError.

        Args:
            message: Error message
            exit_code: Process exit code
            stderr: Standard error output
        """
        details = {"exit_code": exit_code, "stderr": stderr}
        super().__init__(message, details)


# File format exceptions
class FileFormatError(CespyError):
    """Base class for file format related errors."""


class InvalidNetlistError(FileFormatError):
    """Raised when a netlist file is invalid or corrupted."""


class InvalidSchematicError(FileFormatError):
    """Raised when a schematic file is invalid or corrupted."""


class InvalidRawFileError(FileFormatError):
    """Raised when a raw simulation output file is invalid."""


class UnsupportedFormatError(FileFormatError):
    """Raised when a file format is not supported."""

    def __init__(
        self, file_format: str, supported_formats: Optional[List[str]] = None
    ) -> None:
        """
        Initialize UnsupportedFormatError.

        Args:
            file_format: The unsupported format
            supported_formats: List of supported formats
        """
        message = f"Unsupported file format: {file_format}"
        details = {"format": file_format, "supported": supported_formats}
        super().__init__(message, details)


# Component and circuit exceptions
class ComponentError(CespyError):
    """Base class for component-related errors."""


class ComponentNotFoundError(ComponentError):
    """Raised when a component reference is not found in the circuit."""

    def __init__(
        self, component_ref: str, available_components: Optional[List[str]] = None
    ) -> None:
        """
        Initialize ComponentNotFoundError.

        Args:
            component_ref: The component reference that wasn't found
            available_components: Optional list of available components
        """
        message = f"Component not found: {component_ref}"
        details = {"component": component_ref, "available": available_components}
        super().__init__(message, details)


class InvalidComponentError(ComponentError):
    """Raised when a component has invalid parameters or configuration."""

    def __init__(self, component_ref: str, reason: str) -> None:
        """
        Initialize InvalidComponentError.

        Args:
            component_ref: The invalid component reference
            reason: Reason why the component is invalid
        """
        message = f"Invalid component {component_ref}: {reason}"
        details = {"component": component_ref, "reason": reason}
        super().__init__(message, details)


class ParameterError(ComponentError):
    """Raised when there's an error with component parameters."""

    def __init__(self, parameter_name: str, value: Any, reason: str) -> None:
        """
        Initialize ParameterError.

        Args:
            parameter_name: Name of the parameter
            value: The problematic value
            reason: Reason for the error
        """
        message = f"Invalid parameter {parameter_name}={value}: {reason}"
        details = {"parameter": parameter_name, "value": value, "reason": reason}
        super().__init__(message, details)


class ParameterNotFoundError(ComponentError):
    """Raised when a parameter is not found in a component."""

    def __init__(self, component_ref: str, parameter_name: str) -> None:
        """
        Initialize ParameterNotFoundError.

        Args:
            component_ref: The component reference
            parameter_name: The parameter that wasn't found
        """
        message = f"Parameter '{parameter_name}' not found in component {component_ref}"
        details = {"component": component_ref, "parameter": parameter_name}
        super().__init__(message, details)


class ValidationError(ComponentError):
    """Raised when component or circuit validation fails."""

    def __init__(
        self,
        message: str,
        component_ref: Optional[str] = None,
        validation_errors: Optional[List[str]] = None,
    ) -> None:
        """
        Initialize ValidationError.

        Args:
            message: Error message
            component_ref: Optional component reference
            validation_errors: List of validation error details
        """
        details = {"component": component_ref, "validation_errors": validation_errors}
        super().__init__(message, details)


# Analysis exceptions
class AnalysisError(CespyError):
    """Base class for analysis-related errors."""


class OptimizationError(AnalysisError):
    """Raised when an optimization operation fails."""

    def __init__(self, message: str, optimization_type: Optional[str] = None) -> None:
        """
        Initialize OptimizationError.

        Args:
            message: Error message
            optimization_type: Type of optimization that failed
        """
        details = {"optimization_type": optimization_type}
        super().__init__(message, details)


class ConvergenceError(AnalysisError):
    """Raised when a simulation fails to converge."""


class InsufficientDataError(AnalysisError):
    """Raised when there's not enough data for analysis."""


# I/O exceptions
class CespyIOError(CespyError):
    """Base class for I/O related errors."""


class CespyFileNotFoundError(CespyIOError):
    """Raised when a required file is not found."""

    def __init__(self, filepath: str) -> None:
        """
        Initialize FileNotFoundError.

        Args:
            filepath: Path to the missing file
        """
        message = f"File not found: {filepath}"
        details = {"filepath": filepath}
        super().__init__(message, details)


class CespyPermissionError(CespyIOError):
    """Raised when there's insufficient permission to access a file."""


class EncodingError(CespyIOError):
    """Raised when there's an encoding/decoding error."""

    def __init__(
        self, filepath: str, encoding: str, original_error: Optional[Exception] = None
    ) -> None:
        """
        Initialize EncodingError.

        Args:
            filepath: Path to the file with encoding issues
            encoding: The encoding that failed
            original_error: Original exception if any
        """
        message = f"Failed to decode file {filepath} with encoding {encoding}"
        details = {
            "filepath": filepath,
            "encoding": encoding,
            "original_error": str(original_error) if original_error else None,
        }
        super().__init__(message, details)


# Configuration exceptions
class ConfigurationError(CespyError):
    """Base class for configuration-related errors."""


class InvalidConfigurationError(ConfigurationError):
    """Raised when configuration is invalid."""


class MissingConfigurationError(ConfigurationError):
    """Raised when required configuration is missing."""


# Server/Client exceptions
class ServerError(CespyError):
    """Base class for server-related errors."""


class ServerNotRunningError(ServerError):
    """Raised when trying to connect to a server that's not running."""


class ServerConnectionError(ServerError):
    """Raised when unable to connect to the server."""


class ServerTimeoutError(ServerError):
    """Raised when a server operation times out."""


# Deprecated functionality
class DeprecationError(CespyError):
    """Raised when using deprecated functionality."""

    def __init__(self, old_feature: str, new_feature: Optional[str] = None) -> None:
        """
        Initialize DeprecationError.

        Args:
            old_feature: The deprecated feature
            new_feature: Optional replacement feature
        """
        message = f"Deprecated feature: {old_feature}"
        if new_feature:
            message += f". Use {new_feature} instead"
        details = {"old": old_feature, "new": new_feature}
        super().__init__(message, details)
