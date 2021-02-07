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
def redAdjustConstraintDirections(doc):
    '''
    recalculate value of property 'direction' and the sign of property 'offset' of all
    a2p-constraints of a document, in order to reach a solvable state if 
    possible, especially used after updating of imported parts.
    '''
    unknown_constraints = []
    constraints = [ obj for obj in doc.Objects if 'ConstraintInfo' in obj.Content]
    for c in constraints:
        try: #process as much constraints as possible
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
            print("Errors occured during processing of {}".format(c.Label))
        
    if len(unknown_constraints) > 0:
        print("redefineConstraintDirections(): Found unknown constraints: {}".format(
            set(unknown_constraints)
            )
        )
#==============================================================================
class a2p_reAdjustConstraintDirectionsCommand:
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
            doc.openTransaction("Readjust constraint's directions")
            redAdjustConstraintDirections(doc)
            doc.commitTransaction()
                    
    def IsActive(self):
        if FreeCAD.activeDocument() is None: return False
        return True
                    
    def GetResources(self):
        return {
            'Pixmap'  : a2plib.pathOfModule()+'/icons/a2p_ReAdjustConstraints.svg',
            'MenuText': 'Readjust directions of all constraints',
            'ToolTip': 'Readjust directions of all constraints to fit best'
            }
FreeCADGui.addCommand('a2p_reAdjustConstraintDirectionsCommand', a2p_reAdjustConstraintDirectionsCommand())
#==============================================================================
def updateConstraintsGeoRefs(doc,obj,cacheContent):
    if not a2plib.getUseTopoNaming(): return
    
    # return if there are no constraints linked to the object 
    if len([c for c in doc.Objects if  'ConstraintInfo' in c.Content and obj.Name in [c.Object1, c.Object2] ]) == 0:
        return

    deletionList = [] #for broken constraints

    partName = obj.Name
    for c in doc.Objects:
        if 'ConstraintInfo' in c.Content:
            if partName == c.Object1:
                SubElement = "SubElement1"
                topoName = "Toponame1"
            elif partName == c.Object2:
                SubElement = "SubElement2"
                topoName = "Toponame2"
            else:
                SubElement = None
            
            topoString = None    
            try:
                topoString = getattr(c,topoName)
            except:
                pass
            
            if topoString is None or topoString == "":
                print(u"missing toponame for {}, do not update this constraint".format(c.Name))
                continue
                
            if SubElement: #same as subElement <> None
                subElementName = getattr(c, SubElement)
                if subElementName[:4] == 'Face':
                    try:
                        newIndex = cacheContent.faceNames.index(topoString)
                        newSubElementName = 'Face'+str(newIndex+1)
                    except:
                        newIndex = -1
                        newSubElementName = 'INVALID'
                        
                elif subElementName[:4] == 'Edge':
                    try:
                        newIndex = cacheContent.edgeNames.index(topoString)
                        newSubElementName = 'Edge'+str(newIndex+1)
                    except:
                        newIndex = -1
                        newSubElementName = 'INVALID'
                        
                elif subElementName[:6] == 'Vertex':
                    try:
                        newIndex = cacheContent.vertexNames.index(topoString)
                        newSubElementName = 'Vertex'+str(newIndex+1)
                    except:
                        newIndex = -1
                        newSubElementName = 'INVALID'
                        
                else:
                    newIndex = -1
                    newSubElementName = 'INVALID'
                
                if newIndex >= 0:
                    setattr(c, SubElement, newSubElementName )
                    print (u"Updating by SubElement-Map: {} => {} ".format(
                               subElementName,newSubElementName
                               )
                           )
                    continue
                #
                # if code coming here, constraint is broken
                if c.Name not in deletionList:
                    deletionList.append(c.Name)

    if len(deletionList) > 0: # there are broken constraints..
        for cName in deletionList:
        
            flags = QtGui.QMessageBox.StandardButton.Yes | QtGui.QMessageBox.StandardButton.Abort
            message = "Constraint %s is broken. Delete constraint? Otherwise check for wrong linkage." % cName
            #response = QtGui.QMessageBox.critical(QtGui.qApp.activeWindow(), "Broken Constraint", message, flags )
            response = QtGui.QMessageBox.critical(None, "Broken Constraint", message, flags )
        
            if response == QtGui.QMessageBox.Yes:
                FreeCAD.Console.PrintError("Removing constraint %s" % cName)
                c = doc.getObject(cName)
                a2plib.removeConstraint(c)
#=====================================================================================




