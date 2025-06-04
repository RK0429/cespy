#!/usr/bin/env python
# coding=utf-8
"""LTspice simulator implementation for cespy.

This module provides the LTspice class which implements the Simulator interface
for LTspice XVII. It handles simulator detection, command-line argument processing,
and simulation execution specific to LTspice.
"""

import logging
import os
import subprocess

# -------------------------------------------------------------------------------
#
#  ███████╗██████╗ ██╗ ██████╗███████╗██╗     ██╗██████╗
#  ██╔════╝██╔══██╗██║██╔════╝██╔════╝██║     ██║██╔══██╗
#  ███████╗██████╔╝██║██║     █████╗  ██║     ██║██████╔╝
#  ╚════██║██╔═══╝ ██║██║     ██╔══╝  ██║     ██║██╔══██╗
#  ███████║██║     ██║╚██████╗███████╗███████╗██║██████╔╝
#  ╚══════╝╚═╝     ╚═╝ ╚═════╝╚══════╝╚══════╝╚═╝╚═════╝
#
# Name:        ltspice_simulator.py
# Purpose:     Represents a LTspice tool and it's command line options
#
# Author:      Nuno Brum (nuno.brum@gmail.com)
#
# Created:     23-12-2016
# Licence:     refer to the LICENSE file
# -------------------------------------------------------------------------------
import sys
from pathlib import Path
from typing import IO, Dict, List, Optional, Union

# Core imports
from ..core import constants as core_constants
from ..core import paths as core_paths

from ..sim.simulator import Simulator, SpiceSimulatorError, run_function

_logger = logging.getLogger("cespy.LTSpiceSimulator")


class LTspice(Simulator):
    """Stores the simulator location and command line options and is responsible for
    generating netlists and running simulations.

    Searches on the any usual locations for a simulator.
    """

    # Use default paths from core constants
    _spice_exe_win_paths: List[str] = core_paths.get_default_simulator_paths(
        core_constants.Simulators.LTSPICE
    )

    # the default lib paths, as used by get_default_library_paths
    _default_lib_paths: List[str] = [
        "~/AppData/Local/LTspice/lib",
        "~/Documents/LTspiceXVII/lib/",
        "~/Documents/LTspice/lib/",
        "~/My Documents/LTspiceXVII/lib/",
        "~/My Documents/LTspice/lib/",
        "~/Local Settings/Application Data/LTspice/lib",
    ]

    # defaults:
    spice_exe: List[str] = []
    process_name: str = ""
    ltspice_args: Dict[str, List[str]] = {
        "-alt": ["-alt"],  # Set solver to Alternate.
        # Use ASCII.raw files. Seriously degrades program performance.
        "-ascii": ["-ascii"],
        "-big": ["-big"],  # Start as a maximized window.
        "-encrypt": ["-encrypt"],
        # Convert raw file to FastAccess format.
        "-fastaccess": ["-FastAccess"],
        "-FixUpSchematicFonts": ["-FixUpSchematicFonts"],
        "-FixUpSymbolFonts": ["-FixUpSymbolFonts"],
        "-ini": ["-ini", "<path>"],  # Specify alternative LTspice.ini.
        "-I": ["-I<path>"],  # Insert library search path (last option).
        "-max": ["-max"],  # Synonym for -big
        "-netlist": ["-netlist"],  # Generate netlist from schematic.
        "-norm": ["-norm"],  # Set solver to Normal.
        "-PCBnetlist": ["-PCBnetlist"],  # Generate PCB format netlist.
        "-SOI": ["-SOI"],  # Allow up to 7 MOSFET nodes.
        "-sync": ["-sync"],  # Update component libraries.
    }
    _default_run_switches: List[str] = ["-Run", "-b"]

    @classmethod
    def using_macos_native_sim(cls) -> bool:
        """Tells if the simulator used is the MacOS native LTspice.

        :return: True if the MacOS native LTspice is used, False otherwise (will also
            return False on Windows or Linux)
        :rtype: bool
        """
        return (
            sys.platform == "darwin"
            and bool(cls.spice_exe)
            and "wine" not in cls.spice_exe[0].lower()
        )

    @classmethod
    def valid_switch(cls, switch: str, parameter: str = "") -> List[str]:
        """Validate a command line switch.

        Available options for Windows/wine LTspice:
          - -alt: Set solver to Alternate.
          - -ascii: Use ASCII.raw files (slow!).
          - -encrypt: Encrypt a model library.
          - -fastaccess: Convert raw file to FastAccess format.
          - -FixUpSchematicFonts: Update old schematic text fonts.
          - -FixUpSymbolFonts: Update old symbol fonts.
          - -ini <path>: Specify alternative LTspice.ini file.
          - -I<path>: Insert library search path (last option).
          - -max: Start maximized (synonym for -big).
          - -netlist: Generate netlist from schematic.
          - -norm: Set solver to Normal.
          - -PCBnetlist: Generate PCB format netlist.
          - -SOI: Allow up to 7 MOSFET nodes.
          - -sync: Update component libraries.

        Always included (cannot be set):
          - -Run: Start simulation in batch mode.
          - -b: Batch mode.

        MacOS native LTspice supports only batch mode (-b).
        """

        # See if the MacOS simulator is used. If so, check if I use the native
        # simulator
        if cls.using_macos_native_sim():
            # native LTspice has only '-b' switch
            raise ValueError("MacOS native LTspice supports only batch mode ('-b').")

        # format check
        if switch is None:
            return []
        switch = switch.strip()
        if len(switch) == 0:
            return []
        if switch[0] != "-":
            switch = "-" + switch

        # default run switches
        if switch in cls._default_run_switches:
            _logger.info("Switch %s is already in the default switches", switch)
            return []

        if switch in cls.ltspice_args:
            switches = cls.ltspice_args[switch]
            switches = [s.replace("<path>", parameter) for s in switches]
            return switches
        valid_keys = ", ".join(sorted(cls.ltspice_args.keys()))
        raise ValueError(f"Invalid switch '{switch}'. Valid switches are: {valid_keys}")

    @classmethod
    def run(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        cls,
        netlist_file: Union[str, Path],
        cmd_line_switches: Optional[Union[List[str], str]] = None,
        timeout: Optional[float] = None,
        *,
        stdout: Optional[Union[int, IO[bytes]]] = None,
        stderr: Optional[Union[int, IO[bytes]]] = None,
        exe_log: bool = False,
    ) -> int:
        """Executes a LTspice simulation run.

        A raw file and a log file will be generated, with the same name as the netlist
        file, but with `.raw` and `.log` extension.

        :param netlist_file: path to the netlist file
        :type netlist_file: Union[str, Path]
        :param cmd_line_switches: additional command line options. Best to have been
            validated by valid_switch(), defaults to None
        :type cmd_line_switches: Union[list, None], optional
        :param timeout: If timeout is given, and the process takes too long, a
            TimeoutExpired exception will be raised, defaults to None
        :type timeout: Union[float, None], optional
        :param stdout: control redirection of the command's stdout. Valid values are
            None, subprocess.PIPE, subprocess.DEVNULL, an existing file descriptor (a
            positive integer), and an existing file object with a valid file descriptor.
            With the default settings of None, no redirection will occur. Also see
            `exe_log` for a simpler form of control.
        :type stdout: _FILE, optional
        :param stderr: Like stdout, but affecting the command's error output. Also see
            `exe_log` for a simpler form of control.
        :type stderr: _FILE, optional
        :param exe_log: If True, stdout and stderr will be ignored, and the simulator's
            execution console messages will be written to a log file (named ...exe.log)
            instead of console. This is especially useful when running under wine or
            when running simultaneous tasks.
        :type exe_log: bool, optional
        :raises SpiceSimulatorError: when the executable is not found.
        :raises NotImplementedError: when the requested execution is not possible on
            this platform.
        :return: return code from the process
        :rtype: int
        """
        if not cls.is_available():
            _logger.error("================== ALERT! ====================")
            _logger.error("Unable to find a LTspice executable.")
            _logger.error("A specific location of the LTSPICE can be set")
            _logger.error("using the create_from(<location>) class method")
            _logger.error("==============================================")
            raise SpiceSimulatorError("Simulator executable not found.")

        if cmd_line_switches is None:
            cmd_line_switches = []
        elif isinstance(cmd_line_switches, str):
            cmd_line_switches = [cmd_line_switches]
        netlist_file = Path(netlist_file)

        # cannot set raw and log file names or extensions. They are always
        # '<netlist_file>.raw' and '<netlist_file>.log'

        if sys.platform in ("linux", "darwin"):
            if cls.using_macos_native_sim():
                # native MacOS simulator, which has its limitations
                if netlist_file.suffix.lower() == core_constants.FileExtensions.ASC:
                    raise NotImplementedError(
                        "MacOS native LTspice cannot run simulations on '.asc' files. "
                        "Simulate '.net' or '.cir' files or use LTspice under wine."
                    )

                cmd_run = (
                    cls.spice_exe
                    + ["-b"]
                    + [netlist_file.as_posix()]
                    + cmd_line_switches
                )
            else:
                # wine
                # Drive letter 'Z' is the link from wine to the host platform's root
                # directory.
                # Z: is needed for netlists with absolute paths, but will also work with
                # relative paths.
                cmd_run = (
                    cls.spice_exe
                    + ["-Run"]
                    + ["-b"]
                    + ["Z:" + netlist_file.as_posix()]
                    + cmd_line_switches
                )
        else:
            # Windows (well, also aix, wasi, emscripten,... where it will
            # fail.)
            cmd_run = (
                cls.spice_exe
                + ["-Run"]
                + ["-b"]
                + [netlist_file.as_posix()]
                + cmd_line_switches
            )
        # start execution
        if exe_log:
            log_exe_file = netlist_file.with_suffix(
                ".exe.log"
            )  # LTSpice specific log extension
            with open(log_exe_file, "wb") as outfile:
                error = run_function(
                    cmd_run,
                    timeout=timeout,
                    stdout=outfile,
                    stderr=subprocess.STDOUT,
                )
        else:
            error = run_function(cmd_run, timeout=timeout, stdout=stdout, stderr=stderr)
        return error

    @classmethod
    def create_netlist(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        cls,
        circuit_file: Union[str, Path],
        cmd_line_switches: Optional[Union[List[str], str]] = None,
        timeout: Optional[float] = None,
        *,
        stdout: Optional[Union[int, IO[bytes]]] = None,
        stderr: Optional[Union[int, IO[bytes]]] = None,
        exe_log: bool = False,
    ) -> Path:
        """Create a netlist out of the circuit file.

        :param circuit_file: path to the circuit file
        :type circuit_file: Union[str, Path]
        :param cmd_line_switches: additional command line options. Best to have been
            validated by valid_switch(), defaults to None
        :type cmd_line_switches: Union[list, None], optional
        :param timeout: If timeout is given, and the process takes too long, a
            TimeoutExpired exception will be raised, defaults to None
        :type timeout: Union[float, None], optional
        :param stdout: control redirection of the command's stdout. Valid values are
            None, subprocess.PIPE, subprocess.DEVNULL, an existing file descriptor (a
            positive integer), and an existing file object with a valid file descriptor.
            With the default settings of None, no redirection will occur. Also see
            `exe_log` for a simpler form of control.
        :type stdout: _FILE, optional
        :param stderr: Like stdout, but affecting the command's error output. Also see
            `exe_log` for a simpler form of control.
        :type stderr: _FILE, optional
        :param exe_log: If True, stdout and stderr will be ignored, and the simulator's
            execution console messages will be written to a log file (named ...exe.log)
            instead of console. This is especially useful when running under wine or
            when running simultaneous tasks.
        :type exe_log: bool, optional
        :raises NotImplementedError: when the requested execution is not possible on
            this platform.
        :raises RuntimeError: when the netlist cannot be created
        :return: path to the netlist produced
        :rtype: Path
        """
        # prepare instructions, two stages used to enable edits on the netlist w/o open
        # GUI
        # see:
        # https://www.mikrocontroller.net/topic/480647?goto=5965300#5965300
        if cmd_line_switches is None:
            cmd_line_switches = []
        elif isinstance(cmd_line_switches, str):
            cmd_line_switches = [cmd_line_switches]
        circuit_file = Path(circuit_file)

        if cls.using_macos_native_sim():
            # native MacOS simulator
            raise NotImplementedError(
                "MacOS native LTspice does not have netlist generation "
                "capabilities. Use LTspice under wine."
            )

        cmd_netlist = (
            cls.spice_exe + ["-netlist"] + [circuit_file.as_posix()] + cmd_line_switches
        )
        if exe_log:
            log_exe_file = circuit_file.with_suffix(".exe.log")
            with open(log_exe_file, "wb") as outfile:
                error = run_function(
                    cmd_netlist,
                    timeout=timeout,
                    stdout=outfile,
                    stderr=subprocess.STDOUT,
                )
        else:
            error = run_function(
                cmd_netlist, timeout=timeout, stdout=stdout, stderr=stderr
            )

        if error == 0:
            netlist = circuit_file.with_suffix(core_constants.FileExtensions.NET)
            if netlist.exists():
                _logger.debug("OK")
                return netlist
        msg = "Failed to create netlist"
        _logger.error(msg)
        raise SpiceSimulatorError(msg)

    @classmethod
    def detect_executable(cls) -> None:
        """Detect and set spice_exe and process_name based on platform."""
        if sys.platform in ("linux", "darwin"):
            cls._detect_unix_executable()
        else:
            cls._detect_windows_executable()

    @classmethod
    def _detect_unix_executable(cls) -> None:
        """Detect on Linux/Mac using wine and environment variables."""
        spice_folder = os.environ.get("LTSPICEFOLDER")
        spice_executable = os.environ.get("LTSPICEEXECUTABLE")
        if spice_folder and spice_executable:
            cls.spice_exe = [
                "wine",
                core_paths.join_paths(spice_folder, spice_executable),
            ]
            cls.process_name = spice_executable
            return
        if spice_folder:
            cls.spice_exe = [
                "wine",
                core_paths.join_paths(spice_folder, "XVIIx64.exe"),
            ]
            cls.process_name = "XVIIx64.exe"
            return
        if spice_executable:
            default_folder = os.path.expanduser(
                "~/.wine/drive_c/Program Files/LTC/LTspiceXVII"
            )
            cls.spice_exe = [
                "wine",
                core_paths.join_paths(default_folder, spice_executable),
            ]
            cls.process_name = spice_executable
            return
        for exe in cls._spice_exe_win_paths:
            path = exe
            expanded_path, exists = core_paths.expand_and_check_local_dir(path)
            if exists:
                cls.spice_exe = ["wine", expanded_path]
                cls.process_name = core_paths.guess_process_name(expanded_path)
                return
        if sys.platform == "darwin":
            exe = "/Applications/LTspice.app/Contents/MacOS/LTspice"
            if core_paths.is_valid_file(exe):
                cls.spice_exe = [exe]
                cls.process_name = core_paths.guess_process_name(exe)

    @classmethod
    def _detect_windows_executable(cls) -> None:
        """Detect on Windows using default executable paths."""
        for exe in cls._spice_exe_win_paths:
            path = exe
            if path.startswith("~"):
                path = os.path.expanduser(path)
            if core_paths.is_valid_file(path):
                cls.spice_exe = [path]
                cls.process_name = core_paths.guess_process_name(path)
                return


# initialize LTspice executable detection
LTspice.detect_executable()
_logger.debug("Found LTspice installed in: '%s'", LTspice.spice_exe)
