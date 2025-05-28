"""Utilities for handling Windows short filenames.

This module provides functions to get Windows short path names (8.3 format)
which are useful when dealing with paths that contain spaces or special
characters in Windows environments.

Copyright (c) 2023 Nuno Brum
License: GPL-3.0
"""

# -*- coding: utf-8 -*-
# -------------------------------------------------------------------------------
#
#  ███████╗██████╗ ██╗ ██████╗███████╗██╗     ██╗██████╗
#  ██╔════╝██╔══██╗██║██╔════╝██╔════╝██║     ██║██╔══██╗
#  ███████╗██████╔╝██║██║     █████╗  ██║     ██║██████╔╝
#  ╚════██║██╔═══╝ ██║██║     ██╔══╝  ██║     ██║██╔══██╗
#  ███████║██║     ██║╚██████╗███████╗███████╗██║██████╔╝
#  ╚══════╝╚═╝     ╚═╝ ╚═════╝╚══════╝╚══════╝╚═╝╚═════╝
#
# Name:        windows_short_names.py
# Purpose:     Functions to get the short path name of a file on Windows
#
# Author:      Nuno Brum (nuno.brum@gmail.com)
#
# Created:     28-03-2024
# Licence:     refer to the LICENSE file
#
# -------------------------------------------------------------------------------

# From
# https://stackoverflow.com/questions/23598289/how-to-get-windows-short-file-name-in-python
import sys


def get_short_path_name(long_name: str) -> str:
    """Gets the short path name of a given long path.

    http://stackoverflow.com/a/23598461/200291
    """
    if sys.platform != "win32":
        # On non-Windows platforms, just return the original path
        return long_name

    import ctypes
    from ctypes import wintypes

    # Get the Windows API function
    _GetShortPathNameW = (
        ctypes.windll.kernel32.GetShortPathNameW
    )  # pyright: ignore[reportAttributeAccessIssue]
    _GetShortPathNameW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.LPWSTR,
        wintypes.DWORD,
    ]
    _GetShortPathNameW.restype = wintypes.DWORD

    # GetShortPathName is used by first calling it without a destination
    # buffer. It will return the number of characters
    # you need to make the destination buffer. You then call it again with
    # a buffer of that size. If, due to a TOCTTOU
    # problem, the return value is still larger, keep trying until you've got it right. So:
    output_buf_size = 0
    while True:
        output_buf = ctypes.create_unicode_buffer(output_buf_size)
        needed = _GetShortPathNameW(long_name, output_buf, output_buf_size)
        if output_buf_size >= needed:
            return output_buf.value
        output_buf_size = needed
