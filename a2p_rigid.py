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

import os, sys
import random
import time
import traceback
import math
import copy
import FreeCAD, FreeCADGui, Part
from PySide import QtGui, QtCore
from FreeCAD import Base
from a2p_translateUtils import *
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
    PARTIAL_SOLVE_STAGE1,
    )
import a2p_libDOF

from a2p_libDOF import (
    SystemOrigin,
    SystemXAxis,
    SystemYAxis,
    SystemZAxis
    )
#from __builtin__ import False


SPINSTEP_DIVISOR = 12.0 #12
WEIGHT_LINEAR_MOVE = 0.5
WEIGHT_REFPOINT_ROTATION = 8.0



class Rigid():
    """All data necessary for one rigid body."""

    def __init__(self,
                name,
                label,
                fixed,
                placement,
                debugMode
                ):
        self.objectName = name
        self.label = label
        self.fixed = fixed
        self.tempfixed = fixed
        self.moved = False
        self.placement = placement
        self.debugMode = debugMode
        self.savedPlacement = placement
        self.dependencies = []
        self.linkedRigids = []
        self.hierarchyLinkedRigids = []
        self.depsPerLinkedRigids = {}   #dict for each linked obj as key, the value
                                        # is an array with all dep related to it
        self.dofPOSPerLinkedRigids = {} #for each linked rigid (Key) the related dof left free
        self.dofROTPerLinkedRigids = {} #for each linked rigid (Key) the related dof left free
        self.pointConstraints = []
        self.parentRigids = []
        self.childRigids = []
        self.disatanceFromFixed = None
        self.spinCenter = None
        self.spin = None
        self.moveVectorSum = None
        self.maxPosError = 0.0
        self.maxAxisError = 0.0         # This is an avaverage of all single spins
        self.maxSingleAxisError = 0.0   # Also the max single Axis spin has to be checked for solvability
        self.refPointsBoundBoxSize = 0.0
        self.countSpinVectors = 0
        self.currentDOFCount = 6
        self.superRigid = None  #if not None, it means that when action performed to this rigid,
                                #actually the action must be done on the superRigid
        self.posDOF = a2p_libDOF.initPosDOF #each rigid has DOF for position
        self.rotDOF = a2p_libDOF.initRotDOF #each rigid has DOF for rotation
        #dof are useful only for animation at the moment? maybe it can be used to set tempfixed property

    def prepareRestart(self):
        self.tempfixed = self.fixed
        for dep in self.dependencies:
            dep.disable()

    def countDependencies(self):
        return len(self.dependencies)

    def enableDependencies(self, workList):
        for dep in self.dependencies:
            dep.enable(workList)

    # The function only sets parentship for childrens that are distant+1 from fixed rigid
    # The function should be called in a loop with increased distance until it return False
    def assignParentship(self, distance):
        # Current rigid was already set, pass the call to childrens
        haveMore = False
        
        if self.disatanceFromFixed < distance:
            for rig in self.childRigids:
                haveMore = rig.assignParentship(distance)
        elif self.disatanceFromFixed == distance:
            while self.hierarchyLinkedRigids:
                rig = self.hierarchyLinkedRigids[0]
                # Got to a new rigid, set current as it's father
                if rig.disatanceFromFixed is None:
                    rig.parentRigids.append(self)
                    self.childRigids.append(rig)
                    rig.hierarchyLinkedRigids.remove(self)
                    self.hierarchyLinkedRigids.remove(rig)
                    rig.disatanceFromFixed = distance + 1
                # That child was already assigned by another (and closer to fixed) father
                # Leave only child relationship, but don't add current as a father
                else:
                    self.childRigids.append(rig)
                    rig.hierarchyLinkedRigids.remove(self)
                    self.hierarchyLinkedRigids.remove(rig)

            haveMore = len(self.childRigids) + len(self.hierarchyLinkedRigids) > 0

        return haveMore

    def printHierarchy(self, level):
        Msg((level*3)*" ")
        Msg("{} - distance {}\n".format(self.label, self.disatanceFromFixed))
        for rig in self.childRigids:
            rig.printHierarchy(level+1)

    def getCandidates(self, solverStage = None):
        candidates = []
        for linkedRig in self.linkedRigids:
            if linkedRig.tempfixed: continue
            candidates.append(linkedRig)
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
        return all(rig.tempfixed for rig in self.linkedRigids)

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
        self.superRigid = None

    def applySolution(self, doc, solver):
        if self.tempfixed or self.fixed: return

        # Update FreeCAD's placements if deltaPlacement above Tolerances
        base1 = self.placement.Base
        base2 = self.savedPlacement.Base
        absPosMove = base1.sub(base2).Length

        axis1 = self.placement.Rotation.Axis
        axis2 = self.savedPlacement.Rotation.Axis
        angle = math.degrees(axis2.getAngle(axis1))

        '''
        if absPosMove >= solver.mySOLVER_POS_ACCURACY*1e-2 or angle >= solver.mySOLVER_SPIN_ACCURACY*1e-2:
            ob1 = doc.getObject(self.objectName)
            ob1.Placement = self.placement
        '''
        ob1 = doc.getObject(self.objectName)
        ob1.Placement = self.placement

    def getRigidCenter(self):
        _currentRigid = FreeCAD.ActiveDocument.getObject(self.objectName)
        return _currentRigid.Shape.BoundBox.Center

    def calcSpinCenterDepsEnabled(self):
        newSpinCenter = Base.Vector(self.spinCenter)
        countRefPoints = 0
        for dep in self.dependencies:
            if dep.Enabled and dep.refPoint is not None:
                newSpinCenter += dep.refPoint
                countRefPoints += 1
        if countRefPoints > 0:
            self.spinCenter = newSpinCenter / countRefPoints

    def calcSpinCenter(self):
        """
        Calculate the center for rotation (spin center) based on the reference points of dependencies.

        This method iterates over the dependencies and calculates the spin center based on the available reference points.

        Returns:
            None
        """
        # Initialize variables
        refPoints = [dep.refPoint for dep in self.dependencies if dep.refPoint is not None]

        # Check if there are any valid reference points
        if refPoints:
            # Calculate the sum of all reference points
            totalRefPoint = sum(refPoints, Base.Vector(0, 0, 0))
            # Calculate the average by dividing the sum by the number of reference points
            self.spinCenter = totalRefPoint / len(refPoints)

    def calcSpinBasicDataDepsEnabled(self):
        """
        Calculate the spin center and reference points bounding box size based on the enabled dependencies.

        This method iterates over the enabled dependencies, calculates the spin center based on their reference points,
        and determines the size of the bounding box enclosing all reference points.

        Returns:
            None
        """
        # Initialize variables
        newSpinCenter = Base.Vector(0, 0, 0)
        countRefPoints = 0
        refPoints = []  # Collect reference points for bounding box calculation

        # Iterate over enabled dependencies
        for dep in self.dependencies:
            if dep.Enabled:
                # Accumulate reference points and count
                newSpinCenter += dep.refPoint
                countRefPoints += 1
                refPoints.append(dep.refPoint)

        # Calculate the spin center if there are any reference points
        if countRefPoints > 0:
            newSpinCenter.multiply(1.0 / countRefPoints)
            self.spinCenter = newSpinCenter

            # Calculate bounding box size
            minPoint = Base.Vector(min(refPoints, key=lambda p: p.x).x, min(refPoints, key=lambda p: p.y).y,
                                min(refPoints, key=lambda p: p.z).z)
            maxPoint = Base.Vector(max(refPoints, key=lambda p: p.x).x, max(refPoints, key=lambda p: p.y).y,
                                max(refPoints, key=lambda p: p.z).z)
            self.refPointsBoundBoxSize = maxPoint.sub(minPoint).Length

    def calcRefPointsBoundBoxSizeDepsEnabled(self):
        """
        Calculate the size of the bounding box enclosing reference points only for enabled dependencies.

        This method iterates over enabled dependencies and determines the bounding box size based on their reference points.

        Returns:
            None
        """
        # Initialize min and max values with the first enabled dependency's reference point
        first_dep = next((dep for dep in self.dependencies if dep.Enabled), None)
        if first_dep is None:
            return  # No enabled dependencies, exit early
        xmin = xmax = first_dep.refPoint.x
        ymin = ymax = first_dep.refPoint.y
        zmin = zmax = first_dep.refPoint.z

        # Iterate over enabled dependencies starting from the second one
        for dep in self.dependencies:
            if dep.Enabled:
                # Update min and max values for each axis
                xmin = min(xmin, dep.refPoint.x)
                xmax = max(xmax, dep.refPoint.x)
                ymin = min(ymin, dep.refPoint.y)
                ymax = max(ymax, dep.refPoint.y)
                zmin = min(zmin, dep.refPoint.z)
                zmax = max(zmax, dep.refPoint.z)

        # Calculate bounding box size using Euclidean distance formula
        self.refPointsBoundBoxSize = math.sqrt((xmax - xmin) ** 2 + (ymax - ymin) ** 2 + (zmax - zmin) ** 2)


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
        if self.tempfixed or self.fixed:
            return

        depRefPoints = []               #collect Data to compute central movement of rigid
        depMoveVectors = []             #all moveVectors
        depRefPoints_Spin = []          #refPoints, relevant for spin generation...
        depMoveVectors_Spin = []        #depMoveVectors, relevant for spin generation...

        self.maxPosError = 0.0
        self.maxAxisError = 0.0         # SpinError is an average of all single spins
        self.maxSingleAxisError = 0.0   # avoid average, to detect unsolvable assemblies
        self.countSpinVectors = 0
        self.moveVectorSum = Base.Vector(0, 0, 0)
        self.spin = None

        for dep in self.dependencies:
            refPoint, moveVector = dep.getMovement()
            if refPoint is None or moveVector is None: # Should not happen
                continue

            depRefPoints.append(refPoint)
            depMoveVectors.append(moveVector)

            if dep.useRefPointSpin:
                depRefPoints_Spin.append(refPoint)
                depMoveVectors_Spin.append(moveVector)

            # Calculate max move error
            move_length = moveVector.Length
            if move_length > self.maxPosError:
                self.maxPosError = move_length

            # Accumulate all the movements for later average calculations
            self.moveVectorSum += moveVector

        # Calculate the average of all the movements
        num_dep_move_vectors = len(depMoveVectors)
        if num_dep_move_vectors > 0:
            self.moveVectorSum *= 1.0 / num_dep_move_vectors

        # Compute rotation caused by refPoint-attractions
        if len(depMoveVectors_Spin) >= 2:
            #FIXME
            self.spin = Base.Vector(0, 0, 0)
            tmpSpinCenter = depRefPoints_Spin[0] # assume rigid spinning around first depRefPoint

            # Eliminate the offset of depRefPoint[0] from all depMoveVectors
            offsetVector = Base.Vector(depMoveVectors_Spin[0]) # make a copy
            for i in range(len(depMoveVectors_Spin)):
                depMoveVectors_Spin[i] -= offsetVector

            for i in range(1, len(depRefPoints_Spin)):  # do not use index 0, rigid is assumed spinning around this point
                try:
                    vec1 = depRefPoints_Spin[i] - tmpSpinCenter
                    vec2 = depMoveVectors_Spin[i]
                    axis = vec1.cross(vec2)
                    vec1_length = vec1.Length
                    if vec1_length >= 1e-6:
                        vec1 *= self.refPointsBoundBoxSize
                        vec3 = vec1 + vec2
                        beta = math.degrees(vec3.getAngle(vec1))
                        if beta > self.maxSingleAxisError:
                            self.maxSingleAxisError = beta
                        axis *= beta * WEIGHT_REFPOINT_ROTATION
                        self.spin += axis
                        self.countSpinVectors += 1
                except:
                    pass #numerical exception above, no spin !
                
        # Compute rotation caused by axis' of the dependencies //FIXME (align,opposed,none)
        if self.dependencies:
            if self.spin is None:
                self.spin = Base.Vector(0, 0, 0)

            for dep in self.dependencies:
                rotation = dep.getRotation(solver)
                if rotation is None: # No rotation for that dep
                    continue

                # Accumulate all rotations for later average calculation
                self.spin += rotation
                rotationLength = rotation.Length
                if rotationLength > self.maxSingleAxisError:
                    self.maxSingleAxisError = rotationLength
                self.countSpinVectors += 1

        # Calculate max rotation error
        if self.spin is not None:
            axisErr = self.spin.Length
            if axisErr > self.maxAxisError:
                self.maxAxisError = axisErr

    def move(self, doc):
        if self.tempfixed or self.fixed:
            return
        #Linear moving of a rigid
        moveDist = Base.Vector(0, 0, 0)
        if self.moveVectorSum:
            moveDist = Base.Vector(self.moveVectorSum)
            moveDist.multiply(WEIGHT_LINEAR_MOVE) # stabilize computation, adjust if needed...

        #Rotate the rigid...
        center = None
        rotation = None
        if self.spin and self.spin.Length != 0.0 and self.countSpinVectors != 0:
            savedSpin = copy.copy(self.spin)
            spinAngle = min(self.spin.Length / self.countSpinVectors, 15.0)  # Limit the spin angle to 15 degrees
            try:
                spinStep = spinAngle / SPINSTEP_DIVISOR #it was 250.0
                self.spin.multiply(1.0e12)
                self.spin.normalize()
                rotation = FreeCAD.Rotation(self.spin, spinStep)
                center = self.spinCenter
            except Exception as e:
                print("Error occurred during rotation calculation:", e)

        if center is not None and rotation is not None:
            pl = FreeCAD.Placement(moveDist, rotation, center)
            self.applyPlacementStep(pl)
        elif moveDist.Length > 1e-8:
            pl = FreeCAD.Placement()
            pl.move(moveDist)
            self.applyPlacementStep(pl)

    def currentDOF(self):
        """
        Update whole DOF of the rigid (useful for animation and get the number
        useful to determine if an object is fully constrained.
        """
        self.pointConstraints = []
        _dofPos = []
        _dofRot = []
        self.reorderDependencies()
        
        if not self.fixed and self.dependencies:
            for dependency in self.dependencies:
                posDOF, rotDOF = dependency.calcDOF([], [], self.pointConstraints)
                _dofPos.extend(posDOF)
                _dofRot.extend(rotDOF)

        self.posDOF = _dofPos
        self.rotDOF = _dofRot
        self.currentDOFCount = len(_dofPos) + len(_dofRot)
        return self.currentDOFCount

    def isFullyConstrainedByRigid(self,rig):
        if rig not in self.linkedRigids:
            return False
        dofPOS = self.dofPOSPerLinkedRigids[rig]
        dofROT = self.dofROTPerLinkedRigids[rig]
        if len(dofPOS) + len(dofROT) == 0:
            return True
        return False

    def isFullyConstrainedByFixedRigids(self):
        """
        Check if the rigid is fully constrained by fixed rigids.
        """
        self.reorderDependencies()
        if self.dependencies:
            posDOF = []
            rotDOF = []
            for dependency in self.dependencies:
                if dependency.dependedRigid.tempfixed:
                    posDOF, rotDOF = dependency.calcDOF(posDOF, rotDOF, self.pointConstraints)
        else:
            return False

        return not posDOF and not rotDOF

    def linkedTempFixedDOF(self):
        """
        Calculate the number of degrees of freedom (DOFs) constrained by temporary fixed rigids.
        """
        self.reorderDependencies()
        if not self.tempfixed and self.dependencies:
            posDOF = []
            rotDOF = []
            for dependency in self.dependencies:
                if dependency.dependedRigid.tempfixed:
                    posDOF, rotDOF = dependency.calcDOF(posDOF, rotDOF, self.pointConstraints)
        else:
            return 0

        return len(posDOF) + len(rotDOF)

    def reorderDependencies(self):
        """
        place all kind of pointconstraints at the end
        of the dependencies list.
        """
        tmplist1 = []
        tmplist2 = []
        for dep in self.dependencies:
            if dep.isPointConstraint:
                tmplist1.append(dep)
            else:
                tmplist2.append(dep)
        self.dependencies = []
        self.dependencies.extend(tmplist2)
        self.dependencies.extend(tmplist1)

    def beautyDOFPrint(self):
        """
        pretty print output that describe the current DOF of the rigid.
        """
        Msg('\n')
        Msg(translate("A2plus", "Current Rigid = '{}'").format(self.label) + "\n")
        if self.fixed:
            Msg(translate("A2plus", "    is Fixed") + "\n")
        else:
            Msg(translate("A2plus", "    is not Fixed and has {} DegreesOfFreedom").format(self.currentDOF()) + "\n")
        for rig in self.depsPerLinkedRigids.keys():
            Msg(translate("A2plus", "    Depends on Rigid = {}").format(rig.label) + "\n")
            for dep in self.depsPerLinkedRigids[rig]:
                Msg(u"        {}\n".format(dep) )
            Msg(translate("A2plus", "        DOF Position free with this rigid = {}").format( len(self.dofPOSPerLinkedRigids[rig])) + "\n")
            Msg(translate("A2plus", "        DOF Rotation free with this rigid = {}").format( len(self.dofROTPerLinkedRigids[rig])) + "\n")
