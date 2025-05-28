"""Iterator classes for parameter sweeps in SPICE simulations.

This module provides different types of iterators for generating parameter
values during simulation sweeps, including linear, logarithmic, and list-based
iterators.

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
# Name:        sweep_iterators.py
# Purpose:     Iterators to use for sweeping values
#
# Author:      Nuno Brum (nuno.brum@gmail.com)
#
# Created:     24-07-2020
# Licence:     refer to the LICENSE file
#
# -------------------------------------------------------------------------------

import math
from typing import Iterable, Optional, Union

__author__ = "Nuno Canto Brum <nuno.brum@gmail.com>"
__copyright__ = "Copyright 2021, Fribourg Switzerland"

__all__ = ["sweep", "sweep_n", "sweep_log", "sweep_log_n"]


class BaseIterator:
    """Common implementation to all Iterator classes."""

    def __init__(
        self,
        start: Union[int, float],
        stop: Optional[Union[int, float]] = None,
        step: Union[int, float] = 1,
    ):
        self.start: Union[int, float]
        self.stop: Union[int, float]
        self.step: Union[int, float] = step

        if stop is None:
            self.stop = start
            self.start = 0
        else:
            self.start = start
            self.stop = stop
        self.finished = False

    def __iter__(self) -> "BaseIterator":
        self.finished = False
        return self

    def __next__(self) -> Union[int, float]:
        raise NotImplementedError("This function needs to be overriden")


class Sweep(BaseIterator):
    """Generator function to be used in sweeps.

    Advantages towards the range python built-in functions
    - Supports floating point arguments
    - Supports both up and down sweeps
    Usage:

        >>> list(Sweep(0.3, 1.1, 0.2))
        [0.3, 0.5, 0.7, 0.9000000000000001, 1.1]
        >>> list(Sweep(15, -15, 2.5))
        [15, 12.5, 10.0, 7.5, 5.0, 2.5, 0.0, -2.5, -5.0, -7.5, -10.0, -12.5, -15.0]
    """

    def __init__(
        self,
        start: Union[int, float],
        stop: Optional[Union[int, float]] = None,
        step: Union[int, float] = 1,
    ):
        super().__init__(start, stop, step)
        assert step != 0, "Step cannot be 0"
        if self.step < 0 and self.start < self.stop:
            # The sign of the step determines whether it counts up or down.
            self.start, self.stop = self.stop, self.start
        elif self.step > 0 and self.stop < self.start:
            self.step = -self.step  # In this case invert the sigh
        self.niter = 0

    def __iter__(self) -> "sweep":
        super().__iter__()
        # Resets the iterator
        self.niter = 0
        return self

    def __next__(self) -> Union[int, float]:
        val = self.start + self.niter * self.step
        self.niter += 1
        if (self.step > 0 and val <= self.stop) or (self.step < 0 and val >= self.stop):
            return val
        self.finished = True
        raise StopIteration


def sweep_n(
    start: Union[int, float], stop: Union[int, float], n: int
) -> Iterable[float]:
    """Helper function. Generator function that generates a 'N' number of points between
    a start and a stop interval.

    Advantages towards the range python built-in functions
    - Supports floating point arguments
    - Supports both up and down sweeps-
    Usage:

        >>> list(sweep_n(0.3, 1.1, 5))
        [0.3, 0.5, 0.7, 0.9000000000000001, 1.1]
        >>> list(sweep_n(15, -15, 13))
        [15, 12.5, 10.0, 7.5, 5.0, 2.5, 0.0, -2.5, -5.0, -7.5, -10.0, -12.5, -15.0]
    """
    return Sweep(start, stop, (stop - start) / (n - 1))


class SweepLog(BaseIterator):
    """Generator function to be used in logarithmic sweeps.

    Advantages towards the range python built-in functions
    - Supports floating point arguments
    - Supports both up and down sweeps.
    Usage:

        >>> list(SweepLog(0.1, 11e3, 10))
        [0.1, 1.0, 10.0, 100.0, 1000.0, 10000.0]
        >>> list(SweepLog(1000, 1, 2))
        [1000, 500.0, 250.0, 125.0, 62.5, 31.25, 15.625, 7.8125, 3.90625, 1.953125]
    """

    def __init__(
        self,
        start: Union[int, float],
        stop: Optional[Union[int, float]] = None,
        step: Union[int, float] = 10,
    ):
        if stop is None:
            stop = start
            start = 1
        # Ensure step is not None before using it
        actual_step: Union[int, float] = step if step is not None else 10
        super().__init__(start, stop, actual_step)
        assert (
            actual_step != 1 and actual_step > 0
        ), "Step must be higher than 0 and not 1"
        if self.start < self.stop and self.step < 1:
            self.start, self.stop = self.stop, self.start
        elif self.stop < self.start and self.step > 1:
            self.step = 1 / self.step
        self.val = self.start

    def __iter__(self) -> "SweepLog":
        super().__iter__()
        self.val = self.start
        return self

    def __next__(self) -> Union[int, float]:
        val = self.val  # Store previous value
        self.val *= self.step  # Calculate the next item
        if (self.start < self.stop and val <= self.stop) or (
            self.start > self.stop and val >= self.stop
        ):
            return val
        self.finished = True
        raise StopIteration


class SweepLogN(BaseIterator):
    """Helper function. Generator function that generates a 'N' number of points between
    a start and a stop interval.

    Advantages towards the range python built-in functions
    - Supports floating point arguments
    - Supports both up and down sweeps
    Usage:

        >>> list(SweepLogN(1, 10, 6))  # e.g., [1.0, ..., 10.0]
    """

    def __init__(
        self,
        start: Union[int, float],
        stop: Union[int, float],
        number_of_elements: int,
    ):
        # Ensure stop is not None before using it in division
        if stop is None or start is None:
            raise ValueError("start and stop cannot be None")
        step = math.exp(math.log(stop / start) / (number_of_elements - 1))
        assert step != 0, "Step cannot be 0"
        super().__init__(start, number_of_elements, step)
        self.niter = 0

    def __iter__(self) -> "SweepLogN":
        super().__iter__()
        self.niter = 0
        return self

    def __next__(self) -> Union[int, float]:
        if self.niter < self.stop:
            val = self.start * (self.step**self.niter)
            self.niter += 1
            return val
        self.finished = True
        raise StopIteration


# Backward compatibility aliases
sweep = Sweep  # noqa: N816
sweep_log = SweepLog  # noqa: N816
sweep_log_n = SweepLogN  # noqa: N816
