# -*- coding: utf-8 -*-
# ***************************************************************************
# *   Copyright (c) 2014 Yorik van Havre <yorik@uncreated.net>              *
# *   Copyright (c) 2014 sliptonic <shopinthewoods@gmail.com>               *
# *   Copyright (c) 2015 Dan Falck <ddfalck@gmail.com>                      *
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

"""
These are functions related to arguments and values for creating custom post processors.
"""
import argparse
import os
import shlex


def init_shared_arguments(machine_name, preamble, postamble):
    """Initialize the shared arguments for postprocessors."""
    parser = argparse.ArgumentParser(prog=machine_name, add_help=False)
    parser.add_argument(
        "--metric", action="store_true", help="Convert output for Metric mode (G21) (default)"
    )
    parser.add_argument(
        "--inches", action="store_true", help="Convert output for US imperial mode (G20)"
    )
    parser.add_argument("--comments", action="store_true", help="Output comments (default)")
    parser.add_argument("--no-comments", action="store_true", help="Suppress comment output")
    parser.add_argument("--header", action="store_true", help="Output headers (default)")
    parser.add_argument("--no-header", action="store_true", help="Suppress header output")
    parser.add_argument("--line-numbers", action="store_true", help="Prefix with line numbers")
    parser.add_argument(
        "--no-line-numbers",
        action="store_true",
        help="Don't prefix with line numbers (default)",
    )
    parser.add_argument(
        "--modal",
        action="store_true",
        help="Don't output the G-command name if it is the same as the previous line.",
    )
    parser.add_argument(
        "--no-modal",
        action="store_true",
        help="Output the G-command name even if it is the same as the previous line (default)",
    )
    parser.add_argument(
        "--axis-modal",
        action="store_true",
        help="Don't output axis values if they are the same as the previous line",
    )
    parser.add_argument(
        "--no-axis-modal",
        action="store_true",
        help="Output axis values even if they are the same as the previous line (default)",
    )
    parser.add_argument(
        "--show-editor",
        action="store_true",
        help="Pop up editor before writing output (default)",
    )
    parser.add_argument(
        "--no-show-editor",
        action="store_true",
        help="Don't pop up editor before writing output",
    )
    parser.add_argument(
        "--tlo",
        action="store_true",
        help="Output tool length offset (G43) following tool changes (default)",
    )
    parser.add_argument(
        "--no-tlo",
        action="store_true",
        help="Suppress tool length offset (G43) following tool changes",
    )
    parser.add_argument(
        "--postamble",
        help='Set commands to be issued after the last command, default="' + postamble + '"',
    )
    parser.add_argument(
        "--preamble",
        help='Set commands to be issued before the first command, default="' + preamble + '"',
    )
    parser.add_argument(
        "--precision", default="3", help="Number of digits of precision, default = 3"
    )
    return parser


def process_shared_arguments(values, parser, argstring):
    """Process the arguments to the postprocessor."""
    try:
        args = parser.parse_args(shlex.split(argstring))
        if args.comments:
            values["OUTPUT_COMMENTS"] = True
        if args.no_comments:
            values["OUTPUT_COMMENTS"] = False
        if args.header:
            values["OUTPUT_HEADER"] = True
        if args.no_header:
            values["OUTPUT_HEADER"] = False
        if args.line_numbers:
            values["OUTPUT_LINE_NUMBERS"] = True
        if args.no_line_numbers:
            values["OUTPUT_LINE_NUMBERS"] = False
        if args.show_editor:
            values["SHOW_EDITOR"] = True
        if args.no_show_editor:
            values["SHOW_EDITOR"] = False
        if args.preamble is not None:
            values["PREAMBLE"] = args.preamble
        if args.postamble is not None:
            values["POSTAMBLE"] = args.postamble
        if args.metric:
            values["UNITS"] = "G21"
            values["UNIT_SPEED_FORMAT"] = "mm/min"
            values["UNIT_FORMAT"] = "mm"
            values["AXIS_PRECISION"] = 3
            values["FEED_PRECISION"] = 3
        #
        # A bit of possible argument ordering problem here:
        # args.precicion defaults to 3, which matches the
        # default precision for metric but not the default
        # precision for inches.  So we need to check for
        # inches after we check for args.precision.
        # How to override the inches precision?
        #
        if args.precision is not None:
            values["AXIS_PRECISION"] = args.precision
            values["FEED_PRECISION"] = args.precision
        if args.inches:
            values["UNITS"] = "G20"
            values["UNIT_SPEED_FORMAT"] = "in/min"
            values["UNIT_FORMAT"] = "in"
            values["AXIS_PRECISION"] = 4
            values["FEED_PRECISION"] = 4
        if args.modal:
            values["MODAL"] = True
        if args.no_modal:
            values["MODAL"] = False
        if args.tlo:
            values["USE_TLO"] = True
        if args.no_tlo:
            values["USE_TLO"] = False
        if args.axis_modal:
            values["OUTPUT_DOUBLES"] = False
        if args.no_axis_modal:
            values["OUTPUT_DOUBLES"] = True

    except Exception:
        return (False, None)

    return (True, args)


def init_shared_values(values):
    """Initialize the default values in postprocessors."""
    # Default precision for metric
    # (see http://linuxcnc.org/docs/2.7/html/gcode/overview.html#_g_code_best_practices)
    values["AXIS_PRECISION"] = 3
    values["COMMAND_SPACE"] = " "
    values["COMMENT_SYMBOL"] = "("
    # Global variables storing current position
    values["CURRENT_X"] = 0
    values["CURRENT_Y"] = 0
    values["CURRENT_Z"] = 0
    values["DRILL_CYCLES_TO_TRANSLATE"] = ("G81", "G82", "G83")
    # Default value of drill retractations (CURRENT_Z) other possible value is G99
    values["DRILL_RETRACT_MODE"] = "G98"
    values["ENABLE_COOLANT"] = False
    values["ENABLE_MACHINE_SPECIFIC_COMMANDS"] = False
    #
    # By default the line ending characters of the output file(s)
    # are written to match the system that the postprocessor runs on.
    # If you need to force the line ending characters to a specific
    # value, set this variable to "\n" or "\r\n" instead.
    #
    values["END_OF_LINE_CHARACTERS"] = os.linesep
    values["FEED_PRECISION"] = 3
    values["FINISH_LABEL"] = "Finish"
    # line number increment
    values["LINE_INCREMENT"] = 10
    # line number starting value
    values["line_number"] = 100
    values["LIST_TOOLS_IN_PREAMBLE"] = False
    # if true commands are suppressed if they are the same as the previous line.
    values["MODAL"] = False
    values["MOTION_COMMANDS"] = [
        "G0",
        "G00",
        "G1",
        "G01",
        "G2",
        "G02",
        "G3",
        "G03",
    ]
    # Motion gCode commands definition
    # G90 for absolute moves, G91 for relative
    values["MOTION_MODE"] = "G90"
    # default doesn't add bCNC operation block headers in output gCode file
    values["OUTPUT_BCNC"] = False
    values["OUTPUT_COMMENTS"] = True
    # if false duplicate axis values are suppressed if they are the same as the previous line.
    values["OUTPUT_DOUBLES"] = True
    values["OUTPUT_HEADER"] = True
    values["OUTPUT_LINE_NUMBERS"] = False
    values["OUTPUT_PATH_LABELS"] = False
    # output tool change gcode
    values["OUTPUT_TOOL_CHANGE"] = True
    # This list controls the order of parameters in a line during output.
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
    values["POSTAMBLE"] = """"""
    # Post operation text will be inserted after every operation
    values["POST_OPERATION"] = """"""
    values["PREAMBLE"] = """"""
    # Pre operation text will be inserted before every operation
    values["PRE_OPERATION"] = """"""
    values["RAPID_MOVES"] = ["G0", "G00"]
    # Rapid moves gCode commands definition
    values["REMOVE_MESSAGES"] = True
    # no movements after end of program
    values["RETURN_TO"] = None
    values["SAFETYBLOCK"] = """"""
    values["SHOW_EDITOR"] = True
    values["SHOW_MACHINE_UNITS"] = True
    values["SHOW_OPERATION_LABELS"] = True
    values["SPINDLE_DECIMALS"] = 0
    # no waiting after M3 / M4 by default
    values["SPINDLE_WAIT"] = 0
    values["STOP_SPINDLE_FOR_TOOL_CHANGE"] = True
    # These commands are ignored by commenting them out
    values["SUPPRESS_COMMANDS"] = []
    # Tool Change commands will be inserted before a tool change
    values["TOOL_CHANGE"] = """"""
    values["TOOLRETURN"] = """"""
    # If true, G81, G82 & G83 are translated in G0/G1 moves
    values["TRANSLATE_DRILL_CYCLES"] = False
    values["UNITS"] = "G21"
    values["UNIT_FORMAT"] = "mm"
    values["UNIT_SPEED_FORMAT"] = "mm/min"
    # if true G43 will be output following tool changes
    values["USE_TLO"] = True
