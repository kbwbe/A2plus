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
import os, copy, time, sys, platform
import a2plib
from a2p_MuxAssembly import (
    muxObjectsWithKeys,
    Proxy_muxAssemblyObj,
    makePlacedShape,
    muxAssemblyWithTopoNames
    )
from a2p_viewProviderProxies import *
from a2p_versionmanagement import (
    SubAssemblyWalk, 
    A2P_VERSION
    )
import a2p_solversystem
from a2plib import (
    appVersionStr,
    AUTOSOLVE_ENABLED,
    Msg,
    DebugMsg,
    A2P_DEBUG_LEVEL,
    A2P_DEBUG_NONE,
    A2P_DEBUG_1,
    A2P_DEBUG_2,
    A2P_DEBUG_3,
    getRelativePathesEnabled
    )

from a2p_topomapper import (
    TopoMapper
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

def importPartFromFile(_doc, filename, importToCache=False):
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
        else:
            msg = "A part can only be imported from a FreeCAD '*.fcstd' file"
            QtGui.QMessageBox.information(  QtGui.QApplication.activeWindow(), "Value Error", msg )
            return

    #-------------------------------------------
    # Initialize the new TopoMapper
    #-------------------------------------------
    topoMapper = TopoMapper(importDoc)

    #-------------------------------------------
    # Get a list of the importable Objects
    #-------------------------------------------
    importableObjects = topoMapper.getTopLevelObjects()
    
    if len(importableObjects) == 0:
        msg = "No visible Part to import found. Aborting operation"
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

    newObj.Proxy = Proxy_muxAssemblyObj()
    newObj.ViewObject.Proxy = ImportedPartViewProviderProxy()

    newObj.addProperty("App::PropertyString", "a2p_Version","importPart").a2p_Version = A2P_VERSION
    
    assemblyPath = os.path.normpath(os.path.split(doc.FileName)[0])
    absPath = os.path.normpath(filename)
    if getRelativePathesEnabled():
        if platform.system() == "Windows":
            prefix = '.\\'
        else:
            prefix = './'
        relativePath = prefix+os.path.relpath(absPath, assemblyPath)
        newObj.addProperty("App::PropertyFile",    "sourceFile",    "importPart").sourceFile = relativePath
    else:
        newObj.addProperty("App::PropertyFile",    "sourceFile",    "importPart").sourceFile = absPath
    
    newObj.addProperty("App::PropertyStringList","muxInfo","importPart")
    newObj.addProperty("App::PropertyFloat", "timeLastImport","importPart")
    newObj.setEditorMode("timeLastImport",1)
    newObj.timeLastImport = os.path.getmtime( filename )
    newObj.addProperty("App::PropertyBool","fixedPosition","importPart")
    newObj.fixedPosition = not any([i.fixedPosition for i in doc.Objects if hasattr(i, 'fixedPosition') ])
    newObj.addProperty("App::PropertyBool","subassemblyImport","importPart").subassemblyImport = subAssemblyImport
    newObj.setEditorMode("subassemblyImport",1)
    newObj.addProperty("App::PropertyBool","updateColors","importPart").updateColors = True

    if subAssemblyImport:
    #if False:
        #newObj.muxInfo, newObj.Shape, newObj.ViewObject.DiffuseColor = muxObjectsWithKeys(importableObjects, withColor=True)
        newObj.muxInfo, newObj.Shape, newObj.ViewObject.DiffuseColor = muxAssemblyWithTopoNames(
            importDoc, 
            withColor=True
            )
    else:
        # TopoMapper manages import of non A2p-Files. It generates the shapes and appropriate topo names...
        newObj.muxInfo, newObj.Shape, newObj.ViewObject.DiffuseColor = topoMapper.createTopoNames(withColor=True)
        

    doc.recompute()

    if importToCache:
        objectCache.add(filename, newObj)

    if not importDocIsOpen:
        FreeCAD.closeDocument(importDoc.Name)

    return newObj


class a2p_ImportPartCommand():

    def GetResources(self):
        return {'Pixmap'  : a2plib.pathOfModule()+'/icons/a2p_ImportPart.svg',
                'Accel' : "Shift+A", # a default shortcut (optional)
                'MenuText': "add Part from external file",
                'ToolTip' : "add Part from external file"
                }

    def Activated(self):
        if FreeCAD.ActiveDocument == None:
            QtGui.QMessageBox.information(
                QtGui.QApplication.activeWindow(),
               "No active Document found",
               '''First create an empty file and\nsave it under desired name'''
               )
            return
        #
        if FreeCAD.ActiveDocument.FileName == '':
            QtGui.QMessageBox.information(
                QtGui.QApplication.activeWindow(),
               "Unnamed document",
               '''Before inserting first part,\nplease save the empty assembly\nto give it a name'''
               )
            return
        
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
    if doc == None:
        QtGui.QMessageBox.information(  
                        QtGui.QApplication.activeWindow(),
                        "No active document found!",
                        "Before updating parts, you have to open an assembly file."
                        )
        return
        
    # modififying object's subelements causes solving of the assembly, disable autosolve here
    autoSolveState = a2plib.getAutoSolveState()
    a2plib.setAutoSolve(False)
            
    doc.openTransaction("updateImportParts")    
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

            assemblyPath = os.path.normpath(os.path.split(doc.FileName)[0])
            absPath = a2plib.findSourceFileInProject(obj.sourceFile, assemblyPath)

            if absPath == None:
                QtGui.QMessageBox.critical(  QtGui.QApplication.activeWindow(),
                                            u"Source file not found",
                                            u"Unable to find {}".format(
                                                obj.sourceFile
                                                )
                                        )
            if absPath != None and os.path.exists( absPath ):
                newPartCreationTime = os.path.getmtime( absPath )
                if ( 
                    newPartCreationTime > obj.timeLastImport or
                    obj.a2p_Version != A2P_VERSION
                    ):
                    if not objectCache.isCached(absPath): # Load every changed object one time to cache
                        importPartFromFile(doc, absPath, importToCache=True) # the version is now in the cache
                    newObject = objectCache.get(absPath)
                    obj.timeLastImport = newPartCreationTime
                    if hasattr(newObject, 'a2p_Version'):
                        obj.a2p_Version = A2P_VERSION
                    importUpdateConstraintSubobjects( doc, obj, newObject ) # do this before changing shape and mux
                    if hasattr(newObject, 'muxInfo'):
                        obj.muxInfo = newObject.muxInfo
                    # save Placement because following newObject.Shape.copy() isn't resetting it to zeroes...
                    savedPlacement  = obj.Placement
                    obj.Shape = newObject.Shape.copy()
                    obj.ViewObject.DiffuseColor = copy.copy(newObject.ViewObject.DiffuseColor)
                    obj.ViewObject.Transparency = newObject.ViewObject.Transparency
                    obj.Placement = savedPlacement # restore the old placement

    mw = FreeCADGui.getMainWindow()
    mdi = mw.findChild(QtGui.QMdiArea)
    sub = mdi.activeSubWindow()
    if sub != None:
        sub.showMaximized()

    objectCache.cleanUp(doc)
    a2plib.setAutoSolve(autoSolveState)
    
    if not a2plib.getUseTopoNaming():
        # This is only needed when not using toponames. 
        # Otherwise updating constraints.subelements triggers this.
        a2p_solversystem.autoSolveConstraints(
            doc, 
            useTransaction = False, 
            callingFuncName = "updateImportedParts"
            ) #transaction is already open...
    
    doc.recompute()
    doc.commitTransaction()    



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
    if PYVERSION >= 3:
        newObj = doc.addObject("Part::FeaturePython", str(partName.encode("utf-8")) )
    else:
        newObj = doc.addObject("Part::FeaturePython", partName.encode("utf-8") )
    
    newObj.Label = partLabel

    newObj.Proxy = Proxy_importPart()
    newObj.ViewObject.Proxy = ImportedPartViewProviderProxy()


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
        if hasattr(part.ViewObject, p) and p not in ['DiffuseColor','Proxy','MappedColors']:
            setattr(newObj.ViewObject, p, getattr( part.ViewObject, p))

    newObj.ViewObject.DiffuseColor = copy.copy( part.ViewObject.DiffuseColor )
    newObj.ViewObject.Transparency = part.ViewObject.Transparency
    newObj.Placement.Base = part.Placement.Base
    newObj.Placement.Rotation = part.Placement.Rotation
    return newObj

class a2p_DuplicatePartCommand:
    def Activated(self):
        if FreeCAD.activeDocument() == None:
            QtGui.QMessageBox.critical(
                QtGui.QApplication.activeWindow(),
               "No active Document error",
               "First please open an assembly file!"
               )
            return
        selection = [s for s in FreeCADGui.Selection.getSelectionEx() if s.Document == FreeCAD.ActiveDocument ]
        if len(selection) == 1:
            PartMover(  FreeCADGui.activeDocument().activeView(), duplicateImportedPart( selection[0].Object ) )
        else:
            QtGui.QMessageBox.critical(
                QtGui.QApplication.activeWindow(),
               "Selection error",
               "Before duplicating, first please select a part!"
               )
            

    def GetResources(self):
        return {
            'Pixmap'  : a2plib.pathOfModule()+'/icons/a2p_DuplicatePart.svg',
            'MenuText': 'duplicate',
            'ToolTip': 'duplicate part (hold shift for multiple)'
            }

FreeCADGui.addCommand('a2p_duplicatePart', a2p_DuplicatePartCommand())





class a2p_EditPartCommand:
    def Activated(self):
        doc = FreeCAD.activeDocument()
        if doc == None:
            QtGui.QMessageBox.information(  QtGui.QApplication.activeWindow(),
                                        "No active document found!",
                                        "Before editing a part, you have to open an assembly file."
                                    )
            return
        selection = [s for s in FreeCADGui.Selection.getSelection() if s.Document == FreeCAD.ActiveDocument ]
        if not selection:
            msg = \
'''
You must select a part to edit first.
'''
            QtGui.QMessageBox.information(
                QtGui.QApplication.activeWindow(),
                "Selection Error",
                msg
                )
            return
        obj = selection[0]
        FreeCADGui.Selection.clearSelection() # very important! Avoid Editing the assembly the part was called from!
        assemblyPath = os.path.normpath(os.path.split(doc.FileName)[0])
        fileNameWithinProjectFile = a2plib.findSourceFileInProject(obj.sourceFile, assemblyPath)
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
        docs = []
        for d in FreeCAD.listDocuments().values(): #dict_values not indexable, docs now is...
            docs.append(d)
        #docs = FreeCAD.listDocuments().values()
        docFilenames = [ d.FileName for d in docs ]
        
        if not fileNameWithinProjectFile in docFilenames :
            FreeCAD.open(fileNameWithinProjectFile)
        else:
            idx = docFilenames.index(fileNameWithinProjectFile)
            name = docs[idx].Name
            # Search and activate the corresponding document window..
            mw=FreeCADGui.getMainWindow()
            mdi=mw.findChild(QtGui.QMdiArea)
            sub=mdi.subWindowList()
            for s in sub:
                mdi.setActiveSubWindow(s)
                if FreeCAD.activeDocument().Name == name: break
            # This does not work somehow...
            # FreeCAD.setActiveDocument( name )
            # FreeCAD.ActiveDocument=FreeCAD.getDocument( name )
            # FreeCADGui.ActiveDocument=FreeCADGui.getDocument( name )


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
                FreeCAD.activeDocument().recompute()
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
        if FreeCAD.activeDocument() == None:
            QtGui.QMessageBox.critical(
                QtGui.QApplication.activeWindow(),
               "No active Document error",
               "First please open an assembly file!"
               )
            return
            
        selection = [s for s in FreeCADGui.Selection.getSelectionEx() if s.Document == FreeCAD.ActiveDocument ]
        if len(selection) == 1:
            PartMover(  FreeCADGui.activeDocument().activeView(), selection[0].Object )
        else:
            PartMoverSelectionObserver()

    def GetResources(self):
        return {
            #'Pixmap' : ':/assembly2/icons/MovePart.svg',
            'Pixmap'  : a2plib.pathOfModule()+'/icons/a2p_MovePart.svg',
            'MenuText': 'move selected part',
            'ToolTip': 'move selected part'
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

    def hasFaces(self,ob):
        if hasattr(ob,"Shape") and hasattr(ob.Shape,"Faces") and len(ob.Shape.Faces)>0:
            return True
        return False

    def Activated(self):
        if FreeCAD.activeDocument() == None:
            QtGui.QMessageBox.information(  QtGui.QApplication.activeWindow(),
                                        "No active document found!",
                                        "You have to open an assembly file first."
                                    )
            return
        selection = [s for s in FreeCADGui.Selection.getSelection() if s.Document == FreeCAD.ActiveDocument ]
        FreeCADGui.Selection.clearSelection()
        doc = FreeCAD.ActiveDocument

        if len(selection) == 0: # Show all elements
            for obj in doc.Objects:
                if obj.Name == 'PartInformation': continue
                if obj.Name[:4] == 'Page': continue
                if obj.Name == 'SimpleAssemblyShape': continue
                if not self.hasFaces(obj): continue
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
        if FreeCAD.activeDocument() == None:
            QtGui.QMessageBox.information(  QtGui.QApplication.activeWindow(),
                                        "No active document found!",
                                        "You have to open an assembly file first."
                                    )
            return
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

    global a2p_NeedToSolveSystem
    a2p_NeedToSolveSystem = False # Solve only once after editing a constraint's property


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
        if FreeCAD.activeDocument() == None:
            QtGui.QMessageBox.information(  QtGui.QApplication.activeWindow(),
                                        "No active document found!",
                                        "You have to open an assembly file first."
                                    )
            return
        a2p_repairTreeView()

    def GetResources(self):
        return {
            'Pixmap'  :     a2plib.pathOfModule()+'/icons/a2p_RepairTree.svg',
            'MenuText':     'repair treeView',
            'ToolTip':      toolTipMessage
            }
FreeCADGui.addCommand('a2p_repairTreeViewCommand', a2p_repairTreeViewCommand())


class a2p_FlipConstraintDirectionCommand:

    def Activated(self):
        if FreeCAD.activeDocument() == None:
            QtGui.QMessageBox.information(  QtGui.QApplication.activeWindow(),
                                        "No active document found!",
                                        "You have to open an assembly file first."
                                    )
            return
        a2p_FlipConstraintDirection()

    def GetResources(self):
        return {
            'Pixmap'  :     a2plib.pathOfModule()+'/icons/a2p_flipConstraint.svg',
            'MenuText':     'flip direction of last constraint',
            'ToolTip':      'flip direction of last constraint'
            }
FreeCADGui.addCommand('a2p_FlipConstraintDirectionCommand', a2p_FlipConstraintDirectionCommand())

def a2p_FlipConstraintDirection():
    ''' updating constraints, deactivated at moment'''
    constraints = [ obj for obj in FreeCAD.ActiveDocument.Objects 
                        if 'ConstraintInfo' in obj.Content ]
    if len(constraints) == 0:
        QtGui.QMessageBox.information(
            QtGui.qApp.activeWindow(),
            "Command Aborted", 
            'Flip aborted since no a2p constraints in active document.'
            )
        return
    lastConstraintAdded = constraints[-1]
    try:
        if lastConstraintAdded.directionConstraint == 'aligned':
            lastConstraintAdded.directionConstraint = 'opposed'
        else:
            lastConstraintAdded.directionConstraint = 'aligned'
        a2p_solversystem.autoSolveConstraints(FreeCAD.activeDocument(), callingFuncName="a2p_FlipConstraintDirection")
    except:
        pass




class a2p_Show_Hierarchy_Command:

    def Activated(self):
        doc = FreeCAD.activeDocument()
        if doc == None:
            QtGui.QMessageBox.information(  QtGui.QApplication.activeWindow(),
                                        "No active document found!",
                                        "You have to open an assembly file first."
                                    )
            return
        ss = a2p_solversystem.SolverSystem()
        ss.loadSystem(doc)
        ss.assignParentship(doc)
        ss.visualizeHierarchy()

    def GetResources(self):
        return {
            'Pixmap'  :     a2plib.pathOfModule()+'/icons/a2p_treeview.svg',
            'MenuText':     'generate HTML file with detailed constraining structure',
            'ToolTip':      'generate HTML file with detailed constraining structure'
            }
FreeCADGui.addCommand('a2p_Show_Hierarchy_Command', a2p_Show_Hierarchy_Command())



class a2p_Show_DOF_info_Command:

    def Activated(self):
        if FreeCAD.activeDocument() == None:
            QtGui.QMessageBox.information(  QtGui.QApplication.activeWindow(),
                                        "No active document found!",
                                        "You have to open an assembly file first."
                                    )
            return
        ss = a2p_solversystem.SolverSystem()
        ss.DOF_info_to_console()

    def GetResources(self):
        return {
            'Pixmap'  :     a2plib.pathOfModule()+'/icons/a2p_DOFs.svg',
            'MenuText':     'print detailed DOF information to console',
            'ToolTip':      'print detailed DOF information to console'
            }
FreeCADGui.addCommand('a2p_Show_DOF_info_Command', a2p_Show_DOF_info_Command())



class a2p_absPath_to_relPath_Command:
    def Activated(self):
        doc = FreeCAD.activeDocument()
        if doc == None:
            QtGui.QMessageBox.information(  QtGui.QApplication.activeWindow(),
                                        "No active document found!",
                                        "You have to open an assembly file first."
                                    )
            return
        assemblyPath = os.path.normpath(  os.path.split( os.path.normpath(doc.FileName) )[0])
        importParts = [ob for ob in doc.Objects if "mportPart" in ob.Content]
        for iPart in importParts:
            if (
                iPart.sourceFile.startswith("./") or
                iPart.sourceFile.startswith("../") or
                iPart.sourceFile.startswith(".\\") or
                iPart.sourceFile.startswith("..\\")
                ): continue # path is already relative
            filePath = os.path.normpath(iPart.sourceFile)
            if platform.system() == "Windows":
                prefix = '.\\'
            else:
                prefix = './'
            iPart.sourceFile = prefix + os.path.relpath(filePath, assemblyPath)
            
    def GetResources(self):
        return {
            'MenuText':     'convert absolute paths of importParts to relative ones',
            'ToolTip':      'convert absolute paths of importParts to relative ones'
            }
FreeCADGui.addCommand('a2p_absPath_to_relPath_Command', a2p_absPath_to_relPath_Command())







def importUpdateConstraintSubobjects( doc, oldObject, newObject ):
    if not a2plib.getUseTopoNaming(): return
    
    # return if there are no constraints linked to the object 
    if len([c for c in doc.Objects if  'ConstraintInfo' in c.Content and oldObject.Name in [c.Object1, c.Object2] ]) == 0:
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
                                       subElementName,newSubElementName
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
            message = "constraint %s is broken. Delete constraint? otherwise check for wrong linkage." % cName
            #response = QtGui.QMessageBox.critical(QtGui.qApp.activeWindow(), "Broken Constraint", message, flags )
            response = QtGui.QMessageBox.critical(None, "Broken Constraint", message, flags )
        
            if response == QtGui.QMessageBox.Yes:
                FreeCAD.Console.PrintError("removing constraint %s" % cName)
                c = doc.getObject(cName)
                a2plib.removeConstraint(c)
                


