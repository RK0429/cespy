# Plan to Merge **kupicelib** and **kuPyLTSpice** into a Unified Python Package

## Background: Current Architecture of **kupicelib** and **kuPyLTSpice**

**kupicelib** (v1.0.1) and **kuPyLTSpice** (v1.0.0) are currently two separate Python packages on PyPI. KuPyLTSpice is essentially a wrapper that builds on kupicelib, meaning kuPyLTSpice depends on kupicelib (>=1.0.0) for core functionality. Key points about their current structure and relationship:

* **kupicelib** is a comprehensive library for automating SPICE simulations. It provides modules for editing circuit schematic files, running simulations, and parsing simulation outputs. Notably, kupicelib supports multiple SPICE engines – it contains simulator interfaces for LTSpice, NGSpice, QSpice, and Xyce. Its internal structure includes subpackages:

  * `editor/` – classes to read/write LTSpice `.asc` schematics, QSpice `.qsch` files, and general SPICE netlist editing (e.g. `asc_editor.py`, `spice_editor.py`).
  * `log/` – tools to parse LTSpice log files (e.g. extracting step data, device operating points) and QSpice logs.
  * `raw/` – functionality to read and write LTSpice binary waveform `.raw` files (e.g. `raw_read.py`, `raw_write.py`).
  * `sim/` – simulation orchestration (e.g. `sim_runner.py` to run simulations, `sim_stepping.py` for sweeps, `simulator.py` for generic simulator logic) plus a `tookit` (toolkit) of analysis utilities (Monte Carlo, worst-case analysis, etc.).
  * `simulators/` – engine-specific simulator drivers for **LTSpice**, **NGSpice**, **QSpice**, **Xyce**, etc. (each in its own module).
  * `client_server/` – an optional architecture to run simulations in a separate process or server (contains `sim_server.py`, `sim_client.py`).
  * `scripts/` – standalone helper scripts (e.g. converting `.asc` to `.qsch`, plotting waveforms, running a simulation server, etc.) for command-line usage.

* **kuPyLTSpice** is a separate package that was originally a modified fork of the PyLTSpice project. It acts as a high-level interface to LTSpice, and currently **depends on kupicelib** for much of its functionality. The kuPyLTSpice package structure mirrors many of kupicelib’s modules but in a lighter form:

  * It has corresponding subpackages like `editor/`, `log/`, `raw/`, `sim/`, etc., but many of these modules are thin wrappers. For example, kuPyLTSpice includes an `asc_editor.py` (\~1 KB) and `spice_editor.py` (\~2.7 KB) in its `editor` folder, whereas kupicelib’s `asc_editor.py` is \~39 KB (full implementation). This indicates kuPyLTSpice’s editors likely delegate to kupicelib’s implementations.
  * Similar duplication exists for log parsing (`ltsteps.py` in kuPyLTSpice is \~0.8 KB vs \~28 KB in kupicelib) and raw file handling (`raw_read.py` \~9 KB vs \~50 KB in kupicelib). KuPyLTSpice essentially provides an API layer (and perhaps some additional convenience functions or CLI hooks) on top of kupicelib’s core engine.
  * KuPyLTSpice also requires the external **spicelib** package (>=1.4.1), which was part of the original PyLTSpice toolchain. Some functionality might still rely on spicelib (for example, netlist parsing or data structures) that was not fully migrated into kupicelib.

**Drawbacks of the current split architecture:**

* *Duplication & Maintenance Overhead:* Many features exist in both packages (one as the implementation in kupicelib, and again as a wrapper in kuPyLTSpice). This duplication makes the architecture more complex and harder to maintain. Updates to core logic in kupicelib may require synchronized changes in kuPyLTSpice.
* *Installation Complexity:* Users must install two packages (kuPyLTSpice and its dependency kupicelib, and implicitly spicelib). This increases friction and potential version compatibility issues.
* *Inconsistent Namespace:* Functionality is split across two namespaces (`kupicelib` vs `kuPyLTSpice`), which can be confusing. Unifying them would provide a single coherent API surface for the simulation tool.
* *Architecture Complexity:* The presence of a separate wrapper suggests an extra layer that might be simplified by merging. A unified package can remove unnecessary abstraction layers and make the library’s structure more straightforward.

**Goals for the Merger:**

1. **Unified Tool:** Combine kupicelib and kuPyLTSpice into one coherent Python package that provides all simulation capabilities (LTSpice automation, schematic editing, data parsing, etc.) in a single installable library.
2. **Simplified Architecture:** Eliminate redundant code and layers. The new structure should be cleaner, with each component present only once and a clear division of responsibilities (e.g., one module for schematic editing, one for running simulations, etc.).
3. **Shared Utilities:** Any common utilities or helper components currently split between the two projects should be merged, so everything is available in one place. This includes things like file encoding detectors, iteration utilities for sweeps, etc., which both packages have variants of.
4. **Maintainability & Readability:** Improve code organization for easier navigation and future development. This may involve refactoring modules, renaming for clarity, and removing legacy cruft from the PyLTSpice era. Since backward compatibility isn’t strictly required, we have freedom to restructure the API for clarity (while preserving **functionality**).
5. **Single Packaging & Distribution:** The end result should be one PyPI package (pip-installable) containing all features, with a single version number and release process (preferably with a semantic version bump to indicate the major change).

## Proposed Unified Package Design

**Package Name and Repository:** Decide on a name for the unified library. We can either **retain one of the existing names** (e.g. keep `kupicelib` as the base name since it’s already at v1.0.1, or use `kuPyLTSpice` if we want to emphasize LTSpice compatibility), or **choose a new name** to represent the merged tool (for example, something like `kuSpice` or `kupice` if desired). The choice may depend on branding and scope: if the unified package will support multiple SPICE engines (not just LTSpice), a more general name (like **kupicelib** or a new name) is appropriate, whereas `kuPyLTSpice` is LTSpice-specific by name. For this plan, we’ll assume **kupicelib** will be the base for merging (and likely version it to 2.0.0 to indicate the major update).

**Proposed Directory Structure:** Below is a possible layout for the merged package (using `cespy` (named from “Spice” → “ceSpi” → “cespy”) as the package name for illustration). This structure unifies both codebases and organizes modules by functionality:

```text
cespy/                  - Top-level package for the unified library
    __init__.py             - Initialize package (could import key classes for convenience)
    editor/                 - Schematic and netlist editing utilities
        __init__.py
        asc_editor.py       - (Merge: full LTSpice .asc editor from kupicelib)
        qsch_editor.py      - (QSpice .qsch editor)
        base_editor.py      - (common editor base classes)
        base_schematic.py   - (common schematic abstractions)
        asy_reader.py       - (LTSpice symbol file reader, if present)
        ltspice_utils.py    - (helper functions for LTSpice files)
        spice_editor.py     - (possibly general SPICE netlist editor)
    log/                    - Simulation log parsing
        __init__.py
        logfile_data.py     - (data structures for log file info)
        ltsteps.py          - (parse LTSpice `.log` for step data)
        semi_dev_op_reader.py - (read device operating point info)
        qspice_log_reader.py  - (if needed for QSpice logs)
    raw/                    - Raw waveform file handling
        __init__.py
        raw_read.py         - (full binary .raw reader from kupicelib)
        raw_write.py        - (writing .raw files)
        raw_classes.py      - (data classes for waveform data)
        raw_convert.py      - (if exists, utility to convert raw data)
    sim/                    - Simulation control and orchestration
        __init__.py
        simulator.py        - (generic simulation interface/abstract base)
        sim_runner.py       - (job management, runs simulations locally)
        sim_batch.py        - (batch running of simulations, from kuPyLTSpice)
        sim_stepping.py     - (handles parameter sweeps/steps)
        process_callback.py - (callback handling for async processes)
        run_task.py         - (if needed: maybe integrated into sim_runner)
        # Possibly integrate sim_runner and run_task if overlapping.
        toolkit/            - (rename from "tookit" to "toolkit")
            __init__.py
            montecarlo.py   - (Monte Carlo analysis utilities)
            worst_case.py   - (Worst-case analysis)
            fast_worst_case.py  - (if distinct method for worst-case)
            failure_modes.py    - (failure modes analysis)
            sensitivity_analysis.py (quick sensitivity analysis)
            tolerance_deviations.py (tolerance analysis utilities)
            sim_analysis.py     - (common post-simulation analysis routines)
    simulators/             - Interfaces to specific SPICE simulator programs
        __init__.py
        ltspice_simulator.py    - (control LTSpice application for sims)
        ngspice_simulator.py    - (control NGSpice)
        qspice_simulator.py     - (control QSpice)
        xyce_simulator.py       - (control Xyce)
        # Possibly add others in future using similar pattern.
    utils/                  - Shared utility modules
        __init__.py
        detect_encoding.py  - (text file encoding detection util)
        file_search.py      - (to locate SPICE executables or files)
        sweep_iterators.py  - (iterator helpers for param sweeps)
    client_server/          - (Optional: retain this if remote execution is needed)
        __init__.py
        sim_server.py       - (server to run simulations, from kupicelib)
        sim_client.py       - (client to send simulation jobs, from kupicelib)
        srv_sim_runner.py   - (server-side sim runner logic)
    # Remove 'scripts' as a code package; instead expose their functionality via CLI entry points.
```

**Consolidation of Code:**

* All key modules from **kupicelib** will be retained (since kupicelib contains the full implementations). The corresponding **kuPyLTSpice** modules that overlap will either be merged or dropped:

  * For example, kuPyLTSpice’s thin `editor/asc_editor.py` wrapper can be removed, and the unified package will use the comprehensive `editor/asc_editor.py` from kupicelib. If the kuPyLTSpice wrapper added any additional logic or convenience functions, those should be merged into the main implementation or provided elsewhere in the new API.
  * Any functionality unique to kuPyLTSpice (not already in kupicelib) must be integrated. For instance, kuPyLTSpice might have provided certain convenience classes or batch simulation orchestration (e.g., `sim_batch.py`, `sim_runner.py` in kuPyLTSpice) – we will incorporate those into the `sim/` module of the unified package. The goal is **no loss of major features** from either project.
  * Redundant files will be eliminated. We will avoid having two versions of the same utility. This means dropping the smaller duplicate modules from kuPyLTSpice and keeping the robust ones from kupicelib, merging differences as needed.

* **Shared Utilities:** Both packages have a `utils` (or similar) module for things like encoding detection, sweep iteration, etc. These will be unified under `cespy.utils`. For example, the `sweep_iterators.py` appears in both (with identical or similar purpose); we will maintain one version (likely the one from kupicelib unless kuPyLTSpice’s differs significantly).

* **Engine Interfaces:** We will keep the multiple simulator support from kupicelib’s `simulators/` intact (this is a strength of kupicelib). The LTSpice control logic in kuPyLTSpice (which presumably was adapted from PyLTSpice) can be merged with kupicelib’s `ltspice_simulator.py` if there are improvements or differences. The unified package will thus support all the simulators kupicelib supported, under one roof.

* **Client-Server Mode:** If maintaining the remote simulation server capability is desired (it likely is, since kupicelib includes it), we keep the `client_server` subpackage. We might simplify it if possible (for example, ensure that the normal `sim_runner` can optionally run jobs via the server, rather than having entirely separate code paths), but such integration can be an enhancement. At minimum, the existing server/client functionality will be preserved in the unified package (so users can run a `sim_server` and submit simulation tasks remotely or in parallel).

* **External Dependency (spicelib):** Part of simplifying the architecture is evaluating the need for **spicelib**. Since kupicelib was described as a “modified version” of an existing library and does not list spicelib as a dependency, it likely contains replacements for spicelib’s functionality. The unified package should ideally **remove the spicelib dependency** entirely, using our own integrated code. We will:

  * Audit any references to `spicelib` in the kuPyLTSpice code being merged. If, for example, kuPyLTSpice imports something from spicelib (perhaps for plotting or netlist handling), we will port that functionality into the new package. It might be that kupicelib already covers these needs (given its comprehensive feature set).
  * If some niche feature is only available in spicelib and not easily replicated, we have the option to keep spicelib as a dependency. However, the preference is to have a self-contained tool. Since both kupicelib and kuPyLTSpice are GPL-licensed, incorporating code from spicelib (which was part of PyLTSpice) is legally permissible under GPL as well, if needed.
  * Ultimately, the unified package’s dependency list will likely be the union of kupicelib’s and any truly needed extra ones from kuPyLTSpice (which aside from spicelib, are mostly standard scientific packages like NumPy, SciPy, Pandas, etc., all of which kupicelib already uses). Redundant or unnecessary dependencies will be pruned.

* **Choice of Packaging Tool:** Both original packages use **poetry** (indicated by the wheel metadata generated by poetry-core). We can continue to use a **pyproject.toml** with Poetry (or switch to a simpler setup if desired) for the unified package. The packaging configuration will define a single project (name, version, authors, license, etc.) and include all modules. Key points for the unified packaging:

  * Update the project metadata: e.g., name (if changing), version (set to 2.0.0 to mark the merge), description (combine highlights of both projects: mention that it automates LTSpice/Spice simulations, combining capabilities of both prior packages), URLs (new repo or the chosen base repo).
  * Consolidate the **dependency requirements**. Ensure the `pyproject.toml` (or `setup.py`) lists all needed libraries:

    * From kupicelib: `numpy`, `scipy`, `matplotlib`, `pandas` (and `pandas-stubs` for typing), `psutil`, `keyboard`, `clipboard`, etc..
    * From kuPyLTSpice: mostly overlaps, plus `spicelib` which we plan to drop or internalize.
    * Pin versions or ranges as appropriate (e.g., Python >=3.10 as currently, and ensure compatibility with latest versions of dependencies).
  * Define any **entry points** for console scripts if we want to expose command-line tools. For instance, we can create console entry points in `pyproject.toml` like:

    * `cespy-asc-to-qsch = cespy.editor.asc_editor:main` (if we have a main function to convert a file).
    * `cespy-run-server = cespy.client_server.sim_server:main` (to start the simulation server).
    * `cespy-rawplot = cespy.raw.raw_plot:main` (for plotting raw files, if such a function exists).
      By providing these, we replace the need for separate scripts directory. Each script from the original `kupicelib/scripts` can be refactored into a function within the appropriate module, and exposed as a command-line tool via setup. This improves integration and maintainability (no duplicate code in scripts vs library).
  * Ensure that the package is marked as compatible with relevant Python versions and that the license (GPL-3.0) is correctly specified.

## Refactoring and Code Organization Suggestions

To achieve a maintainable and scalable codebase, we will refactor parts of the combined code during the merge:

* **Unify and Clean Module Names:** Correct any inconsistent naming. Notably, rename the `sim/tookit` directory to `sim/toolkit` (a likely typo in the original) for clarity. Ensure module names clearly reflect their purpose (e.g., if `LTSteps.py` in kuPyLTSpice was meant as a user-facing helper for stepping simulations, perhaps its functionality should be integrated into `sim_stepping.py` or exposed via a more descriptive API).
* **Merge Duplicate Classes/Functions:** Where kuPyLTSpice defines a class that extends or wraps a kupicelib class, we can merge them:

  * If kuPyLTSpice’s version only adds minimal tweaks, consider adding that functionality into the kupicelib class and removing the wrapper. For example, if kuPyLTSpice had an `LTSpiceSimRunner` that calls kupicelib’s `SimRunner` but maybe adds one extra log message or parameter, we can incorporate that parameter into the unified SimRunner.
  * Remove any circular dependencies or ping-pong calls between the two packages. After merging, everything will reside in one namespace, so we can replace cross-package imports with internal imports. This might simplify call flows (e.g., kuPyLTSpice’s `run_server.py` likely just invoked kupicelib’s server; in the unified package, there’s just one `run_server` implementation to call).
* **Simplify Simulation API:** Evaluate how a user currently runs a simulation:

  * Possibly, kuPyLTSpice provided a function or class to run LTSpice and get results easily (since PyLTSpice’s goal was user-friendliness). We should ensure the unified package has a clear high-level API for running simulations. For example, we might provide a class like `LTSpiceRunner` or a function like `simulate(netlist_path, ...)` that under the hood uses `kupicelib.sim.sim_runner` and the `simulators/ltspice_simulator`.
  * We can integrate the various simulation approaches: kupicelib has a generic `Simulator` interface and separate classes for each engine, plus a server option. We should present these in a coherent way. Perhaps a user can choose an engine via a parameter, or instantiate a specific simulator class. The key is to document it clearly and make common tasks straightforward.
* **Maintainability Improvements:** Use this merge as an opportunity to improve code quality:

  * Ensure **type hints** are consistent and correct across the codebase (kupicelib already had a `py.typed` marker for typing). Merging code might require reconciling some function signatures or adding missing type hints from the kuPyLTSpice side.
  * Apply a consistent **coding style** (formatting, naming conventions). Resolve any stylistic differences between the two codebases.
  * Remove dead code or legacy sections that are no longer needed after merging. For example, if kuPyLTSpice had workarounds for functionality now fully handled by kupicelib, those can be deleted.
  * Improve internal module documentation: add docstrings to key classes and functions if they are missing. This will help future maintainers or contributors understand the code.
* **Documentation and Examples:** Unify documentation:

  * Combine the READMEs of both projects, distilling the important information from each. The new README should introduce the unified tool, list its features (covering what both original projects did), and provide basic usage examples.
  * If not already present, consider creating a **User Guide** or reference manual. This could cover topics like: setting up LTSpice for use with the library, using the API to modify a circuit and run sweeps, parsing results, performing Monte Carlo analyses, etc.
  * Ensure that any API changes (due to refactoring or renaming) are reflected in the documentation. Since backward compatibility isn't strictly required, we can simplify function names or parameters, but we must update examples accordingly.
  * (Optional) Prepare a short **migration guide** in the documentation: for instance, “If you previously used `kuPyLTSpice.LTSpiceSimulation(...)`, now use `cespy.simulators.LTSpiceSimulator`” – this will help any existing user (or the author themselves) transition smoothly.
* **Retain Major Functionality:** As a guiding principle, all the capabilities from both packages should still be available:

  * **LTSpice Automation:** Running LTSpice simulations headlessly and retrieving data (the core of PyLTSpice/kuPyLTSpice) – this must work seamlessly in the new package.
  * **Schematic Editing:** Programmatically modifying `.asc` or `.qsch` files (for LTSpice and QSpice) – maintain these features from kupicelib.
  * **Data Analysis:** Plotting or analyzing simulation outputs (e.g., the `rawplot` and histogram scripts, Monte Carlo analysis, worst-case analysis) – these should be integrated, possibly with improved interfaces. For instance, instead of separate scripts, we could provide a function `plot_raw_waveform(raw_file, signals)` that users can call, as well as a CLI command for quick usage.
  * **Multi-Engine Support:** Keep support for NGSpice, QSpice, etc., as provided by kupicelib’s design. This may widen the appeal of the unified tool beyond just LTSpice users.
  * **Performance Considerations:** If there are any performance bottlenecks or heavy resource usage (e.g., reading large .raw files can be memory-intensive), note if any refactoring can improve that (maybe using more efficient numpy operations, etc.). While not a primary goal of the merge, it’s worth keeping an eye on opportunities to optimize during consolidation.

By the end of refactoring, the codebase should be organized logically with minimal redundancy. The unified **cespy** package will act as a single source of truth for all simulation automation tasks, making it easier to maintain and extend.

## Unified Packaging and Configuration

With the code merged, the next step is to unify the build and distribution setup:

* **Single PyPI Package:** Only one package will be published. Assuming we keep the name `cespy` (as an example), we will release a new version, e.g. **cespy 0.1.0**, on PyPI. This version will include all functionality from the old kupicelib 1.0.1 *and* kuPyLTSpice 1.0.0. We will clearly mention in the release notes that this is a merged project.

  * If using a new name entirely, ensure to publish that and potentially deprecate the old ones (see “Migration Plan” below for handling existing users of the old packages).

* **pyproject.toml / setup.py:** Create a unified project file. If continuing with Poetry, we will have one `pyproject.toml` in the repository root. Key configurations:

  * **Project metadata:** name, version, description, authors, license. Use the GitHub repository of the unified project for the homepage/URL. Write a concise description that covers both aspects (e.g., “A Python toolkit for automating SPICE circuit simulators (LTSpice, NGSpice, etc.), providing schematic editing, simulation control, and result analysis.”).
  * **Dependencies:** as discussed, include all required libraries. Verify version compatibility (for instance, ensure that the version of Pandas required by kupicelib doesn’t conflict with anything else, etc.). Remove `spicelib` from requirements if we succeeded in eliminating it.
  * **Optional Dependencies:** If there are features that require optional packages (for example, maybe plotting might require matplotlib – which we already include – or if we want to support some GUI integration, etc.), consider grouping them. But likely everything is required as core for now.
  * **Entrypoints:** Under `[tool.poetry.scripts]` or the `[project.scripts]` section (depending on build system), define console script entry points for the tools we want to expose (as noted earlier). For each script that we migrated from `scripts/`, decide if it’s useful to expose to users:

    * `asc_to_qsch`: if converting LTSpice schematics to QSpice is a common need, include a CLI.
    * `rawplot`: could be useful for quick plotting of raw files.
    * `run_server`: definitely include, so users can start the server easily from command line.
    * `histogram` and `ltsteps`: these might have been internal or example utilities; we can expose them if they might be generally useful (e.g., maybe `ltsteps` prints the step values from a .log file – that can be a quick diagnostic tool).
    * Make sure each entry point has a corresponding function in the code that can be invoked.
  * **Testing configuration:** If using pytest or any test framework, ensure it’s listed under dev dependencies and that tests are included in the package manifest if needed.
  * **Package data:** Include any non-code files needed (e.g., the `asc_to_qsch_data.xml` from kupicelib’s scripts should be included in the package, likely by moving it to a proper location inside the package, such as `cespy/editor/asc_to_qsch_data.xml` and listing it in package data). We must be careful to include such data files in the build so that functions can access them at runtime.

* **Version Control & Repository Merge:** On the GitHub side, merge the repositories. This could be done by one of:

  * Moving files from one repo to the other and committing, or
  * Using git subtree or history import to preserve commit history of both (optional but nice for record-keeping).
  * Update the repository README, CI workflows (if any), and issue trackers accordingly.
  * Set up continuous integration (CI) if not already, to run tests and perhaps build wheels.

## Testing and Migration Plan

Ensuring that the unified package preserves all functionality is critical. We will implement a thorough testing and migration strategy:

* **Comprehensive Testing of Features:** Create a test plan covering all major features from both packages:

  * *Circuit Editing:* Test that the unified library can open an LTSpice `.asc` file, modify a component value or wiring, and save it without corruption. Do the same for a QSpice `.qsch` file if supported.
  * *Simulation Execution:* Test running a simple LTSpice simulation via the new API:

    * Without the server (direct execution): e.g., open a netlist or schematic, run an AC analysis, and verify that a `.raw` file is produced and data can be read.
    * With the server: start the simulation server in one process, submit a simulation job from another process (using sim\_client), and ensure results come back correctly.
    * Test NGSpice or others if available: for example, use a small netlist and run NGSpice via the unified tool to ensure that path detection and process handling works for that simulator as well.
  * *Result Parsing:* After a simulation, use the library to parse the .raw file and .log file:

    * Verify that waveform data (node voltages, currents) can be retrieved and are accurate (compare to an expected result or to LTSpice’s GUI output if possible).
    * Verify that the log parser can extract step data (for .step runs) and operating point info, etc.
  * *Analysis Tools:* If the library includes Monte Carlo or worst-case analysis functions, test these on known circuits to see that they produce reasonable outputs (or at least run without errors).
  * *CLI Tools:* For each console script we provide, run it in a test scenario:

    * e.g., run `cespy-run-server` to start the server and see that it listens (perhaps connect a client in tests).
    * Run `cespy-asc-to-qsch example.asc` on a sample file and confirm it outputs a .qsch (and that the output matches expected format).
    * Run `cespy-rawplot example.raw` on a known raw file and see that it produces a plot (this might be hard to automate, but we can at least ensure it does not throw errors).
  * Consider writing **unit tests** for critical modules (if not already existing). For instance, tests for the raw file parser (feeding it a small known binary and checking parsed values), tests for the sweep iterator utility, etc. Automate these with a framework like `pytest`.
  * If possible, integrate these tests into a CI pipeline to run on every commit.

* **Preserving Functionality:** If any test or manual trial reveals missing functionality (e.g., “the old kuPyLTSpice had a function to do X easily, but the new package requires several steps”), consider adding a convenience wrapper or adjusting the API to cover that use-case. The idea is that nothing that **both** packages could do before is lost. It’s acceptable if the exact calling method changes (since backward compatibility isn’t strict), but the capability should remain. We will also verify that all command-line tools or entry points from the old `scripts` still work in their new form.

* **Migration for Users:** Even if backward compatibility is not required, we should make the transition clear:

  * In the **kuPyLTSpice** repository (and PyPI project), it’s wise to publish a final minor release or at least update the README to state that “kuPyLTSpice has been merged into \[new package name] as of \[version]. Please install that package for future updates.” If possible, you could release kuPyLTSpice 1.0.1 that simply imports the unified package and perhaps throws a deprecation warning when used. This way, any existing code using kuPyLTSpice isn’t immediately broken – it will still function by relying on the unified package under the hood – but users are notified to switch. This step is optional, but it smooths the migration.
  * For **kupicelib** users, if we keep the name but restructure some APIs, highlight changes in the documentation. E.g., “The `kupicelib.simulators.LTSpice_Simulator` class is replaced by `cespy.simulators.LTSpiceSimulator` (name change)” or “Functions X and Y moved from module A to module B.”
  * Clearly version the unified release as a new major version (2.x) to signal that breaking changes may be present. This manages expectations for users upgrading.
  * Ensure that both old GitHub repos (if the unified is new or one is deprecated) have pointers to the new unified repo in their descriptions.

* **Performance and Regression Testing:** It’s possible that merging code could introduce regressions. We should test on multiple platforms if relevant (especially because this deals with external simulators like LTSpice which is Windows-only, vs NGSpice which can be Linux, etc.):

  * Test on Windows (for LTSpice and QSpice use-cases), on Linux/macOS (for NGSpice, Xyce use-cases). The unified library should function appropriately on each (with the understanding that certain simulators might not be available on all OS).
  * Monitor memory usage and execution time for key operations (like reading a large .raw file) to ensure the new integration didn’t accidentally worsen performance. If any regression is found, optimize as needed.
  * Validate that path configurations for finding the simulator executables (LTSpice installation path, etc.) still work or have clear configuration options in the new package.

By following this testing plan, we can be confident that the merged library is robust and fully functional, matching or exceeding the capabilities of the two original packages.

## Additional Improvements (Optional)

During or after the merge, a few enhancements can further improve the unified package:

* **Improved Documentation**: Beyond a basic README, consider setting up a documentation site (using Sphinx or MkDocs) for the unified package. This can include tutorials (e.g., “Automating LTSpice with Python – a step-by-step guide using the unified library”), an API reference (documenting all classes and functions), and examples for advanced features (like Monte Carlo analysis).
* **Examples and Tutorials**: Include a directory of example circuits and scripts demonstrating usage. For instance, an `examples/` folder in the repo with small LTSpice files and Python scripts on how to modify and simulate them. This not only tests the library but also serves as user guidance.
* **Command-Line Interface (CLI)**: In addition to the small entry point tools, consider a more unified CLI experience. For example, using something like `argparse` or `click` to allow a command `cespy` with subcommands:

  * `cespy simulate <circuit.asc>` – to run a simulation on the given schematic or netlist.
  * `cespy convert asc2qsch <file.asc>` – to convert formats.
  * `cespy analyze montecarlo <netlist> --runs 100` – to perform a Monte Carlo analysis via CLI.
    This could make the tool usable directly from the shell for quick tasks, complementing the Python API. This can be built on top of the existing functions.
* **API Restructuring**: Consider introducing a higher-level API class that unifies common tasks. For example, a `CircuitSimulator` class where the user can specify which engine to use (LTSpice/NGSpice) and then call methods to run simulations, rather than the user having to manually pick the correct simulator class. This can increase ease of use. Under the hood, it would utilize the classes in `simulators/` and `sim/sim_runner`, but it provides a cleaner facade.
* **Scalability Considerations**: If users might run large numbers of simulations or very large circuits, consider features like:

  * Parallel execution of multiple simulations (maybe leveraging the server mechanism or multiprocessing).
  * More efficient data handling (perhaps not loading entire raw files into memory if not needed, or streaming results).
    While these might be future enhancements, structuring the code with scalability in mind (e.g. a clear separation between data model and processing, so it’s easier to extend later) is beneficial.
* **Community and Contribution**: Since the unified project is larger in scope, it might attract more users or contributors (especially if it’s the only tool combining LTSpice, NGSpice, etc., with Python automation). Setting up contribution guidelines, improving code readability, and writing tests will facilitate external contributions if the project becomes open to them.

## Release Roadmap

1. **Testing**:

   * Before releasing, perform the testing plan. Write automated tests where possible and/or do manual testing of each feature. Start with small unit tests for critical components (file parsing, etc.), then integration tests for full simulation runs.
   * Test installation locally: build the wheel (`poetry build` or `python -m build`) and try `pip install`ing it in a fresh virtual environment. Then run a few example uses to ensure everything is included and working (catch issues like missing files in the package, etc.).
   * Fix any bugs or issues uncovered by testing (e.g., import errors from the refactor, missing dependencies, etc.). Iterate until the unified package runs all tests successfully.
2. **Documentation & Examples**:

   * Write a new README.md that reflects the unified library. Include usage examples (maybe adapted from kuPyLTSpice’s readme and kupicelib’s readme). Make sure to highlight any changes in usage.
   * Optionally, set up a docs site. If not immediately, at least prepare an extended README or a docs/ directory for future expansion.
   * Update any badges or CI status in the README for the unified repo. Remove or update references that are obsolete (e.g., if README still refers to installing kuPyLTSpice separately, change that).
   * If providing a migration guide or deprecation notes, include those in the docs or as a section in the README.
3. **Release**:

   * Once the code and documentation are ready and tested, publish the unified package to PyPI. For example, if using Poetry: `poetry publish` for version 2.0.0.
   * Verify the PyPI release by installing it via pip and running a quick functionality test.
   * Post-release, in the **kuPyLTSpice** PyPI project, consider releasing a final update (version 1.0.1) that has an install requirement of `cespy>=0.1.0` and perhaps prints a warning if used. This will effectively push users to migrate. If you choose not to do this, at least update the project description on PyPI and the GitHub README to indicate it’s deprecated in favor of the new package.
   * Similarly, update the **kupicelib** project description on PyPI if needed (to reflect the new scope).
   * Publish under the name `cespy` and possibly yank old releases or leave them with notes.
4. **Post-Release Follow-Up**:

   * Monitor any issue trackers or user feedback for the new release. Fix any unforeseen issues (e.g., if some environment had a problem, or if an important feature was unintentionally broken).
   * Close out any redundant issue pages or pull requests in the old repos, directing people to the new repository.
   * Continue development on the unified codebase going forward, with all new features being added there.

By following this roadmap, we will successfully unify **kupicelib** and **kuPyLTSpice** into a single, streamlined Python package. The result will be a more powerful and maintainable simulation toolkit, with a cleaner architecture and a one-step installation, meeting the goals of unification and simplification while preserving all the functionality of the original libraries.

**Sources:**

* Wheel metadata for **kuPyLTSpice 1.0.0**, showing its dependency on kupicelib and spicelib and the overlap of modules with kupicelib (e.g. duplicate `asc_editor.py`).
* Wheel metadata for **kupicelib 1.0.1**, showing its comprehensive module set (editors, simulators for multiple engines, etc.).
