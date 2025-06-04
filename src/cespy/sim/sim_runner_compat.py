#!/usr/bin/env python
# coding=utf-8
"""Compatibility layer for transitioning from SimRunner to SimRunnerRefactored.

This module provides a drop-in replacement for the original SimRunner that uses
the refactored implementation while maintaining full backward compatibility.
"""

import warnings
from typing import Any, Optional

from .sim_runner import SimRunner as OriginalSimRunner
from .sim_runner_refactored import SimRunnerRefactored

__all__ = ["SimRunner"]


class SimRunner(SimRunnerRefactored):
    """Compatibility wrapper for SimRunner.

    This class extends SimRunnerRefactored to provide full backward compatibility
    with the original SimRunner API, including deprecated methods and attributes.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize with backward compatibility support."""
        # Handle old-style positional arguments if any
        if args:
            warnings.warn(
                "Positional arguments in SimRunner are deprecated. "
                "Please use keyword arguments.",
                DeprecationWarning,
                stacklevel=2,
            )
            # Map positional args to keyword args based on old signature
            # This is a simplified mapping - adjust based on actual old API
            if len(args) > 0 and "simulator" not in kwargs:
                kwargs["simulator"] = args[0]
            if len(args) > 1 and "parallel_sims" not in kwargs:
                kwargs["parallel_sims"] = args[1]

        super().__init__(**kwargs)

        # Initialize deprecated attributes for backward compatibility
        self._deprecated_attrs: dict[str, Any] = {}

    # Deprecated attribute access
    @property
    def failSim(self) -> int:
        """Deprecated: Use fail_sim instead."""
        warnings.warn(
            "failSim is deprecated, use fail_sim instead",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.fail_sim

    @property
    def okSim(self) -> int:
        """Deprecated: Use ok_sim instead."""
        warnings.warn(
            "okSim is deprecated, use ok_sim instead", DeprecationWarning, stacklevel=2
        )
        return self.ok_sim

    @property
    def runno(self) -> int:
        """Get run number (for compatibility)."""
        return super().runno

    @property
    def results(self) -> Any:
        """Access to result collector for advanced usage."""
        return self._result_collector

    # Deprecated methods
    def setSimulator(self, spice_tool: Any) -> None:
        """Deprecated: Use set_simulator instead."""
        warnings.warn(
            "setSimulator is deprecated, use set_simulator instead",
            DeprecationWarning,
            stacklevel=2,
        )
        self.set_simulator(spice_tool)

    def add_LTspiceRunCmdLineSwitches(self, *args: Any) -> None:
        """Deprecated: Use add_command_line_switch instead."""
        warnings.warn(
            "add_LTspiceRunCmdLineSwitches is deprecated, "
            "use add_command_line_switch instead",
            DeprecationWarning,
            stacklevel=2,
        )
        for arg in args:
            self.add_command_line_switch(arg)

    def run_all(self, *args: Any, **kwargs: Any) -> None:
        """Deprecated: Use run() in a loop instead."""
        warnings.warn(
            "run_all is deprecated, use run() in a loop instead",
            DeprecationWarning,
            stacklevel=2,
        )
        # This would need to be implemented based on old behavior
        raise NotImplementedError("run_all is no longer supported")

    # Additional compatibility methods
    def get_results(self) -> list[Any]:
        """Get all simulation results.

        Returns:
            List of SimulationResult objects
        """
        return list(self._result_collector._results.values())

    def get_successful_results(self) -> list[Any]:
        """Get successful simulation results.

        Returns:
            List of successful SimulationResult objects
        """
        return self._result_collector.get_results_by_status(True)

    def get_failed_results(self) -> list[Any]:
        """Get failed simulation results.

        Returns:
            List of failed SimulationResult objects
        """
        return self._result_collector.get_results_by_status(False)

    def export_results(self, filepath: str) -> None:
        """Export results to CSV file.

        Args:
            filepath: Path to output CSV file
        """
        from pathlib import Path

        self._result_collector.export_to_csv(Path(filepath))

    # Override methods that need special handling
    def run(self, *args: Any, **kwargs: Any) -> Optional[Any]:
        """Run simulation with backward compatibility."""
        # Handle old-style arguments
        if args and not kwargs.get("netlist"):
            # First positional arg was netlist in old API
            kwargs["netlist"] = args[0]
            args = args[1:]

        # Map old parameter names to new ones if needed
        param_mapping = {
            "run_file_name": "run_filename",
            "wait_for_resource": "wait_resource",
            # Add more mappings as needed
        }

        for old_name, new_name in param_mapping.items():
            if old_name in kwargs and new_name not in kwargs:
                kwargs[new_name] = kwargs.pop(old_name)

        # Call parent implementation
        return super().run(**kwargs)

    def wait_completion(self, *args: Any, **kwargs: Any) -> bool:
        """Wait for completion with backward compatibility."""
        # Handle old-style timeout as positional argument
        if args and "timeout" not in kwargs:
            kwargs["timeout"] = args[0]

        return super().wait_completion(**kwargs)

    # Utility method for migration assistance
    @classmethod
    def from_original(cls, original: OriginalSimRunner) -> "SimRunner":
        """Create a compatible SimRunner from an original instance.

        Args:
            original: Original SimRunner instance

        Returns:
            Compatible SimRunner instance with same configuration
        """
        # Extract configuration from original
        config = {
            "simulator": getattr(original, "simulator", None),
            "parallel_sims": getattr(original, "parallel_sims", 4),
            "timeout": getattr(original, "timeout", 600.0),
            "verbose": getattr(original, "verbose", False),
            "output_folder": str(original.output_folder)
            if hasattr(original, "output_folder") and original.output_folder
            else None,
        }

        # Create new instance
        new_runner = cls(**config)

        # Copy command line switches
        if hasattr(original, "cmdline_switches"):
            new_runner.cmdline_switches = original.cmdline_switches.copy()

        return new_runner


def migrate_simrunner(old_runner: OriginalSimRunner) -> SimRunner:
    """Helper function to migrate from old SimRunner to new implementation.

    Args:
        old_runner: Original SimRunner instance

    Returns:
        New SimRunner instance with same configuration
    """
    warnings.warn(
        "Migrating from original SimRunner to refactored implementation. "
        "Please update your code to use the new API directly.",
        FutureWarning,
        stacklevel=2,
    )
    return SimRunner.from_original(old_runner)
