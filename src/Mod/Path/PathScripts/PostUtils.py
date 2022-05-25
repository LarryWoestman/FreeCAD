# -*- coding: utf-8 -*-
# ***************************************************************************
# *   Copyright (c) 2014 Yorik van Havre <yorik@uncreated.net>              *
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
These are common functions and classes for creating custom post processors.
"""
import datetime
import os

from PySide import QtCore, QtGui

import FreeCAD
from FreeCAD import Units

import Path
import Part

from PathMachineState import MachineState
from PathScripts import PathToolController
from PathScripts.PathGeom import CmdMoveArc, edgeForCmd, cmdsForEdge

translate = FreeCAD.Qt.translate
FreeCADGui = None
if FreeCAD.GuiUp:
    import FreeCADGui

# to distinguish python built-in open function from the one declared below
if open.__module__ in ["__builtin__", "io"]:
    pythonopen = open


class GCodeHighlighter(QtGui.QSyntaxHighlighter):
    def __init__(self, parent=None):
        super(GCodeHighlighter, self).__init__(parent)

        keywordFormat = QtGui.QTextCharFormat()
        keywordFormat.setForeground(QtCore.Qt.cyan)
        keywordFormat.setFontWeight(QtGui.QFont.Bold)
        keywordPatterns = ["\\bG[0-9]+\\b", "\\bM[0-9]+\\b"]

        self.highlightingRules = [
            (QtCore.QRegExp(pattern), keywordFormat) for pattern in keywordPatterns
        ]

        speedFormat = QtGui.QTextCharFormat()
        speedFormat.setFontWeight(QtGui.QFont.Bold)
        speedFormat.setForeground(QtCore.Qt.green)
        self.highlightingRules.append((QtCore.QRegExp("\\bF[0-9\\.]+\\b"), speedFormat))

    def highlightBlock(self, text):
        for pattern, hlFormat in self.highlightingRules:
            expression = QtCore.QRegExp(pattern)
            index = expression.indexIn(text)
            while index >= 0:
                length = expression.matchedLength()
                self.setFormat(index, length, hlFormat)
                index = expression.indexIn(text, index + length)


class GCodeEditorDialog(QtGui.QDialog):
    def __init__(self, parent=None):
        if parent is None:
            parent = FreeCADGui.getMainWindow()
        QtGui.QDialog.__init__(self, parent)

        layout = QtGui.QVBoxLayout(self)

        # nice text editor widget for editing the gcode
        self.editor = QtGui.QTextEdit()
        font = QtGui.QFont()
        font.setFamily("Courier")
        font.setFixedPitch(True)
        font.setPointSize(10)
        self.editor.setFont(font)
        self.editor.setText("G01 X55 Y4.5 F300.0")
        layout.addWidget(self.editor)

        # OK and Cancel buttons
        self.buttons = QtGui.QDialogButtonBox(
            QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel,
            QtCore.Qt.Horizontal,
            self,
        )
        layout.addWidget(self.buttons)

        # restore placement and size
        self.paramKey = "User parameter:BaseApp/Values/Mod/Path/GCodeEditor/"
        params = FreeCAD.ParamGet(self.paramKey)
        posX = params.GetInt("posX")
        posY = params.GetInt("posY")
        if posX > 0 and posY > 0:
            self.move(posX, posY)
        width = params.GetInt("width")
        height = params.GetInt("height")
        if width > 0 and height > 0:
            self.resize(width, height)

        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

    def done(self, *args, **kwargs):
        params = FreeCAD.ParamGet(self.paramKey)
        params.SetInt("posX", self.x())
        params.SetInt("posY", self.y())
        params.SetInt("width", self.size().width())
        params.SetInt("height", self.size().height())
        return QtGui.QDialog.done(self, *args, **kwargs)


def stringsplit(commandline):
    returndict = {
        "command": None,
        "X": None,
        "Y": None,
        "Z": None,
        "A": None,
        "B": None,
        "F": None,
        "T": None,
        "S": None,
        "I": None,
        "J": None,
        "K": None,
        "txt": None,
    }
    wordlist = [a.strip() for a in commandline.split(" ")]
    if wordlist[0][0] == "(":
        returndict["command"] = "message"
        returndict["txt"] = wordlist[0]
    else:
        returndict["command"] = wordlist[0]
    for word in wordlist[1:]:
        returndict[word[0]] = word[1:]

    return returndict


def fmt(num, dec, units):
    """Use to format axis moves, feedrate, etc for decimal places and units."""
    if units == "G21":  # metric
        fnum = "%.*f" % (dec, num)
    else:  # inch
        fnum = "%.*f" % (dec, num / 25.4)  # since FreeCAD uses metric units internally
    return fnum


def editor(gcode):
    """Pops up a handy little editor to look at the code output."""
    prefs = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/Path")
    # default Max Highlighter Size = 512 Ko
    defaultMHS = 512 * 1024
    mhs = prefs.GetUnsigned("inspecteditorMaxHighlighterSize", defaultMHS)

    dia = GCodeEditorDialog()
    dia.editor.setText(gcode)
    gcodeSize = len(dia.editor.toPlainText())
    if gcodeSize <= mhs:
        # because of poor performance, syntax highlighting is
        # limited to mhs octets (default 512 KB).
        # It seems than the response time curve has an inflexion near 500 KB
        # beyond 500 KB, the response time increases exponentially.
        dia.highlighter = GCodeHighlighter(dia.editor.document())
    else:
        FreeCAD.Console.PrintMessage(
            translate(
                "Path",
                "GCode size too big ({} o), disabling syntax highlighter.".format(gcodeSize),
            )
        )
    result = dia.exec_()
    if result:  # If user selected 'OK' get modified G Code
        final = dia.editor.toPlainText()
    else:
        final = gcode
    return final


def fcoms(string, commentsym):
    """Filter and rebuild comments with user preferred comment symbol."""
    if len(commentsym) == 1:
        s1 = string.replace("(", commentsym)
        comment = s1.replace(")", "")
    else:
        return string
    return comment


def splitArcs(path):
    """Filter a path object and replace all G2/G3 moves with discrete G1 moves.

    Returns a Path object.
    """
    prefGrp = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/Path")
    deflection = prefGrp.GetFloat("LibAreaCurveAccuarcy", 0.01)

    results = []
    if not isinstance(path, Path.Path):
        raise TypeError("path must be a Path object")

    machine = MachineState()
    for command in path.Commands:

        if command.Name not in CmdMoveArc:
            machine.addCommand(command)
            results.append(command)
            continue

        edge = edgeForCmd(command, machine.getPosition())
        pts = edge.discretize(Deflection=deflection)
        edges = [Part.makeLine(v1, v2) for v1, v2 in zip(pts, pts[1:])]
        for edge in edges:
            results.extend(cmdsForEdge(edge))

        machine.addCommand(command)

    return Path.Path(results)


def init_values(values):
    """Initialize many of the commonly used values in postprocessors."""
    values["COMMAND_SPACE"] = " "
    #
    # By default the line ending characters of the output file(s)
    # are written to match the system that the postprocessor runs on.
    # If you need to force the line ending characters to a specific
    # value, set this variable to "\n" or "\r\n" instead.
    #
    values["END_OF_LINE_CHARACTERS"] = os.linesep
    # line number starting value
    values["line_number"] = 100
    # if true commands are suppressed if they are the same as the previous line.
    values["MODAL"] = False
    values["OUTPUT_COMMENTS"] = True
    values["OUTPUT_HEADER"] = True
    values["OUTPUT_LINE_NUMBERS"] = False
    # if false duplicate axis values are suppressed if they are the same as the previous line.
    values["OUTPUT_DOUBLES"] = True
    # Post operation text will be inserted after every operation
    values["POST_OPERATION"] = """"""
    # Pre operation text will be inserted before every operation
    values["PRE_OPERATION"] = """"""
    values["SHOW_EDITOR"] = True
    values["SPINDLE_DECIMALS"] = 0
    # Tool Change commands will be inserted before a tool change
    values["TOOL_CHANGE"] = """"""
    values["UNIT_FORMAT"] = "mm"
    values["UNIT_SPEED_FORMAT"] = "mm/min"


def linenumber(values):
    """Output the next line number if appropriate."""
    if values["OUTPUT_LINE_NUMBERS"]:
        line_num = str(values["line_number"])
        values["line_number"] += 10
        return "N" + line_num + " "
    return ""


def create_comment(comment_string, comment_symbol):
    """Create a comment from a string using the correct comment symbol."""
    if comment_symbol != "(":
        comment_string = fcoms(comment_string, comment_symbol)
    return comment_string


def parse(values, pathobj):
    """Parse a Path."""
    out = ""
    lastcommand = None
    axis_precision_string = "." + str(values["AXIS_PRECISION"]) + "f"
    feed_precision_string = "." + str(values["FEED_PRECISION"]) + "f"

    currLocation = {}  # keep track for no doubles
    firstmove = Path.Command("G0", {"X": -1, "Y": -1, "Z": -1, "F": 0.0})
    currLocation.update(firstmove.Parameters)  # set First location Parameters

    if hasattr(pathobj, "Group"):  # We have a compound or project.
        # if values["OUTPUT_COMMENTS"]:
        #     comment = create_comment(
        #         "(compound: " + pathobj.Label + ")\n", values["COMMENT_SYMBOL"]
        #     )
        #   out += linenumber(values) + comment
        for p in pathobj.Group:
            out += parse(values, p)
        return out
    else:  # parsing simple path

        # groups might contain non-path things like stock.
        if not hasattr(pathobj, "Path"):
            return out

        # if values["OUTPUT_COMMENTS"]:
        #     comment = create_comment(
        #         "(" + pathobj.Label + ")\n", values["COMMENT_SYMBOL"]
        #     )
        #     out += linenumber(values) + comment

        for c in pathobj.Path.Commands:

            # List of elements in the command, code, and params.
            outstring = []
            # command M or G code or comment string
            command = c.Name
            if command[0] == "(":
                if values["OUTPUT_COMMENTS"]:
                    if values["COMMENT_SYMBOL"] != "(":
                        command = fcoms(command, values["COMMENT_SYMBOL"])
                else:
                    continue
            outstring.append(command)

            # if modal: suppress the command if it is the same as the last one
            if values["MODAL"]:
                if command == lastcommand:
                    outstring.pop(0)

            # Now add the remaining parameters in order
            for param in values["PARAMETER_ORDER"]:
                if param in c.Parameters:
                    if param == "F" and (
                        currLocation[param] != c.Parameters[param] or values["OUTPUT_DOUBLES"]
                    ):
                        # centroid and linuxcnc doesn't use rapid speeds
                        if c.Name not in [
                            "G0",
                            "G00",
                        ]:
                            speed = Units.Quantity(c.Parameters["F"], FreeCAD.Units.Velocity)
                            if speed.getValueAs(values["UNIT_SPEED_FORMAT"]) > 0.0:
                                outstring.append(
                                    param
                                    + format(
                                        float(speed.getValueAs(values["UNIT_SPEED_FORMAT"])),
                                        feed_precision_string,
                                    )
                                )
                        else:
                            continue
                    elif param == "T":
                        outstring.append(param + str(int(c.Parameters["T"])))
                    elif param == "H":
                        outstring.append(param + str(int(c.Parameters["H"])))
                    elif param == "D":
                        outstring.append(param + str(int(c.Parameters["D"])))
                    elif param == "S":
                        outstring.append(
                            param + fmt(c.Parameters["S"], values["SPINDLE_DECIMALS"], "G21")
                        )
                    else:
                        if (
                            (not values["OUTPUT_DOUBLES"])
                            and (param in currLocation)
                            and (currLocation[param] == c.Parameters[param])
                        ):
                            continue
                        else:
                            pos = Units.Quantity(c.Parameters[param], FreeCAD.Units.Length)
                            outstring.append(
                                param
                                + format(
                                    float(pos.getValueAs(values["UNIT_FORMAT"])),
                                    axis_precision_string,
                                )
                            )

            # store the latest command
            lastcommand = command
            currLocation.update(c.Parameters)

            # Check for Tool Change:
            if command == "M6":
                if values["STOP_SPINDLE_FOR_TOOL_CHANGE"]:
                    # stop the spindle
                    out += linenumber(values) + "M5\n"
                for line in values["TOOL_CHANGE"].splitlines(False):
                    out += linenumber(values) + line + "\n"

            if command == "message" and values["REMOVE_MESSAGES"]:
                if values["OUTPUT_COMMENTS"] is False:
                    out = []
                else:
                    outstring.pop(0)  # remove the command

            # prepend a line number and append a newline
            if len(outstring) >= 1:
                if values["OUTPUT_LINE_NUMBERS"]:
                    # In this case we don't use the linenumber function
                    # because it appends a space which we don't want.
                    values["line_number"] += 10
                    line_no = "N" + str(values["line_number"])
                    outstring.insert(0, (line_no))

                # append the line to the final output
                out += values["COMMAND_SPACE"].join(outstring)
                # Note: Do *not* strip `out`, since that forces the allocation
                # of a contiguous string & thus quadratic complexity.
                out += "\n"

            # add height offset
            if command == "M6" and values["USE_TLO"]:
                out += linenumber(values) + "G43 H" + str(int(c.Parameters["T"])) + "\n"

        return out


def export_common(values, objectslist, filename):
    """Do the common parts of postprocessing the objects in objectslist to filename."""
    #
    for obj in objectslist:
        if not hasattr(obj, "Path"):
            print(
                "The object " + obj.Name + " is not a path. Please select only path and Compounds."
            )
            return None

    # for obj in objectslist:
    #    print(obj.Name)

    print("postprocessing...")
    gcode = ""

    # write header
    if values["OUTPUT_HEADER"]:
        comment = create_comment("(Exported by FreeCAD)\n", values["COMMENT_SYMBOL"])
        gcode += linenumber(values) + comment
        comment = create_comment(
            "(Post Processor: " + values["POSTPROCESSOR_FILE_NAME"] + ")\n",
            values["COMMENT_SYMBOL"],
        )
        gcode += linenumber(values) + comment
        if FreeCAD.ActiveDocument:
            cam_file = os.path.basename(FreeCAD.ActiveDocument.FileName)
        else:
            cam_file = "<None>"
        comment = create_comment("(Cam File: " + cam_file + ")\n", values["COMMENT_SYMBOL"])
        gcode += linenumber(values) + comment
        comment = create_comment(
            "(Output Time:" + str(datetime.datetime.now()) + ")\n", values["COMMENT_SYMBOL"]
        )
        gcode += linenumber(values) + comment

    for line in values["SAFETYBLOCK"].splitlines(False):
        gcode += linenumber(values) + line + "\n"

    # Write the preamble
    if values["OUTPUT_COMMENTS"]:
        if values["LIST_TOOLS_IN_PREAMBLE"]:
            for item in objectslist:
                if hasattr(item, "Proxy") and isinstance(
                    item.Proxy, PathToolController.ToolController
                ):
                    comment = create_comment(
                        "(T{}={})\n".format(item.ToolNumber, item.Name), values["COMMENT_SYMBOL"]
                    )
                    gcode += linenumber(values) + comment
        comment = create_comment("(begin preamble)\n", values["COMMENT_SYMBOL"])
        gcode += linenumber(values) + comment
    for line in values["PREAMBLE"].splitlines(False):
        gcode += linenumber(values) + line + "\n"
    gcode += linenumber(values) + values["UNITS"] + "\n"

    for obj in objectslist:

        # Skip inactive operations
        if hasattr(obj, "Active"):
            if not obj.Active:
                continue
        if hasattr(obj, "Base") and hasattr(obj.Base, "Active"):
            if not obj.Base.Active:
                continue

        # do the pre_op
        if values["OUTPUT_COMMENTS"]:
            if values["SHOW_OPERATION_LABELS"]:
                comment = create_comment(
                    "(begin operation: %s)\n" % obj.Label, values["COMMENT_SYMBOL"]
                )
            else:
                comment = create_comment("(begin operation)\n", values["COMMENT_SYMBOL"])
            gcode += linenumber(values) + comment
            if values["SHOW_MACHINE_UNITS"]:
                comment = create_comment(
                    "(machine units: %s)\n" % values["UNIT_SPEED_FORMAT"], values["COMMENT_SYMBOL"]
                )
                gcode += linenumber(values) + comment
        for line in values["PRE_OPERATION"].splitlines(False):
            gcode += linenumber(values) + line + "\n"

        # get coolant mode
        coolantMode = "None"
        if hasattr(obj, "CoolantMode") or hasattr(obj, "Base") and hasattr(obj.Base, "CoolantMode"):
            if hasattr(obj, "CoolantMode"):
                coolantMode = obj.CoolantMode
            else:
                coolantMode = obj.Base.CoolantMode

        # turn coolant on if required
        if values["ENABLE_COOLANT"]:
            if values["OUTPUT_COMMENTS"]:
                if not coolantMode == "None":
                    comment = create_comment(
                        "(Coolant On:" + coolantMode + ")\n", values["COMMENT_SYMBOL"]
                    )
                    gcode += linenumber(values) + comment
            if coolantMode == "Flood":
                gcode += linenumber(values) + "M8" + "\n"
            if coolantMode == "Mist":
                gcode += linenumber(values) + "M7" + "\n"

        # process the operation gcode
        gcode += parse(values, obj)

        # do the post_op
        if values["OUTPUT_COMMENTS"]:
            comment = create_comment(
                "(%s operation: %s)\n" % (values["FINISH_LABEL"], obj.Label),
                values["COMMENT_SYMBOL"],
            )
            gcode += linenumber(values) + comment
        for line in values["POST_OPERATION"].splitlines(False):
            gcode += linenumber(values) + line + "\n"

        # turn coolant off if required
        if values["ENABLE_COOLANT"]:
            if not coolantMode == "None":
                if values["OUTPUT_COMMENTS"]:
                    comment = create_comment(
                        "(Coolant Off:" + coolantMode + ")\n", values["COMMENT_SYMBOL"]
                    )
                    gcode += linenumber(values) + comment
                gcode += linenumber(values) + "M9" + "\n"

    # do the post_amble
    if values["OUTPUT_COMMENTS"]:
        comment = create_comment("(begin postamble)\n", values["COMMENT_SYMBOL"])
        gcode += linenumber(values) + comment
    for line in values["TOOLRETURN"].splitlines(False):
        gcode += linenumber(values) + line + "\n"
    for line in values["SAFETYBLOCK"].splitlines(False):
        gcode += linenumber(values) + line + "\n"
    for line in values["POSTAMBLE"].splitlines(False):
        gcode += linenumber(values) + line + "\n"

    if FreeCAD.GuiUp and values["SHOW_EDITOR"]:
        final = gcode
        if len(gcode) > 100000:
            print("Skipping editor since output is greater than 100kb")
        else:
            dia = GCodeEditorDialog()
            dia.editor.setText(gcode)
            result = dia.exec_()
            if result:
                final = dia.editor.toPlainText()
    else:
        final = gcode

    print("done postprocessing.")

    if not filename == "-":
        gfile = pythonopen(filename, "w", newline=values["END_OF_LINE_CHARACTERS"])
        gfile.write(final)
        gfile.close()

    return final
