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

import FreeCADGui
import FreeCAD
from PySide import QtGui
import copy
import time
from a2p_translateUtils import *
import a2plib
from a2p_MuxAssembly import createTopoInfo
from a2p_versionmanagement import A2P_VERSION
from a2plib import (
    appVersionStr,
    AUTOSOLVE_ENABLED
    )
from a2p_importedPart_class import Proxy_importPart
from a2p_importedPart_class import Proxy_convertPart # for compat.
from a2p_importedPart_class import ImportedPartViewProviderProxy # for compat.

from a2p_topomapper import TopoMapper



def updateConvertedPart(doc, obj):

    obj.timeLastImport = time.time()

    baseObject = doc.getObject(obj.localSourceObject)

    savedPlacement = obj.Placement
    obj.ViewObject.ShapeColor = baseObject.ViewObject.ShapeColor
    topoMapper = TopoMapper(doc) # imports the objects and creates toponames if wanted
    baseObject.ViewObject.Visibility = True #the topomapper ignores invisible shapes
    obj.muxInfo, obj.Shape, obj.ViewObject.DiffuseColor, obj.ViewObject.Transparency = \
        topoMapper.createTopoNames(desiredShapeLabel = baseObject.Label)
    baseObject.ViewObject.Visibility = False #set baseObject invisible again.
    obj.Placement = savedPlacement

    for p in baseObject.ViewObject.PropertiesList: 
        if hasattr(baseObject.ViewObject, p) and p not in [
                'DiffuseColor',
                'Proxy',
                'MappedColors',
                'DisplayModeBody'
                ]:
            try:
                setattr(obj.ViewObject, p, getattr( baseObject.ViewObject, p))
            except:
                pass #a lot of attributes related e.g. to sketcher
            
    if not a2plib.getPerFaceTransparency():
        # switch of perFaceTransparency
        obj.ViewObject.Transparency = 1
        obj.ViewObject.Transparency = 0 # default = nontransparent
        
    obj.recompute()
    obj.ViewObject.Visibility = True

def convertToImportedPart(doc, obj):
    '''
    convertToImportedPart(document, documentObject) - changes a regular FreeCAD object into an A2plus
    importedPart, adds the importedPart to the document and hides the original object from the 
    document. Updating the assembly will also update the converted part
    '''
    partName = a2plib.findUnusedObjectName( obj.Label, document=doc )
    partLabel = a2plib.findUnusedObjectLabel( obj.Label, document=doc )
    filename = "converted"   #or none? if obj is already in this doc, we don't know it's original filename
    
    newObj = doc.addObject("Part::FeaturePython",partName)
    newObj.Label = partLabel

    Proxy_importPart(newObj)
    ImportedPartViewProviderProxy(newObj.ViewObject)

    newObj.a2p_Version = A2P_VERSION
    newObj.sourceFile = filename
    newObj.localSourceObject = obj.Name
    #newObj.sourcePart = ""
    newObj.setEditorMode("timeLastImport",1)
    newObj.timeLastImport = time.time()
    newObj.fixedPosition = False
    newObj.subassemblyImport = False
    newObj.setEditorMode("subassemblyImport",1)
    newObj.updateColors = True

    newObj.ViewObject.ShapeColor = obj.ViewObject.ShapeColor
    
    #-------------------------------------------
    # Initialize the new TopoMapper
    #-------------------------------------------
    topoMapper = TopoMapper(doc)
    newObj.muxInfo, newObj.Shape, newObj.ViewObject.DiffuseColor, newObj.ViewObject.Transparency = \
        topoMapper.createTopoNames(desiredShapeLabel = obj.Label)

    for p in obj.ViewObject.PropertiesList: 
        if hasattr(obj.ViewObject, p) and p not in [
                'DiffuseColor',
                'Proxy',
                'MappedColors',
                'DisplayModeBody'
                ]:
            try:
                setattr(newObj.ViewObject, p, getattr( obj.ViewObject, p))
            except: #some sketcher attributes e.g.
                pass
    
    if not a2plib.getPerFaceTransparency():
        # switch of perFaceTransparency
        newObj.ViewObject.Transparency = 1
        newObj.ViewObject.Transparency = 0 # default = nontransparent
        

    newObj.Placement.Base = obj.Placement.Base
    newObj.Placement.Rotation = obj.Placement.Rotation

    obj.ViewObject.Visibility = False
    newObj.recompute()


toolTip = \
'''
Convert a part, created with
another WB, to a full functional
A2plus part.

After converting, constraints
can be applied. Also you can
duplicate the converted part.

For editing a converted part,
hit the edit button and follow
the instructions shown on screen.

This function is useful, if
you want to use e.g. fasteners
within this workbench.
'''

class a2p_ConvertPartCommand():

    def GetResources(self):
        return {'Pixmap'  : a2plib.pathOfModule()+'/icons/a2p_ConvertPart.svg',
#                'Accel' : "Shift+C", # a default shortcut (optional)
                'MenuText': "Convert a part to A2plus",
                'ToolTip' : toolTip
                }

    def Activated(self):
        doc = FreeCAD.activeDocument()
        selection = FreeCADGui.Selection.getSelection()
        for s in selection:
            if s.ViewObject.Visibility == False:
                msg = u"Please select only visible parts!"
                QtGui.QMessageBox.information(
                    QtGui.QApplication.activeWindow(),
                    u"Conversion Aborted",
                    msg
                    )
                return
        for s in selection:
            doc.openTransaction(u"part converted to A2plus")
            convertToImportedPart(doc, s)
            doc.commitTransaction()

    def IsActive(self):
        if FreeCAD.activeDocument() is None:
            return False

        selection = FreeCADGui.Selection.getSelection()
        if not selection: return False
        for s in selection:
            if a2plib.isA2pPart(s): return False
            if (
                    not s.isDerivedFrom("Part::Feature") and
                    not s.Name.startswith('Sketch')
                    ):
                return False
        return True

FreeCADGui.addCommand('a2p_ConvertPart',a2p_ConvertPartCommand())
