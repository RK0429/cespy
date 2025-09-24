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
    # Patterns
    "COMPONENT_VALUE_PATTERN",
    "COMPONENT_REF_PATTERN",
    "PARAM_PATTERN",
    "SPICE_PATTERNS",
    # Constants
    "DEFAULT_ENCODING",
    "DEFAULT_TIMEOUT",
    "SUPPORTED_SIMULATORS",
    "SPICE_EXTENSIONS",
    # Platform management
    "OSType",
    "Architecture",
    "PlatformInfo",
    "PlatformManager",
    "get_platform_info",
    "get_optimal_workers",
    "is_simulator_available",
    "get_simulator_path",
    # API consistency
    "deprecated",
    "standardize_parameters",
    "APIStandardizer",
    "ParameterValidator",
    "ensure_api_consistency",
    "create_compatibility_wrapper",
    # Performance optimization
    "PerformanceMetrics",
    "PerformanceMonitor",
    "profile_performance",
    "performance_timer",
    "cached_regex",
    "PerformanceOptimizer",
    "benchmark_function",
    "get_performance_report",
    "enable_performance_monitoring",
]
