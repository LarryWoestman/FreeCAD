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

import datetime

import FreeCAD
from FreeCAD import Units
from PathScripts import PathToolController
from PathScripts import PostUtils

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

# to distinguish python built-in open function from the one declared below
if open.__module__ in ["__builtin__", "io"]:
    pythonopen = open


def processArguments(values, argstring):
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
            values["UNITS"] = "G20"
            values["UNIT_SPEED_FORMAT"] = "in/min"
            values["UNIT_FORMAT"] = "in"


def export(objectslist, filename, argstring):
    values = {}
    PostUtils.init_values(values)
    values["COMMENT_SYMBOL"] = ";"
    values["CORNER_MIN"] = {"x": -609.6, "y": -152.4, "z": 0}  # use metric for internal units
    values["CORNER_MAX"] = {"x": 609.6, "y": 152.4, "z": 304.8}  # use metric for internal units
    values["MACHINE_NAME"] = "Centroid"
    # Postamble text will appear following the last operation.
    values["POSTAMBLE"] = """M99
"""
    # Preamble text will appear at the beginning of the GCODE output file.
    values["PREAMBLE"] = """G53 G00 G17
"""

    AXIS_PRECISION = 4
    FEED_PRECISION = 1
    SPINDLE_DECIMALS = 0

    # gCode header with information about CAD-software, post-processor
    # and date/time
    if FreeCAD.ActiveDocument:
        cam_file = FreeCAD.ActiveDocument.FileName
    else:
        cam_file = "<None>"

    HEADER = """;Exported by FreeCAD
    ;Post Processor: {}
    ;CAM file: {}
    ;Output Time: {}
    """.format(
        __name__, cam_file, str(datetime.datetime.now())
    )

    # spindle off,height offset canceled,spindle retracted
    # (M25 is a centroid command to retract spindle)
    TOOLRETURN = """M5
    M25
    G49 H0
    """

    ZAXISRETURN = """G91 G28 X0 Z0
    G90
    """

    SAFETYBLOCK = """G90 G80 G40 G49
    """

    # Tool Change commands will be inserted before a tool change
    TOOL_CHANGE = """"""

    processArguments(argstring)
    for i in objectslist:
        print(i.Name)

    print("postprocessing...")
    gcode = ""

    # write header
    if values["OUTPUT_HEADER"]:
        gcode += HEADER

    gcode += SAFETYBLOCK

    # Write the preamble
    if OUTPUT_COMMENTS:
        for item in objectslist:
            if hasattr(item, "Proxy") and isinstance(
                item.Proxy, PathToolController.ToolController
            ):
                gcode += ";T{}={}\n".format(item.ToolNumber, item.Name)
        gcode += linenumber() + ";begin preamble\n"
    for line in PREAMBLE.splitlines(True):
        gcode += linenumber() + line

    gcode += linenumber() + UNITS + "\n"

    for obj in objectslist:
        # do the pre_op
        if OUTPUT_COMMENTS:
            gcode += linenumber() + ";begin operation\n"
        for line in PRE_OPERATION.splitlines(True):
            gcode += linenumber() + line

        gcode += parse(obj)

        # do the post_op
        if OUTPUT_COMMENTS:
            gcode += linenumber() + ";end operation: %s\n" % obj.Label
        for line in POST_OPERATION.splitlines(True):
            gcode += linenumber() + line

    # do the post_amble

    if OUTPUT_COMMENTS:
        gcode += ";begin postamble\n"
    for line in TOOLRETURN.splitlines(True):
        gcode += linenumber() + line
    for line in SAFETYBLOCK.splitlines(True):
        gcode += linenumber() + line
    for line in POSTAMBLE.splitlines(True):
        gcode += linenumber() + line

    if FreeCAD.GuiUp and values["SHOW_EDITOR"]:
        dia = PostUtils.GCodeEditorDialog()
        dia.editor.setText(gcode)
        result = dia.exec_()
        if result:
            final = dia.editor.toPlainText()
        else:
            final = gcode
    else:
        final = gcode

    print("done postprocessing.")

    if not filename == "-":
        gfile = pythonopen(filename, "w")
        gfile.write(final)
        gfile.close()

    return final


def linenumber():
    global LINENR
    if OUTPUT_LINE_NUMBERS is True:
        LINENR += 10
        return "N" + str(LINENR) + " "
    return ""


def parse(pathobj):
    out = ""
    lastcommand = None
    axis_precision_string = "." + str(AXIS_PRECISION) + "f"
    feed_precision_string = "." + str(FEED_PRECISION) + "f"
    # params = ['X','Y','Z','A','B','I','J','K','F','S'] #This list control
    # the order of parameters
    # centroid doesn't want K properties on XY plane  Arcs need work.
    params = ["X", "Y", "Z", "A", "B", "I", "J", "F", "S", "T", "Q", "R", "L", "H"]

    if hasattr(pathobj, "Group"):  # We have a compound or project.
        # if OUTPUT_COMMENTS:
        #     out += linenumber() + "(compound: " + pathobj.Label + ")\n"
        for p in pathobj.Group:
            out += parse(p)
        return out
    else:  # parsing simple path

        # groups might contain non-path things like stock.
        if not hasattr(pathobj, "Path"):
            return out

        # if OUTPUT_COMMENTS:
        #     out += linenumber() + "(" + pathobj.Label + ")\n"

        for c in pathobj.Path.Commands:
            commandlist = []  # list of elements in the command, code and params.
            command = c.Name  # command M or G code or comment string

            if command[0] == "(":
                command = PostUtils.fcoms(command, values["COMMENT_SYMBOL"])

            commandlist.append(command)
            # if modal: only print the command if it is not the same as the
            # last one
            if MODAL is True:
                if command == lastcommand:
                    commandlist.pop(0)

            # Now add the remaining parameters in order
            for param in params:
                if param in c.Parameters:
                    if param == "F":
                        if c.Name not in [
                            "G0",
                            "G00",
                        ]:  # centroid doesn't use rapid speeds
                            speed = Units.Quantity(
                                c.Parameters["F"], FreeCAD.Units.Velocity
                            )
                            commandlist.append(
                                param
                                + format(
                                    float(speed.getValueAs(UNIT_SPEED_FORMAT)),
                                    feed_precision_string,
                                )
                            )
                    elif param == "H":
                        commandlist.append(param + str(int(c.Parameters["H"])))
                    elif param == "S":
                        commandlist.append(
                            param
                            + PostUtils.fmt(c.Parameters["S"], SPINDLE_DECIMALS, "G21")
                        )
                    elif param == "T":
                        commandlist.append(param + str(int(c.Parameters["T"])))
                    else:
                        pos = Units.Quantity(c.Parameters[param], FreeCAD.Units.Length)
                        commandlist.append(
                            param
                            + format(
                                float(pos.getValueAs(UNIT_FORMAT)),
                                axis_precision_string,
                            )
                        )
            outstr = str(commandlist)
            outstr = outstr.replace("[", "")
            outstr = outstr.replace("]", "")
            outstr = outstr.replace("'", "")
            outstr = outstr.replace(",", "")

            # store the latest command
            lastcommand = command

            # Check for Tool Change:
            if command == "M6":
                # if OUTPUT_COMMENTS:
                #     out += linenumber() + "(begin toolchange)\n"
                for line in TOOL_CHANGE.splitlines(True):
                    out += linenumber() + line

            # if command == "message":
            #     if OUTPUT_COMMENTS is False:
            #         out = []
            #     else:
            #         commandlist.pop(0)  # remove the command

            # prepend a line number and append a newline
            if len(commandlist) >= 1:
                if OUTPUT_LINE_NUMBERS:
                    commandlist.insert(0, (linenumber()))

                # append the line to the final output
                for w in commandlist:
                    out += w + COMMAND_SPACE
                out = out.strip() + "\n"

        return out
