#!/usr/bin/env python
# coding=utf-8

# -------------------------------------------------------------------------------
#    ____        _   _____ ____        _
#   |  _ \ _   _| | |_   _/ ___| _ __ (_) ___ ___
#   | |_) | | | | |   | | \___ \| '_ \| |/ __/ _ \
#   |  __/| |_| | |___| |  ___) | |_) | | (_|  __/
#   |_|    \__, |_____|_| |____/| .__/|_|\___\___|
#          |___/                |_|
#
# Name:        sim_batch.py
# Purpose:     Tool used to launch LTSpice simulation in batch mode. Netlists can
#              be updated by user instructions
#
# Author:      Nuno Brum (nuno.brum@gmail.com)
#
# Licence:     refer to the LICENSE file
# -------------------------------------------------------------------------------
"""** This class is still maintained for backward compatibility. The user is invited to
use the SpiceEditor and SimRunner classes instead. These give more flexibility in the
command of simulations.**

Allows launching LTSpice simulations from a Python Script, thus allowing to overcome the
3 dimensions STEP limitation on LTSpice, update resistor values, or component models.

The code snipped below will simulate a circuit with two different diode models, set the
simulation temperature to 80 degrees, and update the values of R1 and R2 to 3.3k. ::

LTC = SimCommander("my_circuit.asc") LTC.set_parameters(temp=80)  # Sets the simulation
temperature to be 80 degrees LTC.set_component_value('R2', '3.3k')  #  Updates the
resistor R2 value to be 3.3k for dmodel in ("BAT54", "BAT46WJ"):
LTC.set_element_model("D1", model)  # Sets the Diode D1 model     for res_value in
sweep(2.2, 2,4, 0.2):  # Steps from 2.2 to 2.4 with 0.2 increments
LTC.set_component_value('R1', res_value)  #  Updates the resistor R1 value to be 3.3k
LTC.run()

LTC.wait_completion()  # Waits for the LTSpice simulations to complete

print("Total Simulations: {}".format(LTC.runno)) print("Successful Simulations:
{}".format(LTC.okSim)) print("Failed Simulations: {}".format(LTC.failSim))

The first line will create an python class instance that represents the LTSpice file or
netlist that is to be simulated. This object implements methods that are used to
manipulate the spice netlist. For example, the method set_parameters() will set or
update existing parameters defined in the netlist. The method set_component_value() is
used to update existing component values or models.

--------------- Multiprocessing ---------------

For making better use of today's computer capabilities, the SimCommander spawns several
LTSpice instances each executing in parallel a simulation.

By default, the number of parallel simulations is 4, however the user can override this
in two ways. Either using the class constructor argument ``parallel_sims`` or by forcing
the allocation of more processes in the run() call by setting ``wait_resource=False``.
::

LTC.run(wait_resource=False)

The recommended way is to set the parameter ``parallel_sims`` in the class constructor.
::

LTC=SimCommander("my_circuit.asc", parallel_sims=8)

The user then can launch a simulation with the updates done to the netlist by calling
the run() method. Since the processes are not executed right away, but rather just
scheduled for simulation, the wait_completion() function is needed if the user wants to
execute code only after the completion of all scheduled simulations.

The usage of wait_completion() is optional. Just note that the script will only end when
all the scheduled tasks are executed.

--------- Callbacks ---------

As seen above, the `wait_completion()` can be used to wait for all the simulations to be
finished. However, this is not efficient from a multiprocessor point of view. Ideally,
the post-processing should be also handled while other simulations are still running.
For this purpose, the user can use a function call back.

The callback function is called when the simulation has finished directly by the thread
that has handling the simulation. A function callback receives two arguments. The RAW
file and the LOG file names. Below is an example of a callback function::

def processing_data(raw_filename, log_filename):     '''This is a call back function
that just prints the filenames'''     print("Simulation Raw file is %s. The log is %s" %
(raw_filename, log_filename)     # Other code below either using LTSteps.py or
raw_read.py     log_info = LTSpiceLogReader(log_filename)     log_info.read_measures()
rise, measures = log_info.dataset["rise_time"]

The callback function is optional. If  no callback function is given, the thread is
terminated just after the simulation is finished.
"""
__author__ = "Nuno Canto Brum <nuno.brum@gmail.com>"
__copyright__ = "Copyright 2020, Fribourg Switzerland"

import logging
import os
from pathlib import Path
from typing import Any, Callable, Optional, Type, Union

from kupicelib.editor.spice_editor import SpiceEditor
from kupicelib.sim.process_callback import ProcessCallback
from kupicelib.sim.sim_runner import SimRunner
from kupicelib.sim.simulator import Simulator

_logger = logging.getLogger("kupicelib.SimBatch")

END_LINE_TERM = "\n"


class SimCommander(SpiceEditor):
    """*(Deprecated)* Backwards compatibility class.

    This class will be soon deprecated. For a better control of the simulation
    environment, supporting other simulators and allowing to simulate directly the .ASC
    files, the SpiceEditor class is now separated from the Simulator Running class.
    Please check the SimRunner class for more information.
    """

    def __init__(
        self,
        netlist_file: Union[str, Path],
        parallel_sims: int = 4,
        timeout: Optional[float] = None,
        verbose: bool = False,
        encoding: str = "autodetect",
        simulator: Optional[Union[str, Type[Simulator]]] = None,
    ):
        from ..sim.ltspice_simulator import LTspice  # In case no simulator is given

        # Convert simulator to the right type
        actual_simulator: Type[Simulator]
        if simulator is None:
            actual_simulator = LTspice
        elif isinstance(simulator, str):
            actual_simulator = LTspice.create_from(simulator)
        elif isinstance(simulator, type) and issubclass(simulator, Simulator):
            actual_simulator = simulator
        else:
            actual_simulator = LTspice

        netlist_file_path = Path(netlist_file)
        self.netlist_file = netlist_file_path  # Legacy property

        # Handle .asc files by creating a netlist
        if netlist_file_path.suffix == ".asc":
            # Create an instance of the simulator to create the netlist
            simulator_instance = actual_simulator.create_from(None)
            netlist_file_path = simulator_instance.create_netlist(
                netlist_file_path)

        super().__init__(netlist_file_path, encoding)

        # Ensure output_folder is a string
        output_folder = (
            netlist_file_path.parent.as_posix()
            if isinstance(netlist_file_path, Path)
            else os.path.dirname(str(netlist_file))
        )

        # Ensure timeout is a float
        timeout_float = float(timeout) if timeout is not None else 600.0

        self.runner = SimRunner(
            simulator=actual_simulator,
            parallel_sims=parallel_sims,
            timeout=timeout_float,
            verbose=verbose,
            output_folder=output_folder,
        )

    def setLTspiceRunCommand(
            self, spice_tool: Union[str, Type[Simulator]]) -> None:
        """*(Deprecated)* Manually setting the LTSpice run command.

        :param spice_tool: String containing the path to the spice tool to be used, or
            alternatively the Simulator object.
        :type spice_tool: str or Simulator
        :return: Nothing
        :rtype: None
        """
        from ..sim.ltspice_simulator import LTspice

        # Convert spice_tool to the right type
        actual_simulator: Type[Simulator]
        if isinstance(spice_tool, str):
            actual_simulator = LTspice.create_from(spice_tool)
        elif isinstance(spice_tool, type) and issubclass(spice_tool, Simulator):
            actual_simulator = spice_tool
        else:
            _logger.warning("Invalid simulator type. Using default LTspice.")
            actual_simulator = LTspice

        # SimRunner doesn't have a set_run_command method, but it accepts a simulator
        # parameter in the constructor
        # For backward compatibility, we'll issue a warning and attempt to create
        # a new runner with the specified simulator
        _logger.warning(
            "setLTspiceRunCommand is deprecated. Use SimRunner directly with the simulator parameter."
        )

        output_folder = getattr(self.runner, "output_folder", None)
        timeout_val = getattr(self.runner, "timeout", None)
        timeout_float = float(
            timeout_val) if timeout_val is not None else 600.0

        self.runner = SimRunner(
            simulator=actual_simulator,
            parallel_sims=getattr(self.runner, "parallel_sims", 4),
            timeout=timeout_float,
            verbose=getattr(self.runner, "verbose", False),
            output_folder=output_folder,
        )

    def add_LTspiceRunCmdLineSwitches(self, *args) -> None:
        """*(Deprecated)* Used to add an extra command line argument such as -I<path> to
        add symbol search path or -FastAccess to convert the raw file into Fast Access.
        The arguments is a list of strings as is defined in the LTSpice command line
        documentation.

        :param args: list of strings A list of command line switches such as "-ascii"
            for generating a raw file in text format or "-alt" for setting the solver to
            alternate. See Command Line Switches information on LTSpice help file.
        :type args: list[str]
        :returns: Nothing
        """
        self.runner.clear_command_line_switches()
        for option in args:
            self.runner.add_command_line_switch(option)

    def run(
        self,
        wait_resource: bool = True,
        callback: Optional[Union[Type[Any],
                                 Callable[[Path, Path], Any]]] = None,
        timeout: Optional[float] = 600,
        run_filename: Optional[str] = None,
        simulator=None,
    ):
        """Run the simulation with the updated netlist.

        This overrides the parent class method to maintain backward compatibility.

        :param wait_resource: If True, waits for a free slot if all the workers are busy
        :param callback: Optional callback to process the results
        :param timeout: Timeout in seconds for the simulation
        :param run_filename: Optional filename for the netlist
        :param simulator: Optional simulator to use
        :return: A RunTask object
        """
        # Adapt callback if necessary
        adapted_callback: Optional[Union[Type[Any],
                                         Callable[[Path, Path], Any]]] = None

        if callback is not None:
            if isinstance(callback, type) and issubclass(
                    callback, ProcessCallback):
                adapted_callback = callback
            elif callable(callback):
                # Create a wrapper function that adapts the callback to the expected
                # signature
                # For backward compatibility, convert Path objects to strings
                def adapted_callback_wrapper(
                        raw_file: Path, log_file: Path) -> Any:
                    # Type: ignore is used to silence the linter errors while
                    # maintaining backward compatibility with callbacks that expect
                    # string arguments instead of Path objects
                    return callback(str(raw_file), str(
                        log_file))  # type: ignore

                adapted_callback = adapted_callback_wrapper

        # Use non-None timeout
        actual_timeout = float(timeout) if timeout is not None else 600.0

        # If simulator is None, we'll use the default one from the runner
        result = self.runner.run(
            self,
            wait_resource=wait_resource,
            callback=adapted_callback,
            timeout=actual_timeout,
            run_filename=run_filename,
        )

        # Create a dummy RunTask if None is returned
        if result is None:
            _logger.warning("Runner.run() returned None, which is unexpected.")
            return None  # Simply return None if result is None

        return result

    def updated_stats(self):
        """*(Deprecated)* This function updates the OK/Fail statistics and releases
        finished RunTask objects from memory.

        :returns: Nothing
        """
        self.runner.active_threads()
        return

    def wait_completion(self, timeout=None,
                        abort_all_on_timeout=False) -> bool:
        return self.runner.wait_completion(timeout, abort_all_on_timeout)

    @property
    def runno(self):
        """*(Deprecated)* Legacy property."""
        return self.runner.runno

    @property
    def okSim(self):
        """*(Deprecated)* Legacy property."""
        return self.runner.okSim

    @property
    def failSim(self):
        """*(Deprecated)* Legacy property."""
        return self.runner.failSim


if __name__ == "__main__":
    # get script absolute path
    meAbsPath = os.path.dirname(os.path.realpath(__file__))
    meAbsPath, _ = os.path.split(meAbsPath)
    # select spice model
    LTC = SimCommander("C:\\sandbox\\PySpice\\tests\\testfile.asc")
    # set default arguments
    LTC.set_parameters(res=0.001, cap=100e-6)
    # define simulation
    LTC.add_instructions(
        "; Simulation settings",
        # [".STEP PARAM Rmotor LIST 21 28"],
        ".TRAN 3m",
        # ".step param run 1 2 1"
    )
    # do parameter sweep
    for res in range(5):
        # LTC.runs_to_do = range(2)
        LTC.set_parameters(ANA=res)
        raw, log = LTC.run().wait_results()
        _logger.debug("Raw file '%s' | Log File '%s'" % (raw, log))
    # Sim Statistics
    _logger.info(
        "Successful/Total Simulations: " +
        str(LTC.okSim) + "/" + str(LTC.runno)
    )

    def callback_function(raw_file, log_file):
        _logger.debug(
            "Handling the simulation data of %s, log file %s" % (
                raw_file, log_file)
        )

    LTC = SimCommander(
        meAbsPath +
        "\\test_files\\testfile.asc",
        parallel_sims=1)
    tstart = 0
    bias_file = None  # Initialize bias_file to prevent undefined variable error
    for tstop in (2, 5, 8, 10):
        tduration = tstop - tstart
        LTC.add_instruction(
            ".tran {}".format(tduration),
        )
        if tstart != 0 and bias_file is not None:  # Check that bias_file is defined
            LTC.add_instruction(".loadbias {}".format(bias_file))
            # Put here your parameter modifications
            # LTC.set_parameters(param1=1, param2=2, param3=3)
        bias_file = "sim_loadbias_%d.txt" % tstop
        LTC.add_instruction(
            ".savebias {} internal time={}".format(bias_file, tduration)
        )
        tstart = tstop
        LTC.run(callback=callback_function)

    LTC.reset_netlist()
    LTC.add_instruction(".ac dec 40 1m 1G")
    LTC.set_component_value("V1", "AC 1 0")
    LTC.run(callback=callback_function)
    LTC.wait_completion()
