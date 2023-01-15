# ***************************************************************************
# *                                                                         *
# *   Copyright (c) 2020 kbwbe                                              *
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

from PySide import QtGui

import FreeCAD
import FreeCADGui
import a2plib
import a2p_constraints

translate = FreeCAD.Qt.translate


def redAdjustConstraintDirections(doc):
    """
    Recalculate value of property 'direction' and the sign of property 'offset'
    of all a2p-constraints of a document, in order to reach a solvable state if
    possible, especially used after updating of imported parts.
    """
    result = []  # Added for Constraint Diagnostic function
    unknown_constraints = []
    constraints = [obj for obj in doc.Objects if 'ConstraintInfo' in obj.Content]
    for c in constraints:
        try:  # process as much constraints as possible
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
                unknown_constraints.append(c.Type)
        except:
        # Print - All not Ok, we have errors
            print(translate(
                            "A2plus",
                            "Errors occurred during processing of {}").format(
                            c.Label
                            )
                  )
            result.append(c.Name)   # Added for Constraint Diagnostic function

    if len(unknown_constraints) > 0:
        # Print - All not Ok, we have problem
        print(translate(
                        "A2plus_Constraints",
                        "redAdjustConstraintDirections(): Found unknown constraints: {}"
                        ).format(
                        set(unknown_constraints)
                         )
              )
    else:
        # Print - All Ok
        print(translate("A2plus_Constraints", "A2plus: All constraints are recalculated."))

    return(result)                  # Added for Constraint Diagnostic function


class a2p_reAdjustConstraintDirectionsCommand:
    def Activated(self):
        flags = QtGui.QMessageBox.StandardButton.Yes | QtGui.QMessageBox.StandardButton.No
        response = QtGui.QMessageBox.information(
            QtGui.QApplication.activeWindow(),
            translate("A2plus_Constraints", "Recalculate direction of constraints"),
            translate("A2plus_Constraints", "Do you really want to recalculate the directions of all constraints?"),
            flags
            )
        if response == QtGui.QMessageBox.Yes:
            doc = FreeCAD.activeDocument()
            doc.openTransaction("Readjust constraint's directions")
            redAdjustConstraintDirections(doc)
            doc.commitTransaction()

    def IsActive(self):
        if FreeCAD.activeDocument() is None:
            return False
        return True

    def GetResources(self):
        return {
            'Pixmap': a2plib.get_module_path()+'/icons/a2p_ReAdjustConstraints.svg',
            'MenuText': translate("A2plus_Constraints", "Re-adjust directions of all constraints"),
            'ToolTip': translate("A2plus_Constraints", "Re-adjust directions of all constraints to best fit")
            }


FreeCADGui.addCommand('a2p_reAdjustConstraintDirectionsCommand', a2p_reAdjustConstraintDirectionsCommand())
