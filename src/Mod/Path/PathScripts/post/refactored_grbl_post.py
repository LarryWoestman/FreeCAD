# -*- coding: utf-8 -*-
# ***************************************************************************
# *   Copyright (c) 2014 sliptonic <shopinthewoods@gmail.com>               *
# *   Copyright (c) 2018, 2019 Gauthier Briere                              *
# *   Copyright (c) 2019, 2020 Schildkroet                                  *
# *   Copyright (c) 2022 Larry Woestman <LarryWoestman2@gmail.com>          *
# *                                                                         *
# *   This file is part of the FreeCAD CAx development system.              *
# *                                                                         *
# *   This program is free software; you can redistribute it and/or modify  *
# *   it under the terms of the GNU Lesser General Public License (LGPL)    *
# *   as published by the Free Software Foundation; either version 2 of     *
# *   the License, or (at your option) any later version.                   *
# *   for detail see the LICENCE text file.                                 *
# *                                                                         *
# *   FreeCAD is distributed in the hope that it will be useful,            *
# *   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
# *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
# *   GNU Lesser General Public License for more details.                   *
# *                                                                         *
# *   You should have received a copy of the GNU Library General Public     *
# *   License along with FreeCAD; if not, write to the Free Software        *
# *   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  *
# *   USA                                                                   *
# *                                                                         *
# ***************************************************************************

import argparse
import shlex

from PathScripts import PostUtils

#
# The following variables need to be global variables
# to keep the PathPostProcessor.load method happy:
#
#    CORNER_MAX
#    CORNER_MIN
#    MACHINE_NAME
#    TOOLTIP
#    TOOLTIP_ARGS
#    UNITS
#
#    POSTAMBLE and PREAMBLE need to be defined before TOOLTIP_ARGS
#    can be defined, so they end up being global variables also.
#
CORNER_MAX = {"x": 500, "y": 300, "z": 300}
CORNER_MIN = {"x": 0, "y": 0, "z": 0}
MACHINE_NAME = "Grbl"
# default postamble text will appear following the last operation.
POSTAMBLE = """M5
G17 G90
M2
"""
# default preamble text will appear at the beginning of the gCode output file.
PREAMBLE = """G17 G90
"""
TOOLTIP = """
Generate g-code from a Path that is compatible with the grbl controller:

import refactored_grbl_post
refactored_grbl_post.export(object, "/path/to/file.ncc")
"""

# Parser arguments list & definition
parser = argparse.ArgumentParser(prog=MACHINE_NAME, add_help=False)
parser.add_argument(
    "--translate_drill",
    action="store_true",
    help="translate drill cycles G81, G82 & G83 in G0/G1 movements",
)
parser.add_argument(
    "--no-translate_drill",
    action="store_true",
    help="don't translate drill cycles G81, G82 & G83 in G0/G1 movements (default)",
)
parser.add_argument("--tool-change", action="store_true", help="Insert M6 for all tool changes")
parser.add_argument(
    "--wait-for-spindle",
    type=int,
    default=0,
    help="Wait for spindle to reach desired speed after M3 / M4, default=0",
)
parser.add_argument(
    "--return-to",
    default="",
    help="Move to the specified coordinates at the end, e.g. --return-to=0,0",
)
parser.add_argument(
    "--bcnc",
    action="store_true",
    help="Add Job operations as bCNC block headers. Consider suppressing existing comments: Add argument --no-comments",
)
parser.add_argument(
    "--no-bcnc", action="store_true", help="suppress bCNC block header output (default)"
)
TOOLTIP_ARGS = parser.format_help()
# G21 for metric, G20 for us standard
UNITS = "G21"

print(TOOLTIP_ARGS)


def processArguments(values, argstring):
    """Process the arguments to the postprocessor."""
    #
    global POSTAMBLE
    global PREAMBLE
    global UNITS

    try:
        args = parser.parse_args(shlex.split(argstring))
        if args.no_header:
            values["OUTPUT_HEADER"] = False
        if args.header:
            values["OUTPUT_HEADER"] = True
        if args.no_comments:
            values["OUTPUT_COMMENTS"] = False
        if args.comments:
            values["OUTPUT_COMMENTS"] = True
        if args.no_line_numbers:
            values["OUTPUT_LINE_NUMBERS"] = False
        if args.line_numbers:
            values["OUTPUT_LINE_NUMBERS"] = True
        if args.no_show_editor:
            values["SHOW_EDITOR"] = False
        if args.show_editor:
            values["SHOW_EDITOR"] = True
        values["AXIS_PRECISION"] = args.precision
        values["FEED_PRECISION"] = args.precision
        if args.preamble is not None:
            PREAMBLE = args.preamble
        if args.postamble is not None:
            POSTAMBLE = args.postamble
        if args.no_translate_drill:
            values["TRANSLATE_DRILL_CYCLES"] = False
        if args.translate_drill:
            values["TRANSLATE_DRILL_CYCLES"] = True
        if args.inches:
            UNITS = "G20"
            values["UNIT_SPEED_FORMAT"] = "in/min"
            values["UNIT_FORMAT"] = "in"
            values["AXIS_PRECISION"] = 4
            values["FEED_PRECISION"] = 4
        if args.tool_change:
            values["OUTPUT_TOOL_CHANGE"] = True
        if args.wait_for_spindle > 0:
            values["SPINDLE_WAIT"] = args.wait_for_spindle
        if args.return_to != "":
            values["RETURN_TO"] = [int(v) for v in args.return_to.split(",")]
            if len(values["RETURN_TO"]) != 2:
                values["RETURN_TO"] = None
                print("--return-to coordinates must be specified as <x>,<y>, ignoring")
        if args.bcnc:
            values["OUTPUT_BCNC"] = True
        if args.no_bcnc:
            values["OUTPUT_BCNC"] = False

    except Exception:
        return False

    return True


def export(objectslist, filename, argstring):
    """Postprocess the objects in objectslist to filename."""
    #
    global POSTABLE
    global PREAMBLE
    global UNITS
    #
    # Holds various values that are used throughout the postprocessor code.
    #
    values = {}
    PostUtils.init_shared_values(values)

    values["ENABLE_MACHINE_SPECIFIC_COMMANDS"] = True
    values["OUTPUT_PATH_LABELS"] = True
    # default don't output M6 tool changes (comment it) as grbl currently does not handle it
    values["OUTPUT_TOOL_CHANGE"] = False
    values["PARAMETER_ORDER"] = [
        "X",
        "Y",
        "Z",
        "A",
        "B",
        "C",
        "U",
        "V",
        "W",
        "I",
        "J",
        "K",
        "F",
        "S",
        "T",
        "Q",
        "R",
        "L",
        "P",
    ]
    values["POSTPROCESSOR_FILE_NAME"] = __name__
    values["SHOW_MACHINE_UNITS"] = False
    values["USE_TLO"] = False

    if not processArguments(values, argstring):
        return None

    values["POSTAMBLE"] = POSTAMBLE
    values["PREAMBLE"] = PREAMBLE
    values["UNITS"] = UNITS

    return PostUtils.export_common(values, objectslist, filename)


# print(__name__ + ": GCode postprocessor loaded.")
