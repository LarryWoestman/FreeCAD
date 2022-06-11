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
CORNER_MAX = {"x": 609.6, "y": 152.4, "z": 304.8}
CORNER_MIN = {"x": -609.6, "y": -152.4, "z": 0}
#
# Used in the argparser code that parses the options
# and sets up the tooltip arguments.
#
MACHINE_NAME = "Centroid"
#
# Any commands in this value will be output as the last commands
# in the G-code file.
#
POSTAMBLE = """M99"""
#
# Any commands in this value will be output after the header and
# safety block at the beginning of the G-code file.
#
PREAMBLE = """G53 G00 G17"""
#
#
#
TOOLTIP = """
This is a postprocessor file for the Path workbench. It is used to
take a pseudo-gcode fragment outputted by a Path object, and output
real GCode suitable for a centroid 3 axis mill. This postprocessor, once placed
in the appropriate PathScripts folder, can be used directly from inside
FreeCAD, via the GUI importer or via python scripts with:

import refactored_centroid_post
refactored_centroid_post.export(object,"/path/to/file.ncc","")
"""
#
# Parser arguments list & definition
#
parser = PostUtilsArguments.init_shared_arguments(MACHINE_NAME, PREAMBLE, POSTAMBLE)
#
# Add any additional arguments that are not shared with other postprocessors here.
#
centroid_specific = parser.add_argument_group("Centroid specific arguments")
centroid_specific.add_argument(
    "--axis-precision",
    default=-1,
    type=int,
    help="Number of digits of precision for axis moves, default is 4",
)
centroid_specific.add_argument(
    "--feed-precision",
    default=-1,
    type=int,
    help="Number of digits of precision for feed rate, default is 1",
)
centroid_specific.add_argument(
    "--tlo",
    action="store_true",
    help="Output tool length offset (G43) following tool changes",
)
centroid_specific.add_argument(
    "--no-tlo",
    action="store_true",
    help="Suppress tool length offset (G43) following tool changes (default)",
)
centroid_specific.add_argument(
    "--tool-change",
    action="store_true",
    help="Insert M6 and any other tool change G-code for all tool changes (default)",
)
centroid_specific.add_argument(
    "--no-tool-change", action="store_true", help="Convert M6 to a comment for all tool changes"
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
    # The default for metric is 3 digits after the decimal point.
    # Use 4 instead.
    #
    values["AXIS_PRECISION"] = 4
    #
    # Use ";" as the comment symbol
    #
    values["COMMENT_SYMBOL"] = ";"
    #
    # The default precision for feed precision is also set to 3 for metric.
    # Use 1 instead.
    #
    values["FEED_PRECISION"] = 1
    #
    # This value usually shows up in the post_op comment as "Finish operation:".
    # Change it to "End" to produce "End operation:".
    #
    values["FINISH_LABEL"] = "End"
    #
    # If this value is True, then a list of tool numbers
    # with their labels are output just before the preamble.
    #
    values["LIST_TOOLS_IN_PREAMBLE"] = True
    #
    # This list controls the order of parameters in a line during output.
    # centroid doesn't want K properties on XY plane; Arcs need work.
    #
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
    #
    # Output any messages.
    #
    values["REMOVE_MESSAGES"] = False
    #
    # Any commands in this value are output after the header but before the preamble,
    # then again after the TOOLRETURN but before the POSTAMBLE.
    #
    values["SAFETYBLOCK"] = """G90 G80 G40 G49"""
    #
    # Do not show the current machine units just before the PRE_OPERATION.
    #
    values["SHOW_MACHINE_UNITS"] = False
    #
    # Do not show the current operation label just before the PRE_OPERATION.
    #
    values["SHOW_OPERATION_LABELS"] = False
    #
    # Do not output an M5 command to stop the spindle for tool changes.
    #
    values["STOP_SPINDLE_FOR_TOOL_CHANGE"] = False
    #
    # spindle off,height offset canceled,spindle retracted
    # (M25 is a centroid command to retract spindle)
    #
    values[
        "TOOLRETURN"
    ] = """M5
M25
G49 H0"""
    #
    # Default to not outputting a G43 following tool changes
    #
    values["USE_TLO"] = False
    #
    # THis was in the original centroid postprocessor file
    # but does not appear to be used anywhere.
    #
    # ZAXISRETURN = """G91 G28 X0 Z0 G90"""
    #
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
    if args.axis_precision == -1:
        if values["UNITS"] == "G21":
            values["AXIS_PRECISION"] = 4
        if values["UNITS"] == "G20":
            values["AXIS_PRECISION"] = 4
    else:
        values["AXIS_PRECISION"] = args.axis_precision
    if args.feed_precision == -1:
        if values["UNITS"] == "G21":
            values["FEED_PRECISION"] = 1
        if values["UNITS"] == "G20":
            values["FEED_PRECISION"] = 1
    else:
        values["FEED_PRECISION"] = args.feed_precision
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
