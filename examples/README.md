# CESPy Examples

This directory contains comprehensive examples demonstrating all major features and use cases of the CESPy (Circuit Engineering Simulation Python) toolkit.

## Overview

CESPy is a unified Python toolkit for SPICE circuit simulation that supports multiple simulators (LTSpice, NGSpice, QSpice, Xyce) and provides advanced analysis capabilities including Monte Carlo analysis, worst-case analysis, sensitivity analysis, and more.

## Example Files

### 01_basic_simulation.py
**Basic Simulation Examples**
- Getting started with each SPICE simulator
- Simple circuit simulation workflows
- Parameter sweeps and stepping
- Reading and processing simulation results

Key demonstrations:
- LTSpice, NGSpice, QSpice, and Xyce simulation
- Basic raw data file operations
- Parameter modification and sweeps

### 02_circuit_editing.py
**Circuit Editing and Manipulation**
- Programmatic schematic (.asc) editing
- SPICE netlist manipulation and validation
- Component creation and modification
- Parametric design workflows

Key demonstrations:
- AscEditor for LTSpice schematic files
- SpiceEditor for netlist manipulation
- ComponentFactory for creating circuit elements
- Circuit validation and error checking

### 03_analysis_toolkit.py
**Advanced Analysis Capabilities**
- Monte Carlo statistical analysis
- Worst-case corner analysis
- Sensitivity analysis
- Tolerance budget analysis
- Failure mode and reliability analysis

Key demonstrations:
- Statistical variation analysis with component tolerances
- Corner case analysis for specification verification
- Parameter sensitivity studies
- Reliability and MTBF calculations

### 04_data_processing.py
**Data Processing and Visualization**
- Raw file read/write operations
- Lazy loading for large datasets
- Data streaming and caching
- Statistical analysis and visualization

Key demonstrations:
- Memory-efficient data handling
- Intelligent caching systems
- Histogram analysis and distribution fitting
- Advanced visualization techniques

### 05_batch_distributed.py
**Batch and Distributed Simulation**
- Batch processing with parameter sweeps
- Parallel simulation using threading/multiprocessing
- Client-server distributed architecture
- Performance optimization techniques

Key demonstrations:
- Automated batch job management
- Parallel execution strategies
- Distributed simulation infrastructure
- Performance monitoring and optimization

### 06_platform_integration.py
**Platform Integration and Compatibility**
- Cross-platform system detection
- Automatic simulator detection
- File encoding and path handling
- API compatibility and migration

Key demonstrations:
- Windows, macOS, and Linux compatibility
- Robust file system operations
- Environment configuration automation
- Legacy API migration helpers

## Getting Started

1. **Prerequisites**
   ```bash
   # Install required dependencies
   pip install numpy matplotlib scipy pandas
   
   # Install CESPy (if packaged)
   pip install cespy
   ```

2. **Run Examples**
   ```bash
   # Run individual examples
   python 01_basic_simulation.py
   python 02_circuit_editing.py
   # ... etc
   
   # Or run all examples
   python run_all_examples.py
   ```

3. **Simulator Requirements**
   - At least one SPICE simulator installed (LTSpice, NGSpice, QSpice, or Xyce)
   - Simulator executables in PATH or manually configured
   - See platform integration examples for automatic detection

## Example Structure

Each example file follows this structure:

```python
#!/usr/bin/env python3
"""
Example Title and Description
"""

# Standard imports
import os, sys, time, numpy as np
from pathlib import Path

# CESPy imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from cespy import *

def example_specific_function():
    """Demonstrate specific functionality."""
    print("=== Example Section ===")
    # Implementation with error handling
    try:
        # Example code
        pass
    except Exception as e:
        print(f"Error: {e}")

def main():
    """Run all examples in the file."""
    # Execute all example functions
    pass

if __name__ == "__main__":
    main()
```

## Key Features Demonstrated

### Simulation Capabilities
- **Multi-simulator support**: LTSpice, NGSpice, QSpice, Xyce
- **Analysis types**: Transient, AC, DC, Noise, Monte Carlo
- **Parameter sweeps**: Linear, logarithmic, custom
- **Batch processing**: Automated parameter studies

### Circuit Editing
- **Schematic editing**: Programmatic modification of .asc files
- **Netlist manipulation**: Component addition, modification, validation
- **Parametric design**: Template-based circuit generation
- **Error checking**: Circuit validation and floating node detection

### Advanced Analysis
- **Statistical analysis**: Monte Carlo with component tolerances
- **Design verification**: Worst-case corner analysis
- **Optimization**: Sensitivity analysis for design tuning
- **Reliability**: Failure mode analysis and MTBF calculations

### Data Management
- **Large dataset handling**: Lazy loading and streaming
- **Performance optimization**: Intelligent caching systems
- **Visualization**: Advanced plotting and analysis
- **Cross-platform**: Robust file and encoding handling

### Integration Features
- **Platform support**: Windows, macOS, Linux compatibility
- **Environment detection**: Automatic simulator location
- **API evolution**: Backward compatibility and migration
- **Configuration**: Automated setup and environment management

## Common Usage Patterns

### Basic Simulation Workflow
```python
from cespy import LTspice, SimRunner, RawRead

# Initialize simulator
simulator = LTspice()
runner = SimRunner()
runner.simulator = simulator

# Run simulation
runner.set_circuit("my_circuit.asc")
result = runner.run()

# Process results
if result:
    raw_reader = RawRead("my_circuit.raw")
    data = raw_reader.get_trace("V(output)")
```

### Monte Carlo Analysis
```python
from cespy.sim.toolkit import MonteCarloAnalysis

mc = MonteCarloAnalysis()
mc.set_circuit("circuit.net")
mc.add_component_variation("R1", nominal=1000, tolerance=0.05)
results = mc.run_analysis()
statistics = mc.get_statistics()
```

### Batch Processing
```python
from cespy.sim import SimBatch

batch = SimBatch()
batch.set_base_circuit("base.net")

# Add parameter variations
for r_val in [100, 1000, 10000]:
    batch.add_job(parameters={"R": str(r_val)})

results = batch.run_batch()
```

## Tips and Best Practices

1. **Error Handling**: Always wrap simulator calls in try-except blocks
2. **Resource Management**: Clean up temporary files after use
3. **Performance**: Use lazy loading for large datasets
4. **Compatibility**: Use Path objects for cross-platform file handling
5. **Configuration**: Set up environment variables for simulator paths

## Troubleshooting

### Common Issues

1. **Simulator not found**
   - Check PATH environment variable
   - Verify simulator installation
   - Use absolute paths if needed

2. **File encoding errors**
   - Use the encoding detection utilities
   - Specify encoding explicitly when reading files

3. **Memory issues with large files**
   - Use lazy loading (RawReadLazy)
   - Enable data streaming
   - Implement data caching

4. **Platform compatibility**
   - Use Path objects instead of string paths
   - Check platform-specific examples

### Getting Help

- Check the individual example files for detailed implementations
- Review error messages and stack traces
- Consult the main CESPy documentation
- Test with simple circuits first before complex analysis

## Contributing

To add new examples:

1. Follow the existing file naming convention
2. Include comprehensive error handling
3. Add cleanup code for temporary files
4. Document all major features demonstrated
5. Test on multiple platforms if possible

## License

These examples are provided under the same license as the CESPy package.