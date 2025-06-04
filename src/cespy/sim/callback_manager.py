#!/usr/bin/env python
# coding=utf-8
"""Callback manager for handling simulation completion callbacks.

This module provides a manager for registering and executing callbacks when
simulations complete, with support for different callback types and error handling.
"""

import inspect
import logging
import threading
import traceback
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Type, Union

from .process_callback import ProcessCallback

_logger = logging.getLogger("cespy.CallbackManager")


class CallbackType(Enum):
    """Types of callbacks supported."""

    PROCESS_CALLBACK_CLASS = "process_callback_class"
    SIMPLE_FUNCTION = "simple_function"
    PARAMETERIZED_FUNCTION = "parameterized_function"


@dataclass
class CallbackInfo:
    """Information about a registered callback."""

    callback: Union[Type[ProcessCallback], Callable[..., Any]]
    callback_type: CallbackType
    args: Tuple[Any, ...] = ()
    kwargs: Optional[Dict[str, Any]] = None
    error_handler: Optional[Callable[[Exception], None]] = None

    def __post_init__(self) -> None:
        if self.kwargs is None:
            self.kwargs = {}


class CallbackManager:
    """Manages callback registration and execution for simulations.

    This class handles:
    - Multiple callback types (ProcessCallback classes and functions)
    - Callback parameter validation
    - Error handling and recovery
    - Thread-safe callback execution
    - Callback chaining and composition
    """

    def __init__(self, max_callback_errors: int = 3):
        """Initialize callback manager.

        Args:
            max_callback_errors: Maximum errors before disabling a callback
        """
        self.max_callback_errors = max_callback_errors

        # Callback storage
        self._callbacks: Dict[str, CallbackInfo] = {}
        self._callback_errors: Dict[str, int] = {}
        self._disabled_callbacks: Set[str] = set()

        # Thread safety
        self._lock = threading.Lock()

        # Statistics
        self._execution_count = 0
        self._error_count = 0

        _logger.info("CallbackManager initialized")

    def register(
        self,
        callback_id: str,
        callback: Union[Type[ProcessCallback], Callable[..., Any]],
        args: Optional[Tuple[Any, ...]] = None,
        kwargs: Optional[Dict[str, Any]] = None,
        error_handler: Optional[Callable[[Exception], None]] = None,
        replace: bool = False,
    ) -> None:
        """Register a callback.

        Args:
            callback_id: Unique identifier for the callback
            callback: ProcessCallback class or callable function
            args: Positional arguments for parameterized callbacks
            kwargs: Keyword arguments for parameterized callbacks
            error_handler: Optional error handler for this callback
            replace: Whether to replace existing callback with same ID

        Raises:
            ValueError: If callback_id exists and replace is False
            TypeError: If callback type is not supported
        """
        with self._lock:
            if callback_id in self._callbacks and not replace:
                raise ValueError(f"Callback '{callback_id}' already registered")

            # Determine callback type
            callback_type = self._determine_callback_type(callback)

            # Validate callback
            self._validate_callback(callback, callback_type, args, kwargs)

            # Create callback info
            callback_info = CallbackInfo(
                callback=callback,
                callback_type=callback_type,
                args=args or (),
                kwargs=kwargs or {},
                error_handler=error_handler,
            )

            # Register callback
            self._callbacks[callback_id] = callback_info
            self._callback_errors[callback_id] = 0

            # Remove from disabled if it was there
            self._disabled_callbacks.discard(callback_id)

            _logger.debug(
                "Registered callback '%s' of type %s", callback_id, callback_type
            )

    def unregister(self, callback_id: str) -> bool:
        """Unregister a callback.

        Args:
            callback_id: ID of callback to remove

        Returns:
            True if callback was removed, False if not found
        """
        with self._lock:
            if callback_id in self._callbacks:
                del self._callbacks[callback_id]
                self._callback_errors.pop(callback_id, None)
                self._disabled_callbacks.discard(callback_id)
                _logger.debug("Unregistered callback '%s'", callback_id)
                return True
            return False

    def execute(
        self,
        callback_id: str,
        raw_file: Path,
        log_file: Path,
        context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, Optional[Any]]:
        """Execute a specific callback.

        Args:
            callback_id: ID of callback to execute
            raw_file: Path to simulation raw file
            log_file: Path to simulation log file
            context: Optional context data

        Returns:
            Tuple of (success, result)
        """
        with self._lock:
            if callback_id not in self._callbacks:
                _logger.warning("Callback '%s' not found", callback_id)
                return False, None

            if callback_id in self._disabled_callbacks:
                _logger.warning("Callback '%s' is disabled", callback_id)
                return False, None

            callback_info = self._callbacks[callback_id]

        # Execute outside lock to avoid blocking
        return self._execute_callback(
            callback_id, callback_info, raw_file, log_file, context
        )

    def execute_all(
        self,
        raw_file: Path,
        log_file: Path,
        context: Optional[Dict[str, Any]] = None,
        stop_on_error: bool = False,
    ) -> Dict[str, Tuple[bool, Optional[Any]]]:
        """Execute all registered callbacks.

        Args:
            raw_file: Path to simulation raw file
            log_file: Path to simulation log file
            context: Optional context data
            stop_on_error: Whether to stop execution on first error

        Returns:
            Dictionary mapping callback IDs to (success, result) tuples
        """
        results = {}

        # Get snapshot of callbacks to execute
        with self._lock:
            callbacks_to_execute = [
                (cid, cinfo)
                for cid, cinfo in self._callbacks.items()
                if cid not in self._disabled_callbacks
            ]

        # Execute callbacks
        for callback_id, callback_info in callbacks_to_execute:
            success, result = self._execute_callback(
                callback_id, callback_info, raw_file, log_file, context
            )
            results[callback_id] = (success, result)

            if not success and stop_on_error:
                _logger.warning(
                    "Stopping callback execution due to error in '%s'", callback_id
                )
                break

        return results

    def create_chain(self, *callback_ids: str) -> Callable:
        """Create a chained callback that executes multiple callbacks in sequence.

        Args:
            *callback_ids: IDs of callbacks to chain

        Returns:
            Callable that executes all callbacks in order
        """

        def chained_callback(raw_file: Path, log_file: Path) -> List[Tuple[bool, Any]]:
            results = []
            for callback_id in callback_ids:
                success, result = self.execute(callback_id, raw_file, log_file)
                results.append((success, result))
                if not success:
                    _logger.warning("Chain broken at callback '%s'", callback_id)
                    break
            return results

        return chained_callback

    def create_parallel(self, *callback_ids: str) -> Callable:
        """Create a parallel callback that executes multiple callbacks concurrently.

        Args:
            *callback_ids: IDs of callbacks to run in parallel

        Returns:
            Callable that executes all callbacks concurrently
        """
        import concurrent.futures

        def parallel_callback(
            raw_file: Path, log_file: Path
        ) -> Dict[str, Tuple[bool, Any]]:
            results = {}

            with concurrent.futures.ThreadPoolExecutor() as executor:
                # Submit all callbacks
                futures = {
                    executor.submit(self.execute, cid, raw_file, log_file): cid
                    for cid in callback_ids
                }

                # Collect results
                for future in concurrent.futures.as_completed(futures):
                    callback_id = futures[future]
                    try:
                        success, result = future.result()
                        results[callback_id] = (success, result)
                    except Exception as e:
                        _logger.error(
                            "Error in parallel execution of '%s': %s", callback_id, e
                        )
                        results[callback_id] = (False, None)

            return results

        return parallel_callback

    def get_registered_callbacks(self) -> List[str]:
        """Get list of registered callback IDs."""
        with self._lock:
            return list(self._callbacks.keys())

    def get_disabled_callbacks(self) -> List[str]:
        """Get list of disabled callback IDs."""
        with self._lock:
            return list(self._disabled_callbacks)

    def get_statistics(self) -> Dict[str, Any]:
        """Get callback execution statistics."""
        with self._lock:
            return {
                "registered": len(self._callbacks),
                "disabled": len(self._disabled_callbacks),
                "total_executions": self._execution_count,
                "total_errors": self._error_count,
                "error_counts": dict(self._callback_errors),
            }

    def reset_error_count(self, callback_id: str) -> None:
        """Reset error count for a callback and re-enable if disabled.

        Args:
            callback_id: ID of callback to reset
        """
        with self._lock:
            self._callback_errors[callback_id] = 0
            self._disabled_callbacks.discard(callback_id)
            _logger.info("Reset error count for callback '%s'", callback_id)

    def _determine_callback_type(self, callback: Any) -> CallbackType:
        """Determine the type of callback.

        Args:
            callback: Callback to analyze

        Returns:
            CallbackType enum value

        Raises:
            TypeError: If callback type is not supported
        """
        # Check if it's a ProcessCallback subclass
        try:
            if inspect.isclass(callback) and issubclass(callback, ProcessCallback):
                return CallbackType.PROCESS_CALLBACK_CLASS
        except TypeError:
            pass

        # Check if it's a callable
        if callable(callback):
            sig = inspect.signature(callback)
            params = list(sig.parameters.values())

            # Simple function with just raw_file and log_file
            if len(params) == 2:
                return CallbackType.SIMPLE_FUNCTION
            else:
                return CallbackType.PARAMETERIZED_FUNCTION

        raise TypeError(f"Unsupported callback type: {type(callback)}")

    def _validate_callback(
        self,
        callback: Any,
        callback_type: CallbackType,
        args: Optional[Tuple[Any, ...]],
        kwargs: Optional[Dict[str, Any]],
    ) -> None:
        """Validate callback parameters.

        Args:
            callback: Callback to validate
            callback_type: Type of callback
            args: Positional arguments
            kwargs: Keyword arguments

        Raises:
            TypeError: If callback signature doesn't match expected
        """
        if callback_type == CallbackType.PROCESS_CALLBACK_CLASS:
            # Validate ProcessCallback class
            if not hasattr(callback, "run"):
                raise TypeError("ProcessCallback must have a 'run' method")

        elif callback_type in (
            CallbackType.SIMPLE_FUNCTION,
            CallbackType.PARAMETERIZED_FUNCTION,
        ):
            # Validate function signature
            sig = inspect.signature(callback)

            # Check if we can bind the expected arguments
            try:
                if callback_type == CallbackType.SIMPLE_FUNCTION:
                    sig.bind(Path("dummy"), Path("dummy"))
                else:
                    # For parameterized functions, check with provided args/kwargs
                    test_args = (Path("dummy"), Path("dummy")) + (args or ())
                    sig.bind(*test_args, **(kwargs or {}))
            except TypeError as e:
                raise TypeError(f"Callback signature mismatch: {e}")

    def _execute_callback(
        self,
        callback_id: str,
        callback_info: CallbackInfo,
        raw_file: Path,
        log_file: Path,
        context: Optional[Dict[str, Any]],
    ) -> Tuple[bool, Optional[Any]]:
        """Execute a single callback with error handling.

        Args:
            callback_id: ID of callback
            callback_info: Callback information
            raw_file: Raw file path
            log_file: Log file path
            context: Optional context

        Returns:
            Tuple of (success, result)
        """
        try:
            _logger.debug("Executing callback '%s'", callback_id)
            self._execution_count += 1

            result = None

            # Convert Path objects to strings for callbacks
            raw_file_str = str(raw_file)
            log_file_str = str(log_file)

            if callback_info.callback_type == CallbackType.PROCESS_CALLBACK_CLASS:
                # Instantiate and run ProcessCallback
                instance = callback_info.callback(raw_file_str, log_file_str)
                instance.run()
                result = instance

            elif callback_info.callback_type == CallbackType.SIMPLE_FUNCTION:
                # Call simple function
                result = callback_info.callback(raw_file_str, log_file_str)

            elif callback_info.callback_type == CallbackType.PARAMETERIZED_FUNCTION:
                # Call with additional parameters
                all_args = (raw_file_str, log_file_str) + callback_info.args
                kwargs = callback_info.kwargs or {}
                result = callback_info.callback(*all_args, **kwargs)

            # Reset error count on success
            with self._lock:
                self._callback_errors[callback_id] = 0

            return True, result

        except Exception as e:
            self._error_count += 1
            _logger.error("Error in callback '%s': %s", callback_id, e)
            _logger.debug("Traceback: %s", traceback.format_exc())

            # Update error count
            with self._lock:
                self._callback_errors[callback_id] += 1
                error_count = self._callback_errors[callback_id]

                # Disable if too many errors
                if error_count >= self.max_callback_errors:
                    self._disabled_callbacks.add(callback_id)
                    _logger.warning(
                        "Disabled callback '%s' after %d errors",
                        callback_id,
                        error_count,
                    )

            # Call error handler if provided
            if callback_info.error_handler:
                try:
                    callback_info.error_handler(e)
                except Exception as handler_error:
                    _logger.error(
                        "Error in error handler for '%s': %s",
                        callback_id,
                        handler_error,
                    )

            return False, None
