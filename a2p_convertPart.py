#***************************************************************************
#*                                                                         *
#*   Copyright (c) 2018 WandererFan <wandererfan@gmail.com>                *
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
import os, copy, time
import a2plib
from a2p_MuxAssembly import createTopoInfo
from a2p_viewProviderProxies import *
from a2p_versionmanagement import SubAssemblyWalk, A2P_VERSION
import a2p_solversystem
from a2plib import (
    appVersionStr,
    AUTOSOLVE_ENABLED
    )

class Proxy_convertPart:
    def execute(self, shape):
        pass

def convertToImportedPart(doc, obj):
    '''
    convertToImportedPart(document, documentObject) - changes a regular FreeCAD object into an A2plus
    importedPart, adds the importedPart to the document and removes the FreeCAD object from the 
    document. Returns None
    '''
    partName = a2plib.findUnusedObjectName( obj.Label, document=doc )
    partLabel = a2plib.findUnusedObjectLabel( obj.Label, document=doc )
    filename = "converted"   #or none? if obj is already in this doc, we don't know it's original filename
    
    newObj = doc.addObject("Part::FeaturePython",partName)
    newObj.Label = partLabel

    newObj.Proxy = Proxy_convertPart()
    newObj.ViewObject.Proxy = ImportedPartViewProviderProxy()

    newObj.addProperty("App::PropertyString", "a2p_Version","importPart").a2p_Version = A2P_VERSION
    newObj.addProperty("App::PropertyFile",    "sourceFile",    "importPart").sourceFile = filename
    newObj.addProperty("App::PropertyStringList","muxInfo","importPart")
    newObj.addProperty("App::PropertyFloat", "timeLastImport","importPart")
    newObj.setEditorMode("timeLastImport",1)
    newObj.timeLastImport = time.time()
    newObj.addProperty("App::PropertyBool","fixedPosition","importPart")
    newObj.fixedPosition = False
    newObj.addProperty("App::PropertyBool","subassemblyImport","importPart").subassemblyImport = False
    newObj.setEditorMode("subassemblyImport",1)
    newObj.addProperty("App::PropertyBool","updateColors","importPart").updateColors = True

    newObj.Shape = obj.Shape.copy()
    newObj.muxInfo = createTopoInfo(obj)

    for p in obj.ViewObject.PropertiesList: 
        if hasattr(obj.ViewObject, p) and p not in ['DiffuseColor','Proxy','MappedColors']:
            setattr(newObj.ViewObject, p, getattr( obj.ViewObject, p))
    newObj.ViewObject.ShapeColor = obj.ViewObject.ShapeColor
    newObj.ViewObject.DiffuseColor = copy.copy( obj.ViewObject.DiffuseColor ) # diffuse needs to happen last
    
    if not a2plib.getPerPartTransparency():
        # switch of perFaceTransparency
        newObj.ViewObject.Transparency = 1
        newObj.ViewObject.Transparency = 0 # default = nontransparent
        

    newObj.Placement.Base = obj.Placement.Base
    newObj.Placement.Rotation = obj.Placement.Rotation

    doc.removeObject(obj.Name)          # don't want the original in this doc anymore
    newObj.recompute()


toolTip = \
'''
Convert a part, created with
another WB, to a full functional
A2plus part.

After converting, constraints
can be applied. Also you can
duplicate the converted part.

(The shape of the converted part
is not editable anymore, as it
is a static copy of the original
shape.)

This function is useful, if
you want to use e.g. fasteners
within this workbench.
'''

class a2p_ConvertPartCommand():

    def GetResources(self):
        import a2plib
        return {'Pixmap'  : a2plib.pathOfModule()+'/icons/a2p_ConvertPart.svg',
#                'Accel' : "Shift+C", # a default shortcut (optional)
                'MenuText': "Convert a part to A2plus",
                'ToolTip' : toolTip
                }

    def Activated(self):
        if FreeCAD.activeDocument() == None:
            QtGui.QMessageBox.information(
                QtGui.QApplication.activeWindow(),
               "No active document error",
               "Please open an assembly file first!"
               )
            return
        doc = FreeCAD.activeDocument()
        selection = FreeCADGui.Selection.getSelection()
        if not selection:
            msg = \
'''
You must select a part to convert first.
'''
            QtGui.QMessageBox.information(
                QtGui.QApplication.activeWindow(),
                "Selection Error",
                msg
                )
            return
        elif not selection[0].isDerivedFrom("Part::Feature"):    # change here if allowing groups
            msg = \
'''
Please select a Part.
'''
            QtGui.QMessageBox.information(
                QtGui.QApplication.activeWindow(),
                "Selection Error",
                msg
                )
            return

        elif len(selection) > 1:
            for s in selection:
                if not s.isDerivedFrom("Part::Feature"):    # change here if allowing groups
                    msg = \
'''
Please select a Part.
'''
                    QtGui.QMessageBox.information(
                        QtGui.QApplication.activeWindow(),
                        "Selection Error",
                        msg
                        )
                    return
                else:
                    doc.openTransaction("part converted to A2plus")
                    convertToImportedPart(doc, s)
                    doc.commitTransaction()
        else:
            doc.openTransaction("part converted to A2plus")
            convertToImportedPart(doc, selection[0])
            doc.commitTransaction()

    def IsActive(self):
        """Here you can define if the command must be active or not (greyed) if certain conditions
        are met or not. This function is optional."""
        
        return True


FreeCADGui.addCommand('a2p_ConvertPart',a2p_ConvertPartCommand())



