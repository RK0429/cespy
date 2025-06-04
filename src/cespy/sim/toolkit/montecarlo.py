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
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple, Type, Union, cast

from ...editor.base_editor import BaseEditor
from ...log.logfile_data import LogfileData
from ..process_callback import ProcessCallback
from ..run_task import RunTask
from .base_analysis import AnalysisResult, AnalysisStatus, StatisticalAnalysis
from .tolerance_deviations import ComponentDeviation, DeviationType, ToleranceDeviations

_logger = logging.getLogger("cespy.MonteCarloAnalysis")


class Montecarlo(ToleranceDeviations, StatisticalAnalysis):
    """Class to automate Monte Carlo simulations with statistical analysis.

    This class provides two operational modes:

    1. **Testbench Mode** (default): Uses simulator formulas with .STEP directives
       for efficient batch execution. This is faster but requires simulator support.

    2. **Separate Run Mode**: Runs individual simulations with Python managing
       parameter variations. This provides better control and error recovery.

    The class inherits from both ToleranceDeviations (for component variation
    management) and StatisticalAnalysis (for parallel execution and result analysis).

    Example:
        ```python
        # Testbench mode (faster, single simulation with many runs)
        mc = Montecarlo('circuit.asc', num_runs=1000, use_testbench_mode=True)
        mc.set_tolerance('R1', 0.05)  # 5% tolerance
        mc.run_testbench()
        stats = mc.get_measurement_statistics('Vout')

        # Separate run mode (better control, individual simulations)
        mc = Montecarlo('circuit.asc', num_runs=100, use_testbench_mode=False, parallel=True)
        mc.set_tolerance('R1', 0.05)
        results = mc.run_analysis()
        stats = mc.calculate_statistics('Vout')
        ```
    """

    def __init__(
        self,
        circuit_file: Union[str, BaseEditor],
        num_runs: int = 1000,
        seed: Optional[int] = None,
        use_testbench_mode: bool = True,
        **kwargs: Any,
    ):
        """Initialize Monte Carlo analysis.

        Args:
            circuit_file: Circuit file path or editor instance
            num_runs: Number of simulation runs
            seed: Random seed for reproducibility
            use_testbench_mode: If True, use simulator formulas; if False, separate runs
            **kwargs: Additional arguments for base classes
        """
        # Initialize ToleranceDeviations first
        ToleranceDeviations.__init__(self, circuit_file, kwargs.get("runner"))

        # Initialize StatisticalAnalysis
        StatisticalAnalysis.__init__(self, circuit_file, num_runs, seed, **kwargs)

        # Monte Carlo specific attributes
        self.use_testbench_mode = use_testbench_mode
        self._current_run_params: List[Dict[str, Any]] = []

        # Set random seed for Random class too (for backward compatibility)
        if seed is not None:
            random.seed(seed)

    def prepare_runs(self) -> List[Dict[str, Any]]:
        """Prepare parameter sets for all Monte Carlo runs.

        Returns:
            List of parameter dictionaries for each run
        """
        if self.use_testbench_mode:
            # In testbench mode, prepare a single run with formulas
            self.prepare_testbench(num_runs=self.num_runs)
            return [{"run_id": 0, "type": "testbench"}]
        else:
            # In separate run mode, prepare individual parameter sets
            all_params = []
            for run_id in range(self.num_runs):
                params = self._generate_run_parameters(run_id)
                all_params.append(params)
            self._current_run_params = all_params
            return all_params

    def _generate_run_parameters(self, run_id: int) -> Dict[str, Any]:
        """Generate parameters for a single run.

        Args:
            run_id: Run identifier

        Returns:
            Dictionary of parameters for this run
        """
        params: Dict[str, Any] = {"run_id": run_id}

        # Generate component variations
        for ref in self.get_components("*"):
            val, dev = self.get_component_value_deviation_type(ref)
            if isinstance(val, float) and dev.typ != DeviationType.NONE:
                new_val = self._get_sim_value(val, dev)
                if new_val != val:
                    params[f"comp_{ref}"] = new_val

        # Generate parameter variations
        for param in self.parameter_deviations:
            val, dev = self.get_parameter_value_deviation_type(param)
            if isinstance(val, (int, float)) and dev.typ != DeviationType.NONE:
                new_val = self._get_sim_value(val, dev)
                if new_val != val:
                    params[f"param_{param}"] = new_val

        return params

    def apply_parameters(self, parameters: Dict[str, Any]) -> None:
        """Apply parameters to the circuit.

        Args:
            parameters: Parameters to apply
        """
        if parameters.get("type") == "testbench":
            # Testbench mode - formulas already applied
            return

        # Apply component values
        for key, value in parameters.items():
            if key.startswith("comp_"):
                ref = key[5:]  # Remove "comp_" prefix
                self.editor.set_component_value(ref, value)
            elif key.startswith("param_"):
                param = key[6:]  # Remove "param_" prefix
                self.editor.set_parameter(param, value)

    def extract_results(self, run_task: RunTask) -> Dict[str, Any]:
        """Extract measurements from a completed run.

        Args:
            run_task: Completed simulation task

        Returns:
            Dictionary of measurements
        """
        measurements = {}

        # Read log file
        log_data = self.read_logfile(run_task)
        if log_data is not None:
            # Extract all measurements
            for meas_name in log_data.dataset:
                meas_values = log_data.dataset[meas_name]
                if meas_values:
                    # For testbench mode, return all values
                    if self.use_testbench_mode:
                        measurements[meas_name] = meas_values
                    else:
                        # For single run mode, return the last value
                        measurements[meas_name] = meas_values[-1]

        return measurements

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
                    # calculate expression for new value
                    new_val = f"{{utol({val},{tolstr})}}"
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
        """Run Monte Carlo analysis using testbench mode.

        This is the original method for running simulations using simulator
        formulas and .STEP directives. It's faster but less flexible.

        Args:
            callback: Process callback for simulation monitoring
            callback_args: Arguments for the callback
            switches: Additional simulator switches
            timeout: Timeout for the simulation
            exe_log: Whether to log execution
        """
        # Ensure testbench mode is enabled
        original_mode = self.use_testbench_mode
        self.use_testbench_mode = True

        try:
            # Prepare testbench if not already done
            if not getattr(self.testbench, "prepared", False):
                self.prepare_testbench(num_runs=self.num_runs)

            # Clear previous data
            self.elements_analysed.clear()
            self.clear_simulation_data()

            # Reset and apply instructions
            self._reset_netlist()
            self.play_instructions()

            # Run the simulation
            actual_callback = (
                callback if callback is not None else lambda *args, **kwargs: None
            )
            actual_callback_args = callback_args if callback_args is not None else {}
            actual_timeout = timeout if timeout is not None else float("inf")

            self.run(
                wait_resource=True,
                callback=actual_callback,
                callback_args=actual_callback_args,
                switches=switches,
                timeout=actual_timeout,
                exe_log=exe_log,
            )

            self.runner.wait_completion()

            # Process callback results
            if callback is not None:
                callback_rets = []
                for sim_rt in self.simulations:
                    if sim_rt is not None:
                        callback_rets.append(sim_rt.get_results())
                if not hasattr(self, "simulation_results"):
                    self.simulation_results = {}
                self.simulation_results["callback_returns"] = callback_rets

            self.testbench.analysis_executed = True

            # Return iterator if callback was provided
            if callback is not None:
                return (
                    sim.get_results() if sim is not None else None
                    for sim in self.simulations
                    if sim is not None
                )
            return None

        finally:
            self.use_testbench_mode = original_mode

    def run_separate_analysis(
        self,
        callback: Optional[Union[Type[ProcessCallback], Callable[..., Any]]] = None,
        callback_args: Optional[Union[Tuple[Any, ...], Dict[str, Any]]] = None,
        switches: Optional[list[str]] = None,
        timeout: Optional[float] = None,
        exe_log: bool = True,
    ) -> List[AnalysisResult]:
        """Run Monte Carlo analysis with separate simulations.

        This method runs each simulation separately, allowing for better control
        and recovery from individual simulation failures.

        Args:
            callback: Process callback for simulation monitoring
            callback_args: Arguments for the callback
            switches: Additional simulator switches
            timeout: Timeout for each simulation
            exe_log: Whether to log execution

        Returns:
            List of analysis results
        """
        # Temporarily disable testbench mode
        original_mode = self.use_testbench_mode
        self.use_testbench_mode = False

        try:
            # Set up callback forwarding if needed
            if callback is not None:
                self._setup_callback_forwarding(callback, callback_args)

            # Prepare all parameter sets
            param_sets = self.prepare_runs()

            # Run simulations for each parameter set
            results = []
            for params in param_sets:
                self.apply_parameters(params)

                # Run single simulation
                run_task = self._create_run_task(
                    switches=switches,
                    timeout=timeout,
                    exe_log=exe_log,
                )

                # Execute simulation
                if hasattr(self.runner, "run_now"):
                    result_tuple = cast(Any, self.runner).run_now(run_task)
                    if isinstance(result_tuple, tuple) and len(result_tuple) == 2:
                        raw_file, log_file = result_tuple
                    else:
                        raw_file, log_file = None, None
                else:
                    # Use run method for compatibility
                    result_tuple = self.runner.run(run_task.netlist_file)
                    if isinstance(result_tuple, tuple) and len(result_tuple) == 2:
                        raw_file, log_file = result_tuple
                    else:
                        raw_file, log_file = None, None

                # Create result
                result = AnalysisResult(
                    run_id=params.get("run_id", 0),
                    status=AnalysisStatus.COMPLETED if raw_file else AnalysisStatus.FAILED,
                    raw_file=raw_file,
                    log_file=log_file,
                    parameters=params,
                )

                # Execute callback if provided
                if callback is not None and raw_file and log_file:
                    cb_result = None
                    try:
                        if isinstance(callback, type) and issubclass(callback, ProcessCallback):
                            # ProcessCallback subclass needs raw_file and log_file in constructor
                            cb_instance = callback(raw_file, log_file)
                            cb_result = cb_instance.callback(raw_file, log_file)
                        elif callable(callback):
                            # Regular callable
                            if isinstance(callback_args, dict):
                                cb_result = callback(
                                    raw_file, log_file, **callback_args
                                )  # type: ignore[call-arg]
                            elif isinstance(callback_args, tuple):
                                cb_result = callback(
                                    raw_file, log_file, *callback_args
                                )  # type: ignore[call-arg]
                            else:
                                cb_result = callback(raw_file, log_file)  # type: ignore[call-arg]
                    except Exception as e:
                        _logger.warning(f"Callback execution failed: {e}")

                    # Store callback result using a custom attribute pattern
                    if cb_result is not None:
                        # We'll store it in the measurements dict if possible
                        if not result.measurements:
                            result.measurements = {}
                        result.measurements["_callback_result"] = cb_result

                results.append(result)
                self.results.append(result)

            return results

        finally:
            self.use_testbench_mode = original_mode

    def _setup_callback_forwarding(
        self,
        callback: Union[Type[ProcessCallback], Callable[..., Any]],
        callback_args: Optional[Union[Tuple[Any, ...], Dict[str, Any]]],
    ) -> None:
        """Set up callback forwarding for individual runs."""
        # Store original runner callback settings
        self._original_callback = getattr(self.runner, "default_callback", None)
        self._original_callback_args = getattr(
            self.runner, "default_callback_args", None
        )

        # Set new callback
        if hasattr(self.runner, "set_default_callback"):
            cast(Any, self.runner).set_default_callback(callback, callback_args)

    def _process_callback_results(self, results: List[AnalysisResult]) -> None:
        """Process callback results from individual runs."""
        callback_returns = []
        for result in results:
            if result.success and result.measurements and "_callback_result" in result.measurements:
                callback_returns.append(result.measurements["_callback_result"])

        if not hasattr(self, "simulation_results"):
            self.simulation_results = {}
        self.simulation_results["callback_returns"] = callback_returns

    def _create_run_task(
        self,
        switches: Optional[List[str]] = None,
        timeout: Optional[float] = None,
        exe_log: bool = True,
    ) -> RunTask:
        """Create a run task for simulation execution."""
        # Save current netlist to a file
        netlist_file = Path(self.editor.circuit_file).with_suffix('.net')
        self.editor.save_netlist(netlist_file)

        # Get the simulator class
        if hasattr(self.runner, "simulator") and isinstance(cast(Any, self.runner).simulator, type):
            simulator_class = cast(Any, self.runner).simulator
        else:
            # Try to get the simulator from the runner's class
            from ..simulator import Simulator as SimulatorBase
            simulator_class = SimulatorBase  # Default fallback

        return RunTask(
            simulator=simulator_class,
            runno=0,  # Will be set later
            netlist_file=netlist_file,
            callback=None,  # Callbacks handled separately
            callback_args=None,
            switches=switches,
            timeout=timeout,
            verbose=exe_log,
        )

    def analyse_measurement(self, meas_name: str) -> Optional[List[float]]:
        """Returns the measurement data for the given measurement name.

        If the measurement is not found, it returns None Note: It is up to the user to
        make the statistics on the data. The traditional way is to use the numpy package
        to calculate the mean and standard deviation of the data. It is also usual to
        consider max and min as 3 sigma, which is 99.7% of the data.
        """
        if self.use_testbench_mode:
            # In testbench mode, read from log files
            if not getattr(self.testbench, "analysis_executed", False):
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
        else:
            # In separate run mode, collect from results
            values = []
            for result in self.results:
                if result.success and meas_name in result.measurements:
                    value = result.measurements[meas_name]
                    if isinstance(value, (int, float)):
                        values.append(float(value))
            return values if values else None

    def get_measurement_statistics(self, meas_name: str) -> Dict[str, float]:
        """Get statistics for a measurement.

        This is a convenience method that combines analyse_measurement
        with calculate_statistics from the base class.

        Args:
            meas_name: Name of the measurement

        Returns:
            Dictionary with statistical measures
        """
        # If using testbench mode, need to populate results first
        if self.use_testbench_mode and not self.results:
            values = self.analyse_measurement(meas_name)
            if values:
                # Create synthetic results for statistics calculation
                for i, value in enumerate(values):
                    result = AnalysisResult(
                        run_id=i,
                        status=AnalysisStatus.COMPLETED,
                        measurements={meas_name: value},
                    )
                    self.results.append(result)

        return self.calculate_statistics(meas_name)

    def run_analysis(  # type: ignore[override]
        self,
        callback: Optional[Union[Type[ProcessCallback], Callable[..., Any]]] = None,
        callback_args: Optional[Union[Tuple[Any, ...], Dict[str, Any]]] = None,
        switches: Optional[List[str]] = None,
        timeout: Optional[float] = None,
        exe_log: bool = True,
        measure: Optional[str] = None,
        num_runs: Optional[int] = None,
    ) -> Union[
        List[AnalysisResult],
        Optional[
            Tuple[
                float,
                float,
                Dict[str, Union[str, float]],
                float,
                Dict[str, Union[str, float]],
            ]
        ],
    ]:
        """Run the Monte Carlo analysis.

        This method supports both the new BaseAnalysis interface (no args)
        and the legacy ToleranceDeviations interface (with args).

        Returns:
            List of analysis results for new interface,
            tuple for legacy
        """
        # If called without arguments, use new interface
        if (
            callback is None
            and all(arg is None for arg in [callback_args, switches, timeout, measure, num_runs])
            and exe_log
        ):
            if self.use_testbench_mode:
                # Run testbench mode and convert results
                self.run_testbench()
                # Convert stored results to AnalysisResult format
                return self.results
            else:
                # Run separate analysis mode
                return self.run_separate_analysis()
        else:
            # Legacy mode - delegate to run_analysis_legacy
            return self.run_analysis_legacy(
                callback=callback,
                callback_args=callback_args,
                switches=switches,
                timeout=timeout,
                exe_log=exe_log,
                measure=measure,
                num_runs=num_runs,
            )

    # Backward compatibility methods
    def run_analysis_legacy(
        self,
        callback: Optional[Union[Type[ProcessCallback], Callable[..., Any]]] = None,
        callback_args: Optional[Union[Tuple[Any, ...], Dict[str, Any]]] = None,
        switches: Optional[list[str]] = None,
        timeout: Optional[float] = None,
        exe_log: bool = True,
        measure: Optional[str] = None,  # pylint: disable=unused-argument
        num_runs: Optional[int] = None,
    ) -> Optional[
        Tuple[
            float,
            float,
            Dict[str, Union[str, float]],
            float,
            Dict[str, Union[str, float]],
        ]
    ]:
        """Run Monte Carlo analysis (backward compatibility method).

        This method maintains backward compatibility while directing to the
        appropriate analysis method based on the current mode.

        Args:
            callback: Process callback for simulation monitoring
            callback_args: Arguments for the callback
            switches: Additional simulator switches
            timeout: Timeout for simulations
            exe_log: Whether to log execution
            measure: Deprecated parameter (ignored)
            num_runs: Override number of runs (updates self.num_runs)

        Returns:
            List of results if separate mode, None if testbench mode
        """
        # Update num_runs if provided
        if num_runs is not None:
            self.num_runs = num_runs

        if self.use_testbench_mode:
            # Use testbench mode
            self.run_testbench(
                callback=callback,
                callback_args=callback_args,
                switches=switches,
                timeout=timeout,
                exe_log=exe_log,
            )
            return None
        else:
            # Use separate run mode
            return self.run_separate_analysis(  # type: ignore[return-value]
                callback=callback,
                callback_args=callback_args,
                switches=switches,
                timeout=timeout,
                exe_log=exe_log,
            )
