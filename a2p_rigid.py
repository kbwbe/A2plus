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

from a2plib import (
    PARTIAL_SOLVE_STAGE1,
    PARTIAL_SOLVE_STAGE2, 
    PARTIAL_SOLVE_STAGE3,
    PARTIAL_SOLVE_STAGE4,
    PARTIAL_SOLVE_STAGE5,
    PARTIAL_SOLVE_END
    )

from a2p_libDOF import (
    SystemOrigin,
    SystemXAxis,
    SystemYAxis,
    SystemZAxis
    )
import os, sys


SPINSTEP_DIVISOR = 12.0
WEIGHT_LINEAR_MOVE = 0.5
WEIGHT_REFPOINT_ROTATION = 8.0



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
        self.maxAxisError = 0.0
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
            d.Done = False
            d.disable()

    def countDependencies(self):
        return len(self.dependencies)
            
    def enableDependencies(self, workList):
        for dep in self.dependencies:
            dep.enable(workList)

    # The function only sets parentship for childrens that are distant+1 from fixed rigid
    # The function should be called in a loop with increased distance until it return False
    def assignParentship(self, distance):
        #FreeCAD.Console.PrintMessage((self.disatanceFromFixed*3)*" ")
        #FreeCAD.Console.PrintMessage("In {}:{}, distance {}\n".format(self.label, self.disatanceFromFixed, distance))
        # Current rigid was already set, pass the call to childrens
        '''if self.disatanceFromFixed < distance:
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
'''

    def printHierarchy(self, level):
        Msg((level*3)*" ")
        Msg("{} - distance {}\n".format(self.label, self.disatanceFromFixed))
        for rig in self.childRigids:
            rig.printHierarchy(level+1)

    def getCandidates(self, solverStage = None):
        candidates = []
        
        if solverStage == PARTIAL_SOLVE_STAGE1:
            for linkedRig in self.linkedRigids:
                if linkedRig.linkedTempFixedDOF()==0: #found a fully constrained obj to tempfixed rigids
                    for dep in self.depsPerLinkedRigids[linkedRig]: 
                        #enable involved dep
                        if not dep.Done:
                            dep.enable([dep.currentRigid, dep.dependedRigid])
                            #self.solvedCounter += 1
                    if linkedRig.tempfixed: continue
                    candidates.append(linkedRig)
                    
        return candidates #FIXME, not ready...
    
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

    def checkIfAllDone(self):
        for dep in self.dependencies:
            if not dep.Done: return False
        return True

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
            if dep.Enabled:  #handle only enable constraints
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

        if absPosMove >= solver.mySOLVER_POS_ACCURACY*1e-2 or angle >= solver.mySOLVER_SPIN_ACCURACY*1e-1:
            ob1 = doc.getObject(self.objectName)
            ob1.Placement = self.placement

    def getRigidCenter(self):
        _currentRigid = FreeCAD.ActiveDocument.getObject(self.objectName)
        #print "rigidCenter = ", _currentRigid.Shape.BoundBox.Center
        return _currentRigid.Shape.BoundBox.Center
    
    def calcSpinCenter(self):
        newSpinCenter = Base.Vector(0,0,0)
        countRefPoints = 0
        for dep in self.dependencies:
            if dep.Enabled:  #handle only enabled constraints
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
        if self.tempfixed or self.fixed or not self.checkIfInvolved(): return
        
        #print "cqalmovedata"     
        depRefPoints = []
        depMoveVectors = [] #collect Data to compute central movement of rigid
        #
        self.maxPosError = 0.0
        self.maxAxisError = 0.0
        self.countSpinVectors = 0
        self.moveVectorSum = Base.Vector(0,0,0)

        for dep in self.dependencies:
            if dep.Enabled:  #handle only enable constraints
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
                if dep.Enabled:  #handle only enable constraints
                    rotation = dep.getRotation(solver)
    
                    if rotation is None: continue       # No rotation for that dep
    
                    
    
                    # Accumulate all rotations for later average calculation
                    self.spin = self.spin.add(rotation)
                    self.countSpinVectors += 1
                    
                    # Calculate max rotation error
                    axisErr = self.spin.Length
                    if axisErr > self.maxAxisError : self.maxAxisError = axisErr

    def move(self,doc):
        if self.tempfixed or self.fixed or not self.checkIfInvolved(): return
        #print 'move'
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


    def checkIfInvolved(self):
        '''
        check if the rigid has some dependencies enabled
        '''
        for dep in self.dependencies:
            if dep.Enabled:
                return True
        return False
    
    def currentDOF(self):
        '''
        update whole DOF of the rigid (useful for animation and get the number
        useful to determine if an object is fully constrained    
        '''
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
    
    def linkedTempFixedDOF(self):
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
        #print  self.label , len(_dofPos) + len(_dofRot)  
        return len(_dofPos) + len(_dofRot)
    
    def reorderDependencies(self):
        '''
        place all kind of pointconstraints at the end
        of the dependencies list
        '''
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
        '''
        pretty print output that describe the current DOF of the rigid
        '''
        Msg('\n')
        Msg("Current Rigid = {}\n".format(self.label) )
        if self.fixed:
            Msg("    is Fixed\n")
        else:
            Msg("    is not Fixed and has {} DegreesOfFreedom\n".format(self.currentDOF()))
        for rig in self.depsPerLinkedRigids.keys():
            Msg("    Depends on Rigid = {}\n".format(rig.label))
            for dep in self.depsPerLinkedRigids[rig]:
                Msg("        {}\n".format(dep) )
            Msg("        DOF Position free with this rigid = {}\n".format( len(self.dofPOSPerLinkedRigids[rig])))
            Msg("        DOF Rotation free with this rigid = {}\n".format( len(self.dofROTPerLinkedRigids[rig])))





