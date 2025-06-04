#!/usr/bin/env python
# coding=utf-8
"""Result collector for aggregating and processing simulation results.

This module provides functionality to collect, organize, and process simulation
results, including raw data files, log files, and measurements.
"""

import json
import logging
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

_logger = logging.getLogger("cespy.ResultCollector")


@dataclass
class SimulationResult:
    """Container for a single simulation result."""

    task_id: str
    netlist_path: Path
    raw_file: Optional[Path] = None
    log_file: Optional[Path] = None
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    success: bool = False
    error_message: Optional[str] = None
    measurements: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration(self) -> Optional[float]:
        """Get simulation duration in seconds."""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "task_id": self.task_id,
            "netlist_path": str(self.netlist_path),
            "raw_file": str(self.raw_file) if self.raw_file else None,
            "log_file": str(self.log_file) if self.log_file else None,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": self.duration,
            "success": self.success,
            "error_message": self.error_message,
            "measurements": self.measurements,
            "metadata": self.metadata,
        }


@dataclass
class BatchResult:
    """Container for a batch of simulation results."""

    batch_id: str
    results: List[SimulationResult] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None

    @property
    def success_count(self) -> int:
        """Get number of successful simulations."""
        return sum(1 for r in self.results if r.success)

    @property
    def failure_count(self) -> int:
        """Get number of failed simulations."""
        return sum(1 for r in self.results if not r.success)

    @property
    def total_count(self) -> int:
        """Get total number of simulations."""
        return len(self.results)

    @property
    def success_rate(self) -> float:
        """Get success rate as a percentage."""
        if self.total_count == 0:
            return 0.0
        return (self.success_count / self.total_count) * 100.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "batch_id": self.batch_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "total_count": self.total_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "success_rate": self.success_rate,
            "results": [r.to_dict() for r in self.results],
        }


class ResultCollector:
    """Collects and manages simulation results.

    This class provides:
    - Result aggregation and organization
    - Measurement extraction from log files
    - Result persistence and retrieval
    - Statistical analysis of results
    - Result filtering and searching
    """

    def __init__(self, storage_path: Optional[Path] = None):
        """Initialize result collector.

        Args:
            storage_path: Optional path for persistent storage of results
        """
        self.storage_path = storage_path
        if storage_path:
            storage_path.mkdir(parents=True, exist_ok=True)

        # Result storage
        self._results: Dict[str, SimulationResult] = {}
        self._batches: Dict[str, BatchResult] = {}

        # Indexing for fast lookup
        self._results_by_netlist: Dict[Path, List[str]] = {}
        self._results_by_status: Dict[bool, Set[str]] = {True: set(), False: set()}

        # Measurement tracking
        self._all_measurements: Set[str] = set()

        _logger.info("ResultCollector initialized with storage at %s", storage_path)

    def add_result(
        self,
        task_id: str,
        netlist_path: Path,
        raw_file: Optional[Path] = None,
        log_file: Optional[Path] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        batch_id: Optional[str] = None,
    ) -> SimulationResult:
        """Add a simulation result.

        Args:
            task_id: Unique task identifier
            netlist_path: Path to the netlist file
            raw_file: Path to raw output file
            log_file: Path to log file
            success: Whether simulation succeeded
            error_message: Error message if failed
            metadata: Additional metadata
            batch_id: Optional batch identifier

        Returns:
            SimulationResult object
        """
        # Create result object
        result = SimulationResult(
            task_id=task_id,
            netlist_path=netlist_path,
            raw_file=raw_file,
            log_file=log_file,
            success=success,
            error_message=error_message,
            metadata=metadata or {},
        )
        result.end_time = datetime.now()

        # Extract measurements if log file exists
        if log_file and log_file.exists():
            try:
                result.measurements = self._extract_measurements(log_file)
                self._all_measurements.update(result.measurements.keys())
            except Exception as e:
                _logger.warning(
                    "Failed to extract measurements from %s: %s", log_file, e
                )

        # Store result
        self._results[task_id] = result

        # Update indexes
        if netlist_path not in self._results_by_netlist:
            self._results_by_netlist[netlist_path] = []
        self._results_by_netlist[netlist_path].append(task_id)

        self._results_by_status[success].add(task_id)

        # Add to batch if specified
        if batch_id:
            if batch_id not in self._batches:
                self._batches[batch_id] = BatchResult(batch_id=batch_id)
            self._batches[batch_id].results.append(result)

        # Persist if storage is configured
        if self.storage_path:
            self._save_result(result)

        _logger.debug("Added result for task %s (success=%s)", task_id, success)

        return result

    def get_result(self, task_id: str) -> Optional[SimulationResult]:
        """Get a specific simulation result.

        Args:
            task_id: Task identifier

        Returns:
            SimulationResult or None if not found
        """
        return self._results.get(task_id)

    def get_batch(self, batch_id: str) -> Optional[BatchResult]:
        """Get results for a batch.

        Args:
            batch_id: Batch identifier

        Returns:
            BatchResult or None if not found
        """
        return self._batches.get(batch_id)

    def get_results_by_status(self, success: bool) -> List[SimulationResult]:
        """Get all results with a specific status.

        Args:
            success: True for successful, False for failed

        Returns:
            List of matching results
        """
        task_ids = self._results_by_status.get(success, set())
        return [self._results[tid] for tid in task_ids if tid in self._results]

    def get_results_by_netlist(self, netlist_path: Path) -> List[SimulationResult]:
        """Get all results for a specific netlist.

        Args:
            netlist_path: Path to netlist file

        Returns:
            List of matching results
        """
        task_ids = self._results_by_netlist.get(netlist_path, [])
        return [self._results[tid] for tid in task_ids if tid in self._results]

    def get_measurement_summary(self, measurement_name: str) -> Dict[str, Any]:
        """Get statistical summary for a measurement across all results.

        Args:
            measurement_name: Name of the measurement

        Returns:
            Dictionary with statistics (min, max, mean, std, count)
        """
        values = []

        for result in self._results.values():
            if measurement_name in result.measurements:
                value = result.measurements[measurement_name]
                if isinstance(value, (int, float)):
                    values.append(value)

        if not values:
            return {"count": 0}

        import statistics

        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "std": statistics.stdev(values) if len(values) > 1 else 0.0,
        }

    def get_all_measurements(self) -> Set[str]:
        """Get set of all measurement names seen."""
        return self._all_measurements.copy()

    def export_to_csv(self, output_path: Path, batch_id: Optional[str] = None) -> None:
        """Export results to CSV file.

        Args:
            output_path: Path for CSV output
            batch_id: Optional batch to export (None for all)
        """
        import csv

        # Determine which results to export
        if batch_id:
            batch = self._batches.get(batch_id)
            if not batch:
                raise ValueError(f"Batch {batch_id} not found")
            results = batch.results
        else:
            results = list(self._results.values())

        if not results:
            _logger.warning("No results to export")
            return

        # Collect all measurement names
        all_measurements: set[str] = set()
        for result in results:
            all_measurements.update(result.measurements.keys())

        # Write CSV
        with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
            # Define fields
            fields = [
                "task_id",
                "netlist",
                "success",
                "duration",
                "error_message",
            ] + sorted(all_measurements)

            writer = csv.DictWriter(csvfile, fieldnames=fields)
            writer.writeheader()

            for result in results:
                row = {
                    "task_id": result.task_id,
                    "netlist": result.netlist_path.name,
                    "success": result.success,
                    "duration": result.duration,
                    "error_message": result.error_message or "",
                }

                # Add measurements
                for meas in all_measurements:
                    row[meas] = result.measurements.get(meas, "")

                writer.writerow(row)

        _logger.info("Exported %d results to %s", len(results), output_path)

    def archive_results(
        self,
        archive_path: Path,
        batch_id: Optional[str] = None,
        include_files: bool = True,
    ) -> None:
        """Archive results to a directory.

        Args:
            archive_path: Directory for archive
            batch_id: Optional batch to archive (None for all)
            include_files: Whether to copy raw/log files
        """
        archive_path.mkdir(parents=True, exist_ok=True)

        # Determine which results to archive
        if batch_id:
            batch = self._batches.get(batch_id)
            if not batch:
                raise ValueError(f"Batch {batch_id} not found")
            results = batch.results
            # Save batch metadata
            batch_file = archive_path / f"batch_{batch_id}.json"
            with open(batch_file, "w", encoding="utf-8") as f:
                json.dump(batch.to_dict(), f, indent=2)
        else:
            results = list(self._results.values())

        # Save results summary
        summary_file = archive_path / "results_summary.json"
        summary = {
            "total": len(results),
            "successful": sum(1 for r in results if r.success),
            "failed": sum(1 for r in results if not r.success),
            "results": [r.to_dict() for r in results],
        }

        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

        # Copy result files if requested
        if include_files:
            files_dir = archive_path / "files"
            files_dir.mkdir(exist_ok=True)

            for result in results:
                # Create subdirectory for each result
                result_dir = files_dir / result.task_id
                result_dir.mkdir(exist_ok=True)

                # Copy files
                if result.raw_file and result.raw_file.exists():
                    shutil.copy2(result.raw_file, result_dir / result.raw_file.name)

                if result.log_file and result.log_file.exists():
                    shutil.copy2(result.log_file, result_dir / result.log_file.name)

                # Save netlist too
                if result.netlist_path.exists():
                    shutil.copy2(
                        result.netlist_path, result_dir / result.netlist_path.name
                    )

        _logger.info("Archived %d results to %s", len(results), archive_path)

    def clear(self) -> None:
        """Clear all stored results."""
        self._results.clear()
        self._batches.clear()
        self._results_by_netlist.clear()
        self._results_by_status[True].clear()
        self._results_by_status[False].clear()
        self._all_measurements.clear()

        _logger.info("Cleared all results")

    def _extract_measurements(self, log_file: Path) -> Dict[str, Any]:
        """Extract measurements from a log file.

        Args:
            log_file: Path to log file

        Returns:
            Dictionary of measurement values
        """
        try:
            # Try to use LTSpiceLogReader first
            from ..log.ltsteps import LTSpiceLogReader

            log_reader = LTSpiceLogReader(str(log_file))
            measurements = {}

            # Extract all measurements
            for meas_name in log_reader.get_measure_names():
                try:
                    # Get the first value (for non-stepped simulations)
                    value = log_reader.get_measure_value(meas_name, step=0)
                    measurements[meas_name] = value
                except Exception:
                    # Try without step parameter
                    try:
                        value = log_reader.get_measure_value(meas_name)
                        measurements[meas_name] = value
                    except Exception:
                        pass

            return measurements

        except Exception as e:
            _logger.debug("Failed to parse log file with LTSpiceLogReader: %s", e)
            return {}

    def _save_result(self, result: SimulationResult) -> None:
        """Save a result to persistent storage.

        Args:
            result: Result to save
        """
        if not self.storage_path:
            return

        # Save as JSON file
        result_file = self.storage_path / f"{result.task_id}.json"
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(result.to_dict(), f, indent=2)

    def load_from_storage(self) -> int:
        """Load results from persistent storage.

        Returns:
            Number of results loaded
        """
        if not self.storage_path or not self.storage_path.exists():
            return 0

        loaded = 0
        for json_file in self.storage_path.glob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Skip batch files
                if json_file.name.startswith("batch_"):
                    continue

                # Reconstruct result
                result = SimulationResult(
                    task_id=data["task_id"],
                    netlist_path=Path(data["netlist_path"]),
                    raw_file=Path(data["raw_file"]) if data["raw_file"] else None,
                    log_file=Path(data["log_file"]) if data["log_file"] else None,
                    success=data["success"],
                    error_message=data.get("error_message"),
                    measurements=data.get("measurements", {}),
                    metadata=data.get("metadata", {}),
                )

                # Parse times
                result.start_time = datetime.fromisoformat(data["start_time"])
                if data["end_time"]:
                    result.end_time = datetime.fromisoformat(data["end_time"])

                # Store result
                self._results[result.task_id] = result
                loaded += 1

            except Exception as e:
                _logger.warning("Failed to load result from %s: %s", json_file, e)

        _logger.info("Loaded %d results from storage", loaded)
        return loaded
