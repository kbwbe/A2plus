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
import Part
from PySide import QtGui
from PySide import QtCore
import os
import sys
import a2plib
import a2p_topomapper
import a2p_simpleXMLhandler



#==============================================================================
def muxAssemblyWithTopoNames(doc, desiredShapeLabel=None):
    '''
    Mux an a2p assembly

    combines all the a2p objects in the doc into one shape
    and populates muxinfo with a description of an edge or face.
    these descriptions are used later to retrieve the edges or faces...
    '''
    faces = []
    faceColors = []
    muxInfo = [] # List of keys, not used at moment...

    visibleObjects = [ obj for obj in doc.Objects
                       if hasattr(obj,'ViewObject') and obj.ViewObject.isVisible()
                       and hasattr(obj,'Shape') and len(obj.Shape.Faces) > 0
                       and hasattr(obj,'muxInfo')
                       ]
    
    if desiredShapeLabel: # is not None..
        tmp = []
        for ob in visibleObjects:
            if ob.Label == desiredShapeLabel:
                tmp.append(ob)
                break
        visibleObjects = tmp

    transparency = 0
    shape_list = []
    for obj in visibleObjects:
        extendNames = False
        if a2plib.getUseTopoNaming() and len(obj.muxInfo) > 0: # Subelement-Strings existieren schon...
            extendNames = True
            #
            vertexNames = []
            edgeNames = []
            faceNames = []
            #
            for item in obj.muxInfo:
                if item[0] == 'V': vertexNames.append(item)
                if item[0] == 'E': edgeNames.append(item)
                if item[0] == 'F': faceNames.append(item)

        if a2plib.getUseTopoNaming():
            for i in range(0, len(obj.Shape.Vertexes) ):
                if extendNames:
                    newName = "".join((vertexNames[i],obj.Name,';'))
                    muxInfo.append(newName)
                else:
                    newName = "".join(('V;',str(i+1),';',obj.Name,';'))
                    muxInfo.append(newName)
            for i in range(0, len(obj.Shape.Edges) ):
                if extendNames:
                    newName = "".join((edgeNames[i],obj.Name,';'))
                    muxInfo.append(newName)
                else:
                    newName = "".join(('E;',str(i+1),';',obj.Name,';'))
                    muxInfo.append(newName)

        # Save Computing time, store this before the for..enumerate loop later...
        needDiffuseColorExtension = ( len(obj.ViewObject.DiffuseColor) < len(obj.Shape.Faces) )
        shapeCol = obj.ViewObject.ShapeColor
        diffuseCol = obj.ViewObject.DiffuseColor
        tempShape = a2plib.makePlacedShape(obj)
        transparency = obj.ViewObject.Transparency
        shape_list.append(obj.Shape)

        # now start the loop with use of the stored values..(much faster)
        topoNaming = a2plib.getUseTopoNaming()
        diffuseElement = a2plib.makeDiffuseElement(shapeCol,transparency)
        for i in range(0,len(tempShape.Faces)):
            if topoNaming:
                if extendNames:
                    newName = "".join((faceNames[i],obj.Name,';'))
                    muxInfo.append(newName)
                else:
                    newName = "".join(('F;',str(i+1),';',obj.Name,';'))
                    muxInfo.append(newName)
            if needDiffuseColorExtension:
                faceColors.append(diffuseElement)

        if not needDiffuseColorExtension:
            faceColors.extend(diffuseCol)

        faces.extend(tempShape.Faces)

    #if len(faces) == 1:
    #    shell = Part.makeShell([faces])
    #else:
    #    shell = Part.makeShell(faces)
        
    shell = Part.makeShell(faces)
        
    try:
        if a2plib.getUseSolidUnion():
            if len(shape_list) > 1:
                shape_base=shape_list[0]
                shapes=shape_list[1:]
                solid = shape_base.fuse(shapes)
            else:
                solid = Part.Solid(shape_list[0])
        else:
            solid = Part.Solid(shell) # This does not work if shell includes spherical faces. FC-Bug ??
            # Fall back to shell if some faces are missing..
            if len(shell.Faces) != len(solid.Faces):
                solid = shell
    except:
        # keeping a shell if solid is failing
        FreeCAD.Console.PrintWarning('Union of Shapes FAILED\n')
        solid = shell

    # transparency could change to different values depending
    # on the order of imported objects
    # now set it to a default value
    # faceColors still contains the per face transparency values
    transparency = 0
    return muxInfo, solid, faceColors, transparency
#==============================================================================
def getOrCreateA2pFile(
        filename #the full path of the fcstd file which a2p file has to be created from
        ):
    
    if filename is None or not os.path.exists(filename):
        print(u"Import error: File {} does not exist".format(filename))
        return
    
    if not a2plib.getRecalculateImportedParts(): # always create a new file if recalculation is needed...
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
    
    # recalculate imported part if requested by preferences
    if a2plib.getRecalculateImportedParts():
        for ob in importDoc.Objects:
            ob.recompute()
        importDoc.save() # useless without saving...
    
    # Initialize the TopoMapper
    topoMapper = a2p_topomapper.TopoMapper(importDoc)

    # Get a list of the importable Objects
    importableObjects = topoMapper.getTopLevelObjects()
    
    if len(importableObjects) == 0:
        msg = "No visible Part to import found. Create no A2p-file.."
        QtGui.QMessageBox.information(
            QtGui.QApplication.activeWindow(),
            "Import Error",
            msg
            )
        return
    
    # Discover whether we are importing a subassembly or a single part
    subAssemblyImport = False
    if all([ 'importPart' in obj.Content for obj in importableObjects]) == 1:
        subAssemblyImport = True

    if subAssemblyImport:
        muxInfo, Shape, DiffuseColor, transparency = muxAssemblyWithTopoNames(importDoc)
    else:
        # TopoMapper manages import of non A2p-Files. It generates the shapes and appropriate topo names...
        muxInfo, Shape, DiffuseColor, transparency = topoMapper.createTopoNames()
        
    # setup xml information for a2p file
    xmlHandler = a2p_simpleXMLhandler.SimpleXMLhandler()
    xml = xmlHandler.createInformationXML(
        importDoc.Label,
        importDoc.FileName,
        os.path.getmtime(importDoc.FileName),
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
        
    def createOrUpdateEntry(self,cacheKey, obj):
        #Search cache for entry
        fileName = obj.sourceFile
        
        if not a2plib.getRecalculateImportedParts(): #always refresh cache if recalculation is needed
            cacheEntry = self.cache.get(cacheKey,None)
            if cacheEntry is not None:
                if os.path.exists(cacheEntry[1]):
                    sourceFileModificationTime = os.path.getmtime(cacheEntry[1])
                    if cacheEntry[0] >=  sourceFileModificationTime:
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
        print(u"fileNameWithinProjectFile: {}".format(fileNameWithinProjectFile))
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
        importDocFileName = properties["importDocFileName"]
        self.cache[cacheKey] = (sourcePartCreationTime,
                                importDocFileName,
                                vertexNames,
                                edgeNames,
                                faceNames,
                                shape,
                                diffuseColor
                                )
        print(u"file loaded to cache")
        print(u"size of cache is: {}".format(a2plib.getMemSize(self.cache)))
        
    def getSubelementIndex(self,subName):
        idxString = ""
        for c in subName:
            if c in ["0","1","2","3","4","5","6","7","8","9"]:
                idxString+=c
        return int(idxString)-1
        
    def getTopoName(self,obj,subName):
        # No toponaming for import of single shapes
        # Single Shape references have been removed for next time
        if obj.sourcePart is not None and len(obj.sourcePart)>0: 
            return ""
        cacheKey = os.path.split(obj.sourceFile)[1]
        self.createOrUpdateEntry(cacheKey, obj)
        try:
            if subName.startswith("Vertex"):
                names = self.cache[cacheKey][2]
                idx = self.getSubelementIndex(subName)
                return names[idx]
            elif subName.startswith("Edge"):
                names = self.cache[cacheKey][3]
                idx = self.getSubelementIndex(subName)
                return names[idx]
            elif subName.startswith("Face"):
                names = self.cache[cacheKey][4]
                idx = self.getSubelementIndex(subName)
                return names[idx]
        except:
            return ""
        return "" #default if there are problems
        
    def getFullEntry(self,obj):
        print(u"getFullEntry of {}".format(obj.Label))
        # No toponaming for import of single shapes
        # Single Shape references have been removed for next time
        if obj.sourcePart is not None and len(obj.sourcePart)>0: 
            return ""
        cacheKey = os.path.split(obj.sourceFile)[1]
        print(u"cacheKey ={}".format(cacheKey))
        self.createOrUpdateEntry(cacheKey, obj)
        entry = self.cache[cacheKey]
        return (
            entry[0],
            entry[1],
            entry[2],
            entry[3],
            entry[4],
            entry[5],
            entry[6]
            )
        #end of return!
        
fileCache = FileCache()
#==============================================================================
        
