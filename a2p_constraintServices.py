#***************************************************************************
#*                                                                         *
#*   Copyright (c) 2020 kbwbe                                              *
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

import FreeCAD
import FreeCADGui
from PySide import QtGui
import a2plib
import a2p_constraints

#==============================================================================
def redefineConstraintDirections(doc):
    '''
    recalculate value of property 'direction' and the sign of property 'offset' of all
    a2p-constraints of a document, in order to reach a solvable state if 
    possible.
    '''
    constraints = [ obj for obj in doc.Objects if 'ConstraintInfo' in obj.Content]
    for c in constraints:
        if c.Type == 'pointIdentity':
            a2p_constraints.PointIdentityConstraint.recalculateMatingDirection(c)
        elif c.Type == 'pointOnLine':
            a2p_constraints.PointOnLineConstraint.recalculateMatingDirection(c)
        elif c.Type == 'pointOnPlane':
            a2p_constraints.PointOnPlaneConstraint.recalculateMatingDirection(c)
        elif c.Type == 'circularEdge':
            a2p_constraints.CircularEdgeConstraint.recalculateMatingDirection(c)
        elif c.Type == 'axial':
            a2p_constraints.AxialConstraint.recalculateMatingDirection(c)
        elif c.Type == 'axisParallel':
            a2p_constraints.AxisParallelConstraint.recalculateMatingDirection(c)
        elif c.Type == 'axisPlaneParallel':
            a2p_constraints.AxisPlaneParallelConstraint.recalculateMatingDirection(c)
        elif c.Type == 'axisPlaneAngle':
            a2p_constraints.AxisPlaneAngleConstraint.recalculateMatingDirection(c)
        elif c.Type == 'axisPlaneNormal':
            a2p_constraints.AxisPlaneNormalConstraint.recalculateMatingDirection(c)
        elif c.Type == 'planesParallel':
            a2p_constraints.PlanesParallelConstraint.recalculateMatingDirection(c)
        elif c.Type == 'plane':
            a2p_constraints.PlaneConstraint.recalculateMatingDirection(c)
        elif c.Type == 'angledPlanes':
            a2p_constraints.AngledPlanesConstraint.recalculateMatingDirection(c)
        elif c.Type == 'sphereCenterIdent':
            a2p_constraints.SphericalConstraint.recalculateMatingDirection(c)
        elif c.Type == 'CenterOfMass':
            a2p_constraints.CenterOfMassConstraint.recalculateMatingDirection(c)
        else:
            a2p_constraints.BasicConstraint.recalculateMatingDirection(c) #Throws exception...
            

#==============================================================================
class a2p_redefineConstraintDirectionsCommand:
    def Activated(self):
        flags = QtGui.QMessageBox.StandardButton.Yes | QtGui.QMessageBox.StandardButton.No
        response = QtGui.QMessageBox.information(
            QtGui.QApplication.activeWindow(), 
            u'Recalculate direction of constraints', 
            u'Do you really want to recalculate\nthe directions of all constraints?', 
            flags
            )
        if response == QtGui.QMessageBox.Yes:
            doc = FreeCAD.activeDocument()
            doc.openTransaction("Recalcule constraint's directions")
            redefineConstraintDirections(doc)
            doc.commitTransaction()
                    
    def IsActive(self):
        if FreeCAD.activeDocument() is None: return False
        return True
                    
    def GetResources(self):
        return {
            'Pixmap'  : a2plib.pathOfModule()+'/icons/a2p_PartialProcessing.svg',
            'MenuText': 'Redefine directions of all constraints',
            'ToolTip': 'Redefine directions of all constraints'
            }
FreeCADGui.addCommand('a2p_redefineConstraintDirectionsCommand', a2p_redefineConstraintDirectionsCommand())
#==============================================================================



