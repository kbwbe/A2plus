# ***************************************************************************
# *                                                                         *
# *   Copyright (c) 2018 kbwbe                                              *
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
import string

from PySide import QtGui, QtCore

import FreeCAD
import FreeCADGui
import Part
import a2plib
import Spreadsheet

# from a2p_fcdocumentreader import FCdocumentReader
from a2p_simpleXMLreader import FCdocumentReader

from a2p_partlistglobals import (
    PARTLIST_COLUMN_NAMES,
    CLO_PARTLIST_COLUMN_NAMES,
    BOM_SHEET_NAME,
    BOM_SHEET_LABEL,
    CLO_BOM_SHEET_NAME,
    CLO_BOM_SHEET_LABEL,
    PARTINFORMATION_SHEET_NAME,
    BOM_MAX_COLS,
    BOM_MAX_LENGTH
)


translate = FreeCAD.Qt.translate


def createCutListOptimizerPartList(
        importPath,
        parentAssemblyDir,
        partListEntries,
        recursive=False
):
    """
    Extract quantities and descriptions of assembled parts from
    document.xml
    Is able to analyse subassemblies by recursion

    It works with a dict. Structure of an entry is:
    filename: [Quantity,[information,information,....] ]

    CutListOptimizer (https://cutlistoptimizer.com/) expects the following CSV format:
    Length,Width,Qty,Material,Label,Enabled
    200,300,3,DEFAULT_MATERIAL,200×300,true

    NOTE: The column Material could be skipped, if it is the same for all parts.
    """
    fileNameInProject = a2plib.findSourceFileInProject(
        importPath,
        parentAssemblyDir
    )
    workingDir, basicFileName = os.path.split(fileNameInProject)

    docReader1 = FCdocumentReader()
    docReader1.openDocument(fileNameInProject)

    for ob in docReader1.getA2pObjects():
        # skip converted parts...
        if a2plib.to_str(ob.getA2pSource()) == a2plib.to_str('converted'):
            continue

        if ob.isSubassembly() and recursive:
            partListEntries = createPartList(
                ob.getA2pSource(),
                workingDir,
                partListEntries,
                recursive
            )

        # Process information of this a2p object
        if not ob.isSubassembly() or not recursive:
            # Try to get spreadsheetdata _PARTINFO_ from linked source
            linkedSource1 = ob.getA2pSource()
            # this returns unicode on py2 systems!
            linkedSource = a2plib.findSourceFileInProject(
                linkedSource1,
                workingDir
            )
            if linkedSource is None:
                print(translate("A2p_BoM", "BOM ERROR: Could not open sourcefile '{}'").format(
                    linkedSource1))
                continue
            # Is it already processed minimum one time ?
            entry = partListEntries.get(linkedSource, None)
            if entry is not None:
                # count sourcefile usage
                partListEntries.get(linkedSource)[0] += 1
                continue  # only needed to count imports of this file, information exists yet

            # There is no entry in dict, need to read out information from importFile...
            docReader2 = FCdocumentReader()
            docReader2.openDocument(linkedSource)

            # Initialize a default parts information...
            partInformation = []
            for i in range(0, len(CLO_PARTLIST_COLUMN_NAMES)):
                partInformation.append("*")

            # if there is a proper spreadsheet, then read it...
            for ob in docReader2.getSpreadsheetObjects():

                sheetName = PARTINFORMATION_SHEET_NAME
                sheetName = a2plib.to_bytes(PARTINFORMATION_SHEET_NAME)

                if ob.name == sheetName:
                    cells = ob.getCells()
                    for addr in cells.keys():
                        if addr[:1] == b'B':  # column B contains the data, A only the titles
                            idx = int(addr[1:])-1
                            if idx < len(CLO_PARTLIST_COLUMN_NAMES):  # don't read further!
                                partInformation[idx] = cells[addr]
            # last entry of partinformations is reserved for filename
            # without complete path...
            partInformation[-1] = os.path.split(linkedSource)[1]

            # #########################################################
            # add dimensions from the overall bounding box of the file
            # in the last 3 fields before the filename
            dc = FreeCAD.openDocument(linkedSource)
            op = Part.makeCompound([i.Shape for i in dc.findObjects(
                "Part::Feature") if i.ViewObject.Visibility and not i.TypeId == "PartDesign::Plane"])
            bb = op.BoundBox
            partInformation[-2] = str(bb.ZLength)
            partInformation[-3] = str(bb.YLength)
            partInformation[-4] = str(bb.XLength)
            FreeCAD.closeDocument(dc.Name)
            # #########################################################

            # put information to dict and count usage of sourcefiles..
            entry = partListEntries.get(linkedSource, None)
            if entry is None:
                partListEntries[linkedSource] = [
                    1,
                    partInformation
                ]
            else:
                # count sourcefile usage
                partListEntries.get(linkedSource)[0] += 1

    return partListEntries


def createPartList(
        importPath,
        parentAssemblyDir,
        partListEntries,
        recursive=False
):
    """
    Extract quantities and descriptions of assembled parts from
    document.xml
    Is able to analyse subassemblies by recursion

    It works with a dict. Structure of an entry is:
    filename: [Quantity,[information,information,....] ]
    """
    fileNameInProject = a2plib.findSourceFileInProject(
        importPath,
        parentAssemblyDir
    )
    workingDir, basicFileName = os.path.split(fileNameInProject)

    docReader1 = FCdocumentReader()
    docReader1.openDocument(fileNameInProject)

    for ob in docReader1.getA2pObjects():
        # skip converted parts...
        if a2plib.to_str(ob.getA2pSource()) == a2plib.to_str('converted'):
            continue

        if ob.isSubassembly() and recursive:
            partListEntries = createPartList(
                ob.getA2pSource(),
                workingDir,
                partListEntries,
                recursive
            )

        # Process information of this a2p object
        if not ob.isSubassembly() or not recursive:
            # Try to get spreadsheetdata _PARTINFO_ from linked source
            linkedSource1 = ob.getA2pSource()
            # this returns unicode on py2 systems!
            linkedSource = a2plib.findSourceFileInProject(
                linkedSource1,
                workingDir
            )
            if linkedSource is None:
                print(translate("A2p_BoM", "BOM ERROR: Could not open sourcefile '{}'").format(
                    linkedSource1))
                continue
            # Is it already processed minimum one time ?
            entry = partListEntries.get(linkedSource, None)
            if entry is not None:
                # count sourcefile usage
                partListEntries.get(linkedSource)[0] += 1
                continue  # only needed to count imports of this file, information exists yet

            # There is no entry in dict, need to read out information from importFile...
            docReader2 = FCdocumentReader()
            docReader2.openDocument(linkedSource)

            # Initialize a default parts information...
            partInformation = []
            for i in range(0, len(PARTLIST_COLUMN_NAMES)):
                partInformation.append("*")

            # if there is a proper spreadsheet, then read it...
            for ob in docReader2.getSpreadsheetObjects():

                sheetName = PARTINFORMATION_SHEET_NAME
                sheetName = a2plib.to_bytes(PARTINFORMATION_SHEET_NAME)

                if ob.name == sheetName:
                    cells = ob.getCells()
                    for addr in cells.keys():
                        if addr[:1] == b'B':  # column B contains the data, A only the titles
                            idx = int(addr[1:])-1
                            if idx < len(PARTLIST_COLUMN_NAMES):  # don't read further!
                                partInformation[idx] = cells[addr]
            # last entry of partinformations is reserved for filename
            # without complete path...
            partInformation[-1] = os.path.split(linkedSource)[1]

            # put information to dict and count usage of sourcefiles..
            entry = partListEntries.get(linkedSource, None)
            if entry is None:
                partListEntries[linkedSource] = [
                    1,
                    partInformation
                ]
            else:
                # count sourcefile usage
                partListEntries.get(linkedSource)[0] += 1

    return partListEntries


class a2p_CreatePartlist():

    def clearPartList(self):
        alphabet_list = list(string.ascii_uppercase)
        doc = FreeCAD.activeDocument()
        ss = doc.getObject(BOM_SHEET_NAME)
        for i in range(0, BOM_MAX_COLS):
            for k in range(0, BOM_MAX_LENGTH):
                cellAdress = alphabet_list[i] + str(k + 1)
                ss.set(cellAdress, '')

    def Activated(self):
        doc = FreeCAD.activeDocument()
        if doc is None:
            QtGui.QMessageBox.information(
                QtGui.QApplication.activeWindow(),
                translate("A2plus", "No active document found!"),
                translate("A2plus", "You have to open a FCStd file first.")
            )
            return
        completeFilePath = doc.FileName
        p, f = os.path.split(completeFilePath)

        flags = QtGui.QMessageBox.StandardButton.Yes | QtGui.QMessageBox.StandardButton.No
        msg = translate(
            "A2plus", "Please save before generating a parts list! Save now?")
        response = QtGui.QMessageBox.information(QtGui.QApplication.activeWindow(
        ), translate("A2plus", "Save document?"), msg, flags)
        if response == QtGui.QMessageBox.No:
            QtGui.QMessageBox.information(
                QtGui.QApplication.activeWindow(),
                translate("A2plus", "Parts list generation aborted!"),
                translate("A2plus", "You have to save the assembly file first.")
            )
            return
        else:
            doc.save()

        flags = QtGui.QMessageBox.StandardButton.Yes | QtGui.QMessageBox.StandardButton.No
        msg = translate(
            "A2plus", "Do you want to iterate recursively over all included subassemblies?")
        response = QtGui.QMessageBox.information(
            QtGui.QApplication.activeWindow(), translate("A2p_BoM", "PARTSLIST"), msg, flags)
        if response == QtGui.QMessageBox.Yes:
            subAssyRecursion = True
        else:
            subAssyRecursion = False

        partListEntries = createPartList(
            doc.FileName,
            p,
            {},
            recursive=subAssyRecursion
        )

        ss = None
        try:
            ss = doc.getObject(BOM_SHEET_NAME)
        except:
            pass
        if ss is None:
            ss = doc.addObject('Spreadsheet::Sheet', BOM_SHEET_NAME)
            ss.Label = BOM_SHEET_LABEL
        else:
            self.clearPartList()

        # Write Column headers to spreadsheet
        ss.set('A1', translate("A2p_BoM", "POS"))
        ss.set('B1', translate("A2p_BoM", "QTY"))
        self.CreateColumnHeadersInSpreadsheet(ss, PARTLIST_COLUMN_NAMES, 'C')
        # fill entries for partsList...
        idx3 = ord('A')
        for idx, k in enumerate(partListEntries.keys()):
            ss.set('A' + str(idx + 2), str(idx + 1))
            ss.set('B' + str(idx + 2), str(partListEntries[k][0]))
            values = partListEntries[k][1]
            for j, tx in enumerate(values):  # all strings inside values are unicode!
                ss.set(chr(idx3 + 2 + j) + str(idx + 2),
                       tx.replace('&apos;', ''))

        # recompute to finish...
        doc.recompute()
        FreeCAD.Console.PrintMessage(
            translate("A2p_BoM", "#PARTSLIST# spreadsheet has been created") + "\n")

    def GetResources(self):
        return {
            'Pixmap': ':/icons/a2p_PartsList.svg',
            'MenuText': translate("A2plus", "Create a spreadsheet with a parts list of this file"),
            'ToolTip': translate(
                "A2plus", "Create a spreadsheet with a " + "\n" +
                "parts list of this file." + "\n\n" +
                "This function will read out " + "\n" +
                "the #PARTINFO# spreadsheet of " + "\n" +
                "all involved parts of the " + "\n" +
                "assembly and create a new " + "\n" +
                "spreadsheet containing the " + "\n" +
                "parts list." + "\n\n" +
                "This button will open a dialog " + "\n" +
                "with the Question:" + "\n" +
                "- Iterate recursively over " + "\n" +
                "     all subassenblies?" + "\n\n" +
                "Answer Yes:" + "\n" +
                "All parts of all subassemblies are " + "\n" +
                "collected to the partlist " + "\n\n" +
                "Answer No:" + "\n" +
                "Only the parts within the " + "\n" +
                "recent assembly are collected.")
        }

    def CreateColumnHeadersInSpreadsheet(self, ss, columnHeaders, startColumn):
        """
        Creates the column headers in the given spreadsheet (`ss`) starting in the column `startColumn`.
        The column headers are specified in the array `columnHeaders`.
        """
        # Write Column headers to spreadsheet
        idx1 = ord(startColumn)
        idx2 = idx1 + len(columnHeaders)
        i = 0
        for c in range(idx1, idx2):
            ss.set(chr(c) + "1", columnHeaders[i])
            i += 1
        # Set the background color of the column headers
        ss.setBackground('A1:' + chr(idx2 - 1) + '1',
                         (0.000000, 1.000000, 0.000000, 1.000000))
        # Set the columnwith to proper values
        ss.setColumnWidth('A', 40)
        i = 0
        for c in range(idx1, idx2):
            ss.setColumnWidth(chr(c), 150)
            i += 1


class a2p_CreateCutListOptimizerPartlist(a2p_CreatePartlist):

    def clearPartList(self):
        alphabet_list = list(string.ascii_uppercase)
        doc = FreeCAD.activeDocument()
        ss = doc.getObject(CLO_BOM_SHEET_NAME)
        for i in range(0, CLO_BOM_MAX_COLS):
            for k in range(0, CLO_BOM_MAX_LENGTH):
                cellAdress = alphabet_list[i] + str(k + 1)
                ss.set(cellAdress, '')

    def Activated(self):
        doc = FreeCAD.activeDocument()
        if doc is None:
            QtGui.QMessageBox.information(
                QtGui.QApplication.activeWindow(),
                translate("A2plus", "No active document found!"),
                translate("A2plus", "You have to open a FCStd file first.")
            )
            return
        completeFilePath = doc.FileName
        p, f = os.path.split(completeFilePath)

        flags = QtGui.QMessageBox.StandardButton.Yes | QtGui.QMessageBox.StandardButton.No
        msg = translate(
            "A2plus", "Please save before generating a parts list! Save now?")
        response = QtGui.QMessageBox.information(QtGui.QApplication.activeWindow(
        ), translate("A2plus", "Save document?"), msg, flags)
        if response == QtGui.QMessageBox.No:
            QtGui.QMessageBox.information(
                QtGui.QApplication.activeWindow(),
                translate("A2plus", "Parts list generation aborted!"),
                translate("A2plus", "You have to save the assembly file first.")
            )
            return
        else:
            doc.save()

        flags = QtGui.QMessageBox.StandardButton.Yes | QtGui.QMessageBox.StandardButton.No
        msg = translate(
            "A2plus", "Do you want to iterate recursively over all included subassemblies?")
        response = QtGui.QMessageBox.information(
            QtGui.QApplication.activeWindow(), translate("A2p_BoM", "PARTSLIST"), msg, flags)
        if response == QtGui.QMessageBox.Yes:
            subAssyRecursion = True
        else:
            subAssyRecursion = False

        partListEntries = createCutListOptimizerPartList(
            doc.FileName,
            p,
            {},
            recursive=subAssyRecursion
        )

        ss = None
        try:
            ss = doc.getObject(CLO_BOM_SHEET_NAME)
        except:
            pass
        if ss is None:
            ss = doc.addObject('Spreadsheet::Sheet', CLO_BOM_SHEET_NAME)
            ss.Label = CLO_BOM_SHEET_LABEL
        else:
            self.clearPartList()

        self.CreateColumnHeadersInSpreadsheet(
            ss, CLO_PARTLIST_COLUMN_NAMES, 'A')

        self.FillPartsListEntries(ss, partListEntries)

        # recompute to finish...
        doc.recompute()
        FreeCAD.Console.PrintMessage(translate(
            "A2p_BoM", "#PARTSLIST_CutListOptimizer# spreadsheet has been created") + "\n")

    def GetResources(self):
        return {
            'Pixmap': ':/icons/a2p_PartsList_CutListOptimizer.svg',
            'MenuText': translate("A2plus", "Create a spreadsheet with a parts list for https://cutlistoptimizer.com/ of this file"),
            'ToolTip': translate(
                "A2plus", "Create a spreadsheet with a " + "\n" +
                "parts list https://cutlistoptimizer.com/ of this file." + "\n\n" +
                "This function will read out " + "\n" +
                "the #PARTINFO# spreadsheet of " + "\n" +
                "all involved parts of the " + "\n" +
                "assembly and create a new " + "\n" +
                "spreadsheet containing the " + "\n" +
                "parts list." + "\n\n" +
                "This button will open a dialog " + "\n" +
                "with the Question:" + "\n" +
                "- Iterate recursively over " + "\n" +
                "     all subassenblies?" + "\n\n" +
                "Answer Yes:" + "\n" +
                "All parts of all subassemblies are " + "\n" +
                "collected to the partlist " + "\n\n" +
                "Answer No:" + "\n" +
                "Only the parts within the " + "\n" +
                "recent assembly are collected.")
        }

    def FillPartsListEntries(self, ss, partListEntries):
        # [2, ['*', '*', '75.0', '45.0', '1050.0', 'LongBeam.FCStd']]
        QUANTITY_IDX = 0
        LENGTH_IDX = 2
        WIDTH_IDX = 3
        HEIGHT_IDX = 4
        FILENAME_IDX = 5

        for idx, k in enumerate(partListEntries.keys()):
            quantity = partListEntries[k][QUANTITY_IDX]
            values = partListEntries[k][1]
            ss.set('A' + str(idx + 2), str(values[LENGTH_IDX]))
            ss.set('B' + str(idx + 2), str(values[WIDTH_IDX]))
            ss.set('C' + str(idx + 2), str(quantity))
            ss.set('D' + str(idx + 2), str(values[HEIGHT_IDX]))
            ss.set('E' + str(idx + 2), values[FILENAME_IDX])
            ss.set('F' + str(idx + 2), "true")


FreeCADGui.addCommand('a2p_CreatePartlist', a2p_CreatePartlist())
FreeCADGui.addCommand('a2p_CreateCutListOptimizerPartlist',
                      a2p_CreateCutListOptimizerPartlist())
