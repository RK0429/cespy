#!/usr/bin/env python
# coding=utf-8
"""Monte Carlo simulation analysis for circuit components.

This module provides classes to perform Monte Carlo simulations where component
values are replaced by random distributions (gaussian or uniform), enabling
statistical analysis of circuit behavior under component variations.
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
# Name:        montecarlo.py
# Purpose:     Classes to automate Monte-Carlo simulations
#
# Author:      Nuno Brum (nuno.brum@gmail.com)
#
# Created:     10-08-2023
# Licence:     refer to the LICENSE file
# -------------------------------------------------------------------------------

import logging
import random
from typing import Any, Callable, Dict, Optional, Tuple, Type, Union

from ...log.logfile_data import LogfileData
from ..process_callback import ProcessCallback
from .tolerance_deviations import ComponentDeviation, DeviationType, ToleranceDeviations

_logger = logging.getLogger("cespy.SimAnalysis")


class Montecarlo(ToleranceDeviations):
    """Class to automate Montecarlo simulations, where component values and parameters
    are replaced by a random distribution (either a gaussian or a uniform distribution).

    This is a statistical method, hence, it needs a considerable number of simulations
    to achieve a final gaussian distribution in order to apply this method. If the
    number of parameters and component values is low, it is better to use a Worst-Case
    approach.

    Like the Worst-Case and Sensitivity analysis, there are two possible approaches to
    use this class:

    Class to automate Worst-Case simulations, where all possible combinations of maximum
    and minimums possible values of component values and parameters are done.

    It is advised to use this algorithm when the number of parameters to be varied is
    reduced. Typically less than 10 or 12. A higher number will translate into a huge
    number of simulations. For more than 1000 simulations, it is better to use a
    statistical method such as the Montecarlo.

    Like the Worst-Case and Sensitivity analysis, there are two possible approaches to
    use this class:

    1. Preparing a testbench where all combinations are managed directly by the
    simulator, replacing  parameters and component values by formulas and using a .STEP
    primitive to cycle through all possible  combinations.

    2. Launching each simulation separately where the running python script manages all
    parameter value variations.

    The first approach is normally faster, but not possible in all simulators. The
    second approach is a valid backup when every single simulation takes too long, or
    when it is prone to crashes and stalls.
    """

    # pylint: disable=too-many-branches,too-many-statements
    def prepare_testbench(self, **kwargs: Any) -> None:
        """Prepares the simulation by setting the tolerances for the components :keyword
        num_runs: Number of runs to be performed.

        Default is 1000.
        :return: Nothing
        """
        min_max_uni_func = False
        min_max_norm_func = False
        tol_uni_func = False
        tol_norm_func = False
        self.elements_analysed.clear()
        for ref in self.get_components("*"):
            val, dev = self.get_component_value_deviation_type(
                ref
            )  # get there present value
            new_val = val
            if dev.typ == DeviationType.TOLERANCE:
                tolstr = f"{dev.max_val:g}".rstrip("0").rstrip(".")
                if dev.distribution == "uniform":
                    new_val = f"{{utol({val},{tolstr})}}"  # calculate expression for new value
                    tol_uni_func = True
                elif dev.distribution == "normal":
                    new_val = f"{{ntol({val},{tolstr})}}"
                    tol_norm_func = True
            elif dev.typ == DeviationType.MINMAX:
                if dev.distribution == "uniform":
                    new_val = "{urng(%s, %s,%s)}" % (
                        val,
                        dev.min_val,
                        dev.max_val,
                    )  # calculate expression for new value
                    min_max_uni_func = True
                elif dev.distribution == "normal":
                    new_val = "{nrng(%s,%s,%s)}" % (
                        val,
                        dev.min_val,
                        dev.max_val,
                    )
                    min_max_norm_func = True

            if new_val != val:  # Only update the value if it has changed
                assert isinstance(new_val, str)
                self.set_component_value(ref, new_val)  # update the value
                self.elements_analysed.append(ref)

        for param in self.parameter_deviations:
            val, dev = self.get_parameter_value_deviation_type(param)
            new_val = val
            if dev.typ == DeviationType.TOLERANCE:
                if dev.distribution == "uniform":
                    new_val = "{utol(%s,%s)}" % (val, dev.max_val)
                    tol_uni_func = True
                elif dev.distribution == "normal":
                    new_val = "{ntol(%s,%s)}" % (val, dev.max_val)
                    tol_norm_func = True
            elif dev.typ == DeviationType.MINMAX:
                if dev.distribution == "uniform":
                    new_val = "{urng(%s,%s,%s)}" % (
                        val,
                        (dev.max_val + dev.min_val) / 2,
                        (dev.max_val - dev.min_val) / 2,
                    )
                    min_max_uni_func = True
                elif dev.distribution == "normal":
                    new_val = "{nrng(%s,%s,%s)}" % (
                        val,
                        (dev.max_val + dev.min_val) / 2,
                        (dev.max_val - dev.min_val) / 6,
                    )
                    min_max_norm_func = True
            else:
                continue
            self.editor.set_parameter(param, new_val)
            self.elements_analysed.append(param)

        simulator = getattr(self.runner, "simulator", None)
        sim_name = getattr(simulator, "__name__", None)
        if sim_name == "LTspice":
            if tol_uni_func:
                self.editor.add_instruction(
                    ".func utol(nom,tol) if(run<0, nom, mc(nom,tol))"
                )

            if tol_norm_func:
                self.editor.add_instruction(
                    ".func ntol(nom,tol) if(run<0, nom, nom*(1+gauss(tol/3)))"
                )

            if min_max_uni_func:
                self.editor.add_instruction(
                    ".func urng(nom,mean,df2) if(run<0, nom, mean+flat(df2))"
                )

            if min_max_norm_func:
                self.editor.add_instruction(
                    ".func nrng(nom,mean,df6) if(run<0, nom, mean*(1+gauss(df6)))"
                )
        elif sim_name == "Qspice":
            # if gauss function is needed
            #  => This is finally not needed because Qspice has a built-in
            #     gauss function (non-documented)
            # if tol_norm_func or min_max_norm_func:
            #   self.editor.add_instruction(
            #       ".func random_not0() {(random()+1e-7)/(1+1e-7)}")
            #   self.editor.add_instruction(
            #       ".func gauss(sigma) {sqrt(-2*ln(random_not0()))*cos(2*pi*random())*sigma}")
            if tol_uni_func:
                self.editor.add_instruction(
                    ".func utol(nom,tol) {if(run<0, nom, nom*(1+tol*(2*random()-1)))}"
                )

            if tol_norm_func:
                self.editor.add_instruction(
                    ".func ntol(nom,tol) {if(run<0, nom, nom*(1+gauss(tol/3)))}"
                )

            if min_max_uni_func:
                self.editor.add_instruction(
                    ".func urng(nom,mean,df2) if(run<0, nom, mean+(df2*(2*random()-1))"
                )

            if min_max_norm_func:
                self.editor.add_instruction(
                    ".func nrng(nom,mean,df6) if(run<0, nom, mean*(1+gauss(df6)))"
                )
        else:
            _logger.warning("Simulator not supported for this method")
            raise NotImplementedError("Simulator not supported for this method")

        self.last_run_number = kwargs.get(
            "num_runs",
            self.last_run_number if self.last_run_number != 0 else 1000,
        )
        self.editor.add_instruction(f".step param run -1 {self.last_run_number} 1")
        self.editor.set_parameter("run", -1)
        self.testbench.prepared = True

    @staticmethod
    def _get_sim_value(value: float, dev: ComponentDeviation) -> float:
        """Returns a new value for the simulation."""
        new_val = value
        if dev.typ == DeviationType.TOLERANCE:
            if dev.distribution == "uniform":
                new_val = random.Random().uniform(
                    value * (1 - dev.max_val), value * (1 + dev.max_val)
                )
            elif dev.distribution == "normal":
                new_val = random.Random().gauss(value, dev.max_val / 3)
        elif dev.typ == DeviationType.MINMAX:
            if dev.distribution == "uniform":
                new_val = random.Random().uniform(dev.min_val, dev.max_val)
            elif dev.distribution == "normal":
                new_val = random.Random().gauss(
                    (dev.max_val + dev.min_val) / 2,
                    (dev.max_val - dev.min_val) / 6,
                )
        elif dev.typ == DeviationType.NONE:
            pass
        else:
            _logger.warning("Unknown deviation type")
        return new_val

    # pylint: disable=too-many-positional-arguments
    def run_analysis(
        self,
        callback: Optional[Union[Type[ProcessCallback], Callable[..., Any]]] = None,
        callback_args: Optional[Union[Tuple[Any, ...], Dict[str, Any]]] = None,
        switches: Optional[list[str]] = None,
        timeout: Optional[float] = None,
        exe_log: bool = True,
        measure: Optional[str] = None,
        num_runs: int = 1000,
    ) -> None:
        """This method runs the analysis without updating the netlist.

        It will update component values and parameters according to their deviation type
        and call the simulation. The advantage of this method is that it doesn't require
        adding random functions to the netlist. The number of times the simulation is
        done is specified on the argument num_runs.
        """
        self.elements_analysed.clear()
        self.clear_simulation_data()
        for _ in range(num_runs):
            self._reset_netlist()  # reset the netlist
            self.play_instructions()  # play the instructions
            # Preparing the variation on components
            for ref in self.get_components("*"):
                val, dev = self.get_component_value_deviation_type(ref)
                if isinstance(val, float):
                    new_val = self._get_sim_value(val, dev)
                    if new_val != val:
                        self.editor.set_component_value(ref, new_val)
            # Preparing the variation on parameters
            for param in self.parameter_deviations:
                val, dev = self.get_parameter_value_deviation_type(param)
                if isinstance(val, (int, float)):
                    new_val = self._get_sim_value(val, dev)
                    if new_val != val:
                        self.editor.set_parameter(param, new_val)
            # Run the simulation
            # Handle optional parameters properly before passing to run
            actual_callback = (
                callback if callback is not None else lambda *args, **kwargs: None
            )
            actual_callback_args = callback_args if callback_args is not None else {}
            actual_timeout = timeout if timeout is not None else float("inf")

            rt = self.run(
                wait_resource=True,
                callback=actual_callback,
                callback_args=actual_callback_args,
                switches=switches,
                timeout=actual_timeout,
                exe_log=exe_log,
            )

        self.runner.wait_completion()
        if callback is not None:
            callback_rets = []
            for rt in self.simulations:
                if rt is not None:
                    callback_rets.append(rt.get_results())
            self.simulation_results["callback_returns"] = callback_rets
        self.testbench.analysis_executed = True

    def analyse_measurement(self, meas_name: str) -> Optional[Any]:
        """Returns the measurement data for the given measurement name.

        If the measurement is not found, it returns None Note: It is up to the user to
        make the statistics on the data. The traditional way is to use the numpy package
        to calculate the mean and standard deviation of the data. It is also usual to
        consider max and min as 3 sigma, which is 99.7% of the data.
        """
        if not self.testbench.analysis_executed:
            _logger.warning(
                "The analysis was not executed. Please run the analysis before calling"
                " this method"
            )
            return None
        log_data: LogfileData = self.read_logfiles()
        meas_data = log_data[meas_name]
        if meas_data is None:
            _logger.warning("Measurement %s not found in log files", meas_name)
            return None
        return meas_data
