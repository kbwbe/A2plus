#***************************************************************************
#*                                                                         *
#*   Copyright (c) 2018 kbwbe                                     * 
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
from a2plib import (
    drawVector, 
    path_a2p,
    getObjectVertexFromName,
    getObjectEdgeFromName,
    getObjectFaceFromName,
    isLine,
    getPos,
    getAxis,
    appVersionStr
    )
from Units import Unit, Quantity


SOLVER_STEPS_BEFORE_ACCURACYCHECK = 100
SOLVER_MAXSTEPS = 10000
SOLVER_POS_ACCURACY = 1.0e-2 #Need to implement variable stepwith calculation to improve this..
SOLVER_SPIN_ACCURACY = 1.0e-2 #Sorry for that at moment...


#------------------------------------------------------------------------------
class SolverSystem():
    '''
    class Solversystem():
    A new iterative solver, inspired by physics.
    Using "attraction" of parts by constraints
    '''
    def __init__(self):
        self.doc = None
        self.stepCount = 0
        self.rigids = []        # list of rigid bodies
        self.constraints = []
        self.objectNames = []
        
    def clear(self):
        for r in self.rigids:
            r.clear()
        self.stepCount = 0
        self.rigids = []
        self.constraints = []
        self.objectNames = []
        
    def getRigid(self,objectName):
        '''get a Rigid by objectName'''
        rigs = [r for r in self.rigids if r.objectName == objectName]
        if len(rigs) > 0: return rigs[0]
        return None
        
    def loadSystem(self,doc):
        self.clear()
        self.doc = doc
        self.constraints = [ obj for obj in doc.Objects if 'ConstraintInfo' in obj.Content]
        #
        # Extract all the objectnames which are affected by constraints..
        self.objectNames = []
        for c in self.constraints:
            for attr in ['Object1','Object2']:
                objectName = getattr(c, attr, None)
                if objectName <> None and not objectName in self.objectNames:
                    self.objectNames.append( objectName )
        #
        # create a Rigid() dataStructure for each of these objectnames...
        for o in self.objectNames:
            ob1 = doc.getObject(o)
            if hasattr(ob1, "fixedPosition"):
                fx = ob1.fixedPosition
            else:
                fx = False
            rig = Rigid(
                o,
                fx,
                ob1.Placement
                )
            rig.spinCenter = ob1.Shape.BoundBox.Center
            self.rigids.append(rig)
        #
        #link constraints to rigids
        for c in self.constraints:
            rig1 = self.getRigid(c.Object1)
            dep1 = Dependency()
            dep1.Type = c.Type
            try:
                dep1.direction = c.directionConstraint
            except:
                pass # not all constraints do have direction-Property
            try:
                dep1.offset = c.offset 
            except:
                pass # not all constraints do have offset-Property
            try:
                dep1.angle = c.angle 
            except:
                pass # not all constraints do have angle-Property
            
            rig2 = self.getRigid(c.Object2)
            dep2 = Dependency()
            dep2.Type = c.Type
            try:
                dep2.direction = c.directionConstraint
            except:
                pass # not all constraints do have direction-Property
            try:
                dep2.offset = c.offset 
            except:
                pass # not all constraints do have offset-Property
            try:
                dep2.angle = c.angle 
            except:
                pass # not all constraints do have angle-Property

            if c.Type == "pointIdentity":
                dep1.refType = "point"
                dep2.refType = "point"
                ob1 = doc.getObject(c.Object1)
                ob2 = doc.getObject(c.Object2)
                
                vert1 = getObjectVertexFromName(ob1, c.SubElement1)
                vert2 = getObjectVertexFromName(ob2, c.SubElement2)
                dep1.refPoint = vert1.Point
                dep2.refPoint = vert2.Point
                
                axis1 = None
                axis2 = None
                dep1.refAxisEnd = None
                dep2.refAxisEnd = None
                #
                dep1.foreignDependency = dep2
                dep2.foreignDependency = dep1
                rig1.dependencies.append(dep1)
                rig2.dependencies.append(dep2)
                
            if c.Type == "sphereCenterIdent":
                dep1.refType = "point"
                dep2.refType = "point"
                ob1 = doc.getObject(c.Object1)
                ob2 = doc.getObject(c.Object2)
                
                
                vert1 = getPos(ob1, c.SubElement1)
                vert2 = getPos(ob2, c.SubElement2)
                dep1.refPoint = vert1
                dep2.refPoint = vert2
                
                axis1 = None
                axis2 = None
                dep1.refAxisEnd = None
                dep2.refAxisEnd = None
                #
                dep1.foreignDependency = dep2
                dep2.foreignDependency = dep1
                rig1.dependencies.append(dep1)
                rig2.dependencies.append(dep2)
                
            if c.Type == "pointOnLine":
                dep1.refType = "point"
                dep2.refType = "pointAxis"
                ob1 = doc.getObject(c.Object1)
                ob2 = doc.getObject(c.Object2)
                
                vert1 = getObjectVertexFromName(ob1, c.SubElement1)
                line2 = getObjectEdgeFromName(ob2, c.SubElement2)
                dep1.refPoint = vert1.Point
                dep2.refPoint = getPos(ob2,c.SubElement2)
                
                axis1 = None
                axis2 = getAxis(ob2, c.SubElement2)
                dep1.refAxisEnd = None
                dep2.refAxisEnd = dep2.refPoint.add(axis2)
                #
                dep1.foreignDependency = dep2
                dep2.foreignDependency = dep1
                rig1.dependencies.append(dep1)
                rig2.dependencies.append(dep2)
                
            if c.Type == "pointOnPlane":
                dep1.refType = "point"
                dep2.refType = "plane"
                ob1 = doc.getObject(c.Object1)
                ob2 = doc.getObject(c.Object2)
                
                vert1 = getObjectVertexFromName(ob1, c.SubElement1)
                plane2 = getObjectFaceFromName(ob2, c.SubElement2)
                dep1.refPoint = vert1.Point
                dep2.refPoint = plane2.Faces[0].BoundBox.Center
                
                axis1 = None
                normal2 = plane2.Surface.Axis
                dep1.refAxisEnd = None
                dep2.refAxisEnd = dep2.refPoint.add(normal2)
                #
                dep1.foreignDependency = dep2
                dep2.foreignDependency = dep1
                rig1.dependencies.append(dep1)
                rig2.dependencies.append(dep2)
                
            if c.Type == "circularEdge":
                dep1.refType = "pointAxis"
                dep2.refType = "pointAxis"
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
                if abs(dep2.offset) > 1e-6:
                    offsetAdjustVec = Base.Vector(axis2.x,axis2.y,axis2.z)
                    offsetAdjustVec.multiply(dep2.offset)
                    dep2.refPoint = dep2.refPoint.add(offsetAdjustVec)
                    dep2.refAxisEnd = dep2.refAxisEnd.add(offsetAdjustVec)
                #
                dep1.foreignDependency = dep2
                dep2.foreignDependency = dep1
                rig1.dependencies.append(dep1)
                rig2.dependencies.append(dep2)
                
            if c.Type == "planesParallel":
                dep1.refType = "pointNormal"
                dep2.refType = "pointNormal"
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
                dep1.foreignDependency = dep2
                dep2.foreignDependency = dep1
                rig1.dependencies.append(dep1)
                rig2.dependencies.append(dep2)
                
            if c.Type == "angledPlanes":
                dep1.refType = "pointNormal"
                dep2.refType = "pointNormal"
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
                #
                dep1.foreignDependency = dep2
                dep2.foreignDependency = dep1
                rig1.dependencies.append(dep1)
                rig2.dependencies.append(dep2)
                
            if c.Type == "plane":
                dep1.refType = "pointNormal"
                dep2.refType = "pointNormal"
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
                if abs(dep2.offset) > 1e-6:
                    offsetAdjustVec = Base.Vector(normal2.x,normal2.y,normal2.z)
                    offsetAdjustVec.multiply(dep2.offset)
                    dep2.refPoint = dep2.refPoint.add(offsetAdjustVec)
                    dep2.refAxisEnd = dep2.refAxisEnd.add(offsetAdjustVec)
                #
                dep1.foreignDependency = dep2
                dep2.foreignDependency = dep1
                rig1.dependencies.append(dep1)
                rig2.dependencies.append(dep2)
                
            if c.Type == "axial":
                dep1.refType = "pointAxis"
                dep2.refType = "pointAxis"
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
                dep1.foreignDependency = dep2
                dep2.foreignDependency = dep1
                rig1.dependencies.append(dep1)
                rig2.dependencies.append(dep2)
                
                
                
    def calcMoveData(self,doc):
        for rig in self.rigids:
            if rig.fixed: continue
            depRefPoints = [] 
            depMoveVectors = [] #collect Data to compute central movement of rigid
            #
            rig.maxPosError = 0.0
            for dep in rig.dependencies:
                
                if dep.Type == "pointIdentity" or dep.Type == "sphereCenterIdent":
                    depRefPoints.append(dep.refPoint)
                    dep.moveVector = dep.foreignDependency.refPoint.sub(dep.refPoint)
                    depMoveVectors.append(dep.moveVector)
                    
                if dep.Type == "pointOnLine":
                    # two possibilities, dep.refType can be a point or be a line
                    if dep.refType == "point":
                        depRefPoints.append(dep.refPoint)
                        vec1 = dep.foreignDependency.refPoint.sub(dep.refPoint)
                        axis1 = dep.foreignDependency.refAxisEnd.sub(dep.foreignDependency.refPoint)
                        dot = vec1.dot(axis1)
                        axis1.multiply(dot) #projection of vec1 on axis1
                        dep.moveVector = vec1.sub(axis1)
                        depMoveVectors.append(dep.moveVector)
                    if dep.refType == "pointAxis":
                        #depRefPoints.append(dep.refPoint) #is done in special way below
                        vec1 = dep.foreignDependency.refPoint.sub(dep.refPoint)
                        axis1 = dep.refAxisEnd.sub(dep.refPoint)
                        dot = vec1.dot(axis1)
                        axis1.multiply(dot) #projection of vec1 on axis1
                        verticalRefOnLine = dep.refPoint.add(axis1)
                        dep.moveVector = vec1.sub(axis1)
                        depMoveVectors.append(dep.moveVector)
                        depRefPoints.append(verticalRefOnLine) #makes spinning around possible
                        
                    
                if dep.Type == "pointOnPlane":
                    # two possibilities, dep.refType can be a point or be a plane
                    if dep.refType == "point":
                        depRefPoints.append(dep.refPoint)
                        vec1 = dep.foreignDependency.refPoint.sub(dep.refPoint)
                        # Now move along foreign axis
                        normal1 = dep.foreignDependency.refAxisEnd.sub(dep.foreignDependency.refPoint)
                        dot = vec1.dot(normal1)
                        normal1.multiply(dot)
                        dep.moveVector = normal1
                        depMoveVectors.append(dep.moveVector)
                    if dep.refType == "plane":
                        #depRefPoints.append(dep.refPoint) #is done in special way below
                        vec1 = dep.foreignDependency.refPoint.sub(dep.refPoint)
                        normal1 = dep.refAxisEnd.sub(dep.refPoint) # move along own axis
                        dot = vec1.dot(normal1)
                        normal1.multiply(dot)
                        dep.moveVector = normal1
                        depMoveVectors.append(dep.moveVector)
                        verticalRefPointOnPlane = vec1.sub(dep.moveVector)                    
                        depRefPoints.append(verticalRefPointOnPlane) #makes spinning around possible
                    
                if dep.Type == "circularEdge":
                    depRefPoints.append(dep.refPoint)
                    dep.moveVector = dep.foreignDependency.refPoint.sub(dep.refPoint)
                    depMoveVectors.append(dep.moveVector)

                if dep.Type == "planesParallel":
                    depRefPoints.append(dep.refPoint)
                    depMoveVectors.append(Base.Vector(0,0,0))

                if dep.Type == "angledPlanes":
                    depRefPoints.append(dep.refPoint)
                    depMoveVectors.append(Base.Vector(0,0,0))

                if dep.Type == "plane":
                    depRefPoints.append(dep.refPoint)
                    vec1 = dep.foreignDependency.refPoint.sub(dep.refPoint)
                    # move along foreign axis...
                    normal1 = dep.foreignDependency.refAxisEnd.sub(dep.foreignDependency.refPoint)
                    dot = vec1.dot(normal1)
                    normal1.multiply(dot)
                    dep.moveVector = normal1
                    depMoveVectors.append(dep.moveVector)

                if dep.Type == "axial":
                    depRefPoints.append(dep.refPoint)
                    vec1 = dep.foreignDependency.refPoint.sub(dep.refPoint)
                    destinationAxis = dep.foreignDependency.refAxisEnd.sub(dep.foreignDependency.refPoint)
                    dot = vec1.dot(destinationAxis)
                    parallelToAxisVec = destinationAxis.normalize().multiply(dot)
                    dep.moveVector = vec1.sub(parallelToAxisVec)
                    depMoveVectors.append(dep.moveVector)

            #
            #compute rigid.moveVectorSum
            rig.maxPosError = 0.0
            if ( len(depMoveVectors) > 0 ):
                vec = Base.Vector(0,0,0)
                for mv in depMoveVectors:
                    mvl = mv.Length
                    if mvl > rig.maxPosError: rig.maxPosError = mvl
                    vec = vec.add(mv)
                vec.multiply(1.0/len(depMoveVectors)) #the average of all movings
                rig.moveVectorSum = vec
            else:
                rig.moveVectorSum = Base.Vector(0,0,0)
            #
            #compute rotation caused by refPoint-attractions and axes mismatch
            if (
                len(depMoveVectors) > 0 and
                rig.spinCenter != None
                ):
                rig.spin = Base.Vector(0,0,0)
                for i in range(0,len(depRefPoints)):
                    vec1 = depRefPoints[i].sub(rig.spinCenter) # 'aka Radius'
                    vec2 = depMoveVectors[i].sub(rig.moveVectorSum) # 'aka Force'
                    axis = vec1.cross(vec2) #torque-vector
                    rig.spin = rig.spin.add(axis)
                    
                #adjust axis' of the dependencies //FIXME (align,opposed,none)
                rig.maxAxisError = 0.0
                for dep in rig.dependencies:

                    if (
                        dep.Type == "angledPlanes"
                        ):
                        rigAxis = dep.refAxisEnd.sub(dep.refPoint)
                        foreignAxis = dep.foreignDependency.refAxisEnd.sub(
                            dep.foreignDependency.refPoint
                            )
                        recentAngle = foreignAxis.getAngle(rigAxis) / 2.0/ math.pi *360
                        deltaAngle = dep.angle.Value - recentAngle
                        if abs(deltaAngle) < 1e-6:
                            # do not change spin, not necessary..
                            pass
                        else:
                            axis = rigAxis.cross(foreignAxis)
                            axis.normalize()
                            axis.multiply(-deltaAngle*57.296)
                            rig.spin = rig.spin.add(axis)

                    if (
                        dep.Type == "circularEdge" or
                        dep.Type == "plane" or
                        dep.Type == "planesParallel" or
                        dep.Type == "axial"
                        ):
                        if dep.direction != "none":
                            rigAxis = dep.refAxisEnd.sub(dep.refPoint)
                            foreignAxis = dep.foreignDependency.refAxisEnd.sub(
                                dep.foreignDependency.refPoint
                                )
                            #
                            #do we have wrong alignement of axes ??
                            dot = rigAxis.dot(foreignAxis)
                            if abs(dot+1.0) < 1e-3: #both axes nearly aligned but false orientation...
                                x = random.uniform(-1e-3,1e-3)
                                y = random.uniform(-1e-3,1e-3)
                                z = random.uniform(-1e-3,1e-3)
                                disturbVector = Base.Vector(x,y,z)
                                foreignAxis = foreignAxis.add(disturbVector)
                                
                            #axis = foreignAxis.cross(rigAxis)
                            axis = rigAxis.cross(foreignAxis)
                            try:
                                axis.normalize()
                                angle = foreignAxis.getAngle(rigAxis)
                                axis.multiply(angle*57.296*6) #57.296 = 360/2/pi
                                rig.spin = rig.spin.add(axis)
                                axisErr = rig.spin.Length
                                if axisErr > rig.maxAxisError : rig.maxAxisError = axisErr
                            except:
                                pass
                            
                        else: #if dep.direction... (== none)
                            rigAxis = dep.refAxisEnd.sub(dep.refPoint)
                            foreignAxis1 = dep.foreignDependency.refAxisEnd.sub(
                                dep.foreignDependency.refPoint
                                )
                            foreignAxis2 = dep.foreignDependency.refPoint.sub(
                                dep.foreignDependency.refAxisEnd
                                )
                            angle1 = abs(foreignAxis1.getAngle(rigAxis))
                            angle2 = abs(foreignAxis2.getAngle(rigAxis))
                            #
                            if angle1<=angle2:
                                axis = rigAxis.cross(foreignAxis1)
                                foreignAxis = foreignAxis1
                            else:
                                axis = rigAxis.cross(foreignAxis2)
                                foreignAxis = foreignAxis2
                            try:
                                axis.normalize()
                                angle = foreignAxis.getAngle(rigAxis)
                                axis.multiply(angle*57.296*6)
                                rig.spin = rig.spin.add(axis)
                                axisErr = rig.spin.Length
                                if axisErr > rig.maxAxisError : rig.maxAxisError = axisErr
                            except:
                                pass
                    #drawVector(rig.spinCenter,rig.spinCenter.add(rig.spin))
                    #print "len of spin: ",rig.spin.Length
                
    def moveRigids(self,doc):
        for rig in self.rigids:
            if rig.fixed: continue
            #
            #Linear moving of a rigid
            if rig.moveVectorSum != None:
                mov = rig.moveVectorSum
                #mov.multiply(1.0) # stabilize computation, adjust if needed...
                rot = FreeCAD.Rotation()
                center = rig.spinCenter
                pl = FreeCAD.Placement(mov,rot,center)
                rig.applyPlacementStep(pl)
            #    
            #Rotate the rigid...
            if (
                rig.spin != None and
                rig.spin.Length != 0.0
                ):
                mov = Base.Vector(0,0,0) # weitere Verschiebung ist null
                
                # Spinning of more than 360.0 degrees is useless...
                orig = rig.spin.Length
                if orig>359.0: orig=359.0
                if orig>1e-9:
                    try:
                        sq=abs(orig)/300
                        rig.spin.normalize()
                        rig.spin.multiply(sq)
                        rot = FreeCAD.Rotation(rig.spin,rig.spin.Length)
                        cent = rig.spinCenter
                        pl = FreeCAD.Placement(mov,rot,cent)
                        rig.applyPlacementStep(pl)
                    except:
                        pass
                
    def getAccuracy(self,doc):  
        '''returns maxPosError and maxSpinError of worst rigid'''
        self.calcMoveData(doc) 
        maxPosError = 0.0
        maxSpinError = 0.0
        for rig in self.rigids:
            if rig.maxAxisError > maxSpinError:
                maxSpinError = rig.maxAxisError
            if rig.maxPosError > maxPosError:
                maxPosError = rig.maxPosError
        return maxPosError, maxSpinError
                
    def solveSystem(self,doc):
        self.loadSystem(doc)
        self.stepCount = 0
        systemSolved = False
        while True:
            for i in range(0,SOLVER_STEPS_BEFORE_ACCURACYCHECK):
                self.doSolverStep(doc)
            self.stepCount += SOLVER_STEPS_BEFORE_ACCURACYCHECK
            poserror, spinerror = self.getAccuracy(doc)
            if (
                poserror <= SOLVER_POS_ACCURACY and
                spinerror <= SOLVER_SPIN_ACCURACY
                ): 
                systemSolved = True
                break
            if (self.stepCount >= SOLVER_MAXSTEPS):
                break
        FreeCAD.Console.PrintMessage( "Max positionerror: %f\n" %  poserror )
        FreeCAD.Console.PrintMessage( "Max spinerror: %f\n" %  spinerror )
        FreeCAD.Console.PrintMessage( "Total steps used: %d\n" %  self.stepCount )

        if systemSolved:
            self.solutionToParts(doc)
            FreeCAD.Console.PrintMessage( "===== System solved ! ====== \n" )
        else:
            FreeCAD.Console.PrintMessage( "===== Could not solve system ====== \n" )
            
            msg = \
'''
Constraints inconsistent. Cannot solve System. 
Please delete your last created constraint !
'''
            QtGui.QMessageBox.information(  QtGui.QApplication.activeWindow(), "Constraint mismatch", msg )
            
    
    def solutionToParts(self,doc):
        for rig in self.rigids:
            if rig.fixed: continue
            ob1 = doc.getObject(rig.objectName)
            ob1.Placement = rig.placement
        
    def doSolverStep(self,doc):
        self.calcMoveData(doc)
        self.moveRigids(doc)
        
#------------------------------------------------------------------------------
class Rigid():
    ''' All data necessary for one rigid body'''
    def __init__(self,
                 name,
                 fixed,
                 placement
                 ):
        self.objectName = name
        self.fixed = fixed
        self.placement = placement
        self.savedPlacement = placement
        self.dependencies = []
        self.spinCenter = None
        self.spin = None
        self.moveVectorSum = None
        self.maxPosError = 0.0
        self.maxAxisError = 0.0
        
    def applyPlacementStep(self,pl):
        self.placement = pl.multiply(self.placement)
        self.spinCenter = pl.multVec(self.spinCenter)
        for dep in self.dependencies:
            if dep.refPoint != None:
                dep.refPoint = pl.multVec(dep.refPoint)
            if dep.refAxisEnd != None:
                dep.refAxisEnd = pl.multVec(dep.refAxisEnd)
        
    def clear(self):
        for d in self.dependencies:
            d.clear()
        self.dependencies = []
        
#------------------------------------------------------------------------------
class Dependency():
    def __init__(self):
        self.Type = None
        self.refType = None
        self.refPoint = None
        self.refAxisEnd = None
        self.direction = None
        self.offset = None
        self.angle = None
        self.foreignDependency = None
        self.rotationAxis = None
        self.moveVector = None
        
    def clear(self):
        self.Type = None
        self.refType = None
        self.refPoint = None
        self.refAxisEnd = None
        self.direction = None
        self.offset = None
        self.angle = None
        self.foreignDependency = None
        self.rotationAxis = None
        self.moveVector = None
        
#------------------------------------------------------------------------------
        
        

#------------------------------------------------------------------------------
def solveConstraints( doc, cache=None ): #cache because of compatibility to hamish...
    ss = SolverSystem()
    ss.solveSystem(doc)

class a2p_SolverCommand:
    def Activated(self):
        solveConstraints( FreeCAD.ActiveDocument ) #the new iterative solver

    def GetResources(self): 
        return {
            'Pixmap' : path_a2p + '/icons/a2p_solver.svg', 
            'MenuText': 'Solve', 
            'ToolTip': 'Solve Assembly 2 constraints'
            } 

FreeCADGui.addCommand('a2p_SolverCommand', a2p_SolverCommand())
#------------------------------------------------------------------------------
























