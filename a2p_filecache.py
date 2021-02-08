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
def createDefaultTopNames(obj): # used during converting an object to a2p object
    vertexNames = []
    edgeNames = []
    faceNames = []
    for i in range(0, len(obj.Shape.Vertexes) ):
        newName = "".join(('V;',str(i+1),';',obj.Name,';'))
        vertexNames.append(newName)
    for i in range(0, len(obj.Shape.Edges) ):
        newName = "".join(('E;',str(i+1),';',obj.Name,';'))
        edgeNames.append(newName)
    for i in range(0, len(obj.Shape.Faces) ):
        newName = "".join(('F;',str(i+1),';',obj.Name,';'))
        faceNames.append(newName)
    return vertexNames, edgeNames, faceNames
#==============================================================================
def muxAssemblyWithTopoNames(doc):
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
                       and a2plib.isGlobalVisible(obj)
                       ]
    
    transparency = 0
    shape_list = []
    
    for obj in visibleObjects:
        extendNames = False
        entry = None
        
        singleShapeRequested = hasattr(obj,"sourcePart") and obj.sourcePart is not None and len(obj.sourcePart)>0
        if singleShapeRequested:
            loadObjectInfo = obj.sourcePart
        else:
            loadObjectInfo = None
        
        if a2plib.to_bytes(obj.sourceFile) == b"converted":
            vertexNames,edgeNames,faceNames = createDefaultTopNames(obj)
            inputShape = obj.Shape 

        elif a2plib.getUseTopoNaming() and fileCache.loadObject(obj.sourceFile,loadObjectInfo):
            extendNames = True
            entry = fileCache.getFullEntry(obj)
            vertexNames = entry.vertexNames
            edgeNames = entry.edgeNames
            faceNames = entry.faceNames
            inputShape = entry.shape
        
        print(u"MuxAssembly: create muxInfo for {}".format(obj.Label))
        for i in range(0, len(inputShape.Vertexes) ):
            if extendNames:
                newName = "".join((vertexNames[i],obj.Name,';'))
                muxInfo.append(newName)
            else:
                newName = "".join(('V;',str(i+1),';',obj.Name,';'))
                muxInfo.append(newName)
        for i in range(0, len(inputShape.Edges) ):
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
        pl = tempShape.Placement
        obj.Shape = inputShape
        obj.Placement = pl
        tempShape = obj.Shape
        transparency = obj.ViewObject.Transparency
        shape_list.append(obj.Shape)

        # now start the loop with use of the stored values..(much faster)
        diffuseElement = a2plib.makeDiffuseElement(shapeCol,transparency)
        for i in range(0,len(tempShape.Faces)):
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
        filename, #the full path of the fcstd file from which a2p file has to be created
        singleShapeLabel,
        allwaysRecreate = False # used for migration purposes
        ):
    
    if filename is None or not os.path.exists(filename):
        print(u"Import error: File {} does not exist".format(filename))
        return
    
    singleShapeRequested = singleShapeLabel is not None and len(singleShapeLabel)>0

    if singleShapeRequested:
        a2pFileName = filename[:-6]+'-'+singleShapeLabel+'.a2p'
    else: # the normal case
        a2pFileName = filename+'.a2p' #replace .FCStd by .a2p
    
    if not allwaysRecreate:
        if not a2plib.getRecalculateImportedParts(): # always create a new file if recalculation is needed...
            importDocCreationTime = os.path.getmtime(filename)
            if os.path.exists( a2pFileName ):
                a2pFileCreationTime = os.path.getmtime( a2pFileName )
                if a2pFileCreationTime >= importDocCreationTime:
                    print("return existing a2p-file")
                    return a2pFileName # nothing to do...
    
    #Create a new a2p file
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
    
    if singleShapeRequested == False:
        importableObjects = topoMapper.getTopLevelObjects()
    else:
        importableObjects = topoMapper.getTopLevelObjects(allowSketches=True)
    
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
        if singleShapeRequested:
            muxInfo, Shape, DiffuseColor, transparency = topoMapper.createTopoNames(
                                                            desiredShapeLabel=singleShapeLabel
                                                            )
        else:
            muxInfo, Shape, DiffuseColor, transparency = topoMapper.createTopoNames()
        
    #if a step file has been imported, the importDoc is not saved...
    try:
        fTime = os.path.getmtime(importDoc.FileName)
        fName = importDoc.FileName
    except:
        fTime = os.path.getmtime(filename)
        fName = filename
        
    # setup xml information for a2p file
    xmlHandler = a2p_simpleXMLhandler.SimpleXMLhandler()
    xml = xmlHandler.createInformationXML(
        importDoc.Label,
        fName,
        fTime,
        subAssemblyImport,
        transparency
        )    

    if not importDocIsOpen:
        FreeCAD.closeDocument(importDoc.Name)
    zipFileName = a2plib.writeA2pFile(filename,a2pFileName,Shape,muxInfo,DiffuseColor,xml)
    
    
    
    return zipFileName
#==============================================================================
class FileCacheEntry():
    def __init__(
        self,
        sourcePartCreationTime,
        importDocFileName,
        vertexNames,
        edgeNames,
        faceNames,
        shape,
        diffuseColor
        ):
        self.sourcePartCreationTime = sourcePartCreationTime
        self.importDocFileName = importDocFileName
        self.vertexNames = vertexNames
        self.edgeNames = edgeNames
        self.faceNames = faceNames
        self.shape = shape
        self.diffuseColor = diffuseColor
        
#==============================================================================
class FileCache():
    def __init__(self):
        self.cache = {}
        
    def loadObject(self, sourceFile, sourcePart):
        
        '''
        if a2plib.to_bytes(sourceFile) == b'converted':
            return False
        '''
        
        #Search cache for entry, create an entry if there none is found            cacheKey = os.path.split(sourceFile)[1]
        singleShapeRequested = sourcePart is not None and len(sourcePart)>0


        fileName = sourceFile

        if singleShapeRequested:
            cacheKey = os.path.split(sourceFile)[1] + '-'+sourcePart
        else:
            cacheKey = os.path.split(sourceFile)[1]
            
        
        if not a2plib.getRecalculateImportedParts(): #always refresh cache if recalculation is needed
            cacheEntry = self.cache.get(cacheKey,None)
            if cacheEntry is not None:
                if os.path.exists(cacheEntry.importDocFileName):
                    sourceFileModificationTime = os.path.getmtime(cacheEntry.importDocFileName)
                    if cacheEntry.sourcePartCreationTime >=  sourceFileModificationTime:
                        #cache hit !
                        return True #entry found, nothing to do
        
        doc = FreeCAD.activeDocument()
        assemblyPath = os.path.normpath(os.path.split(doc.FileName)[0])
        fileNameWithinProjectFile = a2plib.findSourceFileInProject(fileName, assemblyPath)
        if fileNameWithinProjectFile == None:
            QtGui.QMessageBox.critical(
                QtGui.QApplication.activeWindow(),
                u"File error ! ",
                u"Cannot find {}".format(fileNameWithinProjectFile)
                )
            return False

        #A valid sourcefile is found, search for corresponding a2p-file
        if singleShapeRequested:
            zipFile = getOrCreateA2pFile(fileNameWithinProjectFile,sourcePart)
        else:
            zipFile = getOrCreateA2pFile(fileNameWithinProjectFile,None)
            
        if zipFile is None: 
            QtGui.QMessageBox.critical(
                QtGui.QApplication.activeWindow(),
                u"File error ! ",
                u"Cannot create a2p file for {}".format(fileNameWithinProjectFile)
                )
            return False
        
        #A valid a2p file exists, read it...
        content = a2plib.readA2pFile(zipFile)
    
        sourcePartCreationTime = float(content.properties["sourcePartCreationTime"])
        importDocFileName = content.properties["importDocFileName"]
        self.cache[cacheKey] = FileCacheEntry(
                                sourcePartCreationTime,
                                importDocFileName,
                                content.vertexNames,
                                content.edgeNames,
                                content.faceNames,
                                content.shape,
                                content.diffuseColor
                                )
        print(u"A2p added object {} to it's cache".format(cacheKey))
        print(u"size of a2p cache is: {} byte".format(a2plib.getMemSize(self.cache)))
        return True
        
    def getTopoName(self,obj,subName):
        if obj is None:
            return("")
        
        if obj.TypeId == 'Sketcher::SketchObject': return ""
        if obj.TypeId == 'Part::Part2DObjectPython': return ""
        
        # is there any single Shape requested
        ssr1 = obj.sourcePart is not None and len(obj.sourcePart)>0 
        ssr2 = obj.localSourceObject is not None and len(obj.localSourceObject)>0
        
        if ssr1: #SingleShapeRequested 1
            if not self.loadObject(obj.sourceFile, obj.sourcePart): return ""
            cacheKey = os.path.split(obj.sourceFile)[1] + '-'+obj.sourcePart
        elif ssr2: #SingleShapeRequested 2
            localObject = obj.Document.getObject(obj.localSourceObject)
            if not self.loadObject(obj.Document.FileName, localObject.Label): return ""
            cacheKey = os.path.split(obj.Document.FileName)[1] + '-'+localObject.Label
        else:
            if not self.loadObject(obj.sourceFile, None): return ""
            cacheKey = os.path.split(obj.sourceFile)[1]
        
        try:
            idx = a2plib.getSubelementIndex(subName)
            if subName.startswith("Vertex"):
                return self.cache[cacheKey].vertexNames[idx]
            elif subName.startswith("Edge"):
                return self.cache[cacheKey].edgeNames[idx]
            elif subName.startswith("Face"):
                return self.cache[cacheKey].faceNames[idx]
        except:
            return ""
        
        return "" #default if there are problems
        
    def getFullEntry(self,obj):
        #any single Shape requested
        sr1 = False
        sr2 = False
        try:
            sr1 = obj.sourcePart is not None and len(obj.sourcePart)>0
        except:
            pass 
        try:
            sr2 = obj.localSourceObject is not None and len(obj.localSourceObject)>0
        except:
            pass 

        if sr1:
            if not self.loadObject(obj.sourceFile, obj.sourcePart):
                return None
            cacheKey = os.path.split(obj.sourceFile)[1] + '-'+obj.sourcePart
        elif sr2:
            localObject = obj.Document.getObject(obj.localSourceObject)
            if not self.loadObject(obj.Document.FileName, localObject.Label):
                return None
            cacheKey = os.path.split(obj.Document.FileName)[1] + '-'+localObject.Label
        else:
            if not self.loadObject(obj.sourceFile, None):
                return None
            cacheKey = os.path.split(obj.sourceFile)[1]
        
        try:
            entry = self.cache[cacheKey]
        except:
            entry = None
        return entry
        
#==============================================================================
# The global cache of a2p-files
#==============================================================================
fileCache = FileCache()
#==============================================================================
        
