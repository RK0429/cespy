# Migration Guide

This guide helps users migrate from kupicelib or kuPyLTSpice to the unified cespy package.

## For kupicelib Users

The migration from kupicelib to cespy is straightforward as most APIs remain unchanged. The primary change is updating import statements.

### Import Changes

```python
# Old kupicelib imports
from kupicelib.editor import SpiceEditor, AscEditor, QschEditor
from kupicelib.sim import SimRunner
from kupicelib.simulators import LTspice, NGspiceSimulator
from kupicelib.raw import RawRead, RawWrite

# New cespy imports
from cespy.editor import SpiceEditor, AscEditor, QschEditor
from cespy.sim import SimRunner
from cespy.simulators import LTspice, NGspiceSimulator
from cespy.raw import RawRead, RawWrite
```

### Command-Line Tools

The command-line tools have been renamed with the `cespy-` prefix:

| Old Command | New Command |
|-------------|-------------|
| `asc_to_qsch` | `cespy-asc-to-qsch` |
| `run_server` | `cespy-run-server` |
| `ltsteps` | `cespy-ltsteps` |
| `histogram` | `cespy-histogram` |
| `rawplot` | `cespy-rawplot` |

### No API Changes

All functionality remains the same:
- Component manipulation methods
- Simulation execution
- Result parsing
- Analysis toolkit functions

## For kuPyLTSpice Users

Users migrating from kuPyLTSpice will find that cespy provides all the same functionality with a cleaner, more comprehensive API.

### Simple Migration - Using the High-Level API

The easiest migration path is to use cespy's new high-level `simulate()` function:

```python
# Old kuPyLTSpice approach
from kuPyLTSpice import LTSpiceSimulation
sim = LTSpiceSimulation("circuit.asc")
sim.run()
results = sim.get_results()

# New cespy approach (simple)
from cespy import simulate
results = simulate("circuit.asc", engine="ltspice")
```

### Detailed Migration - Direct Simulator Usage

For more control, use the simulator classes directly:

```python
# Old kuPyLTSpice
from kuPyLTSpice import LTspice
from kuPyLTSpice.sim import SimRunner

ltspice = LTspice(ltspice_exe="path/to/ltspice")
runner = SimRunner(simulator=ltspice)
runner.run("circuit.asc")

# New cespy
from cespy import LTspice
from cespy.sim import SimRunner

ltspice = LTspice(spice_exe="path/to/ltspice")  # Note: parameter name changed
runner = SimRunner(simulator=ltspice)
runner.run("circuit.asc")
```

### Key Differences

1. **No spicelib dependency**: cespy has integrated all necessary functionality
2. **Unified namespace**: All imports come from `cespy` instead of `kuPyLTSpice`
3. **More simulators**: cespy supports NGSpice, QSpice, and Xyce in addition to LTSpice
4. **Enhanced features**: cespy includes all kupicelib features like QSpice support and advanced analysis tools

### Analysis Tools

The analysis tools have been enhanced but maintain backward compatibility:

```python
# Old kuPyLTSpice
from kuPyLTSpice.sim.tookit import Montecarlo  # Note the typo "tookit"

# New cespy
from cespy.sim.toolkit import Montecarlo  # Fixed: "toolkit" is correctly spelled
```

## Common Migration Tasks

### 1. Updating Requirements

Update your `requirements.txt` or `pyproject.toml`:

```bash
# Remove old packages
pip uninstall kupicelib kuPyLTSpice spicelib

# Install cespy
pip install cespy
```

### 2. Search and Replace

In your codebase, perform these replacements:
- `from kupicelib` → `from cespy`
- `import kupicelib` → `import cespy`
- `from kuPyLTSpice` → `from cespy`
- `import kuPyLTSpice` → `import cespy`

### 3. Parameter Name Updates

Some parameter names have been standardized:
- `ltspice_exe` → `spice_exe` (in simulator constructors)
- `tookit` → `toolkit` (typo fixed in module name)

## Getting Help

If you encounter any issues during migration:

1. Check the [README](../README.md) for updated examples
2. Review the API documentation in the source code
3. Open an issue on the [GitHub repository](https://github.com/RK0429/cespy)

## Benefits of Migration

By migrating to cespy, you gain:
- Access to multiple SPICE simulators (not just LTSpice)
- QSpice schematic editing support
- Enhanced analysis toolkit with more options
- Active maintenance and updates
- Cleaner, more consistent API
- Better performance optimizations