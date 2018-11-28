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
        if self.direction != None:
            self.constraintObject.addProperty("App::PropertyEnumeration","directionConstraint", "ConstraintInfo")
            self.constraintObject.directionConstraint = ["aligned","opposed"]
            self.constraintObject.directionConstraint = self.direction
        if self.offset != None:
            self.constraintObject.addProperty('App::PropertyDistance','offset',"ConstraintInfo").offset = self.offset
        if self.angle != None:
            self.constraintObject.addProperty("App::PropertyAngle","angle","ConstraintInfo").angle = self.angle
    
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
        self.angle = normal2.getAngle(normal1) / 2.0 / math.pi * 360.0

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
        







































