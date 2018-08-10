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
from a2p_dependencies import Dependency
from a2p_rigid import Rigid
import os, sys
from os.path import expanduser


SOLVER_MAXSTEPS = 300000
SOLVER_POS_ACCURACY = 1.0e-1  # gets to smaller values during solving
SOLVER_SPIN_ACCURACY = 1.0e-1 # gets to smaller values during solving

SOLVER_STEPS_CONVERGENCY_CHECK = 1000
SOLVER_CONVERGENCY_ERROR_INIT_VALUE = 1.0e+20
MAX_LEVEL_ACCURACY = 4  #accuracy reached is 1.0e-MAX_LEVEL_ACCURACY

PARTIAL_SOLVE_STAGE1 = 1    #solve all rigid fully constrained to tempfixed rigid, enable only involved dep, then set them as tempfixed
PARTIAL_SOLVE_STAGE2 = 2    #solve all rigid constrained only to tempfixed rigids, it doesn't matter if fully constrained or not. in case more than one tempfixed rigid
PARTIAL_SOLVE_STAGE3 = 3    #repeat stage 1 and stage2 as there are rigids that match
PARTIAL_SOLVE_STAGE4 = 4    #look for block of rigids, if a rigid is fully constrained to one rigid, solve them and create a superrigid (disabled at the moment)
PARTIAL_SOLVE_STAGE5 = 5    #take all remaining rigid and dependencies not done and try to solve them all together
PARTIAL_SOLVE_END = 6

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
        self.lastPositionError = SOLVER_CONVERGENCY_ERROR_INIT_VALUE
        self.lastAxisError = SOLVER_CONVERGENCY_ERROR_INIT_VALUE
        self.convergencyCounter = 0
        self.status = "created"
        self.partialSolverCurrentStage = 0
        self.currentstage = 0
        self.solvedCounter = 0

    def clear(self):
        for r in self.rigids:
            r.clear()
        self.stepCount = 0
        self.rigids = []
        self.constraints = []
        self.objectNames = []
        self.partialSolverCurrentStage = PARTIAL_SOLVE_STAGE1

    def getRigid(self,objectName):
        '''get a Rigid by objectName'''
        rigs = [r for r in self.rigids if r.objectName == objectName]
        if len(rigs) > 0: return rigs[0]
        return None

    def loadSystem(self,doc):
        self.clear()
        self.doc = doc
        self.status = "loading"
        #
        self.convergencyCounter = 0
        self.lastPositionError = SOLVER_CONVERGENCY_ERROR_INIT_VALUE
        self.lastAxisError = SOLVER_CONVERGENCY_ERROR_INIT_VALUE
        #
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
        deleteList = [] # a list to collect broken constraints
        for c in self.constraints:
            rigid1 = self.getRigid(c.Object1)
            rigid2 = self.getRigid(c.Object2)
            
            #create and update list of constrained rigids
            if rigid2 != None and not rigid2 in rigid1.linkedRigids: rigid1.linkedRigids.append(rigid2);
            if rigid1 != None and not rigid1 in rigid2.linkedRigids: rigid2.linkedRigids.append(rigid1);
            
            try:
                Dependency.Create(doc, c, self, rigid1, rigid2)
            except:
                self.status = "loadingDependencyError"
                deleteList.append(c)
                
        if len(deleteList) > 0:
            msg = "The following constraints are broken:\n"
            for c in deleteList:
                msg += "{}\n".format(c.Label)
            msg += "Do you want to delete them ?"

            flags = QtGui.QMessageBox.StandardButton.Yes | QtGui.QMessageBox.StandardButton.No
            response = QtGui.QMessageBox.critical(
                QtGui.QApplication.activeWindow(),
                "Delete broken constraints?",
                msg,
                flags
                )
            if response == QtGui.QMessageBox.Yes:
                for c in deleteList:
                    a2plib.removeConstraint(c)
        
        if self.status == "loadingDependencyError":
            return
        
        rig.reorderDependencies()
        for rig in self.rigids:
            
            rig.calcSpinCenter()
            rig.calcRefPointsBoundBoxSize()
        numdep = 0
        self.retrieveDOFInfo() #function only once used here at this place in whole program
        for rig in self.rigids:
            rig.currentDOF()
            rig.beautyDOFPrint()
            numdep+=rig.countDependencies()
        Msg( 'there are {} dependencies\n'.format(numdep/2))       
        self.status = "loaded"

    
    def retrieveDOFInfo(self):
        '''
        method used to retrieve all info related to DOF handling
        the method scans each rigid, and on each not tempfixed rigid scans the list of linkedobjects
        then for each linked object compile a dict where each linked object has its dependencies
        then for each linked object compile a dict where each linked object has its dof position
        then for each linked object compile a dict where each linked object has its dof rotation
        '''
        for rig in self.rigids:            
            if not rig.tempfixed:  #skip already fixed objs
                for linkedRig in rig.linkedRigids:
                    tmplinkedDeps = []
                    tmpLinkedPointDeps = []
                    for dep in rig.dependencies:
                        if linkedRig==dep.dependedRigid:
                            #be sure pointconstraints are at the end of the list
                            if dep.isPointConstraint :
                                tmpLinkedPointDeps.append(dep)
                            else:
                                tmplinkedDeps.append(dep)
                    #add at the end the point constraints
                    tmplinkedDeps.extend(tmpLinkedPointDeps) 
                    rig.depsPerLinkedRigids[linkedRig] = tmplinkedDeps
            
                #dofPOSPerLinkedRigid is a dict where for each 
                for linkedRig in rig.depsPerLinkedRigids.keys():
                    linkedRig.pointConstraints = []
                    _dofPos = linkedRig.posDOF
                    _dofRot = linkedRig.rotDOF
                    for dep in rig.depsPerLinkedRigids[linkedRig]:
                        _dofPos, _dofRot = dep.calcDOF(_dofPos,_dofRot, linkedRig.pointConstraints)
                    rig.dofPOSPerLinkedRigids[linkedRig] = _dofPos
                    rig.dofROTPerLinkedRigids[linkedRig] = _dofRot
            
            #ok each rigid has a dict for each linked objects,
            #so we now know the list of linked objects and which 
            #dof rot and pos both limits.
            


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

        if A2P_DEBUG_LEVEL > 0:
            Msg(20*"=" + "\n")
            Msg("Hierarchy:\n")
            Msg(20*"=" + "\n")
            for rig in self.rigids:
                if rig.fixed: rig.printHierarchy(0)
            Msg(20*"=" + "\n")

        self.visualizeHierarchy()

    def visualizeHierarchy(self):
        home = expanduser("~")
        out_file = os.path.join(home,'assembly_hierarchy.html')
        Msg("Writing visual hierarchy to: {}\n".format(out_file))
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

    def solveSystemWithMode(self,doc, mode):
        self.level_of_accuracy=1

        startTime = int(round(time.time() * 1000))
        self.loadSystem(doc)
        if self.status == "loadingDependencyError":
            return
        self.assignParentship(doc)
        loadTime = int(round(time.time() * 1000))
        while True:
            systemSolved = self.calculateChain(doc, mode)
            totalTime = int(round(time.time() * 1000))
            DebugMsg(A2P_DEBUG_1, "Total steps used: %d\n" %  self.stepCount)
            DebugMsg(A2P_DEBUG_1, "LoadTime (ms): %d\n" % (loadTime - startTime) )
            DebugMsg(A2P_DEBUG_1, "CalcTime (ms): %d\n" % (totalTime - loadTime) )
            DebugMsg(A2P_DEBUG_1, "TotalTime (ms): %d\n" % (totalTime - startTime) )
            if systemSolved:
                self.mySOLVER_SPIN_ACCURACY *= 1e-1
                self.mySOLVER_POS_ACCURACY *= 1e-1
                self.level_of_accuracy+=1
                if self.level_of_accuracy == MAX_LEVEL_ACCURACY:
                    self.solutionToParts(doc)
                    break
                self.prepareRestart()
            else:
                break
        self.mySOLVER_SPIN_ACCURACY = SOLVER_SPIN_ACCURACY
        self.mySOLVER_POS_ACCURACY = SOLVER_POS_ACCURACY
        return systemSolved

    def solveSystem(self,doc):
        Msg( "\n===== Start Solving System ====== \n" )
        if a2plib.isPartialProcessing():
            Msg( "Solvermode = partialProcessing !\n")
            mode = 'partial'
        else:
            Msg( "Solvermode = solve all Parts at once !\n")
            mode = 'magnetic'

        systemSolved = self.solveSystemWithMode(doc,mode)
        if self.status == "loadingDependencyError":
            return

        if not systemSolved and mode == 'partial':
            Msg( "Could not solve system with partial processing, switch to 'magnetic' mode  \n" )
            mode = 'magnetic'
            systemSolved = self.solveSystemWithMode(doc,mode)
        if systemSolved:
            
            self.status = "solved"
            Msg( "===== System solved ! ====== \n" )
        else:
            self.status = "unsolved"
            Msg( "===== Could not solve system ====== \n" )
            msg = \
    '''
    Constraints inconsistent. Cannot solve System.
    Please delete your last created constraint !
    '''
            QtGui.QMessageBox.information(
                QtGui.QApplication.activeWindow(),
                "Constraint mismatch",
                msg
                )



    def printList(self, name, l):
        Msg("{} = (".format(name))
        for e in l:
            Msg( "{} ".format(e.label) )
        Msg("):\n")

    def calculateChain(self, doc, mode):
        self.stepCount = 0
        haveMore = True
        workList = []
        workList.extend(self.rigids)
        
        if mode == 'partial':
            # start from fixed rigids and its children
            self.solvedCounter = 0
            while self.partialSolverCurrentStage != PARTIAL_SOLVE_END:
                print "evaluating stage = ", self.partialSolverCurrentStage
                print 'Tempfixed objs:'
                for i in self.rigids:
                    if i.tempfixed:
                        print '    ',i.label
                while True:
                    
                    if self.calculateChainByPartialStage(self.partialSolverCurrentStage)== False: 
                        break
                    else:
                        #print "found something to solve at stage = ", currentstage
                        #some rigid match stage 1, try solving
                        solutionFound = self.calculateWorkList(doc, workList, mode)
                        if not solutionFound: 
                            return False
                        else:
                            #partial system successfully solved, set as Done and disable
                            for rig in self.rigids:
                                for dep in rig.dependencies:
                                    if dep.Enabled:
                                        dep.Done = True
                                        dep.disable()
                                        #rig.tempfixed = True
                    
        else:
            #enable all dependencies, set all as done=false
            for rig in self.rigids:
                rig.tempfixed = rig.fixed
                for dep in rig.dependencies:
                    dep.Done = False
                    dep.Enabled = True
            
            solutionFound = self.calculateWorkList(doc, workList, mode)
            if not solutionFound: return False
        return True

    def calculateWorkList(self, doc, workList, mode):
        if A2P_DEBUG_LEVEL >= A2P_DEBUG_1:
            self.printList("WorkList", workList)

        #for rig in workList:
        #    rig.enableDependencies(workList)

        self.lastPositionError = SOLVER_CONVERGENCY_ERROR_INIT_VALUE
        self.lastAxisError = SOLVER_CONVERGENCY_ERROR_INIT_VALUE
        self.convergencyCounter = 0

        calcCount = 0
        goodAccuracy = False
        while not goodAccuracy:
            maxPosError = 0.0
            maxAxisError = 0.0

            calcCount += 1
            self.stepCount += 1
            self.convergencyCounter += 1
            # First calculate all the movement vectors
            for w in workList:
                if w.checkIfInvolved():
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
                DebugMsg(A2P_DEBUG_1, "{} counts \n".format(calcCount) )
                for r in workList:
                    if r.checkIfInvolved():
                        r.applySolution(doc, self)
                        if self.partialSolverCurrentStage == PARTIAL_SOLVE_STAGE1:
                            r.tempfixed = True
                        elif r.checkIfAllDone:
                            r.tempfixed = True

            if self.convergencyCounter > SOLVER_STEPS_CONVERGENCY_CHECK:
                if (
                    maxPosError  >= self.lastPositionError or
                    maxAxisError >= self.lastAxisError
                    ):
                    if mode == 'magnetic':
                        Msg( "System not solvable, convergency is incorrect!\n" )
                    return False
                self.lastPositionError = maxPosError
                self.lastAxisError = maxAxisError
                self.convergencyCounter = 0

            if self.stepCount > SOLVER_MAXSTEPS:
                if mode == 'magnetic':
                    Msg( "Reached max calculations count ({})\n".format(SOLVER_MAXSTEPS) )
                return False
        return True

    def solutionToParts(self,doc):
        for rig in self.rigids:
            rig.applySolution(doc, self);
            
    #method to find for rigid and dependencies according to current stage
    def calculateChainByPartialStage(self, currentstage): 
        outputRigidList = []       
        if currentstage == PARTIAL_SOLVE_STAGE1:  
            #solve all rigid fully constrained to tempfixed rigids, enable only involved dep, then set them as tempfixed        
            for rig in self.rigids:
                if not rig.tempfixed: #skip already fixed objs
                    #print 'current dof = ', rig.currentDOF()
                    #print rig.label
                    if rig.linkedTempFixedDOF()==0: #found a fully constrained obj to tempfixed rigids
                        
                        for j in rig.depsPerLinkedRigids.keys(): #look on each linked obj
                            if j.tempfixed: #the linked rigid is already fixed
                                outputRigidList.append(j)
                                for dep in rig.depsPerLinkedRigids[j]: 
                                    #enable involved dep
                                    if not dep.Done:
                                        dep.enable([dep.currentRigid, dep.dependedRigid])
                                        self.solvedCounter += 1
                                        print '        ',dep
                        if len(outputRigidList)>0: #found something!
                            print '        Solve them!'                            
                            return True #something match, return it to solver
            self.partialSolverCurrentStage = PARTIAL_SOLVE_STAGE2
            return False #nothing match, jump to next stage
         
        elif currentstage == PARTIAL_SOLVE_STAGE2:  
            #solve all rigid constrained ONLY to tempfixed rigid, 
            #enable only involved dep, then set them as tempfixed        
            for rig in self.rigids:
                if not rig.tempfixed: #skip already fixed objs                    
                    if rig.areAllParentTempFixed(): #linked only to fixed rigids                                                
                        #all linked rigid are tempfixed, so solve it now    
                        for j in rig.linkedRigids: #look again on each linked obj
                            outputRigidList.append(j)
                            for dep in rig.depsPerLinkedRigids[j]: 
                                #enable involved dep
                                if not dep.Done:
                                    dep.enable([dep.currentRigid, dep.dependedRigid])
                                    self.solvedCounter += 1
                                    print '        ',dep
                    if len(outputRigidList)>0: #found something!
                        print '        solve them!'
                        return True #something match
            if self.solvedCounter > 0:
                self.partialSolverCurrentStage = PARTIAL_SOLVE_STAGE1
                self.solvedCounter = 0
            else:
                self.partialSolverCurrentStage = PARTIAL_SOLVE_STAGE3
            return False #nothing match, jump to next stage                       
                            
        elif currentstage == PARTIAL_SOLVE_STAGE3:
            self.partialSolverCurrentStage = PARTIAL_SOLVE_STAGE4
            return False
        
        elif currentstage == PARTIAL_SOLVE_STAGE4:
            self.partialSolverCurrentStage = PARTIAL_SOLVE_STAGE5
            return False        
        
        elif currentstage == PARTIAL_SOLVE_STAGE5: 
            #enable all dep not marked as done
            tmpfound = False
            for rig in self.rigids:
                if not rig.tempfixed:
                    for dep in rig.dependencies:
                        if not dep.Done and not dep.Enabled:
                            dep.enable([dep.currentRigid, dep.dependedRigid])
                            print '        ',dep
                            tmpfound = True
            
            self.partialSolverCurrentStage = PARTIAL_SOLVE_END  
            return tmpfound
        else:
            return False
#------------------------------------------------------------------------------
def solveConstraints( doc, cache=None ):
    doc.openTransaction("a2p_systemSolving")
    ss = SolverSystem()
    ss.solveSystem(doc)
    doc.commitTransaction()
    try:
        doc.recompute()
    except:
        pass
    
def autoSolveConstraints( doc, cache=None):
    if not a2plib.getAutoSolveState():
        return
    solveConstraints(doc)

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
    DebugMsg(A2P_DEBUG_1, "Starting solveConstraints latest script...\n" )
    doc = FreeCAD.activeDocument()
    solveConstraints(doc)
