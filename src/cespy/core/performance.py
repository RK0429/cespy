#!/usr/bin/env python
# coding=utf-8
"""Performance optimization utilities and profiling tools.

This module provides utilities for performance monitoring, optimization hints,
regex compilation caching, and performance benchmarking across the codebase.
"""

import functools
import logging
import re
import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Pattern, TypeVar, Union

_logger = logging.getLogger("cespy.Performance")

F = TypeVar("F", bound=Callable[..., Any])


@dataclass
class PerformanceMetrics:
    """Container for performance measurement data."""

    function_name: str
    call_count: int = 0
    total_time: float = 0.0
    min_time: float = float("inf")
    max_time: float = 0.0
    avg_time: float = 0.0
    last_call_time: float = 0.0
    memory_usage_mb: float = 0.0

    def update(self, execution_time: float, memory_mb: float = 0.0) -> None:
        """Update metrics with new measurement.

        Args:
            execution_time: Time taken for this call
            memory_mb: Memory usage in MB
        """
        self.call_count += 1
        self.total_time += execution_time
        self.min_time = min(self.min_time, execution_time)
        self.max_time = max(self.max_time, execution_time)
        self.avg_time = self.total_time / self.call_count
        self.last_call_time = execution_time
        self.memory_usage_mb = memory_mb

    def to_dict(self) -> Dict[str, Union[str, int, float]]:
        """Convert metrics to dictionary."""
        return {
            "function_name": self.function_name,
            "call_count": self.call_count,
            "total_time": self.total_time,
            "min_time": self.min_time,
            "max_time": self.max_time,
            "avg_time": self.avg_time,
            "last_call_time": self.last_call_time,
            "memory_usage_mb": self.memory_usage_mb,
        }


class PerformanceMonitor:
    """Centralized performance monitoring and optimization."""

    def __init__(self) -> None:
        self.metrics: Dict[str, PerformanceMetrics] = {}
        self.enabled = True
        self.threshold_warning_time = 1.0  # Warn if function takes > 1 second
        self.threshold_critical_time = 5.0  # Critical if function takes > 5 seconds

    def record_execution(
        self, function_name: str, execution_time: float, memory_mb: float = 0.0
    ) -> None:
        """Record function execution metrics.

        Args:
            function_name: Name of the function
            execution_time: Time taken to execute
            memory_mb: Memory used in MB
        """
        if not self.enabled:
            return

        if function_name not in self.metrics:
            self.metrics[function_name] = PerformanceMetrics(function_name)

        self.metrics[function_name].update(execution_time, memory_mb)

        # Log warnings for slow functions
        if execution_time > self.threshold_critical_time:
            _logger.warning(
                "Critical performance: %s took %.2fs (avg: %.2fs, calls: %d)",
                function_name,
                execution_time,
                self.metrics[function_name].avg_time,
                self.metrics[function_name].call_count,
            )
        elif execution_time > self.threshold_warning_time:
            _logger.debug(
                "Slow function: %s took %.2fs (avg: %.2fs, calls: %d)",
                function_name,
                execution_time,
                self.metrics[function_name].avg_time,
                self.metrics[function_name].call_count,
            )

    def get_metrics(
        self, function_name: Optional[str] = None
    ) -> Union[PerformanceMetrics, Dict[str, PerformanceMetrics]]:
        """Get performance metrics.

        Args:
            function_name: Specific function name, or None for all metrics

        Returns:
            Metrics for specific function or all metrics
        """
        if function_name:
            return self.metrics.get(function_name, PerformanceMetrics(function_name))
        return self.metrics.copy()

    def get_slowest_functions(self, count: int = 10) -> List[PerformanceMetrics]:
        """Get list of slowest functions by average time.

        Args:
            count: Number of functions to return

        Returns:
            List of slowest functions
        """
        return sorted(self.metrics.values(), key=lambda m: m.avg_time, reverse=True)[
            :count
        ]

    def get_most_called_functions(self, count: int = 10) -> List[PerformanceMetrics]:
        """Get list of most frequently called functions.

        Args:
            count: Number of functions to return

        Returns:
            List of most called functions
        """
        return sorted(self.metrics.values(), key=lambda m: m.call_count, reverse=True)[
            :count
        ]

    def reset_metrics(self, function_name: Optional[str] = None) -> None:
        """Reset performance metrics.

        Args:
            function_name: Specific function to reset, or None for all
        """
        if function_name:
            if function_name in self.metrics:
                del self.metrics[function_name]
        else:
            self.metrics.clear()

    def generate_report(self) -> str:
        """Generate performance report.

        Returns:
            Formatted performance report
        """
        if not self.metrics:
            return "No performance data available."

        report_lines = [
            "Performance Report",
            "=" * 50,
            "",
            "Slowest Functions (by average time):",
            "-" * 40,
        ]

        for metric in self.get_slowest_functions(5):
            report_lines.append(
                f"{metric.function_name:30} | "
                f"Avg: {metric.avg_time:6.3f}s | "
                f"Calls: {metric.call_count:5d} | "
                f"Total: {metric.total_time:6.1f}s"
            )

        report_lines.extend(
            [
                "",
                "Most Called Functions:",
                "-" * 40,
            ]
        )

        for metric in self.get_most_called_functions(5):
            report_lines.append(
                f"{metric.function_name:30} | "
                f"Calls: {metric.call_count:5d} | "
                f"Avg: {metric.avg_time:6.3f}s | "
                f"Total: {metric.total_time:6.1f}s"
            )

        return "\n".join(report_lines)


# Global performance monitor instance
performance_monitor = PerformanceMonitor()


def profile_performance(
    include_memory: bool = False, log_calls: bool = False
) -> Callable[[F], F]:
    """Decorator to profile function performance.

    Args:
        include_memory: Whether to monitor memory usage
        log_calls: Whether to log each function call

    Returns:
        Decorated function with performance monitoring
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            if not performance_monitor.enabled:
                return func(*args, **kwargs)

            start_time = time.perf_counter()
            memory_before = 0.0

            if include_memory:
                try:
                    import psutil

                    process = psutil.Process()
                    memory_before = process.memory_info().rss / (1024 * 1024)  # MB
                except ImportError:
                    pass

            if log_calls:
                _logger.debug(
                    "Calling %s with args=%s, kwargs=%s", func.__name__, args, kwargs
                )

            try:
                result = func(*args, **kwargs)
                return result
            finally:
                end_time = time.perf_counter()
                execution_time = end_time - start_time

                memory_usage = 0.0
                if include_memory:
                    try:
                        import psutil

                        process = psutil.Process()
                        memory_after = process.memory_info().rss / (1024 * 1024)  # MB
                        memory_usage = memory_after - memory_before
                    except ImportError:
                        pass

                performance_monitor.record_execution(
                    func.__name__, execution_time, memory_usage
                )

        return wrapper  # type: ignore

    return decorator


@contextmanager
def performance_timer(operation_name: str) -> Any:
    """Context manager for timing operations.

    Args:
        operation_name: Name of the operation being timed
    """
    start_time = time.perf_counter()
    try:
        yield
    finally:
        end_time = time.perf_counter()
        execution_time = end_time - start_time
        performance_monitor.record_execution(operation_name, execution_time)


class RegexCache:
    """Cache for compiled regular expressions to improve performance."""

    def __init__(self, max_size: int = 1000):
        self.cache: Dict[tuple, Pattern] = {}
        self.max_size = max_size
        self.hit_count = 0
        self.miss_count = 0

    def get_pattern(self, pattern: str, flags: int = 0) -> Pattern:
        """Get compiled regex pattern from cache.

        Args:
            pattern: Regular expression pattern
            flags: Regex flags

        Returns:
            Compiled pattern object
        """
        cache_key = (pattern, flags)

        if cache_key in self.cache:
            self.hit_count += 1
            return self.cache[cache_key]

        # Cache miss - compile and store
        self.miss_count += 1
        compiled_pattern = re.compile(pattern, flags)

        # Evict oldest entries if cache is full
        if len(self.cache) >= self.max_size:
            # Remove oldest entry (simple FIFO)
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]

        self.cache[cache_key] = compiled_pattern
        return compiled_pattern

    def get_stats(self) -> Dict[str, Union[int, float]]:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        total_requests = self.hit_count + self.miss_count
        hit_rate = (
            (self.hit_count / total_requests * 100) if total_requests > 0 else 0.0
        )

        return {
            "hit_count": self.hit_count,
            "miss_count": self.miss_count,
            "hit_rate": hit_rate,
            "cache_size": len(self.cache),
            "max_size": self.max_size,
        }

    def clear(self) -> None:
        """Clear the regex cache."""
        self.cache.clear()
        self.hit_count = 0
        self.miss_count = 0


# Global regex cache instance
regex_cache = RegexCache()


def cached_regex(pattern: str, flags: int = 0) -> Pattern:
    """Get cached compiled regex pattern.

    Args:
        pattern: Regular expression pattern
        flags: Regex flags

    Returns:
        Compiled pattern object
    """
    return regex_cache.get_pattern(pattern, flags)


class PerformanceOptimizer:
    """Utility class for performance optimization recommendations."""

    @staticmethod
    def optimize_file_operations(file_size_mb: float) -> Dict[str, Any]:
        """Get optimization recommendations for file operations.

        Args:
            file_size_mb: File size in megabytes

        Returns:
            Dictionary with optimization recommendations
        """
        recommendations: Dict[str, Any] = {}

        if file_size_mb < 1:
            # Small files
            recommendations["read_mode"] = "full"
            recommendations["buffer_size"] = 8192
            recommendations["use_mmap"] = False
        elif file_size_mb < 100:
            # Medium files
            recommendations["read_mode"] = "chunked"
            recommendations["buffer_size"] = 65536
            recommendations["use_mmap"] = True
        else:
            # Large files
            recommendations["read_mode"] = "streaming"
            recommendations["buffer_size"] = 1048576  # 1MB
            recommendations["use_mmap"] = True
            recommendations["use_compression"] = True

        return recommendations

    @staticmethod
    def optimize_regex_patterns(patterns: List[str]) -> Dict[str, Any]:
        """Analyze and optimize regex patterns.

        Args:
            patterns: List of regex patterns to analyze

        Returns:
            Dictionary with optimization recommendations
        """
        recommendations: Dict[str, Any] = {
            "compile_patterns": True,
            "use_cache": True,
            "problematic_patterns": [],
            "optimizations": [],
        }

        for pattern in patterns:
            # Check for common performance issues
            if ".*" in pattern and pattern.count(".*") > 2:
                problematic_patterns = recommendations["problematic_patterns"]
                if isinstance(problematic_patterns, list):
                    problematic_patterns.append(
                        {
                            "pattern": pattern,
                            "issue": "Multiple .* can cause backtracking",
                            "suggestion": "Use more specific patterns or "
                            "possessive quantifiers",
                        }
                    )

            if pattern.startswith(".*") or pattern.endswith(".*"):
                optimizations = recommendations["optimizations"]
                if isinstance(optimizations, list):
                    optimizations.append(
                        {
                            "pattern": pattern,
                            "optimization": "Consider anchoring with ^ or $ "
                            "if possible",
                        }
                    )

            if "|" in pattern and len(pattern.split("|")) > 5:
                optimizations = recommendations["optimizations"]
                if isinstance(optimizations, list):
                    optimizations.append(
                        {
                            "pattern": pattern,
                            "optimization": "Consider splitting complex "
                            "alternations",
                        }
                    )

        return recommendations

    @staticmethod
    def optimize_memory_usage(
        data_size_mb: float, operation_type: str
    ) -> Dict[str, Any]:
        """Get memory optimization recommendations.

        Args:
            data_size_mb: Data size in megabytes
            operation_type: Type of operation (e.g., 'analysis', 'parsing', 'simulation')

        Returns:
            Dictionary with memory optimization recommendations
        """
        recommendations: Dict[str, Any] = {}

        # Get platform info for memory-aware recommendations
        try:
            from .platform import get_platform_info

            platform_info = get_platform_info()
            available_memory = platform_info.total_memory_gb * 1024  # Convert to MB
        except ImportError:
            available_memory = 4096  # Default 4GB

        memory_ratio = data_size_mb / available_memory

        if memory_ratio > 0.5:
            # Data uses more than 50% of available memory
            recommendations["use_streaming"] = True
            recommendations["chunk_size_mb"] = min(100, available_memory * 0.1)
            recommendations["use_memory_mapping"] = True
            recommendations["garbage_collect"] = True
        elif memory_ratio > 0.2:
            # Data uses 20-50% of memory
            recommendations["chunk_size_mb"] = min(200, available_memory * 0.2)
            recommendations["use_memory_mapping"] = operation_type in (
                "parsing",
                "analysis",
            )
        else:
            # Small data relative to memory
            recommendations["load_fully"] = True
            recommendations["use_caching"] = True

        return recommendations


def benchmark_function(
    func: Callable[..., Any], *args: Any, iterations: int = 100, **kwargs: Any
) -> Dict[str, float]:
    """Benchmark a function's performance.

    Args:
        func: Function to benchmark
        *args: Arguments for the function
        iterations: Number of iterations to run
        **kwargs: Keyword arguments for the function

    Returns:
        Dictionary with benchmark results
    """
    times = []

    for _ in range(iterations):
        start_time = time.perf_counter()
        func(*args, **kwargs)
        end_time = time.perf_counter()
        times.append(end_time - start_time)

    import statistics

    return {
        "iterations": iterations,
        "total_time": sum(times),
        "avg_time": statistics.mean(times),
        "median_time": statistics.median(times),
        "min_time": min(times),
        "max_time": max(times),
        "std_dev": statistics.stdev(times) if len(times) > 1 else 0.0,
    }


def get_performance_report() -> str:
    """Get comprehensive performance report.

    Returns:
        Formatted performance report
    """
    report_lines = [
        performance_monitor.generate_report(),
        "",
        "Regex Cache Statistics:",
        "-" * 30,
    ]

    regex_stats = regex_cache.get_stats()
    for key, value in regex_stats.items():
        if isinstance(value, float):
            report_lines.append(f"{key}: {value:.2f}")
        else:
            report_lines.append(f"{key}: {value}")

    return "\n".join(report_lines)


def enable_performance_monitoring(enable: bool = True) -> None:
    """Enable or disable performance monitoring.

    Args:
        enable: Whether to enable monitoring
    """
    performance_monitor.enabled = enable
    _logger.info("Performance monitoring %s", "enabled" if enable else "disabled")
