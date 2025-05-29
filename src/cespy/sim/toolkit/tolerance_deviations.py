#!/usr/bin/env python
# coding=utf-8
"""Tolerance deviation handling for circuit analysis.

This module provides base classes and utilities for managing component tolerances
and deviations in circuit simulations, supporting both tolerance-based and
min/max deviation types.
"""
from __future__ import annotations

# -------------------------------------------------------------------------------
#
#  ███████╗██████╗ ██╗ ██████╗███████╗██╗     ██╗██████╗
#  ██╔════╝██╔══██╗██║██╔════╝██╔════╝██║     ██║██╔══██╗
#  ███████╗██████╔╝██║██║     █████╗  ██║     ██║██████╔╝
#  ╚════██║██╔═══╝ ██║██║     ██╔══╝  ██║     ██║██╔══██╗
#  ███████║██║     ██║╚██████╗███████╗███████╗██║██████╔╝
#  ╚══════╝╚═╝     ╚═╝ ╚═════╝╚══════╝╚══════╝╚═╝╚═════╝
#
# Name:        montecarlo.py
# Purpose:     Classes to automate Monte-Carlo simulations
#
# Author:      Nuno Brum (nuno.brum@gmail.com)
#
# Created:     10-08-2023
# Licence:     refer to the LICENSE file
# -------------------------------------------------------------------------------
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    Iterator,
    List,
    Optional,
    Tuple,
    Type,
    Union,
    cast,
)

from ...editor.base_editor import BaseEditor, scan_eng
from ...log.logfile_data import LogfileData, LTComplex
from ..run_task import RunTask
from ..sim_runner import AnyRunner, ProcessCallback
from .sim_analysis import SimAnalysis


class DeviationType(Enum):
    """Enum to define the type of deviation."""

    tolerance = "tolerance"
    minmax = "minmax"
    none = "none"


@dataclass
class ComponentDeviation:
    """Class to store the deviation of a component."""

    max_val: float
    min_val: float = 0.0
    typ: DeviationType = DeviationType.tolerance
    distribution: str = "uniform"

    @classmethod
    def from_tolerance(
        cls, tolerance: float, distribution: str = "uniform"
    ) -> ComponentDeviation:
        """Create a ComponentDeviation from a tolerance value.
        
        Args:
            tolerance: Tolerance value (e.g., 0.1 for ±10%).
            distribution: Distribution type ('uniform' or 'normal').
            
        Returns:
            A ComponentDeviation instance.
        """
        return cls(tolerance, -tolerance, DeviationType.tolerance, distribution)

    @classmethod
    def from_min_max(
        cls, min_val: float, max_val: float, distribution: str = "uniform"
    ) -> ComponentDeviation:
        """Create a ComponentDeviation from min/max values.
        
        Args:
            min_val: Minimum value.
            max_val: Maximum value.
            distribution: Distribution type ('uniform' or 'normal').
            
        Returns:
            A ComponentDeviation instance.
        """
        return cls(min_val, max_val, DeviationType.minmax, distribution)

    @classmethod
    def none(cls) -> ComponentDeviation:
        """Create a ComponentDeviation with no deviation.
        
        Returns:
            A ComponentDeviation instance with zero deviation.
        """
        return cls(0.0, 0.0, DeviationType.none)


@dataclass
class TestbenchState:
    """Groups testbench-related state flags."""
    prepared: bool = False
    executed: bool = False
    analysis_executed: bool = False
    last_run_number: int = 0


class ToleranceDeviations(SimAnalysis, ABC):
    """Class to automate Monte-Carlo simulations."""

    devices_with_deviation_allowed = ("R", "C", "L", "V", "I")

    def __init__(
        self,
        circuit_file: Union[str, BaseEditor],
        runner: Optional[AnyRunner] = None,
    ):
        super().__init__(circuit_file, runner)
        self.default_tolerance = {
            prefix: ComponentDeviation.none()
            for prefix in self.devices_with_deviation_allowed
        }
        self.device_deviations: Dict[str, ComponentDeviation] = {}
        self.parameter_deviations: Dict[str, ComponentDeviation] = {}
        self.testbench = TestbenchState()
        self.simulation_results: Dict[str, Any] = {}
        self.elements_analysed: List[str] = []

    def reset_tolerances(self) -> None:
        """Clears all the settings for the simulation."""
        self.device_deviations.clear()
        self.parameter_deviations.clear()
        self.testbench.prepared = False
        self.testbench.last_run_number = 0

    def clear_simulation_data(self) -> None:
        """Clears the data from the simulations."""
        super().clear_simulation_data()
        self.simulation_results.clear()
        self.testbench.analysis_executed = False

    def set_tolerance(
        self, ref: str, new_tolerance: float, distribution: str = "uniform"
    ) -> None:
        """Sets the tolerance for a given component.

        If only the prefix is given, the tolerance is set for all. The valid prefixes
        that can be used are: R, C, L, V, I
        """
        if ref in self.devices_with_deviation_allowed:  # Only the prefix is given
            self.default_tolerance[ref] = ComponentDeviation.from_tolerance(
                new_tolerance, distribution
            )
        else:
            if ref in self.editor.get_components(ref[0]):
                self.device_deviations[ref] = ComponentDeviation.from_tolerance(
                    new_tolerance, distribution
                )

    def set_tolerances(
        self, new_tolerances: Dict[str, float], distribution: str = "uniform"
    ) -> None:
        """Sets the tolerances for a set of components.

        The dictionary keys are the references and the values are the tolerances. If
        only the prefix is given, the tolerance is set for all components with that
        prefix. See set_tolerance method.
        """
        for ref, tol in new_tolerances.items():
            self.set_tolerance(ref, tol, distribution)

    def set_deviation(
        self,
        ref: str,
        min_val: float,
        max_val: float,
        distribution: str = "uniform",
    ) -> None:
        """Sets the deviation for a given component.

        This establishes a min and max value for the component. Optionally a
        distribution can be specified. The valid distributions are: uniform or normal
        (gaussian).
        """
        self.device_deviations[ref] = ComponentDeviation.from_min_max(
            min_val, max_val, distribution
        )

    def get_components(self, prefix: str) -> Iterable[str]:
        """Get all components with the given prefix that can have deviations.
        
        Args:
            prefix: Component prefix (e.g., 'R', 'C', 'L') or '*' for all allowed types.
            
        Returns:
            An iterable of component references.
        """
        if prefix == "*":
            return (
                cmp
                for cmp in self.editor.get_components()
                if cmp[0] in self.devices_with_deviation_allowed
            )
        return self.editor.get_components(prefix)

    def get_component_value_deviation_type(
        self, ref: str
    ) -> Tuple[Union[str, float], ComponentDeviation]:
        """Get the value and deviation type for a component.
        
        Args:
            ref: Component reference (e.g., 'R1', 'C2').
            
        Returns:
            A tuple containing (component_value, deviation_info).
            
        Raises:
            ValueError: If the reference is not a valid component type.
        """
        if ref[0] not in self.devices_with_deviation_allowed:
            raise ValueError("The reference must be a valid component type")
        value = self.editor.get_component_value(ref)
        if len(value) == 0:  # This covers empty strings
            return value, ComponentDeviation.none()
        # The value needs to be able to be computed, otherwise it can't be used
        try:
            value_float = scan_eng(value)
            return value_float, self.device_deviations.get(
                ref,
                self.default_tolerance.get(ref[0], ComponentDeviation.none()),
            )
        except ValueError:
            return value, ComponentDeviation.none()

    def set_parameter_deviation(
        self,
        ref: str,
        min_val: float,
        max_val: float,
        distribution: str = "uniform",
    ) -> None:
        """Set the deviation range for a parameter.
        
        Args:
            ref: Parameter reference name.
            min_val: Minimum value.
            max_val: Maximum value.
            distribution: Distribution type ('uniform' or 'normal').
        """
        self.parameter_deviations[ref] = ComponentDeviation.from_min_max(
            min_val, max_val, distribution
        )

    def get_parameter_value_deviation_type(
        self, param: str
    ) -> Tuple[Any, ComponentDeviation]:
        """Get the value and deviation type for a parameter.
        
        Args:
            param: Parameter name.
            
        Returns:
            A tuple containing (parameter_value, deviation_info).
        """
        value = self.editor.get_parameter(param)
        return value, self.parameter_deviations[param]

    def save_netlist(self, filename: str) -> None:
        """Save the netlist to a file, preparing the testbench if necessary.
        
        Args:
            filename: The path to save the netlist to.
        """
        if self.testbench.prepared is False:
            self.prepare_testbench()
        super().save_netlist(filename)

    def _reset_netlist(self) -> None:
        """Reset the netlist to its original state and mark testbench as unprepared."""
        super()._reset_netlist()
        self.testbench.prepared = False

    @abstractmethod
    def prepare_testbench(self, **kwargs: Any) -> None:
        """Prepare the testbench for simulation.
        
        This abstract method must be implemented by subclasses to set up
        the specific testbench configuration for the analysis type.
        
        Args:
            **kwargs: Analysis-specific keyword arguments.
        """
        raise NotImplementedError("Subclasses must implement prepare_testbench")

    # pylint: disable=too-many-arguments
    def run_testbench(
        self,
        *,
        runs_per_sim: int = 512,
        wait_resource: bool = True,
        callback: Optional[Union[Type[ProcessCallback], Callable[..., Any]]] = None,
        callback_args: Optional[Union[Tuple[Any, ...], Dict[str, Any]]] = None,
        switches: Optional[List[str]] = None,
        timeout: Optional[float] = None,
        run_filename: Optional[str] = None,
        exe_log: bool = False,
    ) -> Optional[Iterator[Any]]:
        """Run the simulation testbench with specified parameters.

        :param runs_per_sim: Maximum number of runs per simulation. If the number of
            runs is higher than this number, the simulation is split in multiple runs.
        :param wait_resource: If True, the simulation will wait for the resource to be
            available. If False, the simulation will be queued and the method will
            return immediately.
        :param callback: A callback function to be called when the simulation is
            completed. The callback function must accept a single argument, which is the
            simulation object.
        :param callback_args: A tuple or dictionary with the arguments to be passed to
            the callback function.
        :param switches: A list of switches to be passed to the simulator.
        :param timeout: A timeout in seconds. If the simulation is not completed in this
            time, it will be aborted.
        :param run_filename: The name of the file to be used for the simulation. If
            None, a temporary file will be used.
        :param exe_log: Sends the execution log_file to a file "netlist_name.exe.log".
        :return: The callback returns of every batch if a callback function is given.
            Otherwise, None.
        """
        if self.testbench.prepared is False:
            super()._reset_netlist()
            self.play_instructions()
            self.prepare_testbench()
        else:
            self.play_instructions()
        self.editor.remove_instruction(
            f".step param run -1 {self.testbench.last_run_number} 1"
        )  # removes this instruction
        self.clear_simulation_data()
        # calculate the ideal number of runs per simulation to avoid orphan
        # runs. This is to avoid having a simulation
        # with only one run. Which poses a problem for .step instruction
        total_number_of_runs = (
            self.testbench.last_run_number + 2
        )  # the +2 is to account for the run -1 and the last run
        runs_per_sim = min(runs_per_sim, total_number_of_runs)
        while total_number_of_runs % runs_per_sim == 1:  # Avoid orphan runs
            runs_per_sim += 1

        for sim_no in range(-1, self.testbench.last_run_number + 1, runs_per_sim):
            last_no = sim_no + runs_per_sim - 1
            last_no = min(last_no, self.testbench.last_run_number)

            run_stepping = f".step param run {sim_no} {last_no} 1"
            self.editor.add_instruction(run_stepping)
            # Check if AnyRunner.run supports exe_log parameter, if not, remove it
            # This is a workaround for compatibility with older versions
            sim = None
            try:
                # Try with all parameters first
                sim = self.runner.run(
                    self.editor,
                    wait_resource=wait_resource,
                    callback=callback,
                    callback_args=callback_args,
                    switches=switches,
                    timeout=timeout,
                    run_filename=run_filename,
                    exe_log=exe_log,
                )
            except (TypeError, ValueError):
                # Try without exe_log
                try:
                    sim = self.runner.run(
                        self.editor,
                        wait_resource=wait_resource,
                        callback=callback,
                        callback_args=callback_args,
                        switches=switches,
                        timeout=timeout,
                        run_filename=run_filename,
                    )
                except (TypeError, ValueError):
                    # If that also fails, try with minimal parameters
                    sim = self.runner.run(
                        self.editor,
                        wait_resource=wait_resource,
                    )

            if sim is not None:
                self.simulations.append(sim)
            self.editor.remove_instruction(run_stepping)

        self.runner.wait_completion()
        if callback is not None:
            return (
                sim.get_results() if sim is not None else None
                for sim in self.simulations
                if sim is not None
            )
        self.testbench.executed = True
        return None

    def add_log(self, run_task: RunTask) -> Optional[LogfileData]:
        """Reads a log file and adds it to the simulation_results.

        It does so making sure that the run number is correctly set.
        """
        if run_task.retcode != 0:
            return None

        log_results = self.read_logfile(run_task)
        if log_results is None:
            return None

        # Safely check and process stepset and dataset attributes
        if not (hasattr(log_results, "stepset") and hasattr(log_results, "dataset")):
            return self.log_data.update(log_results)
        
        stepset = getattr(log_results, "stepset", {})
        dataset = getattr(log_results, "dataset", {})

        if len(stepset) > 0:
            return self.log_data.update(log_results)
            
        # Handle empty stepset
        if "run" in dataset and len(dataset["run"]) > 0:
            if isinstance(dataset["run"][0], LTComplex):
                log_results.stepset = {
                    "run": [round(val.real) for val in dataset["run"]]
                }
            else:
                log_results.stepset = {"run": dataset["run"]}
        elif dataset and len(dataset) > 0:
            # auto assign a step starting from 0 and incrementing by 1
            # will use the size of the first element found in the dataset
            any_meas = next(iter(dataset.values()))

            # Safely access self.log_data.stepset
            run_start = 0
            if hasattr(self.log_data, "stepset"):
                stepset_data = getattr(self.log_data, "stepset", {})
                if "run" in stepset_data and len(stepset_data["run"]) > 0:
                    run_start = stepset_data["run"][-1] + 1

            log_results.stepset = {
                "run": list(range(run_start, run_start + len(any_meas)))
            }

        # Set step_count if stepset exists and log_results has that attribute
        if hasattr(log_results, "stepset") and hasattr(log_results, "step_count"):
            log_results.step_count = len(log_results.stepset)

        self.add_log_data(log_results)
        return log_results

    def read_logfiles(self) -> LogfileData:
        """Returns the logdata for the simulations."""
        if self.testbench.analysis_executed is False and self.testbench.executed is False:
            raise RuntimeError("The analysis has not been executed yet")

        if "log_data" in self.simulation_results:
            return cast(LogfileData, self.simulation_results["log_data"])

        super().read_logfiles()
        # The code below makes the run measure (if it exists) available on the stepset.
        # Note: this was only tested with LTSpice
        if hasattr(self.log_data, "stepset") and len(self.log_data.stepset) == 0:
            if hasattr(self.log_data, "dataset"):
                dataset = self.log_data.dataset
                if "runm" in dataset and len(dataset["runm"]) > 0:
                    if isinstance(dataset["runm"][0], LTComplex):
                        self.log_data.stepset = {
                            "run": [round(val.real) for val in dataset["runm"]]
                        }
                    else:
                        self.log_data.stepset = {"run": dataset["runm"]}
                else:
                    # auto assign a step starting from 0 and incrementing by 1
                    # will use the size of the first element found in the
                    # dataset
                    if dataset and len(dataset) > 0:
                        any_meas = next(iter(dataset.values()))
                        self.log_data.stepset = {"run": list(range(len(any_meas)))}

                if hasattr(self.log_data, "step_count"):
                    self.log_data.step_count = len(self.log_data.stepset)

        self.simulation_results["log_data"] = self.log_data
        return self.log_data

    @abstractmethod
    # pylint: disable=too-many-positional-arguments
    def run_analysis(
        self,
        callback: Optional[Union[Type[ProcessCallback], Callable[..., Any]]] = None,
        callback_args: Optional[Union[Tuple[Any, ...], Dict[str, Any]]] = None,
        switches: Optional[List[str]] = None,
        timeout: Optional[float] = None,
        exe_log: bool = True,
        measure: Optional[str] = None,
    ) -> Optional[
        Tuple[
            float,
            float,
            Dict[str, Union[str, float]],
            float,
            Dict[str, Union[str, float]],
        ]
    ]:
        """Run the tolerance analysis.
        
        This abstract method must be implemented by subclasses to perform the actual
        tolerance/sensitivity analysis. The override should set
        self.testbench.analysis_executed to True.
        
        Args:
            callback: Optional callback function to process results.
            callback_args: Arguments to pass to the callback function.
            switches: Command line switches for the simulator.
            timeout: Timeout for each simulation run.
            exe_log: Whether to log simulator execution output.
            measure: Name of the measurement to analyze.
            
        Returns:
            Optional tuple with analysis results, format depends on the specific analysis type.
        """
