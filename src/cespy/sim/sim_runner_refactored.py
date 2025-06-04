#!/usr/bin/env python
# coding=utf-8
"""Refactored SimRunner using new component architecture as a facade.

This module provides a refactored SimRunner that delegates to specialized
components (TaskQueue, ProcessManager, ResultCollector, CallbackManager)
while maintaining backward compatibility with the existing API.
"""

import logging
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type, Union

from ..editor.base_editor import BaseEditor
from ..sim.simulator import Simulator
from .callback_manager import CallbackManager
from .process_callback import ProcessCallback
from .process_manager import ProcessManager, ProcessResult
from .result_collector import ResultCollector
from .run_task import RunTask
from .task_queue import TaskQueue, TaskPriority

__all__ = [
    "SimRunnerRefactored",
    "SimRunnerConfig",
    "RunConfig",
]

_logger = logging.getLogger("cespy.SimRunnerRefactored")

# Type aliases for clarity
CallbackType = Union[Type[ProcessCallback], Callable[[Path, Path], Any]]


@dataclass
class SimRunnerConfig:
    """Configuration for SimRunner initialization."""

    simulator: Optional[Union[str, Path, Type[Simulator]]] = None
    parallel_sims: int = 4
    timeout: float = 600.0
    verbose: bool = False
    output_folder: Optional[str] = None
    max_callback_errors: int = 3
    cleanup_interval: float = 60.0


@dataclass
class RunConfig:
    """Configuration for SimRunner.run() method."""

    wait_resource: bool = True
    callback: Optional[CallbackType] = None
    callback_args: Optional[Union[tuple[Any, ...], dict[str, Any]]] = None
    switches: Optional[List[str]] = None
    timeout: Optional[float] = None
    run_filename: Optional[str] = None
    exe_log: bool = False
    priority: TaskPriority = TaskPriority.NORMAL


class SimRunnerRefactored:
    """Refactored SimRunner using component-based architecture.

    This class maintains the same public API as the original SimRunner
    but delegates to specialized components for better modularity and
    maintainability.
    """

    def __init__(
        self,
        *,
        config: Optional[SimRunnerConfig] = None,
        simulator: Optional[Union[str, Path, Type[Simulator]]] = None,
        parallel_sims: Optional[int] = None,
        timeout: Optional[float] = None,
        verbose: Optional[bool] = None,
        output_folder: Optional[str] = None,
    ) -> None:
        """Initialize SimRunner with component architecture.

        Args:
            config: Configuration object (overrides individual parameters)
            simulator: Simulator to use
            parallel_sims: Number of parallel simulations
            timeout: Default timeout for simulations
            verbose: Enable verbose logging
            output_folder: Output directory for simulation files
        """
        # Apply configuration
        if config is not None:
            simulator = simulator if simulator is not None else config.simulator
            parallel_sims = (
                parallel_sims if parallel_sims is not None else config.parallel_sims
            )
            timeout = timeout if timeout is not None else config.timeout
            verbose = verbose if verbose is not None else config.verbose
            output_folder = (
                output_folder if output_folder is not None else config.output_folder
            )
            max_callback_errors = config.max_callback_errors
            cleanup_interval = config.cleanup_interval
        else:
            parallel_sims = parallel_sims if parallel_sims is not None else 4
            timeout = timeout if timeout is not None else 600.0
            verbose = verbose if verbose is not None else False
            max_callback_errors = 3
            cleanup_interval = 60.0

        # Store configuration
        self.verbose = verbose
        self.timeout = timeout
        self.parallel_sims = parallel_sims
        self.cmdline_switches: List[str] = []

        # Setup output folder
        self.output_folder: Optional[Path] = None
        if output_folder:
            self.output_folder = Path(output_folder)
            if not self.output_folder.exists():
                self.output_folder.mkdir(parents=True)

        # Initialize components
        self._task_queue = TaskQueue()
        self._process_manager = ProcessManager(
            max_processes=parallel_sims, cleanup_interval=cleanup_interval
        )
        self._result_collector = ResultCollector(
            storage_path=self.output_folder / "results" if self.output_folder else None
        )
        self._callback_manager = CallbackManager(
            max_callback_errors=max_callback_errors
        )

        # Setup simulator
        self._setup_simulator(simulator)

        # Statistics
        self._run_count = 0
        self._iterator_counter = 0

        if self.verbose:
            _logger.setLevel(logging.DEBUG)
            logging.getLogger("cespy.RunTask").setLevel(logging.DEBUG)

        _logger.info(
            "SimRunnerRefactored initialized with %d parallel sims", parallel_sims
        )

    def __del__(self) -> None:
        """Clean up resources on deletion."""
        self.wait_completion(abort_all_on_timeout=True)
        self._process_manager.shutdown()

    @property
    def runno(self) -> int:
        """Get total number of runs."""
        return self._run_count

    @property
    def ok_sim(self) -> int:
        """Get number of successful simulations."""
        return self._result_collector.get_results_by_status(True).__len__()

    @property
    def fail_sim(self) -> int:
        """Get number of failed simulations."""
        return self._result_collector.get_results_by_status(False).__len__()

    def active_threads(self) -> int:
        """Get number of active simulation threads."""
        return len(self._process_manager.get_active_processes())

    def set_simulator(self, spice_tool: Type[Simulator]) -> None:
        """Set the simulator to use.

        Args:
            spice_tool: Simulator class
        """
        if not issubclass(spice_tool, Simulator):
            raise TypeError("Expecting Simulator subclass")
        self.simulator = spice_tool

    def clear_command_line_switches(self) -> None:
        """Clear command line switches."""
        self.cmdline_switches.clear()

    def add_command_line_switch(self, switch: str, path: str = "") -> None:
        """Add command line switch.

        Args:
            switch: Switch to add (e.g., "-ascii")
            path: Optional path argument for the switch
        """
        self.cmdline_switches.append(switch)
        if path:
            self.cmdline_switches.append(path)

    def run(
        self,
        netlist: Union[str, Path, BaseEditor],
        *,
        wait_resource: bool = True,
        callback: Optional[CallbackType] = None,
        callback_args: Optional[Union[tuple[Any, ...], dict[str, Any]]] = None,
        switches: Optional[List[str]] = None,
        timeout: Optional[float] = None,
        run_filename: Optional[str] = None,
        exe_log: bool = False,
        priority: TaskPriority = TaskPriority.NORMAL,
    ) -> Optional[RunTask]:
        """Execute a simulation run.

        Args:
            netlist: Circuit to simulate (editor or file path)
            wait_resource: Wait for available resource slot
            callback: Callback function or ProcessCallback class
            callback_args: Arguments for callback
            switches: Command line switches override
            timeout: Simulation timeout
            run_filename: Name for output files
            exe_log: Log simulator console output
            priority: Task priority

        Returns:
            RunTask object or None if resources unavailable
        """
        # Increment run counter
        self._run_count += 1
        run_number = self._run_count

        # Prepare netlist file
        run_netlist_file = self._prepare_netlist(netlist, run_filename, run_number)

        # Create RunTask
        task = RunTask(
            simulator=self.simulator,
            runno=run_number,
            netlist_file=run_netlist_file,
            callback=callback,
            callback_args=self._validate_callback_args(callback, callback_args),
            switches=switches,
            timeout=timeout or self.timeout,
            verbose=self.verbose,
            exe_log=exe_log,
        )

        # Check resources if needed
        if wait_resource:
            # Check if we have available slots
            active_count = len(self._process_manager.get_active_processes())
            if active_count >= self.parallel_sims:
                # Use TaskQueue's blocking behavior
                pass  # TaskQueue will handle waiting

        # Register callback if provided
        if callback:
            callback_id = f"run_{run_number}"
            self._callback_manager.register(
                callback_id=callback_id,
                callback=callback,
                args=callback_args if isinstance(callback_args, tuple) else None,
                kwargs=callback_args if isinstance(callback_args, dict) else None,
            )

        # Submit task to queue
        self._task_queue.submit(
            run_task=task,
            priority=priority,
            dependencies=None,  # Could add dependency support later
        )

        # Start processing if not already running
        self._process_next_task()

        return task

    def wait_completion(
        self,
        timeout: Optional[float] = None,
        abort_all_on_timeout: bool = False,
    ) -> bool:
        """Wait for all simulations to complete.

        Args:
            timeout: Maximum time to wait
            abort_all_on_timeout: Abort remaining tasks on timeout

        Returns:
            True if all completed, False on timeout
        """
        import time

        start_time = time.time()

        while True:
            # Check if all tasks are complete
            stats = self._task_queue.get_statistics()
            active_processes = len(self._process_manager.get_active_processes())

            if (
                stats["pending"] == 0
                and stats["running"] == 0
                and active_processes == 0
            ):
                return True

            # Check timeout
            if timeout and (time.time() - start_time) > timeout:
                if abort_all_on_timeout:
                    self._abort_all()
                return False

            # Process any pending tasks
            self._process_next_task()

            # Small sleep to avoid busy waiting
            time.sleep(0.1)

    def _setup_simulator(
        self, simulator: Optional[Union[str, Path, Type[Simulator]]]
    ) -> None:
        """Setup the simulator instance."""
        if simulator is None:
            # Default to LTspice
            from ..simulators.ltspice_simulator import LTspice

            self.simulator = LTspice
        elif isinstance(simulator, (str, Path)):
            from ..simulators.ltspice_simulator import LTspice

            self.simulator = LTspice.create_from(simulator)
        elif issubclass(simulator, Simulator):
            self.simulator = simulator
        else:
            raise TypeError("Invalid simulator type")

    def _prepare_netlist(
        self,
        netlist: Union[str, Path, BaseEditor],
        run_filename: Optional[str],
        run_number: int,
    ) -> Path:
        """Prepare netlist file for simulation."""
        # Generate filename if not provided
        if run_filename is None:
            if isinstance(netlist, BaseEditor):
                base_name = Path(netlist.circuit_file).stem
            else:
                base_name = Path(netlist).stem
            run_filename = f"{base_name}_{run_number}.net"

        # Get output path
        if self.output_folder:
            output_path = self.output_folder / run_filename
        else:
            output_path = Path(run_filename)

        # Save or copy netlist
        if isinstance(netlist, BaseEditor):
            netlist.save_netlist(output_path)
        else:
            shutil.copy(netlist, output_path)

        return output_path

    def _prepare_run_config(
        self, switches: Optional[List[str]], timeout: Optional[float], exe_log: bool
    ) -> Dict[str, Any]:
        """Prepare run configuration."""
        config = {
            "switches": (switches or []) + self.cmdline_switches,
            "timeout": timeout or self.timeout,
            "exe_log": exe_log,
        }
        return config

    def _validate_callback_args(
        self,
        callback: Optional[CallbackType],
        callback_args: Optional[Union[tuple[Any, ...], dict[str, Any]]],
    ) -> Optional[Dict[str, Any]]:
        """Validate and convert callback arguments."""
        if callback is None:
            return None

        # This is a simplified version - the full implementation
        # would validate argument counts and convert tuples to dicts
        if isinstance(callback_args, dict):
            return callback_args
        if isinstance(callback_args, tuple):
            # Convert to dict (simplified - would need parameter names)
            return {"args": callback_args}
        return {}

    def _process_next_task(self) -> None:
        """Process the next task from the queue if resources available."""
        # Check if we have available process slots
        active_count = len(self._process_manager.get_active_processes())
        if active_count >= self.parallel_sims:
            return

        # Get next task
        task_info = self._task_queue.get_next()
        if not task_info:
            return

        task_id = task_info.task_id
        task = task_info.run_task
        # Check if task is valid
        if task is None:
            _logger.error("Task %s has no run_task", task_id)
            self._task_queue.mark_completed(task_id, success=False)
            return

        # Execute simulation
        try:
            # Task is already marked as running by get_next()

            # Execute simulation using simulator's run method
            return_code = task.simulator.run(
                netlist_file=task.netlist_file,
                cmd_line_switches=task.switches or [],
                timeout=task.timeout,
                exe_log=task.exe_log,
            )
            # Create a mock result for compatibility with existing code
            result = ProcessResult(
                return_code=return_code,
                stdout_path=None,
                stderr_path=None,
                duration=0.0,
                terminated=False,
                error_message=None,
            )

            # Mark complete
            self._task_queue.mark_completed(task_id, success=True)

            # Collect result
            self._handle_result(task, result)

        except Exception as e:
            _logger.error("Error processing task %s: %s", task_id, e)
            self._task_queue.mark_completed(task_id, success=False)

    def _handle_result(self, task: RunTask, result: ProcessResult) -> None:
        """Handle simulation result."""
        # Determine output files
        raw_file = task.netlist_file.with_suffix(".raw")
        log_file = task.netlist_file.with_suffix(".log")

        # Add to result collector
        sim_result = self._result_collector.add_result(
            task_id=f"run_{task.runno}",
            netlist_path=task.netlist_file,
            raw_file=raw_file if raw_file.exists() else None,
            log_file=log_file if log_file.exists() else None,
            success=result.return_code == 0,
            error_message=result.error_message,
            metadata={
                "duration": result.duration,
                "terminated": result.terminated,
            },
        )

        # Execute callback if registered
        if task.callback:
            callback_id = f"run_{task.runno}"
            self._callback_manager.execute(
                callback_id=callback_id,
                raw_file=raw_file,
                log_file=log_file,
                context={"task": task, "result": sim_result},
            )

    def _abort_all(self) -> None:
        """Abort all running and pending tasks."""
        # Shutdown queue (cancels pending tasks)
        self._task_queue.shutdown(wait=False)

        # Terminate active processes
        for process_id in list(self._process_manager.get_active_processes().keys()):
            self._process_manager.terminate_process(process_id)
