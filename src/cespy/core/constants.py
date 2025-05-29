"""
Centralized constants for cespy.

This module contains all constants, magic strings, and default values used
throughout the cespy library to improve maintainability and consistency.
"""

from typing import Dict, List, Tuple

# File extensions


class FileExtensions:
    """File extensions used by various simulators and tools."""

    ASC = ".asc"  # LTSpice schematic
    NET = ".net"  # SPICE netlist
    RAW = ".raw"  # Raw simulation output
    QRAW = ".qraw"  # QSpice raw output
    QSCH = ".qsch"  # QSpice schematic
    ASY = ".asy"  # Symbol file
    OP_RAW = ".op.raw"  # Operating point raw
    LOG = ".log"  # Log file
    OUT = ".out"  # Output file
    ERR = ".err"  # Error file
    CIR = ".cir"  # Circuit file
    SP = ".sp"  # SPICE file
    LIB = ".lib"  # Library file
    INC = ".inc"  # Include file
    MEAS = ".meas"  # Measurement file

    # Collections
    NETLIST_EXTENSIONS = [NET, CIR, SP]
    SCHEMATIC_EXTENSIONS = [ASC, QSCH]
    OUTPUT_EXTENSIONS = [RAW, QRAW, LOG, OUT, MEAS]
    ALL_EXTENSIONS = (
        NETLIST_EXTENSIONS + SCHEMATIC_EXTENSIONS + OUTPUT_EXTENSIONS + [ASY, LIB, INC]
    )


# Simulator identifiers


class Simulators:
    """Simulator names and identifiers."""

    LTSPICE = "ltspice"
    NGSPICE = "ngspice"
    QSPICE = "qspice"
    XYCE = "xyce"

    ALL = [LTSPICE, NGSPICE, QSPICE, XYCE]


# Default configuration values


class Defaults:
    """Default configuration values."""

    # Timeouts
    SIMULATION_TIMEOUT = 600.0  # 10 minutes
    SERVER_TIMEOUT = 300.0  # 5 minutes

    # Parallel execution
    PARALLEL_SIMS = 4

    # Server settings
    SERVER_PORT = 9000
    SERVER_HOST = "localhost"

    # File handling
    OUTPUT_FOLDER = "./temp"
    MAX_OUTPUT_SIZE = 30000  # Maximum characters for output truncation

    # Process management
    PROCESS_POLL_INTERVAL = 0.1  # seconds


# Encoding constants


class Encodings:
    """Text encoding constants."""

    UTF8 = "utf-8"
    UTF16 = "utf-16"
    UTF16_LE = "utf_16_le"
    CP1252 = "cp1252"
    CP1250 = "cp1250"
    WINDOWS_1252 = "windows-1252"
    SHIFT_JIS = "shift_jis"
    ASCII = "ascii"
    LATIN1 = "latin-1"
    AUTODETECT = "autodetect"

    # Default encoding for different platforms
    DEFAULT = UTF8
    WINDOWS_DEFAULT = CP1252

    # Encoding detection order
    DETECTION_ORDER = [UTF8, UTF16, WINDOWS_1252, UTF16_LE, CP1252, CP1250, SHIFT_JIS]


# Component type identifiers


class ComponentTypes:
    """SPICE component type identifiers."""

    RESISTOR = "R"
    CAPACITOR = "C"
    INDUCTOR = "L"
    VOLTAGE_SOURCE = "V"
    CURRENT_SOURCE = "I"
    DIODE = "D"
    BIPOLAR_TRANSISTOR = "Q"
    JFET = "J"
    MOSFET = "M"
    MESFET = "Z"
    SUBCIRCUIT = "X"
    TRANSMISSION_LINE = "T"
    COUPLED_INDUCTORS = "K"
    VOLTAGE_CONTROLLED_VOLTAGE_SOURCE = "E"
    CURRENT_CONTROLLED_CURRENT_SOURCE = "F"
    VOLTAGE_CONTROLLED_CURRENT_SOURCE = "G"
    CURRENT_CONTROLLED_VOLTAGE_SOURCE = "H"
    BEHAVIORAL_SOURCE = "B"
    SWITCH_VOLTAGE_CONTROLLED = "S"
    SWITCH_CURRENT_CONTROLLED = "W"
    UNIFORM_RC_LINE = "U"
    LOSSY_TRANSMISSION_LINE = "O"

    # Component categories
    PASSIVE_COMPONENTS = [RESISTOR, CAPACITOR, INDUCTOR]
    SOURCES = [VOLTAGE_SOURCE, CURRENT_SOURCE]
    SEMICONDUCTORS = [DIODE, BIPOLAR_TRANSISTOR, JFET, MOSFET, MESFET]
    CONTROLLED_SOURCES = [
        VOLTAGE_CONTROLLED_VOLTAGE_SOURCE,
        CURRENT_CONTROLLED_CURRENT_SOURCE,
        VOLTAGE_CONTROLLED_CURRENT_SOURCE,
        CURRENT_CONTROLLED_VOLTAGE_SOURCE,
    ]


# LTSpice specific constants


class LTSpiceConstants:
    """Constants specific to LTSpice."""

    # Parameter names
    VALUE = "Value"
    VALUE2 = "Value2"
    SPICE_MODEL = "SpiceModel"
    SPICE_LINE = "SpiceLine"
    SPICE_LINE2 = "SpiceLine2"

    # Attributes
    INST_NAME = "InstName"
    DEF_SUB = "Def_Sub"

    # File format
    DEFAULT_VERSION = "Version 4"
    DEFAULT_SHEET = "SHEET 1 0 0"

    # Text alignments
    TEXT_ALIGN_LEFT = "Left"
    TEXT_ALIGN_RIGHT = "Right"
    TEXT_ALIGN_CENTER = "Center"
    TEXT_ALIGN_TOP = "Top"
    TEXT_ALIGN_BOTTOM = "Bottom"
    TEXT_ALIGN_INVISIBLE = "Invisible"

    # Rotation angles
    ROTATION_ANGLES = [0, 45, 90, 135, 180, 225, 270, 315]
    MIRROR_OFFSET = 360  # Add to angle for mirrored components


# Raw file constants


class RawFileConstants:
    """Constants for raw simulation output files."""

    # Data types
    TYPE_REAL = "real"
    TYPE_COMPLEX = "complex"
    TYPE_DOUBLE = "double"

    # Flags
    FLAG_FORWARD = "forward"
    FLAG_STEPPED = "stepped"
    FLAG_LOG = "log"
    FLAG_FAST_ACCESS = "FastAccess"

    # Data formats
    FORMAT_ASCII = "ASCII"
    FORMAT_BINARY = "BINARY"

    # Measurement types
    MEAS_TIME = "time"
    MEAS_VOLTAGE = "voltage"
    MEAS_CURRENT = "current"
    MEAS_DEVICE_CURRENT = "device_current"
    MEAS_SUBCKT_CURRENT = "subckt_current"


# Simulation types


class SimulationTypes:
    """Standard SPICE simulation types."""

    OP = "Operation Point"
    DC = "DC transfer characteristic"
    AC = "AC Analysis"
    TRAN = "Transient Analysis"
    NOISE = "Noise Spectral Density - (V/Hz½ or A/Hz½)"
    TF = "Transfer Function"

    # Short names for command line
    SHORT_NAMES = {"op": OP, "dc": DC, "ac": AC, "tran": TRAN, "noise": NOISE, "tf": TF}


# Line terminators


class LineTerminators:
    """Line terminator constants."""

    UNIX = "\n"
    WINDOWS = "\r\n"
    MAC_CLASSIC = "\r"

    # Platform defaults
    DEFAULT = UNIX


# SPICE syntax constants


class SpiceSyntax:
    """SPICE netlist syntax constants."""

    COMMENT_CHAR = "*"
    CONTINUATION_CHAR = "+"
    SUBCKT_START = ".SUBCKT"
    SUBCKT_END = ".ENDS"
    PARAM_PREFIX = ".PARAM"
    LIB_PREFIX = ".LIB"
    INC_PREFIX = ".INC"
    MODEL_PREFIX = ".MODEL"
    END_STATEMENT = ".END"


# Error messages


class ErrorMessages:
    """Standard error messages."""

    SIMULATOR_NOT_FOUND = "Simulator executable not found: {}"
    INVALID_COMPONENT = "Invalid component reference: {}"
    FILE_NOT_FOUND = "File not found: {}"
    SIMULATION_TIMEOUT = "Simulation timed out after {} seconds"
    INVALID_FILE_FORMAT = "Invalid file format: {}"
    ENCODING_ERROR = "Failed to decode file with encoding: {}"


# Server/Client constants


class ServerConstants:
    """Constants for client-server operations."""

    XML_RPC_PROTOCOL = "http"
    DEFAULT_ENCODING = "utf-8"
    MAX_RETRIES = 3
    RETRY_DELAY = 1.0  # seconds


# Supported simulators and file extensions mapping
SUPPORTED_SIMULATORS: List[str] = Simulators.ALL
SPICE_EXTENSIONS: List[str] = FileExtensions.ALL_EXTENSIONS

# Default values export
DEFAULT_ENCODING: str = Encodings.DEFAULT
DEFAULT_TIMEOUT: float = Defaults.SIMULATION_TIMEOUT
