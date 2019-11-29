#***************************************************************************
#*                                                                         *
#*   Copyright (c) 2019 kbwbe                                              *
#*                                                                         *
#*   Portions of code based on hamish's assembly 2                         *
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

import FreeCAD
import FreeCADGui
from PySide import QtGui
from PySide import QtCore
import os
import a2plib
import a2p_topomapper
import a2p_simpleXMLhandler
from a2p_MuxAssembly import muxAssemblyWithTopoNames


#==============================================================================
def getOrCreateA2pFile(
        filename
        ):
    
    if filename is None or not os.path.exists(filename):
        print(u"Import error: File {} does not exist".format(filename))
        return
    
    if not a2plib.getRecalculateImportedParts(): # always create a new file if recalc is needed...
        if filename != None and os.path.exists(filename):
            importDocCreationTime = os.path.getmtime(filename)
            a2pFileName = filename+'.a2p'
            if os.path.exists( a2pFileName ):
                a2pFileCreationTime = os.path.getmtime( a2pFileName )
                if a2pFileCreationTime >= importDocCreationTime:
                    print ("Found existing a2p file")
                    return a2pFileName # nothing to do...
    
    print ("Create a new a2p file")
    importDoc,importDocIsOpen = a2plib.openImportDocFromFile(filename)
    if importDoc is None: return #nothing found
    
    #-------------------------------------------
    # recalculate imported part if requested by preferences
    # This can be useful if the imported part depends on an
    # external master-spreadsheet
    #-------------------------------------------
    if a2plib.getRecalculateImportedParts():
        for ob in importDoc.Objects:
            ob.recompute()
        importDoc.save() # useless without saving...
    
    #-------------------------------------------
    # Initialize the TopoMapper
    #-------------------------------------------
    topoMapper = a2p_topomapper.TopoMapper(importDoc)

    #-------------------------------------------
    # Get a list of the importable Objects
    #-------------------------------------------
    importableObjects = topoMapper.getTopLevelObjects()
    
    if len(importableObjects) == 0:
        msg = "No visible Part to import found. Create no A2p-file.."
        QtGui.QMessageBox.information(
            QtGui.QApplication.activeWindow(),
            "Import Error",
            msg
            )
        return
    
    #-------------------------------------------
    # Discover whether we are importing a subassembly or a single part
    #-------------------------------------------
    subAssemblyImport = False
    if all([ 'importPart' in obj.Content for obj in importableObjects]) == 1:
        subAssemblyImport = True

    if subAssemblyImport:
        muxInfo, Shape, DiffuseColor, transparency = muxAssemblyWithTopoNames(importDoc)
    else:
        # TopoMapper manages import of non A2p-Files. It generates the shapes and appropriate topo names...
        muxInfo, Shape, DiffuseColor, transparency = topoMapper.createTopoNames()
        
    #-------------------------------------------
    # setup xml information for a2p file
    #-------------------------------------------
    xmlHandler = a2p_simpleXMLhandler.SimpleXMLhandler()
    xml = xmlHandler.createInformationXML(
        importDoc.Label,
        os.path.getmtime(filename),
        subAssemblyImport,
        transparency
        )    

    if not importDocIsOpen:
        FreeCAD.closeDocument(importDoc.Name)
    zipFileName = a2plib.writeA2pFile(filename,Shape,muxInfo,DiffuseColor,xml)
    return zipFileName
#==============================================================================
class FileCache():
    def __init__(self):
        self.cache = {}
        
    def load(self,fileName, objectTimeStamp):
        #Search cache for entry
        cacheKey = os.path.split(fileName)[1]
        cacheEntry = self.cache.get(cacheKey,None)
        if cacheEntry is not None:
            if cacheEntry[0] >= objectTimeStamp:
                print(u"cache hit!")
                return #entry found, nothing to do
        
        doc = FreeCAD.activeDocument()
        assemblyPath = os.path.normpath(os.path.split(doc.FileName)[0])
        fileNameWithinProjectFile = a2plib.findSourceFileInProject(fileName, assemblyPath)
        if fileNameWithinProjectFile == None:
            QtGui.QMessageBox.critical(
                QtGui.QApplication.activeWindow(),
                u"File error ! ",
                u"Cannot find {}".format(fileNameWithinProjectFile)
                )
            return

        #A valid sourcefile is found, search for corresponding a2p-file
        zipFile = getOrCreateA2pFile(fileNameWithinProjectFile)
        if zipFile is None: 
            QtGui.QMessageBox.critical(
                QtGui.QApplication.activeWindow(),
                u"File error ! ",
                u"Cannot create a2p file for {}".format(fileNameWithinProjectFile)
                )
            return
        
        #A valid a2p file exists, read it...
        shape, vertexNames, edgeNames, faceNames, diffuseColor, properties = \
            a2plib.readA2pFile(zipFile)
        sourcePartCreationTime = float(properties["sourcePartCreationTime"])
        self.cache[cacheKey] = (sourcePartCreationTime,
                                vertexNames,
                                edgeNames,
                                faceNames
                                )
        print(u"file loaded to cache")
        
    def getSubelementIndex(self,subName):
        idxString = ""
        for c in subName:
            if c in ["0","1","2","3","4","5","6","7","8","9"]:
                idxString+=c
        return int(idxString)-1
        
    def getTopoName(self,obj,subName):
        print("Enter getTopoName()")
        # No toponaming for import of single shapes for now...
        if obj.sourcePart is not None and len(obj.sourcePart)>0: 
            return ""
        cacheKey = os.path.split(obj.sourceFile)[1]
        objectTimeStamp = obj.timeLastImport
        self.load(cacheKey,objectTimeStamp)
        try:
            if subName.startswith("Vertex"):
                names = self.cache[cacheKey][1]
                idx = self.getSubelementIndex(subName)
                return names[idx]
            elif subName.startswith("Edge"):
                names = self.cache[cacheKey][2]
                idx = self.getSubelementIndex(subName)
                return names[idx]
            elif subName.startswith("Face"):
                names = self.cache[cacheKey][3]
                idx = self.getSubelementIndex(subName)
                return names[idx]
        except:
            return ""
        return "" #default if there are problems
        
fileCache = FileCache()
#==============================================================================
        
