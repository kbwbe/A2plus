# ***************************************************************************
# *                                                                         *
# *   Copyright (c) 2018 Turro75                                              *
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

import FreeCAD, FreeCADGui, Part
from FreeCAD import Base
from PySide import QtGui, QtCore

from a2p_translateUtils import *


"""
Library that defines the DOF of a Rigid, each rigids has several dependencies which define a refPoint(cross point the the axis)
and a refAxisEnd which is a vector that defines the direction, togeher we can define an axis used in the constraint.

This code was possible only after the reading of the Hamish's code on His wonderful Assembly2 Workbench for FreeCAD
This code was possible only after the reading of the code of the wonderful WorkFeature Macro for FreeCAD
This code was possible only after the reading of Wikipedia pages on vector math

"""
# define some reference axis
SystemOrigin = FreeCAD.Vector(0.0, 0.0, 0.0)

SystemXAxis = FreeCAD.Axis()
SystemXAxis.Base = SystemOrigin
SystemXAxis.Direction = SystemXAxis.Direction.add(FreeCAD.Vector(1.0, 0.0, 0.0))

SystemYAxis = FreeCAD.Axis()
SystemYAxis.Base = SystemOrigin
SystemYAxis.Direction = SystemYAxis.Direction.add(FreeCAD.Vector(0.0, 1.0, 0.0))

SystemZAxis = FreeCAD.Axis()
SystemZAxis.Base = SystemOrigin
SystemZAxis.Direction = SystemZAxis.Direction.add(FreeCAD.Vector(0.0, 0.0, 1.0))


# at the beginning each rigid is able to move along and around all six DOF
initPosDOF = [SystemXAxis, SystemYAxis, SystemZAxis]
initRotDOF = [SystemXAxis, SystemYAxis, SystemZAxis]
# another array which stores the vertex used in points constraints (pointIdentity, SphericalIdentity, pointOnLine, pointOnPlane)
PointConstraints = []

tolerance = 1e-4  # --> may be equal to parameter accuracy?

# as first some helper functions

# create an axis from refpoint and refAxisEnd taken from rigid deps
def create_Axis(_base, _direction):
    axis = FreeCAD.Axis()
    axis.Base = _base
    axis.Direction = _direction
    return axis


# create an axis that has Base in the first vector argument and direction defined by _start to _end shifted at SystemOrigin
def create_Axis2Points(_start, _end):
    axis = FreeCAD.Axis()
    axis.Base = _start
    axis.Direction = _end.sub(_start)
    # axis.Direction = _end
    return axis


def zeroIfLessThanTol(vector):
    _vector = FreeCAD.Vector(vector)
    if abs(_vector.x) <= tolerance:
        _vector.x = 0.0
    if abs(_vector.y) <= tolerance:
        _vector.y = 0.0
    if abs(_vector.z) <= tolerance:
        _vector.z = 0.0
    return _vector


def cleanAxis(axisa):
    axis = FreeCAD.Axis(axisa)
    axis.Base = zeroIfLessThanTol(axis.Base)
    try:
        axis.Direction.normalize()
    except:
        pass
    axis.Direction = zeroIfLessThanTol(axis.Direction)
    return axis


def copynorm_AxisToOrigin(axisa, dbg=False):
    offset = SystemOrigin.sub(axisa.Base)
    axisb = FreeCAD.Axis(axisa)
    axisb.Base = SystemOrigin
    return cleanAxis(axisb)


def normal_2Axis(axisa, axisb, dbg=False):
    """
    create an axis which is normal to the plane defined by given 2 axes as argument
    """
    # move vectors to origin and normalize
    axis1 = copynorm_AxisToOrigin(axisa)
    axis2 = copynorm_AxisToOrigin(axisb)
    # create an axis with base at SystemOrigin
    axisN = FreeCAD.Axis()
    # set the right direction
    axisN.Direction = axis1.Direction.cross(axis2.Direction)
    return cleanAxis(axisN)


def make_planeNormal(axisa, dbg=False):
    """
    create a plane normal to the given axis, return the 2 axis which define that plane
    """
    axis1 = copynorm_AxisToOrigin(axisa)

    planenormal = Part.makePlane(1.0, 1.0, axis1.Base, axis1.Direction)
    freeAx1 = FreeCAD.Axis()
    freeAx2 = FreeCAD.Axis()
    freeAx1.Direction = FreeCAD.Vector(planenormal.Vertexes[2].Point)
    freeAx2.Direction = FreeCAD.Vector(planenormal.Vertexes[1].Point)
    return [copynorm_AxisToOrigin(freeAx1), copynorm_AxisToOrigin(freeAx2)]


def check_ifParallel(axisa, axisb, dbg=False):
    """
    check if 2 axes are parallel
    """
    # shift edges to the origin and normalize them
    # move vectors to origin and normalize
    axis1 = copynorm_AxisToOrigin(axisa)
    axis2 = copynorm_AxisToOrigin(axisb)

    if abs((axis1.Direction.cross(axis2.Direction)).Length) <= tolerance:
        return True
    else:
        return False


def check_ifPerpendicular(axisa, axisb, dbg=False):
    """
    check if 2 axes are perpendicular
    """
    # shift edges to the origin and normalize them
    # move vectors to origin and normalize
    axis1 = copynorm_AxisToOrigin(axisa)
    axis2 = copynorm_AxisToOrigin(axisb)

    if abs(axis1.Direction.dot(axis2.Direction)) <= tolerance:
        return True
    else:
        return False


def check_ifCollinear(axisa, axisb, dbg=False):
    """
    check if 2 axes are collinear
    """
    # shift edges to the origin and normalize them
    # move vectors to origin and normalize
    axis1 = FreeCAD.Axis(axisa)
    axis2 = FreeCAD.Axis(axisb)
    if check_ifCoincident(axis1.Base, axis2.Base):
        # same base, if parallel the axis are collinear
        if check_ifParallel(axis1, axis2):
            return True
        else:
            return False
    baseMove = SystemOrigin.sub(axis1.Base)
    axis1.Base = SystemOrigin
    axis2.move(baseMove)
    axis1.Direction = axis1.Direction.normalize()  # useless?
    axis2.Direction = axis2.Direction.normalize()  # useless?
    axis3 = FreeCAD.Axis()
    axis3.Direction = axis2.Base  # create an axis with direction base1 to base2

    if check_ifParallel(axis1, axis3) and check_ifParallel(axis2, axis3):
        return True
    else:
        return False


def check_ifCoincident(Vertex1, Vertex2, dbg=False):
    """
    check if 2 vertexes are coincident
    """
    X1 = Vertex1.x
    X2 = Vertex2.x
    Y1 = Vertex1.y
    Y2 = Vertex2.y
    Z1 = Vertex1.z
    Z2 = Vertex2.z
    if (
        (abs(Z2 - Z1) <= tolerance)
        and (abs(X2 - X1) <= tolerance)
        and (abs(Y2 - Y1) <= tolerance)
    ):
        return True
    else:
        return False


def check_ifPointOnAxis(vertexa, axisa, dbg=False):
    """
    check if a point is on an axis
    """
    # shift edges to the origin and normalize them
    # move vectors to origin and normalize
    axis1 = copynorm_AxisToOrigin(axisa)
    vertex1 = FreeCAD.Vector(vertexa)
    _offset = SystemOrigin.sub(axis1.Base)
    vertex1 = vertex1.add(axis1.Base)  # apply the same offset to the point
    if abs((axis1.Direction.cross(vertex1)).Length) <= tolerance:
        return True
    else:
        return False


# now that all helper functions are in place let's start to analyse all basic constraints
# constraints in the toolbar are a combination of basic constraints

# start with Axis Alignment which takes an axis as arguments and operates according to the remaining dof
# this basic constraint affects only rotation DOF
def AxisAlignment(axisa, dofrot, pointconstraints=None, dbg=True):
    currentDOFROTnum = len(dofrot)
    if currentDOFROTnum == 0:  # already locked on rotation so ignore it
        return []
    elif (
        currentDOFROTnum == 1
    ):  # partially locked on rotation so compare to the given axis
        if check_ifCollinear(axisa, dofrot[0]):
            # the axis are collinear, so the constraint is redundant, skip it
            if dofrot[0].Direction.Length == 2:
                # ok return the axisa as new dofrot
                # axisa.Direction.Length = 1
                return [axisa]
            else:  # (axisa.Direction.Length == 2):
                # ok return the dofrot
                # dofrot[0].Direction.Length = 1
                return dofrot

        elif check_ifParallel(axisa, dofrot[0]):
            # the stored axis isn't a specific axis so check if parallel
            if dofrot[0].Direction.Length == 2:
                # ok return the axisa as new dofrot
                # axisa.Direction.Length = 1
                return [axisa]
            elif axisa.Direction.Length == 2:
                # ok return the dofrot
                # dofrot[0].Direction.Length = 1
                return dofrot
            else:
                return []
        else:
            # the axis locks permanently the rotation so DOFRot=[]
            return []
    elif (
        currentDOFROTnum == 3
    ):  # no constraints on rotation so the given axis is the one left free
        return [axisa]
    else:
        # this shouldn't happens...ignore it and return the current dofrot
        return dofrot


# then Lock Rotation which locks the remaining rotation axis when enabled
# this basic constraint affects only rotation DOF
def LockRotation(enabled, dofrot, pointconstraints=None, dbg=True):
    if enabled and (len(dofrot) == 1):
        # lock rotation is only read when a dofrot is 1
        return []
    else:
        # nothing to do return the given dofrot
        return dofrot


# then Angle Alignment which takes an axis as arguments and operates according to the remaining dof
# the axis is the normal of the angled plane, that said it acts exactly as axis alignment, maybe I'll remove it
# this basic constraint affects only rotation DOF
def AngleAlignment(axisa, dofrot, pointconstraints=None, dbg=True):
    currentDOFROTnum = len(dofrot)
    if currentDOFROTnum == 0:  # already locked on rotation so ignore it
        return []
    elif (
        currentDOFROTnum == 1
    ):  # partially locked on rotation so compare to the given axis
        if check_ifCollinear(axisa, dofrot[0]):
            # the axis are collinear, so the constraint is redundant, skip it
            if dofrot[0].Direction.Length == 2:
                # ok return the axisa as new dofrot
                # axisa.Direction.Length = 1
                return [axisa]
            else:  # (axisa.Direction.Length == 2):
                # ok return the dofrot
                # dofrot[0].Direction.Length = 1
                return dofrot

        elif check_ifParallel(axisa, dofrot[0]):
            # the stored axis isn't a specific axis so check if parallel
            if dofrot[0].Direction.Length == 2:
                # ok return the axisa as new dofrot
                # axisa.Direction.Length = 1
                return [axisa]
            elif axisa.Direction.Length == 2:
                # ok return the dofrot
                # dofrot[0].Direction.Length = 1
                return dofrot
            else:
                return []
        else:
            # the axis locks permanently the rotation so DOFRot=[]
            return []
    elif (
        currentDOFROTnum == 3
    ):  # no constraints on rotation so the given axis is the one left free
        return [axisa]
    else:
        # this shouldn't happens...ignore it and return the current dofrot
        return dofrot


# Ok not switch on positional constraints

# the first is axis normal on plane to plane distance
# arguments are
# axisa which the axis used in constraint (axial, circular edge, etc...)
# dofpos which is the array of left free positional axes
def AxisDistance(axisa, dofpos, pointconstraints=None, dbg=False):
    currentDOFPOSnum = len(dofpos)
    if currentDOFPOSnum == 0:  # already locked on position so ignore it
        return []
    elif (
        currentDOFPOSnum == 1
    ):  # partially locked on position so compare axis free to the given axis
        if check_ifParallel(axisa, dofpos[0]):
            # the axis are parallel, so the constraint is redundant, skip it DOFPOS=1
            return dofpos
        else:
            # the axis locks permanently the position so DOFPOS=0
            return []
    elif (
        currentDOFPOSnum == 2
    ):  # there are 2 axis which define a plane where the plane can slide on
        # calculate the axis normal to the plane defined by the 2 axes left free
        tempNormAxis = normal_2Axis(dofpos[0], dofpos[1])
        # now compare it to the given axis

        if check_ifPerpendicular(axisa, tempNormAxis):
            # axes are perpendicular so the axis left free is the normal to the plane defined by given axis and tempNormAxis DOFPOS=1
            return [copynorm_AxisToOrigin(normal_2Axis(axisa, tempNormAxis))]
        else:
            # the object is fully constrained DOFPOS=0
            return []

    elif (
        currentDOFPOSnum == 3
    ):  # there are no constraints on position, so the rigid can slides along the given axis, DOFPOS=1
        return [cleanAxis(axisa)]

    else:
        # this shouldn't happens...ignore it and return the current dofrot
        return dofpos


# then plane to plane constraint
# arguments are
# axisa which the axis normal to the plane constrained
# dofpos which is the array of left free positional axes
def PlaneOffset(axisa, dofpos, pointconstraints=[], dbg=False):
    currentDOFPOSnum = len(dofpos)
    if currentDOFPOSnum == 0:  # already locked on position so ignore it
        return []
    elif (
        currentDOFPOSnum == 1
    ):  # partially locked on position so compare to the given axis
        if check_ifParallel(axisa, dofpos[0]):
            # the axis are parallel, so #the axis locks permanently the position so DOFPos=[]
            return []
        else:
            # as the axes are not parallel, the constraint is redundant as it locks a direction already locked, skip it
            return dofpos
    elif (
        currentDOFPOSnum == 2
    ):  # there are 2 axis which define a plane where the plane can slide on
        # calculate the axis normal to the plane defined by the 2 axes left free
        tempNormAxis = normal_2Axis(dofpos[0], dofpos[1])
        # now compare it to the given axis
        if check_ifParallel(axisa, tempNormAxis):
            # the plane is parallel to the plane where it can slide, so the constraint is redundant, return dofpos as is DOFPOS=2
            return dofpos
        else:
            # now calculate the axis normal to the plane create by the given axis and the tempNormAxis
            # and return it as last free DOFPOS=1
            return [copynorm_AxisToOrigin(normal_2Axis(axisa, tempNormAxis))]

    elif (
        currentDOFPOSnum == 3
    ):  # there are no constraints on position, so the left axes free are the two axes which define a plane normal to the given axis DOFPOS=2
        return make_planeNormal(axisa)

    else:
        # this shouldn't happens...ignore it and return the current dofrot
        return dofpos


def PointIdentity(axisa, dofpos, dofrot, pointconstraints, dbg=False):

    pointA = zeroIfLessThanTol(axisa.Base)
    rigidCenterpoint = zeroIfLessThanTol(axisa.Direction)
    if len(pointconstraints) > 0:
        for a in range(0, len(pointconstraints)):
            if check_ifCoincident(pointA, pointconstraints[a]):
                # the same point is already constrained so skip it , redundant
                return dofpos, dofrot
    pointconstraints.append(pointA)
    if check_ifCoincident(pointA, rigidCenterpoint):
        # the center of rigid is coincident to the point constrained, the obj can't move anymore DOFPOS=0
        return [], dofrot
    else:
        currentDOFPOSnum = len(dofpos)

        if currentDOFPOSnum <= 2:  # already locked on position so ignore it
            tmpdofpos = []

        elif currentDOFPOSnum == 3:
            # if there is only 1 pointidentity do nothing, as single point constraint doesn't lock anything just store the point
            if len(pointconstraints) == 1:
                tmpdofpos = dofpos
            else:

                # check again the count of the point constraint
                if len(pointconstraints) >= 2:
                    # there are 3 unique points so the object is fully constrained DOFPOS=0
                    # this is a circularedge constraint with an axis with Base on pointA and Direction pointconstraint[0] to pointconstraints[1]
                    # so DOFPOS=0 as circular edge always locks all 3 axes in position
                    tmpdofpos = []
        else:
            # this shouldn't happens...ignore it and return the current dofrot
            tmpdofpos = dofpos

        currentDOFROTnum = len(dofrot)
        if currentDOFROTnum == 0:  # already locked on rotation so ignore it
            tmpdofrot = []
        elif (
            currentDOFROTnum == 1
        ):  # already partially locked, an additional point identity locks the object
            if dofrot[0].Direction.Length == 2:
                # the stored axis isn't a specific axis.
                # get the point projected to the plane created by current axis
                dofrot[0].Base = pointA
                dofrot[0].Direction.Length = 1
                tmpdofrot = dofrot
            elif check_ifPointOnAxis(
                pointA, dofrot[0]
            ):  # check if the point is on the same direction of the axis left free
                # the point is on the rotation axis left free, it doesn't lock anything
                tmpdofrot = dofrot
            else:
                # the pointidentity locks permanently
                tmpdofrot = []

        elif (
            currentDOFROTnum == 3
        ):  # no constraints on rotation the point identity does nothing on its own
            # here I have to insert the point on pointconstraint, only if the point is not coincident to some point already stored in pointconstraint
            # return back here
            # if there is only 1 pointidentity do nothing, as single point constraint doesn't lock anything just store the point
            if len(pointconstraints) == 1:
                tmpdofrot = dofrot
            elif len(pointconstraints) >= 3:
                # there are 3 unique points so the object is fully constrained DOFROT=0
                tmpdofrot = []
            elif len(pointconstraints) == 2:
                # this is a circularedge constraint with an axis with Base on pointA and Direction pointconstraint[0] to pointconstraints[1]
                # so DOFROT as circular edge always locks all 3 axes in position
                tmpAxis = create_Axis2Points(pointconstraints[0], pointconstraints[1])
                tmpAxis = cleanAxis(tmpAxis)
                tmpdofrot = AxisAlignment(tmpAxis, dofrot)

        else:
            # this shouldn't happens...ignore it and return the current dofrot
            tmpdofrot = dofrot

    return tmpdofpos, tmpdofrot


# in the end there are the toolbar constraints, those are simply a combination of the ones above

# PointIdentity, PointOnLine, PointOnPlane, Spherical Constraints:
#    PointIdentityPos()    needs to know the point constrained as vector, the dofpos array, the rigid center point as vector and
#                        the pointconstraints which stores all point constraints of the rigid
#    PointIdentityRot()    needs to know the point constrained as vector, the dofrot array, and
#                        the pointconstraints which stores all point constraints of the rigid
# These constraint have to be the last evaluated in the chain of constraints.

# CircularEdgeConstraint:
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


# PlanesParallelConstraint:
#    AxisAlignment()    needs to know the axis normal to the plane constrained (stored in dep as refpoint and refAxisEnd) and the dofrot array

# PlaneCoincident:
#    AxisAlignment()    needs to know the axis normal to the plane constrained (stored in dep as refpoint and refAxisEnd) and the dofrot array
#    PlaneOffset()      needs to know the axis normal to the plane constrained (stored in dep as refpoint and refAxisEnd) and the dofpos array

# AxialConstraint:
#    AxisAlignment()    needs to know the axis normal to circle (stored in dep as refpoint and refAxisEnd) and the dofrot array
#    AxisDistance()     needs to know the axis normal to circle (stored in dep as refpoint and refAxisEnd) and the dofpos array
#    LockRotation()     need to know if LockRotation is True or False and the array dofrot

# AngleBetweenPlanesConstraint
#    AngleAlignment()   needs to know the axis normal to plane constrained (stored in dep as refpoint and refAxisEnd) and the dofrot array

# some test for helper functions
if __name__ == "__main__":
    """
    AXIS1=FreeCAD.Axis()

    AXIS1.Base = FreeCAD.Vector(2,10,12)
    AXIS1.Direction = AXIS1.Direction.add(SystemXAxis.Direction)
    AXIS2=FreeCAD.Axis()
    AXIS2.Base = FreeCAD.Vector(2,10,12)
    AXIS2.Direction = AXIS2.Direction.add(SystemXAxis.Direction)
    AXIS3=FreeCAD.Axis()
    AXIS3.Base = SystemOrigin
    AXIS3.Direction = AXIS3.Direction.add(SystemZAxis.Direction)

    #print "Axis Normal to plane defined by 2 axes = " , normal_2Axis(AXIS1,AXIS2))
    print AXIS1
    print "Axes defining a plane normal to given axis = " , make_planeNormal(AXIS1)
    print "test recursive get normal to a plane created by 2axes defined by 1 axis normal= " , normal_2Axis(make_planeNormal(AXIS1)[0], make_planeNormal(AXIS1)[1])
    print "Axes Parallel? = " , check_ifParallel(AXIS1,AXIS2)
    print "Axes Perpendicular? = " , check_ifPerpendicular(AXIS1,AXIS2)
    print "Axes Collinear? = " , check_ifCollinear(AXIS1,AXIS2)
    print "Vertexes are Coincident ? = " ,  check_ifCoincident(AXIS1.Base, AXIS2.Base)
    dfdfdf = create_Axis(FreeCAD.Vector(12.0,33.5,12.7), FreeCAD.Vector(23.5,22.0,99.0))
    print copynorm_AxisToOrigin(dfdfdf)
    print create_Axis2Points(FreeCAD.Vector(1.0,1.0,1.0), FreeCAD.Vector(3,3,3))
    """
