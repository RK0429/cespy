#!/usr/bin/env python
# coding=utf-8
"""Performance benchmarks and regression testing for cespy.

This module provides a comprehensive benchmarking suite to monitor performance
over time and detect regressions in critical code paths.
"""

import json
import logging
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Union

from .performance import PerformanceMonitor

_logger = logging.getLogger("cespy.Benchmarks")


class BenchmarkSuite:
    """Collection of performance benchmarks for cespy components."""

    def __init__(self) -> None:
        self.results: Dict[str, Dict[str, Union[float, str]]] = {}
        self.baseline_file: Optional[Path] = None
        self.baseline_data: Dict[str, Dict[str, Union[float, str]]] = {}
        self.performance_monitor = PerformanceMonitor()

    def set_baseline_file(self, file_path: Path) -> None:
        """Set file for storing/loading baseline performance data.

        Args:
            file_path: Path to baseline data file
        """
        self.baseline_file = file_path
        if file_path.exists():
            self.load_baseline()

    def load_baseline(self) -> None:
        """Load baseline performance data from file."""
        if not self.baseline_file or not self.baseline_file.exists():
            return

        try:
            with open(self.baseline_file, "r", encoding="utf-8") as f:
                self.baseline_data = json.load(f)
            _logger.info(
                "Loaded baseline data with %d benchmarks", len(self.baseline_data)
            )
        except (FileNotFoundError, json.JSONDecodeError, PermissionError) as e:
            _logger.warning("Failed to load baseline data: %s", e)

    def save_baseline(self) -> None:
        """Save current results as baseline performance data."""
        if not self.baseline_file:
            return

        try:
            import json

            self.baseline_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.baseline_file, "w") as f:
                json.dump(self.results, f, indent=2)
            _logger.info("Saved baseline data with %d benchmarks", len(self.results))
        except Exception as e:
            _logger.error("Failed to save baseline data: %s", e)

    def benchmark_regex_performance(self) -> Dict[str, float]:
        """Benchmark regex pattern compilation and matching performance."""
        import re
        from .patterns import SPICE_PATTERNS

        results = {}
        test_text = """
        R1 net1 net2 1k
        C1 net2 0 1u
        V1 net1 0 DC 5V
        .tran 0 1m 0 1u
        .param Rval=1k
        .measure tran Vout_avg AVG V(net2) FROM 0 TO 1m
        """

        # Test pattern compilation time
        start_time = time.perf_counter()
        patterns = {}
        for name, pattern in SPICE_PATTERNS.items():
            patterns[name] = re.compile(pattern)
        end_time = time.perf_counter()
        results["pattern_compilation_time"] = end_time - start_time

        # Test pattern matching time
        start_time = time.perf_counter()
        for _ in range(1000):
            for pattern in patterns.values():
                pattern.findall(test_text)
        end_time = time.perf_counter()
        results["pattern_matching_time"] = (end_time - start_time) / 1000

        # Test with cached regex
        from .performance import cached_regex

        start_time = time.perf_counter()
        for _ in range(1000):
            for pattern_name, pattern_obj in SPICE_PATTERNS.items():
                cached_pattern = cached_regex(pattern_obj.pattern)
                cached_pattern.findall(test_text)
        end_time = time.perf_counter()
        results["cached_pattern_matching_time"] = (end_time - start_time) / 1000

        return results

    def benchmark_file_operations(self) -> Dict[str, float]:
        """Benchmark file reading and writing operations."""
        results = {}

        # Create test data
        test_data = []
        for i in range(10000):
            test_data.append(f"R{i} net{i} net{i+1} {i}k\n")
        content = "".join(test_data)

        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "benchmark.txt"

            # Benchmark file writing
            start_time = time.perf_counter()
            with open(test_file, "w") as f:
                f.write(content)
            end_time = time.perf_counter()
            results["file_write_time"] = end_time - start_time

            # Benchmark file reading
            start_time = time.perf_counter()
            with open(test_file, "r") as f:
                f.read()
            end_time = time.perf_counter()
            results["file_read_time"] = end_time - start_time

            # Benchmark line-by-line reading
            start_time = time.perf_counter()
            lines = []
            with open(test_file, "r") as f:
                for line in f:
                    lines.append(line)
            end_time = time.perf_counter()
            results["file_readline_time"] = end_time - start_time

        return results

    def benchmark_simulator_detection(self) -> Dict[str, float]:
        """Benchmark simulator detection and path resolution."""
        from .platform import get_simulator_path
        from .constants import Simulators

        results = {}
        simulators = [
            Simulators.LTSPICE,
            Simulators.NGSPICE,
            Simulators.QSPICE,
            Simulators.XYCE,
        ]

        start_time = time.perf_counter()
        for simulator in simulators:
            get_simulator_path(simulator)
        end_time = time.perf_counter()
        results["simulator_detection_time"] = (end_time - start_time) / len(simulators)

        return results

    def benchmark_component_parsing(self) -> Dict[str, float]:
        """Benchmark component value parsing and validation."""
        results = {}

        # Test data
        component_lines = [
            "R1 net1 net2 1k",
            "C1 net2 0 1u",
            "L1 net1 net3 1m",
            "V1 net1 0 DC 5V",
            "I1 0 net2 DC 1m",
            "M1 net1 net2 net3 0 NMOS W=10u L=1u",
            "Q1 net1 net2 net3 NPN",
            "D1 net1 net2 1N4148",
        ] * 1000

        from .patterns import SPICE_PATTERNS

        component_pattern = SPICE_PATTERNS.get("component", r"(\S+)\s+(\S+.*)")

        import re

        pattern = re.compile(component_pattern)

        start_time = time.perf_counter()
        for line in component_lines:
            match = pattern.match(line)
            if match:
                match.group(1)
                # Simple value extraction
                parts = line.split()
                if len(parts) >= 4:
                    parts[3]
        end_time = time.perf_counter()
        results["component_parsing_time"] = (end_time - start_time) / len(
            component_lines
        )

        return results

    def benchmark_analysis_setup(self) -> Dict[str, float]:
        """Benchmark analysis object creation and setup."""
        results = {}

        try:
            # Mock circuit file
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".net", delete=False
            ) as f:
                f.write(
                    """
                V1 net1 0 DC 1V
                R1 net1 net2 1k
                C1 net2 0 1u
                .tran 0 1m 0 1u
                .end
                """
                )
                circuit_file = f.name

            # Test Monte Carlo analysis setup
            start_time = time.perf_counter()
            for _ in range(100):
                from ..sim.toolkit import MonteCarloAnalysis

                mc = MonteCarloAnalysis(circuit_file, num_runs=10)
                mc.set_tolerance("R1", 0.05)
            end_time = time.perf_counter()
            results["montecarlo_setup_time"] = (end_time - start_time) / 100

            # Clean up
            Path(circuit_file).unlink()

        except Exception as e:
            _logger.warning("Failed to benchmark analysis setup: %s", e)
            results["montecarlo_setup_time"] = float("inf")

        return results

    def run_all_benchmarks(self) -> Dict[str, Dict[str, Union[float, str]]]:
        """Run all benchmarks and collect results.

        Returns:
            Dictionary with all benchmark results
        """
        benchmark_methods = [
            ("regex_performance", self.benchmark_regex_performance),
            ("file_operations", self.benchmark_file_operations),
            ("simulator_detection", self.benchmark_simulator_detection),
            ("component_parsing", self.benchmark_component_parsing),
            ("analysis_setup", self.benchmark_analysis_setup),
        ]

        for name, method in benchmark_methods:
            try:
                _logger.info("Running benchmark: %s", name)
                start_time = time.perf_counter()
                result = method()
                end_time = time.perf_counter()

                # Add total time for the benchmark category
                result_with_timing: Dict[str, Union[float, str]] = dict(result)
                result_with_timing["total_benchmark_time"] = end_time - start_time
                self.results[name] = result_with_timing

                _logger.info(
                    "Completed benchmark %s in %.3fs", name, end_time - start_time
                )

            except Exception as e:
                _logger.error("Benchmark %s failed: %s", name, e)
                self.results[name] = {"error": str(e)}

        return self.results

    def compare_with_baseline(self, tolerance: float = 0.1) -> Dict[str, Any]:
        """Compare current results with baseline performance.

        Args:
            tolerance: Acceptable performance degradation (e.g., 0.1 = 10%)

        Returns:
            Dictionary with comparison results
        """
        if not self.baseline_data:
            return {"status": "no_baseline", "message": "No baseline data available"}

        comparison: Dict[str, Any] = {
            "status": "passed",
            "regressions": [],
            "improvements": [],
            "new_benchmarks": [],
            "missing_benchmarks": [],
            "summary": {},
        }

        # Check for missing benchmarks
        for baseline_name in self.baseline_data:
            if baseline_name not in self.results:
                comparison["missing_benchmarks"].append(baseline_name)

        # Check for new benchmarks
        for result_name in self.results:
            if result_name not in self.baseline_data:
                comparison["new_benchmarks"].append(result_name)

        # Compare common benchmarks
        for name in self.baseline_data:
            if name not in self.results:
                continue

            baseline_metrics = self.baseline_data[name]
            current_metrics = self.results[name]

            for metric_name in baseline_metrics:
                if metric_name not in current_metrics:
                    continue

                baseline_value = baseline_metrics[metric_name]
                current_value = current_metrics[metric_name]

                if isinstance(baseline_value, (int, float)) and isinstance(
                    current_value, (int, float)
                ):
                    if baseline_value == 0:
                        continue  # Avoid division by zero

                    change_ratio = (current_value - baseline_value) / baseline_value

                    if change_ratio > tolerance:
                        # Performance regression
                        comparison["regressions"].append(
                            {
                                "benchmark": name,
                                "metric": metric_name,
                                "baseline": baseline_value,
                                "current": current_value,
                                "change_percent": change_ratio * 100,
                            }
                        )
                        comparison["status"] = "failed"
                    elif change_ratio < -0.05:  # 5% improvement threshold
                        # Performance improvement
                        comparison["improvements"].append(
                            {
                                "benchmark": name,
                                "metric": metric_name,
                                "baseline": baseline_value,
                                "current": current_value,
                                "change_percent": change_ratio * 100,
                            }
                        )

        # Generate summary
        comparison["summary"] = {
            "total_regressions": len(comparison["regressions"]),
            "total_improvements": len(comparison["improvements"]),
            "new_benchmarks": len(comparison["new_benchmarks"]),
            "missing_benchmarks": len(comparison["missing_benchmarks"]),
        }

        return comparison

    def generate_report(self, include_comparison: bool = True) -> str:
        """Generate performance benchmark report.

        Args:
            include_comparison: Whether to include baseline comparison

        Returns:
            Formatted benchmark report
        """
        report_lines = ["Performance Benchmark Report", "=" * 50, ""]

        # Current benchmark results
        for benchmark_name, metrics in self.results.items():
            report_lines.append(f"Benchmark: {benchmark_name}")
            report_lines.append("-" * 30)

            for metric_name, value in metrics.items():
                if isinstance(value, float):
                    if value < 0.001:
                        report_lines.append(f"  {metric_name}: {value*1000:.3f} ms")
                    else:
                        report_lines.append(f"  {metric_name}: {value:.3f} s")
                else:
                    report_lines.append(f"  {metric_name}: {value}")

            report_lines.append("")

        # Baseline comparison
        if include_comparison and self.baseline_data:
            comparison = self.compare_with_baseline()

            report_lines.extend(
                [
                    "Baseline Comparison",
                    "=" * 30,
                    f"Status: {comparison['status'].upper()}",
                    "",
                ]
            )

            if comparison["regressions"]:
                report_lines.append("Performance Regressions:")
                for reg in comparison["regressions"]:
                    report_lines.append(
                        f"  {reg['benchmark']}.{reg['metric']}: "
                        f"{reg['change_percent']:+.1f}% "
                        f"({reg['baseline']:.3f} → {reg['current']:.3f})"
                    )
                report_lines.append("")

            if comparison["improvements"]:
                report_lines.append("Performance Improvements:")
                for imp in comparison["improvements"]:
                    report_lines.append(
                        f"  {imp['benchmark']}.{imp['metric']}: "
                        f"{imp['change_percent']:+.1f}% "
                        f"({imp['baseline']:.3f} → {imp['current']:.3f})"
                    )
                report_lines.append("")

            summary = comparison["summary"]
            report_lines.extend(
                [
                    "Summary:",
                    f"  Regressions: {summary['total_regressions']}",
                    f"  Improvements: {summary['total_improvements']}",
                    f"  New benchmarks: {summary['new_benchmarks']}",
                    f"  Missing benchmarks: {summary['missing_benchmarks']}",
                ]
            )

        return "\n".join(report_lines)


def run_performance_benchmarks(
    baseline_file: Optional[Path] = None, save_as_baseline: bool = False
) -> BenchmarkSuite:
    """Run performance benchmarks and optionally compare with baseline.

    Args:
        baseline_file: Path to baseline data file
        save_as_baseline: Whether to save current results as new baseline

    Returns:
        BenchmarkSuite with results
    """
    suite = BenchmarkSuite()

    if baseline_file:
        suite.set_baseline_file(baseline_file)

    # Run all benchmarks
    suite.run_all_benchmarks()

    # Save as baseline if requested
    if save_as_baseline and baseline_file:
        suite.save_baseline()

    return suite


def create_performance_test(
    name: str, baseline_file: Optional[Path] = None
) -> Callable[[], None]:
    """Create a performance test function for use with pytest.

    Args:
        name: Name of the benchmark test
        baseline_file: Path to baseline data file

    Returns:
        Test function that can be used with pytest
    """

    def test_performance() -> None:
        """Performance regression test."""
        suite = run_performance_benchmarks(baseline_file)

        if baseline_file and baseline_file.exists():
            comparison = suite.compare_with_baseline(tolerance=0.2)  # 20% tolerance

            if comparison["status"] == "failed":
                regressions = comparison["regressions"]
                failure_msg = "Performance regressions detected:\n"
                for reg in regressions:
                    failure_msg += (
                        f"  {reg['benchmark']}.{reg['metric']}: "
                        f"{reg['change_percent']:+.1f}% slower\n"
                    )

                # Log full report for debugging
                _logger.error(
                    "Performance benchmark report:\n%s", suite.generate_report()
                )

                raise AssertionError(failure_msg)

        # Always log the current performance for reference
        _logger.info(
            "Performance benchmark report:\n%s",
            suite.generate_report(include_comparison=False),
        )

    test_performance.__name__ = f"test_performance_{name}"
    return test_performance
