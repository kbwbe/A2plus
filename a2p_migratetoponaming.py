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
import a2p_filecache
from a2p_importpart import migrateImportedParts
#from a2p_fcdocumentreader import FCdocumentReader
from a2p_simpleXMLreader import FCdocumentReader


#==============================================================================
def createMigrationFileList(
            importPath,
            parentAssemblyDir,
            filesToUpdate,
            allSourceFiles,
            recursive=False
            ):
    
    # do not update converted parts
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
            continue
        
        #if ob.isSubassembly() and recursive:
        if recursive:
            subAsmNeedsUpdate, filesToUpdate, allSourceFiles = createMigrationFileList(
                                                                ob.getA2pSource(),
                                                                workingDir,
                                                                filesToUpdate,
                                                                allSourceFiles,
                                                                recursive
                                                                )
        needToUpdate = True
        #needToUpdate = subAsmNeedsUpdate
        
        sourceInProject = a2plib.findSourceFileInProject(
            ob.getA2pSource(),
            parentAssemblyDir
            )
        
        if sourceInProject not in allSourceFiles:
            allSourceFiles.append(sourceInProject)
        
            
    if needToUpdate:
        if fileNameInProject not in filesToUpdate:
            filesToUpdate.append(fileNameInProject)
        
    return needToUpdate, filesToUpdate, allSourceFiles
#==============================================================================
toolTip = \
'''
Migrate to new toponaming
recursively over all subassemblies.
'''


class a2p_recursiveToponamingMigrationCommand:

    def Activated(self):
        a2plib.setAutoSolve(True) # makes no sense without autosolve = ON
        doc = FreeCAD.activeDocument()
        fileName = doc.FileName
        workingDir,basicFileName = os.path.split(fileName)
        
        a2p_filecache.fileCache.cache = {}
        
        filesToUpdate = []
        allSourceFiles = []
        subAsmNeedsUpdate, filesToUpdate, allSourceFiles = createMigrationFileList(
                                                            fileName,
                                                            workingDir,
                                                            filesToUpdate,
                                                            allSourceFiles,
                                                            True
                                                            )

        for f in allSourceFiles:
            try:
                os.remove(f+'.a2p')
                print(u"removed '{}' file".format(f+'.a2p'))
            except:
                pass
        
        print("=================")
        for f in allSourceFiles:
            print(u"create a2p file for '{}'".format(f))
            a2p_filecache.getOrCreateA2pFile(f, True) #recrecate Mode
        print("=================")
        print("Assemblies to be updated..")
        for f in filesToUpdate:
            print(f)
        print("=================")
        

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
                    ImportGui.insert(fname,newname)
                    importDoc = FreeCAD.ActiveDocument
                else:
                    msg = "A part can only be imported from a FreeCAD '*.fcstd' file"
                    QtGui.QMessageBox.information(  QtGui.QApplication.activeWindow(), "Value Error", msg )
                    return
            
            migrateImportedParts(importDoc)
            FreeCADGui.updateGui()
            importDoc.save()
            print(
                u"==== Assembly '{}' has been migrated! =====".format(
                    importDoc.FileName
                    )
                )
            if importDoc != doc:
                FreeCAD.closeDocument(importDoc.Name)
            
        

    def GetResources(self):
        return {
            #'Pixmap' : ':/icons/a2p_RecursiveUpdate.svg',
            'MenuText': 'migrate to new toponaming recursively',
            'ToolTip': toolTip
            }

FreeCADGui.addCommand('a2p_recursiveToponamingMigrationCommand', a2p_recursiveToponamingMigrationCommand())
            
    
            
            
