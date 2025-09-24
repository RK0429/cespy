"""
Core utilities package for cespy.

This package contains shared utilities, patterns, and constants used across
the cespy library to reduce code duplication and improve maintainability.
"""

from cespy.core.api_consistency import (
    APIStandardizer,
    ParameterValidator,
    create_compatibility_wrapper,
    deprecated,
    ensure_api_consistency,
    standardize_parameters,
)
from cespy.core.constants import (
    DEFAULT_ENCODING,
    DEFAULT_TIMEOUT,
    SPICE_EXTENSIONS,
    SUPPORTED_SIMULATORS,
)
from cespy.core.patterns import (
    COMPONENT_REF_PATTERN,
    COMPONENT_VALUE_PATTERN,
    PARAM_PATTERN,
    SPICE_PATTERNS,
)
from cespy.core.performance import (
    PerformanceMetrics,
    PerformanceMonitor,
    PerformanceOptimizer,
    benchmark_function,
    cached_regex,
    enable_performance_monitoring,
    get_performance_report,
    performance_timer,
    profile_performance,
)
from cespy.core.platform import (
    Architecture,
    OSType,
    PlatformInfo,
    PlatformManager,
    get_optimal_workers,
    get_platform_info,
    get_simulator_path,
    is_simulator_available,
)

__all__ = [
    "COMPONENT_REF_PATTERN",
    "COMPONENT_VALUE_PATTERN",
    "DEFAULT_ENCODING",
    "DEFAULT_TIMEOUT",
    "PARAM_PATTERN",
    "SPICE_EXTENSIONS",
    "SPICE_PATTERNS",
    "SUPPORTED_SIMULATORS",
    "APIStandardizer",
    "Architecture",
    "OSType",
    "ParameterValidator",
    "PerformanceMetrics",
    "PerformanceMonitor",
    "PerformanceOptimizer",
    "PlatformInfo",
    "PlatformManager",
    "benchmark_function",
    "cached_regex",
    "create_compatibility_wrapper",
    "deprecated",
    "enable_performance_monitoring",
    "ensure_api_consistency",
    "get_optimal_workers",
    "get_performance_report",
    "get_platform_info",
    "get_simulator_path",
    "is_simulator_available",
    "performance_timer",
    "profile_performance",
    "standardize_parameters",
]
