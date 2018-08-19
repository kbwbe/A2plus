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
    A2P_MOVIMODE,
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

from a2plib import (
    PARTIAL_SOLVE_STAGE1,
    PARTIAL_SOLVE_STAGE2, 
    PARTIAL_SOLVE_STAGE3,
    PARTIAL_SOLVE_STAGE4,
    PARTIAL_SOLVE_STAGE5,
    PARTIAL_SOLVE_END
    )

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
        
        for rig in self.rigids:
            rig.hierarchyLinkedRigids.extend(rig.linkedRigids)
               
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
                
        for rig in self.rigids:
            rig.calcSpinCenter()
            rig.calcRefPointsBoundBoxSize()
            
        numdep = 0
        self.retrieveDOFInfo() #function only once used here at this place in whole program
        for rig in self.rigids:
            rig.currentDOF()
            #rig.beautyDOFPrint()
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
                     
            #if not rig.tempfixed:  #skip already fixed objs

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
        #modified hierarchy file name and path, now the html file is in the same folder with the same filename of the assembly
        out_file = os.path.splitext(self.doc.FileName)[0] + '_asm_hierarchy.html'
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
        self.partialSolverCurrentStage = PARTIAL_SOLVE_STAGE1

    def solveAccuracySteps(self,doc):
        self.level_of_accuracy=1

        startTime = int(round(time.time() * 1000))
        self.loadSystem(doc)
        if self.status == "loadingDependencyError":
            return
        self.assignParentship(doc)
        loadTime = int(round(time.time() * 1000))
        while True:
            systemSolved = self.calculateChain(doc)
            totalTime = int(round(time.time() * 1000))
            DebugMsg(A2P_DEBUG_1, "Total steps used: %d\n" %  self.stepCount)
            DebugMsg(A2P_DEBUG_1, "LoadTime (ms): %d\n" % (loadTime - startTime) )
            DebugMsg(A2P_DEBUG_1, "CalcTime (ms): %d\n" % (totalTime - loadTime) )
            DebugMsg(A2P_DEBUG_1, "TotalTime (ms): %d\n" % (totalTime - startTime) )
            if systemSolved:
                self.mySOLVER_SPIN_ACCURACY *= 1e-1
                self.mySOLVER_POS_ACCURACY *= 1e-1
                Msg( '--->SOLVED WITH LEVEL OF ACCURACY :{}\n'.format(self.level_of_accuracy) )
                self.level_of_accuracy+=1
                if self.level_of_accuracy == MAX_LEVEL_ACCURACY:
                    self.solutionToParts(doc)
                    break
                #self.prepareRestart()
                self.solutionToParts(doc)
                self.loadSystem(doc)
            else:
                self.solutionToParts(doc)
                break
        self.mySOLVER_SPIN_ACCURACY = SOLVER_SPIN_ACCURACY
        self.mySOLVER_POS_ACCURACY = SOLVER_POS_ACCURACY
        return systemSolved

    def solveSystem(self,doc):
        Msg( "\n===== Start Solving System ====== \n" )
        Msg( "Solvermode = partial + recursive unfixing!\n")
        mode = 'partial'

        systemSolved = self.solveAccuracySteps(doc)
        if self.status == "loadingDependencyError":
            return

        if not systemSolved:
            Msg( "Could not solve system, try a reload()\n" )
            systemSolved = self.solveAccuracySteps(doc)
        if systemSolved:
            self.status = "solved"
            Msg( "===== System solved using partial + recursive unfixing =====")
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

    def calculateChain(self, doc):
        self.stepCount = 0
        
        # mode is 'partial' now definitely!
        workList = []

        # load initial worklist with all fixed parts...
        for rig in self.rigids:
            if rig.fixed:
                workList.append(rig);
        self.printList("Initial-Worklist", workList)

        while True:
            addList = []
            for rig in workList:
                addList.extend(rig.getCandidates())
            addList = set(addList)
            self.printList("AddList", addList)
            if len(addList) > 0:
                workList.extend(addList)
                solutionFound = self.calculateWorkList(doc, workList)
                if not solutionFound: return False
            else:
                break

        return True

    def calculateWorkList(self, doc, workList):
        reqPosAccuracy = self.mySOLVER_POS_ACCURACY
        reqSpinAccuracy = self.mySOLVER_SPIN_ACCURACY

        for rig in workList:
            rig.enableDependencies(workList)
        for rig in workList:
            rig.calcSpinBasicDataDepsEnabled()

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
                w.calcMoveData(doc, self)
                if w.maxPosError > maxPosError:
                    maxPosError = w.maxPosError
                if w.maxAxisError > maxAxisError:
                    maxAxisError = w.maxAxisError

            # Perform the move
            for w in workList:
                w.move(doc)

            # The accuracy is good, apply the solution to FreeCAD's objects
            if (maxPosError <= reqPosAccuracy and
                maxAxisError <= reqSpinAccuracy):
                # The accuracy is good, we're done here
                goodAccuracy = True
                # Mark the rigids as tempfixed and add its constrained rigids to pending list to be processed next
                DebugMsg(A2P_DEBUG_1, "{} counts \n".format(calcCount) )
                for r in workList:
                    r.applySolution(doc, self)
                    r.tempfixed = True

            if self.convergencyCounter > SOLVER_STEPS_CONVERGENCY_CHECK:
                if (
                    maxPosError  >= self.lastPositionError or
                    maxAxisError >= self.lastAxisError
                    ):
                    enlargedWorkList = False
                    # search for unsolved dependencies...
                    tempfixedRigids = []
                    for rig in workList:
                        if rig.tempfixed: tempfixedRigids.append(rig)
                    for rig in workList:
                        if rig.fixed or rig.tempfixed: continue
                        if rig.maxAxisError >= maxAxisError or rig.maxPosError >= maxPosError:
                            for r in rig.linkedRigids:
                                r.tempfixed = False
                                if r in tempfixedRigids:
                                    Msg("unfixed Rigid {}\n".format(r.label))
                                    enlargedWorkList = True
                    
                    if enlargedWorkList:
                        self.lastPositionError = SOLVER_CONVERGENCY_ERROR_INIT_VALUE
                        self.lastAxisError = SOLVER_CONVERGENCY_ERROR_INIT_VALUE
                        self.convergencyCounter = 0
                        Msg("restart with some unfixed parts\n")
                        tempfixedRigids = []
                        for rig in workList:
                            if rig.tempfixed: tempfixedRigids.append(rig)
                        self.printList("temfixed parts:", tempfixedRigids)
                        unfixedRigids = []
                        for rig in workList:
                            if not rig.tempfixed: unfixedRigids.append(rig)
                        self.printList("unfixed parts:", unfixedRigids)
                        Msg("\n")
                        
                        continue
                    else:            
                        Msg('\n')
                        Msg('convergency-conter: {}\n'.format(self.convergencyCounter))
                        Msg( "System not solvable, convergency is incorrect!\n" )
                        return False
                
                
                
                self.lastPositionError = maxPosError
                self.lastAxisError = maxAxisError
                self.convergencyCounter = 0

            if self.stepCount > SOLVER_MAXSTEPS:
                Msg( "Reached max calculations count ({})\n".format(SOLVER_MAXSTEPS) )
                return False
        return True

    def solutionToParts(self,doc):
        for rig in self.rigids:
            rig.applySolution(doc, self);

#------------------------------------------------------------------------------
def solveConstraints_OperationalMode( doc, cache=None ):
    '''
    Normal solving. Parts are moved according
    required level of accuracy
    '''
    doc.openTransaction("a2p_systemSolving")
    ss = SolverSystem()
    ss.solveSystem(doc)
    doc.commitTransaction()

def solveConstraints_MoviMode( doc, cache=None ):
    '''
    Test solving mode. Solver does only some steps.
    You can view the movement of parts on screen.
    Used for approving correct function of dependencies
    '''
    doc.openTransaction("a2p_systemSolving")
    ss = SolverSystem()
    ss.loadSystem(doc)
    for rig in ss.rigids:
        rig.enableDependencies(ss.rigids)
    for i in range(0,10):
        for r in ss.rigids:
            r.calcMoveData(doc, ss)
        for r in ss.rigids:
            r.move(doc)
            # Enable those 2 lines to see the computation progress on screen
            r.applySolution(doc, ss)
            FreeCADGui.updateGui()
    doc.commitTransaction()
    
def solveConstraints( doc, cache=None ):
    if A2P_MOVIMODE: #visual solver testmode, some visual solversteps on screen
        solveConstraints_MoviMode(doc, cache=None)
    else:
        solveConstraints_OperationalMode(doc, cache=None) #Normal solver mode

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
