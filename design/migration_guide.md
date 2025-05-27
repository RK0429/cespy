# Migration Guide to cespy

This guide helps users migrate existing code and workflows from `kupicelib` and `kuPyLTSpice` to the new unified package `cespy`.

## 1. Installation and Import Changes

| Old Package        | New Package Import                 |
|--------------------|------------------------------------|
| `import kupicelib` | `import cespy`                     |
| `from kupicelib.editor import AscEditor` | `from cespy.editor.asc_editor import AscEditor` |
| `from kuPyLTSpice import SimRunner`      | `from cespy.sim import SimRunner`   |

## 2. Core Class Renaming

| Old Class/Function            | New Class/Function                           | Notes                                    |
|-------------------------------|-----------------------------------------------|------------------------------------------|
| `kupicelib.sim.sim_runner.SimRunner` | `cespy.sim.SimRunner`                     | API unchanged, moved module path         |
| `kuPyLTSpice.LTspice()`       | `cespy.simulators.LTSpiceSimulator.create_from()` | Use `create_from` to set executable path |
| `raw_read.RawRead`            | `cespy.raw.raw_read.RawRead`                  | Moved package structure, same interface  |
| `LTSteps`                     | `cespy.log.ltsteps.LTSpiceLogReader`         | Renamed for clarity                      |

## 3. Entry Point Scripts

| Old Script        | New CLI Command            |
|-------------------|----------------------------|
| `asc_to_qsch.py`  | `cespy-asc-to-qsch`        |
| `raw_convert.py`  | `cespy-raw-convert`        |
| `run_server.py`   | `cespy-run-server`         |
| `sim_client.py`   | `cespy-sim-client`         |

## 4. Example Migration

### Old kupicelib Usage

```python
from kupicelib.editor import AscEditor
from kupicelib.sim.sim_runner import SimRunner

asc = AscEditor("circuit.asc")
runner = SimRunner(simulator=LTspice)
raw, log = runner.run_now(asc)
```

### New cespy Usage

```python
from cespy.editor.asc_editor import AscEditor
from cespy.simulators import LTSpiceSimulator
from cespy.sim import SimRunner

# Create simulator instance
sim = LTSpiceSimulator.create_from("C:/Program Files/LTspiceXVII/XVIIx64.exe")
# Edit schematic
asc = AscEditor("circuit.asc")
# Run simulation
runner = SimRunner(simulator=sim)
raw, log = runner.run_now(asc)
```

## 5. Notes and Best Practices

- All functionality from both original packages is preserved or enhanced.
- Review any custom scripts for direct imports and update paths accordingly.
- Update CI pipelines to install `cespy` instead of the older packages.

_For additional help, visit_ <https://github.com/RK0429/cespy#migration-guide>
