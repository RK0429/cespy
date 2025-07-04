#!/usr/bin/env python
# coding=utf-8
"""Module for handling LTSpice log file data parsing and analysis."""
from __future__ import annotations

import logging
import math
import re
from collections import OrderedDict
from typing import Any, Dict, Iterable, List, Optional, Protocol, TypeVar, Union, cast

# -------------------------------------------------------------------------------
# Name:        logfile_data.py
# Purpose:     Store data related to log files. This is a superclass of LTSpiceLogReader
#
# Author:      Nuno Brum (nuno.brum@gmail.com)
#
# Licence:     refer to the LICENSE file
# -------------------------------------------------------------------------------


_logger = logging.getLogger("cespy.LTSteps")


class LTComplex(complex):
    """Class to represent complex numbers as exported by LTSpice."""

    complex_match = re.compile(
        r"\((?P<mag>.*?)(?P<dB>dB)?,(?P<ph>.*?)(?P<degrees>°)?\)"
    )

    def __new__(cls, strvalue: str) -> "LTComplex":
        match = cls.complex_match.match(strvalue)
        if match:
            mag = float(match.group("mag"))
            ph = float(match.group("ph"))
            if match.group("degrees") is None:
                # This is the cartesian format
                return super().__new__(cls, mag, ph)
            # This is the polar format
            if match.group("dB") is not None:
                mag = 10 ** (mag / 20)
            return super().__new__(
                cls,
                mag * math.cos(math.pi * ph / 180),
                mag * math.sin(math.pi * ph / 180),
            )
        raise ValueError("Invalid complex value format")

    def __init__(self, strvalue: str) -> None:
        self.strvalue = strvalue

    def __str__(self) -> str:
        return self.strvalue

    @property
    def mag(self) -> float:
        """Returns the magnitude of the complex number."""
        return abs(self)

    @property
    def ph(self) -> float:
        """Returns the phase of the complex number in degrees."""
        return math.atan2(self.imag, self.real) * 180 / math.pi

    def mag_db(self) -> float:
        """Returns the magnitude of the complex number in dBV."""
        return 20 * math.log10(self.mag)

    def ph_rad(self) -> float:
        """Return the phase angle in radians."""
        return math.atan2(self.imag, self.real)

    @property
    def unit(self) -> Optional[str]:
        """Return the unit of the complex value if present."""
        _unit = None
        match = self.complex_match.match(self.strvalue)
        if match:
            _unit = match.group("dB")
        return _unit


ValueType = Union[int, float, str, List[Any], LTComplex]
NumericType = Union[int, float, complex, LTComplex]


# Create a protocol for types that can be compared
class Comparable(Protocol):
    """Protocol for types that support less-than comparison."""

    def __lt__(self, other: Any) -> bool: ...

    def dummy_method(self) -> None:
        """Dummy method to satisfy pylint's too-few-public-methods requirement."""


T = TypeVar("T", bound=Comparable)


def try_convert_value(value: Union[str, int, float, List[Any], bytes]) -> ValueType:
    """Tries to convert the string into an integer and if it fails, tries to convert to
    a float, if it fails, then returns the value as string.

    :param value: value to convert
    :type value: str, int or float
    :return: converted value, if applicable
    :rtype: int, float, str
    """
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, list):
        return [try_convert_value(v) for v in value]
    if isinstance(value, bytes):
        value = value.decode("utf-8")

    # Initialize ans with a default type to satisfy the type checker
    ans: ValueType
    if isinstance(value, str):
        ans = value.strip()
    else:
        ans = cast(ValueType, value)

    try:
        ans = int(value)
    except ValueError:
        try:
            ans = float(value)
        except ValueError:
            try:
                ans = LTComplex(str(value))
            except ValueError:
                if isinstance(value, str):
                    ans = value.strip()
                else:
                    ans = cast(ValueType, value)
    return ans


# pylint: disable=too-many-branches
def split_line_into_values(line: str) -> List[ValueType]:
    """Splits a line into values.

    The values are separated by tabs or spaces. If a value starts with ( and ends with
    ), then it is considered a complex value, and it is returned as a single value. If
    converting values within () fails, then the value is returned as a tuple with the
    values inside the ().
    """
    parenthesis: List[str] = []
    i = 0
    value_start = 0
    values: List[ValueType] = []
    for i, c in enumerate(line):
        if (
            c == "("
        ):  # By checking the parenthesis first, we can support nested parenthesis
            parenthesis.insert(0, ")")
        elif c == "[":
            parenthesis.insert(0, "]")
        elif c == "{":
            parenthesis.insert(0, "}")
        elif len(parenthesis) > 0:
            if c == parenthesis[0]:
                parenthesis.pop(0)
                if len(parenthesis) == 0:
                    value_list = split_line_into_values(
                        line[value_start + 1 : i]
                    )  # Excludes the parenthesis
                    values.append(value_list)
                    value_start = i + 1
        elif c in (" ", "\t", "\r", "\n"):
            if value_start < i:
                values.append(try_convert_value(line[value_start:i]))
            value_start = i + 1
        elif c in (",", ";"):
            if value_start < i:
                values.append(try_convert_value(line[value_start:i]))
            else:
                values.append(cast(ValueType, None))
            value_start = i + 1
    if value_start < i + 1:
        values.append(try_convert_value(line[value_start : i + 1]))
    parenthesis_balanced = len(parenthesis) == 0
    if not parenthesis_balanced:
        raise ValueError("Parenthesis are not balanced")
    return values


# pylint: enable=too-many-branches


class LogfileData:
    """This is a subclass of LTSpiceLogReader that is used to analyse the log file of a
    simulation.

    The super class constructor is bypassed and only their attributes are initialized
    """

    def __init__(
        self,
        step_set: Optional[Dict[str, List[Any]]] = None,
        dataset: Optional[Dict[str, List[Any]]] = None,
    ) -> None:
        if step_set is None:
            self.stepset: Dict[str, List[Any]] = {}
        else:
            self.stepset = (
                step_set.copy()
            )  # A copy is done since the dictionary is a mutable object.
            # Changes in step_set would be propagated to object on the call

        if dataset is None:
            # Dictionary in which the order of the keys is kept
            self.dataset: Dict[str, List[Any]] = OrderedDict()
        else:
            self.dataset = (
                dataset.copy()
            )  # A copy is done since the dictionary is a mutable object.

        self.step_count = len(self.stepset)
        self.measure_count = len(self.dataset)

        # For storing the encoding when exporting
        self.encoding: str = "utf-8"

    def __getitem__(self, key: str) -> List[Any]:
        """__getitem__ implements :key: step or measurement name.

        This is case insensitive.
        :return: step or measurement set
        :rtype: List[float]
        """
        if isinstance(key, slice):
            raise NotImplementedError("Slicing in not allowed in this class")
        key = key.lower()
        if key in self.stepset:
            return self.stepset[key]
        if key in self.dataset:
            return self.dataset[
                key
            ]  # This will raise an Index Error if not found here.
        raise IndexError(f"'{key}' is not a valid step variable or measurement name")

    def has_steps(self) -> bool:
        """Returns true if the simulation has steps :return: True if the simulation has
        steps :rtype: bool."""
        return self.step_count > 0

    def steps_with_parameter_equal_to(
        self, param: str, value: Union[str, int, float]
    ) -> List[int]:
        """Returns the steps that contain a given condition.

        :param param: parameter identifier on a stepped simulation. This is case
            insensitive.
        :type param: str
        :param value:
        :type value:
        :return: List of positions that respect the condition of equality with parameter
            value
        :rtype: List[int]
        """
        param = param.lower()
        if param in self.stepset:
            condition_set = self.stepset[param]
        elif param in self.dataset:
            condition_set = self.dataset[param]
        else:
            raise IndexError(
                f"'{param}' is not a valid step variable or measurement name"
            )
        # tries to convert the value to integer or float, for consistency with
        # data loading implementation
        v = try_convert_value(value)
        # returns the positions where there is match
        return [i for i, a in enumerate(condition_set) if a == v]

    def steps_with_conditions(self, **conditions: Union[str, int, float]) -> List[int]:
        """Returns the steps that respect one or more equality conditions.

        :key conditions: parameters within the Spice simulation. Values are the matches
            to be found.
        :type conditions: dict
        :return: List of steps that respect all the given conditions
        :rtype: List[int]
        """
        current_set = None
        for param, value in conditions.items():
            condition_set = self.steps_with_parameter_equal_to(param, value)
            if current_set is None:
                # initialises the list
                current_set = condition_set
            else:
                # makes the intersection between the lists
                current_set = [v for v in current_set if v in condition_set]
        return current_set if current_set is not None else []

    def get_step_vars(self) -> List[str]:
        """Returns the stepped variable names on the log file.

        :return: List of step variables.
        :rtype: list of str
        """
        return list(self.stepset.keys())

    def get_measure_names(self) -> List[str]:
        """Returns the names of the measurements read from the log file.

        :return: List of measurement names.
        :rtype: list of str
        """
        return list(self.dataset.keys())

    def get_measure_value(
        self,
        measure: str,
        step: Optional[Union[int, slice]] = None,
        **kwargs: Union[str, int, float],
    ) -> Union[float, int, str, LTComplex]:
        """Returns a measure value on a given step.

        :param measure: name of the measurement to get. This is case insensitive.
        :type measure: str
        :param step: optional step number or slice if the simulation has no steps.
        :type step: int or slice
        :param kwargs: additional arguments that can be translated into step conditions
        :return: measurement value
        :rtype: int, float, Complex or str
        """
        measure = measure.lower()
        if step is None:
            if kwargs:
                steps = self.steps_with_conditions(**kwargs)
                if len(steps) == 1:
                    # Explicitly cast to the expected return type
                    return cast(
                        Union[float, int, str, LTComplex],
                        self.dataset[measure][steps[0]],
                    )
                raise IndexError("Not sufficient conditions to identify a single step")
            if len(self.dataset[measure]) == 1:
                # Explicitly cast to the expected return type
                return cast(Union[float, int, str, LTComplex], self.dataset[measure][0])
            if len(self.dataset[measure]) == 0:
                _logger.error('No measurements found for measure "%s"', measure)
                raise IndexError(f'No measurements found for measure "{measure}"')
            raise IndexError("In stepped data, the step number needs to be provided")
        if isinstance(step, (slice, int)):
            # Explicitly cast to the expected return type
            return cast(
                Union[float, int, str, LTComplex],
                self.dataset[measure][step],
            )
        raise TypeError("Step must be an integer or a slice")

    def get_measure_values_at_steps(
        self, measure: str, steps: Union[None, int, Iterable[int]]
    ) -> List[ValueType]:
        """Returns the measurements taken at a list of steps provided by the steps list.

        :param measure: name of the measurement to get. This is case insensitive.
        :type measure: str
        :param steps: step number, or list of step numbers.
        :type steps: Optional: int or list
        :return: measurement or list of measurements
        :rtype: list with the values converted to either integer (int) or floating point
            (float)
        """
        measure = measure.lower()
        if steps is None:
            # Return a copy to avoid modifying original data
            return list(self.dataset[measure])
        if isinstance(steps, int):
            # Return as a list for consistency
            return [self.dataset[measure][steps]]
        # Assuming it is an iterable
        return [self.dataset[measure][step] for step in steps]

    def max_measure_value(
        self, measure: str, steps: Union[None, int, Iterable[int]] = None
    ) -> ValueType:
        """Returns the maximum value of a measurement.

        :param measure: name of the measurement to get. This is case insensitive.
        :type measure: str
        :param steps: step number, or list of step numbers.
        :type steps: Optional, int or list
        :return: maximum value of the measurement
        :rtype: float or int
        """
        values = self.get_measure_values_at_steps(measure, steps)
        if not values:
            raise ValueError(f"No values found for measure {measure}")

        # Handle only comparable types
        comparable_values = [
            v for v in values if isinstance(v, (int, float, str, LTComplex))
        ]
        if not comparable_values:
            raise ValueError(f"No comparable values found for measure {measure}")

        # Cast comparable_values to Iterable[Comparable] for max
        return cast(ValueType, max(cast(Iterable[Comparable], comparable_values)))

    def min_measure_value(
        self, measure: str, steps: Union[None, int, Iterable[int]] = None
    ) -> ValueType:
        """Returns the minimum value of a measurement.

        :param measure: name of the measurement to get. This is case insensitive.
        :type measure: str
        :param steps: step number, or list of step numbers.
        :type steps: Optional: int or list
        :return: minimum value of the measurement
        :rtype: float or int
        """
        values = self.get_measure_values_at_steps(measure, steps)
        if not values:
            raise ValueError(f"No values found for measure {measure}")

        # Handle only comparable types
        comparable_values = [
            v for v in values if isinstance(v, (int, float, str, LTComplex))
        ]
        if not comparable_values:
            raise ValueError(f"No comparable values found for measure {measure}")

        # Cast comparable_values to Iterable[Comparable] for min
        return cast(ValueType, min(cast(Iterable[Comparable], comparable_values)))

    def avg_measure_value(
        self, measure: str, steps: Union[None, int, Iterable[int]] = None
    ) -> NumericType:
        """Returns the average value of a measurement.

        :param measure: name of the measurement to get.  This is case insensitive.
        :type measure: str
        :param steps: step number, or list of step numbers.
        :type steps: Optional: int or list
        :return: average value of the measurement
        :rtype: float or int
        """
        values = self.get_measure_values_at_steps(measure, steps)
        # Filter to only numeric values for calculation
        numeric_values: List[NumericType] = [
            v for v in values if isinstance(v, (int, float, complex, LTComplex))
        ]
        if not numeric_values:
            raise ValueError(f"No numeric values found for measure {measure}")
        return sum(numeric_values) / len(numeric_values)

    def obtain_amplitude_and_phase_from_complex_values(self) -> None:
        """Internal function to split the complex values into additional two columns.

        The two columns correspond to the magnitude and phase of the complex value in
        degrees.
        """
        for param in list(self.dataset.keys()):
            if len(self.dataset[param]) > 0 and isinstance(
                self.dataset[param][0], LTComplex
            ):
                self.dataset[param + "_mag"] = [v.mag for v in self.dataset[param]]
                self.dataset[param + "_ph"] = [v.ph for v in self.dataset[param]]

    def split_complex_values_on_datasets(self) -> None:
        """..

        deprecated:: 1.0 Use `obtain_amplitude_and_phase_from_complex_values()` instead.
        """
        self.obtain_amplitude_and_phase_from_complex_values()

    # pylint: disable=too-many-arguments,too-many-locals,too-many-branches,too-many-statements
    def export_data(
        self,
        export_file: str,
        encoding: Optional[str] = None,
        append_with_line_prefix: Optional[str] = None,
        *,
        value_separator: str = "\t",
        line_terminator: str = "\n",
    ) -> None:
        """Exports the measurement information to a tab separated value (.tsv) format.
        If step data is found, it is included in the exported file.

        When using export data together with SpiceBatch.py classes, it may be helpful to
        append data to an existing file. For this purpose, the user can user the
        append_with_line_prefix argument to indicate that an append should be done. And
        in this case, the user must provide a string that will identify the LTSpice
        batch run.

        :param export_file: path to the file containing the information
        :type export_file: str
        :param optional encoding: encoding to be used in the file
        :type encoding: str
        :param optional append_with_line_prefix: user information to be written in the
            file in case an append is to be made.
        :type append_with_line_prefix: str
        :param optional value_separator: character to be used to separate values
        :type value_separator: str
        :param optional line_terminator: Line terminator character
        :type line_terminator: str
        :return: Nothing
        """
        if append_with_line_prefix is None:
            mode = "w"  # rewrites the file
        else:
            mode = "a"  # Appends an existing file

        if len(self.dataset) == 0:
            _logger.warning("Empty data set. Exiting without writing file.")
            return

        if encoding is None:
            encoding = self.encoding if hasattr(self, "encoding") else "utf-8"

        with open(export_file, mode, encoding=encoding) as fout:
            if (
                append_with_line_prefix is not None
            ):  # if appending a file, it must write the column title
                fout.write("user info" + value_separator)

            data_size = None
            fout.write("step")
            columns_per_line = 1
            for title, values in self.stepset.items():
                if data_size is None:
                    data_size = len(values)
                else:
                    if len(values) != data_size:
                        raise ValueError(
                            "Data size mismatch. Not all measurements have the same length."
                        )

                if isinstance(values[0], list) and len(values[0]) > 1:
                    for n in range(len(values[0])):
                        fout.write(value_separator + f"{title}_{n}")
                        columns_per_line += 1
                else:
                    fout.write(value_separator + title)
                    columns_per_line += 1

            for title, values in self.dataset.items():
                if data_size is None:
                    data_size = len(values)
                else:
                    if len(values) != data_size:
                        logging.error(
                            "Data size mismatch. Not all measurements have the same"
                            ' length. Expected %d. "%s" has %d',
                            data_size,
                            title,
                            len(values),
                        )

                if isinstance(values[0], list) and len(values[0]) > 1:
                    for n in range(len(values[0])):
                        fout.write(value_separator + f"{title}_{n}")
                        columns_per_line += 1
                else:
                    fout.write(value_separator + title)
                    columns_per_line += 1

            fout.write(line_terminator)  # Finished to write the headers

            if data_size is None:
                data_size = 0  # Skips writing data in the loop below

            for index in range(data_size):
                if self.step_count == 0:
                    step_data = []  # Empty step
                else:
                    step_data = [
                        self.stepset[param][index] for param in self.stepset.keys()
                    ]
                meas_data = [self.dataset[param][index] for param in self.dataset.keys()]

                if (
                    append_with_line_prefix is not None
                ):  # if appending a file it must write the user info
                    fout.write(append_with_line_prefix + value_separator)
                fout.write(f"{index + 1}")
                columns_writen = 1
                for s in step_data:
                    if isinstance(s, list):
                        for x in s:
                            fout.write(value_separator + f"{x}")
                            columns_writen += 1
                    else:
                        fout.write(value_separator + f"{s}")
                        columns_writen += 1

                for tok in meas_data:
                    if isinstance(tok, list):
                        for x in tok:
                            fout.write(value_separator + f"{x}")
                            columns_writen += 1
                    else:
                        fout.write(value_separator + f"{tok}")
                        columns_writen += 1
                if columns_writen != columns_per_line:
                    logging.error(
                        "Line with wrong number of values. Expected:%d Index %d has %d",
                        columns_per_line,
                        index + 1,
                        columns_writen,
                    )
                fout.write(line_terminator)

    # pylint: enable=too-many-arguments,too-many-locals,too-many-branches,too-many-statements

    # pylint: disable=too-many-arguments,too-many-locals
    def plot_histogram(
        self,
        param: str,
        steps: Optional[Union[int, Iterable[int]]] = None,
        bins: int = 50,
        *,
        normalized: bool = True,
        sigma: float = 3.0,
        title: Optional[str] = None,
        image_file: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Plots a histogram of the parameter."""
        # pylint: disable=import-outside-toplevel
        import matplotlib.pyplot as plt
        import numpy as np

        del kwargs  # Unused but kept for API compatibility

        values = self.get_measure_values_at_steps(param, steps)
        x = np.array(values, dtype=float)
        mu = x.mean()
        mn = x.min()
        mx = x.max()
        sd = x.std()

        # Automatic calculation of the range
        axis_x_min: float = mu - (sigma + 1) * sd
        axis_x_max: float = mu + (sigma + 1) * sd

        axis_x_min = min(axis_x_min, mn)

        axis_x_max = max(axis_x_max, mx)

        counts, bin_edges, _ = plt.hist(
            x,
            bins,
            density=normalized,
            facecolor="green",
            alpha=0.75,
            range=(axis_x_min, axis_x_max),
        )
        # Get max value from counts - ensure single float
        axis_y_max: float
        if isinstance(counts, np.ndarray):
            axis_y_max = float(counts.max()) * 1.1
        else:
            axis_y_max = float(np.max(counts)) * 1.1

        if normalized:
            # add a 'best fit' line
            # Normal distribution PDF: 1/(σ√(2π)) * exp(-(x-μ)^2/(2σ^2))
            y = (1 / (sd * np.sqrt(2 * np.pi))) * np.exp(
                -((bin_edges - mu) ** 2) / (2 * sd**2)
            )
            plt.plot(bin_edges, y, "r--", linewidth=1)
            plt.axvspan(mu - sigma * sd, mu + sigma * sd, alpha=0.2, color="cyan")
            plt.ylabel("Distribution [Normalised]")
        else:
            plt.ylabel("Distribution")
        plt.xlabel(param)

        if title is None:
            fmt = "%g"
            title = (
                r"$\mathrm{Histogram\ of\ %s:}\ \mu="
                + fmt
                + r",\ stdev="
                + fmt
                + r",\ \sigma=%d$"
            ) % (param, mu, sd, sigma)

        plt.title(title)

        plt.axis((axis_x_min, axis_x_max, 0.0, axis_y_max))
        plt.grid(True)
        if image_file is not None:
            plt.savefig(image_file)
        else:
            plt.show()

    # pylint: enable=too-many-arguments,too-many-locals
