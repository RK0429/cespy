# Pylint Fixes Summary

This document summarizes the fixes made to address pylint issues in the cespy module.

## Issues Fixed

### 1. R0913/R0917 (too-many-arguments)
- **File**: `src/cespy/sim/sim_runner.py`
- **Solution**: Created two dataclasses to group related parameters:
  - `SimRunnerConfig`: Groups simulator configuration parameters
  - `RunConfig`: Groups run method parameters
- **Status**: Partial fix - The classes are available for users who want cleaner APIs, but the original method signatures remain for backward compatibility

### 2. C0116 (missing-function-docstring)
- **Files**: Multiple files in `src/cespy/sim/toolkit/`
- **Solution**: Added comprehensive docstrings to all methods missing documentation
- **Status**: Fixed

### 3. R1705/R1704 (no-else-return, redefined-argument)
- **Files**: `worst_case.py`, `sensitivity_analysis.py`, `spice_editor.py`
- **Solution**: 
  - Removed unnecessary `else` blocks after `return` statements
  - Fixed variable name conflicts (e.g., `ref` -> `ref_comp`)
- **Status**: Fixed

### 4. C0209 (consider-using-f-string)
- **Files**: `sensitivity_analysis.py`, `tolerance_deviations.py`
- **Solution**: Converted old-style string formatting to f-strings
- **Status**: Fixed

### 5. R1714 (consider-using-in)
- **File**: `sensitivity_analysis.py`
- **Solution**: Changed `or` comparisons to use `in` operator
- **Status**: Fixed

### 6. C0200 (consider-using-enumerate)
- **File**: `spice_editor.py`
- **Solution**: Replaced `for i in range(len(line))` with `for i, ch in enumerate(line)`
- **Status**: Fixed

### 7. W0101 (unreachable-code)
- **File**: `spice_editor.py`
- **Solution**: Removed unreachable code after `return` statements
- **Status**: Fixed

## Remaining Issues

### Too Many Arguments (R0913, R0917)
Some methods still have many arguments due to the nature of the simulation configuration. The dataclasses provide an alternative API, but the original signatures are maintained for backward compatibility. Users can now choose between:

```python
# Traditional approach
runner = SimRunner(simulator=LTspice, parallel_sims=4, timeout=600)

# New approach with config object
config = SimRunnerConfig(simulator=LTspice, parallel_sims=4, timeout=600)
runner = SimRunner(config=config)
```

### Recommendations
1. Consider deprecating the old method signatures in a future version
2. Update documentation to promote the use of config objects
3. Add examples showing both approaches in the documentation