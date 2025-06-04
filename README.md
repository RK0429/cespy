# cespy

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/downloads/)

*Read this in other languages: [日本語](README_ja.md)*

A unified Python toolkit for automating SPICE circuit simulators, merging the capabilities of spicelib and PyLTSpice. cespy provides comprehensive support for schematic editing, simulation execution, result parsing, and advanced circuit analysis across multiple SPICE engines.

## Features

### 🔧 **Multi-Engine Support**

- **LTSpice** - Full automation support with headless execution
- **NGSpice** - Open-source SPICE simulator integration
- **QSpice** - Next-generation Qorvo simulator support
- **Xyce** - Sandia's parallel SPICE simulator integration

### 📝 **Schematic & Netlist Editing**

- Programmatically modify LTSpice `.asc` schematics
- Edit QSpice `.qsch` files without GUI
- Manipulate SPICE netlists with high-level API
- Support for hierarchical circuits and subcircuits
- Parameter sweeps and component value updates

### 📊 **Simulation & Analysis**

- **Monte Carlo Analysis** - Statistical circuit analysis with component tolerances
- **Worst-Case Analysis** - Find extreme operating conditions
- **Sensitivity Analysis** - Identify critical components
- **Tolerance Deviation** - Analyze impact of component variations
- **Failure Mode Analysis** - Evaluate circuit behavior under component failures
- Batch simulation support with parallel execution

### 📈 **Data Processing**

- Parse binary `.raw` waveform files from all supported simulators
- Extract measurement data from `.log` files
- Process `.meas` statements and step information
- Export data for spreadsheet analysis
- Built-in plotting capabilities

### 🌐 **Distributed Computing**

- Client-server architecture for remote simulations
- Run simulations on powerful remote machines
- Parallel job execution and result retrieval

### 🛠️ **Command-Line Tools**

- `cespy-asc-to-qsch` - Convert LTSpice schematics to QSpice format
- `cespy-run-server` - Start a simulation server
- `cespy-sim-client` - Connect to remote simulation servers
- `cespy-ltsteps` - Process log files for spreadsheet import
- `cespy-rawplot` - Plot waveforms from raw files
- `cespy-histogram` - Create histograms from measurement data
- `cespy-raw-convert` - Convert between raw file formats

### 🚀 **Enhanced Core Features**

- **Performance Monitoring** - Built-in profiling and optimization tools
- **API Consistency** - Compatibility wrappers and parameter validation
- **Platform Management** - Cross-platform simulator detection and configuration
- **Advanced Visualization** - Integrated plotting and analysis visualization

## Installation

Install via pip:

```bash
pip install cespy
```

Or with Poetry:

```bash
poetry add cespy
```

For development installation:

```bash
git clone https://github.com/RK0429/cespy.git
cd cespy
poetry install
```

## Quick Start

### Basic Simulation

```python
from cespy import simulate

# Run a simple simulation using the high-level API
result = simulate("circuit.asc", engine="ltspice")

# The simulate function handles everything:
# - Detects the simulator executable
# - Runs the simulation
# - Returns a SimRunner object with results
```

### Advanced Usage

```python
from cespy import LTspice, SpiceEditor, RawRead

# Edit a netlist programmatically
netlist = SpiceEditor("circuit.net")
netlist['R1'].value = 10000  # Change R1 to 10k
netlist['C1'].value = 1e-9   # Change C1 to 1nF
netlist.set_parameters(TEMP=27, VDD=3.3)
netlist.add_instruction(".step param R1 1k 10k 1k")

# Run simulation with specific simulator
sim = LTspice()
sim.run(netlist)

# Parse results
raw = RawRead("circuit.raw")
time = raw.get_trace("time")
vout = raw.get_trace("V(out)")

# Plot results
import matplotlib.pyplot as plt
plt.plot(time.get_wave(), vout.get_wave())
plt.xlabel("Time (s)")
plt.ylabel("Vout (V)")
plt.show()
```

### Monte Carlo Analysis

```python
from cespy.sim.toolkit import MonteCarloAnalysis
from cespy import AscEditor

# Set up circuit with tolerances
circuit = AscEditor("filter.asc")
mc = MonteCarloAnalysis(circuit, num_runs=1000)

# Define component tolerances
mc.set_tolerance("R1", 0.05)  # 5% tolerance
mc.set_tolerance("C1", 0.10)  # 10% tolerance

# Run analysis
mc.run()

# Get results
results = mc.get_results()
```

### Remote Simulation

```python
from cespy.client_server import SimClient

# Connect to remote simulation server
client = SimClient("http://192.168.1.100", port=9000)

# Submit simulation job
job_id = client.run("large_circuit.net")

# Retrieve results when complete
for completed_job in client:
    results = client.get_runno_data(completed_job)
    print(f"Simulation {completed_job} completed: {results}")
```

## Documentation

Full documentation is available at the [project repository](https://github.com/RK0429/cespy).

### Key Modules

- **`cespy.core`** - Core utilities for patterns, performance, and platform management
- **`cespy.editor`** - Schematic and netlist editing tools
- **`cespy.simulators`** - Simulator-specific implementations
- **`cespy.sim`** - Simulation execution and management
- **`cespy.sim.toolkit`** - Advanced analysis tools
- **`cespy.raw`** - Raw waveform file handling
- **`cespy.log`** - Log file parsing utilities
- **`cespy.client_server`** - Distributed simulation support

## Examples

Check the `examples/` directory for comprehensive examples:

- `01_basic_simulation.py` - Getting started with all supported simulators
- `02_circuit_editing.py` - Programmatic schematic and netlist manipulation
- `03_analysis_toolkit.py` - Monte Carlo, worst-case, and sensitivity analysis
- `04_data_processing.py` - Efficient data handling and visualization
- `05_batch_distributed.py` - Parallel and distributed simulation workflows
- `06_platform_integration.py` - Cross-platform compatibility and auto-detection

Run all examples with: `python examples/run_all_examples.py`

## Migration from spicelib/PyLTSpice

If you're migrating from spicelib or PyLTSpice:

- spicelib users: Most APIs remain the same, just update imports from `spicelib` to `cespy`
- PyLTSpice users: Replace `PyLTSpice.LTSpiceSimulation` with `cespy.simulate()` or `cespy.LTspice`

See the [migration guide](docs/migration_guide.md) for detailed instructions.

## Development

For development installation and testing:

```bash
# Install with development dependencies
poetry install

# Run tests
poetry run pytest

# Code quality checks
poetry run black src/ tests/      # Format code
poetry run flake8 src/ tests/     # Lint check
poetry run mypy src/              # Type checking
poetry run pylint src/            # Additional linting

# Build documentation
cd docs && make html
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

## Authors

- Nuno Brum (original spicelib/PyLTSpice author)
- Ryota Kobayashi (cespy unification and maintenance)

## Acknowledgments

cespy is a unified version of:

- **spicelib** - A comprehensive SPICE automation library
- **PyLTSpice** - A specialized LTSpice automation tool

Both projects were originally created by Nuno Brum.
