# cespy

A unified Python toolkit for automating SPICE circuit simulators, merging functionality from **kupicelib** and **kuPyLTSpice**. It supports LTSpice, NGSpice, QSpice, and Xyce, providing schematic editing, simulation control, and result analysis.

## Features

- Schematic editing for LTSpice `.asc` and QSpice `.qsch` files
- Simulation orchestration across multiple SPICE engines (LTSpice, NGSpice, QSpice, Xyce)
- Parsing `.raw` waveform files and `.log` log files
- Analysis tools: Monte Carlo, worst-case, sensitivity, and tolerance deviation analyses
- Client-server mode for remote or parallel simulation execution

## Installation

Install via pip:

```bash
pip install cespy
```

Or using Poetry:

```bash
poetry add cespy
```

## Quickstart

### Editing a Schematic

```python
from cespy.editor.asc_editor import AscEditor

# Load an LTSpice schematic
editor = AscEditor("circuit.asc")
# Update a component value
editor.set_component_value("R1", 10e3)
# Save changes
editor.save_netlist("circuit_modified.asc")
```

### Running a Simulation

```python
from cespy.simulators import LTspice

lt = LTspice()  # choose the LTSpice engine
lt.run("circuit_modified.asc")
# Parse results
from cespy.raw.raw_read import RawRead
raw = RawRead("circuit_modified.raw")
data = raw.get_data()
```

## Contributing

Contributions are welcome! Please see the [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

This project is licensed under the **GPL-3.0** License. See [LICENSE](LICENSE) for details.
