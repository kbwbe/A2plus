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
from FreeCAD.Qt import translate
from PySide import QtGui
import Part
import os, copy, numpy
from random import random, choice
from FreeCAD import  Base
import time
import a2plib
from a2plib import *

from a2p_importedPart_class import Proxy_muxAssemblyObj # for compat

#===========================================================================
# !!!!!!!!!!!!!!!!!!!
# Relevant muxing of assemblies has been moved to a2p_filecache.py
# !!!!!!!!!!!!!!!!!!!
#
# only SimpleAssemblyShape is still here...
#===========================================================================



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

toolTip = \
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

def createOrUpdateSimpleAssemblyShape(doc):
    visibleImportObjects = [ obj for obj in doc.Objects
                           if 'importPart' in obj.Content
                           and hasattr(obj,'ViewObject')
                           and obj.ViewObject.isVisible()
                           and hasattr(obj,'Shape')
                           and len(obj.Shape.Faces) > 0
                           and a2plib.isGlobalVisible(obj)
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
                shape_base=shape_list[0]
                shapes=shape_list[1:]
                solid = shape_base.fuse(shapes)
            else:
                solid = Part.Solid(shape_list[0])
        else:
            solid = Part.Solid(shell) # This does not work if shell includes spherical faces. FC-Bug ??
            # Fall back to shell if faces are misiing
            if len(shell.Faces) != len(solid.Faces):
                solid = shell
    except:
        # keeping a shell if solid is failing
        FreeCAD.Console.PrintWarning('Union of Shapes FAILED\n')
        solid = shell
    sas.Shape = solid #shell
    sas.ViewObject.Visibility = False


class a2p_SimpleAssemblyShapeCommand():

    def GetResources(self):
        import a2plib
        return {'Pixmap'  : a2plib.path_a2p +'/icons/a2p_SimpleAssemblyShape.svg',
                'MenuText': QT_TRANSLATE_NOOP("A2plus_MuxAssembly", "Create or refresh simple shape of complete assembly"),
                'ToolTip' : toolTip
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
