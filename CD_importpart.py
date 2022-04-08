#***************************************************************************
#*                                                                         *
#*   Copyright (c) 2018 kbwbe                                              *
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

import FreeCADGui,FreeCAD
from PySide import QtGui, QtCore
import os
import os.path
import sys
import platform
import a2plib
from a2p_MuxAssembly import muxAssemblyWithTopoNames
from a2p_versionmanagement import A2P_VERSION
from a2plib import getRelativePathesEnabled

from a2p_topomapper import (
    TopoMapper
    )
import a2p_lcs_support
from a2p_importedPart_class import Proxy_importPart, ImportedPartViewProviderProxy
import a2p_constraintServices

PYVERSION = sys.version_info[0]

#==============================================================================
class DataContainer():
    def __init__(self):
        self.tx = None
##==============================================================================
class ObjectCache:
    '''
    An assembly could use multiple instances of then same importPart.
    Cache them here so fileImports have to be executed only one time...
    '''
    def __init__(self):
        self.objects = {} # dict, key = fileName, val = object

    def cleanUp(self,doc):
        for key in self.objects.keys():
            try:
                doc.removeObject(self.objects[key].Name) #remove temporaryParts from doc
            except:
                pass
        self.objects = {} # dict, key = fileName

    def add(self,fileName,obj): # pi_obj = PartInformation-Object
        self.objects[fileName] = obj

    def get(self,fileName):
        obj = self.objects.get(fileName,None)
        if obj:
            return obj
        else:
            return None

    def isCached(self,fileName):
        if fileName in self.objects.keys():
            return True
        else:
            return False

    def len(self):
        return len(self.objects.keys())

objectCache = ObjectCache()

def importPartFromFile(
        _doc,
        filename,
        extractSingleShape = False, # load only a single user defined shape from file
        desiredShapeLabel = None,
        importToCache = False,
        cacheKey = ""
        ):
    doc = _doc
    #-------------------------------------------
    # Get the importDocument
    #-------------------------------------------
    
    # look only for filenames, not paths, as there are problems on WIN10 (Address-translation??)
    importDoc = None
    importDocIsOpen = False
    requestedFile = os.path.split(filename)[1]
    for d in FreeCAD.listDocuments().values():
        recentFile = os.path.split(d.FileName)[1]
        if requestedFile == recentFile:
            importDoc = d # file is already open...
            importDocIsOpen = True
            break

    if not importDocIsOpen:
        if filename.lower().endswith('.fcstd'):
            importDoc = FreeCAD.openDocument(filename)
        elif filename.lower().endswith('.stp') or filename.lower().endswith('.step'):
            import ImportGui
            fname = os.path.splitext(os.path.basename(filename))[0]
            FreeCAD.newDocument(fname)
            newname = FreeCAD.ActiveDocument.Name
            FreeCAD.setActiveDocument(newname)
            ImportGui.insert(filename, newname)
            importDoc = FreeCAD.ActiveDocument
        else:
            msg = "A part can only be imported from a FreeCAD '*.FCStd' file"
            QtGui.QMessageBox.information( QtGui.QApplication.activeWindow(), "Value Error", msg )
            return

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
    # Initialize the new TopoMapper
    #-------------------------------------------
    topoMapper = TopoMapper(importDoc)

    #-------------------------------------------
    # Get a list of the importable Objects
    #-------------------------------------------
    importableObjects = topoMapper.getTopLevelObjects(allowSketches = True)
    
    if len(importableObjects) == 0:
        msg = "No visible Part to import found. Aborting operation"
        QtGui.QMessageBox.information(
            QtGui.QApplication.activeWindow(),
            "Import Error",
            msg
            )
        return
    
    #-------------------------------------------
    # if only one single shape of the importdoc is wanted..
    #-------------------------------------------
    labelList = []
    dc = DataContainer()
    
    if extractSingleShape:
        if desiredShapeLabel is None: # ask for a shape label
            for io in importableObjects:
                labelList.append(io.Label)
            dialog = a2p_shapeExtractDialog(
                QtGui.QApplication.activeWindow(),
                labelList,
                dc)
            dialog.exec_()
            if dc.tx is None:
                msg = "Import of a shape reference aborted by user"
                QtGui.QMessageBox.information(
                    QtGui.QApplication.activeWindow(),
                    "Import Error",
                    msg
                    )
                return
        else: # use existent shape label
            dc.tx = desiredShapeLabel
            
    #-------------------------------------------
    # Discover whether we are importing a subassembly or a single part
    #-------------------------------------------
    subAssemblyImport = False
    if all([ 'importPart' in obj.Content for obj in importableObjects]) == 1:
        subAssemblyImport = True
        
    #-------------------------------------------
    # create new object
    #-------------------------------------------
    if importToCache:
        partName = 'CachedObject_'+str(objectCache.len())
        newObj = doc.addObject("Part::FeaturePython", partName)
        newObj.Label = partName
    else:
        partName = a2plib.findUnusedObjectName( importDoc.Label, document = doc )
        if extractSingleShape == False:
            partLabel = a2plib.findUnusedObjectLabel( importDoc.Label, document = doc )
        else:
            partLabel = a2plib.findUnusedObjectLabel(
                importDoc.Label,
                document = doc,
                extension = dc.tx
                )
        if PYVERSION < 3:
            newObj = doc.addObject( "Part::FeaturePython", partName.encode('utf-8') )
        else:
            newObj = doc.addObject( "Part::FeaturePython", str(partName.encode('utf-8')) ) # works on Python 3.6.5
        newObj.Label = partLabel

    Proxy_importPart(newObj)
    if FreeCAD.GuiUp:
        ImportedPartViewProviderProxy(newObj.ViewObject)

    newObj.a2p_Version = A2P_VERSION
    assemblyPath = os.path.normpath(os.path.split(doc.FileName)[0])
    absPath = os.path.normpath(filename)
    if getRelativePathesEnabled():
        if platform.system() == "Windows":
            prefix = '.\\'
        else:
            prefix = './'
        relativePath = prefix+os.path.relpath(absPath, assemblyPath)
        newObj.sourceFile = relativePath
    else:
        newObj.sourceFile = absPath
        
    if dc.tx is not None:
        newObj.sourcePart = dc.tx
    
    newObj.setEditorMode("timeLastImport", 1)
    newObj.timeLastImport = os.path.getmtime( filename )
    if a2plib.getForceFixedPosition():
        newObj.fixedPosition = True
    else:
        newObj.fixedPosition = not any([i.fixedPosition for i in doc.Objects if hasattr(i, 'fixedPosition') ])
    newObj.subassemblyImport = subAssemblyImport
    newObj.setEditorMode("subassemblyImport", 1)

    if subAssemblyImport:
        if extractSingleShape:
            newObj.muxInfo, newObj.Shape, newObj.ViewObject.DiffuseColor, newObj.ViewObject.Transparency = \
                muxAssemblyWithTopoNames(importDoc,desiredShapeLabel = dc.tx)
        else:
            newObj.muxInfo, newObj.Shape, newObj.ViewObject.DiffuseColor, newObj.ViewObject.Transparency = \
                muxAssemblyWithTopoNames(importDoc)
    else:
        # TopoMapper manages import of non A2p-Files. It generates the shapes and appropriate topo names...
        if extractSingleShape:
            newObj.muxInfo, newObj.Shape, newObj.ViewObject.DiffuseColor, newObj.ViewObject.Transparency = \
                topoMapper.createTopoNames(desiredShapeLabel = dc.tx)
        else:
            newObj.muxInfo, newObj.Shape, newObj.ViewObject.DiffuseColor, newObj.ViewObject.Transparency = \
                topoMapper.createTopoNames()
    
    newObj.objectType = 'a2pPart'
    if extractSingleShape == True:
        if a2plib.isA2pSketch(newObj):
            newObj.objectType = 'a2pSketch'
    newObj.setEditorMode("objectType", 1)

    doc.recompute()

    if importToCache: # this import is used to update already imported parts
        objectCache.add(cacheKey , newObj)
    else: # this is a first time import of a part
        if not a2plib.getPerFaceTransparency():
            # turn of perFaceTransparency by accessing ViewObject.Transparency and set to zero (non transparent)
            newObj.ViewObject.Transparency = 1
            newObj.ViewObject.Transparency = 0 # import assembly first time as non transparent.


    lcsList = a2p_lcs_support.getListOfLCS(doc, importDoc)
    

    if not importDocIsOpen:
        FreeCAD.closeDocument(importDoc.Name)

    if len(lcsList) > 0:
        #=========================================
        # create a group containing imported LCS's
        lcsGroupObjectName = 'LCS_Collection'
        lcsGroupLabel = 'LCS_Collection'
        
        if PYVERSION < 3:
            lcsGroup = doc.addObject( "Part::FeaturePython", lcsGroupObjectName.encode('utf-8') )
        else:
            lcsGroup = doc.addObject( "Part::FeaturePython", str(lcsGroupObjectName.encode('utf-8')) )    # works on Python 3.6.5
        lcsGroup.Label = lcsGroupLabel
    
        a2p_lcs_support.LCS_Group(lcsGroup)
        a2p_lcs_support.VP_LCS_Group(lcsGroup.ViewObject)
        
        for lcs in lcsList:
            lcsGroup.addObject(lcs)
        
        lcsGroup.Owner = newObj.Name
        
        newObj.addProperty("App::PropertyLinkList", "lcsLink", "importPart").lcsLink = lcsGroup
        newObj.Label = newObj.Label # this is needed to trigger an update
        lcsGroup.Label = lcsGroup.Label
    
        #=========================================

    return newObj






def updateImportedParts(doc, partial = False):  #changed to true Dan
    if doc is None:
        QtGui.QMessageBox.information(  
                        QtGui.QApplication.activeWindow(),
                        "No active document found!",
                        "Before updating parts, you have to open an assembly file."
                        )
        return
        
    doc.openTransaction("updateImportParts")
    objectCache.cleanUp(doc)
    
    
    selectedObjects = []
    selection = [s for s in FreeCADGui.Selection.getSelection() 
                 if s.Document == FreeCAD.ActiveDocument and
                 (a2plib.isA2pPart(s) or a2plib.isA2pSketch())
                 ]
    if selection and len(selection)>0:
        if partial == True:
            response = QtGui.QMessageBox.Yes
        else:
            flags = QtGui.QMessageBox.StandardButton.Yes | QtGui.QMessageBox.StandardButton.No
            msg = u"Do you want to update only the selected parts?"
            response = QtGui.QMessageBox.information(
                            QtGui.QApplication.activeWindow(),
                            u"ASSEMBLY UPDATE",
                            msg,
                            flags
                            )
        if response == QtGui.QMessageBox.Yes:
            for s in selection:
                selectedObjects.append(s)
    
    if len(selectedObjects) >0:
        workingSet = selectedObjects
    else:
        workingSet = doc.Objects
    
    for obj in workingSet:
        if hasattr(obj, 'sourceFile') and a2plib.to_str(obj.sourceFile) != a2plib.to_str('converted'):

            
            #repair data structures (perhaps an old Assembly2 import was found)
            if hasattr(obj, "Content") and 'importPart' in obj.Content: # be sure to have an assembly object
                if obj.Proxy is None:
                    #print (u"Repair Proxy of: {}, Proxy: {}".format(obj.Label, obj.Proxy))
                    Proxy_importPart(obj)
                    ImportedPartViewProviderProxy(obj.ViewObject)
                    
            assemblyPath = os.path.normpath(os.path.split(doc.FileName)[0])
            absPath = a2plib.findSourceFileInProject(obj.sourceFile, assemblyPath)

            if absPath is None:
                QtGui.QMessageBox.critical(QtGui.QApplication.activeWindow(),
                                            u"Source file not found",
                                            u"Unable to find {}".format(
                                                obj.sourceFile
                                                )
                                        )
            if absPath != None and os.path.exists( absPath ):
                newPartCreationTime = os.path.getmtime( absPath )
                if ( 
                    newPartCreationTime > obj.timeLastImport or
                    obj.a2p_Version != A2P_VERSION or
                    a2plib.getRecalculateImportedParts() # open always all parts as they could depend on spreadsheets
                    ):
                    cacheKeyExtension = obj.sourcePart
                    if cacheKeyExtension is None:
                        cacheKeyExtension = "AllShapes"
                    elif cacheKeyExtension == "":
                        cacheKeyExtension = "AllShapes"
                    cacheKeyExtension = '-' + cacheKeyExtension
                    cacheKey = absPath+cacheKeyExtension
                        
                    if not objectCache.isCached(cacheKey): # Load every changed object one time to cache
                        if obj.sourcePart is not None and obj.sourcePart != '':
                            importPartFromFile(
                                doc,
                                absPath,
                                importToCache = True,
                                cacheKey = cacheKey,
                                extractSingleShape = True,
                                desiredShapeLabel = obj.sourcePart
                                ) # the version is now in the cache
                        else:
                            importPartFromFile(
                                doc,
                                absPath,
                                importToCache = True,
                                cacheKey = cacheKey
                                ) # the version is now in the cache
                        
                    newObject = objectCache.get(cacheKey)
                    obj.timeLastImport = newPartCreationTime
                    if hasattr(newObject, 'a2p_Version'):
                        obj.a2p_Version = A2P_VERSION
                    importUpdateConstraintSubobjects( doc, obj, newObject ) # do this before changing shape and mux
                    #if hasattr(newObject, 'muxInfo'):
                    # obj.muxInfo = newObject.muxInfo
                    # save Placement because following newObject.Shape.copy() isn't resetting it to zeroes...
                    savedPlacement = obj.Placement
                    obj.Shape = newObject.Shape.copy()
                    if a2plib.isA2pSketch(obj):
                        pass
                    else:
                        obj.Placement = savedPlacement # restore the old placement
                    a2plib.copyObjectColors(obj, newObject)

    #repair constraint directions if for e.g. face-normals flipped around during updating of parts.
    a2p_constraintServices.redAdjustConstraintDirections(doc)

    mw = FreeCADGui.getMainWindow()
    mdi = mw.findChild(QtGui.QMdiArea)
    sub = mdi.activeSubWindow()
    if sub != None:
        sub.showMaximized()
    objectCache.cleanUp(doc) 
    doc.recompute()
    doc.commitTransaction()


def importUpdateConstraintSubobjects( doc, oldObject, newObject ):
    if not a2plib.getUseTopoNaming(): return
    
    # return if there are no constraints linked to the object 
    if len([c for c in doc.Objects if 'ConstraintInfo' in c.Content and oldObject.Name in [c.Object1, c.Object2] ]) == 0:
        return
    # check, whether object is an assembly with muxInformations.
    # Then find edgenames with mapping in muxinfo...
    deletionList = [] #for broken constraints
    if hasattr(oldObject, 'muxInfo'):
        if hasattr(newObject, 'muxInfo'):
            #
            oldVertexNames = []
            oldEdgeNames = []
            oldFaceNames = []
            for item in oldObject.muxInfo:
                if item[:1] == 'V':
                    oldVertexNames.append(item)
                if item[:1] == 'E':
                    oldEdgeNames.append(item)
                if item[:1] == 'F':
                    oldFaceNames.append(item)
            #
            newVertexNames = []
            newEdgeNames = []
            newFaceNames = []
            for item in newObject.muxInfo:
                if item[:1] == 'V':
                    newVertexNames.append(item)
                if item[:1] == 'E':
                    newEdgeNames.append(item)
                if item[:1] == 'F':
                    newFaceNames.append(item)
            #
            partName = oldObject.Name
            for c in doc.Objects:
                if 'ConstraintInfo' in c.Content:
                    if partName == c.Object1:
                        SubElement = "SubElement1"
                    elif partName == c.Object2:
                        SubElement = "SubElement2"
                    else:
                        SubElement = None
                        
                    if SubElement: #same as subElement <> None
                        
                        subElementName = getattr(c, SubElement)
                        if subElementName[:4] == 'Face':
                            try:
                                oldIndex = int(subElementName[4:])-1
                                oldConstraintString = oldFaceNames[oldIndex]
                                newIndex = newFaceNames.index(oldConstraintString)
                                newSubElementName = 'Face'+str(newIndex+1)
                            except:
                                newIndex = -1
                                newSubElementName = 'INVALID'
                                
                        elif subElementName[:4] == 'Edge':
                            try:
                                oldIndex = int(subElementName[4:])-1
                                oldConstraintString = oldEdgeNames[oldIndex]
                                newIndex = newEdgeNames.index(oldConstraintString)
                                newSubElementName = 'Edge'+str(newIndex+1)
                            except:
                                newIndex = -1
                                newSubElementName = 'INVALID'
                                
                        elif subElementName[:6] == 'Vertex':
                            try:
                                oldIndex = int(subElementName[6:])-1
                                oldConstraintString = oldVertexNames[oldIndex]
                                newIndex = newVertexNames.index(oldConstraintString)
                                newSubElementName = 'Vertex'+str(newIndex+1)
                            except:
                                newIndex = -1
                                newSubElementName = 'INVALID'
                                
                        else:
                            newIndex = -1
                            newSubElementName = 'INVALID'
                        
                        if newIndex >= 0:
                            setattr(c, SubElement, newSubElementName )
                            print (
                                    "oldConstraintString (KEY) : {}".format(
                                    oldConstraintString
                                    )
                                   )
                            print ("Updating by SubElement-Map: {} => {} ".format(
                                       subElementName, newSubElementName
                                       )
                                   )
                            continue
                        #
                        # if code coming here, constraint is broken
                        if c.Name not in deletionList:
                            deletionList.append(c.Name)
                            
    
    if len(deletionList) > 0: # there are broken constraints..
        for cName in deletionList:
        
            flags = QtGui.QMessageBox.StandardButton.Yes | QtGui.QMessageBox.StandardButton.Abort
            message = "Constraint %s is broken. Delete constraint? Otherwise check for wrong linkage." % cName
            response = QtGui.QMessageBox.critical(None, "Broken Constraint", message, flags )
        
            if response == QtGui.QMessageBox.Yes:
                FreeCAD.Console.PrintError("Removing constraint %s" % cName)
                c = doc.getObject(cName)
                a2plib.removeConstraint(c)
                
