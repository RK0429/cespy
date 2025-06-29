#!/usr/bin/env python
# coding=utf-8
"""Fast worst-case analysis implementation for circuit simulations.

This module provides an optimized algorithm for worst-case analysis that reduces
the number of simulations needed by intelligently determining component impacts
and skipping unnecessary simulation combinations.
"""
# -------------------------------------------------------------------------------
#
#  ███████╗██████╗ ██╗ ██████╗███████╗██╗     ██╗██████╗
#  ██╔════╝██╔══██╗██║██╔════╝██╔════╝██║     ██║██╔══██╗
#  ███████╗██████╔╝██║██║     █████╗  ██║     ██║██████╔╝
#  ╚════██║██╔═══╝ ██║██║     ██╔══╝  ██║     ██║██╔══██╗
#  ███████║██║     ██║╚██████╗███████╗███████╗██║██████╔╝
#  ╚══════╝╚═╝     ╚═╝ ╚═════╝╚══════╝╚══════╝╚═╝╚═════╝
#
# Name:        fast_worst_case.py
# Purpose:     Class to automate Worst-Case simulations (Faster Algorithm)
#
# Author:      Nuno Brum (nuno.brum@gmail.com)
#
# Created:     04-11-2023
# Licence:     refer to the LICENSE file
# -------------------------------------------------------------------------------

import logging
from enum import IntEnum
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Union, cast

from ..process_callback import ProcessCallback
from .tolerance_deviations import ComponentDeviation, DeviationType
from .worst_case import WorstCaseAnalysis

_logger = logging.getLogger("cespy.SimAnalysis")


class WorstCaseType(IntEnum):
    """Enumeration for worst case analysis types."""

    nom = 0
    max = 1
    min = 2


class FastWorstCaseAnalysis(WorstCaseAnalysis):
    """This class implements a faster algorithm to perform a worst case analysis. The
    typical worst case analysis makes all possible combinations of the components that
    have a deviation. This means that if there are 10 components with a deviation, there
    will be 1024 simulations to be performed. The number of simulations grows
    exponentially with the number of components with deviation.

    This algorithm speeds up the process, by determining the impact of each component
    with deviation on the final result and skipping simulations that are not necessary.
    The algorithm is as follows:

    1. Make a sensitivity analysis to determine the impact that each component has on
    the final result.

    2. Based on the information collected on 1. set all the components with deviation
    achieve a maximum on the final result. Components are set based on the assumption
    that the system is reaction is to each component is monotonic. That is, if
    increasing the component value, increases the final result, then the component is
    set to the maximum value. If decreasing the component value increases the final
    result, then the component is set to the minimum value.

    3. Validate the assumption based on 2. by making a series of test simulations
    setting each component with their opposite value. If the result is lower, then the
    assumption is correct. If the result is higher, then the assumption is wrong and the
    component is set to the opposite value.

    4. Repeat 2. but this time trying to achieve a minimum on the final result.

    5. Repeat step 3. but this time trying to achieve a minimum on the final result.

    Like in the Worst-Case and Montecarlo, there are two approaches to make this
    analysis. Either preparing a testbench where component variations are managed by the
    simulator, or by ordering each simulation individually. In the testbench method all
    component values are replaced by formulas that depend on a .STEP PARAM run, and then
    run_testbench() will make all the manipulations of the run variable.

    In the latter, each component value is set individually. This is done by calling the
    run_analysis() method.
    """

    # pylint: disable=too-many-arguments
    def run_testbench(
        self,
        *,
        runs_per_sim: Optional[int] = None,  # This parameter is ignored
        wait_resource: bool = True,  # This parameter is ignored
        callback: Optional[Union[Type[ProcessCallback], Callable[..., Any]]] = None,
        callback_args: Optional[Union[Tuple[Any, ...], Dict[str, Any]]] = None,
        switches: Optional[List[str]] = None,
        timeout: Optional[float] = None,
        run_filename: Optional[str] = None,
        exe_log: bool = False,
    ) -> None:
        raise NotImplementedError("run_testbench() is not implemented in this class")

    # pylint: disable=too-many-positional-arguments,too-many-locals
    # pylint: disable=too-many-branches,too-many-statements,too-many-return-statements
    def run_analysis(
        self,
        callback: Optional[Union[Type[ProcessCallback], Callable[..., Any]]] = None,
        callback_args: Optional[Union[Tuple[Any, ...], Dict[str, Any]]] = None,
        switches: Optional[List[str]] = None,
        timeout: Optional[float] = None,
        exe_log: bool = True,
        measure: Optional[str] = None,
    ) -> Tuple[
        float,
        float,
        Dict[str, Union[str, float]],
        float,
        Dict[str, Union[str, float]],
    ]:
        """As described in the class description, this method will perform a worst case
        analysis using a faster algorithm."""
        assert measure is not None, "The measure argument must be defined"

        self.clear_simulation_data()
        self.elements_analysed.clear()
        worst_case_elements = {}

        def check_and_add_component(ref1: str) -> None:
            val1, dev1 = self.get_component_value_deviation_type(
                ref1
            )  # get there present value
            if dev1.min_val == dev1.max_val or dev1.typ == DeviationType.NONE:
                return
            worst_case_elements[ref1] = val1, dev1, "component"
            self.elements_analysed.append(ref1)

        def value_change(
            val: Union[str, float], dev: ComponentDeviation, to: WorstCaseType
        ) -> Union[str, float]:
            """Sets the reference component to the maximum or minimum based on deviation type."""
            if isinstance(val, str):
                return val
            # val is now float
            if dev.typ == DeviationType.TOLERANCE:
                if to == WorstCaseType.max:
                    return val * (1 + dev.max_val)
                if to == WorstCaseType.min:
                    return val * (1 - dev.max_val)
                return val
            if dev.typ == DeviationType.MINMAX:
                if to == WorstCaseType.max:
                    return dev.max_val
                if to == WorstCaseType.min:
                    return dev.min_val
                return val
            _logger.warning("Unknown deviation type")
            return val

        def set_ref_to(ref: str, to: WorstCaseType) -> None:
            val, dev, typ = worst_case_elements[ref]
            new_val = value_change(val, dev, to)
            if typ == "component":
                self.editor.set_component_value(ref, new_val)  # update the value
            elif typ == "parameter":
                self.editor.set_parameter(ref, new_val)
            else:
                _logger.warning("Unknown type")

        def run_and_get_measure() -> float:
            # Run the simulation
            # Prepare callbacks and timeouts
            actual_callback = (
                callback if callback is not None else lambda: None
            )  # default no-op callable
            actual_callback_args = callback_args if callback_args is not None else ()
            actual_timeout = timeout if timeout is not None else 0.0  # default timeout

            task = self.run(
                wait_resource=True,
                callback=actual_callback,
                callback_args=actual_callback_args,
                switches=switches,
                timeout=actual_timeout,
                exe_log=exe_log,
            )
            assert task is not None
            self.wait_completion()
            # Get the results from the simulation
            log_data = self.add_log(task)
            assert log_data is not None
            return cast(float, log_data.get_measure_value(measure))

        for ref in self.device_deviations:
            check_and_add_component(ref)

        for ref in self.parameter_deviations:
            val, dev = self.get_parameter_value_deviation_type(ref)
            if dev.typ in (DeviationType.TOLERANCE, DeviationType.MINMAX):
                worst_case_elements[ref] = val, dev, "parameter"
                self.elements_analysed.append(ref)

        for prefix in self.default_tolerance:
            for ref in self.get_components(prefix):
                if ref not in self.device_deviations:
                    check_and_add_component(ref)

        _logger.info(
            "Worst Case Analysis: %d elements to be analysed",
            len(self.elements_analysed),
        )

        # Prepare callbacks and timeouts for all run calls
        actual_callback = (
            callback if callback is not None else lambda: None
        )  # default no-op callable
        actual_callback_args = callback_args if callback_args is not None else ()
        actual_timeout = timeout if timeout is not None else 0.0  # default timeout

        self._reset_netlist()  # reset the netlist
        self.play_instructions()  # play the instructions
        # Simulate the nominal case
        self.run(
            wait_resource=True,
            callback=actual_callback,
            callback_args=actual_callback_args,
            switches=switches,
            timeout=actual_timeout,
            exe_log=exe_log,
        )

        # Sequence a change of a component value at a time, setting it to the
        # maximum value
        for ref in self.elements_analysed:
            set_ref_to(ref, WorstCaseType.max)
            # Run the simulation
            self.run(
                wait_resource=True,
                callback=actual_callback,
                callback_args=actual_callback_args,
                switches=switches,
                timeout=actual_timeout,
                exe_log=exe_log,
            )
        self.wait_completion()
        # Need to set this to True, so that the next step can be executed
        self.testbench.analysis_executed = True
        self.testbench.executed = True  # Idem
        # Get the results from the simulation
        log_data = self.read_logfiles()
        nominal = cast(float, log_data.get_measure_value(measure, 0))
        _logger.info("Nominal value: %g", nominal)
        component_deltas = {}
        idx = 1
        new_measure = last_measure = nominal
        for ref in self.elements_analysed:
            new_measure = cast(float, log_data.get_measure_value(measure, idx))
            component_deltas[ref] = new_measure - last_measure
            last_measure = new_measure
            _logger.info("Component %s: %g", ref, component_deltas[ref])
            idx += 1
        # Check which components have a positive impact on the final result,
        # that is, increasing the component value increases the final result
        max_setting = {ref: component_deltas[ref] > 0 for ref in component_deltas}

        # Set all components with a positive impact to the maximum value and
        # all components with a negative impact to the minimum value
        component_changed = False
        for ref, is_max in max_setting.items():
            if not is_max:  # Set the negative impact components to the minimum value
                set_ref_to(ref, WorstCaseType.min)
                component_changed = True

        if component_changed:
            # Run the simulation
            # This is the expected maximum
            max_value = run_and_get_measure()
            idx += 1
        else:
            max_value = new_measure

        # Check if the assumption is correct. Cycling each component to its
        # opposite value
        iterator = iter(self.elements_analysed)
        while True:
            try:
                ref = next(iterator)
            except StopIteration:
                break
            if max_setting[
                ref
            ]:  # Set the negative impact components to the minimum value
                set_ref_to(ref, WorstCaseType.min)
            else:
                set_ref_to(ref, WorstCaseType.max)
            # Run the simulation
            new_value = run_and_get_measure()
            idx += 1

            if new_value > max_value:
                # The assumption is wrong, so the component is set to the
                # minimum value
                max_setting[ref] = not max_setting[ref]
                max_value = new_value
                # Need to restart the cycle
                iterator = iter(self.elements_analysed)

            # setting it back to the maximum value
            if max_setting[ref]:
                set_ref_to(ref, WorstCaseType.max)
            else:
                set_ref_to(ref, WorstCaseType.min)

        # Now determining the minimum value: Assuming the opposite of the maximum
        # setting
        min_setting = {ref: not max_setting[ref] for ref in max_setting}

        # Set the component back to their opposite value
        for ref in self.elements_analysed:
            if min_setting[ref]:
                set_ref_to(ref, WorstCaseType.max)
            else:
                set_ref_to(ref, WorstCaseType.min)

        # Run the simulation
        # This is the expected minimum of the final result
        min_value = run_and_get_measure()
        idx += 1

        # Check if the assumption is correct. Cycling each component to its
        # opposite value
        iterator = iter(self.elements_analysed)
        while True:
            try:
                ref = next(iterator)
            except StopIteration:
                break
            if min_setting[ref]:
                set_ref_to(ref, WorstCaseType.min)
            else:
                set_ref_to(ref, WorstCaseType.max)
            # Run the simulation
            new_value = run_and_get_measure()
            idx += 1
            # This is the expected maximum of the final result
            if new_value < min_value:
                # The assumption is wrong, so the component is set to the
                # minimum value
                min_setting[ref] = not min_setting[ref]
                min_value = new_value
                # Need to restart the cycle
                iterator = iter(self.elements_analysed)

            # setting it back to the previous value
            if min_setting[ref]:
                set_ref_to(ref, WorstCaseType.max)
            else:
                set_ref_to(ref, WorstCaseType.min)

        # Now that we have the maximum and minimum values, we can set the
        # components to the nominal value
        min_comp_values = {}
        max_comp_values = {}
        for ref in self.elements_analysed:
            val, dev, _ = worst_case_elements[ref]
            if min_setting[ref]:
                min_comp_values[ref] = value_change(val, dev, WorstCaseType.max)
            else:
                min_comp_values[ref] = value_change(val, dev, WorstCaseType.min)

            if max_setting[ref]:
                max_comp_values[ref] = value_change(val, dev, WorstCaseType.max)
            else:
                max_comp_values[ref] = value_change(val, dev, WorstCaseType.min)

        self.clear_simulation_data()
        self.cleanup_files()
        self._reset_netlist()
        self.play_instructions()

        return nominal, min_value, max_comp_values, max_value, min_comp_values
