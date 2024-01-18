# ***************************************************************************
# *                                                                         *
# *   Copyright (c) 2018 kbwbe                                              *
# *                                                                         *
# *   Portions of code based on hamish's assembly 2                         *
# *                                                                         *
# *   This program is free software; you can redistribute it and/or modify  *
# *   it under the terms of the GNU Lesser General Public License (LGPL)    *
# *   as published by the Free Software Foundation; either version 2 of     *
# *   the License, or (at your option) any later version.                   *
# *   for detail see the LICENCE text file.                                 *
# *                                                                         *
# *   This program is distributed in the hope that it will be useful,       *
# *   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
# *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
# *   GNU Library General Public License for more details.                  *
# *                                                                         *
# *   You should have received a copy of the GNU Library General Public     *
# *   License along with this program; if not, write to the Free Software   *
# *   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  *
# *   USA                                                                   *
# *                                                                         *
# ***************************************************************************

import os
import copy
import time
import numpy
from PySide import QtGui
from random import random, choice

import FreeCAD
from FreeCAD import Base
import FreeCADGui
import Part

import a2plib
from a2plib import *
from a2p_translateUtils import *
from a2p_importedPart_class import Proxy_muxAssemblyObj  # for compat


def createTopoInfo(obj):  # used during converting an object to a2p object
    muxInfo = []
    if not a2plib.getUseTopoNaming():
        return muxInfo
    #
    # Assembly works with topoNaming!
    for i in range(0, len(obj.Shape.Vertexes)):
        newName = "".join(('V;', str(i+1), ';', obj.Name, ';'))
        muxInfo.append(newName)
    for i in range(0, len(obj.Shape.Edges)):
        newName = "".join(('E;', str(i+1), ';', obj.Name, ';'))
        muxInfo.append(newName)
    for i in range(0, len(obj.Shape.Faces)):
        newName = "".join(('F;', str(i+1), ';', obj.Name, ';'))
        muxInfo.append(newName)
    return muxInfo


def makePlacedShape(obj):
    '''return a copy of obj.Shape with proper placement applied'''
    tempShape = obj.Shape.copy()
    plmGlobal = obj.Placement
    try:
        plmGlobal = obj.getGlobalPlacement()
    except ValueError:
        pass
    tempShape.Placement = plmGlobal
    return tempShape


def muxAssemblyWithTopoNames(doc, desiredShapeLabel=None):
    """
    Mux an a2p assembly.

    combines all the a2p objects in the doc into one shape
    and populates muxinfo with a description of an edge or face.
    these descriptions are used later to retrieve the edges or faces...
    """
    faces = []
    faceColors = []
    muxInfo = []  # List of keys, not used at moment...

    visibleObjects = [obj for obj in doc.Objects
                      if hasattr(obj, 'ViewObject') and obj.ViewObject.isVisible()
                      and hasattr(obj, 'Shape') and len(obj.Shape.Faces) > 0
                      and hasattr(obj, 'muxInfo') and
                      a2plib.isGlobalVisible(obj)
                      ]

    if desiredShapeLabel:  # is not None..
        tmp = []
        for ob in visibleObjects:
            if ob.Label == desiredShapeLabel:
                tmp.append(ob)
                break
        visibleObjects = tmp

    transparency = 0
    shape_list = []
    for obj in visibleObjects:
        extendNames = False
        if a2plib.getUseTopoNaming() and len(obj.muxInfo) > 0:  # Subelement-Strings existieren schon...
            extendNames = True
            #
            vertexNames = []
            edgeNames = []
            faceNames = []
            #
            for item in obj.muxInfo:
                if item[0] == 'V':
                    vertexNames.append(item)
                if item[0] == 'E':
                    edgeNames.append(item)
                if item[0] == 'F':
                    faceNames.append(item)

        if a2plib.getUseTopoNaming():
            for i in range(0, len(obj.Shape.Vertexes)):
                if extendNames:
                    newName = "".join((vertexNames[i], obj.Name, ';'))
                    muxInfo.append(newName)
                else:
                    newName = "".join(('V;', str(i+1), ';', obj.Name, ';'))
                    muxInfo.append(newName)
            for i in range(0, len(obj.Shape.Edges)):
                if extendNames:
                    newName = "".join((edgeNames[i], obj.Name, ';'))
                    muxInfo.append(newName)
                else:
                    newName = "".join(('E;', str(i+1), ';', obj.Name, ';'))
                    muxInfo.append(newName)

        # Save Computing time, store this before the for..enumerate loop later...
        needDiffuseColorExtension = (len(obj.ViewObject.DiffuseColor) < len(obj.Shape.Faces))
        shapeCol = obj.ViewObject.ShapeColor
        diffuseCol = obj.ViewObject.DiffuseColor
        tempShape = makePlacedShape(obj)
        transparency = obj.ViewObject.Transparency
        shape_list.append(obj.Shape)

        # now start the loop with use of the stored values..(much faster)
        topoNaming = a2plib.getUseTopoNaming()
        diffuseElement = makeDiffuseElement(shapeCol, transparency)
        for i in range(0, len(tempShape.Faces)):
            if topoNaming:
                if extendNames:
                    newName = "".join((faceNames[i], obj.Name, ';'))
                    muxInfo.append(newName)
                else:
                    newName = "".join(('F;', str(i+1), ';', obj.Name, ';'))
                    muxInfo.append(newName)
            if needDiffuseColorExtension:
                faceColors.append(diffuseElement)

        if not needDiffuseColorExtension:
            faceColors.extend(diffuseCol)

        faces.extend(tempShape.Faces)

    # if len(faces) == 1:
    #     shell = Part.makeShell([faces])
    # else:
    #     shell = Part.makeShell(faces)
    shell = Part.makeShell(faces)

    try:
        if a2plib.getUseSolidUnion():
            if len(shape_list) > 1:
                shape_base = shape_list[0]
                shapes = shape_list[1:]
                solid = shape_base.fuse(shapes)
            else:
                solid = Part.Solid(shape_list[0])
        else:
            solid = Part.Solid(shell)  # This does not work if shell includes spherical faces. FC-Bug ??
            # Fall back to shell if some faces are missing..
            if len(shell.Faces) != len(solid.Faces):
                solid = shell
    except ValueError:
        # keeping a shell if solid is failing
        FreeCAD.Console.PrintWarning(translate("A2plus", "Union of Shapes FAILED") + "\n")
        solid = shell

    # transparency could change to different values depending
    # on the order of imported objects
    # now set it to a default value
    # faceColors still contains the per face transparency values
    transparency = 0
    return muxInfo, solid, faceColors, transparency


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
    def __init__(self, obj):
        obj.Proxy = self

    def onDelete(self, viewObject, subelements):
        return True

    def __getstate__(self):
        return None

    def __setstate__(self, state):
        return None

    def dumps(self):
        return None

    def loads(self, state):
        return None

    def getIcon(self):
        return a2plib.path_a2p + '/icons/SimpleAssemblyShape.svg'

    def attach(self, obj):
        default = coin.SoGroup()
        obj.addDisplayMode(default, "Standard")
        self.object_Name = obj.Object.Name
        self.Object = obj.Object

    def getDisplayModes(self, obj):
        "Return a list of display modes."
        modes = []
        modes.append("Shaded")
        modes.append("Wireframe")
        modes.append("Flat Lines")
        return modes

    def getDefaultDisplayMode(self):
        "Return the name of the default display mode. It must be defined in getDisplayModes."
        return "Flat Lines"

    def setDisplayMode(self, mode):
        return mode

toolTip = \
translate("A2plus",
'''
Create or refresh a simple shape
of the complete Assembly.

All parts within the assembly
are combined to a single shape.
This shape can be used e.g. for the
techdraw module or 3D printing.

The created shape can be found
in the treeview. By default it
is invisible at first time.
'''
          )


def createOrUpdateSimpleAssemblyShape(doc):
    visibleImportObjects = [obj for obj in doc.Objects
                           if 'importPart' in obj.Content
                           and hasattr(obj, 'ViewObject')
                           and obj.ViewObject.isVisible()
                           and hasattr(obj, 'Shape')
                           and len(obj.Shape.Faces) > 0
                            ]

    if len(visibleImportObjects) == 0:
        QtGui.QMessageBox.critical(
                                   QtGui.QApplication.activeWindow(),
                                   translate("A2plus", "Cannot create SimpleAssemblyShape"),
                                   translate("A2plus", "No visible ImportParts found")
                                   )
        return

    sas = doc.getObject('SimpleAssemblyShape')
    if sas is None:
        sas = doc.addObject("Part::FeaturePython", "SimpleAssemblyShape")
        SimpleAssemblyShape(sas)
        # sas.ViewObject.Proxy = 0
        ViewProviderSimpleAssemblyShape(sas.ViewObject)
    faces = []
    shape_list = []
    for obj in visibleImportObjects:
        faces = faces + obj.Shape.Faces
        shape_list.append(obj.Shape)
    if len(faces) == 1:
        shell = Part.makeShell([faces])
    else:
        shell = Part.makeShell(faces)
    try:
        if a2plib.getUseSolidUnion():
            if len(shape_list) > 1:
                shape_base = shape_list[0]
                shapes = shape_list[1:]
                solid = shape_base.fuse(shapes)
            else:
                solid = Part.Solid(shape_list[0])
        else:
            solid = Part.Solid(shell)  # This does not work if shell includes spherical faces. FC-Bug ??
            # Fall back to shell if faces are misiing
            if len(shell.Faces) != len(solid.Faces):
                solid = shell
    except ValueError:
        # keeping a shell if solid is failing
        FreeCAD.Console.PrintWarning(translate("A2plus", "Union of Shapes FAILED") + "\n")
        solid = shell
    sas.Shape = solid  # shell
    sas.ViewObject.Visibility = False
    FreeCAD.Console.PrintMessage(translate("A2plus", "Union of Shapes passed. 'SimpleAssemblyShape' are created.") + "\n")


class a2p_SimpleAssemblyShapeCommand():

    def GetResources(self):
        import a2plib
        return {'Pixmap'  : a2plib.path_a2p + '/icons/a2p_SimpleAssemblyShape.svg',
                'MenuText': translate("A2plus", "Create or refresh simple shape of complete assembly"),
                'ToolTip' : toolTip
                }

    def Activated(self):
        if FreeCAD.activeDocument() is None:
            QtGui.QMessageBox.information(QtGui.QApplication.activeWindow(),
                                        translate("A2plus", "No active document found!"),
                                        translate("A2plus", "You have to open an assembly file first.")
                                          )
            return
        doc = FreeCAD.ActiveDocument
        createOrUpdateSimpleAssemblyShape(doc)
        doc.recompute()

    def IsActive(self):
        return True

FreeCADGui.addCommand('a2p_SimpleAssemblyShapeCommand', a2p_SimpleAssemblyShapeCommand())
