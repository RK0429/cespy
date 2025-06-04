#!/usr/bin/env python
# coding=utf-8
"""Enhanced base classes for circuit simulation analysis.

This module provides improved base classes that extract common patterns
from various analysis types, adding progress reporting, parallel execution
support, and result visualization capabilities.
"""

import logging
import time
from abc import abstractmethod
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import numpy as np
from numpy.typing import NDArray

from ...editor.base_editor import BaseEditor
from ..sim_runner import AnyRunner, RunTask
from .sim_analysis import SimAnalysis

_logger = logging.getLogger("cespy.BaseAnalysis")


class AnalysisStatus(Enum):
    """Status of an analysis run."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AnalysisResult:
    """Container for analysis results."""

    run_id: int
    status: AnalysisStatus
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    measurements: Dict[str, Any] = field(default_factory=dict)
    parameters: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    raw_file: Optional[Path] = None
    log_file: Optional[Path] = None

    @property
    def duration(self) -> Optional[float]:
        """Get run duration in seconds."""
        if self.end_time:
            return self.end_time - self.start_time
        return None

    @property
    def success(self) -> bool:
        """Check if run was successful."""
        return self.status == AnalysisStatus.COMPLETED


class ProgressReporter:
    """Interface for progress reporting during analysis."""

    def __init__(self, callback: Optional[Callable[[int, int, str], None]] = None):
        """Initialize progress reporter.

        Args:
            callback: Optional callback function(current, total, message)
        """
        self.callback = callback
        self._start_time = time.time()
        self._last_report_time = 0.0
        self._report_interval = 1.0  # Report at most once per second

    def report(self, current: int, total: int, message: str = "") -> None:
        """Report progress.

        Args:
            current: Current progress count
            total: Total count
            message: Optional status message
        """
        current_time = time.time()

        # Throttle reports
        if current_time - self._last_report_time < self._report_interval:
            if current < total:  # Always report completion
                return

        self._last_report_time = current_time

        # Calculate metrics
        progress_pct = (current / total * 100) if total > 0 else 0
        elapsed = current_time - self._start_time

        if current > 0 and current < total:
            eta = elapsed / current * (total - current)
            eta_str = self._format_time(eta)
        else:
            eta_str = "N/A"

        # Format message
        full_message = f"[{progress_pct:5.1f}%] {current}/{total}"
        if message:
            full_message += f" - {message}"
        full_message += f" (ETA: {eta_str})"

        # Log progress
        _logger.info(full_message)

        # Call callback if provided
        if self.callback:
            self.callback(current, total, full_message)

    def _format_time(self, seconds: float) -> str:
        """Format time duration."""
        if seconds < 60:
            return f"{seconds:.0f}s"
        if seconds < 3600:
            return f"{seconds/60:.1f}m"
        return f"{seconds/3600:.1f}h"


class BaseAnalysis(SimAnalysis):
    """Enhanced base class for simulation analysis with common patterns extracted."""

    def __init__(
        self,
        circuit_file: Union[str, BaseEditor],
        runner: Optional[AnyRunner] = None,
        parallel: bool = False,
        max_workers: Optional[int] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ):
        """Initialize base analysis.

        Args:
            circuit_file: Circuit file path or editor instance
            runner: Simulation runner instance
            parallel: Enable parallel execution
            max_workers: Maximum parallel workers (None for CPU count)
            progress_callback: Progress reporting callback
        """
        super().__init__(circuit_file, runner)

        self.parallel = parallel
        self.max_workers = max_workers
        self.progress_reporter = ProgressReporter(progress_callback)

        # Results storage
        self.results: List[AnalysisResult] = []
        self._result_cache: Dict[int, AnalysisResult] = {}

        # Execution control
        self._executor: Optional[Union[ThreadPoolExecutor, ProcessPoolExecutor]] = None
        self._cancelled = False

    @abstractmethod
    def prepare_runs(self) -> List[Dict[str, Any]]:
        """Prepare parameter sets for all runs.

        Returns:
            List of parameter dictionaries for each run
        """
        pass

    @abstractmethod
    def apply_parameters(self, parameters: Dict[str, Any]) -> None:
        """Apply parameters to the circuit.

        Args:
            parameters: Parameters to apply
        """
        pass

    @abstractmethod
    def extract_results(self, run_task: RunTask) -> Dict[str, Any]:
        """Extract measurements from a completed run.

        Args:
            run_task: Completed simulation task

        Returns:
            Dictionary of measurements
        """
        pass

    def run_analysis(self) -> List[AnalysisResult]:
        """Run the complete analysis.

        Returns:
            List of analysis results
        """
        # Clear previous results
        self.results.clear()
        self._result_cache.clear()
        self._cancelled = False

        # Prepare all runs
        all_parameters = self.prepare_runs()
        total_runs = len(all_parameters)

        _logger.info("Starting analysis with %d runs", total_runs)
        self.progress_reporter.report(0, total_runs, "Preparing")

        if self.parallel and total_runs > 1:
            results = self._run_parallel(all_parameters)
        else:
            results = self._run_sequential(all_parameters)

        # Final report
        successful = sum(1 for r in results if r.success)
        self.progress_reporter.report(
            total_runs, total_runs, f"Complete: {successful}/{total_runs} successful"
        )

        return results

    def _run_sequential(
        self, all_parameters: List[Dict[str, Any]]
    ) -> List[AnalysisResult]:
        """Run analysis sequentially."""
        results = []

        for i, parameters in enumerate(all_parameters):
            if self._cancelled:
                break

            # Progress update
            self.progress_reporter.report(i, len(all_parameters), "Running simulations")

            # Run single simulation
            result = self._run_single(i, parameters)
            results.append(result)
            self.results.append(result)
            self._result_cache[i] = result

        return results

    def _run_parallel(
        self, all_parameters: List[Dict[str, Any]]
    ) -> List[AnalysisResult]:
        """Run analysis in parallel."""
        results = []

        # Create executor
        if self._executor is None:
            self._executor = ThreadPoolExecutor(max_workers=self.max_workers)

        # Submit all tasks
        futures = {}
        for i, parameters in enumerate(all_parameters):
            future = self._executor.submit(self._run_single, i, parameters)
            futures[future] = i

        # Collect results
        completed = 0
        for future in as_completed(futures):
            if self._cancelled:
                # Cancel remaining futures
                for f in futures:
                    f.cancel()
                break

            run_id = futures[future]
            try:
                result = future.result()
                results.append(result)
                self.results.append(result)
                self._result_cache[run_id] = result
            except Exception as e:
                _logger.error("Run %d failed: %s", run_id, e)
                result = AnalysisResult(
                    run_id=run_id, status=AnalysisStatus.FAILED, error_message=str(e)
                )
                results.append(result)

            completed += 1
            self.progress_reporter.report(
                completed, len(all_parameters), f"Completed run {run_id}"
            )

        return results

    def _run_single(self, run_id: int, parameters: Dict[str, Any]) -> AnalysisResult:
        """Run a single simulation with given parameters."""
        result = AnalysisResult(
            run_id=run_id, status=AnalysisStatus.RUNNING, parameters=parameters.copy()
        )

        try:
            # Reset circuit
            self._reset_netlist()

            # Apply parameters
            self.apply_parameters(parameters)

            # Run simulation
            run_task = self.run(run_filename=f"run_{run_id}", wait_resource=True)

            if run_task is None:
                raise RuntimeError("Failed to start simulation")

            # Wait for completion
            self.runner.wait_completion()

            # Extract results
            measurements = self.extract_results(run_task)

            # Update result
            result.measurements = measurements
            result.status = AnalysisStatus.COMPLETED
            result.end_time = time.time()

            # Store file paths if available
            if hasattr(run_task, "raw_file") and run_task.raw_file is not None:
                result.raw_file = Path(run_task.raw_file)
            if hasattr(run_task, "log_file") and run_task.log_file is not None:
                result.log_file = Path(run_task.log_file)

        except Exception as e:
            _logger.error("Error in run %d: %s", run_id, e)
            result.status = AnalysisStatus.FAILED
            result.error_message = str(e)
            result.end_time = time.time()

        return result

    def cancel(self) -> None:
        """Cancel the analysis."""
        self._cancelled = True
        _logger.info("Analysis cancelled")

    def get_statistics(self) -> Dict[str, Any]:
        """Get analysis statistics.

        Returns:
            Dictionary with statistics
        """
        if not self.results:
            return {}

        successful = [r for r in self.results if r.success]
        failed = [r for r in self.results if r.status == AnalysisStatus.FAILED]

        stats = {
            "total_runs": len(self.results),
            "successful": len(successful),
            "failed": len(failed),
            "success_rate": len(successful) / len(self.results) * 100
            if self.results
            else 0,
        }

        # Calculate timing statistics
        if successful:
            durations = [r.duration for r in successful if r.duration is not None]
            if durations:
                stats["avg_duration"] = float(np.mean(durations))
                stats["min_duration"] = np.min(durations)
                stats["max_duration"] = np.max(durations)
                stats["total_duration"] = np.sum(durations)

        return stats

    def cleanup(self) -> None:
        """Clean up resources."""
        if self._executor is not None:
            self._executor.shutdown(wait=True)
            self._executor = None


class StatisticalAnalysis(BaseAnalysis):
    """Base class for statistical analyses (Monte Carlo, etc.)."""

    def __init__(
        self,
        circuit_file: Union[str, BaseEditor],
        num_runs: int = 1000,
        seed: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize statistical analysis.

        Args:
            circuit_file: Circuit file or editor
            num_runs: Number of simulation runs
            seed: Random seed for reproducibility
            **kwargs: Additional arguments for BaseAnalysis
        """
        super().__init__(circuit_file, **kwargs)
        self.num_runs = num_runs
        self.seed = seed

        # Set random seed if provided
        if seed is not None:
            np.random.seed(seed)

    def calculate_statistics(self, measurement_name: str) -> Dict[str, float]:
        """Calculate statistics for a measurement across all runs.

        Args:
            measurement_name: Name of measurement to analyze

        Returns:
            Dictionary with statistical measures
        """
        values = []

        for result in self.results:
            if result.success and measurement_name in result.measurements:
                value = result.measurements[measurement_name]
                if isinstance(value, (int, float)):
                    values.append(value)

        if not values:
            return {}

        values_array = np.array(values)

        return {
            "count": len(values),
            "mean": float(np.mean(values_array)),
            "std": float(np.std(values_array)),
            "min": float(np.min(values_array)),
            "max": float(np.max(values_array)),
            "median": float(np.median(values_array)),
            "q1": float(np.percentile(values_array, 25)),
            "q3": float(np.percentile(values_array, 75)),
            "cv": float(np.std(values_array) / np.mean(values_array))
            if np.mean(values_array) != 0
            else 0,
        }

    def get_histogram_data(
        self, measurement_name: str, bins: Union[int, str] = "auto"
    ) -> Tuple[NDArray[np.float64], NDArray[np.float64]]:
        """Get histogram data for a measurement.

        Args:
            measurement_name: Name of measurement
            bins: Number of bins or method

        Returns:
            Tuple of (counts, bin_edges)
        """
        values = []

        for result in self.results:
            if result.success and measurement_name in result.measurements:
                value = result.measurements[measurement_name]
                if isinstance(value, (int, float)):
                    values.append(value)

        if not values:
            return np.array([]), np.array([])

        return np.histogram(values, bins=bins)

    def get_correlation_matrix(
        self, measurement_names: List[str]
    ) -> Tuple[NDArray[np.floating[Any]], List[str]]:
        """Calculate correlation matrix between measurements.

        Args:
            measurement_names: List of measurement names

        Returns:
            Tuple of (correlation_matrix, valid_measurements)
        """
        # Collect data for each measurement
        data_dict: Dict[str, List[float]] = {name: [] for name in measurement_names}

        for result in self.results:
            if result.success:
                for name in measurement_names:
                    if name in result.measurements:
                        value = result.measurements[name]
                        if isinstance(value, (int, float)):
                            data_dict[name].append(value)
                        else:
                            data_dict[name].append(np.nan)
                    else:
                        data_dict[name].append(np.nan)

        # Filter measurements with sufficient data
        valid_measurements = []
        valid_data = []

        for name, values in data_dict.items():
            values_array = np.array(values)
            if (
                np.sum(~np.isnan(values_array)) > len(values) * 0.5
            ):  # At least 50% valid
                valid_measurements.append(name)
                valid_data.append(values_array)

        if len(valid_data) < 2:
            return np.array([[]]), valid_measurements

        # Calculate correlation matrix
        data_matrix = np.column_stack(valid_data)
        correlation_matrix = np.corrcoef(data_matrix, rowvar=False)

        return correlation_matrix, valid_measurements


class ParametricAnalysis(BaseAnalysis):
    """Base class for parametric analyses (sweep, sensitivity, etc.)."""

    def __init__(
        self,
        circuit_file: Union[str, BaseEditor],
        parameters: Dict[str, List[Any]],
        **kwargs: Any,
    ) -> None:
        """Initialize parametric analysis.

        Args:
            circuit_file: Circuit file or editor
            parameters: Dictionary of parameter names to value lists
            **kwargs: Additional arguments for BaseAnalysis
        """
        super().__init__(circuit_file, **kwargs)
        self.parameters = parameters

    def get_parameter_sensitivity(
        self, parameter_name: str, measurement_name: str
    ) -> float:
        """Calculate sensitivity of measurement to parameter.

        Args:
            parameter_name: Parameter to analyze
            measurement_name: Measurement to analyze

        Returns:
            Sensitivity coefficient
        """
        # Group results by parameter value
        param_groups = defaultdict(list)

        for result in self.results:
            if result.success and parameter_name in result.parameters:
                param_value = result.parameters[parameter_name]
                if measurement_name in result.measurements:
                    meas_value = result.measurements[measurement_name]
                    if isinstance(meas_value, (int, float)):
                        param_groups[param_value].append(meas_value)

        if len(param_groups) < 2:
            return 0.0

        # Calculate sensitivity using linear regression
        param_values = []
        meas_means = []

        for param_val, meas_vals in param_groups.items():
            if meas_vals:
                param_values.append(float(param_val))
                meas_means.append(np.mean(meas_vals))

        if len(param_values) < 2:
            return 0.0

        # Linear regression
        param_array = np.array(param_values)
        meas_array = np.array(meas_means)

        # Normalize to get relative sensitivity
        param_range = np.ptp(param_array)
        meas_range = np.ptp(meas_array)

        if param_range == 0 or meas_range == 0:
            return 0.0

        # Calculate slope
        coefficients = np.polyfit(param_array, meas_array, 1)
        slope = coefficients[0]

        # Relative sensitivity
        param_mid = np.mean(param_array)
        meas_mid = np.mean(meas_array)

        if meas_mid == 0:
            return float(slope * param_mid)
        return float(slope * param_mid / meas_mid)

    def get_response_surface(
        self, param1_name: str, param2_name: str, measurement_name: str
    ) -> Tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]]:
        """Get 2D response surface for two parameters.

        Args:
            param1_name: First parameter name
            param2_name: Second parameter name
            measurement_name: Measurement name

        Returns:
            Tuple of (param1_grid, param2_grid, measurement_grid)
        """
        # Collect data points
        param1_vals = []
        param2_vals = []
        meas_vals = []

        for result in self.results:
            if result.success:
                if (
                    param1_name in result.parameters
                    and param2_name in result.parameters
                    and measurement_name in result.measurements
                ):
                    param1_vals.append(float(result.parameters[param1_name]))
                    param2_vals.append(float(result.parameters[param2_name]))
                    meas_vals.append(float(result.measurements[measurement_name]))

        if not param1_vals:
            return np.array([]), np.array([]), np.array([])

        # Create grid
        param1_unique = sorted(set(param1_vals))
        param2_unique = sorted(set(param2_vals))

        param1_grid, param2_grid = np.meshgrid(param1_unique, param2_unique)
        meas_grid = np.full(param1_grid.shape, np.nan)

        # Fill grid
        for p1, p2, m in zip(param1_vals, param2_vals, meas_vals):
            i = param2_unique.index(p2)
            j = param1_unique.index(p1)
            meas_grid[i, j] = m

        return param1_grid, param2_grid, meas_grid
