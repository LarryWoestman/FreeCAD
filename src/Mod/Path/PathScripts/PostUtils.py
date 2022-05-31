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
import re

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


def create_comment(comment_string, comment_symbol):
    """Create a comment from a string using the correct comment symbol."""
    if comment_symbol == "(":
        comment_string = "(" + comment_string + ")"
    else:
        comment_string = comment_symbol + comment_string
    return comment_string


def drill_translate(values, outstring, cmd, params):
    """Translate drill cycles."""
    axis_precision_string = "." + str(values["AXIS_PRECISION"]) + "f"
    feed_precision_string = "." + str(values["FEED_PRECISION"]) + "f"

    trBuff = ""

    if values["OUTPUT_COMMENTS"]:  # Comment the original command
        trBuff += (
            linenumber()
            + create_comment(format_outstring(outstring), values["COMMENT_SYMBOL"])
            + "\n"
        )

    # cycle conversion
    # currently only cycles in XY are provided (G17)
    # other plains ZX (G18) and  YZ (G19) are not dealt with : Z drilling only.
    drill_X = Units.Quantity(params["X"], FreeCAD.Units.Length)
    drill_Y = Units.Quantity(params["Y"], FreeCAD.Units.Length)
    drill_Z = Units.Quantity(params["Z"], FreeCAD.Units.Length)
    RETRACT_Z = Units.Quantity(params["R"], FreeCAD.Units.Length)
    # R less than Z is error
    if RETRACT_Z < drill_Z:
        trBuff += (
            linenumber()
            + create_comment("drill cycle error: R less than Z", values["COMMENT_SYMBOL"])
            + "\n"
        )
        return trBuff

    if values["MOTION_MODE"] == "G91":  # G91 relative movements
        drill_X += values["CURRENT_X"]
        drill_Y += values["CURRENT_Y"]
        drill_Z += values["CURRENT_Z"]
        RETRACT_Z += values["CURRENT_Z"]

    if values["DRILL_RETRACT_MODE"] == "G98" and values["CURRENT_Z"] >= RETRACT_Z:
        RETRACT_Z = values["CURRENT_Z"]

    # get the other parameters
    drill_feedrate = Units.Quantity(params["F"], FreeCAD.Units.Velocity)
    if cmd == "G83":
        drill_Step = Units.Quantity(params["Q"], FreeCAD.Units.Length)
        a_bit = (
            drill_Step * 0.05
        )  # NIST 3.5.16.4 G83 Cycle:  "current hole bottom, backed off a bit."
    elif cmd == "G82":
        drill_DwellTime = params["P"]

    # wrap this block to ensure machine's values["MOTION_MODE"] is restored in case of error
    try:
        if values["MOTION_MODE"] == "G91":
            trBuff += linenumber() + "G90\n"  # force absolute coordinates during cycles

        strG0_RETRACT_Z = (
            "G0 Z"
            + format(float(RETRACT_Z.getValueAs(values["UNIT_FORMAT"])), axis_precision_string)
            + "\n"
        )
        strF_Feedrate = (
            " F"
            + format(
                float(drill_feedrate.getValueAs(values["UNIT_SPEED_FORMAT"])), feed_precision_string
            )
            + "\n"
        )
        print(strF_Feedrate)

        # preliminary movement(s)
        if values["CURRENT_Z"] < RETRACT_Z:
            trBuff += linenumber() + strG0_RETRACT_Z
        trBuff += (
            linenumber()
            + "G0 X"
            + format(float(drill_X.getValueAs(values["UNIT_FORMAT"])), axis_precision_string)
            + " Y"
            + format(float(drill_Y.getValueAs(values["UNIT_FORMAT"])), axis_precision_string)
            + "\n"
        )
        if values["CURRENT_Z"] > RETRACT_Z:
            # NIST GCODE 3.5.16.1 Preliminary and In-Between Motion says G0 to RETRACT_Z
            # Here use G1 since retract height may be below surface !
            trBuff += (
                linenumber()
                + "G1 Z"
                + format(float(RETRACT_Z.getValueAs(values["UNIT_FORMAT"])), axis_precision_string)
                + strF_Feedrate
            )
        last_Stop_Z = RETRACT_Z

        # drill moves
        if cmd in ("G81", "G82"):
            trBuff += (
                linenumber()
                + "G1 Z"
                + format(float(drill_Z.getValueAs(values["UNIT_FORMAT"])), axis_precision_string)
                + strF_Feedrate
            )
            # pause where applicable
            if cmd == "G82":
                trBuff += linenumber() + "G4 P" + str(drill_DwellTime) + "\n"
            trBuff += linenumber() + strG0_RETRACT_Z
        else:  # 'G83'
            if params["Q"] != 0:
                while 1:
                    if last_Stop_Z != RETRACT_Z:
                        clearance_depth = (
                            last_Stop_Z + a_bit
                        )  # rapid move to just short of last drilling depth
                        trBuff += (
                            linenumber()
                            + "G0 Z"
                            + format(
                                float(clearance_depth.getValueAs(values["UNIT_FORMAT"])),
                                axis_precision_string,
                            )
                            + "\n"
                        )
                    next_Stop_Z = last_Stop_Z - drill_Step
                    if next_Stop_Z > drill_Z:
                        trBuff += (
                            linenumber()
                            + "G1 Z"
                            + format(
                                float(next_Stop_Z.getValueAs(values["UNIT_FORMAT"])),
                                axis_precision_string,
                            )
                            + strF_Feedrate
                        )
                        trBuff += linenumber() + strG0_RETRACT_Z
                        last_Stop_Z = next_Stop_Z
                    else:
                        trBuff += (
                            linenumber()
                            + "G1 Z"
                            + format(
                                float(drill_Z.getValueAs(values["UNIT_FORMAT"])),
                                axis_precision_string,
                            )
                            + strF_Feedrate
                        )
                        trBuff += linenumber() + strG0_RETRACT_Z
                        break

    except Exception:
        pass

    if values["MOTION_MODE"] == "G91":
        trBuff += linenumber() + "G91\n"  # Restore if changed

    return trBuff


def dump(obj):
    """For debug..."""
    for attr in dir(obj):
        print("obj.%s = %s" % (attr, getattr(obj, attr)))


def format_outstring(values, strTable):
    """Construct the line for the final output."""
    s = ""
    for w in strTable:
        s += w + values["COMMAND_SPACE"]
    s = s.strip()
    return s


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
    values["OUTPUT_HEADER"] = True
    values["OUTPUT_LINE_NUMBERS"] = False
    # if false duplicate axis values are suppressed if they are the same as the previous line.
    values["OUTPUT_DOUBLES"] = True
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


def linenumber(values, space=None):
    """Output the next line number if appropriate."""
    if values["OUTPUT_LINE_NUMBERS"]:
        if space is None:
            space = values["COMMAND_SPACE"]
        line_num = str(values["line_number"])
        values["line_number"] += values["LINE_INCREMENT"]
        return "N" + line_num + space
    return ""


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
        if values["OUTPUT_COMMENTS"]:
            comment = create_comment("compound: " + pathobj.Label, values["COMMENT_SYMBOL"])
            out += linenumber(values) + comment + "\n"
        for p in pathobj.Group:
            out += parse(values, p)
        return out
    else:  # parsing simple path

        # groups might contain non-path things like stock.
        if not hasattr(pathobj, "Path"):
            return out

        if values["OUTPUT_COMMENTS"]:
            comment = create_comment("Path: " + pathobj.Label, values["COMMENT_SYMBOL"])
            out += linenumber(values) + comment + "\n"

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
                        if c.Name not in values["RAPID_MOVES"]:
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
                    elif param in ["D", "L", "P"]:
                        outstring.append(param + str(int(c.Parameters[param])))
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
            # Memorizes the current position for calculating the related movements
            # and the withdrawal plan
            if command in values["MOTION_COMMANDS"]:
                if "X" in c.Parameters:
                    values["CURRENT_X"] = Units.Quantity(c.Parameters["X"], FreeCAD.Units.Length)
                if "Y" in c.Parameters:
                    values["CURRENT_Y"] = Units.Quantity(c.Parameters["Y"], FreeCAD.Units.Length)
                if "Z" in c.Parameters:
                    values["CURRENT_Z"] = Units.Quantity(c.Parameters["Z"], FreeCAD.Units.Length)

            if command in ("G98", "G99"):
                values["DRILL_RETRACT_MODE"] = command

            if command in ("G90", "G91"):
                values["MOTION_MODE"] = command

            if values["TRANSLATE_DRILL_CYCLES"]:
                if command in values["DRILL_CYCLES_TO_TRANSLATE"]:
                    out += drill_translate(values, outstring, command, c.Parameters)
                    # Erase the line we just translated
                    outstring = []

            if values["SPINDLE_WAIT"] > 0:
                if command in ("M3", "M03", "M4", "M04"):
                    out += linenumber(values) + format_outstring(outstring) + "\n"
                    out += (
                        linenumber(values)
                        + format_outstring(["G4", "P%s" % values["SPINDLE_WAIT"]])
                        + "\n"
                    )
                    outstring = []

            # Check for Tool Change:
            if command in ("M6", "M06"):
                if values["OUTPUT_COMMENTS"]:
                    comment = create_comment("Begin toolchange", values["COMMENT_SYMBOL"])
                    out += linenumber(values) + comment + "\n"
                if values["OUTPUT_TOOL_CHANGE"]:
                    if values["STOP_SPINDLE_FOR_TOOL_CHANGE"]:
                        # stop the spindle
                        out += linenumber(values) + "M5\n"
                    for line in values["TOOL_CHANGE"].splitlines(False):
                        out += linenumber(values) + line + "\n"
                else:
                    if values["OUTPUT_COMMENTS"]:
                        # convert the tool change to a comment
                        comment = create_comment(
                            format_outstring(outstring), values["COMMENT_SYMBOL"]
                        )
                        out += linenumber(values) + comment + "\n"
                        outstring = []

            if command == "message" and values["REMOVE_MESSAGES"]:
                if values["OUTPUT_COMMENTS"] is False:
                    out = []
                else:
                    outstring.pop(0)  # remove the command

            if command in values["SUPPRESS_COMMANDS"]:
                if values["OUTPUT_COMMENTS"]:
                    # convert the command to a comment
                    comment = create_comment(format_outstring(outstring), values["COMMENT_SYMBOL"])
                    out += linenumber(values) + comment + "\n"
                # remove the command
                outstring = []

            # prepend a line number and append a newline
            if len(outstring) >= 1:
                if values["OUTPUT_LINE_NUMBERS"]:
                    # In this case we don't want a space after the line number
                    # because the space is added in the join just below.
                    outstring.insert(0, (linenumber(values, "")))

                # append the line to the final output
                out += values["COMMAND_SPACE"].join(outstring)
                # Note: Do *not* strip `out`, since that forces the allocation
                # of a contiguous string & thus quadratic complexity.
                out += "\n"

            # add height offset
            if command in ("M6", "M06") and values["USE_TLO"]:
                out += linenumber(values) + "G43 H" + str(int(c.Parameters["T"])) + "\n"

            # Check for comments containing machine-specific commands
            # to pass literally to the controller
            if values["ENABLE_MACHINE_SPECIFIC_COMMANDS"]:
                m = re.match(r"^\(MC_RUN_COMMAND: ([^)]+)\)$", command)
                if m:
                    raw_command = m.group(1)
                    out += linenumber(values) + raw_command + "\n"

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

    print("PostProcessor:  " + values["POSTPROCESSOR_FILE_NAME"] + " postprocessing...")
    gcode = ""

    # write header
    if values["OUTPUT_HEADER"]:
        comment = create_comment("Exported by FreeCAD", values["COMMENT_SYMBOL"])
        gcode += linenumber(values) + comment + "\n"
        comment = create_comment(
            "Post Processor: " + values["POSTPROCESSOR_FILE_NAME"],
            values["COMMENT_SYMBOL"],
        )
        gcode += linenumber(values) + comment + "\n"
        if FreeCAD.ActiveDocument:
            cam_file = os.path.basename(FreeCAD.ActiveDocument.FileName)
        else:
            cam_file = "<None>"
        comment = create_comment("Cam File: " + cam_file, values["COMMENT_SYMBOL"])
        gcode += linenumber(values) + comment + "\n"
        comment = create_comment(
            "Output Time:" + str(datetime.datetime.now()), values["COMMENT_SYMBOL"]
        )
        gcode += linenumber(values) + comment + "\n"

    # Check canned cycles for drilling
    if values["TRANSLATE_DRILL_CYCLES"]:
        if len(values["SUPPRESS_COMMANDS"]) == 0:
            values["SUPPRESS_COMMANDS"] = ["G99", "G98", "G80"]
        else:
            values["SUPPRESS_COMMANDS"] += ["G99", "G98", "G80"]

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
                        "T{}={}".format(item.ToolNumber, item.Name), values["COMMENT_SYMBOL"]
                    )
                    gcode += linenumber(values) + comment + "\n"
        comment = create_comment("begin preamble", values["COMMENT_SYMBOL"])
        gcode += linenumber(values) + comment + "\n"
    for line in values["PREAMBLE"].splitlines(False):
        gcode += linenumber(values) + line + "\n"
    # verify if PREAMBLE have changed MOTION_MODE or UNITS
    if "G90" in values["PREAMBLE"]:
        values["MOTION_MODE"] = "G90"
    elif "G91" in values["PREAMBLE"]:
        values["MOTION_MODE"] = "G91"
    else:
        gcode += linenumber() + values["MOTION_MODE"] + "\n"
    if "G21" in values["PREAMBLE"]:
        values["UNITS"] = "G21"
        values["UNIT_FORMAT"] = "mm"
        values["UNIT_SPEED_FORMAT"] = "mm/min"
    elif "G20" in values["PREAMBLE"]:
        values["UNITS"] = "G20"
        values["UNIT_FORMAT"] = "in"
        values["UNIT_SPEED_FORMAT"] = "in/min"
    else:
        gcode += linenumber(values) + values["UNITS"] + "\n"

    for obj in objectslist:

        # Debug...
        # print("\n" + "*"*70)
        # dump(obj)
        # print("*"*70 + "\n")

        # Skip inactive operations
        if hasattr(obj, "Active"):
            if not obj.Active:
                continue
        if hasattr(obj, "Base") and hasattr(obj.Base, "Active"):
            if not obj.Base.Active:
                continue

        # do the pre_op
        if values["OUTPUT_BCNC"]:
            comment = create_comment("Block-name: " + obj.Label, values["COMMENT_SYMBOL"])
            gcode += linenumber(values) + comment + "\n"
            comment = create_comment("Block-expand: 0", values["COMMENT_SYMBOL"])
            gcode += linenumber(values) + comment + "\n"
            comment = create_comment("Block-enable: 1", values["COMMENT_SYMBOL"])
            gcode += linenumber(values) + comment + "\n"
        if values["OUTPUT_COMMENTS"]:
            if values["SHOW_OPERATION_LABELS"]:
                comment = create_comment(
                    "begin operation: %s" % obj.Label, values["COMMENT_SYMBOL"]
                )
            else:
                comment = create_comment("begin operation", values["COMMENT_SYMBOL"])
            gcode += linenumber(values) + comment + "\n"
            if values["SHOW_MACHINE_UNITS"]:
                comment = create_comment(
                    "machine units: %s" % values["UNIT_SPEED_FORMAT"], values["COMMENT_SYMBOL"]
                )
                gcode += linenumber(values) + comment + "\n"
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
                    comment = create_comment("Coolant On:" + coolantMode, values["COMMENT_SYMBOL"])
                    gcode += linenumber(values) + comment + "\n"
            if coolantMode == "Flood":
                gcode += linenumber(values) + "M8" + "\n"
            if coolantMode == "Mist":
                gcode += linenumber(values) + "M7" + "\n"

        # process the operation gcode
        gcode += parse(values, obj)

        # do the post_op
        if values["OUTPUT_COMMENTS"]:
            comment = create_comment(
                "%s operation: %s" % (values["FINISH_LABEL"], obj.Label),
                values["COMMENT_SYMBOL"],
            )
            gcode += linenumber(values) + comment + "\n"
        for line in values["POST_OPERATION"].splitlines(False):
            gcode += linenumber(values) + line + "\n"

        # turn coolant off if required
        if values["ENABLE_COOLANT"]:
            if not coolantMode == "None":
                if values["OUTPUT_COMMENTS"]:
                    comment = create_comment("Coolant Off:" + coolantMode, values["COMMENT_SYMBOL"])
                    gcode += linenumber(values) + comment + "\n"
                gcode += linenumber(values) + "M9" + "\n"

    if values["RETURN_TO"]:
        gcode += linenumber() + "G0 X%s Y%s\n" % tuple(values["RETURN_TO"])

    # do the post_amble
    if values["OUTPUT_BCNC"]:
        comment = create_comment("Block-name: post_amble", values["COMMENT_SYMBOL"])
        gcode += linenumber(values) + comment + "\n"
        comment = create_comment("Block-expand: 0", values["COMMENT_SYMBOL"])
        gcode += linenumber(values) + comment + "\n"
        comment = create_comment("Block-enable: 1", values["COMMENT_SYMBOL"])
        gcode += linenumber(values) + comment + "\n"
    if values["OUTPUT_COMMENTS"]:
        comment = create_comment("begin postamble", values["COMMENT_SYMBOL"])
        gcode += linenumber(values) + comment + "\n"
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
