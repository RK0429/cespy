#!/usr/bin/env python
# coding=utf-8
"""API consistency utilities and deprecation management.

This module provides utilities for maintaining API consistency across the
codebase, including standardized method naming, parameter ordering, and
deprecation warnings for old APIs.
"""

import functools
import logging
import warnings
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union

_logger = logging.getLogger("cespy.APIConsistency")

F = TypeVar("F", bound=Callable[..., Any])


class DeprecationLevel:
    """Deprecation levels for API changes."""

    INFO = "info"  # Informational, will be deprecated
    WARNING = "warning"  # Deprecated, still works
    ERROR = "error"  # Deprecated, may not work
    REMOVED = "removed"  # No longer available


def deprecated(
    version: str,
    reason: str,
    replacement: Optional[str] = None,
    level: str = DeprecationLevel.WARNING,
    stacklevel: int = 2,
) -> Callable[[F], F]:
    """Decorator to mark functions/methods as deprecated.

    Args:
        version: Version when deprecation was introduced
        reason: Reason for deprecation
        replacement: Suggested replacement (if any)
        level: Deprecation level
        stacklevel: Stack level for warning location

    Returns:
        Decorated function with deprecation warning
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Format deprecation message
            message = f"{func.__name__} is deprecated since version {version}: {reason}"
            if replacement:
                message += f" Use {replacement} instead."

            # Issue appropriate warning based on level
            if level == DeprecationLevel.INFO:
                _logger.info("Deprecation notice: %s", message)
            elif level == DeprecationLevel.WARNING:
                warnings.warn(message, DeprecationWarning, stacklevel=stacklevel)
            elif level == DeprecationLevel.ERROR:
                warnings.warn(message, FutureWarning, stacklevel=stacklevel)
            elif level == DeprecationLevel.REMOVED:
                raise RuntimeError(f"API removed: {message}")

            return func(*args, **kwargs)

        # Add deprecation metadata
        setattr(wrapper, "__deprecated__", True)
        setattr(
            wrapper,
            "__deprecation_info__",
            {
                "version": version,
                "reason": reason,
                "replacement": replacement,
                "level": level,
            },
        )

        return wrapper  # type: ignore

    return decorator


def standardize_parameters(parameter_map: Dict[str, str]) -> Callable[[F], F]:
    """Decorator to standardize parameter names while maintaining backward compatibility.

    Args:
        parameter_map: Mapping from old parameter names to new names

    Returns:
        Decorated function with parameter name standardization
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Convert old parameter names to new ones
            new_kwargs = {}
            for key, value in kwargs.items():
                if key in parameter_map:
                    new_key = parameter_map[key]
                    if new_key in kwargs:
                        # Both old and new names provided - warn and use new
                        warnings.warn(
                            f"Both '{key}' (deprecated) and '{new_key}' provided. "
                            f"Using '{new_key}' value.",
                            DeprecationWarning,
                            stacklevel=2,
                        )
                        new_kwargs[new_key] = kwargs[new_key]
                    else:
                        # Only old name provided - convert and warn
                        warnings.warn(
                            f"Parameter '{key}' is deprecated. Use '{new_key}' instead.",
                            DeprecationWarning,
                            stacklevel=2,
                        )
                        new_kwargs[new_key] = value
                else:
                    new_kwargs[key] = value

            return func(*args, **new_kwargs)

        return wrapper  # type: ignore

    return decorator


class APIStandardizer:
    """Utility class for API standardization across the codebase."""

    # Standardized method naming conventions
    STANDARD_METHOD_NAMES = {
        # File operations
        "load": "load_file",
        "save": "save_file",
        "read": "read_file",
        "write": "write_file",
        # Component operations
        "get_component": "get_component_value",
        "set_component": "set_component_value",
        "add_component": "add_component",
        "remove_component": "remove_component",
        # Parameter operations
        "get_param": "get_parameter",
        "set_param": "set_parameter",
        "add_param": "add_parameter",
        "remove_param": "remove_parameter",
        # Simulation operations
        "run_sim": "run_simulation",
        "execute": "run_simulation",
        "simulate": "run_simulation",
        # Analysis operations
        "analyze": "run_analysis",
        "analyse": "run_analysis",  # British spelling
        # Result operations
        "get_result": "get_results",
        "fetch_result": "get_results",
    }

    # Standardized parameter naming conventions
    STANDARD_PARAMETER_NAMES = {
        # File paths
        "file": "file_path",
        "filename": "file_path",
        "filepath": "file_path",
        "path": "file_path",
        # Component references
        "comp": "component",
        "component_ref": "component",
        "ref": "component_reference",
        # Values
        "val": "value",
        "new_val": "new_value",
        "old_val": "old_value",
        # Simulation parameters
        "sim_time": "simulation_time",
        "timeout_val": "timeout",
        "max_time": "timeout",
        # Boolean flags
        "wait": "wait_completion",
        "async": "asynchronous",
        "sync": "synchronous",
        # Callback parameters
        "cb": "callback",
        "callback_func": "callback",
        "cb_args": "callback_args",
    }

    # Standard parameter ordering for common operations
    STANDARD_PARAMETER_ORDER = {
        "file_operations": ["file_path", "encoding", "mode"],
        "component_operations": ["component_reference", "value", "attributes"],
        "simulation_operations": ["circuit_file", "runner", "timeout", "callback"],
        "analysis_operations": ["circuit_file", "parameters", "num_runs", "parallel"],
    }

    @classmethod
    def get_standard_method_name(cls, method_name: str) -> str:
        """Get standardized method name.

        Args:
            method_name: Original method name

        Returns:
            Standardized method name
        """
        return cls.STANDARD_METHOD_NAMES.get(method_name, method_name)

    @classmethod
    def get_standard_parameter_name(cls, param_name: str) -> str:
        """Get standardized parameter name.

        Args:
            param_name: Original parameter name

        Returns:
            Standardized parameter name
        """
        return cls.STANDARD_PARAMETER_NAMES.get(param_name, param_name)

    @classmethod
    def validate_parameter_order(
        cls, operation_type: str, parameters: List[str]
    ) -> List[str]:
        """Validate and suggest correct parameter order.

        Args:
            operation_type: Type of operation
            parameters: Current parameter order

        Returns:
            Suggested parameter order
        """
        if operation_type not in cls.STANDARD_PARAMETER_ORDER:
            return parameters

        standard_order = cls.STANDARD_PARAMETER_ORDER[operation_type]

        # Sort parameters according to standard order
        ordered_params = []
        remaining_params = parameters.copy()

        # Add parameters in standard order
        for std_param in standard_order:
            if std_param in remaining_params:
                ordered_params.append(std_param)
                remaining_params.remove(std_param)

        # Add any remaining parameters at the end
        ordered_params.extend(remaining_params)

        return ordered_params


def create_compatibility_wrapper(
    old_name: str, new_name: str, version: str, module_dict: Dict[str, Any]
) -> None:
    """Create a compatibility wrapper for renamed functions/classes.

    Args:
        old_name: Old function/class name
        new_name: New function/class name
        version: Version when change was made
        module_dict: Module's __dict__ to update
    """
    if new_name in module_dict:
        original = module_dict[new_name]

        @deprecated(
            version=version,
            reason=f"Name changed from {old_name} to {new_name}",
            replacement=new_name,
        )
        def wrapper(*args, **kwargs) -> Any:
            return original(*args, **kwargs)

        # Copy attributes for classes
        if hasattr(original, "__name__"):
            wrapper.__name__ = old_name
            wrapper.__qualname__ = old_name

        module_dict[old_name] = wrapper


class ParameterValidator:
    """Validator for standardizing and validating function parameters."""

    def __init__(self) -> None:
        self.standardizer = APIStandardizer()

    def validate_file_path_parameter(self, file_path: Any) -> Union[str, None]:
        """Validate and standardize file path parameter.

        Args:
            file_path: File path to validate

        Returns:
            Standardized file path or None

        Raises:
            TypeError: If file_path is not a valid type
        """
        if file_path is None:
            return None

        if isinstance(file_path, (str, bytes)):
            return str(file_path)

        # Handle Path-like objects
        if hasattr(file_path, "__fspath__"):
            return str(file_path)

        # Handle file-like objects
        if hasattr(file_path, "name"):
            return str(file_path.name)

        raise TypeError(f"Invalid file_path type: {type(file_path)}")

    def validate_timeout_parameter(self, timeout: Any) -> Optional[float]:
        """Validate and standardize timeout parameter.

        Args:
            timeout: Timeout value to validate

        Returns:
            Standardized timeout value or None

        Raises:
            ValueError: If timeout is not a valid value
        """
        if timeout is None:
            return None

        if isinstance(timeout, (int, float)):
            if timeout <= 0:
                raise ValueError("Timeout must be positive")
            return float(timeout)

        if isinstance(timeout, str):
            try:
                value = float(timeout)
                if value <= 0:
                    raise ValueError("Timeout must be positive")
                return value
            except ValueError:
                raise ValueError(f"Invalid timeout format: {timeout}")

        raise TypeError(f"Invalid timeout type: {type(timeout)}")

    def validate_boolean_parameter(self, value: Any, param_name: str) -> bool:
        """Validate and standardize boolean parameter.

        Args:
            value: Value to validate
            param_name: Parameter name for error messages

        Returns:
            Boolean value

        Raises:
            TypeError: If value cannot be converted to boolean
        """
        if isinstance(value, bool):
            return value

        if isinstance(value, (int, float)):
            return bool(value)

        if isinstance(value, str):
            lower_val = value.lower()
            if lower_val in ("true", "1", "yes", "on", "enable", "enabled"):
                return True
            elif lower_val in ("false", "0", "no", "off", "disable", "disabled"):
                return False
            else:
                raise ValueError(f"Invalid boolean value for {param_name}: {value}")

        raise TypeError(f"Cannot convert {type(value)} to boolean for {param_name}")


def ensure_api_consistency(func: F) -> F:
    """Decorator to ensure API consistency in function calls.

    This decorator performs automatic parameter validation and standardization.

    Args:
        func: Function to decorate

    Returns:
        Decorated function with API consistency checks
    """
    validator = ParameterValidator()

    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        # Get function signature for parameter validation
        import inspect

        sig = inspect.signature(func)

        # Validate common parameter types
        validated_kwargs = {}
        for param_name, param_value in kwargs.items():
            if param_name in sig.parameters:
                param = sig.parameters[param_name]

                # Validate based on parameter name patterns
                if "file" in param_name.lower() or "path" in param_name.lower():
                    validated_kwargs[
                        param_name
                    ] = validator.validate_file_path_parameter(param_value)
                elif "timeout" in param_name.lower():
                    timeout_val = validator.validate_timeout_parameter(param_value)
                    validated_kwargs[param_name] = timeout_val
                elif (
                    param.annotation == bool or "bool" in str(param.annotation).lower()
                ):
                    validated_kwargs[param_name] = validator.validate_boolean_parameter(
                        param_value, param_name
                    )
                else:
                    validated_kwargs[param_name] = param_value
            else:
                validated_kwargs[param_name] = param_value

        return func(*args, **validated_kwargs)

    return wrapper  # type: ignore


# Pre-defined compatibility wrappers for common renames
COMPATIBILITY_MAPPINGS = {
    # Simulator class renames
    "LTspiceSimulator": "LTSpiceSimulator",
    "NgspiceSimulator": "NGSpiceSimulator",
    "QspiceSimulator": "QSpiceSimulator",
    "XyceSimulator": "XyceSimulator",
    # Editor class renames
    "ASCEditor": "AscEditor",
    "QSCHEditor": "QschEditor",
    "SpiceNetlistEditor": "SpiceEditor",
    # Analysis class renames
    "MontecarloAnalysis": "MonteCarloAnalysis",
    "WorstcaseAnalysis": "WorstCaseAnalysis",
    "SensitivityAnalysis": "SensitivityAnalysis",
    # Method renames (will be handled by individual modules)
    "run_sim": "run_simulation",
    "get_component": "get_component_value",
    "set_component": "set_component_value",
}
