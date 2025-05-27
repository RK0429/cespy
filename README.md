# cespy

A Python toolkit for automating SPICE circuit simulators (LTSpice, NGSpice, QSpice, Xyce), providing schematic editing, simulation control, result parsing, and analysis tools.

## Features

- Schematic editing: modify LTSpice `.asc` and QSpice `.qsch` files programmatically.
- Simulation execution: run simulations headlessly with LTSpice, NGSpice, QSpice, and Xyce.
- Result parsing: parse `.raw` waveform files and `.log` files for step data and operating points.
- Analysis toolkit: Monte Carlo, worst-case, sensitivity, tolerance deviation, and failure mode analysis.
- Multi-engine support: switch between simulators easily through a unified API.
- Client-server mode: run simulations remotely via a server-client architecture.
- Command-line tools: convert schematics, plot raw data, run simulation server, and more.

## Installation

Install via pip:

```bash
pip install cespy
```

Or with Poetry:

```bash
poetry add cespy
```

## Quick Start

```python
from cespy.simulators import LTSpiceSimulator
from cespy.sim import SimRunner

# Initialize an LTSpice simulator
sim = LTSpiceSimulator(executable_path="C:\\Program Files\\LTspiceXVII\\XVIIx64.exe")

# Run a simulation job
runner = SimRunner(simulator=sim)
result = runner.run("circuit.asc")

# Parse raw waveform data
raw_data = sim.parse_raw("circuit.raw")

# Analyze results (e.g., get voltage at node 'V(out)')
voltage_out = raw_data["V(out)"]
```

For more examples and detailed usage, see the [documentation](https://github.com/username/cespy).

## License

This project is licensed under the GNU GPL v3.0. See the [LICENSE](LICENSE) file for details.
