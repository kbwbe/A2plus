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
            assembliesToUpdate,
            baseSourceFiles,
            ):
    
    # do not update converted parts
    if a2plib.to_bytes(importPath) == b'converted':
        return assembliesToUpdate, baseSourceFiles #stop recursion here
    
    fileNameInProject = a2plib.findSourceFileInProject(
        importPath,
        parentAssemblyDir
        )
    workingDir,basicFileName = os.path.split(fileNameInProject)
    docReader1 = FCdocumentReader()
    
    docReader1.openDocument(fileNameInProject)
    needToUpdate = False
    subAsmNeedsUpdate = False
    a2pObs = docReader1.getA2pObjects()
    
    if len(a2pObs) == 0: #this seems to be a basic input file, it is no assembly
        if fileNameInProject not in baseSourceFiles:
            baseSourceFiles.append(fileNameInProject)
        return assembliesToUpdate, baseSourceFiles #stop recursion here
    
    for ob in a2pObs:
        if a2plib.to_bytes(ob.getA2pSource()) == b'converted':
            continue
        
        assembliesToUpdate, baseSourceFiles = createMigrationFileList(
                                                    ob.getA2pSource(),
                                                    workingDir,
                                                    assembliesToUpdate,
                                                    baseSourceFiles
                                                    )
    if fileNameInProject not in assembliesToUpdate:
        assembliesToUpdate.append(fileNameInProject)
        
    return assembliesToUpdate, baseSourceFiles
#==============================================================================
toolTip = \
'''
Migrate to new toponaming
recursively over all subassemblies.
'''


class a2p_recursiveToponamingMigrationCommand:

    def Activated(self):
        doc = FreeCAD.activeDocument()
        fileName = doc.FileName
        workingDir,basicFileName = os.path.split(fileName)
        
        a2p_filecache.fileCache.cache = {}
        
        assembliesToUpdate = []
        baseSourceFiles = []
        assembliesToUpdate, baseSourceFiles = createMigrationFileList(
                                                    fileName,
                                                    workingDir,
                                                    assembliesToUpdate,
                                                    baseSourceFiles
                                                    )
        allFiles = baseSourceFiles + assembliesToUpdate


        print("=================")
        for f in allFiles:
            try:
                os.remove(f+'.a2p')
                print(u"removed '{}' file".format(f+'.a2p'))
            except:
                pass
        print("=================")
        for f in baseSourceFiles: # this are the basic parts, no one is an assembly
            print(u"create a2p file for '{}'".format(f))
            a2p_filecache.fileCache.loadObject(f) #recent version of part should be in cache now
        print("=================")
        print("Assemblies to be updated..")
        for f in assembliesToUpdate:
            print(f)
        print("=================")
        
        for f in assembliesToUpdate:
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
                else:
                    msg = "A part can only be imported from a FreeCAD '*.fcstd' file"
                    QtGui.QMessageBox.information(  QtGui.QApplication.activeWindow(), "Value Error", msg )
                    return
            
            migrateImportedParts(importDoc)
            FreeCADGui.updateGui()
            importDoc.save()
            a2p_filecache.fileCache.loadObject(f) #create A2p file and load it to cache
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
            
    
            
            
