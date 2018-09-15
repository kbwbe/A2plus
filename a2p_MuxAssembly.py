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

import FreeCAD, FreeCADGui
from a2plib import *
import Part
import os, copy, numpy
from random import random, choice
from FreeCAD import  Base
import time
import a2plib
from PySide import QtGui


class Proxy_muxAssemblyObj:
    def execute(self, shape):
        pass

def createTopoInfo(obj): #deactivated at moment...
    return []

def makePlacedShape(obj):
    '''return a copy of obj.Shape with proper placement applied'''
    tempShape = obj.Shape.copy()
    plmGlobal = obj.Placement
    try:
        plmGlobal = obj.getGlobalPlacement();
    except:
        pass
    tempShape.Placement = plmGlobal
    return tempShape

def muxObjectsWithKeys(objsIn, withColor=False):
    '''
    combines all the objects in objsIn into one shape,
    is able to import colors
    '''
    faces = []
    faceColors = []
    muxInfo = [] # List of keys, not used at moment...

    for obj in objsIn:
        # Save Computing time, store this before the for..enumerate loop later...
        colorFlag = ( len(obj.ViewObject.DiffuseColor) < len(obj.Shape.Faces) )
        shapeCol = obj.ViewObject.ShapeColor
        diffuseCol = obj.ViewObject.DiffuseColor
        tempShape = makePlacedShape(obj)

        # now start the loop with use of the stored values..(much faster)
        for i, face in enumerate(tempShape.Faces):
            faces.append(face)
            DebugMsg(A2P_DEBUG_3,"a2p MUX: i(Faces)={}\n{}\n".format(i,face))

            if withColor:
                if colorFlag:
                    faceColors.append(shapeCol)
                else:
                    faceColors.append(diffuseCol[i])

    shell = Part.makeShell(faces)
    Msg("A2P MUX: result: {}\n".format(shell))
    DebugMsg(A2P_DEBUG_3,"a2p MUX: faceColors:\n{}\n".format(faceColors))            # has result all faces' color values?
    if withColor:
        return muxInfo, shell, faceColors
    else:
        return muxInfo, shell

#NOTE: muxObjects is never called in A2plus
def muxObjects(doc, mode=0):
    'combines all the imported shape object in doc into one shape'
    faces = []
    if mode == 1:
        objects = doc.getSelection()
    else:
        objects = doc.Objects

    for obj in objects:
        if 'importPart' in obj.Content:
            faces = faces + obj.Shape.Faces
    shell = Part.makeShell(faces)
    return shell

class SimpleAssemblyShape:
    def __init__(self, obj):
        obj.addProperty("App::PropertyString", "type").type = 'SimpleAssemblyShape'
        obj.addProperty("App::PropertyFloat", "timeOfGenerating").timeOfGenerating = time.time()
        obj.Proxy = self

    def onChanged(self, fp, prop):
        pass

    def execute(self, fp):
        pass


class ViewProviderSimpleAssemblyShape:
    def __init__(self,obj):
        obj.Proxy = self

    def onDelete(self, viewObject, subelements):
        return True

    def __getstate__(self):
        return None

    def __setstate__(self, state):
        return None

    def getIcon(self):
        return a2plib.path_a2p + '/icons/SimpleAssemblyShape.svg'

    def attach(self, obj):
        default = coin.SoGroup()
        obj.addDisplayMode(default, "Standard")
        self.object_Name = obj.Object.Name
        self.Object = obj.Object

    def getDisplayModes(self,obj):
        "Return a list of display modes."
        modes=[]
        modes.append("Shaded")
        modes.append("Wireframe")
        modes.append("Flat Lines")
        return modes

    def getDefaultDisplayMode(self):
        "Return the name of the default display mode. It must be defined in getDisplayModes."
        return "Flat Lines"

    def setDisplayMode(self,mode):
        return mode


def createOrUpdateSimpleAssemblyShape(doc):
    visibleImportObjects = [ obj for obj in doc.Objects
                           if 'importPart' in obj.Content
                           and hasattr(obj,'ViewObject')
                           and obj.ViewObject.isVisible()
                           and hasattr(obj,'Shape')
                           and len(obj.Shape.Faces) > 0
                           ]

    if len(visibleImportObjects) == 0:
        QtGui.QMessageBox.critical(  QtGui.QApplication.activeWindow(),
                                     "Cannot create SimpleAssemblyShape",
                                     "No visible ImportParts found"
                                   )
        return

    sas = doc.getObject('SimpleAssemblyShape')
    if sas == None:
        sas = doc.addObject("Part::FeaturePython","SimpleAssemblyShape")
        SimpleAssemblyShape(sas)
        #sas.ViewObject.Proxy = 0
        ViewProviderSimpleAssemblyShape(sas.ViewObject)
    faces = []

    for obj in visibleImportObjects:
        faces = faces + obj.Shape.Faces
    shell = Part.makeShell(faces)
    sas.Shape = shell
    sas.ViewObject.Visibility = False


class a2p_SimpleAssemblyShapeCommand():

    def GetResources(self):
        import a2plib
        return {'Pixmap'  : a2plib.path_a2p +'/icons/a2p_SimpleAssemblyShape.svg',
                'MenuText': "create or refresh simple Shape of complete Assembly",
                'ToolTip': "create or refresh simple Shape of complete Assembly"
                }

    def Activated(self):
        if FreeCAD.activeDocument() == None:
            QtGui.QMessageBox.information(  QtGui.QApplication.activeWindow(),
                                        "No active document found!",
                                        "You have to open an assembly file first."
                                    )
            return
        doc = FreeCAD.ActiveDocument
        createOrUpdateSimpleAssemblyShape(doc)
        doc.recompute()

    def IsActive(self):
        return True

FreeCADGui.addCommand('a2p_SimpleAssemblyShapeCommand',a2p_SimpleAssemblyShapeCommand())
