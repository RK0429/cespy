#!/usr/bin/env python
# coding=utf-8
"""LTSpice symbol file (.asy) reader and parser.

This module provides functionality to parse LTSpice symbol files and translate
them into other formats, handling symbol geometry, pins, attributes, and
associated metadata.
"""
# -------------------------------------------------------------------------------
#
#  ███████╗██████╗ ██╗ ██████╗███████╗██╗     ██╗██████╗
#  ██╔════╝██╔══██╗██║██╔════╝██╔════╝██║     ██║██╔══██╗
#  ███████╗██████╔╝██║██║     █████╗  ██║     ██║██████╔╝
#  ╚════██║██╔═══╝ ██║██║     ██╔══╝  ██║     ██║██╔══██╗
#  ███████║██║     ██║╚██████╗███████╗███████╗██║██████╔╝
#  ╚══════╝╚═╝     ╚═╝ ╚═════╝╚══════╝╚══════╝╚═╝╚═════╝
#
# Name:        asy_reader.py
# Purpose:     Class to parse and then translate LTSpice symbol files
#
# Author:      Nuno Brum (nuno.brum@gmail.com)
#
# Licence:     refer to the LICENSE file
# -------------------------------------------------------------------------------

import logging
import re
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Union

from ..utils.detect_encoding import EncodingDetectError, detect_encoding
from .base_schematic import (
    ERotation,
    HorAlign,
    Line,
    Point,
    Shape,
    Text,
    TextTypeEnum,
    VerAlign,
)
from .ltspice_utils import asc_text_align_set
from .qsch_editor import QschTag

_logger = logging.getLogger("cespy.AsyReader")
SCALE_X = 6.25
SCALE_Y = -6.25


@dataclass
class SymbolElements:
    """Groups symbol elements to reduce instance attributes."""

    pins: List = field(default_factory=list)
    lines: List = field(default_factory=list)
    shapes: List = field(default_factory=list)
    windows: List = field(default_factory=list)
    attributes: Dict[str, str] = field(default_factory=OrderedDict)


class AsyReader:
    """Symbol parser."""

    # pylint: disable=too-many-locals,too-many-branches,too-many-statements
    def __init__(
        self, asy_file: Union[Path, str], encoding: str = "autodetect"
    ) -> None:
        super().__init__()
        self.version: str = "4"  # Store version as string
        self.symbol_type = None
        self.elements = SymbolElements()
        self._asy_file_path = Path(asy_file)
        self.encoding: str = ""
        pin = None
        if not self._asy_file_path.exists():
            raise FileNotFoundError(f"File {asy_file} not found")
        # determine encoding
        if encoding == "autodetect":
            try:
                self.encoding = detect_encoding(
                    self._asy_file_path, r"^VERSION ", re_flags=re.IGNORECASE
                )  # Normally the file will start with 'VERSION '
            except EncodingDetectError as err:
                raise err
        else:
            self.encoding = encoding

        with open(self._asy_file_path, "r", encoding=self.encoding) as asc_file:
            _logger.info("Parsing ASY file %s", self._asy_file_path)
            for line_text in asc_file:
                if line_text.startswith("WINDOW"):
                    (
                        _,
                        num_ref,
                        posX,
                        posY,
                        alignment,
                        size_str,
                    ) = line_text.split()
                    coord = Point(int(posX), int(posY))
                    text_obj = Text(
                        coord=coord,
                        text=num_ref,
                        size=int(size_str),  # Convert size to int
                        type=TextTypeEnum.ATTRIBUTE,
                    )
                    text_obj = asc_text_align_set(text_obj, alignment)
                    self.elements.windows.append(text_obj)
                elif line_text.startswith("SYMATTR"):
                    tokens = line_text.split(maxsplit=2)
                    if len(tokens) == 3:
                        _, ref, attr_text = tokens
                    elif len(tokens) == 2:
                        _, ref = tokens
                        attr_text = ""
                    else:
                        continue
                    attr_text = attr_text.strip()  # Gets rid of the \n terminator
                    # make sure prefix is uppercase, as this is used in a lot
                    # of places
                    if ref.upper() == "PREFIX":
                        attr_text = attr_text.upper()
                    self.elements.attributes[ref] = attr_text
                elif line_text.startswith("Version"):
                    _, version = line_text.split()
                    assert version in [
                        "4",
                        "4.0",
                        "4.1",
                    ], f"Unsupported version : {version}"
                    self.version = version  # Store version as string
                elif line_text.startswith("SymbolType "):
                    self.symbol_type = line_text[len("SymbolType ") :].strip()
                elif line_text.startswith("PINATTR"):
                    assert pin is not None, "A PIN was already created."
                    _, attribute, value = line_text.split(" ", maxsplit=3)
                    value = value.strip()  # gets rid of the \n
                    pin.text += f"{attribute}={value};"
                elif line_text.startswith("PIN"):
                    if pin is not None:
                        self.elements.pins.append(pin)
                    _, x, y, justification, offset = line_text.split()
                    coord = Point(int(x), int(y))
                    angle = ERotation.R0

                    if justification == "NONE":
                        vertical_alignment = (
                            VerAlign.CENTER
                        )  # This signals that the pin is not visible
                        text_alignment = HorAlign.CENTER
                    else:
                        text_alignment = HorAlign.LEFT
                        vertical_alignment = VerAlign.BOTTOM
                        if justification.startswith("V"):  # Rotation to 90 degrees
                            angle = ERotation.R90
                            if justification == "VRIGHT":
                                text_alignment = HorAlign.RIGHT
                            elif justification == "VTOP":
                                vertical_alignment = (
                                    VerAlign.TOP
                                )  # Keep vertical alignment as VerAlign
                            # else other two cases are the default
                        else:
                            if justification == "TOP":
                                vertical_alignment = VerAlign.TOP
                            # elif justification == "BOTTOM":
                            #     vertical_alignment = VerAlign.BOTTOM (default)
                            elif justification == "RIGHT":
                                text_alignment = HorAlign.RIGHT
                            # else: justification == "LEFT" (default)

                    pin = Text(
                        coord,
                        "",
                        type=TextTypeEnum.PIN,
                        size=int(offset),
                        textAlignment=text_alignment,
                        verticalAlignment=vertical_alignment,
                        angle=angle,
                    )

                # the following is identical to the code in asc_reader.py. If you modify
                # it, do so in both places.
                elif (
                    line_text.startswith("LINE")
                    or line_text.startswith("RECTANGLE")
                    or line_text.startswith("CIRCLE")
                ):
                    # format: LINE|RECTANGLE|CIRCLE Normal, x1, y1, x2, y2, [line_style]
                    # Maybe support something else than 'Normal', but LTSpice does not
                    # seem to do so.
                    line_elements = line_text.split()
                    assert len(line_elements) in (
                        6,
                        7,
                    ), "Syntax Error, line badly badly formatted"
                    x1 = int(line_elements[2])
                    y1 = int(line_elements[3])
                    x2 = int(line_elements[4])
                    y2 = int(line_elements[5])
                    if line_text.startswith("LINE"):
                        line_obj = Line(Point(x1, y1), Point(x2, y2))
                        if len(line_elements) == 7:
                            line_obj.style.pattern = line_elements[6]
                        self.elements.lines.append(line_obj)
                    if line_elements[0] in ("RECTANGLE", "CIRCLE"):
                        shape = Shape(line_elements[0], [Point(x1, y1), Point(x2, y2)])
                        if len(line_elements) == 7:
                            shape.line_style.pattern = line_elements[6]
                        self.elements.shapes.append(shape)

                elif line_text.startswith("ARC"):
                    # I don't support editing yet, so why make it complicated
                    # format: ARC Normal, x1, y1, x2, y2, x3, y3, x4, y4 [line_style]
                    # Maybe support something else than 'Normal', but LTSpice does not
                    # seem to do so.
                    line_elements = line_text.split()
                    assert len(line_elements) in (
                        10,
                        11,
                    ), "Syntax Error, line badly formatted"
                    points = [
                        Point(int(line_elements[i]), int(line_elements[i + 1]))
                        for i in range(2, 9, 2)
                    ]
                    arc = Shape("ARC", points)
                    if len(line_elements) == 11:
                        arc.line_style.pattern = line_elements[10]
                    self.elements.shapes.append(arc)

                elif line_text.startswith("TEXT "):
                    line_elements = line_text.split()
                    if len(line_elements) == 6:
                        x_pos = int(line_elements[1])
                        y_pos = int(line_elements[2])

                        text_obj = Text(
                            Point(x_pos, y_pos),
                            text=line_elements[5],
                            size=int(line_elements[4]),
                            type=TextTypeEnum.COMMENT,
                            textAlignment=HorAlign(line_elements[3]),
                        )
                        self.elements.windows.append(text_obj)
                    else:
                        # Text in asy not supported however non-critical and not
                        # neccesary to crash the program.
                        _logger.warning(
                            "Cosmetic text in ASY format not supported, text skipped."
                            " ASY file: %s",
                            self._asy_file_path,
                        )
                else:
                    # In order to avoid crashing the program, 1) add the missing
                    # if statement above and 2) contact the author to add
                    # support for the missing primitive.
                    raise NotImplementedError(
                        f'Primitive not supported for ASY file \n"{line_text}"in file:'
                        f" {self._asy_file_path}. Contact the author to add support."
                    )
            if pin is not None:
                self.elements.pins.append(pin)

    # pylint: disable=too-many-locals,too-many-statements
    def to_qsch(self, *args: str) -> QschTag:
        """Create a QschTag representing a component symbol."""
        spice_prefix = self.elements.attributes["Prefix"]
        symbol = QschTag("symbol", spice_prefix[0])
        symbol.items.append(QschTag("type:", spice_prefix))
        symbol.items.append(
            QschTag("description:", self.elements.attributes["Description"])
        )
        symbol.items.append(QschTag("shorted pins:", "false"))
        for line in self.elements.lines:
            x1 = int(line.V1.X * SCALE_X)
            y1 = int(line.V1.Y * SCALE_Y)
            x2 = int(line.V2.X * SCALE_X)
            y2 = int(line.V2.Y * SCALE_Y)
            segment, _ = QschTag.parse(
                f"«line ({x1},{y1}) ({x2},{y2}) 0 0 0x1000000 -1 -1»"
            )
            symbol.items.append(segment)

        for shape in self.elements.shapes:
            if shape.name == "RECTANGLE":
                x1 = int(shape.points[0].X * SCALE_X)
                y1 = int(shape.points[0].Y * SCALE_Y)
                x2 = int(shape.points[1].X * SCALE_X)
                y2 = int(shape.points[1].Y * SCALE_Y)
                shape_tag, _ = QschTag.parse(
                    f"«rect ({x1},{y1}) ({x2},{y2}) 0 0 0 0x4000000 0x1000000 -1 0 -1»"
                )
            elif shape.name == "ARC":
                # translate from 4 points style of ltspice to 3 points style of
                # qsch
                points = shape.points

                px1 = points[0].X
                px2 = points[1].X
                px3 = points[2].X
                px4 = points[3].X

                py1 = points[0].Y
                py2 = points[1].Y
                py3 = points[2].Y
                py4 = points[3].Y

                center = Point((px1 + px2) // 2, (py1 + py2) // 2)
                # Using only the X axis. Assuming a circle not an ellipse
                radius = abs(px2 - px1) / 2
                start = Point((px3 - center.X) / radius, (py3 - center.Y) / radius)
                stop = Point((px4 - center.X) / radius, (py4 - center.Y) / radius)
                # calculate new coordinates for drawing
                x1 = int(center.X * SCALE_X)
                y1 = int(center.Y * SCALE_Y)
                x2 = int(start.X * SCALE_X)
                y2 = int(start.Y * SCALE_Y)
                x3 = int(stop.X * SCALE_X)
                y3 = int(stop.Y * SCALE_Y)
                shape_tag, _ = QschTag.parse(
                    f"«arc3p ({x1},{y1}) ({x2},{y2}) ({x3},{y3}) 0 0 0xff0000 -1 -1»"
                )
            elif shape.name in ("CIRCLE", "ellipse"):
                x1 = int(shape.points[0].X * SCALE_X)
                y1 = int(shape.points[0].Y * SCALE_Y)
                x2 = int(shape.points[1].X * SCALE_X)
                y2 = int(shape.points[1].Y * SCALE_Y)
                shape_tag, _ = QschTag.parse(
                    f"«ellipse ({x1},{y1}) ({x2},{y2}) 0 0 0 0x1000000 0x1000000 -1 -1»"
                )
            else:
                raise ValueError(f"Shape {shape.name} not supported")
            symbol.items.append(shape_tag)

        for i, attr in enumerate(self.elements.windows):
            coord = attr.coord
            x = coord.X * SCALE_X
            y = coord.Y * SCALE_Y
            text, _ = QschTag.parse(
                f'«text ({x:.0f},{y:.0f}) 1 7 0 0x1000000 -1 -1 "{args[i]}"»'
            )
            symbol.items.append(text)

        for pin in self.elements.pins:
            coord = pin.coord
            attr_dict = {}
            for pair in pin.text.split(";"):
                if "=" in pair:
                    k, v = pair.split("=")
                    attr_dict[k] = v

            pin_tag, _ = QschTag.parse(
                f"«pin ({coord.X * SCALE_X:.0f},{coord.Y * SCALE_Y:.0f}) (0,0)"
                f" 1 0 0 0x1000000 -1 \"{attr_dict['PinName']}\"»"
            )
            symbol.items.append(pin_tag)

        return symbol

    def is_subcircuit(self) -> bool:
        """Check if the symbol represents a subcircuit.

        Returns True if the symbol type is BLOCK or has prefix X.
        """
        # Prefix is guaranteed to be uppercase
        return (
            self.symbol_type == "BLOCK" or self.elements.attributes.get("Prefix") == "X"
        )

    def get_library(self) -> Optional[str]:
        """Returns the library name of the model.

        If not found, returns None.
        """
        # Searching in this exact order
        suffixes = (".lib", ".sub", ".cir", ".txt")  # must be lowercase here
        for attr in (
            "ModelFile",
            "SpiceModel",
            "SpiceLine",
            "SpiceLine2",
            "Def_Sub",
            "Value",
            "Value2",
        ):
            if attr in self.elements.attributes and (
                self.elements.attributes[attr].lower().endswith(suffixes)
            ):
                return self.elements.attributes[attr]
        # Default to None if there is no library file attribute
        return self.elements.attributes.get("SpiceModel")

    def get_model(self) -> str:
        """Returns the model name of the component.

        If not found, returns None.
        """
        # Searching in this exact order
        for attr in (
            "Value",
            "SpiceModel",
            "Value2",
            "ModelFile",
            "SpiceLine",
            "SpiceLine2",
            "Def_Sub",
        ):
            if attr in self.elements.attributes:
                return self.elements.attributes[attr]
        raise ValueError("No Value or Value2 attribute found")

    def get_value(self) -> Union[int, float, str]:
        """Returns the value of the component.

        If not found, returns None. If found it tries to convert the value to a number.
        If it fails, it returns the string.
        """
        value = self.get_model()
        try:
            return int(value)
        except ValueError:
            try:
                return float(value)
            except ValueError:
                return value.strip()  # Removes the leading trailing spaces

    def get_schematic_file(self) -> Path:
        """Returns the file name of the component, if it were a .asc file."""
        assert self._asy_file_path.suffix == ".asy", "File is not an asy file"
        assert self.symbol_type == "BLOCK", "File is not a sub-circuit"
        return self._asy_file_path.with_suffix(".asc")
