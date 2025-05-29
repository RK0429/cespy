# Migration Guide for Cespy 2.0

This guide helps users migrate from older versions of cespy to the new refactored architecture. The refactoring preserves backward compatibility while providing new capabilities and improved performance.

## Overview of Changes

### Major Improvements
- **Enhanced Cross-Platform Support**: Automatic platform detection and Wine support for Unix systems
- **Performance Optimization**: Built-in profiling, caching, and parallel execution
- **API Consistency**: Standardized naming conventions and parameter validation
- **Better Analysis Tools**: Enhanced Monte Carlo with parallel execution and visualization
- **Modular Architecture**: Improved separation of concerns and extensibility

### Backward Compatibility
- **All existing APIs work**: Your current code will continue to function
- **Deprecation warnings**: Outdated methods show warnings with migration suggestions
- **Gradual migration**: You can adopt new features incrementally

## Quick Start Migration

### 1. Enable Performance Monitoring (Recommended)
```python
from cespy.core import enable_performance_monitoring, get_performance_report

# Enable monitoring to identify bottlenecks
enable_performance_monitoring(True)

# Your existing code here...

# Get performance insights
print(get_performance_report())
```

### 2. Use Platform Optimization (Recommended)
```python
from cespy.core import get_optimal_workers, get_platform_info

# Get platform-aware settings
workers = get_optimal_workers(memory_intensive=True)
info = get_platform_info()

# Use in your analyses
mc = MonteCarloAnalysis(
    'circuit.asc', 
    num_runs=1000,
    parallel=True,
    max_workers=workers  # Platform-optimized
)
```

## Enhanced Analysis Features

### Monte Carlo Analysis Improvements
```python
# Enhanced Monte Carlo with new features
mc = MonteCarloAnalysis(
    'circuit.asc',
    num_runs=1000,
    parallel=True,                    # NEW: Parallel execution
    use_testbench_mode=False,         # NEW: Individual run mode
    progress_callback=my_callback     # NEW: Progress reporting
)

# Enhanced statistics and visualization
stats = mc.get_measurement_statistics('Vout')
print(f"Mean: {stats['mean']}, Std: {stats['std']}")
```

This migration guide provides comprehensive information for transitioning to cespy 2.0 while maintaining compatibility with existing code.