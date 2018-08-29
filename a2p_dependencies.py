#***************************************************************************
#*                                                                         *
#*   Copyright (c) 2018 kbwbe                                              *
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

import random
import time
import traceback
import math
import copy
import FreeCAD, FreeCADGui, Part
from PySide import QtGui, QtCore
from  FreeCAD import Base
import a2plib
from a2plib import (
    drawVector,
    path_a2p,
    getObjectVertexFromName,
    getObjectEdgeFromName,
    getObjectFaceFromName,
    isLine,
    getPos,
    getAxis,
    appVersionStr,
    Msg,
    DebugMsg,
    A2P_DEBUG_LEVEL,
    A2P_DEBUG_1,
    A2P_DEBUG_2,
    A2P_DEBUG_3,
    )

import a2p_libDOF
from a2p_libDOF import (
    SystemOrigin,
    SystemXAxis,
    SystemYAxis,
    SystemZAxis,
    initPosDOF,
    initRotDOF,
    AxisAlignment,
    AxisDistance,
    PlaneOffset,
    LockRotation,
    AngleAlignment,
    PointIdentity,
    create_Axis,
    cleanAxis,
    create_Axis2Points
    
    )
import os, sys

#------------------------------------------------------------------------------
class Dependency():
    def __init__(self, constraint, refType, axisRotation):
        self.Enabled = False
        self.Type = None
        self.refType = refType
        self.isPointConstraint = False
        self.refPoint = None
        self.refAxisEnd = None
        self.direction = None
        self.offset = None
        self.angle = None
        self.foreignDependency = None
        self.moveVector = None          # TODO: Not used?
        self.currentRigid = None
        self.dependedRigid = None
        self.constraint = constraint    # TODO: remove, probably not needed
        self.axisRotationEnabled = axisRotation
        self.lockRotation = False

        self.Type = constraint.Type
        try:
            self.direction = constraint.directionConstraint
        except:
            pass # not all constraints do have direction-Property
        try:
            self.offset = constraint.offset
        except:
            pass # not all constraints do have offset-Property
        try:
            self.angle = constraint.angle
        except:
            pass # not all constraints do have angle-Property
        try:
            self.lockRotation = constraint.lockRotation
        except:
            pass # not all constraints do have lockRotation

    def clear(self):
        self.Type = None
        self.Enabled = False
        self.refType = None
        self.refPoint = None
        self.isPointConstraint = None
        self.refAxisEnd = None
        self.direction = None
        self.offset = None
        self.angle = None
        self.foreignDependency = None
        self.moveVector = None
        self.currentRigid = None
        self.dependedRigid = None
        self.constraint = None
        self.axisRotationEnabled = False
        self.lockRotation = False

    def __str__(self):
        return "Dependencies between {}-{}, type {}".format(
            self.currentRigid.label,
            self.dependedRigid.label,
            self.Type
            )

    @staticmethod
    def Create(doc, constraint, solver, rigid1, rigid2):
        DebugMsg(
            A2P_DEBUG_2,
            "Creating dependencies between {}-{}, type {}\n".format(
                rigid1.label,
                rigid2.label,
                constraint.Type
                )
            )

        c = constraint

        if c.Type == "pointIdentity":
            dep1 = DependencyPointIdentity(c, "point")
            dep2 = DependencyPointIdentity(c, "point")

            ob1 = doc.getObject(c.Object1)
            ob2 = doc.getObject(c.Object2)

            vert1 = getObjectVertexFromName(ob1, c.SubElement1)
            vert2 = getObjectVertexFromName(ob2, c.SubElement2)
            dep1.refPoint = vert1.Point
            dep2.refPoint = vert2.Point

        elif c.Type == "sphereCenterIdent":
            dep1 = DependencyPointIdentity(c, "point")
            dep2 = DependencyPointIdentity(c, "point")

            ob1 = doc.getObject(c.Object1)
            ob2 = doc.getObject(c.Object2)

            vert1 = getPos(ob1, c.SubElement1)
            vert2 = getPos(ob2, c.SubElement2)
            dep1.refPoint = vert1
            dep2.refPoint = vert2

        elif c.Type == "pointOnLine":
            dep1 = DependencyPointOnLine(c, "point")
            dep2 = DependencyPointOnLine(c, "pointAxis")

            ob1 = doc.getObject(c.Object1)
            ob2 = doc.getObject(c.Object2)

            vert1 = getObjectVertexFromName(ob1, c.SubElement1)
            line2 = getObjectEdgeFromName(ob2, c.SubElement2)
            dep1.refPoint = vert1.Point
            dep2.refPoint = getPos(ob2, c.SubElement2)

            axis2 = getAxis(ob2, c.SubElement2)
            dep2.refAxisEnd = dep2.refPoint.add(axis2)

        elif c.Type == "pointOnPlane":
            dep1 = DependencyPointOnPlane(c, "point")
            dep2 = DependencyPointOnPlane(c, "plane")

            ob1 = doc.getObject(c.Object1)
            ob2 = doc.getObject(c.Object2)

            vert1 = getObjectVertexFromName(ob1, c.SubElement1)
            plane2 = getObjectFaceFromName(ob2, c.SubElement2)
            dep1.refPoint = vert1.Point
            dep2.refPoint = plane2.Faces[0].BoundBox.Center

            normal2 = plane2.Surface.Axis
            dep2.refAxisEnd = dep2.refPoint.add(normal2)

        elif c.Type == "circularEdge":
            dep1 = DependencyCircularEdge(c, "pointAxis")
            dep2 = DependencyCircularEdge(c, "pointAxis")

            ob1 = doc.getObject(c.Object1)
            ob2 = doc.getObject(c.Object2)
            circleEdge1 = getObjectEdgeFromName(ob1, c.SubElement1)
            circleEdge2 = getObjectEdgeFromName(ob2, c.SubElement2)
            dep1.refPoint = circleEdge1.Curve.Center
            dep2.refPoint = circleEdge2.Curve.Center

            axis1 = circleEdge1.Curve.Axis
            axis2 = circleEdge2.Curve.Axis
            if dep2.direction == "opposed":
                axis2.multiply(-1.0)
            dep1.refAxisEnd = dep1.refPoint.add(axis1)
            dep2.refAxisEnd = dep2.refPoint.add(axis2)
            #
            if abs(dep2.offset) > solver.mySOLVER_SPIN_ACCURACY * 1e-1:
                offsetAdjustVec = Base.Vector(axis2.x,axis2.y,axis2.z)
                offsetAdjustVec.multiply(dep2.offset)
                dep2.refPoint = dep2.refPoint.add(offsetAdjustVec)
                dep2.refAxisEnd = dep2.refAxisEnd.add(offsetAdjustVec)

        elif c.Type == "planesParallel":
            dep1 = DependencyParallelPlanes(c, "pointNormal")
            dep2 = DependencyParallelPlanes(c, "pointNormal")

            ob1 = doc.getObject(c.Object1)
            ob2 = doc.getObject(c.Object2)
            plane1 = getObjectFaceFromName(ob1, c.SubElement1)
            plane2 = getObjectFaceFromName(ob2, c.SubElement2)
            dep1.refPoint = plane1.Faces[0].BoundBox.Center
            dep2.refPoint = plane2.Faces[0].BoundBox.Center

            normal1 = plane1.Surface.Axis
            normal2 = plane2.Surface.Axis
            if dep2.direction == "opposed":
                normal2.multiply(-1.0)
            dep1.refAxisEnd = dep1.refPoint.add(normal1)
            dep2.refAxisEnd = dep2.refPoint.add(normal2)

        elif c.Type == "angledPlanes":
            dep1 = DependencyAngledPlanes(c, "pointNormal")
            dep2 = DependencyAngledPlanes(c, "pointNormal")

            ob1 = doc.getObject(c.Object1)
            ob2 = doc.getObject(c.Object2)
            plane1 = getObjectFaceFromName(ob1, c.SubElement1)
            plane2 = getObjectFaceFromName(ob2, c.SubElement2)
            dep1.refPoint = plane1.Faces[0].BoundBox.Center
            dep2.refPoint = plane2.Faces[0].BoundBox.Center

            normal1 = plane1.Surface.Axis
            normal2 = plane2.Surface.Axis
            dep1.refAxisEnd = dep1.refPoint.add(normal1)
            dep2.refAxisEnd = dep2.refPoint.add(normal2)

        elif c.Type == "plane":
            dep1 = DependencyPlane(c, "pointNormal")
            dep2 = DependencyPlane(c, "pointNormal")

            ob1 = doc.getObject(c.Object1)
            ob2 = doc.getObject(c.Object2)
            plane1 = getObjectFaceFromName(ob1, c.SubElement1)
            plane2 = getObjectFaceFromName(ob2, c.SubElement2)
            dep1.refPoint = plane1.Faces[0].BoundBox.Center
            dep2.refPoint = plane2.Faces[0].BoundBox.Center

            normal1 = plane1.Surface.Axis
            normal2 = plane2.Surface.Axis
            if dep2.direction == "opposed":
                normal2.multiply(-1.0)
            dep1.refAxisEnd = dep1.refPoint.add(normal1)
            dep2.refAxisEnd = dep2.refPoint.add(normal2)
            #
            if abs(dep2.offset) > solver.mySOLVER_SPIN_ACCURACY * 1e-1:
                offsetAdjustVec = Base.Vector(normal2.x,normal2.y,normal2.z)
                offsetAdjustVec.multiply(dep2.offset)
                dep2.refPoint = dep2.refPoint.add(offsetAdjustVec)
                dep2.refAxisEnd = dep2.refAxisEnd.add(offsetAdjustVec)

        elif c.Type == "axial":
            dep1 = DependencyAxial(c, "pointAxis")
            dep2 = DependencyAxial(c, "pointAxis")

            ob1 = doc.getObject(c.Object1)
            ob2 = doc.getObject(c.Object2)
            dep1.refPoint = getPos(ob1,c.SubElement1)
            dep2.refPoint = getPos(ob2,c.SubElement2)
            axis1 = getAxis(ob1, c.SubElement1)
            axis2 = getAxis(ob2, c.SubElement2)
            if dep2.direction == "opposed":
                axis2.multiply(-1.0)
            dep1.refAxisEnd = dep1.refPoint.add(axis1)
            dep2.refAxisEnd = dep2.refPoint.add(axis2)

        else:
            raise NotImplementedError("Constraint type {} was not implemented!".format(c.Type))

        # Assignments
        dep1.currentRigid = rigid1
        dep1.dependedRigid = rigid2
        dep1.foreignDependency = dep2

        dep2.currentRigid = rigid2
        dep2.dependedRigid = rigid1
        dep2.foreignDependency = dep1

        rigid1.dependencies.append(dep1)
        rigid2.dependencies.append(dep2)

    def applyPlacement(self, placement):
        if self.refPoint != None:
            self.refPoint = placement.multVec(self.refPoint)
        if self.refAxisEnd != None:
            self.refAxisEnd = placement.multVec(self.refAxisEnd)

    def enable(self, workList):
        if self.dependedRigid not in workList:
            DebugMsg(
                A2P_DEBUG_2,
                "{} - not in working list\n".format(self)
                )
            return

        self.Enabled = True
        self.foreignDependency.Enabled = True
        DebugMsg(
            A2P_DEBUG_2,
            "{} - enabled\n".format(self)
            )

    def disable(self):
        self.Enabled = False
        self.foreignDependency.Enabled = False

    def getMovement(self):
        raise NotImplementedError("Dependency class {} doesn't implement movement, use inherited classes instead!".format(self.__class__.__name__))

    def calcDOF(self, _dofRot, _dofPos, _pointconstraints = []):
        raise NotImplementedError("Dependency class {} doesn't implement calcDOF, use inherited classes instead!".format(self.__class__.__name__))


    def getRotation(self, solver):
        if not self.Enabled: return None
        if not self.axisRotationEnabled: return None

        # The rotation is the same for all dependencies that enabled it
        # Special dependency cases are implemented in its own class

        axis = None # Rotation axis to be returned

        if self.direction != "none":
            rigAxis = self.refAxisEnd.sub(self.refPoint)
            foreignDep = self.foreignDependency
            foreignAxis = foreignDep.refAxisEnd.sub(foreignDep.refPoint)
            #
            #do we have wrong alignment of axes ??
            dot = rigAxis.dot(foreignAxis)
            if abs(dot+1.0) < solver.mySOLVER_SPIN_ACCURACY*1e-1: #both axes nearly aligned but false orientation...
                x = random.uniform(-solver.mySOLVER_SPIN_ACCURACY*1e-1,solver.mySOLVER_SPIN_ACCURACY*1e-1)
                y = random.uniform(-solver.mySOLVER_SPIN_ACCURACY*1e-1,solver.mySOLVER_SPIN_ACCURACY*1e-1)
                z = random.uniform(-solver.mySOLVER_SPIN_ACCURACY*1e-1,solver.mySOLVER_SPIN_ACCURACY*1e-1)
                disturbVector = Base.Vector(x,y,z)
                foreignAxis = foreignAxis.add(disturbVector)

            #axis = foreignAxis.cross(rigAxis)
            axis = rigAxis.cross(foreignAxis)
            try:
                axis.normalize()
                angle = foreignAxis.getAngle(rigAxis)
                axis.multiply(math.degrees(angle))
            except:
                axis = None

        else: #if dep.direction... (== none)
            rigAxis = self.refAxisEnd.sub(self.refPoint)
            foreignDep = self.foreignDependency
            foreignAxis = foreignDep.refAxisEnd.sub(foreignDep.refPoint)
            angle1 = abs(foreignAxis.getAngle(rigAxis))
            angle2 = math.pi-angle1
            #
            if angle1<=angle2:
                axis = rigAxis.cross(foreignAxis)
            else:
                foreignAxis.multiply(-1.0)
                axis = rigAxis.cross(foreignAxis)
            try:
                axis.normalize()
                angle = foreignAxis.getAngle(rigAxis)
                axis.multiply(math.degrees(angle))
            except:
                axis = None

        return axis

#------------------------------------------------------------------------------

class DependencyPointIdentity(Dependency):
    def __init__(self, constraint, refType):
        Dependency.__init__(self, constraint, refType, False)
        self.isPointConstraint = True

    def getMovement(self):
        if not self.Enabled: return None, None

        moveVector = self.foreignDependency.refPoint.sub(self.refPoint)
        return self.refPoint, moveVector

    def calcDOF(self, _dofPos, _dofRot, _pointconstraints=[]):
        #PointIdentity, PointOnLine, PointOnPlane, Spherical Constraints:
        #    PointIdentityPos()    needs to know the point constrained as vector, the dofpos array, the rigid center point as vector and
        #                        the pointconstraints which stores all point constraints of the rigid
        #    PointIdentityRot()    needs to know the point constrained as vector, the dofrot array, and
        #                        the pointconstraints which stores all point constraints of the rigid
        # These constraint have to be the last evaluated in the chain of constraints.
            
        tmpaxis = cleanAxis(create_Axis(self.refPoint, self.currentRigid.getRigidCenter()))
        #dofpos = PointIdentityPos(tmpaxis,_dofPos,_pointconstraints)
        #dofrot = PointIdentityRot(tmpaxis,_dofRot,_pointconstraints)
        return PointIdentity(tmpaxis, _dofPos, _dofRot, _pointconstraints)

class DependencyPointOnLine(Dependency):
    def __init__(self, constraint, refType):
        Dependency.__init__(self, constraint, refType, False)
        self.isPointConstraint = True

    def getMovement(self):
        if not self.Enabled: return None, None

        if self.refType == "point":
            vec1 = self.foreignDependency.refPoint.sub(self.refPoint)
            axis1 = self.foreignDependency.refAxisEnd.sub(self.foreignDependency.refPoint)
            dot = vec1.dot(axis1)
            axis1.multiply(dot) #projection of vec1 on axis1
            moveVector = vec1.sub(axis1)
            return self.refPoint, moveVector

        elif self.refType == "pointAxis":
            # refPoint is calculated in special way below
            vec1 = self.foreignDependency.refPoint.sub(self.refPoint)
            axis1 = self.refAxisEnd.sub(self.refPoint)
            dot = vec1.dot(axis1)
            axis1.multiply(dot) #projection of vec1 on axis1
            verticalRefOnLine = self.refPoint.add(axis1) #makes spinning around possible
            moveVector = vec1.sub(axis1)
            return verticalRefOnLine, moveVector

        else:
            raise NotImplementedError("Wrong refType for class {}".format(self.__class__.__name__))
            
    def calcDOF(self, _dofPos, _dofRot, _pointconstraints=[]):
        #PointIdentity, PointOnLine, PointOnPlane, Spherical Constraints:
        #    PointIdentityPos()    needs to know the point constrained as vector, the dofpos array, the rigid center point as vector and
        #                        the pointconstraints which stores all point constraints of the rigid
        #    PointIdentityRot()    needs to know the point constrained as vector, the dofrot array, and
        #                        the pointconstraints which stores all point constraints of the rigid
        # These constraint have to be the last evaluated in the chain of c    
        tmpaxis = cleanAxis(create_Axis(self.refPoint, self.currentRigid.getRigidCenter()))
        #dofpos = PointIdentityPos(tmpaxis,_dofPos,_pointconstraints)
        #dofrot = PointIdentityRot(tmpaxis,_dofRot,_pointconstraints)
        return PointIdentity(tmpaxis, _dofPos, _dofRot, _pointconstraints)
               


class DependencyPointOnPlane(Dependency):
    def __init__(self, constraint, refType):
        Dependency.__init__(self, constraint, refType, False)
        self.isPointConstraint = True

    def getMovement(self):
        if not self.Enabled: return None, None

        if self.refType == "point":
            vec1 = self.foreignDependency.refPoint.sub(self.refPoint)
            # Now move along foreign axis
            normal1 = self.foreignDependency.refAxisEnd.sub(self.foreignDependency.refPoint)
            dot = vec1.dot(normal1)
            normal1.multiply(dot)
            moveVector = normal1
            return self.refPoint, moveVector

        elif self.refType == "plane":
            # refPoint is calculated in special way below
            vec1 = self.foreignDependency.refPoint.sub(self.refPoint)
            normal1 = self.refAxisEnd.sub(self.refPoint) # move along own axis
            dot = vec1.dot(normal1)
            normal1.multiply(dot)
            moveVector = normal1
            verticalRefPointOnPlane = vec1.sub(moveVector)  #makes spinning around possible
            return verticalRefPointOnPlane, moveVector

        else:
            raise NotImplementedError("Wrong refType for class {}".format(self.__class__.__name__))

    def calcDOF(self, _dofPos, _dofRot, _pointconstraints=[]):
        #PointIdentity, PointOnLine, PointOnPlane, Spherical Constraints:
        #    PointIdentityPos()    needs to know the point constrained as vector, the dofpos array, the rigid center point as vector and
        #                        the pointconstraints which stores all point constraints of the rigid
        #    PointIdentityRot()    needs to know the point constrained as vector, the dofrot array, and
        #                        the pointconstraints which stores all point constraints of the rigid
        # These constraint have to be the last evaluated in the chain of constraints.
               
        tmpaxis = cleanAxis(create_Axis(self.refPoint, self.currentRigid.getRigidCenter()))
        
        #dofpos = PointIdentityPos(tmpaxis,_dofPos,_pointconstraints)
        #dofrot = PointIdentityRot(tmpaxis,_dofRot,_pointconstraints)
        return PointIdentity(tmpaxis, _dofPos, _dofRot, _pointconstraints)
        
class DependencyCircularEdge(Dependency):
    def __init__(self, constraint, refType):
        Dependency.__init__(self, constraint, refType, True)
        self.isPointConstraint = False

    def getMovement(self):
        if not self.Enabled: return None, None

        moveVector = self.foreignDependency.refPoint.sub(self.refPoint)
        return self.refPoint, moveVector
      
    def calcDOF(self, _dofPos, _dofRot, _pointconstraints=[]):
        #function used to determine the dof lost due to this constraint
        #CircularEdgeConstraint:
        #    AxisAlignment()    needs to know the axis normal to circle (stored in dep as refpoint and refAxisEnd) and the dofrot array
        #    AxisDistance()     needs to know the axis normal to circle (stored in dep as refpoint and refAxisEnd) and the dofpos array
        #    PlaneOffset()      needs to know the axis normal to circle (stored in dep as refpoint and refAxisEnd) and the dofpos array
        #    LockRotation()     need to know if LockRotation is True or False and the array dofrot
        #
        #    honestly speaking this would be simplified like this:
        #    if LockRotation:
        #        dofpos = []
        #        dofrot = []
        #    else:
        #        dofpos = []
        #        dofrot = AxisAlignment(ConstraintAxis, dofrot)
        if self.lockRotation:
            return [], []
        else:
            tmpaxis = cleanAxis(create_Axis2Points(self.refPoint,self.refAxisEnd))
            return [], AxisAlignment(tmpaxis,_dofRot)

class DependencyParallelPlanes(Dependency):
    def __init__(self, constraint, refType):
        Dependency.__init__(self, constraint, refType, True)
        self.isPointConstraint = False

    def getMovement(self):
        if not self.Enabled: return None, None

        return self.refPoint, Base.Vector(0,0,0)
            
    def calcDOF(self, _dofPos, _dofRot, _pointconstraints=[]):
        #PlanesParallelConstraint:
        #    AxisAlignment()    needs to know the axis normal to the plane constrained (stored in dep as refpoint and refAxisEnd) and the dofrot array
        tmpaxis = cleanAxis(create_Axis2Points(self.refPoint,self.refAxisEnd))
        tmpaxis.Direction.Length = 2.0
        return _dofPos, AxisAlignment(tmpaxis,_dofRot)

class DependencyAngledPlanes(Dependency):
    def __init__(self, constraint, refType):
        Dependency.__init__(self, constraint, refType, True)
        self.isPointConstraint = False
        
    def getMovement(self):
        if not self.Enabled: return None, None

        return self.refPoint, Base.Vector(0,0,0)

    def getRotation(self, solver):
        if not self.Enabled: return None

        axis = None # Rotation axis to be returned

        rigAxis = self.refAxisEnd.sub(self.refPoint)
        foreignDep = self.foreignDependency
        foreignAxis = foreignDep.refAxisEnd.sub(foreignDep.refPoint)
        recentAngle = math.degrees(foreignAxis.getAngle(rigAxis))
        deltaAngle = abs(self.angle.Value) - recentAngle
        try:
            axis = rigAxis.cross(foreignAxis)
            axis.normalize()
            axis.multiply(-deltaAngle)
            '''
            print (
                "Axis: {}, Length: {} RecentAngle: {} deltaAngle: {}".format(
                    axis,
                    axis.Length,
                    recentAngle,
                    deltaAngle
                    )
                )
            '''
        except: #axis = Vector(0,0,0) and cannot be normalized...
            #print ("Exception in angledPlanes.getRotation\n")
            pass
        #DebugMsg(A2P_DEBUG_3, "{} - rotate by {}\n".format(self, axis.Length))
        return axis
    
    def calcDOF(self, _dofPos, _dofRot, _pointconstraints=[]):
        #AngleBetweenPlanesConstraint
        #    AngleAlignment()   needs to know the axis normal to plane constrained (stored in dep as refpoint and refAxisEnd) and the dofrot array
        tmpaxis = cleanAxis(create_Axis2Points(self.refPoint,self.refAxisEnd))
        tmpaxis.Direction.Length = 2.0
        return _dofPos, AngleAlignment(tmpaxis,_dofRot)

class DependencyPlane(Dependency):
    def __init__(self, constraint, refType):
        Dependency.__init__(self, constraint, refType, True)
        self.isPointConstraint = False

    def getMovement(self):
        if not self.Enabled: return None, None

        vec1 = self.foreignDependency.refPoint.sub(self.refPoint)
        # move along foreign axis...
        normal1 = self.foreignDependency.refAxisEnd.sub(self.foreignDependency.refPoint)
        dot = vec1.dot(normal1)
        normal1.multiply(dot)
        moveVector = normal1
        #DebugMsg(A2P_DEBUG_3,"{} - move by {}\n".format(self, moveVector.Length))
        return self.refPoint, moveVector

    def calcDOF(self, _dofPos, _dofRot, _pointconstraints=[]):
        #PlaneCoincident:
        #    AxisAlignment()    needs to know the axis normal to the plane constrained (stored in dep as refpoint and refAxisEnd) and the dofrot array
        #    PlaneOffset()      needs to know the axis normal to the plane constrained (stored in dep as refpoint and refAxisEnd) and the dofpos array
        tmpaxis = cleanAxis(create_Axis2Points(self.refPoint,self.refAxisEnd))
        
        # the axis used on axisalignment isn't a real axis but a random axis normal to the plane
        #set it to length = 2 instead of normalize it
        pos = PlaneOffset(tmpaxis,_dofPos)
        tmpaxis.Direction.Length = 2.0
        return pos, AxisAlignment(tmpaxis,_dofRot)

class DependencyAxial(Dependency):
    def __init__(self, constraint, refType):
        Dependency.__init__(self, constraint, refType, True)
        self.isPointConstraint = False

    def getMovement(self):
        if not self.Enabled: return None, None

        vec1 = self.foreignDependency.refPoint.sub(self.refPoint)
        destinationAxis = self.foreignDependency.refAxisEnd.sub(self.foreignDependency.refPoint)
        dot = vec1.dot(destinationAxis)
        parallelToAxisVec = destinationAxis.normalize().multiply(dot)
        moveVector = vec1.sub(parallelToAxisVec)
        return self.refPoint, moveVector
    
    
    def calcDOF(self, _dofPos, _dofRot, _pointconstraints=[]):
    #AxialConstraint:
    #    AxisAlignment()    needs to know the axis normal to circle (stored in dep as refpoint and refAxisEnd) and the dofrot array
    #    AxisDistance()     needs to know the axis normal to circle (stored in dep as refpoint and refAxisEnd) and the dofpos array
    #    LockRotation()     need to know if LockRotation is True or False and the array dofrot
        tmpaxis = cleanAxis(create_Axis2Points(self.refPoint,self.refAxisEnd))
        
        if self.lockRotation:
            return AxisDistance(tmpaxis,_dofPos), []
        else:
            return AxisDistance(tmpaxis,_dofPos), AxisAlignment(tmpaxis,_dofRot)
    
