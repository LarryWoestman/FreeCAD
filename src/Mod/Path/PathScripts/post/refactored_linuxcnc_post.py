# ***************************************************************************
# *   Copyright (c) 2014 sliptonic <shopinthewoods@gmail.com>               *
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

from __future__ import print_function

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
MACHINE_NAME = "LinuxCNC"
# Postamble text will appear following the last operation.
POSTAMBLE = """M05
G17 G54 G90 G80 G40
M2
"""
# Preamble text will appear at the beginning of the GCODE output file.
PREAMBLE = """G17 G54 G40 G49 G80 G90
"""
TOOLTIP = """This is a postprocessor file for the Path workbench. It is used to
take a pseudo-gcode fragment outputted by a Path object, and output
real GCode suitable for a linuxcnc 3 axis mill. This postprocessor, once placed
in the appropriate PathScripts folder, can be used directly from inside
FreeCAD, via the GUI importer or via python scripts with:

import linuxcnc_post
linuxcnc_post.export(object,"/path/to/file.ncc","")
"""

parser = argparse.ArgumentParser(prog=MACHINE_NAME, add_help=False)
parser.add_argument("--no-header", action="store_true", help="suppress header output")
parser.add_argument("--no-comments", action="store_true", help="suppress comment output")
parser.add_argument("--line-numbers", action="store_true", help="prefix with line numbers")
parser.add_argument(
    "--no-show-editor",
    action="store_true",
    help="don't pop up editor before writing output",
)
parser.add_argument("--precision", default="3", help="number of digits of precision, default=3")
parser.add_argument(
    "--preamble",
    help='set commands to be issued before the first command, default="' + PREAMBLE + '"',
)
parser.add_argument(
    "--postamble",
    help='set commands to be issued after the last command, default="' + POSTAMBLE + '"',
)
parser.add_argument(
    "--inches", action="store_true", help="Convert output for US imperial mode (G20)"
)
parser.add_argument(
    "--modal",
    action="store_true",
    help="Output the Same G-command Name USE NonModal Mode",
)
parser.add_argument("--axis-modal", action="store_true", help="Output the Same Axis Value Mode")
parser.add_argument(
    "--no-tlo",
    action="store_true",
    help="suppress tool length offset (G43) following tool changes",
)
TOOLTIP_ARGS = parser.format_help()
# G21 for metric, G20 for US standard
UNITS = "G21"


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
        if args.no_comments:
            values["OUTPUT_COMMENTS"] = False
        if args.line_numbers:
            values["OUTPUT_LINE_NUMBERS"] = True
        if args.no_show_editor:
            values["SHOW_EDITOR"] = False
        values["AXIS_PRECISION"] = args.precision
        values["FEED_PRECISION"] = args.precision
        if args.preamble is not None:
            PREAMBLE = args.preamble
        if args.postamble is not None:
            POSTAMBLE = args.postamble
        if args.inches:
            UNITS = "G20"
            values["UNIT_SPEED_FORMAT"] = "in/min"
            values["UNIT_FORMAT"] = "in"
            values["AXIS_PRECISION"] = 4
            values["FEED_PRECISION"] = 4
        if args.modal:
            values["MODAL"] = True
        if args.no_tlo:
            values["USE_TLO"] = False
        if args.axis_modal:
            values["OUTPUT_DOUBLES"] = False

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
    PostUtils.init_values(values)
    values["AXIS_PRECISION"] = 3
    values["COMMENT_SYMBOL"] = "("
    values["ENABLE_COOLANT"] = True
    values["FEED_PRECISION"] = 3
    values["FINISH_LABEL"] = "finish"
    # the order of parameters
    # linuxcnc doesn't want K properties on XY plane; Arcs need work.
    values["LIST_TOOLS_IN_PREAMBLE"] = False
    values["PARAMETER_ORDER"] = [
        "X",
        "Y",
        "Z",
        "A",
        "B",
        "C",
        "I",
        "J",
        "F",
        "S",
        "T",
        "Q",
        "R",
        "L",
        "H",
        "D",
        "P",
    ]
    values["REMOVE_MESSAGES"] = True
    values["SAFETYBLOCK"] = """"""
    values["SHOW_MACHINE_UNITS"] = True
    values["SHOW_OPERATION_LABELS"] = True
    values["STOP_SPINDLE_FOR_TOOL_CHANGE"] = True
    values["TOOLRETURN"] = """"""
    # if true G43 will be output following tool changes
    values["USE_TLO"] = True

    if not processArguments(values, argstring):
        return None

    values["POSTAMBLE"] = POSTAMBLE
    values["PREAMBLE"] = PREAMBLE
    values["UNITS"] = UNITS

    return PostUtils.export_common(values, objectslist, filename)


# print(__name__ + " gcode postprocessor loaded.")
