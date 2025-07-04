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
# Name:        spice_editor.py
# Purpose:     Class made to update Generic Spice netlists
#
# Author:      Nuno Brum (nuno.brum@gmail.com)
#
# Licence:     refer to the LICENSE file
# -------------------------------------------------------------------------------
"""SPICE netlist parsing and editing functionality.

This module provides classes and utilities for reading, parsing, modifying, and
writing SPICE netlists. It supports a wide range of SPICE syntax including:

- Component definitions (resistors, capacitors, transistors, etc.)
- Subcircuit definitions and instantiations
- Parameter definitions and expressions
- Simulation commands (.tran, .ac, .dc, etc.)
- Model definitions and library includes

The main classes are:
- SpiceComponent: Represents a single SPICE component
- SpiceCircuit: Represents a complete SPICE circuit or subcircuit
- SpiceEditor: High-level interface for editing SPICE netlists

Example:
    >>> from cespy.editor import SpiceEditor
    >>> editor = SpiceEditor("circuit.net")
    >>> editor.set_component_value("R1", "10k")
    >>> editor.set_parameter("TEMP", 27)
    >>> editor.add_instruction(".tran 1m 10m")
    >>> editor.save_netlist("modified_circuit.net")
"""
from __future__ import annotations

import logging
import os
import re
from collections import OrderedDict
from pathlib import Path
from typing import (
    IO,
    Any,
    Callable,
    Dict,
    Iterator,
    List,
    Match,
    Optional,
    Pattern,
    Tuple,
    Type,
    Union,
)

from ..log.logfile_data import try_convert_value
from ..sim.sim_runner import SimRunner
from ..simulators.ltspice_simulator import LTspice
from ..utils.detect_encoding import EncodingDetectError, detect_encoding
from ..utils.file_search import search_file_in_containers
from .base_editor import (
    PARAM_REGEX,
    SUBCKT_DIVIDER,
    UNIQUE_SIMULATION_DOT_INSTRUCTIONS,
    BaseEditor,
    Component,
    ComponentNotFoundError,
    ParameterNotFoundError,
    format_eng,
)

_logger = logging.getLogger("cespy.SpiceEditor")

__author__ = "Nuno Canto Brum <nuno.brum@gmail.com>"
__copyright__ = "Copyright 2021, Fribourg Switzerland"

END_LINE_TERM = "\n"  #: This controls the end of line terminator used

# A Spice netlist can only have one of the instructions below, otherwise
# an error will be raised

# Regular expressions for the different components
FLOAT_RGX = r"[-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?"

# Regular expression for a number with decimal qualifier and unit
NUMBER_RGX = r"[-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?(Meg|[kmuµnpfgt])?[a-zA-Z]*"

# Parameters expression of the type: PARAM=value
PARAM_RGX = r"(?P<params>(\s+\w+\s*(=\s*[\w\{\}\(\)\-\+\*\/%\.]+)?)*)?"


def VALUE_RGX(number_regex: str) -> str:
    """Named Regex for a value or a formula."""
    return r"(?P<value>(?P<formula>{)?(?(formula).*}|" + number_regex + "))"


REPLACE_REGEXS: Dict[str, str] = {
    "A": r"",  # LTspice Only : Special Functions, Parameter substitution not supported
    # Behavioral source
    "B": r"^(?P<designator>B§?[VI]?\w+)(?P<nodes>(\s+\S+){2})\s+(?P<value>.*)$",
    "C": (
        r"^(?P<designator>C§?\w+)(?P<nodes>(\s+\S+){2})(?P<model>\s+\w+)?\s+"
        + VALUE_RGX(FLOAT_RGX + r"[muµnpfgt]?F?")
        + PARAM_RGX
        + r".*?$"
    ),  # Capacitor
    "D": (
        r"^(?P<designator>D§?\w+)(?P<nodes>(\s+\S+){2})\s+(?P<value>\w+)"
        + PARAM_RGX
        + ".*?$"
    ),  # Diode
    # Voltage Dependent Voltage Source
    "E": r"^(?P<designator>E§?\w+)(?P<nodes>(\s+\S+){2,4})\s+(?P<value>.*)$",
    # this only supports changing gain values
    # Current Dependent Current Source
    "F": r"^(?P<designator>F§?\w+)(?P<nodes>(\s+\S+){2})\s+(?P<value>.*)$",
    # This implementation replaces everything after the 2 first nets
    # Voltage Dependent Current Source
    "G": r"^(?P<designator>G§?\w+)(?P<nodes>(\s+\S+){2,4})\s+(?P<value>.*)$",
    # This only supports changing gain values
    # Voltage Dependent Current Source
    "H": r"^(?P<designator>H§?\w+)(?P<nodes>(\s+\S+){2})\s+(?P<value>.*)$",
    # This implementation replaces everything after the 2 first nets
    "I": (
        r"^(?P<designator>I§?\w+)(?P<nodes>(\s+\S+){2})\s+(?P<value>.*?)"
        # Independent Current Source
        r"(?P<params>(\s+\w+\s*=\s*[\w\{\}\(\)\-\+\*\/%\.]+)*)$"
    ),
    # This implementation replaces everything after the 2 first nets
    "J": (
        r"^(?P<designator>J§?\w+)(?P<nodes>(\s+\S+){3})\s+(?P<value>\w+)"
        + PARAM_RGX
        + ".*?$"
    ),  # JFET
    # Mutual Inductance
    "K": (
        r"^(?P<designator>K§?\w+)(?P<nodes>(\s+\S+){2,4})\s+"
        r"(?P<value>[\+\-]?[0-9\.E+-]+[kmuµnpgt]?).*$"
    ),
    # Inductance
    "L": (
        r"^(?P<designator>L§?\w+)(?P<nodes>(\s+\S+){2})\s+"
        r"(?P<value>({)?(?(5).*}|([0-9\.E+-]+(Meg|[kmuµnpgt])?H?))).*$"
    ),
    "M": (
        r"^(?P<designator>M§?\w+)(?P<nodes>(\s+\S+){3,4})\s+(?P<value>\w+)"
        + PARAM_RGX
        + ".*?$"
    ),  # MOSFET
    "O": (
        r"^(?P<designator>O§?\w+)(?P<nodes>(\s+\S+){4})\s+(?P<value>\w+)"
        + PARAM_RGX
        + ".*?$"
    ),  # Lossy Transmission Line
    "Q": (
        r"^(?P<designator>Q§?\w+)(?P<nodes>(\s+\S+){3,4})\s+(?P<value>\w+)"
        + PARAM_RGX
        + ".*?$"
    ),  # Bipolar
    "R": (
        r"^(?P<designator>R§?\w+)(?P<nodes>(\s+\S+){2})(?P<model>\s+\w+)?\s+"
        + "(R=)?"
        + VALUE_RGX(FLOAT_RGX + r"(Meg|[kRmuµnpfgt])?\d*")
        + PARAM_RGX
        + ".*?$"
    ),  # Resistor
    # Voltage Controlled Switch
    "S": r"^(?P<designator>S§?\w+)(?P<nodes>(\s+\S+){4})\s+(?P<value>.*)$",
    # Lossless Transmission
    "T": r"^(?P<designator>T§?\w+)(?P<nodes>(\s+\S+){4})\s+(?P<value>.*)$",
    # Uniform RC-line
    "U": r"^(?P<designator>U§?\w+)(?P<nodes>(\s+\S+){3})\s+(?P<value>.*)$",
    "V": (
        r"^(?P<designator>V§?\w+)(?P<nodes>(\s+\S+){2})\s+(?P<value>.*?)"
        # Independent Voltage Source
        r"(?P<params>(\s+\w+\s*=\s*[\w\{\}\(\)\-\+\*\/%\.]+)*)$"
    ),
    # ex: V1 NC_08 NC_09 PWL(1u 0 +2n 1 +1m 1 +2n 0 +1m 0 +2n -1 +1m -1 +2n 0)
    # AC 1 2 Rser=3 Cpar=4
    # Current Controlled Switch
    "W": r"^(?P<designator>W§?\w+)(?P<nodes>(\s+\S+){2})\s+(?P<value>.*)$",
    # This implementation replaces everything after the 2 first nets
    "X": (
        r"^(?P<designator>X§?\w+)(?P<nodes>(\s+\S+){1,99})\s+(?P<value>[\w\.]+)"
        r"(\s+params:)?" + PARAM_RGX + r"\\?$"
    ),  # Sub-circuit. The value is the last before any key-value parameters
    # This is structured differently than the others as it will accept any number of nodes.
    # But it only supports 1 value without any spaces in it (unlike V for example).
    # ex: XU1 NC_01 NC_02 NC_03 NC_04 NC_05 level2 Avol=1Meg GBW=10Meg
    #     Slew=10Meg Ilimit=25m Rail=0 Vos=0 En=0 Enk=0 In=0 Ink=0 Rin=500Meg
    #     XU1 in out1 -V +V out1 OPAx189 bla_v2 =1% bla_sp1=1 bla_sp2 = 1
    #     XU1 in out1 -V +V out1 GND OPAx189_float
    "Z": r"^(?P<designator>Z§?\w+)(?P<nodes>(\s+\S+){3})\s+(?P<value>\w+).*$",
    # MESFET and IBGT. TODO: Parameters substitution not supported
    "@": r"^(?P<designator>@§?\d+)(?P<nodes>(\s+\S+){2})\s?(?P<params>(.*)*)$",
    # Frequency Noise Analysis (FRA) wiggler
    # pattern = r'^@(\d+)\s+(\w+)\s+(\w+)(?:\s+delay=(\d+\w+))?(?:\s+fstart=(\d+\w+))?'
    # r'(?:\s+fend=(\d+\w+))?(?:\s+oct=(\d+))?(?:\s+fcoarse=(\d+\w+))?(?:\s+nmax=(\d+\w+))?'
    # r'\s+(\d+)\s+(\d+\w+)\s+(\d+)(?:\s+pp0=(\d+\.\d+))?(?:\s+pp1=(\d+\.\d+))?(?:\s+f0=(\d+\w+))?'
    # r'(?:\s+f1=(\d+\w+))?(?:\s+tavgmin=(\d+\w+))?(?:\s+tsettle=(\d+\w+))?(?:\s+acmag=(\d+))?$'
    "Ã": (
        r"^(?P<designator>Ã\w+)(?P<nodes>(\s+\S+){16})\s+(?P<value>.*)"
        + PARAM_RGX
        + ".*?$"
    ),  # QSPICE Unique component Ã
    "¥": (
        r"^(?P<designator>¥\w+)(?P<nodes>(\s+\S+){16})\s+(?P<value>.*)"
        + PARAM_RGX
        + ".*?$"
    ),  # QSPICE Unique component ¥
    "€": (
        r"^(?P<designator>€\w+)(?P<nodes>(\s+\S+){32})\s+(?P<value>.*)"
        + PARAM_RGX
        + ".*?$"
    ),  # QSPICE Unique component €
    "£": (
        r"^(?P<designator>£\w+)(?P<nodes>(\s+\S+){64})\s+(?P<value>.*)"
        + PARAM_RGX
        + ".*?$"
    ),  # QSPICE Unique component £
    "Ø": (
        r"^(?P<designator>Ø\w+)(?P<nodes>(\s+\S+){1,99})\s+(?P<value>.*)"
        + PARAM_RGX
        + ".*?$"
    ),  # QSPICE Unique component Ø
    "×": (
        r"^(?P<designator>×\w+)(?P<nodes>(\s+\S+){4,16})\s+"
        r"(?P<value>.*)(?P<params>(\w+\s+){1,8})\s*\\?$"
    ),  # QSPICE proprietaty component ×
    "Ö": (
        r"^(?P<designator>Ö\w+)(?P<nodes>(\s+\S+){5})\s+(?P<params>.*)\s*\\?$"
    ),  # LTspice proprietary component Ö
}

SUBCKT_CLAUSE_FIND = r"^.SUBCKT\s+"

# Code Optimization objects, avoiding repeated compilation of regular
# expressions
component_replace_regexs: Dict[str, Pattern[str]] = {
    prefix: re.compile(pattern, re.IGNORECASE)
    for prefix, pattern in REPLACE_REGEXS.items()
}
subckt_regex: Pattern[str] = re.compile(r"^.SUBCKT\s+(?P<name>[\w\.]+)", re.IGNORECASE)
lib_inc_regex: Pattern[str] = re.compile(r"^\.(LIB|INC)\s+(.*)$", re.IGNORECASE)

# The following variable deprecated, and here only so that people can find it.
# It is replaced by SpiceEditor.set_custom_library_paths().
# Since I cannot keep it operational easily, I do not use the deprecated
# decorator or the magic from https://stackoverflow.com/a/922693.
#
# LibSearchPaths = []


def get_line_command(line: Union[str, "SpiceCircuit"]) -> str:
    """Retrives the type of SPICE command in the line.

    Starts by removing the leading spaces and the evaluates if it is a comment, a
    directive or a component.
    """
    if isinstance(line, str):
        for i, ch in enumerate(line):
            if ch in (" ", "\t"):
                continue
            ch = ch.upper()
            if ch in REPLACE_REGEXS:  # A circuit element
                return ch
            if ch == "+":
                return "+"  # This is a line continuation.
            if ch in "#;*\n\r":  # It is a comment or a blank line
                return "*"
            if ch == ".":  # this is a directive
                j = i + 1
                while j < len(line) and (line[j] not in (" ", "\t", "\r", "\n")):
                    j += 1
                return line[i:j].upper()
            raise SyntaxError(f'Unrecognized command in line: "{line}"')
        # If we get here, the line contains only spaces/tabs
        return "*"  # Treat as blank line
    if isinstance(line, SpiceCircuit):
        return ".SUBCKT"
    raise SyntaxError(f'Unrecognized command in line "{line}"')


def _first_token_upped(line: str) -> str:
    """(Private function.

    Not to be used directly) Returns the first non-space character in the line. If a
    point '.' is found, then it gets the primitive associated.
    """
    i = 0
    while i < len(line) and line[i] in (" ", "\t"):
        i += 1
    j = i
    while i < len(line) and line[i] not in (" ", "\t"):
        i += 1
    return line[j:i].upper()


def _is_unique_instruction(instruction: str) -> bool:
    """(Private function.

    Not to be used directly) Returns true if the instruction is one of the unique
    instructions
    """
    cmd = get_line_command(instruction)
    return cmd in UNIQUE_SIMULATION_DOT_INSTRUCTIONS


def _parse_params(params_str: str) -> dict[str, Any]:
    """Parses the parameters string and returns a dictionary with the parameters."""
    params: OrderedDict[str, Any] = OrderedDict()
    for param in params_str.split():
        key, value = param.split("=")
        params[key] = try_convert_value(value)
    return dict(params)


class UnrecognizedSyntaxError(Exception):
    """Line doesn't match expected Spice syntax."""

    def __init__(self, line: str, regex: str) -> None:
        super().__init__(f'Line: "{line}" doesn\'t match regular expression "{regex}"')


class MissingExpectedClauseError(Exception):
    """Missing expected clause in Spice netlist."""


class SpiceComponent(Component):
    """Represents a SPICE component in the netlist.

    It allows the manipulation of the parameters and the value of the component.
    """

    parent: SpiceCircuit

    def __init__(self, parent: SpiceCircuit, line_no: int) -> None:
        raw_line = parent.netlist[line_no]
        assert isinstance(
            raw_line, str
        ), f"Expected str netlist line, got {type(raw_line)}"
        line = raw_line
        super().__init__(parent, line)
        self.parent = parent
        self.update_attributes_from_line_no(line_no)

    def update_attributes_from_line_no(self, line_no: int) -> Match[str]:
        """Update attributes of a component at a specific line in the netlist.

        :param line_no: line in the netlist
        :type line_no: int
        :raises NotImplementedError: When the component type is not recognized
        :raises UnrecognizedSyntaxError: When the line doesn't match the expected REGEX.
        :return: The match found
        :rtype: re.Match
        :meta private:
        """
        self.line = self.parent.netlist[line_no]
        prefix = self.line[0]
        regex = component_replace_regexs.get(prefix, None)
        if regex is None:
            error_msg = (
                "Component must start with one of these letters:"
                f" {','.join(REPLACE_REGEXS.keys())}\nGot {self.line}"
            )
            _logger.error(error_msg)
            raise NotImplementedError(error_msg)
        match = regex.match(self.line)
        if match is None:
            raise UnrecognizedSyntaxError(self.line, regex.pattern)

        info = match.groupdict()
        self.attributes.clear()
        for attr in info:
            if attr == "designator":
                self.reference = info[attr]
            elif attr == "nodes":
                self.ports = info[attr].split()
            elif attr == "params":
                self.attributes["params"] = _parse_params(info[attr])
            else:
                self.attributes[attr] = info[attr]
        return match

    def update_from_reference(self) -> None:
        """:meta private:"""
        line_no = self.parent.get_line_starting_with(self.reference)
        self.update_attributes_from_line_no(line_no)

    @property
    def value_str(self) -> str:
        # docstring inherited from Component
        self.update_from_reference()
        return str(self.attributes["value"])

    @value_str.setter
    def value_str(self, value: Union[str, int, float]) -> None:
        # docstring inherited from Component
        if self.parent.is_read_only():
            raise ValueError("Editor is read-only")
        self.parent.set_component_value(self.reference, value)

    def __getitem__(self, item: str) -> Any:
        """Get component attribute or parameter value.

        Args:
            item (str): The attribute or parameter name to retrieve

        Returns:
            Any: The value of the attribute or parameter

        Raises:
            KeyError: If the attribute or parameter is not found
        """
        self.update_from_reference()
        try:
            return super().__getitem__(item)
        except KeyError:
            # If the attribute is not found, then it is a parameter
            return self.params[item]

    def __setitem__(self, key: str, value: Any) -> None:
        """Set component attribute or parameter value.

        Args:
            key (str): The attribute or parameter name to set
            value (Any): The value to set

        Raises:
            ValueError: If the editor is read-only
        """
        if self.parent.is_read_only():
            raise ValueError("Editor is read-only")
        if key == "value":
            if isinstance(value, str):
                self.value_str = value
            else:
                self.value = value
        elif key == "params":
            if not isinstance(value, dict):
                raise ValueError("Expecting dict for params")
            # ensure all parameter values are strings
            str_params: dict[str, str] = {k: str(v) for k, v in value.items()}
            self.params = str_params
        else:
            self.set_params(**{key: value})


class SpiceCircuit(BaseEditor):
    """Represents sub-circuits within a SPICE circuit.

    Since sub-circuits can have sub-circuits inside them, it serves as base for the top
    level netlist. This hierarchical approach helps to encapsulate and protect
    parameters and components from edits made at a higher level.
    """

    netlist_file: Path
    simulator_lib_paths: List[str] = LTspice.get_default_library_paths()
    """This is initialised with typical locations found for LTspice. You can (and
    should, if you use wine), call `prepare_for_simulator()` once you've set the
    executable paths. This is a class variable, so it will be shared between all
    instances.

    :meta hide-value:
    """

    def __init__(self, parent: Optional["SpiceCircuit"] = None) -> None:
        super().__init__()
        self.netlist: List[Any] = []
        self._readonly = False
        self.modified_subcircuits: dict[str, "SpiceCircuit"] = {}
        self.parent = parent
        self.encoding = "utf-8"  # Default encoding to handle file operations

    def get_line_starting_with(self, substr: str) -> int:
        """Internal function. Do not use.

        :meta private:
        """
        # This function returns the line number that starts with the substr string.
        # If the line is not found, then -1 is returned.
        substr_upper = substr.upper()
        for line_no, line in enumerate(self.netlist):
            if isinstance(
                line, SpiceCircuit
            ):  # If it is a sub-circuit it will simply ignore it.
                continue
            line_upcase = _first_token_upped(line)
            if line_upcase == substr_upper:
                return line_no
        error_msg = f"line starting with '{substr}' not found in netlist"
        _logger.error(error_msg)
        raise ComponentNotFoundError(error_msg)

    def _add_lines(self, line_iter: Iterator[str]) -> bool:
        """Internal function.

        Do not use. Add a list of lines to the netlist.
        """
        for line in line_iter:
            cmd = get_line_command(line)
            if cmd == ".SUBCKT":
                sub_circuit = SpiceCircuit(self)
                sub_circuit.netlist.append(line)
                # Advance to the next non nested .ENDS
                # pylint: disable=protected-access
                finished = sub_circuit._add_lines(line_iter)
                # pylint: enable=protected-access
                if finished:
                    self.netlist.append(sub_circuit)
                if not finished:
                    return False
            elif cmd == "+":
                assert (
                    len(self.netlist) > 0
                ), "ERROR: The first line cannot be starting with a +"
                # Check if last element is a SpiceCircuit before appending
                if isinstance(self.netlist[-1], str):
                    self.netlist[-1] += line  # Appends to the last line
                else:
                    # Don't attempt to append to a SpiceCircuit
                    self.netlist.append(line)
            elif len(cmd) == 1 and len(line) > 1 and line[1] == "§":
                # strip any §, it is not always present and seems optional, so
                # scrap it
                line = line[0] + line[2:]
                self.netlist.append(line)
            else:
                self.netlist.append(line)
                if cmd[:4] == ".END":  # True for either .END and .ENDS primitives
                    return True  # If a sub-circuit is ended correctly, returns True
        return False  # If a sub-circuit ends abruptly, returns False

    def _write_lines(self, f: IO[str]) -> None:
        """Internal function.

        Do not use.
        """
        # This helper function writes the contents of sub-circuit to the file f
        for command in self.netlist:
            if isinstance(command, SpiceCircuit):
                # pylint: disable=protected-access
                command._write_lines(f)
                # pylint: enable=protected-access
            else:
                # Writes the modified sub-circuits at the end just before the .END
                # clause
                if command.upper().startswith(".ENDS"):
                    # write here the modified sub-circuits
                    for sub in self.modified_subcircuits.values():
                        # pylint: disable=protected-access
                        sub._write_lines(f)
                        # pylint: enable=protected-access
                f.write(command)

    def _get_param_named(self, param_name: str) -> Tuple[int, Optional[Match[str]]]:
        """Internal function.

        Do not use. Returns a line starting with command and matching the search with
        the regular expression
        """
        search_expression = re.compile(PARAM_REGEX(r"\w+"), re.IGNORECASE)
        param_name_upped = param_name.upper()
        line_no = 0
        while line_no < len(self.netlist):
            line = self.netlist[line_no]
            if isinstance(
                line, SpiceCircuit
            ):  # If it is a sub-circuit it will simply ignore it.
                line_no += 1
                continue
            cmd = get_line_command(line)
            if cmd == ".PARAM":
                matches = search_expression.finditer(line)
                for match in matches:
                    if match.group("name").upper() == param_name_upped:
                        return line_no, match
            line_no += 1
        return (
            -1,
            None,
        )  # If it fails, it returns an invalid line number and No match

    def get_all_parameter_names(self, param: str = "") -> List[str]:
        # docstring inherited from BaseEditor
        param_names = []
        search_expression = re.compile(PARAM_REGEX(r"\w+"), re.IGNORECASE)
        for line in self.netlist:
            cmd = get_line_command(line)
            if cmd == ".PARAM":
                matches = search_expression.finditer(line)
                for match in matches:
                    param_name = match.group("name")
                    param_names.append(param_name.upper())
        return sorted(param_names)

    def get_subcircuit_names(self) -> List[str]:
        """Returns a list of the names of the sub-circuits in the netlist.

        :return: list of sub-circuit names
        :rtype: List[str]
        """

        subckt_names: List[str] = []
        for line in self.netlist:
            if isinstance(line, SpiceCircuit):
                subckt_names.append(line.name())
        return subckt_names

    def get_subcircuit_named(self, name: str) -> Optional["SpiceCircuit"]:
        """Returns the sub-circuit object with the given name.

        :param name: name of the subcircuit
        :type name: str
        :return: _description_
        :rtype: _type_
        """

        for line in self.netlist:
            if isinstance(line, SpiceCircuit):
                if line.name() == name:
                    return line
        if self.parent is not None:
            return self.parent.get_subcircuit_named(name)
        return None

    def get_subcircuit(self, reference: str) -> "SpiceCircuit":
        """Returns an object representing a Subcircuit. This object can manipulate
        elements such as the SpiceEditor does.

        :param reference: Reference of the subcircuit
        :type reference: str
        :returns: SpiceCircuit instance
        :rtype: SpiceCircuit
        :raises UnrecognizedSyntaxError: when an spice command is not recognized by
            cespy
        :raises ComponentNotFoundError: When the reference was not found
        """
        if SUBCKT_DIVIDER in reference:
            subckt_ref, sub_subckts = reference.split(SUBCKT_DIVIDER, 1)
        else:
            subckt_ref = reference
            sub_subckts = None  # eliminating the code

        if (
            subckt_ref in self.modified_subcircuits
        ):  # See if this was already a modified sub-circuit instance
            return self.modified_subcircuits[subckt_ref]

        line_no = self.get_line_starting_with(subckt_ref)
        sub_circuit_instance = self.netlist[line_no]
        regex = component_replace_regexs["X"]  # The sub-circuit instance regex
        m = regex.search(sub_circuit_instance)
        if m:
            # last_token of the line before Params:
            subcircuit_name = m.group("value")
        else:
            raise UnrecognizedSyntaxError(sub_circuit_instance, REPLACE_REGEXS["X"])

        # Search for the sub-circuit in the netlist
        sub_circuit = self.get_subcircuit_named(subcircuit_name)
        if sub_circuit is not None:
            if SUBCKT_DIVIDER in reference and sub_subckts is not None:
                return sub_circuit.get_subcircuit(sub_subckts)
            return sub_circuit

        # If we reached here is because the subcircuit was not found. Search for
        # it in declared libraries
        sub_circuit = self.find_subckt_in_included_libs(subcircuit_name)

        if sub_circuit:
            if SUBCKT_DIVIDER in reference and sub_subckts is not None:
                return sub_circuit.get_subcircuit(sub_subckts)
            return sub_circuit
        # The search was not successful
        raise ComponentNotFoundError(f'Sub-circuit "{subcircuit_name}" not found')

    def _get_component_line_and_regex(self, reference: str) -> Tuple[int, Match[str]]:
        """Internal function.

        Do not use.
        """
        prefix = reference[0]
        regex = component_replace_regexs.get(prefix, None)
        if regex is None:
            error_msg = (
                "Component must start with one of these letters:"
                f" {','.join(REPLACE_REGEXS.keys())}\nGot {reference}"
            )
            _logger.error(error_msg)
            raise NotImplementedError(error_msg)
        line_no = self.get_line_starting_with(reference)
        line = self.netlist[line_no]
        match = regex.match(line)
        if match is None:
            raise UnrecognizedSyntaxError(line, regex.pattern)
        return line_no, match

    def _set_component_attribute(
        self, reference: str, attribute: str, value: Any
    ) -> None:
        """Internal method to set the model and value of a component."""

        # Using the first letter of the component to identify what is it
        if (
            reference[0] == "X" and SUBCKT_DIVIDER in reference
        ):  # Replaces a component inside of a subcircuit
            # In this case the sub-circuit needs to be copied so that its copy
            # is modified. A copy is created for each
            # instance of a sub-circuit.
            component_split = reference.split(SUBCKT_DIVIDER)
            subckt_instance = component_split[0]
            # reference = SUBCKT_DIVIDER.join(component_split[1:])
            if (
                subckt_instance in self.modified_subcircuits
            ):  # See if this was already a modified sub-circuit instance
                sub_circuit: SpiceCircuit = self.modified_subcircuits[subckt_instance]
            else:
                sub_circuit_original = self.get_subcircuit(
                    subckt_instance
                )  # If not will look for it.
                if sub_circuit_original:
                    new_name = (
                        sub_circuit_original.name() + "_" + subckt_instance
                    )  # Creates a new name with the path appended
                    sub_circuit = sub_circuit_original.clone(new_name=new_name)

                    # Memorize that the copy is relative to that particular
                    # instance
                    self.modified_subcircuits[subckt_instance] = sub_circuit
                    # Change the call to the sub-circuit
                    self._set_component_attribute(subckt_instance, "model", new_name)
                else:
                    raise ComponentNotFoundError(reference)
            # Update the component
            # pylint: disable=protected-access
            sub_circuit._set_component_attribute(
                SUBCKT_DIVIDER.join(component_split[1:]), attribute, value
            )
            # pylint: enable=protected-access
        else:
            line_no, match = self._get_component_line_and_regex(reference)
            if attribute in ("value", "model"):
                # They are actually the same thing just the model is not
                # converted.
                if isinstance(value, (int, float)):
                    value = format_eng(value)
                start = match.start("value")
                end = match.end("value")
                line = self.netlist[line_no]
                self.netlist[line_no] = line[:start] + value + line[end:]
            elif attribute == "params":
                if not isinstance(value, dict):
                    raise ValueError(
                        "set_component_parameters() expects to receive a dictionary"
                    )
                if match and match.groupdict().get("params"):
                    params_str = match.group("params")
                    params = self._parse_params(params_str)
                else:
                    params = {}

                for key, kvalue in value.items():
                    # format the kvalue
                    if kvalue is None:
                        kvalue_str = None
                    elif isinstance(kvalue, str):
                        kvalue_str = kvalue.strip()
                    else:
                        kvalue_str = f"{kvalue:G}"
                    if kvalue_str is None:
                        # remove those that must disappear
                        if key in params:
                            params.pop(key)
                    else:
                        # create or update
                        params[key] = kvalue_str
                params_str = " ".join(
                    [f"{key}={kvalue}" for key, kvalue in params.items()]
                )
                start = match.start("params")
                end = match.end("params")
                line = self.netlist[line_no]
                self.netlist[line_no] = line[:start] + " " + params_str + line[end:]

    def reset_netlist(self, create_blank: bool = False) -> None:
        """Removes all previous edits done to the netlist, i.e. resets it to the
        original state.

        :returns: Nothing
        """
        # Initialize the netlist without calling super().reset_netlist()
        self.netlist.clear()
        self.modified_subcircuits.clear()

        if create_blank:
            lines = ["* netlist generated from cespy", ".end"]
            finished = self._add_lines(iter(lines))
            if not finished:
                raise SyntaxError("Netlist with missing .END or .ENDS statements")
        elif hasattr(self, "netlist_file") and self.netlist_file.exists():
            with open(
                self.netlist_file,
                "r",
                encoding=self.encoding,
                errors="replace",
            ) as f:
                # Creates an iterator object to consume the file
                finished = self._add_lines(f)
                if not finished:
                    raise SyntaxError("Netlist with missing .END or .ENDS statements")
                # else:
                #     for _ in lines:  # Consuming the rest of the file.
                #         pass  # print("Ignoring %s" % _)
        elif hasattr(self, "netlist_file"):
            _logger.error("Netlist file not found: %s", self.netlist_file)

    def clone(self, **kwargs: Any) -> "SpiceCircuit":
        """Creates a new copy of the SpiceCircuit. Changes done at the new copy do not
        affect the original.

        :key new_name: The new name to be given to the circuit
        :key type new_name: str
        :return: The new replica of the SpiceCircuit object
        :rtype: SpiceCircuit
        """
        clone = SpiceCircuit(self)
        clone.netlist = self.netlist.copy()
        clone.netlist.insert(
            0,
            "***** SpiceEditor Manipulated this sub-circuit ****" + END_LINE_TERM,
        )
        clone.netlist.append("***** ENDS SpiceEditor ****" + END_LINE_TERM)
        new_name = kwargs.get("new_name", None)
        if new_name is not None:
            clone.setname(new_name)
        return clone

    def name(self) -> str:
        """Returns the name of the Sub-Circuit.

        :rtype: str
        """
        if self.netlist:
            for line in self.netlist:
                if isinstance(line, str):
                    m = subckt_regex.search(line)
                    if m:
                        return m.group("name")
            raise RuntimeError("Unable to find .SUBCKT clause in subcircuit")
        raise RuntimeError("Empty Subcircuit")

    def setname(self, new_name: str) -> None:
        """Renames the sub-circuit to a new name. No check is done to the new name. It
        is up to the user to make sure that the new name is valid.

        :param new_name: The new Name.
        :type new_name: str
        :return: Nothing
        """
        if self.netlist:
            lines = len(self.netlist)
            line_no = 0
            while line_no < lines:
                line = self.netlist[line_no]
                if isinstance(line, str):
                    m = subckt_regex.search(line)
                    if m:
                        # Replacing the name in the SUBCKT Clause
                        start = m.start("name")
                        end = m.end("name")
                        self.netlist[line_no] = line[:start] + new_name + line[end:]
                        break
                    line_no += 1
            else:
                raise MissingExpectedClauseError(
                    "Unable to find .SUBCKT clause in subcircuit"
                )

            # This second loop finds the .ENDS clause
            while line_no < lines:
                line = self.netlist[line_no]
                if get_line_command(line) == ".ENDS":
                    self.netlist[line_no] = ".ENDS " + new_name + END_LINE_TERM
                    break
                line_no += 1
            else:
                raise MissingExpectedClauseError(
                    "Unable to find .SUBCKT clause in subcircuit"
                )
        else:
            # Avoiding exception by creating an empty sub-circuit
            self.netlist.append("* SpiceEditor Created this sub-circuit")
            self.netlist.append(f".SUBCKT {new_name}{END_LINE_TERM}")
            self.netlist.append(f".ENDS {new_name}{END_LINE_TERM}")

    def get_component(self, reference: str) -> Component:
        """Returns an object representing the given reference in the schematic file.

        :param reference: Reference of the component
        :type reference: str
        :return: The SpiceComponent object or a SpiceSubcircuit in case of hierarchical
            design
        :rtype: Component
        :raises: ComponentNotFoundError - In case the component is not found
        :raises: UnrecognizedSyntaxError when the line doesn't match the expected REGEX.
        :raises: NotImplementedError if there isn't an associated regular expression for
            the component prefix.
        """
        if SUBCKT_DIVIDER in reference:
            if reference[0] != "X":  # Replaces a component inside of a subciruit
                raise ComponentNotFoundError(
                    "Only subcircuits can have components inside."
                )
            # In this case the sub-circuit needs to be copied so that is copy is modified.
            # A copy is created for each instance of a sub-circuit.
            component_split = reference.split(SUBCKT_DIVIDER)
            subckt_ref = component_split[0]

            if (
                subckt_ref in self.modified_subcircuits
            ):  # See if this was already a modified sub-circuit instance
                subcircuit = self.modified_subcircuits[subckt_ref]
            else:
                subcircuit = self.get_subcircuit(subckt_ref)

            if len(component_split) > 1:
                # Recursively get component from subcircuit - return as
                # Component
                return subcircuit.get_component(
                    SUBCKT_DIVIDER.join(component_split[1:])
                )
            # Need to wrap SpiceCircuit in Component for type
            # compatibility
            line_no = self.get_line_starting_with(subckt_ref)
            return SpiceComponent(self, line_no)
        line_no = self.get_line_starting_with(reference)
        return SpiceComponent(self, line_no)

    def __getitem__(self, item: str) -> Component:
        """Get component by reference name.

        Args:
            item (str): Component reference name (e.g., 'R1', 'C1')

        Returns:
            Component: The component object

        Raises:
            ComponentNotFoundError: If component is not found
        """
        component = super().__getitem__(item)
        if component.parent != self:
            # The HierarchicalComponent class must inherit from Component for this to work,
            # or we need to return the original component instead of wrapping
            # it
            return component
        return component

    def __delitem__(self, key: str) -> None:
        """Delete a component from the circuit.

        Args:
            key (str): Component reference name to delete

        Example:
            >>> del circuit['R1']  # Removes resistor R1
        """
        self.remove_component(key)

    def __contains__(self, key: str) -> bool:
        """Check if a component exists in the circuit.

        Args:
            key (str): Component reference name to check

        Returns:
            bool: True if component exists, False otherwise

        Example:
            >>> 'R1' in circuit  # Returns True if R1 exists
        """
        try:
            self.get_component(key)
            return True
        except ComponentNotFoundError:
            return False

    def __iter__(self) -> Iterator[Component]:
        """Iterate over all components in the circuit.

        Yields:
            Component: Each component in the circuit

        Example:
            >>> for component in circuit:
            ...     print(f"{component.reference}: {component.value}")
        """
        for line_no, line in enumerate(self.netlist):
            if isinstance(line, SpiceCircuit):
                yield from line
            else:
                cmd = get_line_command(line)
                if cmd in REPLACE_REGEXS:
                    yield SpiceComponent(self, line_no)

    def get_component_attribute(self, reference: str, attribute: str) -> str:
        """Returns the attribute of a component retrieved from the netlist.

        :param reference: Reference of the component
        :type reference: str
        :param attribute: Name of the attribute to be retrieved
        :type attribute: str
        :return: Value of the attribute
        :rtype: str
        :raises: ComponentNotFoundError - In case the component is not found
        :raises: UnrecognizedSyntaxError when the line doesn't match the expected REGEX.
        :raises: NotImplementedError if there isn't an associated regular expression for
            the component prefix.
        """
        component = self.get_component(reference)
        if isinstance(component, SpiceComponent):
            return str(component.attributes.get(attribute, ""))
        raise KeyError(f"Attribute '{attribute}' not found in component '{reference}'")

    @staticmethod
    def _parse_params(params_str: str) -> dict[str, Any]:
        """Parses the parameters string and returns a dictionary with the parameters."""
        params: OrderedDict[str, Any] = OrderedDict()
        for param in params_str.split():
            key, value = param.split("=")
            params[key] = try_convert_value(value)
        return dict(params)

    def get_component_parameters(self, element: str) -> dict[str, Any]:
        # docstring inherited from BaseEditor
        _, match = self._get_component_line_and_regex(element)
        if match and match.groupdict().get("params"):
            params_str = match.group("params")
            return self._parse_params(params_str)
        return {}

    def set_component_parameters(
        self, element: str, **kwargs: Union[str, int, float]
    ) -> None:
        # docstring inherited from BaseEditor
        if self.is_read_only():
            raise ValueError("Editor is read-only")
        self._set_component_attribute(element, "params", kwargs)

    def get_parameter(self, param: str) -> str:
        """Returns the value of a parameter retrieved from the netlist.

        :param param: Name of the parameter to be retrieved
        :type param: str
        :return: Value of the parameter being sought
        :rtype: str
        :raises: ParameterNotFoundError - In case the component is not found
        """

        _, match = self._get_param_named(param)
        if match:
            return str(match.group("value"))
        raise ParameterNotFoundError(param)

    def set_parameter(self, param: str, value: Union[str, int, float]) -> None:
        """Sets the value of a parameter in the netlist. If the parameter is not found,
        it is added to the netlist.

        Usage: ::

            runner.set_parameter("TEMP", 80)

        This adds onto the netlist the following line: ::

            .PARAM TEMP=80

        This is an alternative to the set_parameters which is more pythonic in its usage
        and allows setting more than one parameter at once.

        :param param: Spice Parameter name to be added or updated.
        :type param: str
        :param value: Parameter Value to be set.
        :type value: str, int or float
        :return: Nothing
        """
        if self.is_read_only():
            raise ValueError("Editor is read-only")
        param_line, match = self._get_param_named(param)
        if isinstance(value, (int, float)):
            value_str = format_eng(value)
        else:
            value_str = value
        if match:
            start, stop = match.span("value")
            line = self.netlist[param_line]
            if isinstance(line, str):
                self.netlist[param_line] = line[:start] + f"{value_str}" + line[stop:]
            else:
                # This should not happen in normal operation
                _logger.error("Unexpected non-string line at %s", param_line)
        else:
            # Was not found
            # the last two lines are typically (.backano and .end)
            insert_line = len(self.netlist) - 2
            self.netlist.insert(
                insert_line,
                f".PARAM {param}={value_str}  ; Batch instruction" + END_LINE_TERM,
            )

    def set_component_value(self, device: str, value: Union[str, int, float]) -> None:
        """Changes the value of a component, such as a Resistor, Capacitor or Inductor.
        For components inside sub-circuits, use the sub-circuit designator prefix with
        ':' as separator (Example X1:R1).

        Usage::

            runner.set_component_value('R1', '3.3k')
            runner.set_component_value('X1:C1', '10u')

        :param device: Reference of the circuit element to be updated.
        :type device: str
        :param value: value to be set on the given circuit element. Float and integer
            values will be automatically formatted as per the engineering notations 'k'
            for kilo, 'm', for mili and so on.
        :type value: str, int or float
        :raises ComponentNotFoundError: In case the component is not found
        :raises ValueError: In case the value doesn't correspond to the expected format
        :raises NotImplementedError: In case the circuit element is defined in a format
            which is not supported by this version. If this is the case, use GitHub to
            start a ticket. https://github.com/nunobrum/kupicelib
        """
        if self.is_read_only():
            raise ValueError("Editor is read-only")
        self._set_component_attribute(device, "value", value)

    def set_element_model(self, element: str, model: str) -> None:
        """Changes the value of a circuit element, such as a diode model or a voltage
        supply.

        Usage::

            runner.set_element_model('D1', '1N4148')
            runner.set_element_model('V1',
                                    "SINE(0 1 3k 0 0 0)")

        :param element: Reference of the circuit element to be updated.
        :type element: str
        :param model: model name of the device to be updated
        :type model: str
        :raises ComponentNotFoundError: In case the component is not found
        :raises ValueError: In case the model format contains irregular characters
        :raises NotImplementedError: In case the circuit element is defined in
            a format which is not supported by this version. If this is the
            case, use GitHub to start a ticket.
            https://github.com/nunobrum/kupicelib
        """
        if self.is_read_only():
            raise ValueError("Editor is read-only")
        self._set_component_attribute(element, "model", model)

    def get_component_value(self, element: str) -> str:
        """Returns the value of a component retrieved from the netlist."""
        component = self.get_component(element)
        if isinstance(component, SpiceComponent):
            return component.value_str
        if isinstance(component, SpiceCircuit):
            return component.name()
        return str(component)

    def get_element_value(self, element: str) -> str:
        """Returns the model or element value of a component."""
        component = self.get_component(element)
        if isinstance(component, SpiceComponent):
            return str(component.attributes.get("model", ""))
        return str(component)

    def get_component_nodes(self, reference: str) -> List[str]:
        """Returns the nodes to which the component is attached to.

        :param reference: Reference of the circuit element to get the nodes.
        :type reference: str
        :return: List of nodes
        :rtype: list
        """
        component = self.get_component(reference)
        if isinstance(component, SpiceComponent):
            return component.ports
        # For SpiceCircuit, return an empty list since subcircuits don't have
        # ports at this level
        return []

    def get_components(self, prefixes: str = "*") -> List[str]:
        """Returns a list of components that match the list of prefixes indicated on the
        parameter prefixes. In case prefixes is left empty, it returns all the ones that
        are defined by the REPLACE_REGEXES. The list will contain the designators of all
        components found.

        :param prefixes: Type of prefixes to search for. Examples: 'C' for capacitors;
            'R' for Resistors; etc... See prefixes in SPICE documentation for more
            details. The default prefix is '*' which is a special case that returns all
            components.
        :type prefixes: str
        :return: A list of components matching the prefixes demanded.
        """
        answer: List[str] = []
        if prefixes == "*":
            prefixes = "".join(REPLACE_REGEXS.keys())
        for line in self.netlist:
            if isinstance(
                line, SpiceCircuit
            ):  # Only gets components from the main netlist,
                # it currently skips sub-circuits
                continue
            tokens = line.split()
            try:
                if tokens[0][0] in prefixes:
                    answer.append(tokens[0])  # Appends only the designators
            except (IndexError, TypeError):
                pass
        return answer

    def add_component(self, component: Component, **kwargs: Any) -> None:
        """Adds a component to the netlist. The component is added to the end of the
        netlist, just before the .END statement. If the component already exists, it
        will be replaced by the new one.

        :param component: The component to be added to the netlist
        :type component: Component
        :param kwargs: The following keyword arguments are supported: *
            **insert_before** (str) - The reference of the component before which the
            new component should be inserted. * **insert_after** (str) - The reference
            of the component after which the new component should be inserted.
        :return: Nothing
        """
        if self.is_read_only():
            raise ValueError("Editor is read-only")
        if "insert_before" in kwargs:
            line_no = self.get_line_starting_with(kwargs["insert_before"])
        elif "insert_after" in kwargs:
            line_no = self.get_line_starting_with(kwargs["insert_after"])
        else:
            # Insert before backanno instruction
            try:
                # TODO: Improve this. END of line termination could be differnt
                line_no = self.netlist.index(".backanno\n")
            except ValueError:
                line_no = len(self.netlist) - 2

        nodes = " ".join(component.ports)
        model = component.attributes.get("model", "no_model")
        parameters = " ".join(
            [f"{k}={v}" for k, v in component.attributes.items() if k != "model"]
        )
        component_line = (
            f"{component.reference} {nodes} {model} {parameters}{END_LINE_TERM}"
        )
        self.netlist.insert(line_no, component_line)

    def remove_component(self, designator: str) -> None:
        """Removes a component from  the design. Current implementation only allows
        removal of a component from the main netlist, not from a sub-circuit.

        :param designator: Component reference in the design. Ex: V1, C1, R1, etc...
        :type designator: str
        :return: Nothing
        :raises: ComponentNotFoundError - When the component doesn't exist on the
            netlist.
        """
        if self.is_read_only():
            raise ValueError("Editor is read-only")
        line = self.get_line_starting_with(designator)
        self.netlist[line] = ""  # Blanks the line

    @staticmethod
    def add_library_search_paths(*paths: str) -> None:
        """.. deprecated:: 1.1.4
            Use the class method `set_custom_library_paths()` instead.

        Adds search paths for libraries. By default, the local directory and the
        ~username/"Documents/LTspiceXVII/lib/sub will be searched forehand. Only when a
        library is not found in these paths then the paths added by this method will be
        searched.

        :param paths: Path to add to the Search path
        :type paths: str
        :return: Nothing
        """
        SpiceCircuit.set_custom_library_paths(*paths)

    def get_all_nodes(self) -> List[str]:
        """Retrieves all nodes existing on a Netlist.

        :returns: Circuit Nodes
        :rtype: list[str]
        """
        circuit_nodes: List[str] = []
        for line in self.netlist:
            prefix = get_line_command(line)
            if prefix in component_replace_regexs:
                match = component_replace_regexs[prefix].match(line)
                if match:
                    # This separates by all space characters including \t
                    nodes = match.group("nodes").split()
                    for node in nodes:
                        if node not in circuit_nodes:
                            circuit_nodes.append(node)
        return circuit_nodes

    def save_netlist(self, run_netlist_file: Union[str, Path]) -> None:
        # docstring is in the parent class
        # SpiceCircuit objects are only used as subcircuits within a parent netlist
        # They don't save themselves directly to files
        raise NotImplementedError(
            "SpiceCircuit objects cannot be saved directly. "
            "They must be part of a parent netlist."
        )

    def add_instruction(self, instruction: str) -> None:
        """Adds a SPICE instruction to the netlist.

        For example:

        .. code-block:: text

        .tran 10m ; makes a transient simulation .meas TRAN Icurr AVG I(Rs1) TRIG
        time=1.5ms TARG time=2.5ms ; Establishes a measuring .step run 1 100, 1 ; makes
        the simulation run 100 times

        :param instruction: Spice instruction to add to the netlist. This instruction
            will be added at the end of the netlist, typically just before the .BACKANNO
            statement
        :type instruction: str
        :return: Nothing
        """
        if not instruction.endswith(END_LINE_TERM):
            instruction += END_LINE_TERM
        if _is_unique_instruction(instruction):
            # Before adding new instruction, delete previously set unique
            # instructions
            i = 0
            while i < len(self.netlist):
                line = self.netlist[i]
                if _is_unique_instruction(line):
                    self.netlist[i] = instruction
                    break
                i += 1
        elif get_line_command(instruction) == ".PARAM":
            raise RuntimeError(
                'The .PARAM instruction should be added using the "set_parameter"'
                " method"
            )

        # check whether the instruction is already there (dummy proofing)
        # TODO: if adding a .MODEL or .SUBCKT it should verify if it already
        # exists and update it.
        if instruction not in self.netlist:
            # Insert before backanno instruction
            try:
                # TODO: Improve this. END of line termination could be
                # different
                index = self.netlist.index(".backanno\n")
            except ValueError:
                # This is where typically the .backanno instruction is
                index = len(self.netlist) - 2
            self.netlist.insert(index, instruction)

    def remove_instruction(self, instruction: str) -> None:
        # docstring is in the parent class

        # TODO: Make it more intelligent so it recognizes .models, .param and .subckt
        # Because the netlist is stored containing the end of line
        # terminations and because they are added when they
        # they are added to the netlist.
        if not instruction.endswith(END_LINE_TERM):
            instruction += END_LINE_TERM
        if instruction in self.netlist:
            self.netlist.remove(instruction)
            _logger.info('Instruction "%s" removed', instruction)
        else:
            _logger.error('Instruction "%s" not found.', instruction)

    def remove_Xinstruction(self, search_pattern: str) -> None:
        """Remove all instructions matching the given search pattern.

        Args:
            search_pattern: Regular expression pattern to match instructions to remove.
        """
        regex = re.compile(search_pattern, re.IGNORECASE)
        i = 0
        instr_removed = False
        while i < len(self.netlist):
            line = self.netlist[i]
            if isinstance(line, str) and regex.match(line):
                del self.netlist[i]
                instr_removed = True
                _logger.info('Instruction "%s" removed', line)
            else:
                i += 1
        if not instr_removed:
            _logger.error(
                'No instruction matching pattern "%s" was found',
                search_pattern,
            )

    @property
    def circuit_file(self) -> Path:
        """Returns the path of the circuit file.

        Always returns an empty Path for SpiceCircuit.
        """
        return Path("")

    def is_read_only(self) -> bool:
        """Check if the component can be edited. This is useful when the editor is used
        on non modifiable files.

        :return: True if the component is read-only, False otherwise
        :rtype: bool
        """
        return self._readonly

    @staticmethod
    def find_subckt_in_lib(library: str, subckt_name: str) -> Optional["SpiceCircuit"]:
        """Finds a sub-circuit in a library. The search is case-insensitive.

        :param library: path to the library to search
        :type library: str
        :param subckt_name: sub-circuit to search for
        :type subckt_name: str
        :return: Returns a SpiceCircuit instance with the sub-circuit found or None if
            not found
        :rtype: SpiceCircuit
        :meta private:
        """
        # 0. Setup things
        reg_subckt = re.compile(SUBCKT_CLAUSE_FIND + subckt_name, re.IGNORECASE)
        # 1. Find Encoding
        try:
            encoding = detect_encoding(library)
        except EncodingDetectError:
            return None
        #  2. scan the file
        with open(library, encoding=encoding) as lib:
            for line in lib:
                search = reg_subckt.match(line)
                if search:
                    sub_circuit = SpiceCircuit()
                    sub_circuit.netlist.append(line)
                    # Advance to the next non nested .ENDS
                    # pylint: disable=protected-access
                    finished = sub_circuit._add_lines(lib)
                    # pylint: enable=protected-access
                    if finished:
                        # if this is from a lib, don't allow modifications
                        # pylint: disable=protected-access
                        sub_circuit._readonly = True
                        # pylint: enable=protected-access
                        return sub_circuit
        #  3. Return an instance of SpiceCircuit
        return None

    def find_subckt_in_included_libs(
        self, subcircuit_name: str
    ) -> Optional["SpiceCircuit"]:
        """Find the subcircuit in the list of libraries.

        :param subckt_name: sub-circuit to search for
        :type subckt_name: str
        :return: Returns a SpiceCircuit instance with the sub-circuit found or None if
            not found
        :rtype: SpiceCircuit
        :meta private:
        """
        for line in self.netlist:
            if isinstance(
                line, SpiceCircuit
            ):  # If it is a sub-circuit it will simply ignore it.
                continue
            if isinstance(line, str):
                m = lib_inc_regex.match(line)
                if m:  # If it is a library include
                    lib = m.group(2)
                    lib_filename = search_file_in_containers(
                        lib,
                        os.path.split(self.circuit_file)[0],
                        # The directory where the file is located
                        os.path.curdir,  # The current script directory,
                        *self.simulator_lib_paths,  # The simulator's library paths
                        *self.custom_lib_paths,
                    )  # The custom library paths
                    if lib_filename:
                        sub_circuit = SpiceEditor.find_subckt_in_lib(
                            lib_filename, subcircuit_name
                        )
                        if sub_circuit:
                            # Success we can go out
                            # by the way, this circuit will have been marked as
                            # readonly
                            return sub_circuit
        if self.parent is not None:
            # try searching on parent netlists
            return self.parent.find_subckt_in_included_libs(subcircuit_name)
        return None

    def remove_x_instruction(self, search_pattern: str) -> None:
        """Removes a SPICE instruction from the netlist based on a search pattern.

        This method calls remove_Xinstruction for backward compatibility.
        """
        self.remove_Xinstruction(search_pattern)


class SpiceEditor(SpiceCircuit):
    """Provides interfaces to manipulate SPICE netlist files. The class doesn't update
    the netlist file itself. After implementing the modifications the user should call
    the "save_netlist" method to write a new netlist file.

    :param netlist_file: Name of the .NET file to parse
    :type netlist_file: str or Path
    :param encoding: Forcing the encoding to be used on the circuit netlile read.
        Defaults to 'autodetect' which will call a function that tries to detect the
        encoding automatically. This however is not 100% foolproof.
    :type encoding: str, optional
    :param create_blank: Create a blank '.net' file when 'netlist_file' not exist. False
        by default
    :type create_blank: bool, optional
    """

    simulation_command_update_functions: Dict[
        str, Callable[[str, Union[str, int, float]], str]
    ] = {}

    def __init__(
        self,
        netlist_file: Union[str, Path],
        encoding: str = "autodetect",
        create_blank: bool = False,
    ) -> None:
        super().__init__()
        self.netlist_file = Path(netlist_file)
        if create_blank:
            # when user want to create a blank netlist file, and didn't set
            # encoding.
            self.encoding = "utf-8"
        else:
            if encoding == "autodetect":
                try:
                    self.encoding = detect_encoding(
                        self.netlist_file, r"^\*"
                    )  # Normally the file will start with a '*'
                except EncodingDetectError as err:
                    raise err
            else:
                self.encoding = encoding
        self.reset_netlist(create_blank)

    @property
    def circuit_file(self) -> Path:
        # docstring inherited from BaseSchematic
        return self.netlist_file

    def add_instruction(self, instruction: str) -> None:
        """Adds a SPICE instruction to the netlist.

        For example:

        .. code-block:: text

        .tran 10m ; makes a transient simulation .meas TRAN Icurr AVG I(Rs1) TRIG
        time=1.5ms TARG time=2.5ms ; Establishes a measuring .step run 1 100, 1 ; makes
        the simulation run 100 times

        :param instruction: Spice instruction to add to the netlist. This instruction
            will be added at the end of the netlist, typically just before the .BACKANNO
            statement
        :type instruction: str
        :return: Nothing
        """
        if not instruction.endswith(END_LINE_TERM):
            instruction += END_LINE_TERM
        if _is_unique_instruction(instruction):
            # Before adding new instruction, delete previously set unique
            # instructions
            i = 0
            while i < len(self.netlist):
                line = self.netlist[i]
                if _is_unique_instruction(line):
                    self.netlist[i] = instruction
                    break
                i += 1
        elif get_line_command(instruction) == ".PARAM":
            raise RuntimeError(
                'The .PARAM instruction should be added using the "set_parameter"'
                " method"
            )

        # check whether the instruction is already there (dummy proofing)
        # TODO: if adding a .MODEL or .SUBCKT it should verify if it already
        # exists and update it.
        if instruction not in self.netlist:
            # Insert before backanno instruction
            try:
                # TODO: Improve this. END of line termination could be
                # different
                index = self.netlist.index(".backanno\n")
            except ValueError:
                # This is where typically the .backanno instruction is
                index = len(self.netlist) - 2
            self.netlist.insert(index, instruction)

    def remove_instruction(self, instruction: str) -> None:
        # docstring is in the parent class

        # TODO: Make it more intelligent so it recognizes .models, .param and .subckt
        # Because the netlist is stored containing the end of line
        # terminations and because they are added when they
        # they are added to the netlist.
        if not instruction.endswith(END_LINE_TERM):
            instruction += END_LINE_TERM
        if instruction in self.netlist:
            self.netlist.remove(instruction)
            _logger.info('Instruction "%s" removed', instruction)
        else:
            _logger.error('Instruction "%s" not found.', instruction)

    def remove_Xinstruction(self, search_pattern: str) -> None:
        """Remove all instructions matching the given search pattern.

        Args:
            search_pattern: Regular expression pattern to match instructions to remove.
        """
        regex = re.compile(search_pattern, re.IGNORECASE)
        i = 0
        instr_removed = False
        while i < len(self.netlist):
            line = self.netlist[i]
            if isinstance(line, str) and regex.match(line):
                del self.netlist[i]
                instr_removed = True
                _logger.info('Instruction "%s" removed', line)
            else:
                i += 1
        if not instr_removed:
            _logger.error(
                'No instruction matching pattern "%s" was found',
                search_pattern,
            )

    def remove_x_instruction(self, search_pattern: str) -> None:
        """Removes a SPICE instruction from the netlist based on a search pattern.

        This method calls remove_Xinstruction for backward compatibility.
        """
        self.remove_Xinstruction(search_pattern)

    def save_netlist(self, run_netlist_file: Union[str, Path]) -> None:
        # docstring is in the parent class
        if isinstance(run_netlist_file, str):
            run_netlist_file = Path(run_netlist_file)

        with open(run_netlist_file, "w", encoding=self.encoding) as f:
            lines = iter(self.netlist)
            for line in lines:
                if isinstance(line, SpiceCircuit):
                    # pylint: disable=protected-access
                    line._write_lines(f)
                    # pylint: enable=protected-access
                else:
                    # Writes the modified sub-circuits at the end just before the .END
                    # clause
                    if line.upper().startswith(".END"):
                        # write here the modified sub-circuits
                        for sub in self.modified_subcircuits.values():
                            # pylint: disable=protected-access
                            sub._write_lines(f)
                            # pylint: enable=protected-access
                    f.write(line)

    def reset_netlist(self, create_blank: bool = False) -> None:
        """Removes all previous edits done to the netlist, i.e. resets it to the
        original state.

        :returns: Nothing
        """
        # Initialize the netlist without calling super().reset_netlist()
        self.netlist.clear()
        self.modified_subcircuits.clear()

        if create_blank:
            lines = ["* netlist generated from cespy", ".end"]
            finished = self._add_lines(iter(lines))
            if not finished:
                raise SyntaxError("Netlist with missing .END or .ENDS statements")
        elif hasattr(self, "netlist_file") and self.netlist_file.exists():
            with open(
                self.netlist_file,
                "r",
                encoding=self.encoding,
                errors="replace",
            ) as f:
                # Creates an iterator object to consume the file
                finished = self._add_lines(f)
                if not finished:
                    raise SyntaxError("Netlist with missing .END or .ENDS statements")
                # else:
                #     for _ in lines:  # Consuming the rest of the file.
                #         pass  # print("Ignoring %s" % _)
        elif hasattr(self, "netlist_file"):
            _logger.error("Netlist file not found: %s", self.netlist_file)

    def run(
        self,
        wait_resource: bool = True,
        callback: Optional[Union[Type[Any], Callable[[Path, Path], Any]]] = None,
        timeout: Optional[float] = None,
        *,
        run_filename: Optional[str] = None,
        simulator: Optional[Any] = None,
    ) -> Any:
        """.. deprecated:: 1.0 Use the `run` method from the `SimRunner` class instead.

        Convenience function for maintaining legacy with legacy code. Runs the SPICE
        simulation.
        """
        runner = SimRunner(simulator=simulator)
        return runner.run(
            self,
            wait_resource=wait_resource,
            callback=callback,
            timeout=timeout,
            run_filename=run_filename,
        )
