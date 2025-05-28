# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

cespy is a Python toolkit for automating SPICE circuit simulators (LTSpice, NGSpice, QSpice, Xyce). It provides a unified API for schematic editing, simulation execution, result parsing, and advanced circuit analysis.

## Development Commands

```bash
# Install dependencies
poetry install

# Run code formatter
poetry run black src/ tests/

# Run linter
poetry run flake8 src/ tests/

# Run type checker
poetry run mypy src/

# Run tests
poetry run pytest

# Build documentation
cd docs && make html

# Build package
poetry build
```

## Architecture Overview

The codebase is organized into distinct modules under `src/cespy/`:

- **editor/**: Handles schematic and netlist file manipulation
  - `asc_editor.py`: LTSpice schematic editing
  - `qsch_editor.py`: QSpice schematic editing
  - `spice_editor.py`: SPICE netlist editing
  - `asc_to_qsch.py`: Conversion between formats

- **simulators/**: Simulator-specific implementations
  - Each simulator (LTSpice, NGSpice, QSpice, Xyce) has its own driver class
  - All inherit from a common `Simulator` base class

- **sim/**: Simulation orchestration and analysis
  - `sim_runner.py`: Core simulation execution logic
  - `sim_batch.py`: Batch simulation capabilities
  - `toolkit/`: Advanced analysis tools (Monte Carlo, worst-case, sensitivity)

- **raw/**: Binary waveform data handling
  - Reads and writes SPICE raw format files
  - Supports conversion between formats

- **client_server/**: Distributed simulation support
  - XML-RPC based architecture for remote simulations
  - Server manages simulation jobs, clients submit and retrieve results

## Key Design Patterns

1. **Simulator Abstraction**: All simulators implement a common interface, allowing users to switch between simulators with minimal code changes.

2. **Editor Pattern**: Each file format has a dedicated editor class that handles parsing, modification, and serialization.

3. **Analysis Toolkit**: High-level analysis tools are built on top of the core simulation capabilities, providing Monte Carlo, worst-case, and sensitivity analysis out of the box.

4. **Async Process Management**: Simulations run as managed subprocesses with proper output capture and timeout handling.

## Entry Points

The package provides several command-line tools:

- `cespy-asc-to-qsch`: Convert LTSpice schematics to QSpice format
- `cespy-run-server`: Start a simulation server for distributed computing
- `cespy-raw-convert`: Convert between different raw file formats
- `cespy-sim-client`: Connect to a remote simulation server

## Important Notes

- This is a merged project combining kupicelib and kuPyLTSpice functionality
- The project uses Poetry for dependency management - always use `poetry run` or activate the virtual environment
- Type hints are used throughout - run mypy to check type consistency
- The codebase follows black formatting standards (88 character line length)
