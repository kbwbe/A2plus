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
    appVersionStr
    )
import os, sys
from os.path import expanduser
#from Units import Unit, Quantity


SOLVER_MAXSTEPS = 100000
SOLVER_POS_ACCURACY = 1.0e-1 #Need to implement variable stepwith calculation to improve this..
SOLVER_SPIN_ACCURACY = 1.0e-1 #Sorry for that at moment...

SPINSTEP_DIVISOR = 12.0
WEIGHT_LINEAR_MOVE = 0.5
WEIGHT_REFPOINT_ROTATION = 25.0


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
        self.mySOLVER_SPIN_ACCURACY = SOLVER_SPIN_ACCURACY
        self.mySOLVER_POS_ACCURACY = SOLVER_POS_ACCURACY
        
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
                if objectName != None and not objectName in self.objectNames:
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
                ob1.Label,
                fx,
                ob1.Placement
                )
            rig.spinCenter = ob1.Shape.BoundBox.Center
            self.rigids.append(rig)
        #
        #link constraints to rigids using dependencies
        for c in self.constraints:
            rigid1 = self.getRigid(c.Object1)
            rigid2 = self.getRigid(c.Object2)

            rigid1.linkedRigids.append(rigid2);
            rigid2.linkedRigids.append(rigid1);

            Dependency.Create(doc, c, self, rigid1, rigid2)

        for rig in self.rigids:
            rig.calcSpinCenter()
            rig.calcRefPointsBoundBoxSize()            


    # TODO: maybe instead of traversing from the root every time, save a list of objects on current distance
    # and use them to propagate next distance to their children
    def assignParentship(self, doc):
        # Start from fixed parts
        for rig in self.rigids:
            if rig.fixed:
                rig.disatanceFromFixed = 0
                haveMore = True
                distance = 0
                while haveMore:
                    haveMore = rig.assignParentship(distance)
                    distance += 1

        FreeCAD.Console.PrintMessage(20*"=" + "\n")
        FreeCAD.Console.PrintMessage("Hierarchy:\n")
        FreeCAD.Console.PrintMessage(20*"=" + "\n")
        for rig in self.rigids:
            if rig.fixed: rig.printHierarchy(0)
        FreeCAD.Console.PrintMessage(20*"=" + "\n")
        self.visualizeHierarchy()

    def visualizeHierarchy(self):
        home = expanduser("~")
        out_file = os.path.join(home,'assembly_hierarchy.html')
        FreeCAD.Console.PrintMessage("Writing visual hierarchy to: {}\n".format(out_file))
        f = open(out_file, "w")

        f.write("<!DOCTYPE html>\n")
        f.write("<html>\n")
        f.write("<head>\n")
        f.write('    <meta charset="utf-8">\n')
        f.write('    <meta http-equiv="X-UA-Compatible" content="IE=edge">\n')
        f.write('    <title>A2P assembly hierarchy visualization</title>\n')
        f.write("</head>\n")
        f.write("<body>\n")
        f.write('<div class="mermaid">\n')

        f.write("graph TD\n")
        for rig in self.rigids:
            # No children, add current rogod as a leaf entry
            if len(rig.childRigids) == 0:
                f.write("{}\n".format(rig.label))
            else:
                # Rigid have children, add them based on the dependency list
                for d in rig.dependencies:
                    if d.dependedRigid in rig.childRigids:
                        if rig.fixed:
                            f.write("{}({}<br>*FIXED*) -- {} --> {}\n".format(rig.label, rig.label, d.Type, d.dependedRigid.label))
                        else:
                            f.write("{} -- {} --> {}\n".format(rig.label, d.Type, d.dependedRigid.label))

        f.write("</div>\n")
        f.write('    <script src="https://unpkg.com/mermaid@7.1.2/dist/mermaid.js"></script>\n')
        f.write("    <script>\n")
        f.write('        mermaid.initialize({startOnLoad: true});\n')
        f.write("    </script>\n")
        f.write("</body>")
        f.write("</html>")
        f.close()

    def calcMoveData(self,doc):
        for rig in self.rigids:
            rig.calcMoveData(doc, self)
            
    def prepareRestart(self):
        for rig in self.rigids:
            rig.prepareRestart()

    def solveSystem(self,doc):
        self.level_of_accuracy=1
        FreeCAD.Console.PrintMessage( "\n===== Start Solving System ====== \n" )

        startTime = int(round(time.time() * 1000))
        self.loadSystem(doc)
        self.assignParentship(doc)
        loadTime = int(round(time.time() * 1000))
        while True:
            systemSolved = self.calculateChain(doc)
            totalTime = int(round(time.time() * 1000))
            #FreeCAD.Console.PrintMessage( "Position Accuracy: %f\n" %  self.mySOLVER_POS_ACCURACY )
            #FreeCAD.Console.PrintMessage( "Max positionerror: %f\n" %  poserror )
            #FreeCAD.Console.PrintMessage( "Spin Accuracy: %f\n" %  self.mySOLVER_SPIN_ACCURACY )
            #FreeCAD.Console.PrintMessage( "Max spinerror: %f\n" %  spinerror )
            FreeCAD.Console.PrintMessage( "Total steps used: %d\n" %  self.stepCount)
            FreeCAD.Console.PrintMessage( "LoadTime (ms): %d\n" % (loadTime - startTime) )
            FreeCAD.Console.PrintMessage( "CalcTime (ms): %d\n" % (totalTime - loadTime) )
            FreeCAD.Console.PrintMessage( "TotalTime (ms): %d\n" % (totalTime - startTime) )
            if systemSolved:
                FreeCAD.Console.PrintMessage( "===== System solved ! ====== \n" )
                self.mySOLVER_SPIN_ACCURACY *= 1e-1
                self.mySOLVER_POS_ACCURACY *= 1e-1
                self.level_of_accuracy+=1
                if self.level_of_accuracy == 4:
                    self.solutionToParts(doc)
                    break
                self.prepareRestart()
            else:
                FreeCAD.Console.PrintMessage( "===== Could not solve system ====== \n" )

                msg = \
    '''
    Constraints inconsistent. Cannot solve System. 
    Please delete your last created constraint !
    '''
                QtGui.QMessageBox.information(  QtGui.QApplication.activeWindow(), "Constraint mismatch", msg )
                break
        self.mySOLVER_SPIN_ACCURACY = SOLVER_SPIN_ACCURACY
        self.mySOLVER_POS_ACCURACY = SOLVER_POS_ACCURACY

    def printList(self, name, l):
        FreeCAD.Console.PrintMessage("{} = (".format(name))
        for e in l:
            FreeCAD.Console.PrintMessage( "{} ".format(e.label) )
        FreeCAD.Console.PrintMessage("):\n")

    def calculateChain(self, doc):
        self.stepCount = 0
        rigCalcCount = 0
        haveMore = True
        workList = []

        if a2plib.isPartialProcessing():
            FreeCAD.Console.PrintMessage( "Solvermode = partialProcessing !\n")
            # start from fixed rigids and its children
            for rig in self.rigids:
                if rig.fixed:
                    workList.append(rig);
                    workList.extend(set(rig.getCandidates()))
        else:
            FreeCAD.Console.PrintMessage( "Solvermode = solve all Parts at once !\n")
            workList.extend(self.rigids)

        while haveMore:
            solutionFound = self.calculateWorkList(doc, workList)
            if not solutionFound: return False

            addList = []
            for rig in workList:
                addList.extend(rig.getCandidates())
            # Eliminate duplicates
            addList = set(addList)
            workList.extend(addList)
            haveMore = (len(addList) > 0)
            self.printList("AddList", addList)


        return True

    def calculateWorkList(self, doc, workList):
        self.printList("WorkList", workList)

        for rig in workList:
            rig.enableDependencies(workList)

        calcCount = 0
        goodAccuracy = False
        while not goodAccuracy:
            maxPosError = 0.0
            maxAxisError = 0.0

            calcCount += 1
            self.stepCount += 1
            # First calculate all the movement vectors
            for w in workList:
                w.calcMoveData(doc, self)
                if w.maxPosError > maxPosError:
                    maxPosError = w.maxPosError
                if w.maxAxisError > maxAxisError:
                    maxAxisError = w.maxAxisError

            # Perform the move
            for w in workList:
                w.move(doc)
                # Enable those 2 lines to see the computation progress on screen
                #w.applySolution(doc, self)
                #FreeCADGui.updateGui()

            # The accuracy is good, apply the solution to FreeCAD's objects
            if (maxPosError <= self.mySOLVER_POS_ACCURACY and
                maxAxisError <= self.mySOLVER_SPIN_ACCURACY):
                # The accuracy is good, we're done here
                goodAccuracy = True
                # Mark the rigids as tempfixed and add its constrained rigids to pending list to be processed next
                FreeCAD.Console.PrintMessage( "{} counts \n".format(calcCount) )
                for r in workList:
                    r.applySolution(doc, self)
                    r.tempfixed = True

            if self.stepCount > SOLVER_MAXSTEPS:
                FreeCAD.Console.PrintMessage( "Reached max calculations count ({})\n".format(SOLVER_MAXSTEPS) )
                return False
        return True

    def solutionToParts(self,doc):
        for rig in self.rigids:
            rig.applySolution(doc, self);

#------------------------------------------------------------------------------
class Rigid():
    ''' All data necessary for one rigid body'''
    def __init__(self,
                name,
                label,
                fixed,
                placement
                ):
        self.objectName = name
        self.label = label
        self.fixed = fixed
        self.tempfixed = fixed
        self.placement = placement
        self.savedPlacement = placement
        self.dependencies = []
        self.linkedRigids = []
        self.parentRigids = []
        self.childRigids = []
        self.disatanceFromFixed = None
        self.spinCenter = None
        self.spin = None
        self.moveVectorSum = None
        self.maxPosError = 0.0
        self.maxAxisError = 0.0
        self.refPointsBoundBoxSize = 0.0
        self.countSpinVectors = 0
        
    def prepareRestart(self):
        self.tempfixed = False
        for d in self.dependencies:
            d.disable()
            

    def enableDependencies(self, workList):
        for dep in self.dependencies:
            dep.enable(workList)

    # The function only sets parentship for childrens that are distant+1 from fixed rigid
    # The function should be called in a loop with increased distance until it return False
    def assignParentship(self, distance):
        #FreeCAD.Console.PrintMessage((self.disatanceFromFixed*3)*" ")
        #FreeCAD.Console.PrintMessage("In {}:{}, distance {}\n".format(self.label, self.disatanceFromFixed, distance))
        # Current rigid was already set, pass the call to childrens
        if self.disatanceFromFixed < distance:
            haveMore = False
            for rig in self.childRigids:
                #FreeCAD.Console.PrintMessage((self.disatanceFromFixed*3)*" ")
                #FreeCAD.Console.PrintMessage("   passing to {}:{}, distance {}\n".format(rig.label, rig.disatanceFromFixed, distance))
                if rig.assignParentship(distance):
                    haveMore = True
            return haveMore
        elif self.disatanceFromFixed == distance:
            while len(self.linkedRigids) > 0:
                rig = self.linkedRigids[0]
                # Got to a new rigid, set current as it's father
                if rig.disatanceFromFixed is None:
                    #FreeCAD.Console.PrintMessage((self.disatanceFromFixed*3)*" ")
                    #FreeCAD.Console.PrintMessage("   setting {}:{} with distance {}\n".format(rig.label, rig.disatanceFromFixed, distance+1))
                    rig.parentRigids.append(self)
                    self.childRigids.append(rig)
                    rig.linkedRigids.remove(self)
                    self.linkedRigids.remove(rig)
                    rig.disatanceFromFixed = distance+1
                # That child was already assigned by another (and closer to fixed) father
                # Leave only child relationship, but don't add current as a father
                else:
                    #FreeCAD.Console.PrintMessage((self.disatanceFromFixed*3)*" ")
                    #FreeCAD.Console.PrintMessage("   the {}:{} was already set, ignore\n".format(rig.label, rig.disatanceFromFixed))
                    self.childRigids.append(rig)
                    rig.linkedRigids.remove(self)
                    self.linkedRigids.remove(rig)

            if len(self.childRigids) + len(self.linkedRigids) > 0: return True
            else: return False
#        else:
#            FreeCAD.Console.PrintMessage("Should not happen: {}:{} got distance {}\n".format(self.label, self.disatanceFromFixed, distance))
            

    def printHierarchy(self, level):
        FreeCAD.Console.PrintMessage((level*3)*" ")
        FreeCAD.Console.PrintMessage("{} - distance {}\n".format(self.label, self.disatanceFromFixed))
        for rig in self.childRigids:
            rig.printHierarchy(level+1)
    
    def getCandidates(self):
        candidates = []
        for rig in self.childRigids:
            if not rig.tempfixed and rig.areAllParentTempFixed(): 
                candidates.append(rig)
        return set(candidates)

    def addChildrenByDistance(self, addList, distance):
        # Current rigid is the father of the needed distance, so it might have needed children
        if self.disatanceFromFixed == distance-1:
            # No children
            if len(self.childRigids) == 0: return False
            else:
                # There are some childrens, add with the matching distance
                for rig in self.childRigids:
                    if rig.disatanceFromFixed == distance:
                        addList.append(rig)
        # That rigid have children for needed distance
        else: return False

    def areAllParentTempFixed(self):
        for rig in self.parentRigids:
            if not rig.tempfixed: 
                return False
        return True

    def applyPlacementStep(self, pl):
        self.placement = pl.multiply(self.placement)
        self.spinCenter = pl.multVec(self.spinCenter)
        # Update dependencies
        for dep in self.dependencies:
            dep.applyPlacement(pl)

    def clear(self):
        for d in self.dependencies:
            d.clear()
        self.dependencies = []

    def applySolution(self, doc, solver):
        if self.tempfixed or self.fixed: return

        # Update FreeCAD's placements if deltaPlacement above Tolerances
        base1 = self.placement.Base
        base2 = self.savedPlacement.Base
        absPosMove = base1.sub(base2).Length

        axis1 = self.placement.Rotation.Axis
        axis2 = self.savedPlacement.Rotation.Axis
        angle = math.degrees(axis2.getAngle(axis1))

        if absPosMove >= solver.mySOLVER_POS_ACCURACY*1e-2 or angle >= solver.mySOLVER_SPIN_ACCURACY*1e-1:
            ob1 = doc.getObject(self.objectName)
            ob1.Placement = self.placement

    def calcSpinCenter(self):
        newSpinCenter = Base.Vector(0,0,0)
        countRefPoints = 0
        for dep in self.dependencies:
            if dep.refPoint != None:
                newSpinCenter = newSpinCenter.add(dep.refPoint)
                countRefPoints += 1
        if countRefPoints > 0:
            newSpinCenter.multiply(1.0/countRefPoints)
            self.spinCenter = newSpinCenter

    def calcRefPointsBoundBoxSize(self):
        xmin = 0
        xmax = 0
        ymin = 0
        ymax = 0
        zmin = 0
        zmax = 0
        for dep in self.dependencies:
            if dep.refPoint.x < xmin: xmin=dep.refPoint.x
            if dep.refPoint.x > xmax: xmax=dep.refPoint.x
            if dep.refPoint.y < ymin: ymin=dep.refPoint.y
            if dep.refPoint.y > ymax: ymax=dep.refPoint.y
            if dep.refPoint.z < zmin: zmin=dep.refPoint.z
            if dep.refPoint.z > zmax: zmax=dep.refPoint.z
        self.refPointsBoundBoxSize = math.sqrt( (xmax-xmin)**2 + (ymax-ymin)**2 + (zmax-zmin)**2 ) 

    def calcMoveData(self, doc, solver):
        if self.tempfixed or self.fixed: return
        depRefPoints = [] 
        depMoveVectors = [] #collect Data to compute central movement of rigid
        #
        self.maxPosError = 0.0
        self.maxAxisError = 0.0
        self.countSpinVectors = 0
        self.moveVectorSum = Base.Vector(0,0,0)

        for dep in self.dependencies:
            refPoint, moveVector = dep.getMovement()
            if refPoint is None or moveVector is None: continue     # Should not happen

            depRefPoints.append(refPoint)
            depMoveVectors.append(moveVector)

            # Calculate max move error
            if moveVector.Length > self.maxPosError: self.maxPosError = moveVector.Length

            # Accomulate all the movements for later average calculations
            self.moveVectorSum = self.moveVectorSum.add(moveVector)

        # Calculate the average of all the movements
        if len(depMoveVectors) > 0:
            self.moveVectorSum = self.moveVectorSum.multiply(1.0/len(depMoveVectors))

        #compute rotation caused by refPoint-attractions and axes mismatch
        if len(depMoveVectors) > 0 and self.spinCenter != None:
            self.spin = Base.Vector(0,0,0)

            #realMoveVectorSum = FreeCAD.Vector(self.moveVectorSum)
            #realMoveVectorSum.multiply(WEIGHT_LINEAR_MOVE)
            for i in range(0, len(depRefPoints)):
                try:
                    vec1 = depRefPoints[i].sub(self.spinCenter) # 'aka Radius'
                    vec2 = depMoveVectors[i].sub(self.moveVectorSum) # 'aka Force'
                    axis = vec1.cross(vec2) #torque-vector

                    vec1.normalize()
                    vec1.multiply(self.refPointsBoundBoxSize)
                    vec3 = vec1.add(vec2)
                    beta = vec3.getAngle(vec1)

                    axis.normalize()
                    axis.multiply(math.degrees(beta)*WEIGHT_REFPOINT_ROTATION) #here use degrees
                    self.spin = self.spin.add(axis)
                    self.countSpinVectors += 1
                except:
                    pass #numerical exception above, no spin !

            #adjust axis' of the dependencies //FIXME (align,opposed,none)

            for dep in self.dependencies:
                rotation = dep.getRotation(solver)

                if rotation is None: continue       # No rotation for that dep

                # Calculate max rotation error
                axisErr = self.spin.Length
                if axisErr > self.maxAxisError : self.maxAxisError = axisErr

                # Accumulate all rotations for later average calculation
                self.spin = self.spin.add(rotation)
                self.countSpinVectors += 1

    def move(self,doc):
        if self.tempfixed or self.fixed: return
        #
        #Linear moving of a rigid
        moveDist = Base.Vector(0,0,0)
        if self.moveVectorSum != None:
            moveDist = Base.Vector(self.moveVectorSum)
            moveDist.multiply(WEIGHT_LINEAR_MOVE) # stabilize computation, adjust if needed...
        #    
        #Rotate the rigid...
        center = None
        rotation = None
        if (self.spin != None and self.spin.Length != 0.0 and self.countSpinVectors != 0):
            spinAngle = self.spin.Length / self.countSpinVectors
            if spinAngle>15.0: spinAngle=15.0 # do not accept more degrees
            if spinAngle> 1e-8:
                try:
                    spinStep = spinAngle/(SPINSTEP_DIVISOR) #it was 250.0
                    self.spin.normalize()
                    rotation = FreeCAD.Rotation(self.spin, spinStep)
                    center = self.spinCenter
                except:
                    pass
                
        if center != None and rotation != None:
            pl = FreeCAD.Placement(moveDist,rotation,center)
            self.applyPlacementStep(pl)
        else:
            if moveDist.Length > 1e-8:
                pl = FreeCAD.Placement()
                pl.move(moveDist)
                self.applyPlacementStep(pl)
        
            
            

#------------------------------------------------------------------------------
class Dependency():
    def __init__(self, constraint, refType, axisRotation):
        self.Enabled = False
        self.Type = None
        self.refType = refType
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


    def clear(self):
        self.Type = None
        self.refType = None
        self.refPoint = None
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

    def __str__(self):
        return "Dependencies between {}-{}, type {}".format(self.currentRigid.label, self.dependedRigid.label, self.Type)

    @staticmethod
    def Create(doc, constraint, solver, rigid1, rigid2):
        FreeCAD.Console.PrintMessage("Creating dependencies between {}-{}, type {}\n".format(rigid1.label, rigid2.label, constraint.Type))

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
            FreeCAD.Console.PrintMessage("{} - not in working list\n".format(self))
            return

        self.Enabled = True
        self.foreignDependency.Enabled = True
        FreeCAD.Console.PrintMessage("{} - enabled\n".format(self))
        
    def disable(self):
        self.Enabled = False
        self.foreignDependency.Enabled = False

    def getMovement(self):
        raise NotImplementedError("Dependecly class {} doesn't implement movement, use inherited classes instead!".format(self.__class__.__name__))

    def getRotation(self, solver):
        if not self.Enabled: return None
        if not self.axisRotationEnabled: return None

        # The rotation is the same for all dependinties that enabled it
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

        #FreeCAD.Console.PrintMessage("{} - rotate by {}\n".format(self, axis.Length))
        return axis

#------------------------------------------------------------------------------

class DependencyPointIdentity(Dependency):
    def __init__(self, constraint, refType):
        Dependency.__init__(self, constraint, refType, False)

    def getMovement(self):
        if not self.Enabled: return None, None

        moveVector = self.foreignDependency.refPoint.sub(self.refPoint)
        #FreeCAD.Console.PrintMessage("{} - move by {}\n".format(self, moveVector.Length))
        return self.refPoint, moveVector

class DependencyPointOnLine(Dependency):
    def __init__(self, constraint, refType):
        Dependency.__init__(self, constraint, refType, False)

    def getMovement(self):
        if not self.Enabled: return None, None

        if self.refType == "point":
            vec1 = self.foreignDependency.refPoint.sub(self.refPoint)
            axis1 = self.foreignDependency.refAxisEnd.sub(self.foreignDependency.refPoint)
            dot = vec1.dot(axis1)
            axis1.multiply(dot) #projection of vec1 on axis1
            moveVector = vec1.sub(axis1)
            #FreeCAD.Console.PrintMessage("{} - move by {}\n".format(self, moveVector.Length))
            return self.refPoint, moveVector

        elif self.refType == "pointAxis":
            # refPoint is calculated in special way below
            vec1 = self.foreignDependency.refPoint.sub(self.refPoint)
            axis1 = self.refAxisEnd.sub(self.refPoint)
            dot = vec1.dot(axis1)
            axis1.multiply(dot) #projection of vec1 on axis1
            verticalRefOnLine = self.refPoint.add(axis1) #makes spinning around possible
            moveVector = vec1.sub(axis1)
            #FreeCAD.Console.PrintMessage("{} - move by {}\n".format(self, moveVector.Length))
            return verticalRefOnLine, moveVector

        else:
            raise NotImplementedError("Wrong refType for class {}".format(self.__class__.__name__))


class DependencyPointOnPlane(Dependency):
    def __init__(self, constraint, refType):
        Dependency.__init__(self, constraint, refType, False)

    def getMovement(self):
        if not self.Enabled: return None, None

        if self.refType == "point":
            vec1 = self.foreignDependency.refPoint.sub(self.refPoint)
            # Now move along foreign axis
            normal1 = self.foreignDependency.refAxisEnd.sub(self.foreignDependency.refPoint)
            dot = vec1.dot(normal1)
            normal1.multiply(dot)
            moveVector = normal1
            #FreeCAD.Console.PrintMessage("{} - move by {}\n".format(self, moveVector.Length))
            return self.refPoint, moveVector

        elif self.refType == "plane":
            # refPoint is calculated in special way below
            vec1 = self.foreignDependency.refPoint.sub(self.refPoint)
            normal1 = self.refAxisEnd.sub(self.refPoint) # move along own axis
            dot = vec1.dot(normal1)
            normal1.multiply(dot)
            moveVector = normal1
            verticalRefPointOnPlane = vec1.sub(moveVector)  #makes spinning around possible
            #FreeCAD.Console.PrintMessage("{} - move by {}\n".format(self, moveVector.Length))
            return verticalRefPointOnPlane, moveVector

        else:
            raise NotImplementedError("Wrong refType for class {}".format(self.__class__.__name__))

class DependencyCircularEdge(Dependency):
    def __init__(self, constraint, refType):
        Dependency.__init__(self, constraint, refType, True)

    def getMovement(self):
        if not self.Enabled: return None, None

        moveVector = self.foreignDependency.refPoint.sub(self.refPoint)
        #FreeCAD.Console.PrintMessage("{} - move by {}\n".format(self, moveVector.Length))
        return self.refPoint, moveVector

class DependencyParallelPlanes(Dependency):
    def __init__(self, constraint, refType):
        Dependency.__init__(self, constraint, refType, True)

    def getMovement(self):
        if not self.Enabled: return None, None

        #FreeCAD.Console.PrintMessage("{} - no move\n".format(self))
        return self.refPoint, Base.Vector(0,0,0)

class DependencyAngledPlanes(Dependency):
    def __init__(self, constraint, refType):
        Dependency.__init__(self, constraint, refType, True)

    def getMovement(self):
        if not self.Enabled: return None, None

        #FreeCAD.Console.PrintMessage("{} - no move\n".format(self))
        return self.refPoint, Base.Vector(0,0,0)

    def getRotation(self, solver):
        if not self.Enabled: return None

        axis = None # Rotation axis to be returned

        rigAxis = self.refAxisEnd.sub(self.refPoint)
        foreignDep = self.foreignDependency
        foreignAxis = foreignDep.refAxisEnd.sub(foreignDep.refPoint)
        recentAngle = math.degrees(foreignAxis.getAngle(rigAxis))
        deltaAngle = abs(self.angle.Value) - recentAngle
        if abs(deltaAngle) < 1e-6:
            # do not change spin, not necessary..
            axis = None
        else:
            try: 
                axis = rigAxis.cross(foreignAxis)
                axis.normalize()
                axis.multiply(math.degrees(-deltaAngle))
            except: #axis = Vector(0,0,0) and cannot be normalized...
                x = random.uniform(-solver.mySOLVER_SPIN_ACCURACY*1e-1,solver.mySOLVER_SPIN_ACCURACY*1e-1)
                y = random.uniform(-solver.mySOLVER_SPIN_ACCURACY*1e-1,solver.mySOLVER_SPIN_ACCURACY*1e-1)
                z = random.uniform(-solver.mySOLVER_SPIN_ACCURACY*1e-1,solver.mySOLVER_SPIN_ACCURACY*1e-1)
                axis = Base.Vector(x,y,z)
        #FreeCAD.Console.PrintMessage("{} - rotate by {}\n".format(self, axis.Length))
        return axis

class DependencyPlane(Dependency):
    def __init__(self, constraint, refType):
        Dependency.__init__(self, constraint, refType, True)

    def getMovement(self):
        if not self.Enabled: return None, None

        vec1 = self.foreignDependency.refPoint.sub(self.refPoint)
        # move along foreign axis...
        normal1 = self.foreignDependency.refAxisEnd.sub(self.foreignDependency.refPoint)
        dot = vec1.dot(normal1)
        normal1.multiply(dot)
        moveVector = normal1
        #FreeCAD.Console.PrintMessage("{} - move by {}\n".format(self, moveVector.Length))
        return self.refPoint, moveVector

class DependencyAxial(Dependency):
    def __init__(self, constraint, refType):
        Dependency.__init__(self, constraint, refType, True)

    def getMovement(self):
        if not self.Enabled: return None, None

        vec1 = self.foreignDependency.refPoint.sub(self.refPoint)
        destinationAxis = self.foreignDependency.refAxisEnd.sub(self.foreignDependency.refPoint)
        dot = vec1.dot(destinationAxis)
        parallelToAxisVec = destinationAxis.normalize().multiply(dot)
        moveVector = vec1.sub(parallelToAxisVec)
        #FreeCAD.Console.PrintMessage("{} - move by {}\n".format(self, moveVector.Length))
        return self.refPoint, moveVector



#------------------------------------------------------------------------------
def solveConstraints( doc, cache=None ): #cache because of compatibility to hamish...
    ss = SolverSystem()
    ss.solveSystem(doc)

def autoSolveConstraints( doc, cache=None):
    if not a2plib.getAutoSolveState():
        return
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




if __name__ == "__main__":
    FreeCAD.Console.PrintMessage( "Starting...\n" )
    doc = FreeCAD.activeDocument()
    solveConstraints(doc)


















