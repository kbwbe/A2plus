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

import FreeCAD
import Part
from a2p_translateUtils import *
import a2plib
from a2plib import (
    path_a2p,
    findUnusedObjectName,
    vertexSelected,
    LinearEdgeSelected,
    planeSelected,
    sphericalSurfaceSelected,
    cylindricalFaceSelected,
    CircularEdgeSelected,
    ClosedEdgeSelected,
    getPos,
    getAxis,
    getObjectEdgeFromName,
    getObjectFaceFromName,
)
import math
from a2p_viewProviderProxies import ConstraintObjectProxy, ConstraintViewProviderProxy

# ==============================================================================
class BasicConstraint:
    """
    Base class of all Constraints, only use inherited classes...
    """

    def __init__(self, selection):
        self.typeInfo = None  # give the appropriate type string for A2plus solver
        self.constraintBaseName = None  # <== give a base name here
        self.iconPath = None
        #
        # Fields for storing data of the two constrainted objects
        self.ob1Name = None
        self.ob2Name = None
        self.ob1Label = None
        self.ob2Label = None
        self.ob1 = None  # the two constrainted FC objects
        self.ob2 = None
        self.sub1 = None  # the two constrainted FC subelements
        self.sub2 = None
        #
        self.constraintObject = None
        #
        self.direction = None
        self.offset = None
        self.angle = None
        self.lockRotation = None

    def create(self, selection):
        cName = findUnusedObjectName(self.constraintBaseName)
        ob = FreeCAD.activeDocument().addObject("App::FeaturePython", cName)
        s1, s2 = selection

        self.ob1Name = s1.ObjectName
        self.ob2Name = s2.ObjectName
        self.ob1Label = s1.Object.Label
        self.ob2Label = s2.Object.Label

        self.ob1 = FreeCAD.activeDocument().getObject(s1.ObjectName)
        self.ob2 = FreeCAD.activeDocument().getObject(s2.ObjectName)

        self.sub1 = s1.SubElementNames[0]
        self.sub2 = s2.SubElementNames[0]

        ob.addProperty(
            "App::PropertyString", "Type", "ConstraintInfo"
        ).Type = self.typeInfo
        ob.addProperty(
            "App::PropertyString", "Object1", "ConstraintInfo"
        ).Object1 = self.ob1Name
        ob.addProperty(
            "App::PropertyString", "SubElement1", "ConstraintInfo"
        ).SubElement1 = self.sub1
        ob.addProperty(
            "App::PropertyString", "Object2", "ConstraintInfo"
        ).Object2 = self.ob2Name
        ob.addProperty(
            "App::PropertyString", "SubElement2", "ConstraintInfo"
        ).SubElement2 = self.sub2
        ob.addProperty(
            "App::PropertyString", "Toponame1", "ConstraintInfo"
        ).Toponame1 = ""
        ob.addProperty(
            "App::PropertyString", "Toponame2", "ConstraintInfo"
        ).Toponame2 = ""
        ob.addProperty(
            "App::PropertyBool", "Suppressed", "ConstraintInfo"
        ).Suppressed = False

        for prop in ["Object1", "Object2", "SubElement1", "SubElement2", "Type"]:
            ob.setEditorMode(prop, 1)

        self.constraintObject = ob

        self.calcInitialValues()  # override in subclass !
        self.setInitialValues()
        self.groupUnderParentTreeObject()
        self.setupProxies()

    def setupProxies(self):
        c = self.constraintObject
        c.Proxy = ConstraintObjectProxy()
        c.ViewObject.Proxy = ConstraintViewProviderProxy(
            c, self.iconPath, True, self.ob2Label, self.ob1Label
        )

    def groupUnderParentTreeObject(self):
        c = self.constraintObject
        parent = FreeCAD.ActiveDocument.getObject(c.Object1)
        c.addProperty(
            "App::PropertyLink", "ParentTreeObject", "ConstraintInfo"
        ).ParentTreeObject = parent
        c.setEditorMode("ParentTreeObject", 1)
        # this is needed to trigger an update
        parent.touch()

    def setInitialValues(self):
        c = self.constraintObject
        if self.direction != None:
            c.addProperty(
                "App::PropertyEnumeration", "directionConstraint", "ConstraintInfo"
            )
            c.directionConstraint = ["aligned", "opposed"]
            c.directionConstraint = self.direction
            c.setEditorMode("directionConstraint", 0)  # set not editable...
        if self.offset != None:
            c.addProperty(
                "App::PropertyDistance", "offset", "ConstraintInfo"
            ).offset = self.offset
            c.setEditorMode("offset", 0)  # set not editable...
        if self.angle != None:
            c.addProperty(
                "App::PropertyAngle", "angle", "ConstraintInfo"
            ).angle = self.angle
            c.setEditorMode("angle", 0)  # set not editable...
        if self.lockRotation != None:
            c.addProperty(
                "App::PropertyBool", "lockRotation", "ConstraintInfo"
            ).lockRotation = self.lockRotation
            c.setEditorMode("lockRotation", 0)  # set not editable...

    def calcInitialValues(self):
        raise NotImplementedError(
            "Class {} doesn't implement calcInitialValues(), use inherited classes instead!".format(
                self.__class__.__name__
            )
        )

    @staticmethod
    def recalculateMatingDirection(c):
        raise NotImplementedError(
            "Class {} doesn't implement recalculateMatingDirection(), use inherited classes instead!".format(
                c.__class__.__name__
            )
        )

    @staticmethod
    def getToolTip(self):
        return "Invalid Base Class BasicConstraint"

    @staticmethod
    def isValidSelection(selection):
        return True


# ==============================================================================
class PointIdentityConstraint(BasicConstraint):
    def __init__(self, selection):
        BasicConstraint.__init__(self, selection)
        self.typeInfo = "pointIdentity"
        self.constraintBaseName = "pointIdentity"
        self.iconPath = ":/icons/a2p_PointIdentity.svg"
        self.create(selection)

    def calcInitialValues(self):
        pass

    @staticmethod
    def recalculateMatingDirection(c):
        pass

    @staticmethod
    def getToolTip():
        return """
Create the point-to-point constraint (pointIdentity)

Select:
1) A vertex, a circle, or a sphere (on a part)
2) A vertex, a circle, or a sphere (on another part)

Button gets active after correct selection.
"""

    @staticmethod
    def isValidSelection(selection):
        validSelection = False
        if len(selection) == 2:
            s1, s2 = selection
            if s1.ObjectName != s2.ObjectName:
                if (
                    vertexSelected(s1)
                    or sphericalSurfaceSelected(s1)
                    or CircularEdgeSelected(s1)
                ) and (
                    vertexSelected(s2)
                    or sphericalSurfaceSelected(s2)
                    or CircularEdgeSelected(s2)
                ):
                    validSelection = True
        return validSelection


# ==============================================================================
class PointOnLineConstraint(BasicConstraint):
    def __init__(self, selection):
        BasicConstraint.__init__(self, selection)
        self.typeInfo = "pointOnLine"
        self.constraintBaseName = "pointOnLine"
        self.iconPath = ":/icons/a2p_PointOnLineConstraint.svg"
        self.create(selection)

    def calcInitialValues(self):
        pass

    @staticmethod
    def recalculateMatingDirection(c):
        pass

    @staticmethod
    def getToolTip():
        return """
Create the point-on-line constraint (pointOnLine)

Select:
1) A vertex, a sphere, or a circle (on a part)
2) A linear/circular edge, or a cylindrical face (on another part)

If the circular edge is selected, 
it's axis will be taken as line definition.

Button gets active after correct selection.
"""

    @staticmethod
    def isValidSelection(selection):
        validSelection = False
        if len(selection) == 2:
            s1, s2 = selection
            if s1.ObjectName != s2.ObjectName:
                if (
                    vertexSelected(s1)
                    or sphericalSurfaceSelected(s1)
                    or CircularEdgeSelected(s1)
                ) and (
                    LinearEdgeSelected(s2)
                    or cylindricalFaceSelected(s2)
                    or CircularEdgeSelected(s2)
                ):
                    validSelection = True
        return validSelection


# ==============================================================================
class PointOnPlaneConstraint(BasicConstraint):
    def __init__(self, selection):
        BasicConstraint.__init__(self, selection)
        self.typeInfo = "pointOnPlane"
        self.constraintBaseName = "pointOnPlane"
        self.iconPath = ":/icons/a2p_PointOnPlaneConstraint.svg"
        self.create(selection)

    def calcInitialValues(self):
        self.offset = 0.0

    @staticmethod
    def recalculateMatingDirection(c):
        point = getPos(c.Object1, c.SubElement1)
        plane = getObjectFaceFromName(c.Object2, c.SubElement2)
        planeNormal = a2plib.getPlaneNormal(plane.Surface)
        planePos = getPos(c.Object2, c.SubElement2)

        # calculate recent offset...
        delta = point.sub(planePos)
        offset = delta.dot(planeNormal)
        if offset >= 0:
            c.offset = abs(c.offset)
        else:
            c.offset = -abs(c.offset)

    @staticmethod
    def getToolTip():
        return """
Create the point-on-plane constraint (pointOnPlane)

Select:
1) A vertex, a center of a circle, or a sphere (on a part)
2) A plane (on another part)

Button gets active after correct selection.
"""

    @staticmethod
    def isValidSelection(selection):
        validSelection = False
        if len(selection) == 2:
            s1, s2 = selection
            if s1.ObjectName != s2.ObjectName:
                if (
                    vertexSelected(s1)
                    or CircularEdgeSelected(s1)
                    or sphericalSurfaceSelected(s1)
                ) and planeSelected(s2):
                    validSelection = True
        return validSelection


# ==============================================================================
class CircularEdgeConstraint(BasicConstraint):
    def __init__(self, selection):
        BasicConstraint.__init__(self, selection)
        self.typeInfo = "circularEdge"
        self.constraintBaseName = "circularEdge"
        self.iconPath = ":/icons/a2p_CircularEdgeConstraint.svg"
        self.create(selection)

    def calcInitialValues(self):
        c = self.constraintObject
        # circleEdge1 = getObjectEdgeFromName(self.ob1, c.SubElement1)
        # circleEdge2 = getObjectEdgeFromName(self.ob2, c.SubElement2)
        # axis1 = circleEdge1.Curve.Axis
        # axis2 = circleEdge2.Curve.Axis
        axis1 = getAxis(self.ob1, c.SubElement1)
        axis2 = getAxis(self.ob2, c.SubElement2)

        angle = math.degrees(axis1.getAngle(axis2))
        if angle <= 90.0:
            self.direction = "aligned"
        else:
            self.direction = "opposed"
        self.offset = 0.0
        self.lockRotation = False

    @staticmethod
    def recalculateMatingDirection(c):
        ob1 = c.Document.getObject(c.Object1)
        ob2 = c.Document.getObject(c.Object2)
        # circleEdge1 = getObjectEdgeFromName(ob1, c.SubElement1)
        # circleEdge2 = getObjectEdgeFromName(ob2, c.SubElement2)
        # axis1 = circleEdge1.Curve.Axis
        # axis2 = circleEdge2.Curve.Axis

        axis1 = getAxis(ob1, c.SubElement1)
        axis2 = getAxis(ob2, c.SubElement2)

        angle = math.degrees(axis1.getAngle(axis2))
        if angle <= 90.0:
            direction = "aligned"
        else:
            direction = "opposed"
        if c.directionConstraint != direction:
            c.offset = -c.offset
        c.directionConstraint = direction

    @staticmethod
    def getToolTip():
        return """
Create the circular-edge constraint (circularEdge)

Select:
1) A circular edge (on a part)
2) A circular edge (on another part)

Button gets active after correct selection.
"""

    @staticmethod
    def isValidSelection(selection):
        validSelection = False
        if len(selection) == 2:
            s1, s2 = selection
            if s1.ObjectName != s2.ObjectName:
                if CircularEdgeSelected(s1) and CircularEdgeSelected(s2):
                    validSelection = True
        return validSelection


# ==============================================================================
class AxialConstraint(BasicConstraint):
    def __init__(self, selection):
        BasicConstraint.__init__(self, selection)
        self.typeInfo = "axial"
        self.constraintBaseName = "axisCoincident"
        self.iconPath = ":/icons/a2p_AxialConstraint.svg"
        self.create(selection)

    def calcInitialValues(self):
        c = self.constraintObject
        axis1 = getAxis(self.ob1, c.SubElement1)
        axis2 = getAxis(self.ob2, c.SubElement2)
        angle = math.degrees(axis1.getAngle(axis2))
        if angle <= 90.0:
            self.direction = "aligned"
        else:
            self.direction = "opposed"
        self.lockRotation = False

    @staticmethod
    def recalculateMatingDirection(c):
        ob1 = c.Document.getObject(c.Object1)
        ob2 = c.Document.getObject(c.Object2)
        axis1 = getAxis(ob1, c.SubElement1)
        axis2 = getAxis(ob2, c.SubElement2)
        angle = math.degrees(axis1.getAngle(axis2))
        if angle <= 90.0:
            c.directionConstraint = "aligned"
        else:
            c.directionConstraint = "opposed"

    @staticmethod
    def getToolTip():
        return """
Create the axis-to-axis constraint (axisCoincident)

2 axis are aligned and will be moved to be coincident.

Select:
1) A cylindrical face or linear edge (on a part)
2) A cylindrical face or linear edge (on another part)

Button gets active after correct selection.
"""

    @staticmethod
    def isValidSelection(selection):
        def ValidSelection(selectionExObj):
            return (
                cylindricalFaceSelected(selectionExObj)
                or LinearEdgeSelected(selectionExObj)
                or CircularEdgeSelected(selectionExObj)
            )

        validSelection = False
        if len(selection) == 2:
            s1, s2 = selection
            if s1.ObjectName != s2.ObjectName:
                if ValidSelection(s1) and ValidSelection(s2):
                    validSelection = True
        return validSelection


# ==============================================================================
class AxisParallelConstraint(BasicConstraint):
    def __init__(self, selection):
        BasicConstraint.__init__(self, selection)
        self.typeInfo = "axisParallel"
        self.constraintBaseName = "axisParallel"
        self.iconPath = ":/icons/a2p_AxisParallelConstraint.svg"
        self.create(selection)

    def calcInitialValues(self):
        c = self.constraintObject
        axis1 = getAxis(self.ob1, c.SubElement1)
        axis2 = getAxis(self.ob2, c.SubElement2)
        angle = math.degrees(axis1.getAngle(axis2))
        if angle <= 90.0:
            self.direction = "aligned"
        else:
            self.direction = "opposed"

    @staticmethod
    def recalculateMatingDirection(c):
        ob1 = c.Document.getObject(c.Object1)
        ob2 = c.Document.getObject(c.Object2)
        axis1 = getAxis(ob1, c.SubElement1)
        axis2 = getAxis(ob2, c.SubElement2)
        angle = math.degrees(axis1.getAngle(axis2))
        if angle <= 90.0:
            c.directionConstraint = "aligned"
        else:
            c.directionConstraint = "opposed"

    @staticmethod
    def getToolTip():
        return """
Create the parallel-axis constraint (axisParallel)

Axis' will only rotate to be parallel, but will not 
be moved to be coincident.

Select:
1) A linear/circular edge, or cylindrical face (on a part)
2) A linear/circular edge, or cylindrical face (on another part)

If using circular edge, it's axis will be taken as line.

Button gets active after correct selection.
"""

    @staticmethod
    def isValidSelection(selection):
        validSelection = False
        if len(selection) == 2:
            s1, s2 = selection
            if s1.ObjectName != s2.ObjectName:
                if (
                    LinearEdgeSelected(s1)
                    or cylindricalFaceSelected(s1)
                    or CircularEdgeSelected(s1)
                ) and (
                    LinearEdgeSelected(s2)
                    or cylindricalFaceSelected(s2)
                    or CircularEdgeSelected(s2)
                ):
                    validSelection = True
        return validSelection


# ==============================================================================
class AxisPlaneParallelConstraint(BasicConstraint):
    def __init__(self, selection):
        BasicConstraint.__init__(self, selection)
        self.typeInfo = "axisPlaneParallel"
        self.constraintBaseName = "axisPlaneParallel"
        self.iconPath = ":/icons/a2p_AxisPlaneParallelConstraint.svg"
        self.create(selection)

    def calcInitialValues(self):
        pass

    @staticmethod
    def recalculateMatingDirection(c):
        pass

    @staticmethod
    def getToolTip():
        return """
Create the axis-to-plane parallelism constraint (axisPlaneParallel)

Select:
1) A linear edge, or cylinder axis (on a part)
2) A plane face (on another part)

This constraint adjusts an axis parallel to a 
selected plane. The parts are not moved to be coincident.

Button gets active after correct selection.
"""

    @staticmethod
    def isValidSelection(selection):
        validSelection = False
        if len(selection) == 2:
            s1, s2 = selection
            if s1.ObjectName != s2.ObjectName:
                if (
                    LinearEdgeSelected(s1) or cylindricalFaceSelected(s1)
                ) and planeSelected(s2):
                    validSelection = True
        return validSelection


# ==============================================================================
class AxisPlaneAngleConstraint(BasicConstraint):
    def __init__(self, selection):
        BasicConstraint.__init__(self, selection)
        self.typeInfo = "axisPlaneAngle"
        self.constraintBaseName = "axisPlaneAngle"
        self.iconPath = ":/icons/a2p_AxisPlaneAngleConstraint.svg"
        self.create(selection)

    def calcInitialValues(self):
        c = self.constraintObject
        axis1 = getAxis(self.ob1, c.SubElement1)
        plane2 = getObjectFaceFromName(self.ob2, c.SubElement2)
        axis2 = a2plib.getPlaneNormal(plane2.Surface)
        angle = math.degrees(axis1.getAngle(axis2))
        # the following section has been tested and is working,
        # just it does not meet expectations.
        # opposed/aligned are set to the opposite of expectation
        # this has to be checked again.
        if angle <= 90.0:
            self.direction = "opposed"
            self.angle = 90 - angle
        else:
            self.direction = "aligned"
            self.angle = -90 + angle

    @staticmethod
    def recalculateMatingDirection(c):
        ob1 = c.Document.getObject(c.Object1)
        ob2 = c.Document.getObject(c.Object2)
        axis1 = getAxis(ob1, c.SubElement1)
        plane2 = getObjectFaceFromName(ob2, c.SubElement2)
        axis2 = a2plib.getPlaneNormal(plane2.Surface)
        angle = math.degrees(axis1.getAngle(axis2))
        if angle <= 90.0:
            direction = "opposed"
        else:
            direction = "aligned"
        c.directionConstraint = direction

    @staticmethod
    def getToolTip():
        return """
Create the angular axis-to-plane constraint (axisPlaneAngle)

Select:
1) A linear edge, or cylinder axis (on a part)
2) A plane face (on another part)

At first this constraint adjusts an axis parallel to a 
selected plane. Within the following popUp dialog you 
can define an angle.

The parts are not moved to be coincident.

Button gets active after correct selection.
"""

    @staticmethod
    def isValidSelection(selection):
        validSelection = False
        if len(selection) == 2:
            s1, s2 = selection
            if s1.ObjectName != s2.ObjectName:
                if (
                    LinearEdgeSelected(s1) or cylindricalFaceSelected(s1)
                ) and planeSelected(s2):
                    validSelection = True
        return validSelection


# ==============================================================================
class AxisPlaneNormalConstraint(BasicConstraint):
    def __init__(self, selection):
        BasicConstraint.__init__(self, selection)
        self.typeInfo = "axisPlaneNormal"
        self.constraintBaseName = "axisPlaneNormal"
        self.iconPath = ":/icons/a2p_AxisPlaneNormalConstraint.svg"
        self.create(selection)

    def calcInitialValues(self):
        c = self.constraintObject
        axis1 = getAxis(self.ob1, c.SubElement1)
        plane2 = getObjectFaceFromName(self.ob2, c.SubElement2)
        axis2 = a2plib.getPlaneNormal(plane2.Surface)

        angle = math.degrees(axis1.getAngle(axis2))
        if angle <= 90.0:
            self.direction = "aligned"
        else:
            self.direction = "opposed"

    @staticmethod
    def recalculateMatingDirection(c):
        ob1 = c.Document.getObject(c.Object1)
        ob2 = c.Document.getObject(c.Object2)
        axis1 = getAxis(ob1, c.SubElement1)
        plane2 = getObjectFaceFromName(ob2, c.SubElement2)
        axis2 = a2plib.getPlaneNormal(plane2.Surface)

        angle = math.degrees(axis1.getAngle(axis2))
        if angle <= 90.0:
            c.directionConstraint = "aligned"
        else:
            c.directionConstraint = "opposed"

    @staticmethod
    def getToolTip():
        return """
Create the axis-plane-normal constraint (axisPlaneNormal)

Select:
1) A linear edge, or cylinder axis (on a part)
2) A plane face (on another part)

This constraint adjusts an axis vertical to a 
selected plane. The parts are not moved to be 
coincident.

Button gets active after correct selection.
"""

    @staticmethod
    def isValidSelection(selection):
        validSelection = False
        if len(selection) == 2:
            s1, s2 = selection
            if s1.ObjectName != s2.ObjectName:
                if (
                    LinearEdgeSelected(s1) or cylindricalFaceSelected(s1)
                ) and planeSelected(s2):
                    validSelection = True
        return validSelection


# ==============================================================================
class PlanesParallelConstraint(BasicConstraint):
    def __init__(self, selection):
        BasicConstraint.__init__(self, selection)
        self.typeInfo = "planesParallel"
        self.constraintBaseName = "planesParallel"
        self.iconPath = ":/icons/a2p_PlanesParallelConstraint.svg"
        self.create(selection)

    def calcInitialValues(self):
        c = self.constraintObject
        plane1 = getObjectFaceFromName(self.ob1, c.SubElement1)
        plane2 = getObjectFaceFromName(self.ob2, c.SubElement2)

        normal1 = a2plib.getPlaneNormal(plane1.Surface)
        normal2 = a2plib.getPlaneNormal(plane2.Surface)

        angle = math.degrees(normal1.getAngle(normal2))
        if angle <= 90.0:
            self.direction = "aligned"
        else:
            self.direction = "opposed"

    @staticmethod
    def recalculateMatingDirection(c):
        ob1 = c.Document.getObject(c.Object1)
        ob2 = c.Document.getObject(c.Object2)
        plane1 = getObjectFaceFromName(ob1, c.SubElement1)
        plane2 = getObjectFaceFromName(ob2, c.SubElement2)

        normal1 = a2plib.getPlaneNormal(plane1.Surface)
        normal2 = a2plib.getPlaneNormal(plane2.Surface)

        angle = math.degrees(normal1.getAngle(normal2))
        if angle <= 90.0:
            c.directionConstraint = "aligned"
        else:
            c.directionConstraint = "opposed"

    @staticmethod
    def getToolTip():
        return """
Create the planes-parallelism constraint (planesParallel)

Planes will only rotate to be parallel, but not
moved to be coincident.

Select:
1) A plane (on a part)
2) A plane (on another part)

Button gets active after correct selection.
"""

    @staticmethod
    def isValidSelection(selection):
        validSelection = False
        if len(selection) == 2:
            s1, s2 = selection
            if s1.ObjectName != s2.ObjectName:
                # if not planeSelected(s1): #????
                #    s2, s1 = s1, s2 #?????
                if planeSelected(s1) and planeSelected(s2):
                    validSelection = True
        return validSelection


# ==============================================================================
class PlaneConstraint(BasicConstraint):
    def __init__(self, selection):
        BasicConstraint.__init__(self, selection)
        self.typeInfo = "plane"
        self.constraintBaseName = "planeCoincident"
        self.iconPath = ":/icons/a2p_PlaneCoincidentConstraint.svg"
        self.create(selection)

    def calcInitialValues(self):
        c = self.constraintObject
        plane1 = getObjectFaceFromName(self.ob1, c.SubElement1)
        plane2 = getObjectFaceFromName(self.ob2, c.SubElement2)

        normal1 = a2plib.getPlaneNormal(plane1.Surface)
        normal2 = a2plib.getPlaneNormal(plane2.Surface)

        angle = math.degrees(normal1.getAngle(normal2))
        if angle <= 90.0:
            self.direction = "aligned"
        else:
            self.direction = "opposed"
        self.offset = 0.0

    @staticmethod
    def recalculateMatingDirection(c):
        ob1 = c.Document.getObject(c.Object1)
        ob2 = c.Document.getObject(c.Object2)
        plane1 = getObjectFaceFromName(ob1, c.SubElement1)
        plane2 = getObjectFaceFromName(ob2, c.SubElement2)

        normal1 = a2plib.getPlaneNormal(plane1.Surface)
        normal2 = a2plib.getPlaneNormal(plane2.Surface)

        angle = math.degrees(normal1.getAngle(normal2))
        if angle <= 90.0:
            direction = "aligned"
        else:
            direction = "opposed"
        # if c.directionConstraint != direction:
        #    c.offset = -c.offset
        c.directionConstraint = direction

    @staticmethod
    def getToolTip():
        return """
Create the coincident-plane constraint (planeCoincident)

Select:
1) A plane (on a part)
2) A plane (on another part)

Button gets active after correct selection.
"""

    @staticmethod
    def isValidSelection(selection):
        validSelection = False
        if len(selection) == 2:
            s1, s2 = selection
            if s1.ObjectName != s2.ObjectName:
                # if not planeSelected(s1):
                #    s2, s1 = s1, s2
                if planeSelected(s1) and planeSelected(s2):
                    validSelection = True
        return validSelection


# ==============================================================================
class AngledPlanesConstraint(BasicConstraint):
    def __init__(self, selection):
        BasicConstraint.__init__(self, selection)
        self.typeInfo = "angledPlanes"
        self.constraintBaseName = "angledPlanes"
        self.iconPath = ":/icons/a2p_AngleConstraint.svg"
        self.create(selection)

    def calcInitialValues(self):
        plane1 = getObjectFaceFromName(self.ob1, self.sub1)
        plane2 = getObjectFaceFromName(self.ob2, self.sub2)
        normal1 = a2plib.getPlaneNormal(plane1.Surface)
        normal2 = a2plib.getPlaneNormal(plane2.Surface)
        self.angle = math.degrees(normal2.getAngle(normal1))

    @staticmethod
    def recalculateMatingDirection(c):
        pass

    @staticmethod
    def getToolTip():
        return """
Create the angled-planes constraint (angledPlanes)

Select:
1) A plane (on a part)
2) A plane (on another part)

After setting this constraint at first the actual 
angle between both planes is been calculated and 
stored to entry "angle" in object editor.

The angle can be changed in the object editor

Avoid using angles equals to 0 and 180 degrees.
You could get strange results.
For that, is better to use planesParallel constraint.

Button gets active after correct selection.
"""

    @staticmethod
    def isValidSelection(selection):
        validSelection = False
        if len(selection) == 2:
            s1, s2 = selection
            if s1.ObjectName != s2.ObjectName:
                if planeSelected(s1) and planeSelected(s2):
                    validSelection = True
        return validSelection


# ==============================================================================
class SphericalConstraint(BasicConstraint):
    def __init__(self, selection):
        BasicConstraint.__init__(self, selection)
        self.typeInfo = "sphereCenterIdent"
        self.constraintBaseName = "sphereCenterIdent"
        self.iconPath = ":/icons/a2p_SphericalSurfaceConstraint.svg"
        self.create(selection)

    def calcInitialValues(self):
        pass

    @staticmethod
    def recalculateMatingDirection(c):
        pass

    @staticmethod
    def getToolTip():
        return """
Create the sphere-to-sphere constraint (sphereCenterIdent)

Select:
1) A spherical surface, or a vertex (on a part)
2) A spherical surface, or a vertex (on another part)

When selecting a circle, it's center is used as a vertex.

Button gets active after correct selection.
"""

    @staticmethod
    def isValidSelection(selection):
        validSelection = False
        if len(selection) == 2:
            s1, s2 = selection
            if s1.ObjectName != s2.ObjectName:
                if (
                    vertexSelected(s1)
                    or sphericalSurfaceSelected(s1)
                    or CircularEdgeSelected(s1)
                ) and (
                    vertexSelected(s2)
                    or sphericalSurfaceSelected(s2)
                    or CircularEdgeSelected(s2)
                ):
                    validSelection = True
        return validSelection


# ==============================================================================


class CenterOfMassConstraint(BasicConstraint):
    def __init__(self, selection):
        BasicConstraint.__init__(self, selection)
        self.typeInfo = "CenterOfMass"
        self.constraintBaseName = "centerOfMass"
        self.iconPath = path_a2p + "/icons/a2p_CenterOfMassConstraint.svg"
        self.create(selection)

    def calcInitialValues(self):
        if self.sub1.startswith("Face"):
            plane1 = getObjectFaceFromName(self.ob1, self.sub1)
        elif self.sub1.startswith("Edge"):
            # print(self.sub1)
            plane1 = Part.Face(Part.Wire(getObjectEdgeFromName(self.ob1, self.sub1)))
        if self.sub2.startswith("Face"):
            plane2 = getObjectFaceFromName(self.ob2, self.sub2)
        elif self.sub2.startswith("Edge"):
            plane2 = Part.Face(Part.Wire(getObjectEdgeFromName(self.ob2, self.sub2)))
        # plane2 = getObjectFaceFromName(self.ob2, self.sub2)
        axis1 = a2plib.getPlaneNormal(plane1.Surface)
        axis2 = a2plib.getPlaneNormal(plane2.Surface)
        angle = math.degrees(axis1.getAngle(axis2))
        if angle <= 90.0:
            self.direction = "aligned"
        else:
            self.direction = "opposed"
        self.offset = 0.0
        self.lockRotation = False

    @staticmethod
    def recalculateMatingDirection(c):
        ob1 = c.Document.getObject(c.Object1)
        ob2 = c.Document.getObject(c.Object2)
        if c.SubElement1.startswith("Face"):
            plane1 = getObjectFaceFromName(ob1, c.SubElement1)
        elif c.SubElement1.startswith("Edge"):
            # print(self.sub1)
            plane1 = Part.Face(Part.Wire(getObjectEdgeFromName(ob1, c.SubElement1)))
        if c.SubElement2.startswith("Face"):
            plane2 = getObjectFaceFromName(ob2, c.SubElement2)
        elif c.SubElement2.startswith("Edge"):
            plane2 = Part.Face(Part.Wire(getObjectEdgeFromName(ob2, c.SubElement2)))
        axis1 = a2plib.getPlaneNormal(plane1.Surface)
        axis2 = a2plib.getPlaneNormal(plane2.Surface)
        angle = math.degrees(axis1.getAngle(axis2))
        if angle <= 90.0:
            c.directionConstraint = "aligned"
        else:
            c.directionConstraint = "opposed"

    @staticmethod
    def getToolTip():
        return """
Create the center-of-mass constraint (centerOfMass)

Select:
1) A face, or a closed edge (on a part)
2) A face, or a closed edge (on another part)

It is possible to change the offset in object editor.

Button gets active after correct selection.
"""

    @staticmethod
    def isValidSelection(selection):
        validSelection = False
        if len(selection) == 2:
            s1, s2 = selection
            if s1.ObjectName != s2.ObjectName:
                if (planeSelected(s1) or ClosedEdgeSelected(s1)) and (
                    planeSelected(s2) or ClosedEdgeSelected(s2)
                ):
                    validSelection = True
        return validSelection


# ==============================================================================
