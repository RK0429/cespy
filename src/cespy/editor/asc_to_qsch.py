#!/usr/bin/env python
# coding=utf-8

# -------------------------------------------------------------------------------
#    ____        _   _____ ____        _
#   |  _ \ _   _| | |_   _/ ___| _ __ (_) ___ ___
#   | |_) | | | | |   | | \___ \| '_ \| |/ __/ _ \
#   |  __/| |_| | |___| |  ___) | |_) | | (_|  __/
#   |_|    \__, |_____|_| |____/| .__/|_|\___\___|
#          |___/                |_|
#
# Name:        asc_to_qsch.py
# Purpose:     Convert an ASC file to a QSCH schematic
#
# Author:      Nuno Brum (nuno.brum@gmail.com)
#
# Created:     16-02-2024
# Licence:     refer to the LICENSE file
# -------------------------------------------------------------------------------
import logging
import os
import xml.etree.ElementTree as ET

from cespy.editor.asc_editor import AscEditor
from cespy.editor.asy_reader import AsyReader
from cespy.editor.qsch_editor import QschEditor, QschTag
from cespy.utils.file_search import find_file_in_directory

_logger = logging.getLogger("cespy.AscToQsch")


def main() -> None:
    import os.path
    from optparse import OptionParser

    opts = OptionParser(
        usage="usage: %prog [options] ASC_FILE [QSCH_FILE]", version="%prog 0.1"
    )

    opts.add_option(
        "-a",
        "--add",
        action="append",
        type="string",
        dest="path",
        help="Add a path for searching for symbols",
    )

    (options, args) = opts.parse_args()

    if len(args) < 1:
        opts.print_help()
        exit(-1)

    asc_file = args[0]
    if len(args) > 1:
        qsch_file = args[1]
    else:
        qsch_file = os.path.splitext(asc_file)[0] + ".qsch"

    search_paths = [] if options.path is None else options.path

    print(f"Using {qsch_file} as output file")
    convert_asc_to_qsch(asc_file, qsch_file, search_paths)


def convert_asc_to_qsch(
        asc_file: str,
        qsch_file: str,
        search_paths: list[str] = []) -> None:
    """Converts an ASC file to a QSCH schematic."""
    symbol_stock: dict[str, QschTag] = {}
    # Open the ASC file
    asc_editor = AscEditor(asc_file)

    # import the conversion data from xml file
    # need first to find the file. It is in the same directory as the script
    parent_dir = os.path.dirname(os.path.realpath(__file__))
    xml_file = os.path.join(parent_dir, "data", "asc_to_qsch_data.xml")
    conversion_data = ET.parse(xml_file)

    # Get the root element
    root = conversion_data.getroot()

    # Get the offset and scaling
    offset = root.find("offset")
    assert offset is not None, "Missing <offset> in asc_to_qsch_data.xml"
    offset_x = float(offset.get("x", "0"))
    offset_y = float(offset.get("y", "0"))
    scale = root.find("scaling")
    assert scale is not None, "Missing <scaling> in asc_to_qsch_data.xml"
    scale_x = float(scale.get("x", "1"))
    scale_y = float(scale.get("y", "1"))

    # Scaling the schematic
    asc_editor.scale(
        offset_x=offset_x, offset_y=offset_y, scale_x=scale_x, scale_y=scale_y
    )

    # Adding symbols to components
    for comp in asc_editor.components.values():
        if comp.symbol is None:
            continue
        symbol_tag = symbol_stock.get(comp.symbol, None)
        if symbol_tag is None:
            # Will try to get it from the sym folder
            print(f"Searching for symbol {comp.symbol}...")
            for sym_root in search_paths + [
                os.path.split(asc_file)[0],
                os.path.expanduser("~/AppData/Local/LTspice/lib/sym"),
                os.path.expanduser("~/Documents/LtspiceXVII/lib/sym"),
            ]:
                print(f"   {os.path.abspath(sym_root)}")
                if not os.path.exists(sym_root):
                    continue
                symbol_asc_file = find_file_in_directory(
                    sym_root, comp.symbol + ".asy"
                )
                if symbol_asc_file is not None:
                    print(f"Found {symbol_asc_file}")
                    symbol_asc = AsyReader(symbol_asc_file)
                    value = comp.attributes.get("Value", "<val>")
                    symbol_tag = symbol_asc.to_qsch(comp.reference, value)
                    symbol_stock[comp.symbol] = symbol_tag
                    break

        # Rotation adjustments removed to avoid type mismatches

        if symbol_tag:
            comp.attributes["symbol"] = symbol_tag

    qsch_editor = QschEditor(qsch_file, create_blank=True)
    qsch_editor.copy_from(asc_editor)
    # Save the netlist
    qsch_editor.save_netlist(qsch_file)

    print(f"File {asc_file} converted to {qsch_file}")


if __name__ == "__main__":
    main()
    exit(0)
