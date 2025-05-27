# User Guide for cespy

## Purpose & Scope

This User Guide provides step-by-step instructions and examples for using `cespy`, the unified Python toolkit for automating SPICE circuit simulators (LTSpice, NGSpice, QSpice, Xyce). It covers installation, core modules, command-line tools, and advanced workflows.

## Table of Contents

1. Installation
2. Quick Start Example
3. Schematic Editing
   - Loading and Saving ASC/QSCH Files
   - Modifying Components and Parameters
4. Running Simulations
   - Direct Execution with `SimRunner`
   - Parallel Simulations and Callbacks
5. Result Parsing
   - Reading Raw Waveform Data
   - Extracting Log Information
6. Analysis Toolkit
   - Monte Carlo Analysis
   - Worst-Case and Sensitivity Analysis
7. Client-Server Mode
   - Starting the Simulation Server
   - Submitting Jobs via Client
8. Command-Line Tools
   - `cespy-asc-to-qsch`
   - `cespy-raw-convert`
   - `cespy-run-server` / `cespy-sim-client`

---

## Architecture Overview

```text
 .---------------.     .-----------.     .--------------.     .---------------.
 |  ASC Editor   | --> | SimRunner | --> | RawRead/Log  | --> | Analysis     |
 | (AscEditor,   |     | (run/run_now)   | (RawRead,     | Toolkit)      |
 |  QschEditor)  |     |             )  |  LTSpiceLog)  | (MonteCarlo,  |
 '---------------'     '-----------'     '--------------'     '---------------'
```

*Figure: High-level workflow of `cespy`.*

## 1. Installation

Install via PyPI or Poetry:

```bash
pip install cespy
# or
poetry add cespy
```

## 2. Quick Start Example

```python
from cespy.simulators import LTSpiceSimulator
from cespy.sim import SimRunner

# Initialize LTSpice simulator with executable path
sim = LTSpiceSimulator.create_from(
    path_to_exe=r"C:\Program Files\LTspiceXVII\XVIIx64.exe"
)

# Configure runner
runner = SimRunner(simulator=sim)

# Run a simulation on an existing .asc file
raw_file, log_file = runner.run(
    circuit_file="examples/bandpass.asc",
    run_filename="bandpass_test"
)

# Parse results
from cespy.raw.raw_read import RawRead
waveform = RawRead(raw_file, traces=["V(out)"])
print(waveform.get_trace_data("V(out)"))
```

## 3. Schematic Editing

### Loading and Saving

```python
from cespy.editor import AscEditor, QschEditor

# Load an LTSpice schematic
asc = AscEditor("examples/oscillator.asc")
# Modify parameters
asc.set_component_value("R1", "10k")
# Save modified schematic
asc.save_netlist("build/oscillator_mod.asc")
```

### Converting to Qschematics

Use the `cespy-asc-to-qsch` CLI to convert an LTSpice `.asc` file to a QSpice `.qsch` file:

```bash
cespy-asc-to-qsch examples/oscillator.asc converted.qsch
```

### Modifying Components and Parameters

- `get_component_info(reference)` to inspect attributes
- `set_parameter(name, value)` to update `.PARAM` directives
- `add_instruction(instruction)` to insert SPICE directives

## 4. Running Simulations

### Direct Execution

Use `SimRunner.run()` for asynchronous or `run_now()` for blocking:

```python
runner = SimRunner(simulator=sim)
raw, log = runner.run_now(asc, run_filename="test_run")
```

### Parallel Simulations

```python
# Run up to 4 parallel sims and process via callback
def process(raw_path, log_path):
    print("Sim completed:", raw_path)

runner = SimRunner(
    simulator=sim, parallel_sims=4
)
runner.run(asc, run_filename="batch", callback=process)
runner.wait_completion()
```

## 5. Result Parsing

### Raw Waveform Data

```python
from cespy.raw.raw_read import RawRead
raw = RawRead("bandpass.raw", traces=["V(out)"])
traces = raw.export()
```

### Log Information

```python
from cespy.log.ltsteps import LTSpiceLogReader
log = LTSpiceLogReader("bandpass.log")
log.read_measures()
print(log.dataset["rise_time"])
```

## 6. Analysis Toolkit

Explore Monte Carlo and worst-case analyses:

```python
from cespy.sim.toolkit import MonteCarlo
mc = MonteCarlo(asc_file, sim, runs=1000)
results = mc.run()
```

### Worst-Case and Sensitivity Analysis

```python
from cespy.sim.toolkit import WorstCase, SensitivityAnalysis
wc = WorstCase(asc_file, sim, parameters={'R1': (1e3, 10e3)})
wc_results = wc.run()
sa = SensitivityAnalysis(asc_file, sim, parameter='C1', step=1e-12)
sa_results = sa.run()
```

## 7. Client-Server Mode

### Starting the Server

```bash
cespy-run-server --port 5000
```

### Submitting a Job

```python
from cespy.client_server import sim_client
result = sim_client.submit(
    asc_file, host="localhost", port=5000
)
```

## 8. Command-Line Tools

- `cespy-asc-to-qsch`: Convert `.asc` to `.qsch`
- `cespy-raw-convert`: Export raw data to CSV/Excel/Clipboard
- `cespy-run-server` / `cespy-sim-client`: Remote execution

---

*For more details, refer to the full documentation at* <https://github.com/RK0429/cespy/docs>
