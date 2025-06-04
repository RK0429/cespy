#!/usr/bin/env python
# coding=utf-8
"""Tests for core performance monitoring and optimization functionality."""

import re
import time
import pytest
from unittest.mock import Mock, patch

from cespy.core.performance import (
    PerformanceMetrics,
    PerformanceMonitor,
    profile_performance,
    performance_timer,
    RegexCache,
    cached_regex,
    PerformanceOptimizer,
    benchmark_function,
    get_performance_report,
    enable_performance_monitoring,
)


class TestPerformanceMetrics:
    """Test PerformanceMetrics dataclass."""

    def test_metrics_creation(self):
        """Test PerformanceMetrics creation and initialization."""
        metrics = PerformanceMetrics("test_function")

        assert metrics.function_name == "test_function"
        assert metrics.call_count == 0
        assert metrics.total_time == 0.0
        assert metrics.min_time == float('inf')
        assert metrics.max_time == 0.0
        assert metrics.avg_time == 0.0

    def test_metrics_update(self):
        """Test metrics update functionality."""
        metrics = PerformanceMetrics("test_function")

        # First update
        metrics.update(0.5, 10.0)
        assert metrics.call_count == 1
        assert metrics.total_time == 0.5
        assert metrics.min_time == 0.5
        assert metrics.max_time == 0.5
        assert metrics.avg_time == 0.5
        assert metrics.memory_usage_mb == 10.0

        # Second update
        metrics.update(1.0, 15.0)
        assert metrics.call_count == 2
        assert metrics.total_time == 1.5
        assert metrics.min_time == 0.5
        assert metrics.max_time == 1.0
        assert metrics.avg_time == 0.75
        assert metrics.memory_usage_mb == 15.0

    def test_metrics_to_dict(self):
        """Test conversion to dictionary."""
        metrics = PerformanceMetrics("test_function")
        metrics.update(0.5, 10.0)

        result = metrics.to_dict()
        expected_keys = [
            'function_name', 'call_count', 'total_time', 'min_time',
            'max_time', 'avg_time', 'last_call_time', 'memory_usage_mb'
        ]

        for key in expected_keys:
            assert key in result

        assert result['function_name'] == "test_function"
        assert result['call_count'] == 1


class TestPerformanceMonitor:
    """Test PerformanceMonitor class."""

    def test_monitor_creation(self):
        """Test PerformanceMonitor creation."""
        monitor = PerformanceMonitor()

        assert monitor.enabled is True
        assert monitor.threshold_warning_time == 1.0
        assert monitor.threshold_critical_time == 5.0
        assert len(monitor.metrics) == 0

    def test_record_execution(self):
        """Test execution recording."""
        monitor = PerformanceMonitor()

        monitor.record_execution("test_func", 0.5, 10.0)

        assert "test_func" in monitor.metrics
        metrics = monitor.metrics["test_func"]
        assert metrics.call_count == 1
        assert metrics.total_time == 0.5
        assert metrics.memory_usage_mb == 10.0

    def test_disabled_monitor(self):
        """Test disabled monitor doesn't record."""
        monitor = PerformanceMonitor()
        monitor.enabled = False

        monitor.record_execution("test_func", 0.5, 10.0)

        assert len(monitor.metrics) == 0

    def test_get_metrics(self):
        """Test metrics retrieval."""
        monitor = PerformanceMonitor()
        monitor.record_execution("func1", 0.5)
        monitor.record_execution("func2", 1.0)

        # Get specific function metrics
        func1_metrics = monitor.get_metrics("func1")
        assert func1_metrics.function_name == "func1"
        assert func1_metrics.total_time == 0.5

        # Get all metrics
        all_metrics = monitor.get_metrics()
        assert len(all_metrics) == 2
        assert "func1" in all_metrics
        assert "func2" in all_metrics

    def test_slowest_functions(self):
        """Test slowest functions retrieval."""
        monitor = PerformanceMonitor()
        monitor.record_execution("fast_func", 0.1)
        monitor.record_execution("slow_func", 2.0)
        monitor.record_execution("medium_func", 0.5)

        slowest = monitor.get_slowest_functions(2)
        assert len(slowest) == 2
        assert slowest[0].function_name == "slow_func"
        assert slowest[1].function_name == "medium_func"

    def test_most_called_functions(self):
        """Test most called functions retrieval."""
        monitor = PerformanceMonitor()

        # Call functions different numbers of times
        for _ in range(5):
            monitor.record_execution("popular_func", 0.1)
        for _ in range(2):
            monitor.record_execution("rare_func", 0.1)
        for _ in range(3):
            monitor.record_execution("medium_func", 0.1)

        most_called = monitor.get_most_called_functions(2)
        assert len(most_called) == 2
        assert most_called[0].function_name == "popular_func"
        assert most_called[1].function_name == "medium_func"

    def test_reset_metrics(self):
        """Test metrics reset functionality."""
        monitor = PerformanceMonitor()
        monitor.record_execution("func1", 0.5)
        monitor.record_execution("func2", 1.0)

        # Reset specific function
        monitor.reset_metrics("func1")
        assert "func1" not in monitor.metrics
        assert "func2" in monitor.metrics

        # Reset all functions
        monitor.reset_metrics()
        assert len(monitor.metrics) == 0

    @patch('cespy.core.performance._logger')
    def test_warning_thresholds(self, mock_logger):
        """Test warning and critical threshold logging."""
        monitor = PerformanceMonitor()
        monitor.threshold_warning_time = 0.5
        monitor.threshold_critical_time = 1.0

        # Should trigger critical warning
        monitor.record_execution("critical_func", 1.5)
        mock_logger.warning.assert_called()

        # Should trigger debug warning
        monitor.record_execution("slow_func", 0.7)
        mock_logger.debug.assert_called()


class TestProfilePerformanceDecorator:
    """Test @profile_performance decorator."""

    def test_basic_profiling(self):
        """Test basic function profiling."""
        from cespy.core.performance import performance_monitor

        # Clear existing metrics
        performance_monitor.reset_metrics()

        @profile_performance()
        def test_function(x):
            time.sleep(0.01)  # Small delay
            return x * 2

        result = test_function(5)
        assert result == 10

        # Check metrics were recorded
        metrics = performance_monitor.get_metrics("test_function")
        assert metrics is not None
        assert metrics.call_count == 1
        assert metrics.total_time > 0.005  # Should be at least 5ms

    def test_profiling_with_memory(self):
        """Test profiling with memory monitoring."""
        from cespy.core.performance import performance_monitor
        performance_monitor.reset_metrics()

        @profile_performance(include_memory=True)
        def memory_function():
            # Create some data to use memory
            data = [i for i in range(1000)]
            return len(data)

        result = memory_function()
        assert result == 1000

        metrics = performance_monitor.get_metrics("memory_function")
        assert metrics is not None
        assert metrics.call_count == 1

    def test_profiling_disabled(self):
        """Test profiling when monitoring is disabled."""
        from cespy.core.performance import performance_monitor

        # Disable monitoring
        original_enabled = performance_monitor.enabled
        performance_monitor.enabled = False
        performance_monitor.reset_metrics()

        try:
            @profile_performance()
            def disabled_function():
                return "test"

            result = disabled_function()
            assert result == "test"

            # Should not have recorded metrics
            metrics = performance_monitor.get_metrics("disabled_function")
            assert metrics is None

        finally:
            performance_monitor.enabled = original_enabled


class TestPerformanceTimer:
    """Test performance_timer context manager."""

    def test_basic_timing(self):
        """Test basic timing functionality."""
        from cespy.core.performance import performance_monitor
        performance_monitor.reset_metrics()

        with performance_timer("test_operation"):
            time.sleep(0.01)

        metrics = performance_monitor.get_metrics("test_operation")
        assert metrics is not None
        assert metrics.call_count == 1
        assert metrics.total_time > 0.005

    def test_timer_with_exception(self):
        """Test timer behavior when exception occurs."""
        from cespy.core.performance import performance_monitor
        performance_monitor.reset_metrics()

        with pytest.raises(ValueError):
            with performance_timer("error_operation"):
                time.sleep(0.01)
                raise ValueError("Test error")

        # Should still record metrics despite exception
        metrics = performance_monitor.get_metrics("error_operation")
        assert metrics is not None
        assert metrics.call_count == 1


class TestRegexCache:
    """Test RegexCache functionality."""

    def test_cache_creation(self):
        """Test cache creation and initialization."""
        cache = RegexCache(max_size=100)

        assert len(cache.cache) == 0
        assert cache.max_size == 100
        assert cache.hit_count == 0
        assert cache.miss_count == 0

    def test_pattern_caching(self):
        """Test pattern compilation and caching."""
        cache = RegexCache()

        # First access should be a cache miss
        pattern1 = cache.get_pattern(r'\d+')
        assert cache.miss_count == 1
        assert cache.hit_count == 0

        # Second access should be a cache hit
        pattern2 = cache.get_pattern(r'\d+')
        assert cache.miss_count == 1
        assert cache.hit_count == 1

        # Should be the same compiled pattern object
        assert pattern1 is pattern2

    def test_pattern_with_flags(self):
        """Test pattern caching with different flags."""
        cache = RegexCache()

        pattern1 = cache.get_pattern(r'test', re.IGNORECASE)
        pattern2 = cache.get_pattern(r'test', 0)  # No flags
        pattern3 = cache.get_pattern(r'test', re.IGNORECASE)  # Same as pattern1

        # Different flags should create different cache entries
        assert pattern1 is not pattern2
        assert pattern1 is pattern3
        assert cache.miss_count == 2  # Two different patterns
        assert cache.hit_count == 1   # One hit for pattern3

    def test_cache_eviction(self):
        """Test cache eviction when max size is reached."""
        cache = RegexCache(max_size=2)

        # Fill cache to capacity
        pattern1 = cache.get_pattern(r'pattern1')
        pattern2 = cache.get_pattern(r'pattern2')
        assert len(cache.cache) == 2

        # Adding third pattern should evict first (FIFO)
        pattern3 = cache.get_pattern(r'pattern3')
        assert len(cache.cache) == 2

        # First pattern should have been evicted
        pattern1_new = cache.get_pattern(r'pattern1')
        assert cache.miss_count == 4  # Original 3 + 1 for re-compilation

    def test_cache_stats(self):
        """Test cache statistics."""
        cache = RegexCache()

        # Generate some cache activity
        cache.get_pattern(r'test1')
        cache.get_pattern(r'test2')
        cache.get_pattern(r'test1')  # Hit
        cache.get_pattern(r'test3')
        cache.get_pattern(r'test2')  # Hit

        stats = cache.get_stats()
        assert stats['hit_count'] == 2
        assert stats['miss_count'] == 3
        assert stats['hit_rate'] == 40.0  # 2/5 * 100
        assert stats['cache_size'] == 3

    def test_cache_clear(self):
        """Test cache clearing functionality."""
        cache = RegexCache()

        cache.get_pattern(r'test1')
        cache.get_pattern(r'test2')
        assert len(cache.cache) == 2

        cache.clear()
        assert len(cache.cache) == 0
        assert cache.hit_count == 0
        assert cache.miss_count == 0


class TestCachedRegex:
    """Test cached_regex function."""

    def test_cached_regex_function(self):
        """Test module-level cached_regex function."""
        # Clear global cache first
        from cespy.core.performance import regex_cache
        regex_cache.clear()

        pattern1 = cached_regex(r'\w+')
        pattern2 = cached_regex(r'\w+')

        assert pattern1 is pattern2
        assert regex_cache.hit_count >= 1  # Should have at least one hit

    def test_pattern_functionality(self):
        """Test that cached patterns work correctly."""
        pattern = cached_regex(r'R(\d+)')

        match = pattern.match("R123 net1 net2 1k")
        assert match is not None
        assert match.group(1) == "123"

        no_match = pattern.match("C456 net1 net2 1u")
        assert no_match is None


class TestPerformanceOptimizer:
    """Test PerformanceOptimizer utility class."""

    def test_file_operation_optimization(self):
        """Test file operation optimization recommendations."""
        # Small file
        small_rec = PerformanceOptimizer.optimize_file_operations(0.5)
        assert small_rec['read_mode'] == 'full'
        assert small_rec['use_mmap'] is False

        # Medium file
        medium_rec = PerformanceOptimizer.optimize_file_operations(50)
        assert medium_rec['read_mode'] == 'chunked'
        assert medium_rec['use_mmap'] is True

        # Large file
        large_rec = PerformanceOptimizer.optimize_file_operations(500)
        assert large_rec['read_mode'] == 'streaming'
        assert large_rec['use_compression'] is True

    def test_regex_optimization(self):
        """Test regex pattern optimization analysis."""
        patterns = [
            r'simple_pattern',
            r'.*dangerous.*pattern.*',  # Multiple .* should be flagged
            r'.*start_pattern',         # Starting with .* should be noted
            r'complex|choice|with|many|alternatives|here|too',  # Many alternatives
        ]

        recommendations = PerformanceOptimizer.optimize_regex_patterns(patterns)

        assert recommendations['compile_patterns'] is True
        assert recommendations['use_cache'] is True
        assert len(recommendations['problematic_patterns']) > 0
        assert len(recommendations['optimizations']) > 0

    def test_memory_optimization(self):
        """Test memory usage optimization recommendations."""
        # Test with mocked platform info
        with patch('cespy.core.performance.get_platform_info') as mock_get_info:
            from cespy.core.platform import PlatformInfo, OSType, Architecture

            mock_info = PlatformInfo(
                os_type=OSType.LINUX,
                architecture=Architecture.X86_64,
                os_version="5.4",
                python_version="3.9",
                is_wine_available=False,
                wine_prefix=None,
                cpu_count=8,
                total_memory_gb=16.0
            )
            mock_get_info.return_value = mock_info

            # Large data requiring streaming
            large_rec = PerformanceOptimizer.optimize_memory_usage(10000, 'analysis')  # 10GB
            assert large_rec['use_streaming'] is True
            assert large_rec['use_memory_mapping'] is True

            # Small data that can be loaded fully
            small_rec = PerformanceOptimizer.optimize_memory_usage(100, 'parsing')  # 100MB
            assert small_rec.get('load_fully') is True or small_rec.get('chunk_size_mb') is not None


class TestBenchmarkFunction:
    """Test benchmark_function utility."""

    def test_basic_benchmarking(self):
        """Test basic function benchmarking."""
        def test_func(x):
            return x * 2

        results = benchmark_function(test_func, 5, iterations=10)

        assert results['iterations'] == 10
        assert results['total_time'] > 0
        assert results['avg_time'] > 0
        assert results['min_time'] > 0
        assert results['max_time'] >= results['min_time']
        assert 'std_dev' in results

    def test_benchmark_with_kwargs(self):
        """Test benchmarking with keyword arguments."""
        def test_func(x, multiplier=2):
            return x * multiplier

        results = benchmark_function(test_func, 5, multiplier=3, iterations=5)

        assert results['iterations'] == 5
        assert results['total_time'] > 0


class TestModuleFunctions:
    """Test module-level utility functions."""

    def test_enable_performance_monitoring(self):
        """Test enable/disable performance monitoring."""
        from cespy.core.performance import performance_monitor

        original_state = performance_monitor.enabled

        try:
            enable_performance_monitoring(False)
            assert performance_monitor.enabled is False

            enable_performance_monitoring(True)
            assert performance_monitor.enabled is True

        finally:
            performance_monitor.enabled = original_state

    def test_get_performance_report(self):
        """Test performance report generation."""
        from cespy.core.performance import performance_monitor
        performance_monitor.reset_metrics()

        # Generate some performance data
        performance_monitor.record_execution("test_func1", 0.5)
        performance_monitor.record_execution("test_func2", 1.0)

        report = get_performance_report()
        assert isinstance(report, str)
        assert "Performance Report" in report
        assert "test_func1" in report
        assert "test_func2" in report


class TestErrorHandling:
    """Test error handling in performance monitoring."""

    def test_profiling_with_exception(self):
        """Test that profiling handles function exceptions correctly."""
        from cespy.core.performance import performance_monitor
        performance_monitor.reset_metrics()

        @profile_performance()
        def failing_function():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            failing_function()

        # Should still record timing even with exception
        metrics = performance_monitor.get_metrics("failing_function")
        assert metrics is not None
        assert metrics.call_count == 1

    def test_memory_profiling_without_psutil(self):
        """Test memory profiling when psutil is not available."""
        from cespy.core.performance import performance_monitor
        performance_monitor.reset_metrics()

        with patch('builtins.__import__', side_effect=ImportError("No psutil")):
            @profile_performance(include_memory=True)
            def test_function():
                return "test"

            result = test_function()
            assert result == "test"

            # Should work without memory monitoring
            metrics = performance_monitor.get_metrics("test_function")
            assert metrics is not None


if __name__ == "__main__":
    pytest.main([__file__])
