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
from PySide import QtGui
import math
from a2p_viewProviderProxies import *

#==============================================================================
class BasicConstraint():
    '''
    Base class of all Constraints, only use inherited classes...
    '''
    def __init__(self,selection):
        self.typeInfo = None # give the appropiate type string for A2plus solver
        self.constraintBaseName = None # <== give a base name here
        self.iconPath = None
        #
        # Fields for storing data of the two constrainted objects
        self.ob1Name = None
        self.ob2Name = None
        self.ob1Label = None
        self.ob2Label = None
        self.ob1 = None # the two constrainted FC objects
        self.ob2 = None
        self.sub1 = None # the two constrainted FC subelements
        self.sub2 = None
        #
        self.constraintObject = None
        #
        self.direction = None
        self.offset = None
        self.angle = None
        self.lockRotation = None
        
        
    def create(self,selection):
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

        ob.addProperty("App::PropertyString","Type","ConstraintInfo").Type = self.typeInfo
        ob.addProperty("App::PropertyString","Object1","ConstraintInfo").Object1 = self.ob1Name
        ob.addProperty("App::PropertyString","SubElement1","ConstraintInfo").SubElement1 = self.sub1
        ob.addProperty("App::PropertyString","Object2","ConstraintInfo").Object2 = self.ob2Name
        ob.addProperty("App::PropertyString","SubElement2","ConstraintInfo").SubElement2 = self.sub2
        
        for prop in ["Object1","Object2","SubElement1","SubElement2","Type"]:
            ob.setEditorMode(prop, 1)

        self.constraintObject = ob
        
        self.calcInitialValues() #override in subclass !
        self.setInitialValues()
        self.groupUnderParentObjectInTree()
        self.setupProxies()
        
    def setupProxies(self):
        c = self.constraintObject
        c.Proxy = ConstraintObjectProxy()
        c.ViewObject.Proxy = ConstraintViewProviderProxy(
            c,
            self.iconPath,
            True,
            self.ob1Label,
            self.ob2Label
            )
    
    def groupUnderParentTreeObject(self):
        c = self.constraintObject
        parent = FreeCAD.ActiveDocument.getObject(c.Object1)
        c.addProperty("App::PropertyLink","ParentTreeObject","ConstraintInfo").ParentTreeObject = parent
        c.setEditorMode('ParentTreeObject',1)
        parent.Label = parent.Label # this is needed to trigger an update
    
    def setInitialValues(self):
        c = self.constraintObject
        if self.direction != None:
            c.addProperty("App::PropertyEnumeration","directionConstraint", "ConstraintInfo")
            c.directionConstraint = ["aligned","opposed"]
            c.directionConstraint = self.direction
        if self.offset != None:
            c.addProperty('App::PropertyDistance','offset',"ConstraintInfo").offset = self.offset
        if self.angle != None:
            c.addProperty("App::PropertyAngle","angle","ConstraintInfo").angle = self.angle
        if self.lockRotation != None:
            c.addProperty("App::PropertyBool","lockRotation","ConstraintInfo").lockRotation = self.lockRotation
            
    
    def calcInitialValues(self):
        raise NotImplementedError(
            "Class {} doesn't implement calcInitialValues(), use inherited classes instead!".format(
                self.__class__.__name__
                )
            )
        
    @staticmethod
    def getToolTip(self):
        return 'Invalid Base Class BasicConstraint'
        
#==============================================================================
class PointIdentityConstraint(BasicConstraint):
    def __init__(self,selection):
        BasicConstraint.__init__(self, selection)
        self.typeInfo = 'pointIdentity'
        self.constraintBaseName = 'pointIdentity'
        self.iconPath = ':/icons/a2p_PointOnLineConstraint.svg'
        self.create(selection)
        
    def calcInitialValues(self):
        pass

    @staticmethod
    def getToolTip(self):
        return \
'''
Add PointIdentity Constraint:
selection:
1.) select a vertex on a part
2.) select a vertex on another part
'''
#==============================================================================
class PointOnLineConstraint(BasicConstraint):
    def __init__(self,selection):
        BasicConstraint.__init__(self, selection)
        self.typeInfo = 'pointOnLine'
        self.constraintBaseName = 'pointOnLine'
        self.iconPath = ':/icons/a2p_PointIdentity.svg'
        self.create(selection)
        
    def calcInitialValues(self):
        pass

    @staticmethod
    def getToolTip(self):
        return \
'''
Add a PointOnLine constraint between two objects
1.) select a vertex from a part
2.) select a line (linear edge) on another part
'''
#==============================================================================
class PointOnPlaneConstraint(BasicConstraint):
    def __init__(self,selection):
        BasicConstraint.__init__(self, selection)
        self.typeInfo = 'pointOnPlane'
        self.constraintBaseName = 'pointOnPlane'
        self.iconPath = ':/icons/a2p_PointOnPlaneConstraint.svg'
        self.create(selection)
        
    def calcInitialValues(self):
        c = self.constraintObject
        point = getPos(self.ob1, c.SubElement1)
        plane = getObjectFaceFromName(self.ob2, c.SubElement2)
        planeNormal = plane.Surface.Axis
        planePos = getPos(self.ob2, c.SubElement2)
        #
        # calculate recent offset...
        delta = point.sub(planePos)
        self.offset = delta.dot(planeNormal)

    @staticmethod
    def getToolTip(self):
        return \
'''
Add a Point on Plane constraint between two objects
1.) select a vertex or a center of a circle
2.) select a plane on other part
'''
#==============================================================================
class CircularEdgeConstraint(BasicConstraint):
    def __init__(self,selection):
        BasicConstraint.__init__(self, selection)
        self.typeInfo = 'circularEdge'
        self.constraintBaseName = 'circularEdgeConstraint'
        self.iconPath = ':/icons/a2p_CircularEdgeConstraint.svg'
        self.create(selection)
        
    def calcInitialValues(self):
        c = self.constraintObject
        circleEdge1 = getObjectEdgeFromName(self.ob1, c.SubElement1)
        circleEdge2 = getObjectEdgeFromName(self.ob2, c.SubElement2)
        axis1 = circleEdge1.Curve.Axis
        axis2 = circleEdge2.Curve.Axis
        angle = math.degrees(axis1.getAngle(axis2))
        if angle <= 90.0:
            self.direction = "aligned"
        else:
            self.direction = "opposed"
        self.offset = 0.0
        self.lockRotation = False

    @staticmethod
    def getToolTip(self):
        return \
'''
Add a circular edge constraint between two parts
selection-hint:
1.) select circular edge on first importPart
2.) select circular edge on other importPart
'''
#==============================================================================
class AxialConstraint(BasicConstraint):
    def __init__(self,selection):
        BasicConstraint.__init__(self, selection)
        self.typeInfo = 'axial'
        self.constraintBaseName = 'axialConstraint'
        self.iconPath = ':/icons/a2p_AxialConstraint.svg'
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
    def getToolTip(self):
        return \
'''
Add an axialConstraint between two parts

2 axis are aligned and be moved
to be coincident

Selection:
1.) Select cylindrical face or linear edge on a part
2.) Select cylindrical face or linear edge on another part
'''
#==============================================================================
class AxisParallelConstraint(BasicConstraint):
    def __init__(self,selection):
        BasicConstraint.__init__(self, selection)
        self.typeInfo = 'axisParallel'
        self.constraintBaseName = 'axisParallel'
        self.iconPath = ':/icons/a2p_AxisParallelConstraint.svg'
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
    def getToolTip(self):
        return \
'''
Add an axisParallel constraint between two objects

Axis' will only rotate to be parallel, but not be
moved to be coincident

select:
1.) linearEdge or cylinderFace from a part
2.) linearEdge or cylinderFace from another part
'''
#==============================================================================
class AxisPlaneParallelConstraint(BasicConstraint):
    def __init__(self,selection):
        BasicConstraint.__init__(self, selection)
        self.typeInfo = 'axisPlaneParallel'
        self.constraintBaseName = 'axisPlaneParallel'
        self.iconPath = ':/icons/a2p_AxisPlaneParallelConstraint.svg'
        self.create(selection)
        
    def calcInitialValues(self):
        pass

    @staticmethod
    def getToolTip(self):
        return \
'''
Creates an axisPlaneParallel constraint.

1) select a linearEdge or cylinderAxis
2) select a plane face on another part

This constraint adjusts an axis parallel
to a selected plane. The parts are not
moved to be coincident.
'''
#==============================================================================
class PlanesParallelConstraint(BasicConstraint):
    def __init__(self,selection):
        BasicConstraint.__init__(self, selection)
        self.typeInfo = 'planeParallel'
        self.constraintBaseName = 'planeParallel'
        self.iconPath = ':/icons/a2p_PlanesParallelConstraint.svg'
        self.create(selection)
        
    def calcInitialValues(self):
        c = self.constraintObject
        plane1 = getObjectFaceFromName(self.ob1, c.SubElement1)
        plane2 = getObjectFaceFromName(self.ob2, c.SubElement2)
        normal1 = plane1.Surface.Axis
        normal2 = plane2.Surface.Axis
        angle = math.degrees(normal1.getAngle(normal2))
        if angle <= 90.0:
            self.direction = "aligned"
        else:
            self.direction = "opposed"

    @staticmethod
    def getToolTip(self):
        return \
'''
Add a planesParallel constraint between two objects

Planes will only rotate to be parallel, but not
moved to be coincident

select:
1.) select a plane on a part
2.) select a plane from another part
'''
#==============================================================================
class PlaneConstraint(BasicConstraint):
    def __init__(self,selection):
        BasicConstraint.__init__(self, selection)
        self.typeInfo = 'plane'
        self.constraintBaseName = 'planeConstraint'
        self.iconPath = ':/icons/a2p_PlaneCoincidentConstraint.svg'
        self.create(selection)
        
    def calcInitialValues(self):
        c = self.constraintObject
        plane1 = getObjectFaceFromName(self.ob1, c.SubElement1)
        plane2 = getObjectFaceFromName(self.ob2, c.SubElement2)
        normal1 = plane1.Surface.Axis
        normal2 = plane2.Surface.Axis
        angle = math.degrees(normal1.getAngle(normal2))
        if angle <= 90.0:
            self.direction = "aligned"
        else:
            self.direction = "opposed"
        self.offset = 0.0

    @staticmethod
    def getToolTip(self):
        return \
'''
Add a planeCoincident constraint between two objects
(An offset can be given)

select:
1.) select a plane on a part
2.) select a plane from another part
'''
#==============================================================================
class AngledPlanesConstraint(BasicConstraint):
    def __init__(self,selection):
        BasicConstraint.__init__(self, selection)
        self.typeInfo = 'angledPlanes'
        self.constraintBaseName = 'angledPlanesContraint'
        self.iconPath = ':/icons/a2p_AngleConstraint.svg'
        self.create(selection)
        
    def calcInitialValues(self):
        plane1 = getObjectFaceFromName(self.ob1, self.sub1)
        plane2 = getObjectFaceFromName(self.ob2, self.sub2)
        normal1 = plane1.Surface.Axis
        normal2 = plane2.Surface.Axis
        self.angle = math.degrees(normal2.getAngle(normal1))

    @staticmethod
    def getToolTip(self):
        return \
'''
Creates an angleBetweenPlanes constraint.

1) select first plane object
2) select second plane object on another part

After setting this constraint at first
the actual angle between both planes is
been calculated and stored to entry "angle" in
object editor.

After creating this constraint you can change
entry "angle" in object editor to desired value.

Avoid use of angle 0 degrees and 180 degrees.
You could get strange results.

Better for that is using planesParallelConstraint.
'''
#==============================================================================
class SphericalConstraint(BasicConstraint):
    def __init__(self,selection):
        BasicConstraint.__init__(self, selection)
        self.typeInfo = 'sphereCenterIdent'
        self.constraintBaseName = 'sphericalConstraint'
        self.iconPath = ':/icons/a2p_SphericalSurfaceConstraint.svg'
        self.create(selection)
        
    def calcInitialValues(self):
        pass

    @staticmethod
    def getToolTip(self):
        return \
'''
Add a spherical constraint between to objects

Selection options:
- spherical surface or vertex on a part
- spherical surface or vertex on another part
'''
#==============================================================================
        







































