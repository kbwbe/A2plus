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
import copy
import sys
import platform
from a2p_translateUtils import *
import a2plib
from a2p_MuxAssembly import muxAssemblyWithTopoNames
from a2p_versionmanagement import A2P_VERSION
import a2p_solversystem
from a2plib import getRelativePathesEnabled
import a2p_importedPart_class
import a2p_convertPart

from a2p_topomapper import TopoMapper

import a2p_lcs_support
from a2p_importedPart_class import Proxy_importPart, ImportedPartViewProviderProxy
import a2p_constraintServices

PYVERSION =  sys.version_info[0]

#==============================================================================
class DataContainer():
    def __init__(self):
        self.tx = None
#==============================================================================
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

#==============================================================================
class a2p_multiShapeExtractDialog(QtGui.QDialog):
    '''
    select a label from shape which has to be imported from a file
    '''
    Deleted = QtCore.Signal()
    Accepted = QtCore.Signal()

    def __init__(self, parent, labelList = [], iconList = [], data = None):
        super(a2p_multiShapeExtractDialog,self).__init__(parent=parent)
        self.labelList = labelList
        self.iconList = iconList
        self.data = data
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Import Objects')
        self.mainLayout = QtGui.QGridLayout() # a VBoxLayout for the whole form

        lzip = sorted(zip(self.labelList, self.iconList))
        self.labelList = [li[0] for li in lzip]
        self.iconList = [li[1] for li in lzip]
        l = self.labelList

        self.label = QtGui.QLabel(self)
        self.label.setText("Select objects to import")

        self.listView = QtGui.QListWidget()
        for i, item in enumerate(l):
            icon = self.iconList[i]
            item = QtGui.QListWidgetItem(item)
            item.setIcon(icon)
            item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable)
            item.setCheckState(QtCore.Qt.Unchecked)
            self.listView.addItem(item)

        self.buttons = QtGui.QDialogButtonBox(self)
        self.buttons.setOrientation(QtCore.Qt.Horizontal)
        self.buttons.addButton("Cancel", QtGui.QDialogButtonBox.RejectRole)
        self.buttons.addButton("Import", QtGui.QDialogButtonBox.AcceptRole)
        self.connect(self.buttons, QtCore.SIGNAL("accepted()"), self, QtCore.SLOT("accept()"))
        self.connect(self.buttons, QtCore.SIGNAL("rejected()"), self, QtCore.SLOT("reject()"))

        self.mainLayout.addWidget(self.label)
        self.mainLayout.addWidget(self.listView)
        self.mainLayout.addWidget(self.buttons)
        self.setLayout(self.mainLayout)

    def accept(self):
        if self.data != None:

            checked_items = []
            for index in range(self.listView.count()):
                if self.listView.item(index).checkState() == QtCore.Qt.Checked:
                    checked_items.append(self.listView.item(index).text())

            if checked_items:
                for i in checked_items:
                    print("Importing", i)

            self.data.tx = checked_items

        self.deleteLater()

    def reject(self):
        self.deleteLater()


#==============================================================================
class a2p_shapeExtractDialog(QtGui.QDialog):
    '''
    select a label from shape which has to be imported from a file
    '''
    Deleted = QtCore.Signal()
    Accepted = QtCore.Signal()


    def __init__(self,parent,labelList = [], data = None):
        super(a2p_shapeExtractDialog,self).__init__(parent=parent)
        #super(a2p_shapeExtractDialog,self).__init__()
        self.labelList = labelList
        self.data = data
        self.initUI()

    def initUI(self):
        self.resize(400,100)
        self.setWindowTitle('select a shape to be imported')
        self.mainLayout = QtGui.QGridLayout() # a VBoxLayout for the whole form

        self.shapeCombo = QtGui.QComboBox(self)

        l = sorted(self.labelList)
        self.shapeCombo.addItems(l)

        self.buttons = QtGui.QDialogButtonBox(self)
        self.buttons.setOrientation(QtCore.Qt.Horizontal)
        self.buttons.addButton("Cancel", QtGui.QDialogButtonBox.RejectRole)
        self.buttons.addButton("Choose", QtGui.QDialogButtonBox.AcceptRole)
        self.connect(self.buttons, QtCore.SIGNAL("accepted()"), self, QtCore.SLOT("accept()"))
        self.connect(self.buttons, QtCore.SIGNAL("rejected()"), self, QtCore.SLOT("reject()"))

        self.mainLayout.addWidget(self.shapeCombo,0,0,1,1)
        self.mainLayout.addWidget(self.buttons,1,0,1,1)
        self.setLayout(self.mainLayout)

    def accept(self):
        if self.data != None:
            self.data.tx = self.shapeCombo.currentText()
        self.deleteLater()

    def reject(self):
        self.deleteLater()

#==============================================================================
def importPartFromFile(
        _doc,
        filename,
        extractSingleShape = False, # load only a single user defined shape from file
        desiredShapeLabel=None,
        importToCache=False,
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
            fname =  os.path.splitext(os.path.basename(filename))[0]
            FreeCAD.newDocument(fname)
            newname = FreeCAD.ActiveDocument.Name
            FreeCAD.setActiveDocument(newname)
            ImportGui.insert(filename,newname)
            importDoc = FreeCAD.ActiveDocument
        else:
            msg = translate("A2plus_importpart","A part can only be imported from a FreeCAD '*.FCStd' file")
            QtGui.QMessageBox.information( QtGui.QApplication.activeWindow(), translate("A2plus_importpart","Value Error"), msg )
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
    importableObjects = topoMapper.getTopLevelObjects(allowSketches=True)

    if len(importableObjects) == 0:
        msg = translate("A2plus_importpart","No visible Part to import found. Aborting operation")
        QtGui.QMessageBox.information(
            QtGui.QApplication.activeWindow(),
            translate("A2plus_importpart","Import Error"),
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
                msg = translate("A2plus_importpart","Import of a shape reference aborted by user")
                QtGui.QMessageBox.information(
                    QtGui.QApplication.activeWindow(),
                    translate("A2plus_importpart","Import Error"),
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
        newObj = doc.addObject("Part::FeaturePython",partName)
        newObj.Label = partName
    else:
        partName = a2plib.findUnusedObjectName( importDoc.Label, document=doc )
        if extractSingleShape == False:
            partLabel = a2plib.findUnusedObjectLabel( importDoc.Label, document=doc )
        else:
            partLabel = a2plib.findUnusedObjectLabel(
                importDoc.Label,
                document=doc,
                extension=dc.tx
                )
        if PYVERSION < 3:
            newObj = doc.addObject( "Part::FeaturePython", partName.encode('utf-8') )
        else:
            newObj = doc.addObject( "Part::FeaturePython", str(partName.encode('utf-8')) )    # works on Python 3.6.5
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

    newObj.setEditorMode("timeLastImport",1)
    newObj.timeLastImport = os.path.getmtime( filename )
    if a2plib.getForceFixedPosition():
        newObj.fixedPosition = True
    else:
        newObj.fixedPosition = not any([i.fixedPosition for i in doc.Objects if hasattr(i, 'fixedPosition') ])
    newObj.subassemblyImport = subAssemblyImport
    newObj.setEditorMode("subassemblyImport",1)

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
    newObj.setEditorMode("objectType",1)

    doc.recompute()

    if importToCache: # this import is used to update already imported parts
        objectCache.add(cacheKey, newObj)
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

        a2p_lcs_support.LCS_Group(lcsGroup)
        a2p_lcs_support.VP_LCS_Group(lcsGroup.ViewObject)

        for lcs in lcsList:
            lcsGroup.addObject(lcs)

        lcsGroup.Owner = newObj.Name

        newObj.addProperty("App::PropertyLinkList","lcsLink","importPart").lcsLink = lcsGroup
        newObj.Label = newObj.Label # this is needed to trigger an update
        lcsGroup.Label = lcsGroup.Label

        #=========================================

    return newObj


#==============================================================================
toolTip = \
translate("A2plus_importpart",
'''
Add shapes from an external file
to the assembly
'''
)

class a2p_ImportShapeReferenceCommand():

    def GetResources(self):
        return {'Pixmap'  : a2plib.pathOfModule()+'/icons/a2p_ShapeReference.svg',
                'Accel' : "Ctrl+Shift+A", # a default shortcut (optional)
                'MenuText': translate("A2plus_importpart","Add shapes from an external file"),
                'ToolTip' : toolTip
                }

    def Activated(self):
        if FreeCAD.ActiveDocument is None:
            QtGui.QMessageBox.information(
                QtGui.QApplication.activeWindow(),
               translate("A2plus_importpart","No active Document found"),
               translate("A2plus_importpart","First create an empty file and save it under desired name")
               )
            return
        #
        if FreeCAD.ActiveDocument.FileName == '':
            QtGui.QMessageBox.information(
                QtGui.QApplication.activeWindow(),
               translate("A2plus_importpart","Unnamed document"),
               translate("A2plus_importpart","Before inserting first part, please save the empty assembly to give it a name")
               )
            FreeCADGui.SendMsgToActiveView("Save")
            return

        doc = FreeCAD.activeDocument()
        guidoc = FreeCADGui.activeDocument()
        view = guidoc.activeView()

        dialog = QtGui.QFileDialog(
            QtGui.QApplication.activeWindow(),
            translate("A2plus_importpart","Select FreeCAD document to import part from")
            )
        # set option "DontUseNativeDialog"=True, as native Filedialog shows
        # misbehavior on Unbuntu 18.04 LTS. It works case sensitively, what is not wanted...
        if a2plib.getNativeFileManagerUsage():
            dialog.setOption(QtGui.QFileDialog.DontUseNativeDialog, False)
        else:
            dialog.setOption(QtGui.QFileDialog.DontUseNativeDialog, True)
        dialog.setNameFilter(translate("A2plus_importpart","Supported Formats (*.FCStd *.fcstd *.stp *.step);;All files (*.*)"))
        if dialog.exec_():
            if PYVERSION < 3:
                filename = unicode(dialog.selectedFiles()[0])
            else:
                filename = str(dialog.selectedFiles()[0])
        else:
            return

        if not a2plib.checkFileIsInProjectFolder(filename):
            msg = translate("A2plus_importpart","The part you try to import is outside of your project-folder! Check your settings of A2plus preferences.")
            QtGui.QMessageBox.information(
                QtGui.QApplication.activeWindow(),
                translate("A2plus_importpart","Import Error"),
                msg
                )
            return



        #==========================================================================================
        # for multiple part import: first open the importDoc, if possible
        #==========================================================================================
        # look only for filenames, not paths, as there are problems on WIN10 (Address-translation??)
        #==========================================================================================
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
                msg = translate("A2plus_importpart","A part can only be imported from a FreeCAD '*.FCStd' file")
                QtGui.QMessageBox.information( QtGui.QApplication.activeWindow(), translate("A2plus_importpart","Value Error"), msg )
                return
        #==========================================================================================
        # file seems to be open....
        # detect the importable objects...
        #==========================================================================================
        topoMapper = TopoMapper(importDoc)
        importableObjects = topoMapper.getTopLevelObjects(allowSketches=True)

        if len(importableObjects) == 0:
            msg = "No visible Part to import found. Aborting operation"
            QtGui.QMessageBox.information(
                QtGui.QApplication.activeWindow(),
                translate("A2plus_importpart","Import Error"),
                msg
                )
            return

        #==========================================================================================
        # creates a dialog for selecting the parts
        #==========================================================================================
        labelList = []
        iconList = []
        dc = DataContainer()

        for io in importableObjects:
            labelList.append(io.Label)
            iconList.append(io.ViewObject.Icon)

        dialog = a2p_multiShapeExtractDialog(
                QtGui.QApplication.activeWindow(),
                labelList, iconList,
                dc
                )
        dialog.exec_()

        if dialog.rejected:
            FreeCAD.closeDocument(importDoc.Name)

        if dc.tx is None or len(dc.tx)==0:
            return

        selectedObjects = dc.tx
        importedObjectsList = []
        for so in selectedObjects:
            importedObject = importPartFromFile(doc, filename, extractSingleShape=True, desiredShapeLabel = so)

            if not importedObject:
                a2plib.Msg(translate("A2plus_importpart","imported Object is empty/none\n"))
                continue

            importedObjectsList.append(importedObject)
        try:
            FreeCAD.closeDocument(importDoc.Name) #avoid errormessage if doc already closed...
        except:
            pass

        mw = FreeCADGui.getMainWindow()
        mdi = mw.findChild(QtGui.QMdiArea)
        sub = mdi.activeSubWindow()
        if sub != None:
            sub.showMaximized()

        self.timer = QtCore.QTimer()
        QtCore.QObject.connect(self.timer, QtCore.SIGNAL("timeout()"), self.GuiViewFit)
        self.timer.start( 200 ) #0.2 seconds

        for io in importedObjectsList:
            if io and a2plib.isA2pSketch(io):
                if not any([i.fixedPosition for i in doc.Objects if hasattr(i, 'fixedPosition') ]):
                    io.fixedPosition = True

        # At first, make all imported Objects invisible,
        for io in importedObjectsList:
            io.ViewObject.Visibility = False

        for io in importedObjectsList:
            io.ViewObject.Visibility = True # make imported objects visible step by step,
                                            # in order to see, which one is recently being placed..
            if io and not a2plib.isA2pSketch(io) and not io.fixedPosition:
                pm = PartMover( view, io, deleteOnEscape = True )
                while pm.isActive:
                    FreeCADGui.updateGui() # keeping the UI responsible
                del pm

        return

    def IsActive(self):
        doc = FreeCAD.activeDocument()
        if doc is None: return False
        return True

    def GuiViewFit(self):
        FreeCADGui.SendMsgToActiveView("ViewFit")
        self.timer.stop()


FreeCADGui.addCommand('a2p_ImportShapeReferenceCommand',a2p_ImportShapeReferenceCommand())

#==============================================================================
toolTip = \
translate("A2plus_importpart",
'''
Restore transparency to
active document objects
'''
)

class a2p_Restore_Transparency_Command():

    def GetResources(self):
        return {'Pixmap'  : a2plib.pathOfModule()+'/icons/a2p_Restore_Transparency.svg',
                'Accel'   : "Shift+T", # a default shortcut (optional)
                'MenuText': translate("A2plus_importpart", "Restore transparency to active document objects"),
                'ToolTip' : toolTip
                }

    def Activated(self):
        doc = FreeCAD.ActiveDocument
        if doc is None:
            FreeCAD.Console.Print("No active document found")
            return
        else:
            for obj in doc.Objects:
                if hasattr (obj, 'ViewObject'):
                    if hasattr (obj.ViewObject, 'Transparency'):
                        if obj.ViewObject.Transparency < 100:
                            transparency = obj.ViewObject.Transparency
                            obj.ViewObject.Transparency = transparency + 1
                            obj.ViewObject.Transparency = transparency
        return

    def IsActive(self):
        doc = FreeCAD.activeDocument()
        if doc is None: return False
        return True

FreeCADGui.addCommand('a2p_Restore_Transparency',a2p_Restore_Transparency_Command())

#==============================================================================
toolTip = \
translate("A2plus_importpart",
'''
Add a part from an external file
to the assembly
'''
)

class a2p_ImportPartCommand():

    def GetResources(self):
        return {'Pixmap'  : a2plib.pathOfModule()+'/icons/a2p_ImportPart.svg',
                'Accel'   : "Shift+A", # a default shortcut (optional)
                'MenuText': translate("A2plus_importpart", "Add a part from an external file"),
                'ToolTip' : toolTip
                }

    def Activated(self):
        if FreeCAD.ActiveDocument is None:
            QtGui.QMessageBox.information(
                QtGui.QApplication.activeWindow(),
               translate("A2plus_importpart","No active Document found"),
               translate("A2plus_importpart","First create an empty file and save it under desired name")
               )
            return
        #
        if FreeCAD.ActiveDocument.FileName == '':
            QtGui.QMessageBox.information(
                QtGui.QApplication.activeWindow(),
               translate("A2plus_importpart","Unnamed document"),
               translate("A2plus_importpart","Before inserting first part, please save the empty assembly to give it a name")
               )
            FreeCADGui.SendMsgToActiveView("Save")
            return

        doc = FreeCAD.activeDocument()
        guidoc = FreeCADGui.activeDocument()
        view = guidoc.activeView()

        dialog = QtGui.QFileDialog(
            QtGui.QApplication.activeWindow(),
            translate("A2plus_importpart","Select FreeCAD document to import part from")
            )
        # set option "DontUseNativeDialog"=True, as native Filedialog shows
        # misbehavior on Unbuntu 18.04 LTS. It works case sensitively, what is not wanted...
        if a2plib.getNativeFileManagerUsage():
            dialog.setOption(QtGui.QFileDialog.DontUseNativeDialog, False)
        else:
            dialog.setOption(QtGui.QFileDialog.DontUseNativeDialog, True)
        dialog.setNameFilter(translate("A2plus_importpart","Supported Formats (*.FCStd *.fcstd *.stp *.step);;All files (*.*)"))
        if dialog.exec_():
            if PYVERSION < 3:
                filename = unicode(dialog.selectedFiles()[0])
            else:
                filename = str(dialog.selectedFiles()[0])
        else:
            return

        if not a2plib.checkFileIsInProjectFolder(filename):
            msg = translate("A2plus_importpart","The part you try to import is outside of your project-folder! Check your settings of A2plus preferences.")
            QtGui.QMessageBox.information(
                QtGui.QApplication.activeWindow(),
                translate("A2plus_importpart","Import Error"),
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
            PartMover( view, importedObject, deleteOnEscape = True )
        else:
            self.timer = QtCore.QTimer()
            QtCore.QObject.connect(self.timer, QtCore.SIGNAL("timeout()"), self.GuiViewFit)
            self.timer.start( 200 ) #0.2 seconds
        return

    def IsActive(self):
        doc = FreeCAD.activeDocument()
        if doc is None: return False
        return True

    def GuiViewFit(self):
        FreeCADGui.SendMsgToActiveView("ViewFit")
        self.timer.stop()


FreeCADGui.addCommand('a2p_ImportPart',a2p_ImportPartCommand())
#==============================================================================




def updateImportedParts(doc, partial=False):
    if doc is None:
        QtGui.QMessageBox.information(
                        QtGui.QApplication.activeWindow(),
                        translate("A2plus_importpart","No active document found!"),
                        translate("A2plus_importpart","Before updating parts, you have to open an assembly file.")
                        )
        return

    doc.openTransaction("updateImportParts")
    objectCache.cleanUp(doc)


    selectedObjects=[]
    selection = [s for s in FreeCADGui.Selection.getSelection()
                 if s.Document == FreeCAD.ActiveDocument and
                 (a2plib.isA2pPart(s) or a2plib.isA2pSketch(s))
                 ]
    if selection and len(selection)>0:
        if partial==True:
            response = QtGui.QMessageBox.Yes
        else:
            flags = QtGui.QMessageBox.StandardButton.Yes | QtGui.QMessageBox.StandardButton.No
            msg = translate("A2plus_importpart","Do you want to update only the selected parts?")
            response = QtGui.QMessageBox.information(
                            QtGui.QApplication.activeWindow(),
                            translate("A2plus_importpart","ASSEMBLY UPDATE"),
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
        if hasattr(obj, 'sourceFile') and a2plib.to_str(obj.sourceFile) == a2plib.to_str('converted'):
            if hasattr(obj,'localSourceObject') and obj.localSourceObject is not None and obj.localSourceObject != "":
                a2p_convertPart.updateConvertedPart(doc, obj)
            continue

        if hasattr(obj, 'sourceFile') and a2plib.to_str(obj.sourceFile) != a2plib.to_str('converted'):


            #repair data structures (perhaps an old Assembly2 import was found)
            if hasattr(obj,"Content") and 'importPart' in obj.Content: # be sure to have an assembly object
                if obj.Proxy is None:
                    #print (u"Repair Proxy of: {}, Proxy: {}".format(obj.Label, obj.Proxy))
                    Proxy_importPart(obj)
                    ImportedPartViewProviderProxy(obj.ViewObject)

            assemblyPath = os.path.normpath(os.path.split(doc.FileName)[0])
            absPath = a2plib.findSourceFileInProject(obj.sourceFile, assemblyPath)

            if absPath is None:
                QtGui.QMessageBox.critical(  QtGui.QApplication.activeWindow(),
                                            translate("A2plus_importpart","Source file not found"),
                                            translate("A2plus_importpart","Unable to find {}").format(
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
                                importToCache=True,
                                cacheKey = cacheKey,
                                extractSingleShape = True,
                                desiredShapeLabel = obj.sourcePart
                                ) # the version is now in the cache
                        else:
                            importPartFromFile(
                                doc,
                                absPath,
                                importToCache=True,
                                cacheKey = cacheKey
                                ) # the version is now in the cache

                    newObject = objectCache.get(cacheKey)
                    obj.timeLastImport = newPartCreationTime
                    if hasattr(newObject, 'a2p_Version'):
                        obj.a2p_Version = A2P_VERSION
                    importUpdateConstraintSubobjects( doc, obj, newObject ) # do this before changing shape and mux
                    if hasattr(newObject, 'muxInfo'):
                        obj.muxInfo = newObject.muxInfo
                    # save Placement because following newObject.Shape.copy() isn't resetting it to zeroes...
                    savedPlacement  = obj.Placement
                    obj.Shape = newObject.Shape.copy()
                    if a2plib.isA2pSketch(obj):
                        pass
                    else:
                        obj.Placement = savedPlacement # restore the old placement
                    a2plib.copyObjectColors(obj,newObject)

    #repair constraint directions if for e.g. face-normals flipped around during updating of parts.
    a2p_constraintServices.redAdjustConstraintDirections(doc)

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
translate("A2plus_importpart",
'''
Update parts, which have been
imported to the assembly.

(If you modify a part in an
external file, the new shape
is taken to the assembly by
this function.)
'''
)
class a2p_UpdateImportedPartsCommand:

    def Activated(self):
        doc = FreeCAD.ActiveDocument
        updateImportedParts(doc)

    def GetResources(self):
        return {
            'Pixmap'  : a2plib.path_a2p + '/icons/a2p_ImportPart_Update.svg',
            'MenuText': translate("A2plus_importpart", "Update parts imported into the assembly"),
            'ToolTip' : toolTip
            }

FreeCADGui.addCommand('a2p_updateImportedParts', a2p_UpdateImportedPartsCommand())



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

    Proxy_importPart(newObj)
    ImportedPartViewProviderProxy(newObj.ViewObject)


    newObj.a2p_Version = part.a2p_Version
    newObj.sourceFile = part.sourceFile
    newObj.sourcePart = part.sourcePart
    newObj.localSourceObject = part.localSourceObject
    newObj.timeLastImport =  part.timeLastImport
    newObj.setEditorMode("timeLastImport",1)
    newObj.fixedPosition = False
    newObj.updateColors = getattr(part,'updateColors',True)
    newObj.muxInfo = part.muxInfo
    newObj.subassemblyImport = part.subassemblyImport
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
translate("A2plus_importpart",
'''
Make a duplicate of a
part, which is already
imported to the assembly.

Select a imported part and hit
this button. A duplicate
will be created and can be
placed somewhere by mouse.

Hold "Shift" for doing this
multiple times.
'''
)
class a2p_DuplicatePartCommand:

    def __init__(self):
        self.partMover = None

    def Activated(self):
        doc = FreeCAD.activeDocument()
        selection = [s for s in FreeCADGui.Selection.getSelectionEx() if s.Document == doc ]
        self.partMover = PartMover(
            FreeCADGui.activeDocument().activeView(),
            duplicateImportedPart(selection[0].Object),
            deleteOnEscape = True
            )
        self.timer = QtCore.QTimer()
        QtCore.QObject.connect(self.timer, QtCore.SIGNAL("timeout()"), self.onTimer)
        self.timer.start( 100 )

    def onTimer(self):
        if self.partMover != None:
            if self.partMover.objectToDelete != None:
                FreeCAD.activeDocument().removeObject(self.partMover.objectToDelete.Name)
                self.partMover.objectToDelete = None
        self.timer.start(100)

    def IsActive(self):
        doc = FreeCAD.activeDocument()
        if doc is None: return False
        #
        selection = [s for s in FreeCADGui.Selection.getSelectionEx() if s.Document == doc ]
        if len(selection) != 1: return False
        #
        obj = selection[0].Object
        if not a2plib.isA2pPart(obj): return False
        #
        return True

    def GetResources(self):
        return {
            'Pixmap'  : a2plib.pathOfModule()+'/icons/a2p_DuplicatePart.svg',
            'MenuText': translate("A2plus_importpart", "Create duplicate of a part"),
            'ToolTip' : toolTip
            }

FreeCADGui.addCommand('a2p_duplicatePart', a2p_DuplicatePartCommand())



toolTip = \
translate("A2plus_importpart",
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
)

class a2p_EditPartCommand:
    def Activated(self):
        doc = FreeCAD.activeDocument()
        selection = [s for s in FreeCADGui.Selection.getSelection() if s.Document == FreeCAD.ActiveDocument ]

        #====================================================
        # Do we deal with a converted Part ?
        #====================================================
        obj = selection[0]
        if obj.sourceFile == 'converted':
            try:
                originalPart = doc.getObject(obj.localSourceObject)
                FreeCADGui.Selection.clearSelection()
                FreeCADGui.Selection.addSelection(originalPart)

                QtGui.QMessageBox.information(
                    QtGui.QApplication.activeWindow(),
                    translate("A2plus_importpart","Information"),
                    translate("A2plus_importpart","Please edit the highlighted object. When finished, update the assembly")
                    )
                return
            except:
                pass
            QtGui.QMessageBox.critical(
                QtGui.QApplication.activeWindow(),
                translate("A2plus_importpart","File error ! "),
                translate("A2plus_importpart","Cannot find the local source object. Has it been deleted?")
                )
            return



        #====================================================
        # Does the file exist ?
        #====================================================
        obj = selection[0]
        FreeCADGui.Selection.clearSelection() # very important! Avoid Editing the assembly the part was called from!
        assemblyPath = os.path.normpath(os.path.split(doc.FileName)[0])
        fileNameWithinProjectFile = a2plib.findSourceFileInProject(obj.sourceFile, assemblyPath)
        if fileNameWithinProjectFile is None:
            msg = translate("A2plus_importpart","You want to edit a file which is not found below your project-folder. This is not allowed when using preference Use project Folder")
            QtGui.QMessageBox.critical(
                QtGui.QApplication.activeWindow(),
                translate("A2plus_importpart","File error ! "),
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
                msg = translate("A2plus_importpart","Editing a STEP file as '*.FCStd' file\nPlease export the saved file as \'.step\'\n") + fileNameWithinProjectFile
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

    def IsActive(self):
        doc = FreeCAD.activeDocument()
        if doc is None: return False

        selection = [s for s in FreeCADGui.Selection.getSelection() if s.Document == FreeCAD.ActiveDocument ]
        if len(selection) != 1: return False

        if not a2plib.isEditableA2pPart(selection[0]): return False

        return True

    def GetResources(self):
        return {
            'Pixmap'  : a2plib.pathOfModule()+'/icons/a2p_EditPart.svg',
            'MenuText': translate("A2plus_importpart", "Edit an imported part (open linked FCStd file)"),
            'ToolTip' : toolTip
            }

FreeCADGui.addCommand('a2p_editImportedPart', a2p_EditPartCommand())




#===============================================================================
class PartMover:
    def __init__(self, view, obj, deleteOnEscape):
        self.obj = obj
        self.initialPosition = self.obj.Placement.Base
        self.view = view
        self.deleteOnEscape = deleteOnEscape
        self.callbackMove = self.view.addEventCallback("SoLocation2Event",self.moveMouse)
        self.callbackClick = self.view.addEventCallback("SoMouseButtonEvent",self.clickMouse)
        self.callbackKey = self.view.addEventCallback("SoKeyboardEvent",self.KeyboardEvent)
        self.objectToDelete = None # object reference when pressing the escape key
        self.isActive = True

    def moveMouse(self, info):
        newPos = self.view.getPoint( *info['Position'] )
        self.obj.Placement.Base = newPos

    def removeCallbacks(self):
        self.view.removeEventCallback("SoLocation2Event",self.callbackMove)
        self.view.removeEventCallback("SoMouseButtonEvent",self.callbackClick)
        self.view.removeEventCallback("SoKeyboardEvent",self.callbackKey)
        self.isActive = False

    def clickMouse(self, info):
        if info['Button'] == 'BUTTON1' and info['State'] == 'DOWN':
            #if not info['ShiftDown'] and not info['CtrlDown']: #struggles within Inventor Navigation
            if not info['ShiftDown']:
                self.removeCallbacks()
                FreeCAD.activeDocument().recompute()
            elif info['ShiftDown']:
                self.obj = duplicateImportedPart(self.obj)
                self.deleteOnEscape = True

    def KeyboardEvent(self, info):
        if info['State'] == 'UP' and info['Key'] == 'ESCAPE':
            self.removeCallbacks()
            if not self.deleteOnEscape:
                self.obj.Placement.Base = self.initialPosition
            else:
                self.objectToDelete = self.obj #This can be asked by a timer in a calling func...
                #This causes a crash in FC0.19/Qt5/Py3
                #FreeCAD.activeDocument().removeObject(self.obj.Name)
#===============================================================================
toolTip = \
translate("A2plus_importpart",
'''
Move the selected part.

Select a part and hit this
button. The part can be moved
around by mouse.

If the part is constrained, it
will jump back by next solving
of the assembly.
'''
)

class a2p_MovePartCommand:

    def __init__(self):
        self.partMover = None

    def Activated(self):
        doc = FreeCAD.activeDocument()
        selection = [s for s in FreeCADGui.Selection.getSelectionEx() if s.Document == doc ]
        FreeCADGui.ActiveDocument.setEdit(selection[0].Object)

    def IsActive(self):
        doc = FreeCAD.activeDocument()
        if doc is None: return False
        #
        selection = [s for s in FreeCADGui.Selection.getSelectionEx() if s.Document == doc ]
        if len(selection) != 1: return False
        #
        obj = selection[0].Object
        if not a2plib.isA2pPart(obj): return False
        #
        return True

    def GetResources(self):
        return {
            #'Pixmap' : ':/assembly2/icons/MovePart.svg',
            'Pixmap'  : a2plib.pathOfModule()+'/icons/a2p_MovePart.svg',
            'MenuText': translate("A2plus_importpart", "Move the selected part"),
            'ToolTip' : toolTip
            }

FreeCADGui.addCommand('a2p_movePart', a2p_MovePartCommand())
#===============================================================================
class ConstrainedPartsMover:
    def __init__(self, view):
        self.obj = None
        self.view = view
        self.doc = FreeCAD.activeDocument()
        self.callbackMove = self.view.addEventCallback("SoLocation2Event",self.onMouseMove)
        self.callbackClick = self.view.addEventCallback("SoMouseButtonEvent",self.onMouseClicked)
        self.callbackKey = self.view.addEventCallback("SoKeyboardEvent",self.KeyboardEvent)
        self.motionActivated = False

    def setPreselection(self,doc,obj,sub):
        if not self.motionActivated:
            doc = FreeCAD.activeDocument()
            self.obj = doc.getObject(obj)

    def addSelection(self,doc,obj,sub,pnt):
        pass

    def removeSelection(self,doc,obj,sub):
        pass

    def clearSelection(self,doc):
        pass

    def onMouseMove(self, info):
        if self.obj is None: return
        if self.motionActivated:
            newPos = self.view.getPoint( *info['Position'] )
            self.obj.Placement.Base = newPos
            a2plib.setSimulationState(True)
            systemSolved = a2p_solversystem.solveConstraints(self.doc, useTransaction = False)
            a2plib.setSimulationState(False)
            if systemSolved == False:
                self.doc.commitTransaction()
                QtGui.QMessageBox.information(
                    QtGui.QApplication.activeWindow(),
                   translate("A2plus_importpart","Animation problem detected"),
                   translate("A2plus_importpart","Use system undo if necessary.")
                   )
                self.removeCallbacks()

    def removeCallbacks(self):
        self.view.removeEventCallback("SoLocation2Event",self.callbackMove)
        self.view.removeEventCallback("SoMouseButtonEvent",self.callbackClick)
        self.view.removeEventCallback("SoKeyboardEvent",self.callbackKey)
        FreeCADGui.Selection.removeObserver(self)

    def onMouseClicked(self, info):
        if self.obj is None: return
        if info['Button'] == 'BUTTON1' and info['State'] == 'DOWN':
            if hasattr(self.obj, 'fixedPosition') and self.obj.fixedPosition == True:
                QtGui.QMessageBox.information(
                    QtGui.QApplication.activeWindow(),
                   translate("A2plus_importpart","Invalid selection"),
                   translate("A2plus_importpart","A2plus will not move a part with property") + '''fixedPosition == True'''
                   )
                self.removeCallbacks()
                del self
            else:
                self.motionActivated = not self.motionActivated
                if self.motionActivated == True:
                    self.doc.openTransaction("drag constrained parts")
                if self.motionActivated == False:
                    # Solve last time with high accuracy to finish
                    a2plib.setSimulationState(False)
                    a2p_solversystem.solveConstraints(self.doc, useTransaction = False)
                    self.doc.commitTransaction()
                    self.removeCallbacks()

    def KeyboardEvent(self, info):
        doc = FreeCAD.activeDocument()
        if info['State'] == 'UP' and info['Key'] == 'ESCAPE':
            doc.commitTransaction()
            self.removeCallbacks()
#===============================================================================
toolTip = \
translate("A2plus_importpart",
'''
Move the a part under rule of constraints.

1) Hit this button
2) Click a part and it is glued to the cursor and can be moved
3) Click again (or press ESC) and the command terminates
'''
)

class a2p_MovePartUnderConstraints:

    def __init__(self):
        self.partMover = None

    def Activated(self):
        self.partMover = ConstrainedPartsMover(
                            FreeCADGui.activeDocument().activeView()
                            )
        FreeCADGui.Selection.addObserver(self.partMover)

    def IsActive(self):
        doc = FreeCAD.activeDocument()
        if doc is None: return False
        #
        #selection = [s for s in FreeCADGui.Selection.getSelectionEx() if s.Document == doc ]
        #if len(selection) != 1: return False
        #
        #obj = selection[0].Object
        #if not a2plib.isA2pPart(obj): return False
        #
        return True

    def GetResources(self):
        return {
            #'Pixmap' : ':/assembly2/icons/MovePart.svg',
            'Pixmap'  : a2plib.pathOfModule()+'/icons/a2p_MovePartUnderConstraints.svg',
            'MenuText': translate("A2plus_importpart", "Move the selected part under constraints"),
            'ToolTip' : toolTip
            }

FreeCADGui.addCommand('a2p_MovePartUnderConstraints', a2p_MovePartUnderConstraints())
#===============================================================================




toolTipText = \
translate("A2plus_importpart",
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
)

class DeleteConnectionsCommand:
    def Activated(self):
        selection = [s for s in FreeCADGui.Selection.getSelection() if s.Document == FreeCAD.ActiveDocument ]
        #if len(selection) == 1: not required as this check is done in initGui
        # WF: still get 'list index out of range' if nothing selected.
        if len(selection) != 1:
            QtGui.QMessageBox.critical(
                QtGui.QApplication.activeWindow(),
               translate("A2plus_importpart","Selection Error"),
               translate("A2plus_importpart","Select exactly 1 part"))
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
                translate("A2plus_importpart","Delete constraints?"),
                msg,
                flags
                )
            if response == QtGui.QMessageBox.Yes:
                doc = FreeCAD.activeDocument()
                doc.openTransaction(translate("A2plus_importpart","Deleting part's constraints"))
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
            'MenuText': translate("A2plus_importpart", "Delete all constraints of selected parts"),
            'ToolTip' : toolTipText
            }
FreeCADGui.addCommand('a2p_DeleteConnectionsCommand', DeleteConnectionsCommand())

toolTip = \
translate("A2plus_importpart",
'''
Highlight both parts, which are
related to a selected constraint.

Select a constraint within
the treeview and hit this button.

The whole assembly is switched to
transparent mode and you can inspect
the desired constraint.
'''
)

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
            'Pixmap'  : a2plib.pathOfModule()+'/icons/a2p_ViewConnection.svg',
            'MenuText': translate("A2plus_importpart", "Highlight both constrained parts"),
            'ToolTip' : toolTip
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
translate("A2plus_importpart",
'''
Show only selected elements,
or all if none is selected.

Select one or more parts,
which are the only ones you
want to see in a big assembly.

Hit this button, and all other
parts will be made invisible.

If you select nothing and hit
this button, all invisible parts
will be made visible again.
'''
)

class a2p_isolateCommand:

    def hasFaces(self,ob):
        if hasattr(ob,"Shape") and hasattr(ob.Shape,"Faces") and len(ob.Shape.Faces)>0:
            return True
        return False

    def Activated(self):
        if FreeCAD.activeDocument() is None:
            QtGui.QMessageBox.information(  QtGui.QApplication.activeWindow(),
                                        translate("A2plus_importpart","No active document found!"),
                                        translate("A2plus_importpart","You have to open an assembly file first.")
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
                if a2plib.isA2pConstraint(obj): continue
                if hasattr(obj,'ViewObject'):
                    if hasattr(obj.ViewObject,'Visibility'):
                        if obj in selection:
                            obj.ViewObject.Visibility = True
                        else:
                            obj.ViewObject.Visibility = False

    def GetResources(self):
        return {
            'Pixmap'  : a2plib.pathOfModule()+'/icons/a2p_Isolate_Element.svg',
            'MenuText': translate("A2plus_importpart", "Show only selected elements or all if none is selected"),
            'ToolTip' : toolTip
            }

FreeCADGui.addCommand('a2p_isolateCommand', a2p_isolateCommand())





class a2p_ToggleTransparencyCommand:
    def Activated(self, checked):
        if FreeCAD.activeDocument() is None:
            QtGui.QMessageBox.information(  QtGui.QApplication.activeWindow(),
                                        translate("A2plus_importpart","No active document found!"),
                                        translate("A2plus_importpart","You have to open an assembly file first.")
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
            'Pixmap'   : a2plib.pathOfModule()+'/icons/a2p_ToggleTransparency.svg',
            'MenuText' : translate("A2plus_importpart", "Toggle transparency of assembly"),
            'ToolTip'  : translate("A2plus_importpart", "Toggles transparency of assembly"),
            'Checkable': self.IsChecked()
        }
FreeCADGui.addCommand('a2p_ToggleTransparencyCommand', a2p_ToggleTransparencyCommand())



toolTipMessage = \
translate("A2plus_importpart",
'''
Toggle AutoSolve

By pressing this button you can
enable or disable automatic solving
after a constraint has been edited

If automatic solving is disabled
you have to start it manually
by hitting the solvebutton
'''
)

class a2p_ToggleAutoSolveCommand:

    def Activated(self, checked):
        a2plib.setAutoSolve(checked)

    def IsChecked(self):
        return a2plib.getAutoSolveState()

    def GetResources(self):
        return {
            'Pixmap'   : a2plib.pathOfModule()+'/icons/a2p_ToggleAutoSolve.svg',
            'MenuText' : translate("A2plus_importpart", "Toggle auto solve"),
            'ToolTip'  : toolTipMessage,
            'Checkable': self.IsChecked()
            }
FreeCADGui.addCommand('a2p_ToggleAutoSolveCommand', a2p_ToggleAutoSolveCommand())



class a2p_TogglePartialProcessingCommand:

    def Activated(self, checked):
        a2plib.setPartialProcessing(checked)

    def IsChecked(self):
        return a2plib.isPartialProcessing()

    def GetResources(self):
        return {
            'Pixmap'   : a2plib.pathOfModule()+'/icons/a2p_TogglePartial.svg',
            'MenuText' : translate("A2plus_importpart", "Toggle partial processing"),
            'ToolTip'  : translate("A2plus_importpart", "Toggle partial processing"),
            'Checkable': self.IsChecked()
            }
FreeCADGui.addCommand('a2p_TogglePartialProcessingCommand', a2p_TogglePartialProcessingCommand())



toolTipMessage = \
translate("A2plus_importpart","Repair the treeview, if it is damaged somehow. After pressing this button, constraints will grouped under corresponding parts again.")

class a2p_repairTreeViewCommand:

    def Activated(self):
        if FreeCAD.activeDocument() is None:
            QtGui.QMessageBox.information(  QtGui.QApplication.activeWindow(),
                                        translate("A2plus_importpart","No active document found!"),
                                        translate("A2plus_importpart","You have to open an assembly file first.")
                                    )
            return
        a2plib.a2p_repairTreeView()

    def GetResources(self):
        return {
            'Pixmap'  : a2plib.pathOfModule()+'/icons/a2p_RepairTree.svg',
            'MenuText': translate("A2plus_importpart", "Repair the tree view if it is somehow damaged"),
            'ToolTip' : toolTipMessage
            }
FreeCADGui.addCommand('a2p_repairTreeViewCommand', a2p_repairTreeViewCommand())

toolTip = \
translate("A2plus_importpart",
'''
Flip direction of last constraint.

If the last constraint, which has
been defined, has a property
'direction', its value will be
toggled between 'aligned' and
'opposed' (alignment of axis)
'''
)


class a2p_FlipConstraintDirectionCommand:

    def Activated(self):
        if FreeCAD.activeDocument() is None:
            QtGui.QMessageBox.information(  QtGui.QApplication.activeWindow(),
                                        translate("A2plus_importpart","No active document found!"),
                                        translate("A2plus_importpart","You have to open an assembly file first.")
                                    )
            return
        a2p_FlipConstraintDirection()

    def GetResources(self):
        return {
            'Pixmap'  : a2plib.pathOfModule()+'/icons/a2p_FlipConstraint.svg',
            'MenuText': translate("A2plus_importpart", "Flip direction of last constraint"),
            'ToolTip' : toolTip
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
        if doc is None:
            QtGui.QMessageBox.information(  QtGui.QApplication.activeWindow(),
                                        translate("A2plus_importpart","No active document found!"),
                                        translate("A2plus_importpart","You have to open an assembly file first.")
                                    )
            return
        ss = a2p_solversystem.SolverSystem()
        ss.loadSystem(doc)
        ss.assignParentship(doc)
        ss.visualizeHierarchy()

    def GetResources(self):
        return {
            'Pixmap'  : a2plib.pathOfModule()+'/icons/a2p_Treeview.svg',
            'MenuText': translate("A2plus_importpart", "Generate HTML file with detailed constraining structure"),
            'ToolTip' : translate("A2plus_importpart", "Generates HTML file with detailed constraining structure")
            }
FreeCADGui.addCommand('a2p_Show_Hierarchy_Command', a2p_Show_Hierarchy_Command())



class a2p_Show_PartLabels_Command:

    def Activated(self, index):
        doc = FreeCAD.activeDocument()
        if index == 0:
            '''remove labels from 3D view'''
            dofGroup = doc.getObject("partLabels")
            if dofGroup != None:
                for lbl in dofGroup.Group:
                    doc.removeObject(lbl.Name)
                doc.removeObject("partLabels")
        else:
            '''create or update labels within 3D view'''
            a2pObjects = []
            for ob in doc.Objects:
                if a2plib.isA2pPart(ob):
                    a2pObjects.append(ob)
            if len(a2pObjects) == 0:
                QtGui.QMessageBox.information(  QtGui.QApplication.activeWindow(),
                                            translate("A2plus_importpart","Nothing found to be labeled!"),
                                            translate("A2plus_importpart","This document does not contain A2p-objects")
                                        )
                return

            labelGroup = doc.getObject("partLabels")
            if labelGroup is None:
                labelGroup=doc.addObject("App::DocumentObjectGroup", "partLabels")
            else:
                for lbl in labelGroup.Group:
                    doc.removeObject(lbl.Name)
                doc.removeObject("partLabels")
                labelGroup=doc.addObject("App::DocumentObjectGroup", "partLabels")

            for ob in a2pObjects:
                if ob.ViewObject.Visibility == True:
                    bbCenter = ob.Shape.BoundBox.Center
                    partLabel = doc.addObject("App::AnnotationLabel","partLabel")
                    partLabel.LabelText = a2plib.to_str(ob.Label)
                    partLabel.BasePosition.x = bbCenter.x
                    partLabel.BasePosition.y = bbCenter.y
                    partLabel.BasePosition.z = bbCenter.z
                    #
                    partLabel.ViewObject.BackgroundColor = a2plib.YELLOW
                    partLabel.ViewObject.TextColor = a2plib.BLACK
                    labelGroup.addObject(partLabel)

    def IsChecked(self):
        doc = FreeCAD.activeDocument()
        if not doc: return False
        labelGroup = doc.getObject("partLabels")
        return labelGroup != None

    def IsActive(self):
        doc = FreeCAD.activeDocument()
        return doc != None

    def GetResources(self):
        return {
            'Pixmap'   : a2plib.pathOfModule()+'/icons/a2p_PartLabel.svg',
            'MenuText' : translate("A2plus_importpart", "Show part labels in 3D view"),
            'ToolTip'  : translate("A2plus_importpart", "Toggle showing part labels in 3D view"),
            'Checkable': False
            }
FreeCADGui.addCommand('a2p_Show_PartLabels_Command', a2p_Show_PartLabels_Command())


class a2p_Show_DOF_info_Command:

    def Activated(self, index):
        if index == 0:
            ''' Remove the existing labels from screen'''
            doc = FreeCAD.activeDocument()
            dofGroup = doc.getObject("dofLabels")
            if dofGroup != None:
                for lbl in dofGroup.Group:
                    doc.removeObject(lbl.Name)
                doc.removeObject("dofLabels")
        else:
            ss = a2p_solversystem.SolverSystem()
            ss.DOF_info_to_console()

    def IsActive(self):
        doc = FreeCAD.activeDocument()
        return doc != None

    def IsChecked(self):
        doc = FreeCAD.activeDocument()
        if not doc: return False
        dofGroup = doc.getObject("dofLabels")
        return dofGroup != None

    def GetResources(self):
        return {
            'Pixmap'   : a2plib.pathOfModule()+'/icons/a2p_DOFs.svg',
            'MenuText' : translate("A2plus_importpart", "Print detailed DOF information"),
            'ToolTip'  : translate("A2plus_importpart", "Toggle printing detailed DOF information"),
            'Checkable': False
            }
FreeCADGui.addCommand('a2p_Show_DOF_info_Command', a2p_Show_DOF_info_Command())



class a2p_absPath_to_relPath_Command:
    def Activated(self):
        doc = FreeCAD.activeDocument()
        if doc is None:
            QtGui.QMessageBox.information(  QtGui.QApplication.activeWindow(),
                                        translate("A2plus_importpart","No active document found!"),
                                        translate("A2plus_importpart","You have to open an assembly file first.")
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
            'Pixmap'  : a2plib.pathOfModule()+'/icons/a2p_SetRelativePathes.svg',
            'MenuText': translate("A2plus_importpart", "Convert absolute paths of imported parts to relative ones"),
            'ToolTip' : translate("A2plus_importpart", "Converts absolute paths of imported parts to relative ones")
            }
FreeCADGui.addCommand('a2p_absPath_to_relPath_Command', a2p_absPath_to_relPath_Command())




#==============================================================================
class a2p_SaveAndExit_Command:
    def Activated(self):
        doc = FreeCAD.activeDocument()
        try:
            doc.save()
            FreeCAD.closeDocument(doc.Name)
        except:
            FreeCADGui.SendMsgToActiveView("Save")
            if not FreeCADGui.activeDocument().Modified: # user really saved the file
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
            'Pixmap'  : a2plib.pathOfModule()+'/icons/a2p_Save_and_exit.svg',
            'MenuText': translate("A2plus_importpart", "Save and exit the active document"),
            'ToolTip' : translate("A2plus_importpart", "Save and exit the active document")
            }
FreeCADGui.addCommand('a2p_SaveAndExit_Command', a2p_SaveAndExit_Command())

#==============================================================================
toolTip = \
translate("A2plus_importpart",
'''
Migrate proxies of imported parts

Very old A2plus assemblies do not
show the correct icons for imported
parts and have obsolete properties.

With this function, you can migrate
the viewProviders of old imported parts
to the recent state.

After running this function, you
should save and reopen your
assembly file.
'''
)

class a2p_MigrateProxiesCommand():

    def Activated(self):
        flags = QtGui.QMessageBox.StandardButton.Yes | QtGui.QMessageBox.StandardButton.No
        response = QtGui.QMessageBox.information(
            QtGui.QApplication.activeWindow(),
            translate("A2plus_importpart","Migrate proxies of importedParts to recent version"),
            translate("A2plus_importpart","Make sure you have a backup of your files. Proceed?"),
            flags
            )
        if response == QtGui.QMessageBox.Yes:
            doc = FreeCAD.activeDocument()
            for ob in doc.Objects:
                if a2plib.isA2pPart(ob):
                    #setup proxies
                    a2p_importedPart_class.Proxy_importPart(ob)
                    if FreeCAD.GuiUp:
                        a2p_importedPart_class.ImportedPartViewProviderProxy(ob.ViewObject)
                    #delete obsolete properties
                    deleteList = []
                    tmp = ob.PropertiesList
                    for prop in tmp:
                        if prop.startswith('pi_') or prop == 'assembly2Version':
                            deleteList.append(prop)
                    for prop in deleteList:
                        ob.removeProperty(prop)

        QtGui.QMessageBox.information(
            QtGui.QApplication.activeWindow(),
            translate("A2plus_importpart","The proxies have been migrated."),
            translate("A2plus_importpart","Please save and reopen this assembly file")
            )



    def GetResources(self):
        return {
            'Pixmap' : ':/icons/a2p_Upgrade.svg',
            'MenuText': translate("A2plus_importpart", "Migrate proxies of imported parts"),
            'ToolTip': toolTip
            }

FreeCADGui.addCommand('a2p_MigrateProxiesCommand', a2p_MigrateProxiesCommand())
#==============================================================================







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


#==============================================================================
toolTip = \
translate("A2plus_importpart",
'''
Clean up solver debug output from 3D view
'''
)

class a2p_cleanUpDebug3dCommand():

    def Activated(self):
        sg = FreeCADGui.ActiveDocument.ActiveView.getSceneGraph()
        if sg is not None:
            print('3D-Debug contained {} vectors'.format(len(a2plib.solver_debug_objects)))
            for vec in a2plib.solver_debug_objects:
                sg.removeChild(vec)
            a2plib.graphical_debug_output = []


    def GetResources(self):
        return {
            'Pixmap'  : ':/icons/a2p_RemoveDebug3D.svg',
            'MenuText': translate("A2plus_importpart", "Clean up solver debug output from 3D view"),
            'ToolTip' : toolTip
            }

FreeCADGui.addCommand('a2p_cleanUpDebug3dCommand', a2p_cleanUpDebug3dCommand())
#==============================================================================


