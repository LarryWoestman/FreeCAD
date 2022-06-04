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
CORNER_MAX = {"x": 500, "y": 300, "z": 300}
CORNER_MIN = {"x": 0, "y": 0, "z": 0}
MACHINE_NAME = "LinuxCNC"
# Postamble text will appear following the last operation.
POSTAMBLE = """M05
G17 G54 G90 G80 G40
M2"""
# Preamble text will appear at the beginning of the GCODE output file.
PREAMBLE = """G17 G54 G40 G49 G80 G90"""
TOOLTIP = """This is a postprocessor file for the Path workbench. It is used to
take a pseudo-gcode fragment outputted by a Path object, and output
real GCode suitable for a linuxcnc 3 axis mill. This postprocessor, once placed
in the appropriate PathScripts folder, can be used directly from inside
FreeCAD, via the GUI importer or via python scripts with:

import refactored_linuxcnc_post
refactored_linuxcnc_post.export(object,"/path/to/file.ncc","")
"""
parser = PostUtilsArguments.init_shared_arguments(MACHINE_NAME, PREAMBLE, POSTAMBLE)
#
# Add any additional arguments that are not shared here.
#
TOOLTIP_ARGS = parser.format_help()
# G21 for metric, G20 for US standard
UNITS = "G21"


def export(objectslist, filename, argstring):
    """Postprocess the objects in objectslist to filename."""
    #
    global parser
    global POSTAMBLE
    global PREAMBLE
    global UNITS

#    print(parser.format_help())

    #
    # Holds various values that are used throughout the postprocessor code.
    #
    values = {}
    PostUtilsArguments.init_shared_values(values)
    #
    # Set any values here that need to override the default values set
    # in the init_shared_values routine.
    #
    values["ENABLE_COOLANT"] = True
    # the order of parameters
    # linuxcnc doesn't want K properties on XY plane; Arcs need work.
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
    # if args.example:  # for an argument that is a flag:  --example
    #     values["example"] = True
    # if args.no_example:  # for an argument that is a flag:  --no-example
    #     values["example"] = False
    # if args.example is not None:  # for an argument with a value:  --example 1234
    #     values["example"] = args.example
    #
    # Update the global variables that might have been modified
    # while processing the arguments.
    #
    POSTAMBLE = values["POSTAMBLE"]
    PREAMBLE = values["PREAMBLE"]
    UNITS = values["UNITS"]

    return PostUtilsExport.export_common(values, objectslist, filename)


# print(__name__ + " gcode postprocessor loaded.")
