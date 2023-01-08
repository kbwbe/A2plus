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
from PySide import QtGui

import FreeCAD
import FreeCADGui
import a2plib
from a2p_importpart import updateImportedParts
from a2p_simpleXMLreader import FCdocumentReader

translate = FreeCAD.Qt.translate


def createUpdateFileList(
            importPath,
            parentAssemblyDir,
            filesToUpdate,
            recursive=False,
            selectedFiles=[]  # only update parts with these sourceFiles
            ):

    # do not update converted parts
    print(
          translate(
                    "A2plus",
                    "createUpdateFileList(): ImportPath = {}").format(
                        importPath
                    )
            )

    if a2plib.to_bytes(importPath) == b'converted':
        return False, filesToUpdate

    fileNameInProject = a2plib.findSourceFileInProject(
        importPath,
        parentAssemblyDir
        )
    workingDir, basicFileName = os.path.split(fileNameInProject)
    docReader1 = FCdocumentReader()

    docReader1.openDocument(fileNameInProject)
    needToUpdate = False
    subAsmNeedsUpdate = False
    for ob in docReader1.getA2pObjects():

        if a2plib.to_bytes(ob.getA2pSource()) == b'converted':
            print(
                translate(
                    "A2plus", "Did not update converted part '{}'").format(
                    ob.name
                    )
                )
            continue

        # Only update parts which are selected by the user...
        fDir, fName = os.path.split(ob.getA2pSource())
        if len(selectedFiles) > 0 and fName not in selectedFiles:
            continue

        if ob.isSubassembly() and recursive:
            subAsmNeedsUpdate, filesToUpdate = createUpdateFileList(
                                                ob.getA2pSource(),
                                                workingDir,
                                                filesToUpdate,
                                                recursive
                                                )
        if subAsmNeedsUpdate:
            needToUpdate = True

        objFileNameInProject = a2plib.findSourceFileInProject(
            ob.getA2pSource(),
            workingDir
            )
        mtime = os.path.getmtime(objFileNameInProject)
        if ob.getTimeLastImport() < mtime:
            needToUpdate = True

    if needToUpdate:
        if fileNameInProject not in filesToUpdate:
            filesToUpdate.append(fileNameInProject)

    return needToUpdate, filesToUpdate


class a2p_recursiveUpdateImportedPartsCommand:

    def Activated(self):
        a2plib.setAutoSolve(True)  # makes no sense without autosolve = ON
        doc = FreeCAD.activeDocument()

        if doc is None:
            QtGui.QMessageBox.information(
                    QtGui.QApplication.activeWindow(),
                    translate("A2plus", "No active document found!"),
                    translate(
                        "A2plus",
                        "Before recursive updating parts, you have to open an assembly file."
                                )
                        )
            return

        fileName = doc.FileName
        workingDir, basicFileName = os.path.split(fileName)

        selectedFiles = []
        partial = False
        selection = [s for s in FreeCADGui.Selection.getSelection()
                     if s.Document == FreeCAD.ActiveDocument and
                     (a2plib.isA2pPart(s) or a2plib.isA2pSketch(s))
                     ]
        if selection and len(selection) > 0:
            flags = QtGui.QMessageBox.StandardButton.Yes | QtGui.QMessageBox.StandardButton.No
            msg = translate("A2plus", "Do you want to update the selected parts only?")
            response = QtGui.QMessageBox.information(
                            QtGui.QApplication.activeWindow(),
                            translate("A2plus", "RECURSIVE UPDATE"),
                            msg,
                            flags
                            )
            if response == QtGui.QMessageBox.Yes:
                for s in selection:
                    fDir, fName = os.path.split(s.sourceFile)
                    selectedFiles.append(fName)
                    partial = True

        filesToUpdate = []
        subAsmNeedsUpdate, filesToUpdate = createUpdateFileList(
                                            fileName,
                                            workingDir,
                                            filesToUpdate,
                                            True,
                                            selectedFiles
                                            )

        for f in filesToUpdate:
            # update necessary documents

            # look only for filenames, not paths, as there are problems on WIN10 (Address-translation??)
            importDoc = None
            importDocIsOpen = False
            requestedFile = os.path.split(f)[1]
            for d in FreeCAD.listDocuments().values():
                recentFile = os.path.split(d.FileName)[1]
                if requestedFile == recentFile:
                    importDoc = d  # file is already open...
                    importDocIsOpen = True
                    break

            if not importDocIsOpen:
                if f.lower().endswith('.fcstd'):
                    importDoc = FreeCAD.openDocument(f)
                elif f.lower().endswith('.stp') or f.lower().endswith('.step'):
                    import ImportGui
                    fname = os.path.splitext(os.path.basename(f))[0]
                    FreeCAD.newDocument(fname)
                    newname = FreeCAD.ActiveDocument.Name
                    FreeCAD.setActiveDocument(newname)
                    ImportGui.insert(filename, newname)
                    importDoc = FreeCAD.ActiveDocument
                else:
                    QtGui.QMessageBox.information(
                                QtGui.QApplication.activeWindow(),
                                translate("A2plus", "Value Error"),
                                translate("A2plus", "A part can only be imported from a FreeCAD '*.FCStd' file")
                                                  )
                    return

            if importDoc == doc and partial is True:
                updateImportedParts(importDoc, True)
            else:
                updateImportedParts(importDoc)

            FreeCADGui.updateGui()
            importDoc.save()
            FreeCAD.Console.PrintMessage(
                "===== " + translate(
                                "A2plus",
                                "Assembly '{}' has been updated!").format(
                                    importDoc.FileName
                                        ) + " =====\n"
                                     )
            if importDoc != doc:
                FreeCAD.closeDocument(importDoc.Name)

    def GetResources(self):
        return {
            'Pixmap': ':/icons/a2p_RecursiveUpdate.svg',
            'MenuText': translate("A2plus", "Update imports recursively"),
            'ToolTip': translate(
                                "A2plus",
                                "Update parts, which have been" + "\n" +
                                "imported to the assembly." + "\n\n" +
                                "(If you modify a part in an" + "\n" +
                                "external file, the new shape" + "\n" +
                                "is taken to the assembly by" + "\n" +
                                "this function)." + "\n\n" +
                                "This command does this recursively" + "\n" +
                                "over all involved subassemblies." + "\n\n" +
                                "Subassemblies are updated," + "\n" +
                                "if necessary, too."
                                )
                }


FreeCADGui.addCommand('a2p_recursiveUpdateImportedPartsCommand', a2p_recursiveUpdateImportedPartsCommand())
