#!/usr/bin/env python
# coding=utf-8

# -------------------------------------------------------------------------------
#
#  ███████╗██████╗ ██╗ ██████╗███████╗██╗     ██╗██████╗
#  ██╔════╝██╔══██╗██║██╔════╝██╔════╝██║     ██║██╔══██╗
#  ███████╗██████╔╝██║██║     █████╗  ██║     ██║██████╔╝
#  ╚════██║██╔═══╝ ██║██║     ██╔══╝  ██║     ██║██╔══██╗
#  ███████║██║     ██║╚██████╗███████╗███████╗██║██████╔╝
#  ╚══════╝╚═╝     ╚═╝ ╚═════╝╚══════╝╚══════╝╚═╝╚═════╝
#
# Name:        run_task.py
# Purpose:     Class used for a spice tool using a process call
#
# Author:      Nuno Brum (nuno.brum@gmail.com)
#
# Created:     23-12-2016
# Licence:     refer to the LICENSE file
# -------------------------------------------------------------------------------
"""Internal classes not to be used directly by the user."""
__author__ = "Nuno Canto Brum <nuno.brum@gmail.com>"
__copyright__ = "Copyright 2023, Fribourg Switzerland"

import logging
import sys
import time
from pathlib import Path
from time import sleep
from typing import Any, Callable, Optional, Tuple, Type, Union

from .process_callback import ProcessCallback
from .simulator import Simulator

_logger = logging.getLogger("cespy.RunTask")

# Configure structured logging formatter if python-json-logger is installed
try:
    from pythonjsonlogger.json import JsonFormatter

    handler = logging.StreamHandler()
    json_formatter = JsonFormatter(
        "%(asctime)s %(name)s %(levelname)s "
        "[runno=%(runno)s netlist=%(netlist)s] %(message)s"
    )
    handler.setFormatter(json_formatter)
    if not _logger.handlers:
        _logger.addHandler(handler)
except (ImportError, ModuleNotFoundError):
    pass

END_LINE_TERM = "\n"

if sys.version_info.major >= 3 and sys.version_info.minor >= 6:
    clock_function = time.time
else:
    clock_function = time.perf_counter


def format_time_difference(time_diff: float) -> str:
    """Formats the time difference in a human-readable format, stripping the hours or
    minutes if they are zero."""
    seconds_difference = int(time_diff)
    milliseconds = int((time_diff - seconds_difference) * 1000)
    hours, remainder = divmod(seconds_difference, 3600)
    minutes, seconds = divmod(remainder, 60)

    if hours == 0 and minutes == 0:
        return f"{int(seconds):02d}.{milliseconds:04d} secs"
    if hours == 0:
        return f"{int(minutes):02d}:{int(seconds):02d}.{milliseconds:04d}"
    return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}.{milliseconds:04d}"


class RunTask:  # pylint: disable=too-many-instance-attributes
    """This is an internal Class and should not be used directly by the User."""

    # Instance variable annotations for type checking
    start_time: Optional[float]
    stop_time: Optional[float]
    verbose: bool
    switches: Any
    timeout: Optional[float]
    simulator: Type[Simulator]
    runno: int
    netlist_file: Path
    callback: Any
    callback_args: Optional[dict[str, Any]]
    retcode: int
    raw_file: Optional[Path]
    log_file: Optional[Path]
    callback_return: Any
    exe_log: bool
    logger: Any

    def __init__(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        simulator: Type[Simulator],
        runno: int,
        netlist_file: Path,
        callback: Any,
        callback_args: Optional[dict[str, Any]] = None,
        switches: Any = None,
        timeout: Optional[float] = None,
        verbose: bool = False,
        exe_log: bool = False,
    ) -> None:
        self.start_time = None
        self.stop_time = None
        self.verbose = verbose
        self.switches = switches
        self.timeout = timeout  # Thanks to Daniel Phili for implementing this
        self.simulator = simulator
        self.runno = runno
        self.netlist_file = netlist_file
        self.callback = callback
        self.callback_args = callback_args
        self.retcode = -1  # Signals an error by default
        self.raw_file = None
        self.log_file = None
        self.callback_return = None
        self.exe_log = exe_log
        # Create a LoggerAdapter to include run number and netlist in logs
        self.logger = logging.LoggerAdapter(
            _logger, {"runno": self.runno, "netlist": str(self.netlist_file)}
        )

    def print_info(self, logger_fun: Callable[[str], Any], message: str) -> None:
        """Print information and optionally log it.

        Args:
            logger_fun: Logger function to use (e.g., _logger.info)
            message: Message to print/log
        """
        # Use contextual logger for info/error messages
        logger_fun(message)
        if self.verbose:
            print(f"{time.asctime()} {logger_fun.__name__}: {message}{END_LINE_TERM}")

    def run(self) -> None:  # pylint: disable=too-many-branches,too-many-statements
        """Execute the simulation task."""
        # Running the Simulation
        self.start_time = clock_function()
        self.print_info(
            _logger.info,
            f": Starting simulation {self.runno}: {self.netlist_file}",
        )
        # Initialize default executable if none configured and method available
        if not self.simulator.spice_exe:
            get_default_exec = getattr(self.simulator, "get_default_executable", None)
            if callable(get_default_exec):
                default_exec = get_default_exec()
                if isinstance(default_exec, (str, Path)):
                    self.simulator = self.simulator.create_from(default_exec)
                else:
                    _logger.warning(
                        "get_default_executable returned unexpected type: %s", type(default_exec)
                    )
        # start execution
        self.retcode = self.simulator.run(
            self.netlist_file.absolute().as_posix(),
            self.switches,
            self.timeout,
            exe_log=self.exe_log,
        )
        self.stop_time = clock_function()
        # print simulation time with format HH:MM:SS.mmmmmm

        # Calculate the time difference
        sim_time = format_time_difference(self.stop_time - self.start_time)
        # Format the time difference
        self.log_file = self.netlist_file.with_suffix(".log")

        # Cleanup everything
        if self.retcode == 0:
            self.raw_file = self.netlist_file.with_suffix(self.simulator.raw_extension)
            if self.raw_file.exists() and self.log_file.exists():
                # simulation successful
                self.print_info(
                    _logger.info,
                    f"Simulation Successful. Time elapsed: {sim_time}",
                )

                if self.callback:
                    if self.callback_args is not None:
                        callback_print = ", ".join(
                            [
                                f"{key}={value}"
                                for key, value in self.callback_args.items()
                            ]
                        )
                    else:
                        callback_print = ""
                    self.print_info(
                        _logger.info,
                        f"Simulation Finished. Calling...{self.callback.__name__}"
                        f"(rawfile, logfile{callback_print})",
                    )
                    # Invoke callback: ProcessCallback subclass or function
                    assert self.raw_file is not None and self.log_file is not None
                    if isinstance(self.callback, type) and issubclass(
                        self.callback, ProcessCallback
                    ):
                        # ProcessCallback uses str parameters
                        raw_str = self.raw_file.as_posix()
                        log_str = self.log_file.as_posix()
                        if self.callback_args is not None:
                            return_or_process = self.callback(
                                raw_str, log_str, **self.callback_args
                            )
                        else:
                            return_or_process = self.callback(raw_str, log_str)
                    else:
                        # Function callback uses Path parameters
                        if self.callback_args is not None:
                            return_or_process = self.callback(
                                self.raw_file,
                                self.log_file,
                                **self.callback_args,
                            )
                        else:
                            return_or_process = self.callback(
                                self.raw_file, self.log_file
                            )
                    try:
                        if isinstance(return_or_process, ProcessCallback):
                            proc = return_or_process
                            proc.start()
                            self.callback_return = proc.queue.get()
                            proc.join()
                        else:
                            self.callback_return = return_or_process
                    except (ValueError, TypeError, RuntimeError) as exc:
                        self.logger.exception(
                            "Exception during callback execution: %s", exc
                        )
                    else:
                        callback_start_time = self.stop_time
                        self.stop_time = clock_function()
                        self.print_info(
                            _logger.info,
                            f"Callback Finished. Time elapsed: "
                            f"{format_time_difference(self.stop_time - callback_start_time)}",
                        )
                else:
                    self.print_info(
                        _logger.info,
                        "Simulation Finished. No Callback function given",
                    )
            else:
                self.print_info(
                    _logger.error,
                    "Simulation Raw file or Log file were not found",
                )
        else:
            # Simulation failed
            self.logger.error("Simulation Aborted. Time elapsed: %s", sim_time)
            if self.log_file.exists():
                self.log_file = self.log_file.replace(
                    self.log_file.with_suffix(".fail")
                )

    def get_results(self) -> Union[None, Any, Tuple[str, str]]:
        """Returns the simulation outputs if the simulation and callback function has
        already finished.

        If the simulation is not finished, it simply returns None. If no callback
        function is defined, then it returns a tuple with (raw_file, log_file). If a
        callback function is defined, it returns whatever the callback function is
        returning.
        """
        # simulation not started or still running if retcode unset
        if self.retcode == -1:
            return None

        if self.retcode == 0:  # All finished OK
            if self.callback:
                return self.callback_return
            return self.raw_file, self.log_file

        if self.callback:
            return None
        return self.raw_file, self.log_file

    def wait_results(self) -> Union[Any, Tuple[str, str]]:
        """Waits for the completion of the task and returns a tuple with the raw and log
        files.

        :returns: Tuple with the path to the raw file and the path to the log file
        :rtype: tuple(str, str)
        """
        # wait until simulation run() has been executed
        while self.retcode == -1:
            sleep(0.1)
        return self.get_results()

    def __call__(self) -> "RunTask":
        """Allow this object to be submitted to an Executor."""
        self.run()
        return self
