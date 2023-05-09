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

# import os
# import copy
# from random import choice, random
# import numpy
import time

import FreeCAD
# from FreeCAD import Base
import FreeCADGui
import Part

from PySide import QtGui

import a2plib
# from a2plib import *
# from a2p_importedPart_class import Proxy_muxAssemblyObj  # for compat
# from a2p_translateUtils import *

from pivy import coin

translate = FreeCAD.Qt.translate


def create_topo_info(obj):  # used during converting an object to a2p object
    mux_info = []
    if not a2plib.getUseTopoNaming():
        return mux_info

    # Assembly works with topo_naming!
    for i in range(0, len(obj.Shape.Vertexes)):
        new_name = "".join(('V;', str(i+1), ';', obj.Name, ';'))
        mux_info.append(new_name)
    for i in range(0, len(obj.Shape.Edges)):
        new_name = "".join(('E;', str(i+1), ';', obj.Name, ';'))
        mux_info.append(new_name)
    for i in range(0, len(obj.Shape.Faces)):
        new_name = "".join(('F;', str(i+1), ';', obj.Name, ';'))
        mux_info.append(new_name)
    return mux_info


def make_placed_shape(obj):
    '''return a copy of obj.Shape with proper placement applied'''
    temp_shape = obj.Shape.copy()
    plm_global = obj.Placement
    try:
        plm_global = obj.getGlobalPlacement()
    except ValueError:
        pass
    temp_shape.Placement = plm_global
    return temp_shape


def mux_assembly_with_topo_names(doc, desired_shape_label=None):
    """
    Mux an a2p assembly.

    combines all the a2p objects in the doc into one shape
    and populates mux_info with a description of an edge or face.
    these descriptions are used later to retrieve the edges or faces...
    """
    faces = []
    face_colors = []
    mux_info = []  # List of keys, not used at moment...

    visible_objects = [
        obj for obj in doc.Objects
        if hasattr(obj, 'ViewObject') and obj.ViewObject.isVisible()
        and hasattr(obj, 'Shape') and len(obj.Shape.Faces) > 0
        and hasattr(obj, 'mux_info') and a2plib.isGlobalVisible(obj)
        ]

    if desired_shape_label:  # is not None..
        tmp = []
        for ob in visible_objects:
            if ob.Label == desired_shape_label:
                tmp.append(ob)
                break
        visible_objects = tmp

    transparency = 0
    shape_list = []
    for obj in visible_objects:
        extend_names = False
        # Subelement-Strings existieren schon...
        if a2plib.getUseTopoNaming() and len(obj.mux_info) > 0:
            extend_names = True
            #
            vertex_names = []
            edge_names = []
            face_names = []
            #
            for item in obj.mux_info:
                if item[0] == 'V':
                    vertex_names.append(item)
                if item[0] == 'E':
                    edge_names.append(item)
                if item[0] == 'F':
                    face_names.append(item)

        if a2plib.getUseTopoNaming():
            for i in range(0, len(obj.Shape.Vertexes)):
                if extend_names:
                    new_name = "".join((vertex_names[i], obj.Name, ';'))
                    # mux_info.append(new_name)
                else:
                    new_name = "".join(('V;', str(i+1), ';', obj.Name, ';'))
                    # mux_info.append(new_name)
                mux_info.append(new_name)

            for i in range(0, len(obj.Shape.Edges)):
                if extend_names:
                    new_name = "".join((edge_names[i], obj.Name, ';'))
                    # mux_info.append(new_name)
                else:
                    new_name = "".join(('E;', str(i+1), ';', obj.Name, ';'))
                    # mux_info.append(new_name)
                mux_info.append(new_name)

        # Save Computing time, store this before 'for'..enumerate loop later...
        need_diffuse_color_extension = (
            len(obj.ViewObject.DiffuseColor) < len(obj.Shape.Faces)
            )
        shape_col = obj.ViewObject.ShapeColor
        diffuse_col = obj.ViewObject.DiffuseColor
        temp_shape = make_placed_shape(obj)
        transparency = obj.ViewObject.Transparency
        shape_list.append(obj.Shape)

        # now start the loop with use of the stored values..(much faster)
        topo_naming = a2plib.getUseTopoNaming()
        diffuse_element = a2plib.makeDiffuseElement(shape_col, transparency)
        for i in range(0, len(temp_shape.Faces)):
            if topo_naming:
                if extend_names:
                    new_name = "".join((face_names[i], obj.Name, ';'))
                    # mux_info.append(new_name)
                else:
                    new_name = "".join(('F;', str(i+1), ';', obj.Name, ';'))
                    # mux_info.append(new_name)
                mux_info.append(new_name)

            if need_diffuse_color_extension:
                face_colors.append(diffuse_element)

        if not need_diffuse_color_extension:
            face_colors.extend(diffuse_col)

        faces.extend(temp_shape.Faces)

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
            # This does not work if shell includes spherical faces. FC-Bug ??
            solid = Part.Solid(shell)
            # Fall back to shell if some faces are missing..
            if len(shell.Faces) != len(solid.Faces):
                solid = shell
    except ValueError:
        # keeping a shell if solid is failing
        FreeCAD.Console.PrintWarning(
            translate("A2plus", "Union of Shapes FAILED") + "\n"
            )
        solid = shell

    # transparency could change to different values depending
    # on the order of imported objects
    # now set it to a default value
    # face_colors still contains the per face transparency values
    transparency = 0
    return mux_info, solid, face_colors, transparency


class SimpleAssemblyShape:
    def __init__(self, obj):
        obj.addProperty(
            "App::PropertyString", "type"
            ).type = 'SimpleAssemblyShape'
        obj.addProperty(
            "App::PropertyFloat", "timeOfGenerating"
            ).timeOfGenerating = time.time()
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

    def getIcon(self):
        return a2plib.get_module_path() + '/icons/SimpleAssemblyShape.svg'

    def attach(self, obj):
        default = coin.SoGroup()
        obj.addDisplayMode(default, "Standard")
        self.object_Name = obj.Object.Name
        self.Object = obj.Object

    def getDisplayModes(self, obj):
        '''Return a list of display modes'''
        modes = []
        modes.append("Shaded")
        modes.append("Wireframe")
        modes.append("Flat Lines")
        return modes

    def getDefaultDisplayMode(self):
        '''Return the name of the default display mode.
        It must be defined in getDisplayModes.'''
        return "Flat Lines"

    def setDisplayMode(self, mode):
        return mode


def createOrUpdateSimpleAssemblyShape(doc):
    visibleImportObjects = [
        obj for obj in doc.Objects
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
            # This does not work if shell includes spherical faces. FC-Bug ??
            solid = Part.Solid(shell)
            # Fall back to shell if faces are misiing
            if len(shell.Faces) != len(solid.Faces):
                solid = shell
    except ValueError:
        # keeping a shell if solid is failing
        FreeCAD.Console.PrintWarning(
            translate("A2plus", "Union of Shapes FAILED") + "\n"
             )
        solid = shell
    sas.Shape = solid  # shell
    sas.ViewObject.Visibility = False
    FreeCAD.Console.PrintMessage(
        translate(
            "A2plus",
            "Union of Shapes passed. 'SimpleAssemblyShape' are created."
             ) + "\n"
         )


class a2p_SimpleAssemblyShapeCommand():

    def GetResources(self):
        return {
                'Pixmap': a2plib.get_module_path() +
                '/icons/a2p_SimpleAssemblyShape.svg',
                'MenuText': translate(
                    "A2plus",
                    "Create or refresh simple shape of complete assembly"
                    ),
                'ToolTip': translate(
                    "A2plus",
                    "Create or refresh a simple shape" + "\n"
                    "of the complete Assembly." + "\n\n"
                    "All parts within the assembly" + "\n"
                    "are combined to a single shape." + "\n"
                    "This shape can be used e.g. for the" + "\n"
                    "techdraw module or 3D printing." + "\n\n"
                    "The created shape can be found" + "\n"
                    "in the treeview. By default it" + "\n"
                    "is invisible at first time."
                    )
                }

    def Activated(self):
        if FreeCAD.activeDocument() is None:
            QtGui.QMessageBox.information(
                QtGui.QApplication.activeWindow(),
                translate("A2plus", "No active document found!"),
                translate("A2plus", "You have to open an assembly file first.")
                 )
            return

        doc = FreeCAD.ActiveDocument
        createOrUpdateSimpleAssemblyShape(doc)
        doc.recompute()

    def IsActive(self):
        return True


FreeCADGui.addCommand(
    'a2p_SimpleAssemblyShapeCommand',
    a2p_SimpleAssemblyShapeCommand()
    )
