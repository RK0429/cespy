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
# -------------------------------------------------------------------------------
# Name:        international_support.py
# Purpose:     Pragmatic way to detect encoding.
#
# Author:      Nuno Brum (nuno.brum@gmail.com) with special thanks to
#              Fugio Yokohama (yokohama.fujio@gmail.com)
#
# Created:     14-05-2022
# Licence:     refer to the LICENSE file
# -------------------------------------------------------------------------------
"""International Support functions Not using other known unicode detection libraries
because we don't need something so complicated.

LTSpice only supports for the time being a reduced set of encodings.
"""

import re
from pathlib import Path
from typing import Union

# Core imports
from ..core import constants as core_constants


class EncodingDetectError(Exception):
    """Exception raised when the encoding of a file cannot be detected."""


def detect_encoding(
    file_path: Union[str, Path],
    expected_pattern: str = "",
    re_flags: Union[int, re.RegexFlag] = 0,
) -> str:
    """Simple strategy to detect file encoding.  If an expected_str is given the
    function will scan through the possible encodings and return a match. If an expected
    string is not given, it will use the second character is null, high chances are that
    this file has an 'utf_16_le' encoding, otherwise it is assuming that it is 'utf-8'.
    :param file_path: path to the filename :type file_path: str :param expected_pattern:
    regular expression to match the first line of the file :type expected_pattern: str
    :param re_flags: flags to be used in the regular expression :type re_flags: int
    :return: detected encoding.

    :rtype: str
    """
    for encoding in (
        core_constants.Encodings.UTF8,
        core_constants.Encodings.UTF16,
        core_constants.Encodings.WINDOWS_1252,
        core_constants.Encodings.UTF16_LE,
        core_constants.Encodings.CP1252,
        core_constants.Encodings.CP1250,
        core_constants.Encodings.SHIFT_JIS,
    ):
        try:
            with open(file_path, "r", encoding=encoding) as f:
                lines = f.read()
                f.seek(0)
        except UnicodeDecodeError:
            # This encoding didn't work, let's try again
            continue
        except UnicodeError:
            # This encoding didn't work, let's try again
            continue
        else:
            if len(lines) == 0:
                # Empty file
                continue
            if expected_pattern:
                # Search expected pattern at start of any line using MULTILINE
                # flag
                if not re.search(expected_pattern, lines, re_flags | re.MULTILINE):
                    # File did not have the expected string for this encoding
                    continue
            if encoding == core_constants.Encodings.UTF8 and lines[1] == "\x00":
                continue
            return encoding
    # Handle failure after trying all encodings
    if expected_pattern:
        raise EncodingDetectError(
            f'Expected pattern "{expected_pattern}" not found in file:{file_path}'
        )
    raise EncodingDetectError(f"Unable to detect encoding on log file: {file_path}")
