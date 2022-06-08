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

from __future__ import print_function

from PathScripts import PostUtilsArguments
from PathScripts import PostUtilsExport

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
# What are these variables used for?
# They are referenced in PathPostPostprocessor.PostProcessor.load(),
# don't appear to be used anywhere that I can find after that.
#
CORNER_MAX = {"x": 500, "y": 300, "z": 300}
CORNER_MIN = {"x": 0, "y": 0, "z": 0}
#
# Used in the argparser code that parses the options
# and sets up the tooltip arguments.
#
MACHINE_NAME = "GRBL"
#
# Any commands in this value will be output as the last commands
# in the G-code file.
#
POSTAMBLE = """M5
G17 G90
M2"""
#
# Any commands in this value will be output after the header and
# safety block at the beginning of the G-code file.
#
PREAMBLE = """G17 G90"""
#
#
#
TOOLTIP = """
Generate g-code from a Path that is compatible with the grbl controller:

import refactored_grbl_post
refactored_grbl_post.export(object, "/path/to/file.ncc")
"""
#
# Parser arguments list & definition
#
parser = PostUtilsArguments.init_shared_arguments(MACHINE_NAME, PREAMBLE, POSTAMBLE)
#
# Add any additional arguments that are not shared with other postprocessors here.
#
grbl_specific = parser.add_argument_group("GRBL specific arguments")
grbl_specific.add_argument(
    "--precision",
    default=-1,
    type=int,
    help="Number of digits of precision for both feed rate and axis moves, default is 3 for metric or 4 for inches",
)
grbl_specific.add_argument(
    "--tlo",
    action="store_true",
    help="Output tool length offset (G43) following tool changes",
)
grbl_specific.add_argument(
    "--no-tlo",
    action="store_true",
    help="Suppress tool length offset (G43) following tool changes (default)",
)
grbl_specific.add_argument(
    "--tool-change",
    action="store_true",
    help="Insert M6 and any other tool change G-code for all tool changes",
)
grbl_specific.add_argument(
    "--no-tool-change",
    action="store_true",
    help="Convert M6 to a comment for all tool changes (default)",
)
TOOLTIP_ARGS = parser.format_help()
#
# Default to metric mode
#
UNITS = "G21"


def export(objectslist, filename, argstring):
    """Postprocess the objects in objectslist to filename."""
    #
    global parser
    global POSTAMBLE
    global PREAMBLE
    global UNITS

    # print(parser.format_help())

    #
    # Holds various values that are used throughout the postprocessor code.
    #
    values = {}
    PostUtilsArguments.init_shared_values(values)
    #
    # Set any values here that need to override the default values set
    # in the init_shared_values routine.
    #
    # If this is set to True, then commands that are placed in
    # comments that look like (MC_RUN_COMMAND: blah) will be output.
    #
    values["ENABLE_MACHINE_SPECIFIC_COMMANDS"] = True
    #
    # Default to outputting Path labels at the beginning of each Path.
    #
    values["OUTPUT_PATH_LABELS"] = True
    #
    # Default to not outputting M6 tool changes (comment it) as grbl currently does not handle it
    #
    values["OUTPUT_TOOL_CHANGE"] = False
    #
    # The order of the parameters.
    # Arcs may only work on the XY plane (this needs to be verified).
    #
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
    #
    # Do not show the current machine units just before the PRE_OPERATION.
    #
    values["SHOW_MACHINE_UNITS"] = False
    #
    # Default to not outputting a G43 following tool changes
    #
    values["USE_TLO"] = False

    values["POSTAMBLE"] = POSTAMBLE
    values["POSTPROCESSOR_FILE_NAME"] = __name__
    values["PREAMBLE"] = PREAMBLE
    values["UNITS"] = UNITS

    (flag, args) = PostUtilsArguments.process_shared_arguments(values, parser, argstring)
    if not flag:
        return None
    #
    # Process any additional arguments here
    #
    if args.precision == -1:
        if values["UNITS"] == "G21":
            values["AXIS_PRECISION"] = 3
            values["FEED_PRECISION"] = 3
        if values["UNITS"] == "G20":
            values["AXIS_PRECISION"] = 4
            values["FEED_PRECISION"] = 4
    else:
        values["AXIS_PRECISION"] = args.precision
        values["FEED_PRECISION"] = args.precision
    if args.tlo:
        values["USE_TLO"] = True
    if args.no_tlo:
        values["USE_TLO"] = False
    if args.tool_change:
        values["OUTPUT_TOOL_CHANGE"] = True
    if args.no_tool_change:
        values["OUTPUT_TOOL_CHANGE"] = False
    #
    # Update the global variables that might have been modified
    # while processing the arguments.
    #
    POSTAMBLE = values["POSTAMBLE"]
    PREAMBLE = values["PREAMBLE"]
    UNITS = values["UNITS"]

    return PostUtilsExport.export_common(values, objectslist, filename)


# print(__name__ + ": GCode postprocessor loaded.")
