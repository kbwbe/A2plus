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


SOLVER_MAXSTEPS = 60000
SOLVER_POS_ACCURACY = 1.0e-1  # gets to smaller values during solving
#SOLVER_SPIN_ACCURACY = 1.0e-4 # gets to smaller values during solving

SOLVER_STEPS_CONVERGENCY_CHECK = 1000
SOLVER_CONVERGENCY_ERROR_INIT_VALUE = 1.0e+20
SOLVER_CONVERGENCY_FACTOR = 0.99
MAX_LEVEL_ACCURACY = 5  #accuracy reached is 1.0e-MAX_LEVEL_ACCURACY

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
        #self.mySOLVER_SPIN_ACCURACY = SOLVER_SPIN_ACCURACY
        self.mySOLVER_POS_ACCURACY = SOLVER_POS_ACCURACY
        self.lastPositionError = SOLVER_CONVERGENCY_ERROR_INIT_VALUE
        self.lastAxisError = SOLVER_CONVERGENCY_ERROR_INIT_VALUE
        self.convergencyCounter = 0
        self.status = "created"
        self.partialSolverCurrentStage = 0

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
        #igs = [r for r in self.rigids if r.objectName == objectName]
        rigs = [r for r in self.rigids if objectName in r.objectName]
        if len(rigs) > 0: return rigs[0]
        return None

    def loadSystem(self,doc):
        
        import sys;sys.path.append(r'C:\Users\Turro\.p2\pool\plugins\org.python.pydev.core_6.4.4.201807281807\pysrc')
        #import pydevd;pydevd.settrace()
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
            #rig.spinCenter = ob1.Shape.BoundBox.Center
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
            
        self.numdep = 0
        self.retrieveDOFInfo() #function only once used here at this place in whole program
        for rig in self.rigids:
            rig.currentDOF()
            #rig.beautyDOFPrint()
            self.numdep+=rig.countDependencies()
        Msg( 'there are {} dependencies\n'.format(self.numdep/2))       
        self.status = "loaded"
        self.calcSpinAccuracy()
        
        

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
        #import WebGui
        #str = "file://",out_file
        #WebGui.openBrowser(str.__str__()) 

#     def calcMoveData(self,doc):
#         for rig in self.rigids:
#             rig.calcMoveData(doc, self)
            
    def calcSpinAccuracy(self, init=False):
        #first find the max boundsize
        xmin = 0.0
        xmax = 0.0
        ymin = 0.0
        ymax = 0.0
        zmin = 0.0
        zmax = 0.0
        
        for rig in self.rigids:
            tmplist = rig.calcBoundBoxSize(self.doc)
            xmin = min(xmin,tmplist[0])
            xmax = max(xmax,tmplist[1])
            ymin = min(ymin,tmplist[2])
            ymax = max(ymax,tmplist[3])
            zmin = min(zmin,tmplist[4])
            zmax = max(zmax,tmplist[5])
        
        vec1 = Base.Vector(xmin,ymin,zmin)
        vec2 = Base.Vector(xmax,ymax,zmax)
        assemblysize = vec1.distanceToPoint(vec2)
        #print 'Assembly size = ', assemblysize
        #accuracydivider = 1000.0 * (10**self.level_of_accuracy)
        #for a in range(self.level_of_accuracy):
        #    accuracydivider*=10
        
        #self.mySOLVER_POS_ACCURACY= assemblysize / accuracydivider            
        self.mySOLVER_SPIN_ACCURACY = math.degrees(math.atan(self.mySOLVER_POS_ACCURACY / assemblysize))
        #self.mySOLVER_SPIN_ACCURACY = math.degrees(math.atan(1 / accuracydivider))
        #self.mySOLVER_SPIN_ACCURACY = self.mySOLVER_POS_ACCURACY
        
    def prepareRestart(self):
        #self.mySOLVER_POS_ACCURACY = SOLVER_POS_ACCURACY
        #self.calcSpinAccuracy()
        
        for rig in self.rigids:
            rig.prepareRestart()
        #self.partialSolverCurrentStage = PARTIAL_SOLVE_STAGE1

    def solveSystemWithMode(self,doc):
        self.level_of_accuracy=1
        startTime = int(round(time.time() * 1000))
        self.loadSystem(doc)
        if self.status == "loadingDependencyError":
            return
        
        #self.progress_bar.start("Solving Assembly...",(self.numdep/2)*(MAX_LEVEL_ACCURACY-1)+1)  
        
        #self.progress_bar.next()
        
        self.assignParentship(doc)
        #self.prepareRestart()
        loadTime = int(round(time.time() * 1000))
        while True:
             
#             self.progress_bar.next()       
#             FreeCADGui.updateGui()
            systemSolved = self.calculateChain(doc)
            totalTime = int(round(time.time() * 1000))
            DebugMsg(A2P_DEBUG_1, "Total steps used: %d\n" %  self.stepCount)
            DebugMsg(A2P_DEBUG_1, "LoadTime (ms): %d\n" % (loadTime - startTime) )
            DebugMsg(A2P_DEBUG_1, "CalcTime (ms): %d\n" % (totalTime - loadTime) )
            DebugMsg(A2P_DEBUG_1, "TotalTime (ms): %d\n" % (totalTime - startTime) )
            if systemSolved:
                #self.mySOLVER_SPIN_ACCURACY *= 1e-1
                
                Msg('\nPOS ACCURACY: {}\n'.format(self.mySOLVER_POS_ACCURACY))
                Msg('SPIN ACCURACY: {}\n'.format(self.mySOLVER_SPIN_ACCURACY))
                Msg( '--->LEVEL OF ACCURACY :{} DONE!\n'.format(self.level_of_accuracy) )
                
                self.level_of_accuracy+=1 
                               
                #FreeCADGui.updateGui()
                if self.level_of_accuracy == MAX_LEVEL_ACCURACY: 
                    #self.solutionToParts(doc)                   
                    break
                
                self.mySOLVER_POS_ACCURACY *= 1e-1
                self.loadSystem(doc)
                #self.calcSpinAccuracy()
                #self.prepareRestart()
            else:
                break
        #self.mySOLVER_SPIN_ACCURACY = SOLVER_SPIN_ACCURACY
        #self.progress_bar.stop()
        return systemSolved

    def solveSystem(self,doc):
        Msg( "\n===== Start Solving System ====== \n" )
        #self.progress_bar = FreeCAD.Base.ProgressIndicator() 
        
#         if a2plib.isPartialProcessing():
#             Msg( "Solvermode = partialProcessing !\n")
#             mode = 'partial'            
#         else:
#             Msg( "Solvermode = solve all Parts at once !\n")
#             mode = 'Progressive magnetic'
#         
        systemSolved = self.solveSystemWithMode(doc)
        
                            
        #FreeCADGui.updateGui()
        
        if self.status == "loadingDependencyError":
            return

        #if not systemSolved and mode == 'partial':
        #    Msg( "Could not solve system with partial processing, switch to 'magnetic' mode  \n" )
        #    mode = 'magnetic'
        #    systemSolved = self.solveSystemWithMode(doc,mode)
        
        
        
        if systemSolved:
            
            self.status = "solved"
            Msg( "===== System solved !  =====" )
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
        
        self.partialSolverCurrentStage = PARTIAL_SOLVE_STAGE1
        #mainWorklist = []
        while self.partialSolverCurrentStage != PARTIAL_SOLVE_END:
            #print "evaluating stage = ", self.partialSolverCurrentStage
            DebugMsg(A2P_DEBUG_1, "Evaluating stage = {}\n".format(self.partialSolverCurrentStage))
            DebugMsg(A2P_DEBUG_1, "Tempfixed objs:\n")
            if A2P_DEBUG_LEVEL>=A2P_DEBUG_1:
                for i in self.rigids:
                    if i.tempfixed:
                        DebugMsg(A2P_DEBUG_1,"    {}\n".format(i.label))
            DebugMsg(A2P_DEBUG_1, "End of Tempfixed objs\n")
            
            while True: 
                somethingFound = False
                #mainWorklist = []
                workList=[]                     
                myCounter = len(self.rigids) 
                numdep=0                 
                for rig in self.rigids:
                    #somethingFound = False
                    workList.extend(rig.getCandidates(self.partialSolverCurrentStage))
                    myCounter-=1
                    workList = list(set(workList))
                    #mainWorklist.extend(workList)
                    #mainWorklist = list(set(mainWorklist))
                    if ((self.partialSolverCurrentStage==PARTIAL_SOLVE_STAGE5) and (myCounter>0)):
                        continue
                    if len(workList)> 0:
                        somethingFound = True
                        #if mode == 'partial':
                        solutionFound = self.calculateWorkList(doc, workList)
                        #else:
                        #    solutionFound = self.calculateWorkList(doc, mainWorklist, mode)                                
                        #solutionFound = True
                        if not solutionFound: 
                            return False
                        else:                                      
                            workList=[]
                if not somethingFound:
                    self.partialSolverCurrentStage +=1
                    workList = []
                    break 
                                
        return True

    def calculateWorkList(self, doc, workList):
        #print 'calculate worklist'
        #reqPosAccuracy = self.mySOLVER_POS_ACCURACY
        #reqSpinAccuracy = self.mySOLVER_SPIN_ACCURACY
        if A2P_DEBUG_LEVEL >= A2P_DEBUG_1:
            self.printList("WorkList", workList)

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
                maxPosError = max(maxPosError , w.maxPosError)
                maxAxisError = max(maxAxisError , w.maxAxisError)
                    

            # Perform the move
            for w in workList:                
                w.move(doc)
                # Enable those 2 lines to see the computation progress on screen
                #w.applySolution(doc, self)
                #FreeCADGui.updateGui()

            # The accuracy is good, apply the solution to FreeCAD's objects
            if (maxPosError < 0.9 * self.mySOLVER_POS_ACCURACY and
                maxAxisError < 0.9 * self.mySOLVER_SPIN_ACCURACY):
                # The accuracy is good, we're done here
                goodAccuracy = True
                # Mark the rigids as tempfixed and add its constrained rigids to pending list to be processed next
                DebugMsg(A2P_DEBUG_1, "{} counts \n".format(calcCount) )
                #self.prnPlacement()
                
                
                for r in workList:                    
                    r.applySolution(doc,self) 
                    FreeCADGui.updateGui()  
                    for dep in r.dependencies:
                        if dep.Enabled:
                            #self.progress_bar.next()
                            dep.Done = True
                            dep.disable()                                  
                    if self.partialSolverCurrentStage == PARTIAL_SOLVE_STAGE1 or r.checkIfAllDone():
                        r.tempfixed = True
                    elif self.partialSolverCurrentStage == PARTIAL_SOLVE_STAGE2 and r.checkIfAllDone():
                        r.tempfixed = True
                        #Msg("Fixed Rigid {}\n".format(r.label))
                if self.partialSolverCurrentStage == PARTIAL_SOLVE_STAGE3:
                    if len(workList)==2:
                        workList[0].mergeRigid(self,workList[1])
                    
            if self.convergencyCounter > SOLVER_STEPS_CONVERGENCY_CHECK:
                if (
                    maxPosError  >= self.lastPositionError or
                    maxAxisError >= self.lastAxisError
                    ):     
                    
                    foundRigidToUnfix = False
                    # search for unsolved dependencies...
                    for rig in workList:
                        if rig.maxAxisError > self.mySOLVER_SPIN_ACCURACY or rig.maxPosError > self.mySOLVER_POS_ACCURACY:
                            for r in rig.linkedRigids:
                                if r.tempfixed and not r.fixed:
                                    r.tempfixed = False
                                    #Msg("unfixed Rigid {}\n".format(r.label))
                                    foundRigidToUnfix = True
                                    #foundRigidToUnfix = False
                    
                    if foundRigidToUnfix:
                        self.lastPositionError = SOLVER_CONVERGENCY_ERROR_INIT_VALUE
                        self.lastAxisError = SOLVER_CONVERGENCY_ERROR_INIT_VALUE
                        self.convergencyCounter = 0
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
def solveConstraints( doc, cache=None ):
    doc.openTransaction("a2p_systemSolving")
    ss = SolverSystem()
    ss.solveSystem(doc)
    doc.commitTransaction()
    #try:
        #doc.recompute()
    #except:
    #    pass
    
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
