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

import FreeCADGui,FreeCAD
from PySide import QtGui, QtCore
import os
import string

import a2plib
from a2p_importpart import updateImportedParts
#from a2p_fcdocumentreader import FCdocumentReader
from a2p_simpleXMLreader import FCdocumentReader


#==============================================================================
def createUpdateFileList(
            importPath,
            parentAssemblyDir,
            filesToUpdate,
            recursive=False,
            selectedFiles=[] #only update parts with these sourceFiles
            ):
    
    # do not update converted parts
    print(
        "createUpdateFileList importPath = {}".format(
            importPath
            )
        )
    if a2plib.to_bytes(importPath) == b'converted':
        return False, filesToUpdate
    
    fileNameInProject = a2plib.findSourceFileInProject(
        importPath,
        parentAssemblyDir
        )
    workingDir,basicFileName = os.path.split(fileNameInProject)
    docReader1 = FCdocumentReader()
    
    docReader1.openDocument(fileNameInProject)
    needToUpdate = False
    subAsmNeedsUpdate = False
    for ob in docReader1.getA2pObjects():
        
        if a2plib.to_bytes(ob.getA2pSource()) == b'converted':
            print(
                "Did not update converted part '{}'".format(
                    ob.name
                    )
                )
            continue
        
        #Only update parts which are selected by the user...
        fDir,fName = os.path.split(ob.getA2pSource())
        if len(selectedFiles)>0 and fName not in selectedFiles:
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
#==============================================================================
toolTip = \
'''
Update parts, which have been
imported to the assembly.

(If you modify a part in an
external file, the new shape
is taken to the assembly by
this function.)

This command does this recursively
over all involved subassemblies.

Subassemblies are updated,
if necessary, too.
'''


class a2p_recursiveUpdateImportedPartsCommand:

    def Activated(self):
        a2plib.setAutoSolve(True) # makes no sense without autosolve = ON
        doc = FreeCAD.activeDocument()
        fileName = doc.FileName
        workingDir,basicFileName = os.path.split(fileName)
        
        selectedFiles=[]
        partial = False
        selection = [s for s in FreeCADGui.Selection.getSelection() 
                     if s.Document == FreeCAD.ActiveDocument and
                     (a2plib.isA2pPart(s) or a2plib.isA2pSketch())
                     ]
        if selection and len(selection)>0:
            flags = QtGui.QMessageBox.StandardButton.Yes | QtGui.QMessageBox.StandardButton.No
            msg = u"Do you want to update only the selected parts?"
            response = QtGui.QMessageBox.information(
                            QtGui.QApplication.activeWindow(),
                            u"RECURSIVE UPDATE",
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
            #-------------------------------------------
            # update necessary documents
            #-------------------------------------------
            
            # look only for filenames, not paths, as there are problems on WIN10 (Address-translation??)
            importDoc = None
            importDocIsOpen = False
            requestedFile = os.path.split(f)[1]
            for d in FreeCAD.listDocuments().values():
                recentFile = os.path.split(d.FileName)[1]
                if requestedFile == recentFile:
                    importDoc = d # file is already open...
                    importDocIsOpen = True
                    break
        
            if not importDocIsOpen:
                if f.lower().endswith('.fcstd'):
                    importDoc = FreeCAD.openDocument(f)
                elif f.lower().endswith('.stp') or f.lower().endswith('.step'):
                    import ImportGui
                    fname =  os.path.splitext(os.path.basename(f))[0]
                    FreeCAD.newDocument(fname)
                    newname = FreeCAD.ActiveDocument.Name
                    FreeCAD.setActiveDocument(newname)
                    ImportGui.insert(filename,newname)
                    importDoc = FreeCAD.ActiveDocument
                else:
                    msg = "A part can only be imported from a FreeCAD '*.fcstd' file"
                    QtGui.QMessageBox.information(  QtGui.QApplication.activeWindow(), "Value Error", msg )
                    return
            
            if importDoc==doc and partial==True:
                updateImportedParts(importDoc,True)
            else:
                updateImportedParts(importDoc)
                
            FreeCADGui.updateGui()
            importDoc.save()
            print(
                u"==== Assembly '{}' has been updated! =====".format(
                    importDoc.FileName
                    )
                )
            if importDoc != doc:
                FreeCAD.closeDocument(importDoc.Name)
            
        

    def GetResources(self):
        return {
            'Pixmap' : ':/icons/a2p_RecursiveUpdate.svg',
            'MenuText': 'update imports recursively',
            'ToolTip': toolTip
            }

FreeCADGui.addCommand('a2p_recursiveUpdateImportedPartsCommand', a2p_recursiveUpdateImportedPartsCommand())
            
    
            
            
