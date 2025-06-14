# Checklist for Merging kupicelib and kuPyLTSpice

## I. Project Initialization and High-Level Design

- [x] **A. Decide on Unified Package Name:**
  - [x] Evaluate options: `kupicelib`, `kuPyLTSpice`, a new name (e.g., `cespy`, `kuSpice`, `kupice`).
  - [x] Finalize the chosen name for the unified library. (Using `cespy`).
- [x] **B. Versioning Strategy:**
  - [x] If retaining an existing name (e.g., `kupicelib`), plan for a major version bump (e.g., to 2.0.0).
  - [x] If using a new name (e.g., `cespy`), plan for an initial version (e.g., 0.1.0).
- [x] **C. Choose Packaging Tool:**
  - [x] Confirm continuation with Poetry (as used by both packages).

## II. Proposed Unified Directory Structure Setup (using `cespy` as example name)

- [x] **A. Create Top-Level Package Directory:**
  - [x] Create `cespy/`.
  - [x] Create `cespy/__init__.py`.
    - [x] *Imported key simulator classes into `cespy/__init__.py` for user convenience.*
- [x] **B. Create `editor/` Subpackage:**
  - [x] Create `cespy/editor/` directory.
  - [x] Create `cespy/editor/__init__.py`.
  - [x] Create/Move `cespy/editor/asc_editor.py` (full implementation from `kupicelib`).
  - [x] Create/Move `cespy/editor/qsch_editor.py` (from `kupicelib`).
  - [x] Create/Move `cespy/editor/base_editor.py` (common editor base classes).
  - [x] Create/Move `cespy/editor/base_schematic.py` (common schematic abstractions).
  - [x] Create/Move `cespy/editor/asy_reader.py` (LTSpice symbol file reader, if present/needed).
  - [x] Create/Move `cespy/editor/ltspice_utils.py` (helper functions for LTSpice files).
  - [x] Create/Move `cespy/editor/spice_editor.py` (general SPICE netlist editor).
- [x] **C. Create `log/` Subpackage:**
  - [x] Create `cespy/log/` directory.
  - [x] Create `cespy/log/__init__.py`.
  - [x] Create/Move `cespy/log/logfile_data.py` (data structures for log info).
  - [x] Create/Move `cespy/log/ltsteps.py` (LTSpice `.log` step data parser).
  - [x] Create/Move `cespy/log/semi_dev_op_reader.py` (device operating point info reader).
  - [x] Create/Move `cespy/log/qspice_log_reader.py` (if needed for QSpice logs).
- [x] **D. Create `raw/` Subpackage:**
  - [x] Create `cespy/raw/` directory.
  - [x] Create `cespy/raw/__init__.py`.
  - [x] Create/Move `cespy/raw/raw_read.py` (full binary `.raw` reader from `kupicelib`).
  - [x] Create/Move `cespy/raw/raw_write.py` (for writing `.raw` files).
  - [x] Create/Move `cespy/raw/raw_classes.py` (data classes for waveform data).
  - [x] Create/Move `cespy/raw/raw_convert.py` (if exists, for raw data conversion).
- [x] **E. Create `sim/` Subpackage:**
  - [x] Create `cespy/sim/` directory.
  - [x] Create `cespy/sim/__init__.py`.
  - [x] Create/Move `cespy/sim/simulator.py` (generic simulation interface/base).
  - [x] Create/Move `cespy/sim/sim_runner.py` (local simulation job management).
  - [x] Create/Move `cespy/sim/sim_batch.py` (batch simulation, from `kuPyLTSpice`).
  - [x] Create/Move `cespy/sim/sim_stepping.py` (parameter sweep/step handling).
  - [x] Create/Move `cespy/sim/process_callback.py` (async process callback handling).
  - [x] Create/Move `cespy/sim/run_task.py` (if needed, or integrate into `sim_runner`).
  - [x] Create `cespy/sim/toolkit/` subpackage (ensure rename from "tookit").
    - [x] Create `cespy/sim/toolkit/__init__.py`.
    - [x] Create/Move `cespy/sim/toolkit/montecarlo.py`.
    - [x] Create/Move `cespy/sim/toolkit/worst_case.py`.
    - [x] Create/Move `cespy/sim/toolkit/fast_worst_case.py` (if distinct).
    - [x] Create/Move `cespy/sim/toolkit/failure_modes.py`.
    - [x] Create/Move `cespy/sim/toolkit/sensitivity_analysis.py`.
    - [x] Create/Move `cespy/sim/toolkit/tolerance_deviations.py`.
    - [x] Create/Move `cespy/sim/toolkit/sim_analysis.py`.
- [x] **F. Create `simulators/` Subpackage:**
  - [x] Create `cespy/simulators/` directory.
  - [x] Create `cespy/simulators/__init__.py`.
  - [x] Create/Move `cespy/simulators/ltspice_simulator.py`.
  - [x] Create/Move `cespy/simulators/ngspice_simulator.py`.
  - [x] Create/Move `cespy/simulators/qspice_simulator.py`.
  - [x] Create/Move `cespy/simulators/xyce_simulator.py`.
- [x] **G. Create `utils/` Subpackage:**
  - [x] Create `cespy/utils/` directory.
  - [x] Create `cespy/utils/__init__.py`.
  - [x] Create/Move `cespy/utils/detect_encoding.py`.
  - [x] Create/Move `cespy/utils/file_search.py`.
  - [x] Create/Move `cespy/utils/sweep_iterators.py`.
- [x] **H. Create `client_server/` Subpackage (if retaining remote execution):**
  - [x] Create `cespy/client_server/` directory.
  - [x] Create `cespy/client_server/__init__.py`.
  - [x] Create/Move `cespy/client_server/sim_server.py`.
  - [x] Create/Move `cespy/client_server/sim_client.py`.
  - [x] Create/Move `cespy/client_server/srv_sim_runner.py`.
- [x] **I. Plan for `scripts/` directory removal:**
  - [x] Identify all scripts in `kupicelib/scripts/`.
  - [x] Plan to refactor their functionality into functions within appropriate modules and expose via CLI entry points.

## III. Code Consolidation from `kupicelib` and `kuPyLTSpice`

- [x] **A. Prioritize `kupicelib` Implementations:**
  - [x] For all modules, retain the comprehensive implementations from `kupicelib`.
- [x] **B. Merge Overlapping Modules:**
  - [x] Identify modules present in both `kupicelib` and `kuPyLTSpice` (e.g., `asc_editor.py`, `spice_editor.py`, `ltsteps.py`, `raw_read.py`).
  - [x] Remove the thin wrapper versions from `kuPyLTSpice` (not copied to `cespy`).
  - [x] Review `kuPyLTSpice` wrapper versions for any additional logic or convenience functions not present in `kupicelib`.
  - [x] Integrate any such unique, valuable logic from `kuPyLTSpice` wrappers into the corresponding `kupicelib` (now UnifiedPackage) modules (none were needed).
- [x] **C. Integrate Unique `kuPyLTSpice` Functionality:**
  - [x] Identify features or modules unique to `kuPyLTSpice` (e.g., specific batch simulation orchestration like `sim_batch.py`, or specific `sim_runner.py` logic if different).
  - [x] Merge these unique features into the appropriate subpackages of the UnifiedPackage (e.g., into `cespy/sim/`).
- [x] **D. Unify Shared Utilities:**
  - [x] Consolidate all utility functions (e.g., encoding detection, sweep iterators) into the `cespy/utils/` subpackage.
  - [x] For utilities like `sweep_iterators.py` appearing in both, select the most comprehensive/correct version (kupicelib's), merging any distinct, valuable features from the other.
- [x] **E. Consolidate Simulator Interfaces:**
  - [x] Retain the multi-engine support from `kupicelib`'s `simulators/` directory.
  - [x] Review `kuPyLTSpice`'s LTSpice control logic.
  - [x] Merge any improvements or distinct, valuable features from `kuPyLTSpice`'s LTSpice control into `cespy/simulators/ltspice_simulator.py`.
- [x] **F. Client-Server Functionality:**
  - [x] If `client_server/` subpackage is retained, ensure all its existing functionality from `kupicelib` is preserved.
- [x] **G. Eliminate Redundant Files:**
  - [x] After merging logic, delete all duplicate or wrapper files originating from `kuPyLTSpice` that are now superseded.

## IV. Dependency Management

- [x] **A. Analyze `spicelib` Dependency (from `kuPyLTSpice`):**
  - [x] Audit `kuPyLTSpice` code for all imports and uses of `spicelib`.
  - [x] Determine if `kupicelib` (now UnifiedPackage) already provides equivalent functionality.
  - [x] **If `spicelib` functionality is needed and not covered:**
    - [x] Attempt to port the required functionality directly into the UnifiedPackage. (Not needed, functionality covered by kupicelib)
    - [x] *If porting is infeasible, make a conscious decision to keep `spicelib` as a dependency (preference was to remove).*
    - [x] *If incorporating code from `spicelib`, ensure GPL license compatibility is maintained. (N/A)*
  - [x] Aim to remove `spicelib` from the UnifiedPackage's dependencies.
- [x] **B. Consolidate All Other Dependencies:**
  - [x] List all dependencies from `kupicelib` (e.g., `numpy`, `scipy`, `matplotlib`, `pandas`, `psutil`, `keyboard`, `clipboard`).
  - [x] List any remaining, necessary dependencies from `kuPyLTSpice` (none; merged implementations cover everything).
  - [x] Create a final, unified list of dependencies for `pyproject.toml`.
- [x] **C. Prune Unnecessary Dependencies:**
  - [x] Review the consolidated list and remove any dependencies that are no longer needed after the merge (spicelib, kupicelib removed).

## V. Refactoring, Code Organization, and API Simplification

- [x] **A. Module and Naming Conventions:**
  - [x] Rename `sim/tookit/` to `sim/toolkit/`.
  - [x] Review all module and package names for clarity and consistency.
  - [x] Ensure class and function names clearly reflect their purpose.
- [x] **B. Code Cleanup:**
  - [x] Merge duplicate classes/functions where `kuPyLTSpice` extended or minimally wrapped `kupicelib` components.
  - [x] Remove any circular dependencies that might have existed between the two original packages.
  - [x] Replace all cross-package imports with internal imports within the UnifiedPackage.
  - [x] Identify and remove dead or legacy code sections no longer needed after merging.
- [x] **C. Improve Code Quality:**
  - [x] Ensure consistent and correct type hints across the entire codebase.
    - [x] Reconcile function signatures if they differed.
    - [x] Add missing type hints, especially from `kuPyLTSpice` code.
  - [x] Apply a consistent coding style (e.g., using a formatter like Black, Flake8 for linting).
  - [x] Improve internal code documentation: add or update docstrings for modules, classes, and functions.
- [x] **D. Simplify Simulation API:**
  - [x] Evaluate the current user workflow for running simulations from both original packages.
  - [x] Design and implement a clear, high-level API for running simulations in the UnifiedPackage.
    - [x] *Consider providing a top-level class (e.g., `LTSpiceRunner`) or function (e.g., `simulate(netlist_path, ...)`).*
  - [x] Ensure simulator engine choices (LTSpice, NGSpice, etc.) are presented coherently to the user (e.g., via a parameter, or by instantiating specific simulator classes).
- [x] **E. Retain All Major Functionality:**
  - [x] Systematically verify that all capabilities from both `kupicelib` and `kuPyLTSpice` are present in the unified tool:
    - [x] LTSpice Automation (headless runs, data retrieval).
    - [x] Schematic Editing (`.asc`, `.qsch`).
    - [x] Data Analysis (plotting, Monte Carlo, worst-case analysis tools).
    - [x] Multi-Engine Support (NGSpice, Qspice, Xyce, etc.).
    - [x] Client-Server simulation mode.
- [x] **F. Performance Considerations:**
  - [x] During refactoring, identify any potential performance bottlenecks (e.g., large file I/O, heavy computations).
  - [x] Note opportunities for optimization, even if not implemented immediately.

## VI. Documentation and Examples

- [x] **A. Unified README:**
  - [x] Combine the `README.md` files from `kupicelib` and `kuPyLTSpice`.
  - [x] The new README should:
    - [x] Introduce the UnifiedPackage.
    - [x] List its key features (covering combined capabilities).
    - [x] Provide basic installation and usage examples.
    - [x] Clearly state the license (GPL-3.0).
- [x] **B. API Documentation:**
  - [x] Ensure all public APIs (classes, functions, methods) have clear docstrings.
  - [x] Update all documentation to reflect any API changes due to refactoring or renaming.
- [x] **C. User Guide / Reference Manual (Recommended):**
  - [x] Consider creating a more detailed User Guide or reference manual.
  - [x] Topics could include: setup, circuit modification, running sweeps, result parsing, analysis tools.
- [x] **D. Migration Guide (Optional but Recommended):**
  - [x] Prepare a short guide for users transitioning from `kupicelib` or `kuPyLTSpice`.
  - [x] Example: "If you used `kuPyLTSpice.LTSpiceSimulation(...)`, now use `cespy.simulators.LTSpiceSimulator(...)`."

## VII. Unified Packaging and Build Configuration

- [x] **A. Configure `pyproject.toml` (assuming Poetry):**
  - [x] **Project Metadata:**
    - [x] Set `name` to the chosen UnifiedPackage name.
    - [x] Set `version` (e.g., `2.0.0` or `0.1.0`).
    - [x] Write a comprehensive `description`.
    - [x] List `authors`.
    - [x] Specify `license = "GPL-3.0"`.
    - [x] Update `homepage` and `repository` URLs to the unified project's GitHub repository.
  - [x] **Dependencies:**
    - [x] List all consolidated runtime dependencies with appropriate version specifiers (e.g., `numpy`, `scipy`, `pandas`, `matplotlib`, `python = ">=3.10"`).
    - [x] List all development dependencies (e.g., `pytest`, linters, formatters).
  - [x] **Entry Points (Console Scripts):**
    - [x] For each script from `kupicelib/scripts/` (and any relevant `kuPyLTSpice` tools):
      - [x] Refactor the script's core logic into a callable function within an appropriate module of the UnifiedPackage.
      - [x] Define a console script entry point in `pyproject.toml` under `[tool.poetry.scripts]`. Examples:
        - [x] `cespy-asc-to-qsch = cespy.editor.asc_editor:main_function_for_conversion`
        - [x] `cespy-run-server = cespy.client_server.sim_server:main_server_function`
        - [x] `cespy-rawplot = cespy.raw.raw_plot:main_plot_function` (if `raw_plot.py` exists and is to be exposed)
  - [x] **Python Version Compatibility:**
    - [x] Ensure `python` version constraint is correctly specified (e.g., `>=3.10`).
  - [x] **Package Data (Non-code files):**
    - [x] Identify any necessary non-code files (e.g., `asc_to_qsch_data.xml`).
    - [x] Move these files to an appropriate location within the package (e.g., `cespy/editor/data/asc_to_qsch_data.xml`).
    - [x] Ensure these files are included in the build (e.g., using `include` in `pyproject.toml` or `MANIFEST.in` if necessary).
  - [x] **Typing Information:**
    - [x] Ensure a `py.typed` marker file is present in the top-level package directory (`cespy/py.typed`) if providing type information.
- [x] **B. Build System:**
  - [x] Ensure the chosen build system (Poetry) is correctly configured for the unified project.

## VIII. Comprehensive Testing

- [x] **A. Develop a Test Plan:**
  - [x] Document a test plan covering all major features from both original packages.
- [x] **B. Write/Update Unit Tests:**
  - [x] Write unit tests for critical modules (e.g., raw file parsing, schematic editing logic, sweep iterators, utility functions).
  - [x] Ensure high test coverage for core functionality.
- [x] **C. Write/Update Integration Tests:**
  - [x] **Circuit Editing:** Test opening, modifying, and saving `.asc` and `.qsch` files.
  - [x] **Simulation Execution (LTSpice):**
    - [x] Test direct (local) execution of LTSpice simulations (e.g., AC analysis).
    - [x] Test server-based execution (start server, submit job via client, get results).
  - [x] **Simulation Execution (Other Engines):** Test NGSpice, QSpice, Xyce execution with simple netlists.
  - [x] **Result Parsing:**
    - [x] Verify parsing of `.raw` files (waveform data accuracy).
    - [x] Verify parsing of `.log` files (step data, operating point info).
  - [x] **Analysis Tools:** Test Monte Carlo, worst-case analysis functions with known circuits.
  - [x] **CLI Tools:** Test each defined console script entry point with sample inputs.
- [x] **D. Test Automation:**
  - [x] Automate all unit and integration tests using a framework like `pytest`.
- [x] **E. Continuous Integration (CI):**
  - [x] Set up or update a CI pipeline (e.g., GitHub Actions).
  - [x] Configure CI to run tests on every commit/pull request.
  - [x] Configure CI to build wheels/sdist.
- [x] **F. Functionality Preservation Testing:**
  - [x] If any test reveals missing functionality that existed in either original package, address it by adding wrappers or adjusting the API.
  - [x] Verify that all command-line tools from the old `scripts/` directory work as intended via their new entry points.
- [x] **G. Performance and Regression Testing:**
  - [x] Test on multiple target platforms (Windows for LTSpice/QSpice; Linux/macOS for NGSpice/Xyce).
  - [x] Monitor memory usage and execution time for key operations (e.g., reading large `.raw` files). Identify and address regressions.
  - [x] Validate that path configurations for finding simulator executables work correctly or have clear configuration options.

## IX. User Migration Strategy and Repository Transition

- [x] **A. GitHub Repository Merge/Transition:**
  - [x] Choose a strategy for the GitHub repositories:
    - [x] Option 1: Designate one existing repository (e.g., `kupicelib`'s) as the primary and merge `kuPyLTSpice` code into it.
    - [x] Option 2: Create a new repository for the UnifiedPackage and migrate code from both.
  - [x] If migrating history, use `git subtree` or history import tools (optional, but good for record-keeping).
  - [x] Update the chosen repository's README to reflect the unified project.
  - [x] Update CI workflows, issue trackers, and other repository settings.
- [ ] **B. `kuPyLTSpice` User Migration:**
  - [ ] In the `kuPyLTSpice` repository: Update README to state it has been merged into the UnifiedPackage, providing the new name and version, and link to the new repository/PyPI page.
  - [ ] On PyPI for `kuPyLTSpice`:
    - [ ] Update the project description similarly.
    - [ ] *Optional (Recommended): Publish a final `kuPyLTSpice` version (e.g., 1.0.1) that:*
      - [ ] Adds the UnifiedPackage as a dependency.
      - [ ] Imports from the UnifiedPackage and re-exports `kuPyLTSpice`'s old API.
      - [ ] Issues a `DeprecationWarning` when `kuPyLTSpice` modules are imported, advising users to switch.
- [ ] **C. `kupicelib` User Migration (if name changes or significant API restructuring):**
  - [ ] In the `kupicelib` repository (if it's not the chosen base or is also being deprecated): Update README similar to `kuPyLTSpice`.
  - [ ] On PyPI for `kupicelib`: Update project description if the name changes or it's superseded.
  - [ ] If `kupicelib` is the base name but APIs change, clearly document these changes in the new version's release notes and documentation (see Migration Guide task).
- [ ] **D. Version Number Signaling:**
  - [ ] Ensure the unified release uses a version number that clearly signals potentially breaking changes (e.g., `2.0.0` if `kupicelib` is base, or `0.1.0`/`1.0.0` for a new name).
- [ ] **E. Redirect Old Repositories:**
  - [ ] Ensure the descriptions of any old/deprecated GitHub repositories clearly point to the new unified repository.

## X. Release Roadmap Execution

- [ ] **A. Pre-Release Final Checks:**
  - [ ] Confirm all planned tests (unit, integration, manual) are passing.
  - [ ] Build the package locally (`poetry build` or `python -m build`).
  - [ ] Install the locally built wheel/sdist in a fresh virtual environment.
  - [ ] Perform a smoke test by running a few key examples/commands to ensure everything is included and works.
  - [ ] Finalize the `README.md` and any other core documentation (release notes, migration guide if created).
  - [ ] Update any badges (CI status, PyPI version) in the README.
- [ ] **B. Publish to PyPI:**
  - [ ] Tag the release in Git.
  - [ ] Publish the unified package to PyPI (e.g., `poetry publish`).
  - [ ] Verify the PyPI release:
    - [ ] Check the PyPI project page for correct metadata.
    - [ ] Install the package from PyPI (`pip install UnifiedPackageName`) in a fresh environment.
    - [ ] Run a quick functionality test with the PyPI-installed version.
- [ ] **C. Deprecation/Redirection of Old Packages (if not done pre-release):**
  - [ ] Execute the plan for `kuPyLTSpice` on PyPI (final release with warning or description update).
  - [ ] Update `kupicelib` on PyPI if necessary.
  - [ ] Consider yanking old/problematic releases from PyPI if appropriate, or leave them with clear deprecation notes.
- [ ] **D. Post-Release Monitoring:**
  - [ ] Monitor issue trackers (GitHub, etc.) and user feedback channels for any bugs or problems with the new release.
  - [ ] Prepare to issue patch releases quickly if critical issues are found.
  - [ ] Close out any redundant issue pages or pull requests in the old repositories, directing users to the new repository.
  - [ ] Officially switch all future development efforts to the unified codebase.

## XI. Optional Additional Improvements (Post-Initial Merge)

- [ ] **A. Enhanced Documentation Site:**
  - [ ] Set up a dedicated documentation website (e.g., using Sphinx, MkDocs, ReadTheDocs).
  - [ ] Include tutorials, an API reference, and advanced examples.
- [ ] **B. Example Suite:**
  - [ ] Create an `examples/` directory in the repository.
  - [ ] Add example circuits and Python scripts demonstrating various use cases.
- [ ] **C. Unified Command-Line Interface (CLI):**
  - [ ] Design and implement a more comprehensive CLI (e.g., `cespy <subcommand>`) using a framework like `click` or `argparse`.
  - [ ] Subcommands could include `simulate`, `convert`, `analyze`, etc.
- [ ] **D. Higher-Level API Abstraction:**
  - [ ] Consider introducing a higher-level API class (e.g., `CircuitSimulator`) to simplify common tasks and engine selection.
- [ ] **E. Scalability Enhancements:**
  - [ ] Investigate and implement features for scalability if needed (e.g., parallel simulation execution, more efficient large data handling).
- [ ] **F. Community and Contribution:**
  - [ ] Establish clear contribution guidelines (`CONTRIBUTING.md`).
  - [ ] Foster a welcoming environment for potential contributors.
