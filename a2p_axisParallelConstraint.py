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

import math
from a2plib import *
from pivy import coin
from PySide import QtGui

class PlanesParallelSelectionGate:
    def allow(self, doc, obj, sub):
        s1 = SelectionExObject(doc, obj, sub)
        return LinearEdgeSelected( s1 ) or cylindricalPlaneSelected( s1 )

class PlanesParallelSelectionGate2:
    def allow(self, doc, obj, sub):
        s2 = SelectionExObject(doc, obj, sub)
        return LinearEdgeSelected( s2 ) or cylindricalPlaneSelected( s2 )

def parseSelection(selection, objectToUpdate=None):
    validSelection = False
    if len(selection) == 2:
        s1, s2 = selection
        if s1.ObjectName != s2.ObjectName:
            if (
                (LinearEdgeSelected(s1) or cylindricalPlaneSelected(s1)) and
                (LinearEdgeSelected(s2) or cylindricalPlaneSelected(s2))
                ): 
                validSelection = True
                cParms = [ [s1.ObjectName, s1.SubElementNames[0], s1.Object.Label ],
                           [s2.ObjectName, s2.SubElementNames[0], s2.Object.Label ] ]
    if not validSelection:
        msg = '''
              axisParallelConstraint requires a selection of:
              - cylinderAxis or linearEdge on a part
              - cylinderAxis or linearEdge on another part
              Selection made: %s
              ''' % printSelection(selection)

        QtGui.QMessageBox.information(  QtGui.QApplication.activeWindow(), "Incorrect Usage", msg)
        return

    if objectToUpdate == None:
        extraText = ''
        cName = findUnusedObjectName('axisParallel')
        c = FreeCAD.ActiveDocument.addObject("App::FeaturePython", cName)
        c.addProperty("App::PropertyString","Type","ConstraintInfo").Type = 'axisParallel'
        c.addProperty("App::PropertyString","Object1","ConstraintInfo").Object1 = cParms[0][0]
        c.addProperty("App::PropertyString","SubElement1","ConstraintInfo").SubElement1 = cParms[0][1]
        c.addProperty("App::PropertyString","Object2","ConstraintInfo").Object2 = cParms[1][0]
        c.addProperty("App::PropertyString","SubElement2","ConstraintInfo").SubElement2 = cParms[1][1]

        doc = FreeCAD.activeDocument()
        ob1 = doc.getObject(c.Object1)
        ob2 = doc.getObject(c.Object2)
        axis1 = getAxis(ob1, c.SubElement1)
        axis2 = getAxis(ob2, c.SubElement2)
        angle = math.degrees(axis1.getAngle(axis2))
        
        c.addProperty("App::PropertyEnumeration","directionConstraint", "ConstraintInfo")
        c.directionConstraint = ["aligned","opposed"]

        if angle <= 90.0:
            c.directionConstraint = "aligned"
        else:
            c.directionConstraint = "opposed"

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
            ':/icons/a2p_AxisParallelConstraint.svg',
            True, cParms[1][2],
            cParms[0][2],
            extraText
            )
    else:
        c = objectToUpdate
        c.Object1 = cParms[0][0]
        c.SubElement1 = cParms[0][1]
        c.Object2 = cParms[1][0]
        c.SubElement2 = cParms[1][1]
        updateObjectProperties(c)

    c.purgeTouched()
    c.Proxy.callSolveConstraints()


selection_text = \
'''
1.) linearEdge or cylinderFace from a part
2.) linearEdge or cylinderFace from another part
'''

toolTipText = \
'''
Add an axisParallel constraint between two objects

Axis' will only rotate to be parallel, but not be
moved to be coincident

select:
1.) linearEdge or cylinderFace from a part
2.) linearEdge or cylinderFace from another part
'''

class a2p_AxisParallelCommand:
    def Activated(self):
        selection = FreeCADGui.Selection.getSelectionEx()
        if len(selection) == 2:
            parseSelection( selection )
        else:
            FreeCADGui.Selection.clearSelection()
            ConstraintSelectionObserver(
                 PlanesParallelSelectionGate(),
                 parseSelection,
                 taskDialog_title ='add planesParallel constraint',
                 taskDialog_iconPath = self.GetResources()['Pixmap'],
                 taskDialog_text = selection_text,
                 secondSelectionGate = PlanesParallelSelectionGate2() )

    def GetResources(self):
        return {
             'Pixmap' : ':/icons/a2p_AxisParallelConstraint.svg',
             'MenuText': 'Add axisParallel constraint',
             'ToolTip': toolTipText
             }

FreeCADGui.addCommand('a2p_AxisParallelCommand', a2p_AxisParallelCommand())
