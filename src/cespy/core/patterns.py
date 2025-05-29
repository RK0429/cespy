"""
Centralized regex patterns for cespy.

This module contains all regex patterns used throughout the cespy library,
organized by category to reduce duplication and improve maintainability.
"""

import re
from typing import Dict, Pattern

# Component value patterns
COMPONENT_VALUE_PATTERN: Pattern[str] = re.compile(r'value=([^"\s]+)')
COMPONENT_REF_PATTERN: Pattern[str] = re.compile(r"^[RLCVIJKEFHGBDMOQSTUWXZ]\w+")

# Parameter patterns
PARAM_PATTERN: Pattern[str] = re.compile(r"\.param\s+(\w+)\s*=\s*(.+)", re.IGNORECASE)
PARAM_ASSIGNMENT_PATTERN: Pattern[str] = re.compile(
    r"(?P<name>\w+)\s*[= ]\s*(?P<value>(?P<cb>\{)?(?(cb)[^\}]*\}|[\d\.\+\-Ee]+[a-zA-Z%]*))"
)

# Voltage/Current/Power reference patterns
VOLTAGE_REF_PATTERN_1: Pattern[str] = re.compile(r"V\((\w+),0\)")
VOLTAGE_REF_PATTERN_2: Pattern[str] = re.compile(r"V\(0,(\w+)\)")
VOLTAGE_REF_PATTERN_3: Pattern[str] = re.compile(r"V\((\w+),(\w+)\)")
VIP_REF_PATTERN: Pattern[str] = re.compile(r"(V|I|P)\((\w+)\)")
VI_REF_PATTERN: Pattern[str] = re.compile(r"(V|I)\((\w+)\)")

# Unit patterns
UNIT_PATTERN: Pattern[str] = re.compile(r"(\d+)((mho)|(ohm))")

# Log file patterns
SECTION_TITLE_PATTERN: Pattern[str] = re.compile(r"^\s*--- (.*) ---\s*$")
WHITESPACE_PATTERN: Pattern[str] = re.compile(r"\s+")

# Step information patterns
LTSPICE_STEP_INFO_PATTERN: Pattern[str] = re.compile(
    r"Step Information: ([\w=\d\. \-]+) +\((?:Run|Step): (\d*)/\d*\)\n"
)
LTSPICE_RUN_INFO_PATTERN: Pattern[str] = re.compile(
    r"([\w=\d\. -]+) +\(Run: (\d*)/\d*\)\n"
)
QSPICE_STEP_PATTERN: Pattern[str] = re.compile(
    r"^\s*(\d+) of \d+ steps:\s+\.step (.*)$"
)

# Measurement patterns
MEAS_STATEMENT_PATTERN: Pattern[str] = re.compile(r"^\.meas (\w+) (\w+) (.*)$")
MEAS_DATA_PATTERN: Pattern[str] = re.compile(
    r"^(?P<name>\w+)(:\s+.*)?=(?P<value>[\d(inf)E+\-\(\)dB,°(-/\w]+)"
    r"( FROM (?P<from>[\d\.E+-]*) TO (?P<to>[\d\.E+-]*)|( at (?P<at>[\d\.E+-]*)))?"
)
FLOAT_PATTERN: Pattern[str] = re.compile(r"\d+\.\d+")

# Complex number pattern (LTSpice format)
COMPLEX_NUMBER_PATTERN: Pattern[str] = re.compile(
    r"\((?P<mag>.*?)(?P<dB>dB)?,(?P<ph>.*?)(?P<degrees>°)?\)"
)

# SPICE component patterns
SPICE_PATTERNS: Dict[str, Pattern[str]] = {
    # Behavioral source
    "B": re.compile(
        r"^(?P<designator>B§?[VI]?\w+)(?P<nodes>(\s+\S+){2})\s+(?P<value>.*)$"
    ),
    # Capacitor
    "C": re.compile(
        r"^(?P<designator>C§?\w+)(?P<nodes>(\s+\S+){2})(?P<model>\s+\w+)?\s+"
        r"(?P<value>(?P<formula>{)?(?(formula).*}|[-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?[muµnpfgt]?F?))"
        r"(?P<params>(\s+\w+\s*(=\s*[\w\{\}\(\)\-\+\*\/%\.]+)?)*)?"
    ),
    # Diode
    "D": re.compile(
        r"^(?P<designator>D§?\w+)(?P<nodes>(\s+\S+){2})\s+(?P<value>\w+)"
        r"(?P<params>(\s+\w+\s*(=\s*[\w\-\+\*\/%\{\}\(\)\.]+)?)*)?"
    ),
    # Voltage controlled voltage source
    "E": re.compile(r"^(?P<designator>E§?\w+)(?P<nodes>(\s+\S+){2})(?P<value>.*)$"),
    # Current controlled current source
    "F": re.compile(
        r"^(?P<designator>F§?\w+)(?P<nodes>(\s+\S+){2})\s+(?P<value>\w+)\s+(?P<factor>[\+\-]?\d*\.?\d*[eE]?[\+\-]?\d*)"
    ),
    # Voltage controlled current source
    "G": re.compile(r"^(?P<designator>G§?\w+)(?P<nodes>(\s+\S+){2})(?P<value>.*)$"),
    # Current controlled voltage source
    "H": re.compile(
        r"^(?P<designator>H§?\w+)(?P<nodes>(\s+\S+){2})\s+(?P<value>\w+)"
        r"\s+(?P<factor>[\+\-]?\d*\.?\d+[eE]?[\+\-]?\d*)"
    ),
    # Current source
    "I": re.compile(r"^(?P<designator>I§?\w+)(?P<nodes>(\s+\S+){2})\s+(?P<value>.*)$"),
    # JFET
    "J": re.compile(
        r"^(?P<designator>J§?\w+)(?P<nodes>(\s+\S+){3})\s+(?P<value>\w+)"
        r"(?P<params>(\s+\w+\s*(=\s*[\+\-\w\*\/%\{\}\(\)\.]+)?)*)?"
    ),
    # Coupled inductors
    "K": re.compile(
        r"^(?P<designator>K§?\w+)\s+(?P<inductor1>L§?\w+)\s+(?P<inductor2>L§?\w+)"
        r"\s+(?P<value>[\+\-]?\d*\.?\d+[eE]?[\+\-]?\d*)"
        r"(?P<params>(\s+\w+\s*(=\s*[\w\-\+\*\/%\{\}\(\)\.]+)?)*)?"
    ),
    # Inductor
    "L": re.compile(
        r"^(?P<designator>L§?\w+)(?P<nodes>(\s+\S+){2})(?P<model>\s+\w+)?\s+"
        r"(?P<value>(?P<formula>{)?(?(formula).*}|[\+\-]?[0-9]*\.?[0-9]+([eE][\+\-]?[0-9]+)?[muµnpfk]?H?))"
        r"(?P<params>(\s+\w+\s*(=\s*[\w\-\+\*\/%\{\}\(\)\.]+)?)*)?"
    ),
    # MOSFET
    "M": re.compile(
        r"^(?P<designator>M§?\w+)(?P<nodes>(\s+\S+){3,4})\s+(?P<value>[\w\.]+)"
        r"(?P<params>(\s+\w+\s*(=\s*[\w\-\+\*\/%\{\}\(\)\.]+)?)*)?"
    ),
    # Lossy transmission line
    "O": re.compile(
        r"^(?P<designator>O§?\w+)(?P<nodes>(\s+\S+){4})\s+(?P<value>\w+)"
        r"(?P<params>.*)"
    ),
    # Bipolar transistor
    "Q": re.compile(
        r"^(?P<designator>Q§?\w+)(?P<nodes>(\s+\S+){3,4})\s+(?P<value>[\w\.]+)"
        r"(?P<params>(\s+\w+\s*(=\s*[\w\-\+\*\/%\{\}\(\)\.]+)?)*)?"
    ),
    # Resistor
    "R": re.compile(
        r"^(?P<designator>R§?\w+)(?P<nodes>(\s+\S+){2})(?P<model>\s+\w+)?\s+"
        r"(?P<value>(?P<formula>\{)?(?(formula).*\}|[\+\-]?[0-9\.E]+\s*[TGMkmuµnp]?(?P<unit>[Ω☐■◘]|ohm)?))"
        r"(?P<params>(\s+\w+\s*(=\s*[\w\-\+\*\/%\{\}\(\)\.]+)?)*)?"
    ),
    # Voltage controlled switch
    "S": re.compile(
        r"^(?P<designator>S§?\w+)(?P<nodes>(\s+\S+){4})\s+(?P<value>[\w\.]+)"
        r"(?P<params>.*)?"
    ),
    # Transmission line
    "T": re.compile(r"^(?P<designator>T§?\w+)(?P<nodes>(\s+\S+){4})" r"(?P<params>.*)"),
    # Uniform RC line
    "U": re.compile(r"^(?P<designator>U§?\w+)(?P<nodes>(\s+\S+){3})" r"(?P<model>.*)"),
    # Voltage source
    "V": re.compile(r"^(?P<designator>V§?\w+)(?P<nodes>(\s+\S+){2})\s+(?P<value>.*)$"),
    # Current controlled switch
    "W": re.compile(
        r"^(?P<designator>W§?\w+)(?P<nodes>(\s+\S+){2})\s+(?P<value>\w+)"
        r"\s+(?P<model>[\w\.]+)(?P<params>.*)"
    ),
    # Subcircuit
    "X": re.compile(
        r"^(?P<designator>X§?\w+)(?P<nodes>(\s+\S+)+)\s+(?P<value>[\w\./\:]+)"
        r"(?P<params>(\s+\w+\s*(=\s*[\w\-\+\*\/%\{\}\(\)\.]+)?)*)"
    ),
    # MESFET
    "Z": re.compile(
        r"^(?P<designator>Z§?\w+)(?P<nodes>(\s+\S+){3})\s+(?P<value>\w+)"
        r"(?P<params>(\s+\w+\s*(=\s*[\w\-\+\*\/%\{\}\(\)\.]+)?)*)?"
    ),
}

# Subcircuit and library patterns
SUBCKT_PATTERN: Pattern[str] = re.compile(r"^\.SUBCKT\s+(?P<name>[\w\.]+)")
LIB_INC_PATTERN: Pattern[str] = re.compile(r"^\.(LIB|INC)\s+(.*)$")

# LTSpice specific patterns
TEXT_COMMAND_PATTERN: Pattern[str] = re.compile(
    r"TEXT (-?\d+)\s+(-?\d+)\s+V?(Left|Right|Top|Bottom|Center|Invisible)\s(\d+)"
    r"\s*(?P<type>[!;])(?P<text>.*)"
)

# ASC TEXT pattern (same as TEXT_COMMAND_PATTERN but with IGNORECASE)
ASC_TEXT_PATTERN: Pattern[str] = re.compile(
    r"TEXT"
    r" (-?\d+)\s+(-?\d+)\s+V?(Left|Right|Top|Bottom|Center|Invisible)\s"
    r"(\d+)\s*(?P<type>[!;])(?P<text>.*)",
    re.IGNORECASE,
)

# QSpice specific patterns
QSPICE_PARAM_PATTERN: Pattern[str] = re.compile(r"(\w+)=<(.*)>")
QSPICE_SPLIT_PATTERN: Pattern[str] = re.compile(r'[^"\s]+|"[^"]*"')

# File format patterns
VERSION_PATTERN: Pattern[str] = re.compile(r"^VERSION ")

# Engineering notation pattern
ENG_NOTATION_PATTERN: Pattern[str] = re.compile(
    r"[-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?[TGMkmuµnpf]?"
)

# Float number pattern (alias for engineering notation)
FLOAT_NUMBER_PATTERN: Pattern[str] = ENG_NOTATION_PATTERN
