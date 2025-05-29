# Performance Tuning Guide for Cespy

This guide provides comprehensive information on optimizing performance in cespy, from basic configuration to advanced optimization techniques.

## Quick Start Performance Tips

### 1. Enable Performance Monitoring
```python
from cespy.core import enable_performance_monitoring

# Enable monitoring to identify bottlenecks
enable_performance_monitoring(True)

# Your code here...

# Get performance report
from cespy.core import get_performance_report
print(get_performance_report())
```

### 2. Use Parallel Execution
```python
from cespy.sim.toolkit import MonteCarloAnalysis

# Enable parallel execution for Monte Carlo
mc = MonteCarloAnalysis(
    'circuit.asc', 
    num_runs=1000,
    parallel=True,          # Enable parallel execution
    max_workers=4           # Limit workers based on your system
)
```

### 3. Optimize for Your Platform
```python
from cespy.core import get_platform_info, get_optimal_workers

info = get_platform_info()
optimal_workers = get_optimal_workers(memory_intensive=True)

print(f"Platform: {info.os_type.value}")
print(f"Recommended workers: {optimal_workers}")
print(f"Memory per worker: {info.memory_per_worker_gb:.1f} GB")
```

## Performance Monitoring

### Automatic Function Profiling
Use the `@profile_performance` decorator to automatically monitor function performance:

```python
from cespy.core import profile_performance

@profile_performance(include_memory=True, log_calls=True)
def expensive_analysis():
    # Your analysis code
    pass

# Performance metrics are automatically collected
```

### Manual Performance Timing
For specific code blocks:

```python
from cespy.core import performance_timer

with performance_timer("data_processing"):
    # Your code here
    process_large_dataset()

# Timing data is automatically recorded
```

### Performance Benchmarking
Run standardized benchmarks to establish baselines:

```python
from cespy.core.benchmarks import run_performance_benchmarks

# Run all benchmarks and save as baseline
suite = run_performance_benchmarks(
    baseline_file=Path("performance_baseline.json"),
    save_as_baseline=True
)

print(suite.generate_report())
```

## Optimization Strategies

### 1. File Operations

#### Small Files (< 1 MB)
```python
# For small netlists and schematics
with open('small_circuit.net', 'r') as f:
    content = f.read()  # Read entire file at once
```

#### Medium Files (1-100 MB)
```python
# For medium-sized raw files
from cespy.raw import RawRead

# Use memory mapping for better performance
raw_data = RawRead('medium_data.raw', use_mmap=True)
```

#### Large Files (> 100 MB)
```python
# For large raw files, use streaming
from cespy.raw import RawFileStreamer

streamer = RawFileStreamer('large_data.raw')
for chunk in streamer.stream_data(chunk_size=1024*1024):  # 1MB chunks
    process_chunk(chunk)
```

### 2. Regular Expressions

#### Use Cached Patterns
```python
from cespy.core import cached_regex

# Instead of re.compile() every time
pattern = cached_regex(r'R\w+\s+\S+\s+\S+\s+(\S+)')

# Cached patterns are reused automatically
for line in netlist_lines:
    match = pattern.match(line)
```

#### Optimize Pattern Usage
```python
# Good: Specific patterns
component_pattern = cached_regex(r'^([RLCVIJM]\w*)\s+')

# Avoid: Greedy patterns that cause backtracking
# bad_pattern = r'.*?value.*?=.*?(\d+.*)'  # Causes backtracking
good_pattern = r'value\s*=\s*([^\s]+)'     # More specific
```

### 3. Memory Management

#### Lazy Loading for Large Datasets
```python
from cespy.raw import RawReadLazy

# Load raw file with lazy loading
raw_reader = RawReadLazy('large_simulation.raw')

# Data is loaded only when accessed
voltage_trace = raw_reader.get_wave('V(out)')  # Loads only this trace
```

#### Memory-Mapped Files
```python
import mmap

def process_large_file(file_path):
    with open(file_path, 'rb') as f:
        with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mmapped_file:
            # Process file without loading into memory
            return parse_mapped_data(mmapped_file)
```

#### Cache Configuration
```python
from cespy.raw import RawDataCache

# Configure cache for your use case
cache = RawDataCache(
    max_size_mb=500,        # 500 MB cache
    policy='LRU',           # Least Recently Used eviction
    persistence=True        # Save cache between sessions
)
```

### 4. Parallel Processing

#### CPU-Bound Operations
```python
from concurrent.futures import ProcessPoolExecutor
from cespy.core import get_optimal_workers

# Use process pool for CPU-intensive tasks
max_workers = get_optimal_workers(memory_intensive=False)

with ProcessPoolExecutor(max_workers=max_workers) as executor:
    futures = [executor.submit(run_simulation, params) for params in param_sets]
    results = [future.result() for future in futures]
```

#### I/O-Bound Operations
```python
from concurrent.futures import ThreadPoolExecutor

# Use thread pool for I/O-intensive tasks
with ThreadPoolExecutor(max_workers=10) as executor:
    futures = [executor.submit(read_file, path) for path in file_paths]
    data = [future.result() for future in futures]
```

#### Analysis-Specific Optimizations
```python
# Monte Carlo with optimized settings
mc = MonteCarloAnalysis(
    'circuit.asc',
    num_runs=10000,
    parallel=True,
    max_workers=get_optimal_workers(memory_intensive=True),
    use_testbench_mode=True,  # Faster for supported simulators
    seed=42                   # Reproducible results
)

# Use separate run mode for better error recovery
mc_robust = MonteCarloAnalysis(
    'circuit.asc',
    num_runs=1000,
    use_testbench_mode=False,  # Individual runs, better fault tolerance
    parallel=True
)
```

## Platform-Specific Optimizations

### Windows Optimizations
```python
from cespy.core import get_platform_info

if get_platform_info().is_windows:
    # Use job objects for better process management
    import subprocess
    
    # Windows-specific simulator execution
    env = os.environ.copy()
    env['PROCESSOR_AFFINITY_MASK'] = '0xFF'  # Use all cores
    
    process = subprocess.Popen(
        command,
        env=env,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
    )
```

### Linux/Unix Optimizations
```python
if get_platform_info().is_unix_like:
    # Use tmpfs for temporary files (faster I/O)
    import tempfile
    
    with tempfile.TemporaryDirectory(dir='/tmp') as temp_dir:
        # Temporary files in RAM-based filesystem
        temp_netlist = Path(temp_dir) / 'circuit.net'
        # Process files in tmpfs
```

### macOS Optimizations
```python
if get_platform_info().is_macos:
    # Handle Rosetta translation for x86_64 simulators on Apple Silicon
    if get_platform_info().architecture == Architecture.ARM64:
        # May need different optimization strategies
        max_workers = min(4, get_optimal_workers())  # Conservative on Rosetta
```

## Simulator-Specific Performance

### LTSpice Optimization
```python
# Use testbench mode for Monte Carlo (much faster)
mc = MonteCarloAnalysis('circuit.asc', use_testbench_mode=True)
mc.prepare_testbench(num_runs=10000)
mc.run_testbench()

# Optimize LTSpice command line
ltspice_options = {
    'max_threads': get_optimal_workers(),
    'ascii_raw': False,  # Binary is faster to parse
    'batch_mode': True,
    'no_splash': True
}
```

### NGSpice Optimization
```python
# NGSpice typically benefits from fewer parallel processes
ngspice_workers = min(2, get_optimal_workers())  # NGSpice can be unstable with many processes

# Use optimized netlist format
netlist_options = {
    'use_subcircuits': True,   # Better for large circuits
    'optimize_nodes': True,    # Reduce node count
    'merge_parallel': True     # Combine parallel components
}
```

### QSpice Optimization
```python
# QSpice usually handles parallel well
qspice_options = {
    'threads': get_optimal_workers(),
    'fast_mode': True,
    'reduced_precision': False  # Maintain accuracy
}
```

## Memory Optimization

### Large Circuit Analysis
```python
# For large circuits, use streaming analysis
from cespy.editor import NetlistOptimizer

# Optimize netlist before simulation
optimizer = NetlistOptimizer(level='moderate')
optimized_netlist = optimizer.optimize('large_circuit.net')

# Use lazy loading for results
raw_reader = RawReadLazy(optimized_netlist.replace('.net', '.raw'))
```

### Memory-Conscious Monte Carlo
```python
# Process results in batches to limit memory usage
def batch_monte_carlo(circuit_file, total_runs, batch_size=100):
    all_results = []
    
    for start_run in range(0, total_runs, batch_size):
        batch_runs = min(batch_size, total_runs - start_run)
        
        mc = MonteCarloAnalysis(circuit_file, num_runs=batch_runs)
        batch_results = mc.run_analysis()
        
        # Process batch results immediately
        process_results(batch_results)
        all_results.extend(batch_results)
        
        # Force garbage collection
        import gc
        gc.collect()
    
    return all_results
```

### Garbage Collection Optimization
```python
import gc

# For long-running analyses, manage garbage collection
def optimized_long_analysis():
    for i, simulation in enumerate(long_simulation_list):
        result = run_simulation(simulation)
        process_result(result)
        
        # Periodic garbage collection
        if i % 100 == 0:
            gc.collect()
```

## Profiling and Debugging

### CPU Profiling
```python
import cProfile
import pstats

def profile_analysis():
    profiler = cProfile.Profile()
    profiler.enable()
    
    # Your analysis code
    mc = MonteCarloAnalysis('circuit.asc', num_runs=1000)
    results = mc.run_analysis()
    
    profiler.disable()
    
    # Analyze results
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(20)  # Top 20 functions

profile_analysis()
```

### Memory Profiling
```python
try:
    from memory_profiler import profile
    
    @profile
    def memory_intensive_analysis():
        # Your analysis code
        pass
        
    memory_intensive_analysis()
except ImportError:
    print("Install memory_profiler: pip install memory-profiler")
```

### Custom Performance Metrics
```python
from cespy.core import PerformanceMonitor

# Create custom performance monitor
custom_monitor = PerformanceMonitor()
custom_monitor.threshold_warning_time = 0.5  # Warn at 500ms
custom_monitor.threshold_critical_time = 2.0  # Critical at 2s

# Use with context manager
with performance_timer("custom_operation"):
    expensive_operation()

# Get detailed metrics
metrics = custom_monitor.get_metrics("custom_operation")
print(f"Average time: {metrics.avg_time:.3f}s")
print(f"Call count: {metrics.call_count}")
```

## Performance Testing

### Automated Performance Tests
```python
from cespy.core.benchmarks import create_performance_test

# Create pytest performance test
test_regex_performance = create_performance_test(
    "regex", 
    baseline_file=Path("benchmarks/regex_baseline.json")
)

def test_my_analysis_performance():
    """Custom performance test"""
    import time
    
    start_time = time.perf_counter()
    
    # Your analysis
    mc = MonteCarloAnalysis('test_circuit.asc', num_runs=100)
    results = mc.run_analysis()
    
    end_time = time.perf_counter()
    duration = end_time - start_time
    
    # Assert performance requirements
    assert duration < 10.0, f"Analysis took too long: {duration:.2f}s"
    assert len(results) == 100, "Incorrect number of results"
```

### Continuous Performance Monitoring
```python
# Add to CI/CD pipeline
def ci_performance_check():
    from cespy.core.benchmarks import run_performance_benchmarks
    
    suite = run_performance_benchmarks(
        baseline_file=Path("ci/performance_baseline.json")
    )
    
    comparison = suite.compare_with_baseline(tolerance=0.15)  # 15% tolerance
    
    if comparison['status'] == 'failed':
        print("Performance regression detected!")
        for regression in comparison['regressions']:
            print(f"  {regression['benchmark']}: {regression['change_percent']:+.1f}%")
        exit(1)
    
    print("Performance check passed")

if __name__ == "__main__":
    ci_performance_check()
```

## Best Practices Summary

### 1. Measurement First
- Always measure before optimizing
- Use profiling to identify real bottlenecks
- Establish baselines for critical operations

### 2. Platform Awareness
- Use platform-specific optimizations
- Respect system resource limits
- Handle cross-platform differences gracefully

### 3. Memory Management
- Use lazy loading for large datasets
- Implement appropriate caching strategies
- Monitor memory usage in long-running processes

### 4. Parallel Processing
- Choose appropriate parallelism model (threads vs. processes)
- Consider memory overhead of parallel execution
- Handle errors gracefully in parallel code

### 5. Continuous Monitoring
- Implement performance regression tests
- Monitor performance in production
- Regular performance reviews and optimization

### 6. Documentation
- Document performance characteristics
- Include performance requirements in tests
- Share optimization knowledge with team

This guide provides the foundation for optimal performance with cespy. Regular profiling and monitoring will help maintain performance as the codebase evolves.