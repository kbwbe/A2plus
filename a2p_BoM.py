#***************************************************************************
#*                                                                         *
#*   Copyright (c) 2018 kbwbe                                              *
#*                                                                         *
#*   This program is free software; you can redistribute it and/or modify  *
#*   it under the terms of the GNU Lesser General Public License (LGPL)    *
#*   as published by the Free Software Foundation; either version 2 of     *
#*   the License, or (at your option) any later version.                   *
#*   for detail see the LICENCE text file.                                 *
#*                                                                         *
#*   This program is distributed in the hope that it will be useful,       *
#*   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
#*   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
#*   GNU Library General Public License for more details.                  *
#*                                                                         *
#*   You should have received a copy of the GNU Library General Public     *
#*   License along with this program; if not, write to the Free Software   *
#*   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  *
#*   USA                                                                   *
#*                                                                         *
#***************************************************************************

import os
import FreeCAD, FreeCADGui
from PySide import QtGui, QtCore
import Spreadsheet
import string

import a2plib
#from a2p_fcdocumentreader import FCdocumentReader
from a2p_simpleXMLreader import FCdocumentReader

from a2p_partlistglobals import (
    PARTLIST_COLUMN_NAMES,
    BOM_SHEET_NAME,
    BOM_SHEET_LABEL,
    PARTINFORMATION_SHEET_NAME,
    BOM_MAX_COLS,
    BOM_MAX_LENGTH
    )

translate = FreeCAD.Qt.translate

#------------------------------------------------------------------------------
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
    workingDir,basicFileName = os.path.split(fileNameInProject)

    docReader1 = FCdocumentReader()
    docReader1.openDocument(fileNameInProject)

    for ob in docReader1.getA2pObjects():
        # skip converted parts...
        if a2plib.to_str(ob.getA2pSource()) == a2plib.to_str('converted'): continue

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
            linkedSource = a2plib.findSourceFileInProject( #this returns unicode on py2 systems!
                            linkedSource1,
                            workingDir
                            )
            if linkedSource is None:
                print(translate("A2p_BoM", "BOM ERROR: Could not open sourcefile '{}'").format(linkedSource1))
                continue
            # Is it already processed minimum one time ?
            entry = partListEntries.get(linkedSource,None)
            if entry is not None:
                partListEntries.get(linkedSource)[0]+=1 #count sourcefile usage
                continue # only needed to count imports of this file, information exists yet

            # There is no entry in dict, need to read out information from importFile...
            docReader2 = FCdocumentReader()
            docReader2.openDocument(linkedSource)

            # Initialize a default parts information...
            partInformation = []
            for i in range(0,len(PARTLIST_COLUMN_NAMES)):
                partInformation.append("*")

            # if there is a proper spreadsheet, then read it...
            for ob in docReader2.getSpreadsheetObjects():

                sheetName = PARTINFORMATION_SHEET_NAME
                sheetName = a2plib.to_bytes(PARTINFORMATION_SHEET_NAME)

                if ob.name == sheetName:
                    cells = ob.getCells()
                    for addr in cells.keys():
                        if addr[:1] == b'B': #column B contains the data, A only the titles
                            idx = int(addr[1:])-1
                            if idx < len(PARTLIST_COLUMN_NAMES): # don't read further!
                                partInformation[idx] = cells[addr]
            # last entry of partinformations is reserved for filename
            partInformation[-1] = os.path.split(linkedSource)[1] #without complete path...

            # put information to dict and count usage of sourcefiles..
            entry = partListEntries.get(linkedSource,None)
            if entry is None:
                partListEntries[linkedSource] = [
                    1,
                    partInformation
                    ]
            else:
                partListEntries.get(linkedSource)[0]+=1 #count sourcefile usage

    return partListEntries


#------------------------------------------------------------------------------
toolTip = translate("A2plus",
'''
Create a spreadsheet with a
parts list of this file.

This function will read out
the #PARTINFO# spreadsheet of
all involved parts of the
assembly and create a new
spreadsheet containing the
parts list.

This button will open a dialog
with the Question:
- Iterate recursively over
     all subassenblies?

Answer Yes:
All parts of all subassemblies are
collected to the partlist

Answer No:
Only the parts within the
recent assembly are collected.
'''
)

class a2p_CreatePartlist():

    def clearPartList(self):
        alphabet_list = list(string.ascii_uppercase)
        doc = FreeCAD.activeDocument()
        ss = doc.getObject(BOM_SHEET_NAME)
        for i in range(0,BOM_MAX_COLS):
            for k in range(0,BOM_MAX_LENGTH):
                cellAdress = alphabet_list[i]+str(k+1)
                ss.set(cellAdress,'')

    def Activated(self):
        doc = FreeCAD.activeDocument()
        if doc is None:
            QtGui.QMessageBox.information(  QtGui.QApplication.activeWindow(),
                                        translate("A2plus", "No active document found!"),
                                        translate("A2plus", "You have to open a FCStd file first.")
                                    )
            return
        completeFilePath = doc.FileName
        p,f = os.path.split(completeFilePath)

        flags = QtGui.QMessageBox.StandardButton.Yes | QtGui.QMessageBox.StandardButton.No
        msg = translate("A2plus", "Please save before generating a parts list! Save now?")
        response = QtGui.QMessageBox.information(QtGui.QApplication.activeWindow(), translate("A2plus", "Save document?"), msg, flags )
        if response == QtGui.QMessageBox.No:
            QtGui.QMessageBox.information(  QtGui.QApplication.activeWindow(),
                                        translate("A2plus", "Parts list generation aborted!"),
                                        translate("A2plus", "You have to save the assembly file first.")
                                    )
            return
        else:
            doc.save()

        flags = QtGui.QMessageBox.StandardButton.Yes | QtGui.QMessageBox.StandardButton.No
        msg = translate("A2plus", "Do you want to iterate recursively over all included subassemblies?")
        response = QtGui.QMessageBox.information(QtGui.QApplication.activeWindow(), translate("A2p_BoM", "PARTSLIST"), msg, flags )
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
            ss = doc.addObject('Spreadsheet::Sheet',BOM_SHEET_NAME)
            ss.Label = BOM_SHEET_LABEL
        else:
            self.clearPartList()

        # Write Column headers to spreadsheet
        ss.set('A1', translate("A2p_BoM", "POS"))
        ss.set('B1', translate("A2p_BoM", "QTY"))
        idx1 = ord('C')
        idx2 = idx1 + len(PARTLIST_COLUMN_NAMES)
        i=0
        for c in range(idx1,idx2):
            ss.set(chr(c)+"1",PARTLIST_COLUMN_NAMES[i])
            i+=1
        # Set the background color of the column headers
        ss.setBackground('A1:'+chr(idx2-1)+'1', (0.000000,1.000000,0.000000,1.000000))
        # Set the columnwith to proper values
        ss.setColumnWidth('A',40)
        i=0
        for c in range(idx1,idx2):
            ss.setColumnWidth(chr(c),150)
            i+=1
        # fill entries for partsList...
        idx3 = ord('A')
        for idx, k in enumerate(partListEntries.keys()):
            ss.set('A'+str(idx+2),str(idx+1))
            ss.set('B'+str(idx+2),str(partListEntries[k][0]))
            values = partListEntries[k][1]
            for j,tx in enumerate(values): # all strings inside values are unicode!
                #ss.set needs 2. argument as unicode for py3 and utf-8 string for py2!!!
                tx2 = tx # preserve unicode
                ss.set(chr(idx3+2+j)+str(idx+2),tx2)

        # recompute to finish..
        doc.recompute()
        FreeCAD.Console.PrintMessage(translate("A2p_BoM", "#PARTSLIST# spreadsheet has been created") + "\n")

    def GetResources(self):
        return {
            'Pixmap'  : ':/icons/a2p_PartsList.svg',
            'MenuText': translate("A2plus", "Create a spreadsheet with a parts list of this file"),
            'ToolTip' : toolTip
            }

FreeCADGui.addCommand('a2p_CreatePartlist', a2p_CreatePartlist())
#------------------------------------------------------------------------------
