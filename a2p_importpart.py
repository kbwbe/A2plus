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
import os, copy, time, sys
import a2plib
from a2p_MuxAssembly import muxObjectsWithKeys, createTopoInfo, Proxy_muxAssemblyObj
from a2p_viewProviderProxies import *
from a2p_versionmanagement import SubAssemblyWalk, A2P_VERSION
import a2p_solversystem
from a2plib import (
    appVersionStr,
    AUTOSOLVE_ENABLED
    )

PYVERSION =  sys.version_info[0]

class ObjectCache:
    '''
    An assembly could use multiple instances of then same importPart.
    Cache them here so fileImports have to be executed only one time...
    '''
    def __init__(self):
        self.objects = {} # dict, key=fileName, val=object

    def cleanUp(self,doc):
        for key in self.objects.keys():
            try:
                doc.removeObject(self.objects[key].Name) #remove temporaryParts from doc
            except:
                pass
        self.objects = {} # dict, key=fileName

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

def globalVisibility(doc, imp):
    if not imp.InList:
        return imp.ViewObject.Visibility
    else:
        for parent in imp.InList:
            if not parent.ViewObject.Visibility:
               return parent.ViewObject.Visibility
            else:
               return globalVisibility(doc, parent)

def getImpPartsFromDoc(doc, visibleOnly = True):
    objsIn = doc.Objects
    impPartsOut = list()
    for obj in objsIn:
        impPartList = filterImpParts(obj)
        if (impPartList):
            if (visibleOnly):
                vizParts = list()
                for imp in impPartList:
                    if imp.isDerivedFrom("PartDesign::Body"):
                        if hasattr(imp,'ViewObject') and imp.ViewObject.isVisible() and \
                           hasattr(imp.Tip,'ViewObject') and imp.Tip.ViewObject.isVisible():
                            gv = globalVisibility(doc, imp)
                            if gv: 
                                vizParts.append(imp)
                    else: 
                        if hasattr(imp,'ViewObject') and imp.ViewObject.isVisible():
                            gv = globalVisibility(doc, imp)
                            if gv: 
                                vizParts.append(imp)
                impPartsOut.extend(vizParts)
            else:
                impPartsOut.extend(impPartList)
    return impPartsOut

def filterImpParts(obj):
    impPartsOut = list()
    if obj.isDerivedFrom("Sketcher::SketchObject"):
        pass
    elif obj.isDerivedFrom("PartDesign::Feature"):
        pass
    elif obj.isDerivedFrom("PartDesign::Body"):
        # we want bodies that are top level in the document or top level in a container(App::Part)
        # we don't want bodies that are inside other bodies.  
        if ((not(obj.InList)) or  \
            ((len(obj.InList) == 1) and (obj.InList[0].hasExtension("App::GroupExtension")))):  #top of group
            plmGlobal = obj.getGlobalPlacement();
            plmLocal  = obj.Placement;
            if (plmGlobal != plmLocal):
                obj.Placement = plmGlobal             # should obj be a copy here?  not in orig doc - maybe no problem?
            impPartsOut.append(obj)
    elif obj.hasExtension("App::GroupExtension"):     # App::Part container.  GroupEx contents are already in list, 
        pass                                          # don't need to find them      
    elif obj.isDerivedFrom("Part::Feature"):
        if not(obj.InList):
            plmGlobal = obj.getGlobalPlacement();
            plmLocal  = obj.Placement;
            if (plmGlobal != plmLocal):
                obj.Placement = plmGlobal
            impPartsOut.append(obj)                  # top level in within Document 
        elif (len(obj.InList) == 1) and (obj.InList[0].hasExtension("App::GroupExtension")):
            plmGlobal = obj.getGlobalPlacement();
            plmLocal  = obj.Placement;
            if (plmGlobal != plmLocal):
                obj.Placement = plmGlobal
            impPartsOut.append(obj)                  # top level within Group
        elif a2plib.isA2pPart(obj):                  # imported part
            impPartsOut.append(obj)
        else:
            pass                                     # more odd PF cases?? BaseFeature in body??
    else:
        pass                                         # garbage objects - Origins, Axis, etc
    return impPartsOut


def importPartFromFile(_doc, filename, importToCache=False):
    doc = _doc
    #-------------------------------------------
    # Get the importDocument
    #-------------------------------------------
    importDocIsOpen = filename in [ d.FileName for d in FreeCAD.listDocuments().values() ]
    if importDocIsOpen:
        importDoc = [ d for d in FreeCAD.listDocuments().values() if d.FileName == filename][0]
    else:
        if filename.lower().endswith('.fcstd'):
            importDoc = FreeCAD.openDocument(filename)
        else:
            msg = "A part can only be imported from a FreeCAD '*.fcstd' file"
            QtGui.QMessageBox.information(  QtGui.QApplication.activeWindow(), "Value Error", msg )
            return
    #-------------------------------------------
    # Get a list of the importable Objects
    #-------------------------------------------

    importableObjects = list()
    importableObjects.extend(getImpPartsFromDoc(importDoc))            #visible parts only
#    importableObjects.extend(getImpPartsFromDoc(importDoc, False))     #take invisible parts too

    if importableObjects == None or len(importableObjects) == 0:
        msg = "No visible Part to import found. Aborting operation"
        QtGui.QMessageBox.information(
            QtGui.QApplication.activeWindow(),
            "Import Error",
            msg
            )
        return

    #TODO: allow import multiple parts as separate items
    #-------------------------------------------
    # Discover whether we are importing a subassembly or a single part
    #-------------------------------------------
    #if any([ 'importPart' in obj.Content for obj in importDoc.Objects]) and not len(visibleObjects) == 1:
    subAssemblyImport = False
    if len(importableObjects) > 1:
        subAssemblyImport = True

    #-------------------------------------------
    # create new object
    #-------------------------------------------
    if importToCache:
        partName = 'CachedObject_'+str(objectCache.len())
        newObj = doc.addObject("Part::FeaturePython",partName)
        newObj.Label = partName
    else:
        partName = a2plib.findUnusedObjectName( importDoc.Label, document=doc )
        partLabel = a2plib.findUnusedObjectLabel( importDoc.Label, document=doc )
        if PYVERSION < 3:
            newObj = doc.addObject( "Part::FeaturePython", partName.encode('utf-8') )
        else:
            newObj = doc.addObject( "Part::FeaturePython", str(partName.encode('utf-8')) )    # works on Python 3.6.5
        newObj.Label = partLabel


    newObj.addProperty("App::PropertyString", "a2p_Version","importPart").a2p_Version = A2P_VERSION
    newObj.addProperty("App::PropertyFile",    "sourceFile",    "importPart").sourceFile = filename
    newObj.addProperty("App::PropertyStringList","muxInfo","importPart")
    newObj.addProperty("App::PropertyFloat", "timeLastImport","importPart")
    newObj.setEditorMode("timeLastImport",1)
    newObj.timeLastImport = os.path.getmtime( filename )
    newObj.addProperty("App::PropertyBool","fixedPosition","importPart")
    newObj.fixedPosition = not any([i.fixedPosition for i in doc.Objects if hasattr(i, 'fixedPosition') ])
    newObj.addProperty("App::PropertyBool","subassemblyImport","importPart").subassemblyImport = subAssemblyImport
    newObj.setEditorMode("subassemblyImport",1)
    newObj.addProperty("App::PropertyBool","updateColors","importPart").updateColors = True
    #
    if subAssemblyImport:
        newObj.muxInfo, newObj.Shape, newObj.ViewObject.DiffuseColor = muxObjectsWithKeys(importableObjects, withColor=True)
        #newObj.muxInfo, newObj.Shape = muxObjectsWithKeys(importDoc, withColor=False)
    else:
        tmpObj = importableObjects[0]
        newObj.Shape = tmpObj.Shape.copy()
        newObj.ViewObject.ShapeColor = tmpObj.ViewObject.ShapeColor
        if appVersionStr() <= '000.016': #FC0.17: DiffuseColor overrides ShapeColor !
            newObj.ViewObject.DiffuseColor = tmpObj.ViewObject.DiffuseColor
        newObj.muxInfo = createTopoInfo(tmpObj)
        newObj.ViewObject.Transparency = tmpObj.ViewObject.Transparency

    newObj.Proxy = Proxy_muxAssemblyObj()
    newObj.ViewObject.Proxy = ImportedPartViewProviderProxy()

    doc.recompute()

    if importToCache:
        objectCache.add(newObj.sourceFile, newObj)

    if not importDocIsOpen:
        FreeCAD.closeDocument(importDoc.Name)

    return newObj


class a2p_ImportPartCommand():

    def GetResources(self):
        import a2plib
        return {'Pixmap'  : a2plib.pathOfModule()+'/icons/a2p_ImportPart.svg',
                'Accel' : "Shift+A", # a default shortcut (optional)
                'MenuText': "add Part from external file",
                'ToolTip' : "add Part from external file"
                }

    def Activated(self):
        if FreeCAD.ActiveDocument == None:
            FreeCAD.newDocument()
        doc = FreeCAD.activeDocument()
        guidoc = FreeCADGui.activeDocument()
        view = guidoc.activeView()

        dialog = QtGui.QFileDialog(
            QtGui.QApplication.activeWindow(),
            "Select FreeCAD document to import part from"
            )
        dialog.setNameFilter("Supported Formats (*.FCStd);;All files (*.*)")
        if dialog.exec_():
            if PYVERSION < 3:
                filename = unicode(dialog.selectedFiles()[0])
            else:
                filename = str(dialog.selectedFiles()[0])
        else:
            return

        if not a2plib.checkFileIsInProjectFolder(filename):
            msg = \
'''
The part you try to import is
outside of your project-folder !
Check your settings of A2plus preferences.
'''
            QtGui.QMessageBox.information(
                QtGui.QApplication.activeWindow(),
                "Import Error",
                msg
                )
            return

        #TODO: change for multi separate part import
        importedObject = importPartFromFile(doc, filename)

        if not importedObject:
            a2plib.Msg("imported Object is empty/none\n")
            return

        mw = FreeCADGui.getMainWindow()
        mdi = mw.findChild(QtGui.QMdiArea)
        sub = mdi.activeSubWindow()
        if sub != None:
            sub.showMaximized()

# WF: how will this work for multiple imported objects?
#     only A2p AI's will have property "fixedPosition"
        if importedObject and not importedObject.fixedPosition:
            PartMover( view, importedObject )
        else:
            from PySide import QtCore
            self.timer = QtCore.QTimer()
            QtCore.QObject.connect(self.timer, QtCore.SIGNAL("timeout()"), self.GuiViewFit)
            self.timer.start( 200 ) #0.2 seconds
        return

    def IsActive(self):
        """Here you can define if the command must be active or not (greyed) if certain conditions
        are met or not. This function is optional."""
        return True

    def GuiViewFit(self):
        FreeCADGui.SendMsgToActiveView("ViewFit")
        self.timer.stop()


FreeCADGui.addCommand('a2p_ImportPart',a2p_ImportPartCommand())




def updateImportedParts(doc):
    objectCache.cleanUp(doc)
    for obj in doc.Objects:
        if hasattr(obj, 'sourceFile'):
            if not hasattr( obj, 'timeLastImport'):
                obj.addProperty("App::PropertyFloat", "timeLastImport","importPart") #should default to zero which will force update.
                obj.setEditorMode("timeLastImport",1)
            if not hasattr( obj, 'a2p_Version'):
                obj.addProperty("App::PropertyString", "a2p_Version","importPart").a2p_Version = 'V0.0'
                obj.setEditorMode("a2p_Version",1)
            if not hasattr( obj, 'muxInfo'):
                obj.addProperty("App::PropertyStringList","muxInfo","importPart").muxInfo = []

            if a2plib.USE_PROJECTFILE:
                replacement = a2plib.findSourceFileInProject(obj.sourceFile) # work in any case with files within projectFolder!
            else:
                replacement = obj.sourceFile

            if replacement == None:
                QtGui.QMessageBox.critical(  QtGui.QApplication.activeWindow(),
                                            "Source file not found",
                                            "update of %s aborted!\nUnable to find %s" % (
                                                obj.Name,
                                                obj.sourceFile
                                                )
                                        )
            else:
                obj.sourceFile = replacement # update Filepath, perhaps location changed !

            if os.path.exists( obj.sourceFile ):
                newPartCreationTime = os.path.getmtime( obj.sourceFile )
                if ( newPartCreationTime > obj.timeLastImport or
                    obj.a2p_Version != A2P_VERSION
                    ):
                    if not objectCache.isCached(obj.sourceFile): # Load every changed object one time to cache
                        importPartFromFile(doc, obj.sourceFile, importToCache=True) # the version is now in the cache
                    newObject = objectCache.get(obj.sourceFile)
                    obj.timeLastImport = newPartCreationTime
                    if hasattr(newObject, 'a2p_Version'):
                        obj.a2p_Version = newObject.a2p_Version
                    importUpdateConstraintSubobjects( doc, obj, newObject )# do this before changing shape and mux
                    if hasattr(newObject, 'muxInfo'):
                        obj.muxInfo = newObject.muxInfo
                    # save Placement becaause following newObject.Shape.copy() ist resetting it to zeroes...
                    savedPlacement  = obj.Placement
                    obj.Shape = newObject.Shape.copy()
                    obj.ViewObject.DiffuseColor = copy.copy(newObject.ViewObject.DiffuseColor)
                    obj.ViewObject.Transparency = newObject.ViewObject.Transparency
                    obj.Placement = savedPlacement # restore the old placement

    mw = FreeCADGui.getMainWindow()
    mdi = mw.findChild(QtGui.QMdiArea)
    sub = mdi.activeSubWindow()
    sub.showMaximized()

    objectCache.cleanUp(doc)
    a2p_solversystem.autoSolveConstraints(doc)
    doc.recompute()


class a2p_UpdateImportedPartsCommand:

    def Activated(self):
        doc = FreeCAD.ActiveDocument
        updateImportedParts(doc)

    def GetResources(self):
        return {
            'Pixmap' : a2plib.path_a2p + '/icons/a2p_ImportPart_Update.svg',
            'MenuText': 'Update parts imported into the assembly',
            'ToolTip': 'Update parts imported into the assembly'
            }

FreeCADGui.addCommand('a2p_updateImportedParts', a2p_UpdateImportedPartsCommand())






class Proxy_importPart:
    def execute(self, shape):
        pass

def duplicateImportedPart( part ):
    doc = FreeCAD.ActiveDocument

    nameBase = part.Label
    partName = a2plib.findUnusedObjectName(nameBase,document=doc)
    partLabel = a2plib.findUnusedObjectLabel(nameBase,document=doc)
    newObj = doc.addObject("Part::FeaturePython", partName)
    newObj.Label = partLabel
    #
    if hasattr(part,'a2p_Version'):
        newObj.addProperty("App::PropertyString", "a2p_Version","importPart").a2p_Version = part.a2p_Version
    newObj.addProperty("App::PropertyFile",    "sourceFile",    "importPart").sourceFile = part.sourceFile
    newObj.addProperty("App::PropertyFloat", "timeLastImport","importPart").timeLastImport =  part.timeLastImport
    newObj.setEditorMode("timeLastImport",1)
    newObj.addProperty("App::PropertyBool","fixedPosition","importPart").fixedPosition = False# part.fixedPosition
    newObj.addProperty("App::PropertyBool","updateColors","importPart").updateColors = getattr(part,'updateColors',True)
    if hasattr(part, "muxInfo"):
        newObj.addProperty("App::PropertyStringList","muxInfo","importPart").muxInfo = part.muxInfo
    if hasattr(part, 'subassemblyImport'):
        newObj.addProperty("App::PropertyBool","subassemblyImport","importPart").subassemblyImport = part.subassemblyImport
    newObj.Shape = part.Shape.copy()
    for p in part.ViewObject.PropertiesList: #assuming that the user may change the appearance of parts differently depending on their role in the assembly.
        if hasattr(newObj.ViewObject, p) and p not in ['DiffuseColor','Proxy','MappedColors']:
            setattr(newObj.ViewObject, p, getattr( part.ViewObject, p))
    newObj.ViewObject.DiffuseColor = copy.copy( part.ViewObject.DiffuseColor )
    newObj.ViewObject.Transparency = part.ViewObject.Transparency
    newObj.Proxy = Proxy_importPart()
    newObj.ViewObject.Proxy = ImportedPartViewProviderProxy()
    newObj.Placement.Base = part.Placement.Base
    newObj.Placement.Rotation = part.Placement.Rotation
    return newObj

class a2p_DuplicatePartCommand:
    def Activated(self):
        selection = [s for s in FreeCADGui.Selection.getSelectionEx() if s.Document == FreeCAD.ActiveDocument ]
        if len(selection) == 1:
            PartMover(  FreeCADGui.activeDocument().activeView(), duplicateImportedPart( selection[0].Object ) )

    def GetResources(self):
        return {
            'Pixmap'  : a2plib.pathOfModule()+'/icons/a2p_DuplicatePart.svg',
            'MenuText': 'duplicate',
            'ToolTip': 'duplicate part (hold shift for multiple)'
            }

FreeCADGui.addCommand('a2p_duplicatePart', a2p_DuplicatePartCommand())





class a2p_EditPartCommand:
    def Activated(self):
        selection = [s for s in FreeCADGui.Selection.getSelection() if s.Document == FreeCAD.ActiveDocument ]
        if len(selection) == 0: 
            a2plib.Msg("First select a part to be edited!\n")
            return # user selected nothing!
        obj = selection[0]
        FreeCADGui.Selection.clearSelection() # very imporant! Avoid Editing the assembly the part was called from!
        fileNameWithinProjectFile = a2plib.findSourceFileInProject(obj.sourceFile)
        if fileNameWithinProjectFile == None:
            msg = \
'''
You want to edit a file which
is not found below your project-folder.
This is not allowed when using preference
"Use project Folder"
'''
            QtGui.QMessageBox.critical(
                QtGui.QApplication.activeWindow(),
                "File error ! ",
                msg
                )
            return
        #TODO: WF fails if "use folder" = false here
        docs = FreeCAD.listDocuments().values()
        docFilenames = [ d.FileName for d in docs ]
        if not fileNameWithinProjectFile in docFilenames :
            FreeCAD.open(fileNameWithinProjectFile)
        else:
            name = docs[docFilenames.index(fileNameWithinProjectFile)].Name
            FreeCAD.setActiveDocument( name )
            FreeCAD.ActiveDocument=FreeCAD.getDocument( name )
            FreeCADGui.ActiveDocument=FreeCADGui.getDocument( name )

    def GetResources(self):
        return {
            'Pixmap'  : a2plib.pathOfModule()+'/icons/a2p_EditPart.svg',
            'MenuText': 'edit',
            }

FreeCADGui.addCommand('a2p_editImportedPart', a2p_EditPartCommand())







class PartMover:
    def __init__(self, view, obj):
        self.obj = obj
        self.initialPostion = self.obj.Placement.Base
        self.copiedObject = False
        self.view = view
        self.callbackMove = self.view.addEventCallback("SoLocation2Event",self.moveMouse)
        self.callbackClick = self.view.addEventCallback("SoMouseButtonEvent",self.clickMouse)
        self.callbackKey = self.view.addEventCallback("SoKeyboardEvent",self.KeyboardEvent)
    def moveMouse(self, info):
        newPos = self.view.getPoint( *info['Position'] )
        self.obj.Placement.Base = newPos
    def removeCallbacks(self):
        self.view.removeEventCallback("SoLocation2Event",self.callbackMove)
        self.view.removeEventCallback("SoMouseButtonEvent",self.callbackClick)
        self.view.removeEventCallback("SoKeyboardEvent",self.callbackKey)
    def clickMouse(self, info):
        if info['Button'] == 'BUTTON1' and info['State'] == 'DOWN':
            if not info['ShiftDown'] and not info['CtrlDown']:
                self.removeCallbacks()
    def KeyboardEvent(self, info):
        if info['State'] == 'UP' and info['Key'] == 'ESCAPE':
            if not self.copiedObject:
                self.obj.Placement.Base = self.initialPostion
            else:
                FreeCAD.ActiveDocument.removeObject(self.obj.Name)
            self.removeCallbacks()

class PartMoverSelectionObserver:
    def __init__(self):
        FreeCADGui.Selection.addObserver(self)
        FreeCADGui.Selection.removeSelectionGate()
    def addSelection( self, docName, objName, sub, pnt ):
        FreeCADGui.Selection.removeObserver(self)
        obj = FreeCAD.ActiveDocument.getObject(objName)
        view = FreeCADGui.activeDocument().activeView()
        PartMover( view, obj )

class a2p_MovePartCommand:
    def Activated(self):
        selection = [s for s in FreeCADGui.Selection.getSelectionEx() if s.Document == FreeCAD.ActiveDocument ]
        if len(selection) == 1:
            PartMover(  FreeCADGui.activeDocument().activeView(), selection[0].Object )
        else:
            PartMoverSelectionObserver()

    def GetResources(self):
        return {
            #'Pixmap' : ':/assembly2/icons/MovePart.svg',
            'Pixmap'  : a2plib.pathOfModule()+'/icons/a2p_MovePart.svg',
            'MenuText': 'move',
            'ToolTip': 'move part  ( shift+click to copy )'
            }

FreeCADGui.addCommand('a2p_movePart', a2p_MovePartCommand())




class DeleteConnectionsCommand:
    def Activated(self):
        selection = [s for s in FreeCADGui.Selection.getSelection() if s.Document == FreeCAD.ActiveDocument ]
        #if len(selection) == 1: not required as this check is done in initGui
        # WF: still get 'list index out of range' if nothing selected.
        if len(selection) != 1:
            QtGui.QMessageBox.critical(
                QtGui.QApplication.activeWindow(),
               "Selection Error",
               "Select exactly 1 Part")
            return
        part = selection[0]
        deleteList = []
        for c in FreeCAD.ActiveDocument.Objects:
            if 'ConstraintInfo' in c.Content:
                if part.Name in [ c.Object1, c.Object2 ]:
                    deleteList.append(c)
        if len(deleteList) == 0:
            QtGui.QMessageBox.information(  QtGui.QApplication.activeWindow(), "Info", 'No constraints refer to "%s"' % part.Name)
        else:
            flags = QtGui.QMessageBox.StandardButton.Yes | QtGui.QMessageBox.StandardButton.No
            msg = "Delete %s's constraint(s):\n  - %s?" % ( part.Name, '\n  - '.join( c.Name for c in deleteList))
            response = QtGui.QMessageBox.critical(QtGui.QApplication.activeWindow(), "Delete constraints?", msg, flags )
            if response == QtGui.QMessageBox.Yes:
                for c in deleteList:
                    a2plib.removeConstraint(c)
    def GetResources(self):
        return {
            'Pixmap'  : a2plib.pathOfModule()+'/icons/a2p_DeleteConnections.svg',
            'MenuText': 'delete constraints',
            }
FreeCADGui.addCommand('a2p_DeleteConnectionsCommand', DeleteConnectionsCommand())


class ViewConnectionsCommand:
    def Activated(self):
        doc = FreeCAD.ActiveDocument

        selected = a2plib.getSelectedConstraint()
        if selected is None:
            return

        if not a2plib.isTransparencyEnabled():
            a2plib.setTransparency()

        FreeCADGui.Selection.clearSelection()
        FreeCADGui.Selection.addSelection(
            doc.getObject(selected.Object1), selected.SubElement1)

        FreeCADGui.Selection.addSelection(
            doc.getObject(selected.Object2), selected.SubElement2)

        # Add observer to remove the transparency when the selection is changing or removing
        FreeCADGui.Selection.addObserver(ViewConnectionsObserver())

    def IsActive(self):
        return (a2plib.getSelectedConstraint() is not None and a2plib.isTransparencyEnabled() == False)

    def GetResources(self):
        return {
            'Pixmap'  :     a2plib.pathOfModule()+'/icons/a2p_ViewConnection.svg',
            'MenuText':     'show connected elements',
            'ToolTip':      'show connected elements',
            }

FreeCADGui.addCommand('a2p_ViewConnectionsCommand', ViewConnectionsCommand())

class ViewConnectionsObserver:
    def __init__(self):
        self.ignoreClear = False

    def clearSelection(self, doc):
        if self.ignoreClear:
            self.ignoreClear = False
        else:
            if a2plib.isTransparencyEnabled():
                a2plib.restoreTransparency()
                FreeCADGui.Selection.removeObserver(self)

    def setSelection(self, doc):
        selected = a2plib.getSelectedConstraint()
        if selected is not None:
            self.ignoreClear = True
            FreeCADGui.Selection.clearSelection()
            FreeCADGui.Selection.addSelection(
                FreeCAD.ActiveDocument.getObject(selected.Object1), selected.SubElement1)

            FreeCADGui.Selection.addSelection(
                FreeCAD.ActiveDocument.getObject(selected.Object2), selected.SubElement2)

class a2p_isolateCommand:
    def Activated(self):
        selection = [s for s in FreeCADGui.Selection.getSelection() if s.Document == FreeCAD.ActiveDocument ]
        FreeCADGui.Selection.clearSelection()
        doc = FreeCAD.ActiveDocument

        if len(selection) == 0: # Show all elements
            for obj in doc.Objects:
                if obj.Name == 'PartInformation': continue
                if obj.Name[:4] == 'Page': continue
                if obj.Name == 'SimpleAssemblyShape': continue
                if hasattr(obj,'ViewObject'):
                    if hasattr(obj.ViewObject,'Visibility'):
                        obj.ViewObject.Visibility = True
        else:                   # Show only selected elements
            for obj in doc.Objects:
                if obj.Name == 'PartInformation': continue
                if obj.Name[:4] == 'Page': continue
                if obj.Name == 'SimpleAssemblyShape': continue
                if hasattr(obj,'ViewObject'):
                    if hasattr(obj.ViewObject,'Visibility'):
                        if obj in selection:
                            obj.ViewObject.Visibility = True
                        else:
                            obj.ViewObject.Visibility = False

    def GetResources(self):
        return {
            'Pixmap'  : a2plib.pathOfModule()+'/icons/a2p_Isolate_Element.svg',
            'MenuText': 'show only selected elements, or all if none is selected',
            'ToolTip': 'show only selected elements, or all if none is selected'
            }

FreeCADGui.addCommand('a2p_isolateCommand', a2p_isolateCommand())





class a2p_ToggleTransparencyCommand:
    def Activated(self, checked):
        if a2plib.isTransparencyEnabled():
            a2plib.restoreTransparency()
        else:
            a2plib.setTransparency()

    def IsChecked(self):
        return a2plib.isTransparencyEnabled()

    def GetResources(self):
        return {
            'Pixmap'  :     a2plib.pathOfModule()+'/icons/a2p_ToggleTranparency.svg',
            'MenuText':     'toggle transparency of assembly',
            'ToolTip':      'toggle transparency of assembly',
            'Checkable':    self.IsChecked()
        }
FreeCADGui.addCommand('a2p_ToggleTransparencyCommand', a2p_ToggleTransparencyCommand())



toolTipMessage = \
'''
toggle AutoSolve

By pressing this button you can
enable or disable automatic solving
after a constraint has been edited

If automatic solving is disabled
you have to start it manually
by hitting the solvebutton

'''

class a2p_ToggleAutoSolveCommand:

    def Activated(self, checked):
        a2plib.setAutoSolve(checked)

    def IsChecked(self):
        return a2plib.getAutoSolveState()

    def GetResources(self):
        return {
            'Pixmap'  :     a2plib.pathOfModule()+'/icons/a2p_ToggleAutoSolve.svg',
            'MenuText':     'toggle AutoSolve',
            'ToolTip':      toolTipMessage,
            'Checkable':    self.IsChecked()
            }
FreeCADGui.addCommand('a2p_ToggleAutoSolveCommand', a2p_ToggleAutoSolveCommand())



class a2p_TogglePartialProcessingCommand:

    def Activated(self, checked):
        a2plib.setPartialProcessing(checked)

    def IsChecked(self):
        return a2plib.isPartialProcessing()

    def GetResources(self):
        return {
            'Pixmap'  :     a2plib.pathOfModule()+'/icons/a2p_TogglePartial.svg',
            'MenuText':     'toggle partial processing',
            'ToolTip':      'toggle partial processing',
            'Checkable':    self.IsChecked()
            }
FreeCADGui.addCommand('a2p_TogglePartialProcessingCommand', a2p_TogglePartialProcessingCommand())



def a2p_repairTreeView():
    doc = FreeCAD.activeDocument()
    if doc == None: return

    constraints = [ obj for obj in doc.Objects if 'ConstraintInfo' in obj.Content]
    for c in constraints:
        if c.Proxy != None:
            c.Proxy.disable_onChanged = True
        if not hasattr(c,"ParentTreeObject"):
            c.addProperty("App::PropertyLink","ParentTreeObject","ConstraintInfo")
            c.setEditorMode("ParentTreeObject", 1)
        parent = doc.getObject(c.Object1)
        c.ParentTreeObject = parent
        parent.Label = parent.Label # trigger an update...
        if c.Proxy != None:
            c.Proxy.disable_onChanged = False
    #
    mirrors = [ obj for obj in doc.Objects if 'ConstraintNfo' in obj.Content]
    for m in mirrors:
        if m.Proxy != None:
            m.Proxy.disable_onChanged = True
        if not hasattr(m,"ParentTreeObject"):
            m.addProperty("App::PropertyLink","ParentTreeObject","ConstraintNfo")
            m.setEditorMode("ParentTreeObject", 1)
        parent = doc.getObject(m.Object2)
        m.ParentTreeObject = parent
        parent.Label = parent.Label # trigger an update...
        if m.Proxy != None:
            m.Proxy.disable_onChanged = False
    #

toolTipMessage = \
'''
repair the treeview,
if being damaged somehow.

After pressing this button,
constraints will grouped under
corresponding parts again
'''


class a2p_repairTreeViewCommand:

    def Activated(self):
        a2p_repairTreeView()

    def GetResources(self):
        return {
            'Pixmap'  :     a2plib.pathOfModule()+'/icons/a2p_RepairTree.svg',
            'MenuText':     'repair treeView',
            'ToolTip':      toolTipMessage
            }
FreeCADGui.addCommand('a2p_repairTreeViewCommand', a2p_repairTreeViewCommand())






def importUpdateConstraintSubobjects( doc, oldObject, newObject ):
    ''' updating constraints, deactivated at moment'''
    return
