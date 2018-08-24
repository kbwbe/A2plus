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
        self.objectName = [name]
        self.label = label
        self.fixed = fixed
        self.tempfixed = fixed
        self.placement = [placement]
        self.savedPlacement = [placement]
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
        self.calcSpinCenter()
        self.calcRefPointsBoundBoxSize()
        for d in self.dependencies:
            d.Done = False
            d.disable()

    def countDependencies(self):
        return len(self.dependencies)
    
    def countDependenciesEnabled(self):
        counter = 0
        for dep in self.dependencies:
            if dep.Enabled:
                counter+=1
        return counter
            
    def enableDependencies(self, workList):
        for dep in self.dependencies:
            dep.enable(workList)
            #dep.calcRefPoints(dep.index)

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
        
        if solverStage == PARTIAL_SOLVE_STAGE1:
            if not self.tempfixed: #skip already fixed objs
                #print 'current dof = ', rig.currentDOF()
                DebugMsg(A2P_DEBUG_1, "    eval {}\n".format(self.label))
                
                if self.linkedTempFixedDOF()==0: #found a fully constrained obj to tempfixed rigids
                    for j in self.depsPerLinkedRigids.keys(): #look on each linked obj
                        if j.tempfixed: #the linked rigid is already fixed
                            for dep in self.depsPerLinkedRigids[j]: 
                                #enable involved dep
                                if not dep.Done and not dep.Enabled:
                                    #dep.enable([dep.currentRigid, dep.dependedRigid])
                                    candidates.extend([dep.currentRigid, dep.dependedRigid])                                        
                                    DebugMsg(A2P_DEBUG_1, "        {}\n".format(dep))
                    #if len(outputRigidList)>0: #found something!
                        #print '        Solve them!'                            
            
                    
        elif solverStage == PARTIAL_SOLVE_STAGE2:  
            #solve all rigid constrained ONLY to tempfixed rigid, 
            #enable only involved dep, then set them as tempfixed        
            
            if not self.tempfixed: #skip already fixed objs  
                DebugMsg(A2P_DEBUG_1, "    eval {}\n".format(self.label))                
                if self.areAllParentTempFixed(): #linked only to fixed rigids                                                
                    
                    #print rig.linkedRigids 
                    if not self.checkIfAllDone():                              
                        #all linked rigid are tempfixed, so solve it now    
                        #print rig.label
                        for j in self.depsPerLinkedRigids.keys(): #look again on each linked obj
                            #outputRigidList.append(j)
                            #print 'Rigid ', j.label
                            for dep in self.depsPerLinkedRigids[j]: 
                                
                                #enable involved dep
                                if not dep.Done and not dep.Enabled:
                                    #dep.enable([dep.currentRigid, dep.dependedRigid])
                                    candidates.extend([dep.currentRigid, dep.dependedRigid])
                                    #self.solvedCounter += 1
                                    DebugMsg(A2P_DEBUG_1, "        {}\n".format(dep))
            
        
        elif solverStage == PARTIAL_SOLVE_STAGE3:
            if not self.tempfixed:
                for rig in self.linkedRigids:
                    if not rig.tempfixed:
                        if (len(self.dofPOSPerLinkedRigids[rig]) + len(self.dofROTPerLinkedRigids[rig])) == 0:
                            #rig is fully constrained 
                            candidates.append(self)
                            candidates.append(rig)
                            return candidates 
                
            return candidates
            
            
            #pass

        elif solverStage == PARTIAL_SOLVE_STAGE4:
            pass

        elif solverStage == PARTIAL_SOLVE_STAGE5:
            if not self.checkIfAllDone():
                candidates.extend([self])
                

        #candidates = list(set(candidates))
        return candidates#something match, return it to solver
    
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
        for ind in range(len(self.placement)):
            self.placement[ind] = pl.multiply(self.placement[ind])
            self.spinCenter = pl.multVec(self.spinCenter)
        # Update dependencies
        for dep in self.dependencies:
            dep.applyPlacement(pl)
            #dep.calcRefPoints(dep.index)

    def clear(self):
        for d in self.dependencies:
            d.clear()
        self.dependencies = []
        self.superRigid = None
    
    def returnIfsolved(self):
        if self.tempfixed: 
        #if self.fixed:
            return True
        else:
            return False

    def applySolution(self, doc, solver):
        #if self.returnIfsolved(): return
        if self.fixed: return

        # Update FreeCAD's placements if deltaPlacement above Tolerances
        for ind in range(len(self.placement)):
        
            base1 = self.placement[ind].Base
            base2 = self.savedPlacement[ind].Base
            absPosMove = base1.sub(base2).Length

            axis1 = self.placement[ind].Rotation.Axis
            axis2 = self.savedPlacement[ind].Rotation.Axis
            angle = math.degrees(axis2.getAngle(axis1))

            if absPosMove >= solver.mySOLVER_POS_ACCURACY * 0.1 or angle >= solver.mySOLVER_SPIN_ACCURACY * 0.1:
                #for objname in self.objectName:
                obj = doc.getObject(self.objectName[ind])            
                obj.Placement = self.placement[ind]

    def getRigidCenter(self):
        _currentRigid = FreeCAD.ActiveDocument.getObject(self.objectName[0])
        return _currentRigid.Shape.BoundBox.Center
    
    def calcSpinCenterDepsEnabled(self):
        newSpinCenter = Base.Vector(self.spinCenter)
        countRefPoints = 0
        for dep in self.dependencies:
            if dep.Enabled:
                if dep.refPoint != None:
                    newSpinCenter = newSpinCenter.add(dep.refPoint)
                    countRefPoints += 1
        if countRefPoints > 0:
            newSpinCenter.multiply(1.0/countRefPoints)
            self.spinCenter = newSpinCenter
    
#     def calcSpinBasicDataDepsEnabled(self):
#         xmin = 0
#         xmax = 0
#         ymin = 0
#         ymax = 0
#         zmin = 0
#         zmax = 0
#         for dep in self.dependencies:
#             if dep.Enabled:
#                 if dep.refPoint.x < xmin: xmin=dep.refPoint.x
#                 if dep.refPoint.x > xmax: xmax=dep.refPoint.x
#                 if dep.refPoint.y < ymin: ymin=dep.refPoint.y
#                 if dep.refPoint.y > ymax: ymax=dep.refPoint.y
#                 if dep.refPoint.z < zmin: zmin=dep.refPoint.z
#                 if dep.refPoint.z > zmax: zmax=dep.refPoint.z
#         self.refPointsBoundBoxSize = math.sqrt( (xmax-xmin)**2 + (ymax-ymin)**2 + (zmax-zmin)**2 )
#         x = (xmax+xmin)/2.0
#         y = (ymax+ymin)/2.0
#         z = (zmax+zmin)/2.0
#         self.spinCenter = Base.Vector(x,y,z)
    
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

    def calcBoundBoxSize(self, doc):
        xmin = 0
        xmax = 0
        ymin = 0
        ymax = 0
        zmin = 0
        zmax = 0
        for objname in self.objectName:
            obj = doc.getObject(objname)
            xmin = min(xmin,obj.Shape.BoundBox.XMin)
            xmax = max(xmax,obj.Shape.BoundBox.XMax)
            ymin = min(ymin,obj.Shape.BoundBox.YMin)
            ymax = max(ymax,obj.Shape.BoundBox.YMax)
            zmin = min(zmin,obj.Shape.BoundBox.ZMin)
            zmax = max(zmax,obj.Shape.BoundBox.ZMax)        
        return [xmin,xmax,ymin,ymax,zmin,zmax]
    
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
        if self.tempfixed: return
        
        
        depRefPoints = []
        depMoveVectors = [] #collect Data to compute central movement of rigid
        #
        self.maxPosError = 0.0
        self.maxAxisError = 0.0
        self.countSpinVectors = 0
        self.moveVectorSum = Base.Vector(0,0,0)

        for dep in self.dependencies:
            if dep.Enabled:
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
                if dep.Enabled:
                    rotation = dep.getRotation(solver)
    
                    if rotation is None: continue       # No rotation for that dep
    
                    # Accumulate all rotations for later average calculation
                    self.spin = self.spin.add(rotation)
                    self.countSpinVectors += 1
    
                    # Calculate max rotation error
                    axisErr = self.spin.Length
                    if axisErr > self.maxAxisError : self.maxAxisError = axisErr

    def move(self,doc):
        if self.tempfixed: return
        
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
        self.pointConstraints = []
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
            Msg("    Depends on Rigid = {} fixed = {}\n".format(rig.label,rig.tempfixed))
            for dep in self.depsPerLinkedRigids[rig]:
                Msg("        {}\n".format(dep) )
            Msg("        DOF Position free with this rigid = {}\n".format( len(self.dofPOSPerLinkedRigids[rig])))
            Msg("        DOF Rotation free with this rigid = {}\n".format( len(self.dofROTPerLinkedRigids[rig])))


    def mergeRigid(self, solver, rigid):
        #function which includes a rigid in another
        
        #first insert the rigid object name in the current objectname
        if rigid.objectName in self.objectName or self.objectName in rigid.objectName:
            return
        self.objectName.extend(rigid.objectName)
        
        #print '    merge ', rigid.label , ' in ', self.label
        self.label += '#' + rigid.label
        self.placement.extend(rigid.placement)
        self.savedPlacement.extend(rigid.savedPlacement)
        
        #now merge all dependencies
        self.dependencies.extend(rigid.dependencies)
        commondependencies = []
        for dep in self.dependencies:
            if dep.dependedRigid == self or dep.dependedRigid == rigid:
                commondependencies.append(dep)
                
        for dep in commondependencies:
            self.dependencies.remove(dep)
        for dep in self.dependencies: 
            if dep.currentRigid == rigid:
                dep.currentRigid = self
                dep.foreignDependency.dependedRigid = self
                #dep.setCurrentRigid(self)          
            #print '        ', dep
        
        
        self.linkedRigids.extend(rigid.linkedRigids)
        self.linkedRigids.remove(self)
        self.linkedRigids.remove(rigid)
        self.dofPOSPerLinkedRigids.update(rigid.dofPOSPerLinkedRigids)
        del self.dofPOSPerLinkedRigids[self]
        del self.dofPOSPerLinkedRigids[rigid]
        self.dofROTPerLinkedRigids.update(rigid.dofROTPerLinkedRigids)
        del self.dofROTPerLinkedRigids[self]
        del self.dofROTPerLinkedRigids[rigid]
        
        for rig in solver.rigids:
            for ind in range(len(rig.linkedRigids)):
                if rig.linkedRigids[ind] == rigid:
                    rig.linkedRigids[ind] = self
            rig.linkedRigids = list(set(rig.linkedRigids))

            for ind in range(len(rig.dofPOSPerLinkedRigids)):
                if rigid in rig.dofPOSPerLinkedRigids.keys():
                    rig.dofPOSPerLinkedRigids[self] = rig.dofPOSPerLinkedRigids[rigid]
                    del rig.dofPOSPerLinkedRigids[rigid]
                    
            for ind in range(len(rig.dofROTPerLinkedRigids)):
                if rigid in rig.dofROTPerLinkedRigids.keys():
                    rig.dofROTPerLinkedRigids[self] = rig.dofROTPerLinkedRigids[rigid]
                    del rig.dofROTPerLinkedRigids[rigid]
                    
        solver.rigids.remove(rigid)
