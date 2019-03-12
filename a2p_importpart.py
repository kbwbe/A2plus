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

import a2p_lcs_support

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
        elif filename.lower().endswith('.stp') or filename.lower().endswith('.step'):
            import ImportGui
            fname =  os.path.splitext(os.path.basename(filename))[0]
            FreeCAD.newDocument(fname)
            newname = FreeCAD.ActiveDocument.Name
            FreeCAD.setActiveDocument(newname)
            ImportGui.insert(filename,newname)
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
            #ob.touch()
            ob.recompute()
        #importDoc.recompute()
        importDoc.save() # useless without saving...
    
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
    if a2plib.getForceFixedPosition():
        newObj.fixedPosition = True
    else:
        newObj.fixedPosition = not any([i.fixedPosition for i in doc.Objects if hasattr(i, 'fixedPosition') ])
    newObj.addProperty("App::PropertyBool","subassemblyImport","importPart").subassemblyImport = subAssemblyImport
    newObj.setEditorMode("subassemblyImport",1)
    newObj.addProperty("App::PropertyBool","updateColors","importPart").updateColors = True

    if subAssemblyImport:
    #if False:
        #newObj.muxInfo, newObj.Shape, newObj.ViewObject.DiffuseColor = muxObjectsWithKeys(importableObjects, withColor=True)
        newObj.muxInfo, newObj.Shape, newObj.ViewObject.DiffuseColor, newObj.ViewObject.Transparency = \
            muxAssemblyWithTopoNames(importDoc)
    else:
        # TopoMapper manages import of non A2p-Files. It generates the shapes and appropriate topo names...
        newObj.muxInfo, newObj.Shape, newObj.ViewObject.DiffuseColor, newObj.ViewObject.Transparency = \
            topoMapper.createTopoNames()
        

    doc.recompute()

    if importToCache: # this import is used to update already imported parts
        objectCache.add(filename, newObj)
    else: # this is a first time import of a part
        if not a2plib.getPerFaceTransparency():
            # turn of perFaceTransparency by accessing ViewObject.Transparency and set to zero (non transparent)
            newObj.ViewObject.Transparency = 1
            newObj.ViewObject.Transparency = 0 # import assembly first time as non transparent.


    lcsList = a2p_lcs_support.getListOfLCS(doc,importDoc)
    

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
    
        proxy = a2p_lcs_support.LCS_Group(lcsGroup)
        vp_proxy = a2p_lcs_support.VP_LCS_Group(lcsGroup.ViewObject)
        
        for lcs in lcsList:
            lcsGroup.addObject(lcs)
        
        lcsGroup.Owner = newObj.Name
        
        newObj.addProperty("App::PropertyLinkList","lcsLink","importPart").lcsLink = lcsGroup
        newObj.Label = newObj.Label # this is needed to trigger an update
        lcsGroup.Label = lcsGroup.Label
    
        #=========================================

    return newObj



toolTip = \
'''
Add a part from an external file
to the assembly
'''

class a2p_ImportPartCommand():

    def GetResources(self):
        return {'Pixmap'  : a2plib.pathOfModule()+'/icons/a2p_ImportPart.svg',
                'Accel' : "Shift+A", # a default shortcut (optional)
                'MenuText': "Add a part from an external file",
                'ToolTip' : toolTip
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
            FreeCADGui.SendMsgToActiveView("Save")
            return
        
        doc = FreeCAD.activeDocument()
        guidoc = FreeCADGui.activeDocument()
        view = guidoc.activeView()

        dialog = QtGui.QFileDialog(
            QtGui.QApplication.activeWindow(),
            "Select FreeCAD document to import part from"
            )
        #dialog.setNameFilter("Supported Formats (*.FCStd);;STEP files (*.stp *.step);;All files (*.*)")
        dialog.setNameFilter("Supported Formats (*.FCStd *.stp *.step)") #;;All files (*.*)")
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
        
    doc.openTransaction("updateImportParts")    
    objectCache.cleanUp(doc)
    for obj in doc.Objects:
        if hasattr(obj, 'sourceFile'):
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
                    obj.a2p_Version != A2P_VERSION or
                    a2plib.getRecalculateImportedParts() # open always all parts as they could depend on spreadsheets
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
                    obj.Placement = savedPlacement # restore the old placement
                    a2plib.copyObjectColors(newObject,obj)    # order is: source,target  *MK.


    mw = FreeCADGui.getMainWindow()
    mdi = mw.findChild(QtGui.QMdiArea)
    sub = mdi.activeSubWindow()
    if sub != None:
        sub.showMaximized()
    objectCache.cleanUp(doc)
    a2p_solversystem.autoSolveConstraints(
        doc, 
        useTransaction = False, 
        callingFuncName = "updateImportedParts"
        ) #transaction is already open...
    doc.recompute()
    doc.commitTransaction()    



toolTip = \
'''
Update parts, which have been
imported to the assembly.

(If you modify a part in an
external file, the new shape
is taken to the assembly by
this function.)
'''

class a2p_UpdateImportedPartsCommand:

    def Activated(self):
        doc = FreeCAD.ActiveDocument
        updateImportedParts(doc)

    def GetResources(self):
        return {
            'Pixmap' : a2plib.path_a2p + '/icons/a2p_ImportPart_Update.svg',
            'MenuText': 'Update parts imported into the assembly',
            'ToolTip': toolTip
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

toolTip = \
'''
Make a duplicate of a
part, which is already
imported to the assembly.

Select a part and hit
this button. A duplicate
will be created and can be 
placed somewhere by mouse.
'''

class a2p_DuplicatePartCommand:
    def Activated(self):
        #====================================================
        # Is there an open Doc ?
        #====================================================
        if FreeCAD.activeDocument() == None:
            QtGui.QMessageBox.information(
                QtGui.QApplication.activeWindow(),
               u"No active Document error",
               u"First please open an assembly file!"
               )
            return
        
        #====================================================
        # Is something been selected ?
        #====================================================
        selection = [s for s in FreeCADGui.Selection.getSelectionEx() if s.Document == FreeCAD.ActiveDocument ]
        if len(selection) != 1:
            QtGui.QMessageBox.information(
                QtGui.QApplication.activeWindow(),
               u"Selection error",
               u"Before duplicating, first please select a part!"
               )
            return
            
        #====================================================
        # Is the selection an a2p part ?
        #====================================================
        obj = selection[0].Object
        if not a2plib.isA2pPart(obj):
            QtGui.QMessageBox.information(  QtGui.QApplication.activeWindow(),
                                        u"Duplicate: Selection invalid!",
                                        u"This object is no imported part!"
                                    )
            return
        
        #====================================================
        # Duplicate the part
        #====================================================
        PartMover(  FreeCADGui.activeDocument().activeView(), duplicateImportedPart( selection[0].Object ) )
        

    def GetResources(self):
        return {
            'Pixmap'  : a2plib.pathOfModule()+'/icons/a2p_DuplicatePart.svg',
            'MenuText': 'Create duplicate of a part',
            'ToolTip':  toolTip
            }

FreeCADGui.addCommand('a2p_duplicatePart', a2p_DuplicatePartCommand())



toolTip = \
'''
Edit an imported part.

Select an imported part
and hit this button.

The appropriate FCStd file,
linked to this part will
be opened and you can modify
this part at this place.

After editing and saving,
you have to use the function
'update imported parts' in
order to see the new shape
within the assembly.
'''

class a2p_EditPartCommand:
    def Activated(self):
        doc = FreeCAD.activeDocument()
        #====================================================
        # Is there an open Doc ?
        #====================================================
        if doc == None:
            QtGui.QMessageBox.information(  QtGui.QApplication.activeWindow(),
                                        u"No active document found!",
                                        u"Before editing a part, you have to open an assembly file."
                                    )
            return
        
        #====================================================
        # Is something been selected ?
        #====================================================
        selection = [s for s in FreeCADGui.Selection.getSelection() if s.Document == FreeCAD.ActiveDocument ]
        if not selection:
            QtGui.QMessageBox.information(
                QtGui.QApplication.activeWindow(),
                u"Selection Error",
                u"You must select a part to edit first."
                )
            return
        
        #====================================================
        # Has the selected object an editable a2p file ?
        #====================================================
        obj = selection[0]
        if not a2plib.isEditableA2pPart(obj):
            QtGui.QMessageBox.information(  QtGui.QApplication.activeWindow(),
                                        u"Edit: Selection invalid!",
                                        u"This object is no imported part!"
                                    )
            return
        
        #====================================================
        # Does the file exist ?
        #====================================================
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

        #====================================================
        # Open the file for editing and switch the window
        #====================================================
        
        #Workaround to detect open files on Win10 (Address Translation problem??)
        importDocIsOpen = False
        requestedFile = os.path.split(fileNameWithinProjectFile)[1]
        for d in FreeCAD.listDocuments().values():
            recentFile = os.path.split(d.FileName)[1]
            if requestedFile == recentFile:
                importDoc = d # file is already open...
                importDocIsOpen = True
                break
        
        if not importDocIsOpen:
            if fileNameWithinProjectFile.lower().endswith('.stp') or fileNameWithinProjectFile.lower().endswith('.step'):
                import ImportGui
                fname =  os.path.splitext(os.path.basename(fileNameWithinProjectFile))[0]
                FreeCAD.newDocument(fname)
                newname = FreeCAD.ActiveDocument.Name
                ImportGui.open(fileNameWithinProjectFile, newname)
                FreeCAD.ActiveDocument.Label = fname
                FreeCADGui.SendMsgToActiveView("ViewFit")
                msg = "Editing a STEP file as '*.FCStd' file\nPlease export the saved file as \'.step\'\n" + fileNameWithinProjectFile
                QtGui.QMessageBox.information( QtGui.QApplication.activeWindow(), "Info", msg )                
            else:
                FreeCAD.open(fileNameWithinProjectFile)
        else:
            name = importDoc.Name
            # Search and activate the corresponding document window..
            mw=FreeCADGui.getMainWindow()
            mdi=mw.findChild(QtGui.QMdiArea)
            sub=mdi.subWindowList()
            for s in sub:
                mdi.setActiveSubWindow(s)
                if FreeCAD.activeDocument().Name == name: break


    def GetResources(self):
        return {
            'Pixmap'  : a2plib.pathOfModule()+'/icons/a2p_EditPart.svg',
            'MenuText': 'Edit an imported part (open linked FCStd file)',
            'ToolTip':  toolTip
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
            #if not info['ShiftDown'] and not info['CtrlDown']: #struggles within Inventor Navigation
            if not info['ShiftDown']:
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

toolTip = \
'''
Move the selected part.

Select a part and hit this
button. The part can be moved
around by mouse.

If the part is constrained, it
will jump back by next solving
of the assembly.
'''

class a2p_MovePartCommand:
    def Activated(self):
        #====================================================
        # Is there an open Doc ?
        #====================================================
        if FreeCAD.activeDocument() == None:
            QtGui.QMessageBox.critical(
                QtGui.QApplication.activeWindow(),
               u"No active Document error",
               u"First please open an assembly file!"
               )
            return
        
        #====================================================
        # Is something been selected ?
        #====================================================
        selection = [s for s in FreeCADGui.Selection.getSelectionEx() if s.Document == FreeCAD.ActiveDocument ]
        if len(selection) != 1:
            QtGui.QMessageBox.information(
                QtGui.QApplication.activeWindow(),
               u"Selection error",
               u"Before moving, first please select exact 1 part!"
               )
            return
            
        #====================================================
        # Move object, if possible
        #====================================================
        try:
            PartMover(  FreeCADGui.activeDocument().activeView(), selection[0].Object )
        except:
            QtGui.QMessageBox.information(
                QtGui.QApplication.activeWindow(),
               u"Wrong selection",
               u"Cannot move selected object!"
               )
            

    def GetResources(self):
        return {
            #'Pixmap' : ':/assembly2/icons/MovePart.svg',
            'Pixmap'  : a2plib.pathOfModule()+'/icons/a2p_MovePart.svg',
            'MenuText': 'Move the selected part',
            'ToolTip': toolTip
            }

FreeCADGui.addCommand('a2p_movePart', a2p_MovePartCommand())




toolTipText = \
'''
Delete all constraints
of a selected part.

Select exact one part 
and hit this button.

A confirmation dialog pops
up, showing all constraints
related to the selected part.

After confirmation all related
constraints are deleted
at once.
'''

class DeleteConnectionsCommand:
    def Activated(self):
        selection = [s for s in FreeCADGui.Selection.getSelection() if s.Document == FreeCAD.ActiveDocument ]
        #if len(selection) == 1: not required as this check is done in initGui
        # WF: still get 'list index out of range' if nothing selected.
        if len(selection) != 1:
            QtGui.QMessageBox.critical(
                QtGui.QApplication.activeWindow(),
               "Selection Error",
               "Select exactly 1 part")
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
            msg = u"Delete {}'s constraint(s):\n  - {}?".format(
                part.Label,
                u'\n  - '.join( c.Name for c in deleteList)
                )
            response = QtGui.QMessageBox.information(
                QtGui.QApplication.activeWindow(), 
                "Delete constraints?", 
                msg, 
                flags
                )
            if response == QtGui.QMessageBox.Yes:
                doc = FreeCAD.activeDocument()
                doc.openTransaction("Deleting part's constraints")
                for c in deleteList:
                    a2plib.removeConstraint(c)
                doc.commitTransaction()
                    
    def IsActive(self):
        selection = FreeCADGui.Selection.getSelection()
        if len(selection) != 1: 
            return False

        obj = selection[0]
        if a2plib.isConstrainedPart(FreeCAD.activeDocument(), obj):
            return True
        else:
            return False
                    
    def GetResources(self):
        return {
            'Pixmap'  : a2plib.pathOfModule()+'/icons/a2p_DeleteConnections.svg',
            'MenuText': 'Delete all constraints of selected parts',
            'ToolTip': toolTipText
            }
FreeCADGui.addCommand('a2p_DeleteConnectionsCommand', DeleteConnectionsCommand())

toolTip = \
'''
Highlight both parts, which are
related to a selected constraint.

Select a constraint within
the treeview and hit this button.

The whole assembly is switched to
transparent mode and you can inspect
the desired constraint.
'''

class ViewConnectionsCommand:
    def Activated(self):
        doc = FreeCAD.ActiveDocument

        selected = a2plib.getSelectedConstraint()
        if selected is None:
            return

        initialTransparencyState = a2plib.isTransparencyEnabled()
        if not initialTransparencyState:
            a2plib.setTransparency()

        FreeCADGui.Selection.clearSelection()
        FreeCADGui.Selection.addSelection(
            doc.getObject(selected.Object1), selected.SubElement1)

        FreeCADGui.Selection.addSelection(
            doc.getObject(selected.Object2), selected.SubElement2)

        # Add observer to remove the transparency when the selection is changing or removing
        FreeCADGui.Selection.addObserver(ViewConnectionsObserver(initialTransparencyState))

    def IsActive(self):
        #return (a2plib.getSelectedConstraint() is not None and a2plib.isTransparencyEnabled() == False)
        return (a2plib.getSelectedConstraint() is not None)
    
    def GetResources(self):
        return {
            'Pixmap'  :     a2plib.pathOfModule()+'/icons/a2p_ViewConnection.svg',
            'MenuText':     'Highlight both constrained parts',
            'ToolTip':      toolTip,
            }

FreeCADGui.addCommand('a2p_ViewConnectionsCommand', ViewConnectionsCommand())

class ViewConnectionsObserver:
    def __init__(self,initialTransparencyState):
        self.ignoreClear = False
        self.initialTransparencyState = initialTransparencyState
        a2plib.setConstraintViewMode(True)

    def clearSelection(self, doc):
        if self.ignoreClear:
            self.ignoreClear = False
        else:
            # remove observer at once, as restoreTransparency would trigger it again...
            FreeCADGui.Selection.removeObserver(self)
            #
            if a2plib.isTransparencyEnabled() and not self.initialTransparencyState:
                a2plib.restoreTransparency()
            a2plib.setConstraintViewMode(False)

    def setSelection(self, doc):
        selected = a2plib.getSelectedConstraint()
        if selected is not None:
            self.ignoreClear = True
            FreeCADGui.Selection.clearSelection()
            FreeCADGui.Selection.addSelection(
                FreeCAD.ActiveDocument.getObject(selected.Object1), selected.SubElement1)

            FreeCADGui.Selection.addSelection(
                FreeCAD.ActiveDocument.getObject(selected.Object2), selected.SubElement2)

toolTip = \
'''
Show only selected elements,
or all if none is selected.

Select one ore more parts,
which are the only ones you
want to see in a big assembly.

Hit this button, and all other
parts will be made invisible.

If you select nothing and hit
this button, all invisible parts
will be made visible again.
'''

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
            'MenuText': 'Show only selected elements or all if none is selected',
            'ToolTip': toolTip
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

    def IsActive(self):
        return not a2plib.getConstraintViewMode()

    def GetResources(self):
        return {
            'Pixmap'  :     a2plib.pathOfModule()+'/icons/a2p_ToggleTransparency.svg',
            'MenuText':     'Toggle transparency of assembly',
            'ToolTip':      'Toggles transparency of assembly',
            'Checkable':    self.IsChecked()
        }
FreeCADGui.addCommand('a2p_ToggleTransparencyCommand', a2p_ToggleTransparencyCommand())



toolTipMessage = \
'''
Toggle AutoSolve

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
            'MenuText':     'Toggle auto solve',
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
            'MenuText':     'Toggle partial processing',
            'ToolTip':      'Toggles partial processing',
            'Checkable':    self.IsChecked()
            }
FreeCADGui.addCommand('a2p_TogglePartialProcessingCommand', a2p_TogglePartialProcessingCommand())



toolTipMessage = \
'''
Repair the treeview, if it
is damaged somehow.

After pressing this button,
constraints will grouped under
corresponding parts again.
'''

class a2p_repairTreeViewCommand:

    def Activated(self):
        if FreeCAD.activeDocument() == None:
            QtGui.QMessageBox.information(  QtGui.QApplication.activeWindow(),
                                        "No active document found!",
                                        "You have to open an assembly file first."
                                    )
            return
        a2plib.a2p_repairTreeView()

    def GetResources(self):
        return {
            'Pixmap'  :     a2plib.pathOfModule()+'/icons/a2p_RepairTree.svg',
            'MenuText':     'Repair the tree view if it is somehow damaged',
            'ToolTip':      toolTipMessage
            }
FreeCADGui.addCommand('a2p_repairTreeViewCommand', a2p_repairTreeViewCommand())

toolTip = \
'''
Flip direction of last constraint.

If the last constraint, which has
been defined, has a property
'direction', its value will be
toggled between 'aligned' and
'opposed' (alignment of axis)
'''


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
            'Pixmap'  :     a2plib.pathOfModule()+'/icons/a2p_FlipConstraint.svg',
            'MenuText':     'Flip direction of last constraint',
            'ToolTip':      toolTip
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
            'Pixmap'  :     a2plib.pathOfModule()+'/icons/a2p_Treeview.svg',
            'MenuText':     'Generate HTML file with detailed constraining structure',
            'ToolTip':      'Generates HTML file with detailed constraining structure'
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
            'MenuText':     'Print detailed DOF information to console',
            'ToolTip':      'Prints detailed DOF information to console'
            }
FreeCADGui.addCommand('a2p_Show_DOF_info_Command', a2p_Show_DOF_info_Command())



tt = \
'''
Remove the DOF information labels
from the 3D view, which were created
by the detailed DOF info command.
'''

class a2p_Remove_DOF_Labels_Command:

    def Activated(self):
        doc = FreeCAD.activeDocument()
        dofGroup = doc.getObject("dofLabels")
        if dofGroup != None:
            for lbl in dofGroup.Group:
                doc.removeObject(lbl.Name)
            doc.removeObject("dofLabels")

    def IsActive(self):
        doc = FreeCAD.activeDocument()
        dofGroup = doc.getObject("dofLabels")
        return dofGroup != None

    def GetResources(self):
        return {
            'Pixmap'  :     a2plib.pathOfModule()+'/icons/a2p_Unlabel_DOFs.svg',
            'MenuText':     'Remove DOF-labels from 3D view',
            'ToolTip':      tt
            }
FreeCADGui.addCommand('a2p_Remove_DOF_Labels_Command', a2p_Remove_DOF_Labels_Command())



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
            'Pixmap'  :     a2plib.pathOfModule()+'/icons/a2p_SetRelativePathes.svg',
            'MenuText':     'Convert absolute paths of imported parts to relative ones',
            'ToolTip':      'Converts absolute paths of imported parts to relative ones'
            }
FreeCADGui.addCommand('a2p_absPath_to_relPath_Command', a2p_absPath_to_relPath_Command())




class a2p_SaveAndExit_Command:
    def Activated(self):
        doc = FreeCAD.activeDocument()
        try:
            doc.save()
        except:
            FreeCADGui.SendMsgToActiveView("Save")            
        FreeCAD.closeDocument(doc.Name)
        #
        mw = FreeCADGui.getMainWindow()
        mdi = mw.findChild(QtGui.QMdiArea)
        sub = mdi.activeSubWindow()
        if sub != None:
            sub.showMaximized()
            
    def IsActive(self):
        return FreeCAD.activeDocument() != None
            
    def GetResources(self):
        return {
            'Pixmap'  :     a2plib.pathOfModule()+'/icons/a2p_Save_and_exit.svg',
            'MenuText':     'Save and exit the active document',
            'ToolTip':      'Save and exit the active document'
            }
FreeCADGui.addCommand('a2p_SaveAndExit_Command', a2p_SaveAndExit_Command())





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
            message = "Constraint %s is broken. Delete constraint? Otherwise check for wrong linkage." % cName
            #response = QtGui.QMessageBox.critical(QtGui.qApp.activeWindow(), "Broken Constraint", message, flags )
            response = QtGui.QMessageBox.critical(None, "Broken Constraint", message, flags )
        
            if response == QtGui.QMessageBox.Yes:
                FreeCAD.Console.PrintError("Removing constraint %s" % cName)
                c = doc.getObject(cName)
                a2plib.removeConstraint(c)
                


