# -*- coding: utf-8 -*-
# ***************************************************************************
# *   Copyright (c) 2015 Dan Falck <ddfalck@gmail.com>                      *
# *   Copyright (c) 2020 Schildkroet                                        *
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
CORNER_MAX = {"x": 609.6, "y": 152.4, "z": 304.8}
CORNER_MIN = {"x": -609.6, "y": -152.4, "z": 0}
MACHINE_NAME = "Centroid"
TOOLTIP = """
This is a postprocessor file for the Path workbench. It is used to
take a pseudo-gcode fragment outputted by a Path object, and output
real GCode suitable for a centroid 3 axis mill. This postprocessor, once placed
in the appropriate PathScripts folder, can be used directly from inside
FreeCAD, via the GUI importer or via python scripts with:

import centroid_post
centroid_post.export(object,"/path/to/file.ncc","")
"""
TOOLTIP_ARGS = """
Arguments for centroid:
    --header,--no-header             ... output headers (--header)
    --comments,--no-comments         ... output comments (--comments)
    --line-numbers,--no-line-numbers ... prefix with line numbers (--no-lin-numbers)
    --show-editor, --no-show-editor  ... pop up editor before writing output(--show-editor)
    --feed-precision=1               ... number of digits of precision for feed rate.  Default=1
    --axis-precision=4               ... number of digits of precision for axis moves.  Default=4
    --inches                         ... Convert output for US imperial mode (G20)
"""
# G21 for metric, G20 for US standard
UNITS = "G21"

# to distinguish python built-in open function from the one declared below
if open.__module__ in ["__builtin__", "io"]:
    pythonopen = open


def processArguments(values, argstring):
    """Process the arguments to the postprocessor."""
    #
    global UNITS

    try:
        for arg in argstring.split():
            if arg == "--header":
                values["OUTPUT_HEADER"] = True
            elif arg == "--no-header":
                values["OUTPUT_HEADER"] = False
            elif arg == "--comments":
                values["OUTPUT_COMMENTS"] = True
            elif arg == "--no-comments":
                values["OUTPUT_COMMENTS"] = False
            elif arg == "--line-numbers":
                values["OUTPUT_LINE_NUMBERS"] = True
            elif arg == "--no-line-numbers":
                values["OUTPUT_LINE_NUMBERS"] = False
            elif arg == "--show-editor":
                values["SHOW_EDITOR"] = True
            elif arg == "--no-show-editor":
                values["SHOW_EDITOR"] = False
            elif arg.split("=")[0] == "--axis-precision":
                values["AXIS_PRECISION"] = arg.split("=")[1]
            elif arg.split("=")[0] == "--feed-precision":
                values["FEED_PRECISION"] = arg.split("=")[1]
            elif arg == "--inches":
                UNITS = "G20"
                values["UNIT_SPEED_FORMAT"] = "in/min"
                values["UNIT_FORMAT"] = "in"

    except Exception:
        return False

    return True


def export(objectslist, filename, argstring):
    """Postprocess the objects in objectslist to filename."""
    #
    global UNITS

    #
    # Holds various values that are used throughout the postprocessor code.
    #
    values = {}
    PostUtils.init_values(values)
    values["AXIS_PRECISION"] = 4
    values["COMMENT_SYMBOL"] = ";"
    values["ENABLE_COOLANT"] = False
    values["FEED_PRECISION"] = 1
    values["FINISH_LABEL"] = "end"
    values["LIST_TOOLS_IN_PREAMBLE"] = True
    # This list controls the order of parameters in a line during output.
    # centroid doesn't want K properties on XY plane; Arcs need work.
    values["PARAMETER_ORDER"] = [
        "X",
        "Y",
        "Z",
        "A",
        "B",
        "I",
        "J",
        "F",
        "S",
        "T",
        "Q",
        "R",
        "L",
        "H",
    ]
    # Postamble text will appear following the last operation.
    values[
        "POSTAMBLE"
    ] = """M99
"""
    # Preamble text will appear at the beginning of the GCODE output file.
    values[
        "PREAMBLE"
    ] = """G53 G00 G17
"""
    values["REMOVE_MESSAGES"] = False
    values[
        "SAFETYBLOCK"
    ] = """G90 G80 G40 G49
"""
    values["SHOW_MACHINE_UNITS"] = False
    values["SHOW_OPERATION_LABELS"] = False
    values["STOP_SPINDLE_FOR_TOOL_CHANGE"] = False
    # spindle off,height offset canceled,spindle retracted
    # (M25 is a centroid command to retract spindle)
    values[
        "TOOLRETURN"
    ] = """M5
M25
G49 H0
"""
    # if true G43 will be output following tool changes
    values["USE_TLO"] = False
    # ZAXISRETURN = """G91 G28 X0 Z0
    # G90
    # """

    if not processArguments(values, argstring):
        return None

    values["UNITS"] = UNITS

    return PostUtils.export_common(values, objectslist, filename)
