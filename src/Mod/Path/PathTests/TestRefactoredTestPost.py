# -*- coding: utf-8 -*-
# ***************************************************************************
# *   Copyright (c) 2022 sliptonic <shopinthewoods@gmail.com>               *
# *   Copyright (c) 2022 Larry Woestman <LarryWoestman2@gmail.com>          *
# *                                                                         *
# *   This program is free software; you can redistribute it and/or modify  *
# *   it under the terms of the GNU Lesser General Public License (LGPL)    *
# *   as published by the Free Software Foundation; either version 2 of     *
# *   the License, or (at your option) any later version.                   *
# *   for detail see the LICENCE text file.                                 *
# *                                                                         *
# *   This program is distributed in the hope that it will be useful,       *
# *   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
# *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
# *   GNU Library General Public License for more details.                  *
# *                                                                         *
# *   You should have received a copy of the GNU Library General Public     *
# *   License along with this program; if not, write to the Free Software   *
# *   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  *
# *   USA                                                                   *
# *                                                                         *
# ***************************************************************************

import os
from typing import Any, Dict, List

import FreeCAD

import Path

from Path import Log
from Path.Tool import Bit
from Path.Tool import Controller
from Path.Post.scripts import refactored_test_post as postprocessor
from PathTests import PathTestUtils

from PySide.QtCore import QT_TRANSLATE_NOOP  # type: ignore

Log.setLevel(Log.Level.DEBUG, Log.thisModule())
Log.trackModule(Log.thisModule())


class TestRefactoredTestPost(PathTestUtils.PathTestBase):
    """Test the refactored_test_post.py postprocessor."""

    @classmethod
    def setUpClass(cls) -> None:
        """setUpClass()...

        This method is called upon instantiation of this test class.  Add code
        and objects here that are needed for the duration of the test() methods
        in this class.  In other words, set up the 'global' test environment
        here; use the `setUp()` method to set up a 'local' test environment.
        This method does not have access to the class `self` reference, but it
        is able to call static methods within this same class.
        """
        # Open existing FreeCAD document with test geometry
        FreeCAD.newDocument("Unnamed")

    @classmethod
    def tearDownClass(cls) -> None:
        """tearDownClass()...

        This method is called prior to destruction of this test class.  Add
        code and objects here that cleanup the test environment after the
        test() methods in this class have been executed.  This method does
        not have access to the class `self` reference.  This method is able
        to call static methods within this same class.
        """
        # Close geometry document without saving
        FreeCAD.closeDocument(FreeCAD.ActiveDocument.Name)

    # Setup and tear down methods called before and after each unit test

    def setUp(self) -> None:
        """setUp()...

        This method is called prior to each `test()` method.  Add code and
        objects here that are needed for multiple `test()` methods.
        """
        self.maxDiff = None
        self.doc = FreeCAD.ActiveDocument
        self.con = FreeCAD.Console
        self.docobj = FreeCAD.ActiveDocument.addObject("Path::Feature", "testpath")
        # Re-initialize all of the values before doing a test.
        postprocessor.UNITS = "G21"
        postprocessor.init_values(postprocessor.global_values)

    def tearDown(self) -> None:
        """tearDown()...

        This method is called after each test() method. Add cleanup instructions here.
        Such cleanup instructions will likely undo those in the setUp() method.
        """
        FreeCAD.ActiveDocument.removeObject("testpath")

    def single_compare(
        self, path: List[Path.Command], expected: str, args: str, debug: bool = False
    ) -> None:
        """Perform a test with a single comparison."""
        nl: str = "\n"

        self.docobj.Path = Path.Path(path)
        postables = [self.docobj]
        gcode: str = postprocessor.export(postables, "gcode.tmp", args)
        if debug:
            print(f"--------{nl}{gcode}--------{nl}")
            print(f"--------{nl}{gcode}--------{nl}")
        self.assertEqual(gcode, expected)

    def compare_third_line(
        self, path_string: str, expected: str, args: str, debug: bool = False
    ) -> None:
        """Perform a test with a single comparison to the third line of the output."""
        nl: str = "\n"

        if path_string:
            self.docobj.Path = Path.Path([Path.Command(path_string)])
        else:
            self.docobj.Path = Path.Path([])
        postables = [self.docobj]
        gcode: str = postprocessor.export(postables, "gcode.tmp", args)
        if debug:
            print(f"--------{nl}{gcode}--------{nl}")
            print(f"--------{nl}{gcode}--------{nl}")
        self.assertEqual(gcode.splitlines()[2], expected)

    #############################################################################
    #
    # The tests are organized into groups:
    #
    #   00000 - 00099  tests that don't fit any other category
    #   00100 - 09999  tests for all of the various arguments/options
    #   10000 - 19999  tests for the various G codes at 10000 + 10 * g_code_value
    #   20000 - 29999  tests for the various M codes at 20000 + 10 * m_code_value
    #
    #############################################################################

    def test00100(self) -> None:
        """Test axis modal.

        Suppress the axis coordinate if the same as previous
        """
        args: str
        gcode: str

        c = Path.Command("G0 X10 Y20 Z30")
        c1 = Path.Command("G0 X10 Y30 Z30")

        self.docobj.Path = Path.Path([c, c1])
        postables = [self.docobj]

        args = "--axis-modal"
        gcode = postprocessor.export(postables, "gcode.tmp", args)
        # print("--------\n" + gcode + "--------\n")
        self.assertEqual(gcode.splitlines()[3], "G0 Y30.000")

        args = "--no-axis-modal"
        gcode = postprocessor.export(postables, "gcode.tmp", args)
        # print("--------\n" + gcode + "--------\n")
        self.assertEqual(gcode.splitlines()[3], "G0 X10.000 Y30.000 Z30.000")

    #############################################################################

    def test00110(self) -> None:
        """Test axis-precision."""
        self.compare_third_line(
            "G0 X10 Y20 Z30", "G0 X10.00 Y20.00 Z30.00", "--axis-precision=2"
        )

    #############################################################################

    def test00120(self) -> None:
        """Test bcnc."""
        self.single_compare(
            [],
            """G90
G21
(Block-name: testpath)
(Block-expand: 0)
(Block-enable: 1)
(Block-name: post_amble)
(Block-expand: 0)
(Block-enable: 1)
""",
            "--bcnc",
        )
        self.single_compare(
            [],
            """G90
G21
""",
            "--no-bcnc",
        )

    #############################################################################

    def test00125(self) -> None:
        """Test chipbreaking amount."""
        path = [
            Path.Command("G0 X1 Y2"),
            Path.Command("G0 Z8"),
            Path.Command("G90"),
            Path.Command("G99"),
            Path.Command("G73 X1 Y2 Z0 F123 Q1.5 R5"),
            Path.Command("G80"),
            Path.Command("G90"),
        ]
        # check the default chipbreaking amount
        self.single_compare(
            path,
            """G90
G21
G0 X1.000 Y2.000
G0 Z8.000
G90
G0 X1.000 Y2.000
G1 Z5.000 F7380.000
G1 Z3.500 F7380.000
G0 Z3.750
G0 Z3.575
G1 Z2.000 F7380.000
G0 Z2.250
G0 Z2.075
G1 Z0.500 F7380.000
G0 Z0.750
G0 Z0.575
G1 Z0.000 F7380.000
G0 Z5.000
G90
""",
            "--translate_drill",
        )
        # check for a metric chipbreaking amount
        self.single_compare(
            path,
            """G90
G21
G0 X1.000 Y2.000
G0 Z8.000
G90
G0 X1.000 Y2.000
G1 Z5.000 F7380.000
G1 Z3.500 F7380.000
G0 Z4.735
G0 Z3.575
G1 Z2.000 F7380.000
G0 Z3.235
G0 Z2.075
G1 Z0.500 F7380.000
G0 Z1.735
G0 Z0.575
G1 Z0.000 F7380.000
G0 Z5.000
G90
""",
            "--translate_drill --chipbreaking_amount='1.23456 mm'",
        )
        # check for an inch/imperial chipbreaking amount
        path = [
            Path.Command("G0 X25.4 Y50.8"),
            Path.Command("G0 Z203.2"),
            Path.Command("G90"),
            Path.Command("G99"),
            Path.Command("G73 X25.4 Y50.8 Z0 F123 Q38.1 R127"),
            Path.Command("G80"),
            Path.Command("G90"),
        ]
        self.single_compare(
            path,
            """G90
G20
G0 X1.0000 Y2.0000
G0 Z8.0000
G90
G0 X1.0000 Y2.0000
G1 Z5.0000 F290.5512
G1 Z3.5000 F290.5512
G0 Z3.7500
G0 Z3.5750
G1 Z2.0000 F290.5512
G0 Z2.2500
G0 Z2.0750
G1 Z0.5000 F290.5512
G0 Z0.7500
G0 Z0.5750
G1 Z0.0000 F290.5512
G0 Z5.0000
G90
""",
            "--translate_drill --chipbreaking_amount='0.25 in' --inches",
        )

    #############################################################################

    def test00126(self) -> None:
        """Test command space."""
        self.compare_third_line("G0 X10 Y20 Z30", "G0 X10.000 Y20.000 Z30.000", "")
        self.compare_third_line(
            "G0 X10 Y20 Z30", "G0X10.000Y20.000Z30.000", "--command_space=''"
        )
        self.compare_third_line(
            "G0 X10 Y20 Z30", "G0_X10.000_Y20.000_Z30.000", "--command_space='_'"
        )
        path = [Path.Command("(comment with spaces)")]
        self.single_compare(
            path,
            """(Begin preamble)
G90
G21
(Begin operation)
(comment with spaces)
(Finish operation: testpath)
(Begin postamble)
""",
            "--command_space=' ' --comments",
        )
        self.single_compare(
            path,
            """(Begin preamble)
G90
G21
(Begin operation)
(comment with spaces)
(Finish operation: testpath)
(Begin postamble)
""",
            "--command_space='' --comments",
        )

    #############################################################################

    def test00127(self) -> None:
        """Test comment symbol."""
        path = [Path.Command("(comment with spaces)")]
        self.single_compare(
            path,
            """(Begin preamble)
G90
G21
(Begin operation)
(comment with spaces)
(Finish operation: testpath)
(Begin postamble)
""",
            "--comments",
        )
        self.single_compare(
            path,
            """;Begin preamble
G90
G21
;Begin operation
;comment with spaces
;Finish operation: testpath
;Begin postamble
""",
            "--comment_symbol=';' --comments",
        )
        self.single_compare(
            path,
            """!Begin preamble
G90
G21
!Begin operation
!comment with spaces
!Finish operation: testpath
!Begin postamble
""",
            "--comment_symbol='!' --comments",
        )

    #############################################################################

    def test00130(self) -> None:
        """Test comments."""
        args: str
        expected: str
        gcode: str

        c = Path.Command("(comment)")
        self.docobj.Path = Path.Path([c])
        postables = [self.docobj]
        args = "--comments"
        gcode = postprocessor.export(postables, "gcode.tmp", args)
        # print("--------\n" + gcode + "--------\n")
        self.assertEqual(gcode.splitlines()[4], "(comment)")
        expected = """G90
G21
"""
        args = "--no-comments"
        gcode = postprocessor.export(postables, "gcode.tmp", args)
        # print("--------\n" + gcode + "--------\n")
        self.assertEqual(gcode, expected)

    #############################################################################

    def test00135(self) -> None:
        """Test enabling and disabling coolant."""
        args: str
        expected: str
        gcode: str

        c = Path.Command("G0 X10 Y20 Z30")
        self.docobj.Path = Path.Path([c])

        # Test Flood coolant enabled
        self.docobj.addProperty(
            "App::PropertyEnumeration",
            "CoolantMode",
            "Path",
            QT_TRANSLATE_NOOP("App::Property", "Coolant option for this operation"),
        )
        self.docobj.CoolantMode = ["None", "Flood", "Mist"]
        self.docobj.CoolantMode = "Flood"
        postables = [self.docobj]
        expected = """(Begin preamble)
G90
G21
(Begin operation)
(Coolant On: Flood)
M8
G0 X10.000 Y20.000 Z30.000
(Finish operation: testpath)
(Coolant Off: Flood)
M9
(Begin postamble)
"""
        args = "--enable_coolant --comments"
        gcode = postprocessor.export(postables, "gcode.tmp", args)
        # print("--------\n" + gcode + "--------\n")
        self.docobj.removeProperty("CoolantMode")
        self.assertEqual(gcode, expected)

        # Test Mist coolant enabled
        self.docobj.addProperty(
            "App::PropertyEnumeration",
            "CoolantMode",
            "Path",
            QT_TRANSLATE_NOOP("App::Property", "Coolant option for this operation"),
        )
        self.docobj.CoolantMode = ["None", "Flood", "Mist"]
        self.docobj.CoolantMode = "Mist"
        postables = [self.docobj]
        expected = """(Begin preamble)
G90
G21
(Begin operation)
(Coolant On: Mist)
M7
G0 X10.000 Y20.000 Z30.000
(Finish operation: testpath)
(Coolant Off: Mist)
M9
(Begin postamble)
"""
        args = "--enable_coolant --comments"
        gcode = postprocessor.export(postables, "gcode.tmp", args)
        # print("--------\n" + gcode + "--------\n")
        self.docobj.removeProperty("CoolantMode")
        self.assertEqual(gcode, expected)

        # Test None coolant enabled with CoolantMode property
        self.docobj.addProperty(
            "App::PropertyEnumeration",
            "CoolantMode",
            "Path",
            QT_TRANSLATE_NOOP("App::Property", "Coolant option for this operation"),
        )
        self.docobj.CoolantMode = ["None", "Flood", "Mist"]
        self.docobj.CoolantMode = "None"
        postables = [self.docobj]
        expected = """(Begin preamble)
G90
G21
(Begin operation)
G0 X10.000 Y20.000 Z30.000
(Finish operation: testpath)
(Begin postamble)
"""
        args = "--enable_coolant --comments"
        gcode = postprocessor.export(postables, "gcode.tmp", args)
        # print("--------\n" + gcode + "--------\n")
        self.docobj.removeProperty("CoolantMode")
        self.assertEqual(gcode, expected)

        # Test coolant enabled without a CoolantMode property
        postables = [self.docobj]
        expected = """(Begin preamble)
G90
G21
(Begin operation)
G0 X10.000 Y20.000 Z30.000
(Finish operation: testpath)
(Begin postamble)
"""
        args = "--enable_coolant --comments"
        gcode = postprocessor.export(postables, "gcode.tmp", args)
        # print("--------\n" + gcode + "--------\n")
        self.assertEqual(gcode, expected)

        # Test Flood coolant disabled
        self.docobj.addProperty(
            "App::PropertyEnumeration",
            "CoolantMode",
            "Path",
            QT_TRANSLATE_NOOP("App::Property", "Coolant option for this operation"),
        )
        self.docobj.CoolantMode = ["None", "Flood", "Mist"]
        self.docobj.CoolantMode = "Flood"
        postables = [self.docobj]
        expected = """(Begin preamble)
G90
G21
(Begin operation)
G0 X10.000 Y20.000 Z30.000
(Finish operation: testpath)
(Begin postamble)
"""
        args = "--disable_coolant --comments"
        gcode = postprocessor.export(postables, "gcode.tmp", args)
        # print("--------\n" + gcode + "--------\n")
        self.docobj.removeProperty("CoolantMode")
        self.assertEqual(gcode, expected)

        # Test Mist coolant disabled
        self.docobj.addProperty(
            "App::PropertyEnumeration",
            "CoolantMode",
            "Path",
            QT_TRANSLATE_NOOP("App::Property", "Coolant option for this operation"),
        )
        self.docobj.CoolantMode = ["None", "Flood", "Mist"]
        self.docobj.CoolantMode = "Mist"
        postables = [self.docobj]
        expected = """(Begin preamble)
G90
G21
(Begin operation)
G0 X10.000 Y20.000 Z30.000
(Finish operation: testpath)
(Begin postamble)
"""
        args = "--disable_coolant --comments"
        gcode = postprocessor.export(postables, "gcode.tmp", args)
        # print("--------\n" + gcode + "--------\n")
        self.docobj.removeProperty("CoolantMode")
        self.assertEqual(gcode, expected)

        # Test None coolant disabled with CoolantMode property
        self.docobj.addProperty(
            "App::PropertyEnumeration",
            "CoolantMode",
            "Path",
            QT_TRANSLATE_NOOP("App::Property", "Coolant option for this operation"),
        )
        self.docobj.CoolantMode = ["None", "Flood", "Mist"]
        self.docobj.CoolantMode = "None"
        postables = [self.docobj]
        expected = """(Begin preamble)
G90
G21
(Begin operation)
G0 X10.000 Y20.000 Z30.000
(Finish operation: testpath)
(Begin postamble)
"""
        args = "--disable_coolant --comments"
        gcode = postprocessor.export(postables, "gcode.tmp", args)
        # print("--------\n" + gcode + "--------\n")
        self.docobj.removeProperty("CoolantMode")
        self.assertEqual(gcode, expected)

        # Test coolant disabled without a CoolantMode property
        postables = [self.docobj]
        expected = """(Begin preamble)
G90
G21
(Begin operation)
G0 X10.000 Y20.000 Z30.000
(Finish operation: testpath)
(Begin postamble)
"""
        args = "--disable_coolant --comments"
        gcode = postprocessor.export(postables, "gcode.tmp", args)
        # print("--------\n" + gcode + "--------\n")
        self.assertEqual(gcode, expected)

        # Test Flood coolant configured but no coolant argument (default)
        self.docobj.addProperty(
            "App::PropertyEnumeration",
            "CoolantMode",
            "Path",
            QT_TRANSLATE_NOOP("App::Property", "Coolant option for this operation"),
        )
        self.docobj.CoolantMode = ["None", "Flood", "Mist"]
        self.docobj.CoolantMode = "Flood"
        postables = [self.docobj]
        expected = """(Begin preamble)
G90
G21
(Begin operation)
G0 X10.000 Y20.000 Z30.000
(Finish operation: testpath)
(Begin postamble)
"""
        args = "--comments"
        gcode = postprocessor.export(postables, "gcode.tmp", args)
        # print("--------\n" + gcode + "--------\n")
        self.docobj.removeProperty("CoolantMode")
        self.assertEqual(gcode, expected)

    #############################################################################

    def test00137(self) -> None:
        """Test enabling/disabling machine specific commands."""
        path = [Path.Command("(MC_RUN_COMMAND: blah)")]
        # test with machine specific commands enabled
        self.single_compare(
            path,
            """(Begin preamble)
G90
G21
(Begin operation)
(MC_RUN_COMMAND: blah)
blah
(Finish operation: testpath)
(Begin postamble)
""",
            "--enable_machine_specific_commands --comments",
        )
        # test with machine specific commands disabled
        self.single_compare(
            path,
            """(Begin preamble)
G90
G21
(Begin operation)
(MC_RUN_COMMAND: blah)
(Finish operation: testpath)
(Begin postamble)
""",
            "--disable_machine_specific_commands --comments",
        )
        # test with machine specific commands default
        self.single_compare(
            path,
            """(Begin preamble)
G90
G21
(Begin operation)
(MC_RUN_COMMAND: blah)
(Finish operation: testpath)
(Begin postamble)
""",
            "--comments",
        )
        # test with odd characters and spaces in the machine specific command
        path = [Path.Command("(MC_RUN_COMMAND: These are odd characters:!@#$%^&*?/)")]
        self.single_compare(
            path,
            """(Begin preamble)
G90
G21
(Begin operation)
(MC_RUN_COMMAND: These are odd characters:!@#$%^&*?/)
These are odd characters:!@#$%^&*?/
(Finish operation: testpath)
(Begin postamble)
""",
            "--enable_machine_specific_commands --comments",
        )

    #############################################################################

    def test00138(self) -> None:
        """Test end of line characters."""
        args: str
        expected: bytes
        gcode_bytes: bytes

        self.docobj.Path = Path.Path([])
        postables = [self.docobj]

        # Test with whatever the system running the test happens to use
        expected = b"G90" + os.linesep.encode() + b"G21" + os.linesep.encode()
        args = ""
        _ = postprocessor.export(postables, "gcode.tmp", args)
        with open("gcode.tmp", mode="rb") as bfile:
            gcode_bytes = bfile.read()
        self.assertEqual(gcode_bytes, expected)

        # Test with a new line
        expected = b"G90\nG21\n"
        args = "--end_of_line_characters='\n'"
        _ = postprocessor.export(postables, "gcode.tmp", args)
        with open("gcode.tmp", mode="rb") as bfile:
            gcode_bytes = bfile.read()
        self.assertEqual(gcode_bytes, expected)

        # Test with a carriage return followed by a new line
        expected = b"G90\r\nG21\r\n"
        args = "--end_of_line_characters='\r\n'"
        _ = postprocessor.export(postables, "gcode.tmp", args)
        with open("gcode.tmp", mode="rb") as bfile:
            gcode_bytes = bfile.read()
        self.assertEqual(gcode_bytes, expected)

        # Test with a carriage return
        expected = b"G90\rG21\r"
        args = "--end_of_line_characters='\r'"
        _ = postprocessor.export(postables, "gcode.tmp", args)
        with open("gcode.tmp", mode="rb") as bfile:
            gcode_bytes = bfile.read()
        self.assertEqual(gcode_bytes, expected)

    #############################################################################

    def test00140(self) -> None:
        """Test feed-precision."""
        args: str
        gcode: str

        c = Path.Command("G1 X10 Y20 Z30 F123.123456")

        self.docobj.Path = Path.Path([c])
        postables = [self.docobj]

        args = ""
        gcode = postprocessor.export(postables, "gcode.tmp", args)
        # print("--------\n" + gcode + "--------\n")
        # Note:  The "internal" F speed is in mm/s,
        #        while the output F speed is in mm/min.
        self.assertEqual(gcode.splitlines()[2], "G1 X10.000 Y20.000 Z30.000 F7387.407")

        args = "--feed-precision=2"
        gcode = postprocessor.export(postables, "gcode.tmp", args)
        # print("--------\n" + gcode + "--------\n")
        # Note:  The "internal" F speed is in mm/s,
        #        while the output F speed is in mm/min.
        self.assertEqual(gcode.splitlines()[2], "G1 X10.000 Y20.000 Z30.000 F7387.41")

    #############################################################################

    def test00145(self) -> None:
        """Test the finish label argument."""
        # test the default finish label
        self.single_compare(
            [],
            """(Begin preamble)
G90
G21
(Begin operation)
(Finish operation: testpath)
(Begin postamble)
""",
            "--comments",
        )

        # test a changed finish label
        self.single_compare(
            [],
            """(Begin preamble)
G90
G21
(Begin operation)
(End operation: testpath)
(Begin postamble)
""",
            "--finish_label='End' --comments",
        )

    #############################################################################

    def test00150(self) -> None:
        """Test output with an empty path.

    def test00138(self) -> None:
        """Test end of line characters."""
        args: str
        expected: bytes
        gcode_bytes: bytes

        self.docobj.Path = Path.Path([])
        postables = [self.docobj]

        # Test with whatever the system running the test happens to use
        expected = b"G90" + os.linesep.encode() + b"G21" + os.linesep.encode()
        args = ""
        _ = postprocessor.export(postables, "gcode.tmp", args)
        with open("gcode.tmp", mode="rb") as bfile:
            gcode_bytes = bfile.read()
        self.assertEqual(gcode_bytes, expected)

        # Test with a new line
        expected = b"G90\nG21\n"
        args = "--end_of_line_characters='\n'"
        _ = postprocessor.export(postables, "gcode.tmp", args)
        with open("gcode.tmp", mode="rb") as bfile:
            gcode_bytes = bfile.read()
        self.assertEqual(gcode_bytes, expected)

        # Test with a carriage return followed by a new line
        expected = b"G90\r\nG21\r\n"
        args = "--end_of_line_characters='\r\n'"
        _ = postprocessor.export(postables, "gcode.tmp", args)
        with open("gcode.tmp", mode="rb") as bfile:
            gcode_bytes = bfile.read()
        self.assertEqual(gcode_bytes, expected)

        # Test with a carriage return
        expected = b"G90\rG21\r"
        args = "--end_of_line_characters='\r'"
        _ = postprocessor.export(postables, "gcode.tmp", args)
        with open("gcode.tmp", mode="rb") as bfile:
            gcode_bytes = bfile.read()
        self.assertEqual(gcode_bytes, expected)

    #############################################################################

    def test00140(self) -> None:
        """Test feed-precision."""
        args: str
        gcode: str

        c = Path.Command("G1 X10 Y20 Z30 F123.123456")

        self.docobj.Path = Path.Path([c])
        postables = [self.docobj]

        args = ""
        gcode = postprocessor.export(postables, "gcode.tmp", args)
        # print("--------\n" + gcode + "--------\n")
        # Note:  The "internal" F speed is in mm/s,
        #        while the output F speed is in mm/min.
        self.assertEqual(gcode.splitlines()[2], "G1 X10.000 Y20.000 Z30.000 F7387.407")

        args = "--feed-precision=2"
        gcode = postprocessor.export(postables, "gcode.tmp", args)
        # print("--------\n" + gcode + "--------\n")
        # Note:  The "internal" F speed is in mm/s,
        #        while the output F speed is in mm/min.
        self.assertEqual(gcode.splitlines()[2], "G1 X10.000 Y20.000 Z30.000 F7387.41")

    #############################################################################

    def test00145(self) -> None:
        """Test the finish label argument."""
        # test the default finish label
        self.single_compare(
            [],
            """(Begin preamble)
G90
G21
(Begin operation)
(Finish operation: testpath)
(Begin postamble)
""",
            "--comments",
        )

        # test a changed finish label
        self.single_compare(
            [],
            """(Begin preamble)
G90
G21
(Begin operation)
(End operation: testpath)
(Begin postamble)
""",
            "--finish_label='End' --comments",
        )

    #############################################################################

    def test00150(self) -> None:
        """Test output with an empty path.

        Also tests the interactions between --comments and --header.
        """
        args: str
        expected: str
        gcode: str

        self.docobj.Path = Path.Path([])
        postables = [self.docobj]

        # Test generating with comments and header.
        # The header contains a time stamp that messes up unit testing.
        # Only test the length of the line that contains the time.
        args = "--comments --header"
        gcode = postprocessor.export(postables, "gcode.tmp", args)
        # print("--------\n" + gcode + "--------\n")
        self.assertEqual(gcode.splitlines()[0], "(Exported by FreeCAD)")
        self.assertEqual(
            gcode.splitlines()[1],
            "(Post Processor: Path.Post.scripts.refactored_test_post)",
        )
        self.assertEqual(gcode.splitlines()[2], "(Cam File: )")
        self.assertIn("(Output Time: ", gcode.splitlines()[3])
        self.assertTrue(len(gcode.splitlines()[3]) == 41)
        self.assertEqual(gcode.splitlines()[4], "(Begin preamble)")
        self.assertEqual(gcode.splitlines()[5], "G90")
        self.assertEqual(gcode.splitlines()[6], "G21")
        self.assertEqual(gcode.splitlines()[7], "(Begin operation)")
        self.assertEqual(gcode.splitlines()[8], "(Finish operation: testpath)")
        self.assertEqual(gcode.splitlines()[9], "(Begin postamble)")

        # Test with comments without header.
        expected = """(Begin preamble)
G90
G21
(Begin operation)
(Finish operation: testpath)
(Begin postamble)
"""
        args = "--comments --no-header"
        gcode = postprocessor.export(postables, "gcode.tmp", args)
        # print("--------\n" + gcode + "--------\n")
        self.assertEqual(gcode, expected)

        # Test without comments with header.
        args = "--no-comments --header"
        gcode = postprocessor.export(postables, "gcode.tmp", args)
        # print("--------\n" + gcode + "--------\n")
        self.assertEqual(gcode.splitlines()[0], "(Exported by FreeCAD)")
        self.assertEqual(
            gcode.splitlines()[1],
            "(Post Processor: Path.Post.scripts.refactored_test_post)",
        )
        self.assertEqual(gcode.splitlines()[2], "(Cam File: )")
        self.assertIn("(Output Time: ", gcode.splitlines()[3])
        self.assertTrue(len(gcode.splitlines()[3]) == 41)
        self.assertEqual(gcode.splitlines()[4], "G90")
        self.assertEqual(gcode.splitlines()[5], "G21")

        # Test without comments or header.
        expected = """G90
G21
"""
        args = "--no-comments --no-header"
        gcode = postprocessor.export(postables, "gcode.tmp", args)
        # print("--------\n" + gcode + "--------\n")
        self.assertEqual(gcode, expected)

    #############################################################################

    def test00160(self) -> None:
        """Test Line Numbers."""
        self.compare_third_line(
            "G0 X10 Y20 Z30", "N120 G0 X10.000 Y20.000 Z30.000", "--line-numbers"
        )
        self.compare_third_line(
            "G0 X10 Y20 Z30", "G0 X10.000 Y20.000 Z30.000", "--no-line-numbers"
        )

    #############################################################################

    def test00165(self) -> None:
        """Test line number increment."""
        path = [
            Path.Command("G0 X1 Y2"),
            Path.Command("G0 Z8"),
        ]
        # check the default line number increment
        self.single_compare(
            path,
            """N100 G90
N110 G21
N120 G0 X1.000 Y2.000
N130 G0 Z8.000
""",
            "--line-numbers",
        )

        # check a non-default line number increment
        self.single_compare(
            path,
            """N140 G90
N143 G21
N146 G0 X1.000 Y2.000
N149 G0 Z8.000
""",
            "--line-numbers --line_number_increment=3",
        )

        # check a non-default starting line number
        self.single_compare(
            path,
            """N123 G90
N126 G21
N129 G0 X1.000 Y2.000
N132 G0 Z8.000
""",
            "--line-numbers --line_number_increment=3 --line_number_start=123",
        )

    #############################################################################

#     def test00166(self) -> None:
#         """Test listing tools in preamble."""

#         # test the default behavior for listing tools in the preamble
#         args: str
#         attrs: Dict[str, Any]
#         expected: str
#         gcode: str

#         path = [
#             Path.Command("M6 T2"),
#             Path.Command("M3 S3000"),
#         ]
#         self.docobj.Path = Path.Path(path)
#         default_tool_controller = Controller.Create()
#         attrs = {
#             "shape": None,
#             "name": "T2",
#             "parameter": {"Diameter": 1.75},
#             "attribute": [],
#         }
#         tool2 = Bit.Factory.CreateFromAttrs(attrs, "T2")
#         tool2_controller = Controller.Create(
#             name="TC2", tool=tool2, toolNumber=2
#         )
#         postables = [default_tool_controller, tool2_controller, self.docobj]
#         expected = """(Begin preamble)
# G90
# G21
# (Begin operation)
# (Begin toolchange)
# M6 T2
# M3 S3000
# (Finish operation: testpath)
# (Begin postamble)
# """
#         args = "--comments --tool_change --list_tools_in_preamble"
#         gcode = postprocessor.export(postables, "gcode.tmp", args)
#         print("--------\n" + gcode + "--------\n")
#         self.docobj.removeProperty("tool2")
#         self.assertEqual(gcode, expected)

    #############################################################################

    def test00170(self) -> None:
        """Test metric and inches."""
        args: str
        gcode: str

        c = Path.Command("G0 X10 Y20 Z30 A10 B20 C30 U10 V20 W30")
        self.docobj.Path = Path.Path([c])
        postables = [self.docobj]
        args = "--inches"
        gcode = postprocessor.export(postables, "gcode.tmp", args)
        # print("--------\n" + gcode + "--------\n")
        self.assertEqual(gcode.splitlines()[1], "G20")
        self.assertEqual(
            gcode.splitlines()[2],
            "G0 X0.3937 Y0.7874 Z1.1811 A0.3937 B0.7874 C1.1811 U0.3937 V0.7874 W1.1811",
        )
        args = "--metric"
        gcode = postprocessor.export(postables, "gcode.tmp", args)
        # print("--------\n" + gcode + "--------\n")
        self.assertEqual(gcode.splitlines()[1], "G21")
        self.assertEqual(
            gcode.splitlines()[2],
            "G0 X10.000 Y20.000 Z30.000 A10.000 B20.000 C30.000 U10.000 V20.000 W30.000",
        )

    #############################################################################

    def test00180(self) -> None:
        """Test modal.

        Suppress the command name if the same as previous
        """
        args: str
        gcode: str

        c = Path.Command("G0 X10 Y20 Z30")
        c1 = Path.Command("G0 X10 Y30 Z30")
        self.docobj.Path = Path.Path([c, c1])
        postables = [self.docobj]
        args = "--modal"
        gcode = postprocessor.export(postables, "gcode.tmp", args)
        # print("--------\n" + gcode + "--------\n")
        self.assertEqual(gcode.splitlines()[3], "X10.000 Y30.000 Z30.000")
        args = "--no-modal"
        gcode = postprocessor.export(postables, "gcode.tmp", args)
        # print("--------\n" + gcode + "--------\n")
        self.assertEqual(gcode.splitlines()[3], "G0 X10.000 Y30.000 Z30.000")

    #############################################################################

    def test00190(self) -> None:
        """Test Outputting all arguments.

        Empty path.  Outputs all arguments.
        """
        expected = """Arguments that are commonly used:
  --metric              Convert output for Metric mode (G21) (default)
  --inches              Convert output for US imperial mode (G20)
  --axis-modal          Don't output axis values if they are the same as the
                        previous line
  --no-axis-modal       Output axis values even if they are the same as the
                        previous line (default)
  --axis-precision AXIS_PRECISION
                        Number of digits of precision for axis moves, default
                        is 3
  --bcnc                Add Job operations as bCNC block headers. Consider
                        suppressing comments by adding --no-comments
  --no-bcnc             Suppress bCNC block header output (default)
  --chipbreaking_amount CHIPBREAKING_AMOUNT
                        Amount to move for chipbreaking in a translated G73
                        command, default is 0.25 mm
  --command_space COMMAND_SPACE
                        The character to use between parts of a command,
                        default is a space, may also use a null string
  --comments            Output comments (default)
  --no-comments         Suppress comment output
  --comment_symbol COMMENT_SYMBOL
                        The character used to start a comment, default is "("
  --enable_coolant      Enable coolant
  --disable_coolant     Disable coolant (default)
  --enable_machine_specific_commands
                        Enable machine specific commands of the form
                        (MC_RUN_COMMAND: blah)
  --disable_machine_specific_commands
                        Disable machine specific commands (default)
  --end_of_line_characters END_OF_LINE_CHARACTERS
                        The character(s) to use at the end of each line in the
                        output file, default is whatever the system uses, may
                        also use '\\n' or '\\r\\n'
  --feed-precision FEED_PRECISION
                        Number of digits of precision for feed rate, default
                        is 3
  --finish_label FINISH_LABEL
                        The characters to use in the 'Finish operation'
                        comment, default is "Finish"
  --header              Output headers (default)
  --no-header           Suppress header output
  --line_number_increment LINE_NUMBER_INCREMENT
                        Amount to increment the line numbers, default is 10
  --line_number_start LINE_NUMBER_START
                        The number the line numbers start at, default is 100
  --line-numbers        Prefix with line numbers
  --no-line-numbers     Don't prefix with line numbers (default)
  --list_tools_in_preamble
                        List the tools used in the operation in the preamble
  --no-list_tools_in_preamble
                        Don't list the tools used in the operation (default)
  --modal               Don't output the G-command name if it is the same as
                        the previous line
  --no-modal            Output the G-command name even if it is the same as
                        the previous line (default)
  --output_adaptive     Enables special processing for operations with
                        'Adaptive' in the name
  --no-output_adaptive  Disables special processing for operations with
                        'Adaptive' in the name (default)
  --output_all_arguments
                        Output all of the available arguments
  --no-output_all_arguments
                        Don't output all of the available arguments (default)
  --output_machine_name
                        Output the machine name in the pre-operation
                        information
  --no-output_machine_name
                        Don't output the machine name in the pre-operation
                        information (default)
  --output_path_labels  Output Path labels at the beginning of each Path
  --no-output_path_labels
                        Don't output Path labels at the beginning of each Path
                        (default)
  --output_visible_arguments
                        Output all of the visible arguments
  --no-output_visible_arguments
                        Don't output the visible arguments (default)
  --postamble POSTAMBLE
                        Set commands to be issued after the last command,
                        default is ""
  --post_operation POST_OPERATION
                        Set commands to be issued after every operation,
                        default is ""
  --preamble PREAMBLE   Set commands to be issued before the first command,
                        default is ""
  --precision PRECISION
                        Number of digits of precision for both feed rate and
                        axis moves, default is 3 for metric or 4 for inches
  --return-to RETURN_TO
                        Move to the specified x,y,z coordinates at the end,
                        e.g. --return-to=0,0,0 (default is do not move)
  --show-editor         Pop up editor before writing output (default)
  --no-show-editor      Don't pop up editor before writing output
  --tlo                 Output tool length offset (G43) following tool changes
                        (default)
  --no-tlo              Suppress tool length offset (G43) following tool
                        changes
  --tool_change         Insert M6 and any other tool change G-code for all
                        tool changes (default)
  --no-tool_change      Convert M6 to a comment for all tool changes
  --translate_drill     Translate drill cycles G73, G81, G82 & G83 into G0/G1
                        movements
  --no-translate_drill  Don't translate drill cycles G73, G81, G82 & G83 into
                        G0/G1 movements (default)
  --wait-for-spindle WAIT_FOR_SPINDLE
                        Time to wait (in seconds) after M3, M4 (default = 0.0)
"""
        self.docobj.Path = Path.Path([])
        postables = [self.docobj]
        gcode: str = postprocessor.export(postables, "gcode.tmp", "--output_all_arguments")
        # The argparse help routine turns out to be sensitive to the
        # number of columns in the terminal window that the tests
        # are run from.  This affects the indenting in the output.
        # The next couple of lines remove all of the white space.
        gcode = "".join(gcode.split())
        expected = "".join(expected.split())
        self.assertEqual(gcode, expected)

    #############################################################################

    def test00200(self) -> None:
        """Test Outputting visible arguments.

        Empty path.  Outputs visible arguments.
        """
        self.single_compare([], "", "--output_visible_arguments")

    #############################################################################

    def test00205(self) -> None:
        """Test output_machine_name argument."""
        # test the default behavior
        self.single_compare(
            [],
            """(Begin preamble)
G90
G21
(Begin operation)
(Finish operation: testpath)
(Begin postamble)
""",
            "--comments",
        )

        # test outputting the machine name
        self.single_compare(
            [],
            """(Begin preamble)
G90
G21
(Begin operation)
(Machine: test, mm/min)
(Finish operation: testpath)
(Begin postamble)
""",
            "--output_machine_name --comments",
        )

        # test not outputting the machine name
        self.single_compare(
            [],
            """(Begin preamble)
G90
G21
(Begin operation)
(Finish operation: testpath)
(Begin postamble)
""",
            "--no-output_machine_name --comments",
        )

    #############################################################################

    def test00206(self) -> None:
        """Test output_path_labels argument."""
        # test the default behavior
        self.single_compare(
            [],
            """(Begin preamble)
G90
G21
(Begin operation)
(Finish operation: testpath)
(Begin postamble)
""",
            "--comments",
        )

        # test outputting the path labels
        self.single_compare(
            [],
            """(Begin preamble)
G90
G21
(Begin operation)
(Path: testpath)
(Finish operation: testpath)
(Begin postamble)
""",
            "--output_path_labels --comments",
        )

        # test not outputting the path labels
        self.single_compare(
            [],
            """(Begin preamble)
G90
G21
(Begin operation)
(Finish operation: testpath)
(Begin postamble)
""",
            "--no-output_path_labels --comments",
        )

    #############################################################################

    def test00210(self) -> None:
        """Test Postamble."""
        args: str
        gcode: str

        self.docobj.Path = Path.Path([])
        postables = [self.docobj]
        args = "--postamble='G0 Z50\nM2'"
        gcode = postprocessor.export(postables, "gcode.tmp", args)
        # print("--------\n" + gcode + "--------\n")
        self.assertEqual(gcode.splitlines()[-2], "G0 Z50")
        self.assertEqual(gcode.splitlines()[-1], "M2")

    #############################################################################

    def test00215(self) -> None:
        """Test the post_operation argument."""
        self.single_compare(
            [],
            """G90
G21
G90 G80
G40 G49
""",
            "--post_operation='G90 G80\nG40 G49'",
        )

    #############################################################################

    def test00220(self) -> None:
        """Test Preamble."""
        args: str
        gcode: str

        self.docobj.Path = Path.Path([])
        postables = [self.docobj]
        args = "--preamble='G18 G55'"
        gcode = postprocessor.export(postables, "gcode.tmp", args)
        # print("--------\n" + gcode + "--------\n")
        self.assertEqual(gcode.splitlines()[0], "G18 G55")

    #############################################################################

    def test00230(self) -> None:
        """Test precision."""
        self.compare_third_line(
            "G1 X10 Y20 Z30 F100",
            "G1 X10.00 Y20.00 Z30.00 F6000.00",
            "--precision=2",
        )
        self.compare_third_line(
            "G1 X10 Y20 Z30 F100",
            "G1 X0.39 Y0.79 Z1.18 F236.22",
            "--inches --precision=2",
        )

    #############################################################################

    def test00240(self) -> None:
        """Test return-to."""
        self.compare_third_line("", "G0 X12 Y34 Z56", "--return-to='12,34,56'")

    #############################################################################

    # The --show-editor argument must be tested interactively.
    # The --no-show-editor argument is also the default.

    #############################################################################

    def test00250(self) -> None:
        """Test tlo."""
        args: str
        gcode: str

        c = Path.Command("M6 T2")
        c2 = Path.Command("M3 S3000")
        self.docobj.Path = Path.Path([c, c2])
        postables = [self.docobj]
        args = "--tlo"
        gcode = postprocessor.export(postables, "gcode.tmp", args)
        # print("--------\n" + gcode + "--------\n")
        self.assertEqual(gcode.splitlines()[2], "M6 T2")
        self.assertEqual(gcode.splitlines()[3], "G43 H2")
        self.assertEqual(gcode.splitlines()[4], "M3 S3000")
        # suppress TLO
        args = "--no-tlo"
        gcode = postprocessor.export(postables, "gcode.tmp", args)
        # print("--------\n" + gcode + "--------\n")
        self.assertEqual(gcode.splitlines()[2], "M6 T2")
        self.assertEqual(gcode.splitlines()[3], "M3 S3000")

    #############################################################################

    def test00260(self) -> None:
        """Test tool_change."""
        args: str
        gcode: str

        c = Path.Command("M6 T2")
        c2 = Path.Command("M3 S3000")
        self.docobj.Path = Path.Path([c, c2])
        postables = [self.docobj]
        args = "--tool_change"
        gcode = postprocessor.export(postables, "gcode.tmp", args)
        # print("--------\n" + gcode + "--------\n")
        self.assertEqual(gcode.splitlines()[2], "M6 T2")
        self.assertEqual(gcode.splitlines()[3], "M3 S3000")
        args = "--comments --no-tool_change"
        gcode = postprocessor.export(postables, "gcode.tmp", args)
        # print("--------\n" + gcode + "--------\n")
        self.assertEqual(gcode.splitlines()[5], "( M6 T2 )")
        self.assertEqual(gcode.splitlines()[6], "M3 S3000")

    #############################################################################

    # The --translate_drill and --no-translate_drill arguments
    # are tested in the tests for G73, G81, G82, and G83.

    #############################################################################

    def test00270(self) -> None:
        """Test wait-for-spindle."""
        args: str
        gcode: str

        c = Path.Command("M3 S3000")
        self.docobj.Path = Path.Path([c])
        postables = [self.docobj]
        args = ""
        gcode = postprocessor.export(postables, "gcode.tmp", args)
        # print("--------\n" + gcode + "--------\n")
        self.assertEqual(gcode.splitlines()[2], "M3 S3000")
        args = "--wait-for-spindle=1.23456"
        gcode = postprocessor.export(postables, "gcode.tmp", args)
        # print("--------\n" + gcode + "--------\n")
        self.assertEqual(gcode.splitlines()[2], "M3 S3000")
        self.assertEqual(gcode.splitlines()[3], "G4 P1.23456")
        c = Path.Command("M4 S3000")
        self.docobj.Path = Path.Path([c])
        postables = [self.docobj]
        # This also tests that the default for --wait-for-spindle
        # goes back to 0.0 (no wait)
        args = ""
        gcode = postprocessor.export(postables, "gcode.tmp", args)
        # print("--------\n" + gcode + "--------\n")
        self.assertEqual(gcode.splitlines()[2], "M4 S3000")
        args = "--wait-for-spindle=1.23456"
        gcode = postprocessor.export(postables, "gcode.tmp", args)
        # print("--------\n" + gcode + "--------\n")
        self.assertEqual(gcode.splitlines()[2], "M4 S3000")
        self.assertEqual(gcode.splitlines()[3], "G4 P1.23456")
