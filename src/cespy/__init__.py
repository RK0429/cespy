"""CESPy - Circuit Engineering and SPICE Python package.

This package provides a high-level Python interface for circuit simulation using various
SPICE simulators (LTspice, NGspice, QSpice, Xyce). It includes tools for circuit editing,
simulation management, and result analysis.
"""

# Add top-level version and imports for key simulator classes
__version__ = "0.1.0"

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

from cespy.editor.asc_editor import AscEditor
from cespy.editor.spice_editor import SpiceCircuit, SpiceEditor
from cespy.log.ltsteps import LTSpiceLogReader
from cespy.raw.raw_read import RawRead, SpiceReadException
from cespy.raw.raw_write import RawWrite, Trace

# High-level simplified simulation API
from .sim import SimRunner
from .simulators.ltspice_simulator import LTspice
from .simulators.ngspice_simulator import NGspiceSimulator
from .simulators.qspice_simulator import Qspice
from .simulators.xyce_simulator import XyceSimulator

__all__ = [
    "LTspice",
    "NGspiceSimulator",
    "Qspice",
    "XyceSimulator",
    "AscEditor",
    "SpiceEditor",
    "SpiceCircuit",
    "LTSpiceLogReader",
    "RawRead",
    "SpiceReadException",
    "RawWrite",
    "Trace",
]


def simulate(
    circuit: Union[str, Path, Any],
    engine: str = "ltspice",
    *,
    parallel_sims: int = 4,
    timeout: float = 600.0,
    verbose: bool = False,
    output_folder: Optional[str] = None,
    wait_resource: bool = True,
    callback: Optional[Callable[..., Any]] = None,
    callback_args: Optional[Union[tuple[Any, ...], Dict[str, Any]]] = None,
    switches: Optional[List[str]] = None,
    run_filename: Optional[str] = None,
    exe_log: bool = False,
) -> SimRunner:
    """Run a simulation for a given circuit file or editor using the
    specified engine.

    :param circuit: Path to the circuit file or a SpiceEditor instance.
    :param engine: The simulation engine to use: 'ltspice', 'ngspice',
        'qspice', or 'xyce'.
    :param parallel_sims: Number of parallel simulations to run.
    :param timeout: Timeout in seconds for each simulation.
    :param verbose: Enable verbose logging.
    :param output_folder: Folder to store simulation outputs.
    :param wait_resource: Whether to wait for resource availability.
    :param callback: Optional callback function or ProcessCallback class.
    :param callback_args: Arguments for the callback.
    :param switches: Command-line switches for the simulator.
    :param run_filename: Custom filename for output files.
    :param exe_log: Log simulator console output to a file.
    :return: A SimRunner instance after completion.
    """
    engines = {
        "ltspice": LTspice,
        "ngspice": NGspiceSimulator,
        "qspice": Qspice,
        "xyce": XyceSimulator,
    }
    sim_key = engine.lower()
    if sim_key not in engines:
        raise ValueError(
            f"Unsupported engine '{engine}'. Choose from {list(engines.keys())}."
        )
    sim_cls = engines[sim_key]
    runner = SimRunner(
        simulator=sim_cls,
        parallel_sims=parallel_sims,
        timeout=timeout,
        verbose=verbose,
        output_folder=output_folder,
    )
    runner.run(
        circuit,
        wait_resource=wait_resource,
        callback=callback,
        callback_args=callback_args,
        switches=switches,
        timeout=timeout,
        run_filename=run_filename,
        exe_log=exe_log,
    )
    runner.wait_completion()
    return runner


# Expose the high-level API
__all__.append("simulate")
