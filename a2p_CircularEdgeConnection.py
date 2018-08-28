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
#from lib3D import *
from pivy import coin
from PySide import QtGui
from FreeCAD import Base

from a2p_viewProviderProxies import *


class CircularEdgeSelectionGate:
    def allow(self, doc, obj, sub):
        s1 = SelectionExObject(doc, obj, sub)
        return CircularEdgeSelected(s1)

class CircularEdgeSelectionGate2:
    def allow(self, doc, obj, sub):
        s1 = SelectionExObject(doc, obj, sub)
        return CircularEdgeSelected(s1)

def parseSelection(selection, objectToUpdate=None, callSolveConstraints=True, lockRotation = False):
    validSelection = False
    if len(selection) == 2:
        s1, s2 = selection
        if s1.ObjectName != s2.ObjectName:
            if CircularEdgeSelected(s1) and CircularEdgeSelected(s2):
                validSelection = True
                cParms = [ [s1.ObjectName, s1.SubElementNames[0], s1.Object.Label ],
                           [s2.ObjectName, s2.SubElementNames[0], s2.Object.Label ] ]
    if not validSelection:
        msg = '''Please select two circular edges from different parts. But election made is:%s'''  % printSelection(selection)
        QtGui.QMessageBox.information(  QtGui.QApplication.activeWindow(), "Incorrect Usage", msg)
        return

    if objectToUpdate == None:
        cName = findUnusedObjectName('circularEdgeConstraint')
        c = FreeCAD.ActiveDocument.addObject("App::FeaturePython", cName)

        c.addProperty("App::PropertyString","Type","ConstraintInfo").Type = 'circularEdge'
        c.addProperty("App::PropertyString","Object1","ConstraintInfo").Object1 = cParms[0][0]
        c.addProperty("App::PropertyString","SubElement1","ConstraintInfo").SubElement1 = cParms[0][1]
        c.addProperty("App::PropertyString","Object2","ConstraintInfo").Object2 = cParms[1][0]
        c.addProperty("App::PropertyString","SubElement2","ConstraintInfo").SubElement2 = cParms[1][1]

        c.addProperty("App::PropertyEnumeration","directionConstraint", "ConstraintInfo")
        c.directionConstraint = ["aligned","opposed"]
        c.addProperty("App::PropertyDistance","offset","ConstraintInfo")
        c.addProperty("App::PropertyBool","lockRotation","ConstraintInfo").lockRotation = lockRotation

        c.setEditorMode('Type',1)
        for prop in ["Object1","Object2","SubElement1","SubElement2"]:
            c.setEditorMode(prop, 1)

        #-------------------------------------------
        # Group correctly under ParentObject in tree
        #-------------------------------------------
        parent = FreeCAD.ActiveDocument.getObject(c.Object1)
        c.addProperty("App::PropertyLink","ParentTreeObject","ConstraintInfo").ParentTreeObject = parent
        c.setEditorMode('ParentTreeObject',1)
        parent.Label = parent.Label # this is needed to trigger an update
        #-------------------------------------------

        c.Proxy = ConstraintObjectProxy()
        c.ViewObject.Proxy = ConstraintViewProviderProxy(
            c,
            path_a2p + '/icons/a2p_CircularEdgeConstraint.svg',
            True,
            cParms[1][2],
            cParms[0][2]
            )
    else:
        c = objectToUpdate
        c.Object1 = cParms[0][0]
        c.SubElement1 = cParms[0][1]
        c.Object2 = cParms[1][0]
        c.SubElement2 = cParms[1][1]
        updateObjectProperties(c)

    c.purgeTouched()
    if callSolveConstraints:
        c.Proxy.callSolveConstraints()
    #FreeCADGui.Selection.clearSelection()
    #FreeCADGui.Selection.addSelection(c)
    return c



selection_text = \
'''1.) select circular edge on first importPart
   2.) select circular edge on other importPart
'''

toolTipText = \
'''
Add a circular edge constraint between two parts
selection-hint:
1.) select circular edge on first importPart
2.) select circular edge on other importPart
'''


class a2p_CircularEdgeConnectionCommand:
    def Activated(self):
        selection = FreeCADGui.Selection.getSelectionEx()
        if len(selection) == 2:
            parseSelection( selection )
        else:
            FreeCADGui.Selection.clearSelection()
            ConstraintSelectionObserver(
                CircularEdgeSelectionGate(),
                parseSelection,
                taskDialog_title ='add circular edge constraint',
                taskDialog_iconPath = self.GetResources()['Pixmap'],
                taskDialog_text = selection_text,
                 secondSelectionGate = CircularEdgeSelectionGate2()
                )

    def GetResources(self):
        return {
            'Pixmap' : path_a2p + '/icons/a2p_CircularEdgeConstraint.svg' ,
            'MenuText': 'Add circular edge connection',
            'ToolTip': toolTipText
            }

FreeCADGui.addCommand('a2p_CircularEdgeConnection', a2p_CircularEdgeConnectionCommand())
