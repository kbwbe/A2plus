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
from a2p_importpart import filterImpParts
from a2p_topo import createTopoInfo
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
    '''convertToImportedPart(document, documentObject) - changes a regular FreeCAD object into an A2plus
    importedPart, adds the importedPart to the document and removes the FreeCAD object from the 
    document. Returns None'''
    
#    objExpand = filterImpParts(obj)
#    if not objExpand:
#        msg = obj.Name + " was not converted."
#        FreeCADGui.Console.Message(msg)
#    for oe in objExpand:

    #partName = obj.Name
    partName = a2plib.findUnusedObjectName( obj.Label, document=doc )
    partLabel = a2plib.findUnusedObjectLabel( obj.Label, document=doc )
    filename = "converted"   #or none? if obj is already in this doc, we don't know it's original filename
    
    newObj = doc.addObject("Part::FeaturePython",partName)
    newObj.Label = partLabel
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
        if hasattr(newObj.ViewObject, p) and p not in ['DiffuseColor','Proxy','MappedColors']:
            setattr(newObj.ViewObject, p, getattr( obj.ViewObject, p))
    newObj.ViewObject.DiffuseColor = copy.copy( obj.ViewObject.DiffuseColor )
    newObj.ViewObject.Transparency = obj.ViewObject.Transparency
    newObj.Placement.Base = obj.Placement.Base
    newObj.Placement.Rotation = obj.Placement.Rotation

    newObj.Proxy = Proxy_convertPart()
    newObj.ViewObject.Proxy = ImportedPartViewProviderProxy()

    doc.removeObject(obj.Name)          # don't want the original in this doc anymore
    newObj.recompute()


class a2p_ConvertPartCommand():

    def GetResources(self):
        import a2plib
        return {'Pixmap'  : a2plib.pathOfModule()+'/icons/a2p_ConvertPart.svg',
#                'Accel' : "Shift+C", # a default shortcut (optional)
                'MenuText': "convert Part to A2plus form",
                'ToolTip' : "convert Part to A2plus form"
                }

    def Activated(self):
        if FreeCAD.activeDocument() == None:
            QtGui.QMessageBox.information(
                QtGui.QApplication.activeWindow(),
               "No active Document error",
               "First please open an assembly file!"
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
        elif len(selection) > 1:
            msg = \
'''
One part at a time please.
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

        convertToImportedPart(doc, selection[0])

        return

    def IsActive(self):
        """Here you can define if the command must be active or not (greyed) if certain conditions
        are met or not. This function is optional."""
        return True


FreeCADGui.addCommand('a2p_ConvertPart',a2p_ConvertPartCommand())


