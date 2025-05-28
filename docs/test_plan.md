# cespy Test Plan

## Overview

This document outlines the comprehensive testing strategy for the cespy project, which merges functionality from kupicelib and kuPyLTSpice. The test plan ensures all features from both original packages are preserved and working correctly in the unified implementation.

## Testing Framework

- **Framework**: pytest
- **Test Structure**: tests/ directory with subdirectories mirroring source structure
- **Coverage Tool**: pytest-cov
- **Type Checking**: mypy with strict configuration
- **Style Checking**: black, flake8

## Test Categories

### 1. Unit Tests

#### 1.1 Editor Module Tests
- **test_asc_editor.py**
  - Test opening/reading LTSpice .asc files
  - Test modifying component values
  - Test adding/removing components
  - Test saving files without corruption
  - Test invalid file handling

- **test_qsch_editor.py**
  - Test opening/reading QSpice .qsch files
  - Test component manipulation
  - Test file format preservation
  - Test conversion between formats

- **test_spice_editor.py**
  - Test netlist parsing
  - Test parameter modification
  - Test subcircuit handling
  - Test directive parsing

#### 1.2 Raw Module Tests
- **test_raw_read.py**
  - Test binary raw file reading (LTSpice, NGSpice, QSpice, Xyce)
  - Test ASCII raw file reading
  - Test dialect auto-detection
  - Test large file handling
  - Test memory efficiency

- **test_raw_write.py**
  - Test writing raw files
  - Test format conversions
  - Test data integrity

- **test_raw_classes.py**
  - Test TraceRead class
  - Test RawRead class methods
  - Test data access patterns

#### 1.3 Simulator Module Tests
- **test_ltspice_simulator.py**
  - Test executable detection
  - Test command line switch validation
  - Test simulation execution
  - Test netlist generation
  - Test platform-specific behavior (Windows/Linux/macOS)

- **test_ngspice_simulator.py**
  - Test NGSpice specific features
  - Test command generation
  - Test output parsing

- **test_qspice_simulator.py**
  - Test QSpice integration
  - Test specific QSpice features

- **test_xyce_simulator.py**
  - Test Xyce integration
  - Test parallel simulation support

#### 1.4 Sim Module Tests
- **test_sim_runner.py**
  - Test simulation job management
  - Test parallel execution
  - Test callback mechanisms
  - Test timeout handling

- **test_sim_batch.py**
  - Test batch simulation execution
  - Test parameter sweeps
  - Test result collection

- **test_sim_stepping.py**
  - Test parameter stepping
  - Test sweep configurations
  - Test multi-dimensional sweeps

#### 1.5 Toolkit Tests
- **test_montecarlo.py**
  - Test Monte Carlo analysis
  - Test statistical distributions
  - Test result aggregation

- **test_worst_case.py**
  - Test worst-case analysis
  - Test tolerance calculations
  - Test corner cases

- **test_sensitivity_analysis.py**
  - Test sensitivity calculations
  - Test parameter ranking
  - Test visualization

#### 1.6 Utility Tests
- **test_detect_encoding.py**
  - Test encoding detection
  - Test various file encodings
  - Test edge cases

- **test_sweep_iterators.py**
  - Test sweep generation
  - Test linear/log/list sweeps
  - Test multi-parameter sweeps

### 2. Integration Tests

#### 2.1 End-to-End Simulation Tests
- **test_simulation_workflow.py**
  - Test complete simulation workflow:
    1. Open schematic
    2. Modify parameters
    3. Generate netlist
    4. Run simulation
    5. Parse results
    6. Analyze data

#### 2.2 Multi-Simulator Tests
- **test_simulator_compatibility.py**
  - Test same circuit across different simulators
  - Verify result consistency
  - Test simulator-specific features

#### 2.3 Client-Server Tests
- **test_client_server_integration.py**
  - Test server startup/shutdown
  - Test client-server communication
  - Test distributed simulation
  - Test error handling

#### 2.4 Analysis Pipeline Tests
- **test_analysis_pipeline.py**
  - Test Monte Carlo → Statistical Analysis
  - Test Worst-Case → Report Generation
  - Test combined analyses

### 3. Compatibility Tests

#### 3.1 Legacy API Tests
- **test_kupicelib_compatibility.py**
  - Test that kupicelib API still works
  - Test deprecated function warnings

- **test_kupyltspice_compatibility.py**
  - Test kuPyLTSpice API compatibility
  - Test migration paths

#### 3.2 File Format Tests
- **test_file_formats.py**
  - Test various LTSpice file versions
  - Test QSpice format variations
  - Test cross-simulator netlists

### 4. Performance Tests

#### 4.1 Benchmark Tests
- **test_performance.py**
  - Test large file parsing speed
  - Test simulation execution time
  - Test memory usage patterns
  - Compare with original packages

### 5. Platform Tests

#### 5.1 OS-Specific Tests
- **test_windows_specific.py**
  - Test Windows path handling
  - Test executable detection on Windows

- **test_linux_specific.py**
  - Test Wine integration
  - Test native Linux simulators

- **test_macos_specific.py**
  - Test macOS native LTSpice
  - Test Wine on macOS

## Test Data

### Required Test Files
Located in `tests/testfiles/`:
- Sample .asc files (various versions)
- Sample .qsch files
- Sample .net files
- Sample .raw files (binary and ASCII)
- Sample .log files
- Invalid/corrupted files for error testing

### Test Circuits
- Simple RC circuit
- Op-amp circuit
- Digital circuit
- Mixed-signal circuit
- Hierarchical design with subcircuits

## Test Execution

### Local Testing
```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=cespy --cov-report=html

# Run specific test category
poetry run pytest tests/unit/
poetry run pytest tests/integration/

# Run with verbose output
poetry run pytest -v

# Run specific test file
poetry run pytest tests/unit/test_asc_editor.py
```

### Type Checking
```bash
# Run mypy type checking
poetry run mypy src/

# Check specific module
poetry run mypy src/cespy/editor/
```

### Style Checking
```bash
# Check code formatting
poetry run black --check src/ tests/

# Run linter
poetry run flake8 src/ tests/
```

## Continuous Integration

### GitHub Actions Workflow
```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        python-version: ['3.10', '3.11', '3.12']
    
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    - name: Install dependencies
      run: |
        pip install poetry
        poetry install
    - name: Run tests
      run: |
        poetry run pytest --cov=cespy
    - name: Type check
      run: |
        poetry run mypy src/
    - name: Style check
      run: |
        poetry run black --check src/ tests/
        poetry run flake8 src/ tests/
```

## Test Coverage Goals

- **Overall Coverage**: Minimum 80%
- **Critical Modules**: Minimum 90%
  - raw_read.py
  - sim_runner.py
  - ltspice_simulator.py
- **New Code**: 100% coverage required

## Test Review Process

1. All new features must include tests
2. Tests must pass before PR merge
3. Coverage must not decrease
4. Performance benchmarks must not regress significantly

## Known Testing Challenges

1. **Simulator Availability**: Some tests require specific simulators installed
   - Solution: Mock simulator calls for unit tests, skip integration tests if simulator not available

2. **Platform Dependencies**: Some features are OS-specific
   - Solution: Use pytest markers to skip platform-specific tests

3. **Large Test Files**: Some raw files can be large
   - Solution: Generate test data programmatically when possible

4. **Timing Issues**: Simulation execution can vary
   - Solution: Use appropriate timeouts and retry logic

## Test Maintenance

- Review and update test plan quarterly
- Add tests for reported bugs before fixing
- Update test data as new file formats emerge
- Monitor test execution time and optimize slow tests