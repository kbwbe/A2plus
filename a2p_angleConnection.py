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

from a2plib import *
#from lib3D import *
from pivy import coin
from PySide import QtGui

class PlaneSelectionGate:
    def allow(self, doc, obj, sub):
        s = SelectionExObject(doc, obj, sub)
        return planeSelected(s) or LinearEdgeSelected(s)

def parseSelection(selection, objectToUpdate=None):
    validSelection = False
    if len(selection) == 2:
        s1, s2 = selection
        if s1.ObjectName <> s2.ObjectName:
            if ( planeSelected(s1) or LinearEdgeSelected(s1)) \
                     and ( planeSelected(s2) or LinearEdgeSelected(s2)):
                validSelection = True
                cParms = [ [s1.ObjectName, s1.SubElementNames[0], s1.Object.Label ],
                           [s2.ObjectName, s2.SubElementNames[0], s2.Object.Label ] ]
    if not validSelection:
        msg = '''
              Angle constraint requires a selection of 2 planes or two 
              straight lines, each from different objects.Selection made:
              %s
              '''  % printSelection(selection)
        QtGui.QMessageBox.information(  QtGui.QApplication.activeWindow(), "Incorrect Usage", msg)
        return 
    
    if objectToUpdate == None:
        cName = findUnusedObjectName('angleConstraint')
        c = FreeCAD.ActiveDocument.addObject("App::FeaturePython", cName)
        c.addProperty("App::PropertyString","Type","ConstraintInfo").Type = 'angle_between_planes'
        c.addProperty("App::PropertyString","Object1","ConstraintInfo").Object1 = cParms[0][0]
        c.addProperty("App::PropertyString","SubElement1","ConstraintInfo").SubElement1 = cParms[0][1]
        c.addProperty("App::PropertyString","Object2","ConstraintInfo").Object2 = cParms[1][0]
        c.addProperty("App::PropertyString","SubElement2","ConstraintInfo").SubElement2 = cParms[1][1]
        c.addProperty("App::PropertyAngle","angle","ConstraintInfo")
        c.Object1 = cParms[0][0]
        c.SubElement1 = cParms[0][1]
        c.Object2 = cParms[1][0]
        c.SubElement2 = cParms[1][1]
        for prop in ["Object1","Object2","SubElement1","SubElement2","Type"]:
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
            ':/assembly2/icons/angleConstraint.svg', 
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
    c.Proxy.callSolveConstraints()
         

selection_text = \
  '''
  Selection options:
  - plane surface
  - edge
  '''

class a2p_AngleConnectionCommand:
    def Activated(self):
        selection = FreeCADGui.Selection.getSelectionEx()
        if len(selection) == 2:
            parseSelection( selection )
        else:
            FreeCADGui.Selection.clearSelection()
            ConstraintSelectionObserver( 
                 PlaneSelectionGate(), 
                 parseSelection,
                 taskDialog_title ='add angular constraint', 
                 taskDialog_iconPath = self.GetResources()['Pixmap'], 
                 taskDialog_text = selection_text 
                 )
              
    def GetResources(self): 
        msg = 'Create an angular constraint between two planes'
        return {
             'Pixmap' : path_a2p + '/icons/angleConstraint.svg', 
             'MenuText': msg, 
             'ToolTip': msg,
             } 

FreeCADGui.addCommand('a2p_AngleConnection', a2p_AngleConnectionCommand())

















































