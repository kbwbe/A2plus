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
        for d in self.dependencies:
            d.disable()

    def countDependencies(self):
        return len(self.dependencies)

    def enableDependencies(self, workList):
        for dep in self.dependencies:
            dep.enable(workList)

    # The function only sets parentship for childrens that are distant+1 from fixed rigid
    # The function should be called in a loop with increased distance until it return False
    def assignParentship(self, distance):
        # Current rigid was already set, pass the call to childrens
        if self.disatanceFromFixed < distance:
            haveMore = False
            for rig in self.childRigids:
                if rig.assignParentship(distance):
                    haveMore = True
            return haveMore
        elif self.disatanceFromFixed == distance:
            while len(self.hierarchyLinkedRigids) > 0:
                rig = self.hierarchyLinkedRigids[0]
                # Got to a new rigid, set current as it's father
                if rig.disatanceFromFixed is None:
                    rig.parentRigids.append(self)
                    self.childRigids.append(rig)
                    rig.hierarchyLinkedRigids.remove(self)
                    self.hierarchyLinkedRigids.remove(rig)
                    rig.disatanceFromFixed = distance+1
                # That child was already assigned by another (and closer to fixed) father
                # Leave only child relationship, but don't add current as a father
                else:
                    self.childRigids.append(rig)
                    rig.hierarchyLinkedRigids.remove(self)
                    self.hierarchyLinkedRigids.remove(rig)

            if len(self.childRigids) + len(self.hierarchyLinkedRigids) > 0: return True
            else: return False

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
        for rig in self.linkedRigids:
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
            if dep.Enabled:
                if dep.refPoint is not None:
                    newSpinCenter = newSpinCenter.add(dep.refPoint)
                    countRefPoints += 1
        if countRefPoints > 0:
            newSpinCenter.multiply(1.0/countRefPoints)
            self.spinCenter = newSpinCenter

    def calcSpinCenter(self):
        newSpinCenter = Base.Vector(0,0,0)
        countRefPoints = 0
        for dep in self.dependencies:
            if dep.refPoint is not None:
                newSpinCenter = newSpinCenter.add(dep.refPoint)
                countRefPoints += 1
        if countRefPoints > 0:
            newSpinCenter.multiply(1.0/countRefPoints)
            self.spinCenter = newSpinCenter

    def calcSpinBasicDataDepsEnabled(self):
        newSpinCenter = Base.Vector(0,0,0)
        countRefPoints = 0
        xmin = 0
        xmax = 0
        ymin = 0
        ymax = 0
        zmin = 0
        zmax = 0
        for dep in self.dependencies:
            if dep.Enabled:
                newSpinCenter = newSpinCenter.add(dep.refPoint)
                countRefPoints += 1
                if dep.refPoint.x < xmin: xmin=dep.refPoint.x
                if dep.refPoint.x > xmax: xmax=dep.refPoint.x
                if dep.refPoint.y < ymin: ymin=dep.refPoint.y
                if dep.refPoint.y > ymax: ymax=dep.refPoint.y
                if dep.refPoint.z < zmin: zmin=dep.refPoint.z
                if dep.refPoint.z > zmax: zmax=dep.refPoint.z
        vmin = Base.Vector(xmin,ymin,zmin)
        vmax = Base.Vector(xmax,ymax,zmax)
        self.refPointsBoundBoxSize = vmax.sub(vmin).Length

        if countRefPoints > 0:
            newSpinCenter.multiply(1.0/countRefPoints)
            self.spinCenter = newSpinCenter

    def calcRefPointsBoundBoxSizeDepsEnabled(self):
        xmin = 0
        xmax = 0
        ymin = 0
        ymax = 0
        zmin = 0
        zmax = 0
        for dep in self.dependencies:
            if dep.Enabled:
                if dep.refPoint.x < xmin: xmin=dep.refPoint.x
                if dep.refPoint.x > xmax: xmax=dep.refPoint.x
                if dep.refPoint.y < ymin: ymin=dep.refPoint.y
                if dep.refPoint.y > ymax: ymax=dep.refPoint.y
                if dep.refPoint.z < zmin: zmin=dep.refPoint.z
                if dep.refPoint.z > zmax: zmax=dep.refPoint.z
        self.refPointsBoundBoxSize = math.sqrt( (xmax-xmin)**2 + (ymax-ymin)**2 + (zmax-zmin)**2 )

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



    def move(self,doc):
        if self.tempfixed or self.fixed: return
        #
        #Linear moving of a rigid
        moveDist = Base.Vector(0,0,0)
        if self.moveVectorSum is not None:
            moveDist = Base.Vector(self.moveVectorSum)
            moveDist.multiply(WEIGHT_LINEAR_MOVE) # stabilize computation, adjust if needed...
            if self.debugMode == True:
                a2plib.drawDebugVectorAt(self.spinCenter, moveDist, a2plib.BLUE)
        #
        #Rotate the rigid...
        center = None
        rotation = None
        if (self.spin is not None and self.spin.Length != 0.0 and self.countSpinVectors != 0):
            savedSpin = copy.copy(self.spin)
            spinAngle = self.spin.Length / self.countSpinVectors
            if spinAngle>15.0: spinAngle=15.0 # do not accept more degrees
            try:
                spinStep = spinAngle/(SPINSTEP_DIVISOR) #it was 250.0
                self.spin.multiply(1.0e12)
                self.spin.normalize()
                rotation = FreeCAD.Rotation(self.spin, spinStep)
                center = self.spinCenter
                if self.debugMode == True:
                    a2plib.drawDebugVectorAt(center, savedSpin, a2plib.RED)
            except:
                pass

        if center is not None and rotation is not None:
            pl = FreeCAD.Placement(moveDist,rotation,center)
            self.applyPlacementStep(pl)
        else:
            if moveDist.Length > 1e-8:
                pl = FreeCAD.Placement()
                pl.move(moveDist)
                self.applyPlacementStep(pl)

    def currentDOF(self):
        """
        update whole DOF of the rigid (useful for animation and get the number
        useful to determine if an object is fully constrained.
        """
        self.pointConstraints = []
        _dofPos = a2p_libDOF.initPosDOF
        _dofRot = a2p_libDOF.initRotDOF
        self.reorderDependencies()
        if not self.fixed:
            if len(self.dependencies) > 0:
                for x in self.dependencies:
                    _dofPos, _dofRot = x.calcDOF(_dofPos,_dofRot, self.pointConstraints)
        else:
            _dofPos, _dofRot = [] , []
        self.posDOF = _dofPos
        self.rotDOF = _dofRot
        self.currentDOFCount = len(self.posDOF) + len(self.rotDOF)
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
        _dofPos = a2p_libDOF.initPosDOF
        _dofRot = a2p_libDOF.initRotDOF
        self.reorderDependencies()
        if len(self.dependencies) > 0:
            for dep in self.dependencies:
                if dep.dependedRigid.tempfixed:
                    _dofPos, _dofRot = dep.calcDOF(_dofPos,_dofRot, self.pointConstraints)
        else:
            return False
        if len(_dofPos) + len(_dofRot):
            return False
        else:
            return True

    def linkedTempFixedDOF(self):
        #pointConstraints = []
        _dofPos = a2p_libDOF.initPosDOF
        _dofRot = a2p_libDOF.initRotDOF
        self.reorderDependencies()
        if not self.tempfixed:
            if len(self.dependencies) > 0:
                for x in self.dependencies:
                    if x.dependedRigid.tempfixed:
                        _dofPos, _dofRot = x.calcDOF(_dofPos,_dofRot, self.pointConstraints)
        else:
            _dofPos, _dofRot = [] , []
        return len(_dofPos) + len(_dofRot)

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
