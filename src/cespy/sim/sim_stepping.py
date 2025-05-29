#!/usr/bin/env python
"""Module for managing stepped simulations with parameter sweeps."""

# flake8: noqa

# -------------------------------------------------------------------------------
#
#  ███████╗██████╗ ██╗ ██████╗███████╗██╗     ██╗██████╗
#  ██╔════╝██╔══██╗██║██╔════╝██╔════╝██║     ██║██╔══██╗
#  ███████╗██████╔╝██║██║     █████╗  ██║     ██║██████╔╝
#  ╚════██║██╔═══╝ ██║██║     ██╔══╝  ██║     ██║██╔══██╗
#  ███████║██║     ██║╚██████╗███████╗███████╗██║██████╔╝
#  ╚══════╝╚═╝     ╚═╝ ╚═════╝╚══════╝╚══════╝╚═╝╚═════╝
#
# Name:        sim_stepping.py
# Purpose:     Spice Simulation Library intended to automate the exploring of
#              design corners, try different models and different parameter
#              settings.
#
# Author:      Nuno Brum (nuno.brum@gmail.com)
#
# Created:     31-07-2020
# Licence:     refer to the LICENSE file
# -------------------------------------------------------------------------------

__author__ = "Nuno Canto Brum <nuno.brum@gmail.com>"
__copyright__ = "Copyright 2017, Fribourg Switzerland"

import logging
import sys
from functools import wraps
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Optional,
    Protocol,
    Tuple,
    Type,
    Union,
)

from ..editor.base_editor import BaseEditor
from .process_callback import ProcessCallback
from .sim_runner import AnyRunner

_logger = logging.getLogger("cespy.SimStepper")


class RunnerProtocol(AnyRunner, Protocol):
    """Protocol for runner used in SimStepper, includes ok_sim and runno attributes."""

    @property
    def ok_sim(self) -> int:
        """Return the number of successful simulations."""
        raise NotImplementedError("ok_sim must be implemented by subclass")

    @property
    def runno(self) -> int:
        """Return the total number of simulations run."""
        raise NotImplementedError("runno must be implemented by subclass")


class StepInfo:
    """Container for simulation step information."""

    def __init__(self, what: str, elem: str, iterable: Iterable[Any]) -> None:
        self.what = what
        self.elem = elem
        self.iter = iterable

    def __len__(self) -> int:
        return len(list(self.iter))

    def __str__(self) -> str:
        return f"Iteration on {self.what} {self.elem} : {self.iter}"


class SimStepper:
    """This class is intended to be used for simulations with many parameter sweeps.
    This provides a more user-friendly interface than the SpiceEditor/SimRunner class
    when there are many parameters to be stepped.

    Using the SpiceEditor/SimRunner classes a loop needs to be added for each dimension
    of the simulations. A typical usage would be as follows:

    .. code-block:: python

        netlist = SpiceEditor("my_circuit.asc")
        runner = SimRunner(parallel_sims=4)
        for dmodel in ("BAT54", "BAT46WJ"):
            netlist.set_element_model("D1", model)  # Sets the Diode D1 model
            for res_value1 in sweep(2.2, 2.4, 0.2):  # Steps from 2.2 to 2.4 with 0.2 increments
                # Updates the resistor R1 value
                netlist.set_component_value('R1', res_value1)
                for temperature in sweep(0, 80, 20):  # Temperature step 0-80°C in 20° steps
                    # Sets the simulation temperature
                    netlist.set_parameters(temp=80)
                    for res_value2 in (10, 25, 32):
                        # Updates the resistor R2 value
                        netlist.set_component_value('R2', res_value2)
                        runner.run(netlist)

        runner.wait_completion()  # Waits for the Spice simulations to complete

    With SimStepper the same thing can be done as follows, resulting in a cleaner code.

    .. code-block:: python

        netlist = SpiceEditor("my_circuit.asc")
        Stepper = SimStepper(netlist, SimRunner(parallel_sims=4, output_folder="./output"))
        Stepper.add_model_sweep('D1', "BAT54", "BAT46WJ")
        # Steps from 2.2 to 2.4 with 0.2 increments
        Stepper.add_component_sweep('R1', sweep(2.2, 2.4, 0.2))
        # Temperature step from 0 to 80 degrees in 20 degree steps
        Stepper.add_parameter_sweep('temp', sweep(0, 80, 20))
        Stepper.add_component_sweep('R2', (10, 25, 32))  # Updates the resistor R2 value
        Stepper.run_all()

    Another advantage of using SimStepper is that it can optionally use the .SAVEBIAS in
    the first simulation and then use the .LOADBIAS command at the subsequent ones to
    speed up the simulation times.
    """

    def __init__(self, circuit: BaseEditor, runner: RunnerProtocol) -> None:
        self.runner = runner
        self.netlist = circuit
        self.iter_list: List[StepInfo] = []

    @wraps(BaseEditor.add_instruction)
    def add_instruction(self, instruction: str) -> None:
        """Add an instruction to the circuit."""
        self.netlist.add_instruction(instruction)

    @wraps(BaseEditor.add_instructions)
    def add_instructions(self, *instructions: str) -> None:
        """Add multiple instructions to the circuit."""
        self.netlist.add_instructions(*instructions)

    @wraps(BaseEditor.remove_instruction)
    def remove_instruction(self, instruction: str) -> None:
        """Remove an instruction from the circuit."""
        self.netlist.remove_instruction(instruction)

    @wraps(BaseEditor.remove_x_instruction)
    def remove_x_instruction(self, search_pattern: str) -> None:
        """Remove instructions matching a pattern."""
        self.netlist.remove_x_instruction(search_pattern)

    @wraps(BaseEditor.set_parameters)
    def set_parameters(self, **kwargs: Union[str, int, float]) -> None:
        """Set multiple parameters in the circuit."""
        self.netlist.set_parameters(**kwargs)

    @wraps(BaseEditor.set_parameter)
    def set_parameter(self, param: str, value: Union[str, int, float]) -> None:
        """Set a single parameter in the circuit."""
        self.netlist.set_parameter(param, value)

    @wraps(BaseEditor.set_component_values)
    def set_component_values(self, **kwargs: Union[str, int, float]) -> None:
        """Set multiple component values in the circuit."""
        self.netlist.set_component_values(**kwargs)

    @wraps(BaseEditor.set_component_value)
    def set_component_value(self, device: str, value: Union[str, int, float]) -> None:
        """Set a single component value in the circuit."""
        self.netlist.set_component_value(device, value)

    @wraps(BaseEditor.set_element_model)
    def set_element_model(self, element: str, model: str) -> None:
        """Set the model for a circuit element."""
        self.netlist.set_element_model(element, model)

    def add_param_sweep(self, param: str, iterable: Iterable[Any]) -> None:
        """Adds a dimension to the simulation, where the param is swept."""
        self.iter_list.append(StepInfo("param", param, iterable))

    def add_value_sweep(self, comp: str, iterable: Iterable[Any]) -> None:
        """Adds a dimension to the simulation, where a component value is swept."""
        # The next line raises an ComponentNotFoundError if the component
        # doesn't exist
        _ = self.netlist.get_component_value(comp)
        self.iter_list.append(StepInfo("component", comp, iterable))

    def add_model_sweep(self, comp: str, iterable: Iterable[Any]) -> None:
        """Adds a dimension to the simulation, where a component model is swept."""
        # The next line raises an ComponentNotFoundError if the component
        # doesn't exist
        _ = self.netlist.get_component_value(comp)
        self.iter_list.append(StepInfo("model", comp, iterable))

    def total_number_of_simulations(self) -> int:
        """Returns the total number of simulations foreseen."""
        total = 1
        for step in self.iter_list:
            step_length = len(step)
            if step_length:
                total *= step_length
            else:
                _logger.debug("'%s' is empty.", step)
        return total

    def run_all(
        self,
        callback: Optional[Union[Type[ProcessCallback], Callable[..., Any]]] = None,
        callback_args: Optional[Union[Tuple[Any, ...], Dict[str, Any]]] = None,
        switches: Optional[List[str]] = None,
        *,
        timeout: Optional[float] = None,
        use_loadbias: str = "Auto",
        wait_completion: bool = True,
    ) -> None:
        """Run all simulations defined by the sweeps."""
        assert use_loadbias in (
            "Auto",
            "Yes",
            "No",
        ), "use_loadbias argument must be 'Auto', 'Yes' or 'No'"
        if (
            use_loadbias == "Auto" and self.total_number_of_simulations() > 10
        ) or use_loadbias == "Yes":
            # Use .SAVEBIAS/.LOADBIAS if simulations > 10
            # TODO: Make a first simulation and storing the bias
            pass
        iter_no = 0
        iterators = [iter(step.iter) for step in self.iter_list]
        while True:
            while 0 <= iter_no < len(self.iter_list):
                try:
                    value = next(iterators[iter_no])
                except StopIteration:
                    iterators[iter_no] = iter(self.iter_list[iter_no].iter)
                    iter_no -= 1
                    continue
                if self.iter_list[iter_no].what == "param":
                    self.netlist.set_parameter(self.iter_list[iter_no].elem, value)
                elif self.iter_list[iter_no].what == "component":
                    self.netlist.set_component_value(
                        self.iter_list[iter_no].elem, value
                    )
                elif self.iter_list[iter_no].what == "model":
                    self.netlist.set_element_model(self.iter_list[iter_no].elem, value)
                else:
                    # TODO: develop other types of sweeps EX: add .STEP
                    # instruction
                    raise ValueError("Not Supported sweep")
                iter_no += 1
            if iter_no < 0:
                break
            self.runner.run(
                self.netlist,
                callback=callback,
                callback_args=callback_args,
                switches=switches,
                timeout=timeout,
            )  # Like this a recursion is avoided
            iter_no = (
                len(self.iter_list) - 1
            )  # Resets the counter to start next iteration
        if wait_completion:
            # Now waits for the simulations to end
            self.runner.wait_completion()

    def run(self) -> None:
        """Rather uses run_all instead."""
        self.run_all()

    @property
    def ok_sim(self) -> int:
        """Number of successful simulations."""
        return self.runner.ok_sim

    @property
    def runno(self) -> int:
        """Current run number."""
        return self.runner.runno


if __name__ == "__main__":
    from ..editor.spice_editor import SpiceEditor
    from ..utils.sweep_iterators import sweep_log
    from .sim_runner import SimRunner

    # Correct example for demonstration purposes
    netlist = SpiceEditor("../../tests/DC sweep.asc")
    sim_runner = SimRunner()
    test = SimStepper(netlist, sim_runner)
    # The set_parameter method is decorated with @wraps which causes type checking issues
    # in the test code, but it works correctly at runtime
    netlist.set_parameter("R1", 3)  # Set parameter on the netlist directly
    test.add_param_sweep("res", [10, 11, 9])
    test.add_value_sweep("R1", sweep_log(0.1, 10))
    # test.add_model_sweep("D1", ("model1", "model2"))
    test.run_all()
    print("Finished")
    sys.exit(0)
