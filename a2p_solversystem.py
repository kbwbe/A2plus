# -*- coding: utf-8 -*-
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

import os
import FreeCAD, FreeCADGui
from PySide import QtGui
#from a2p_translateUtils import *
import a2plib
import cProfile
from a2plib import (
    path_a2p,
    Msg,
    DebugMsg,
    A2P_DEBUG_LEVEL,
    A2P_DEBUG_1,
    PARTIAL_SOLVE_STAGE1,
    )
from a2p_dependencies import Dependency
from a2p_rigid import Rigid

SOLVER_MAXSTEPS = 50000
MAX_CONVERGENCY_COUNTER = 50000  # Define the maximum number of convergency attempts allowed
translate = FreeCAD.Qt.translate

# SOLVER_CONTROLDATA has been replaced by SolverSystem.getSolverControlData()
#SOLVER_CONTROLDATA = {
#    #Index:(posAccuracy,spinAccuracy,completeSolvingRequired)
#    1:(0.1,0.1,True),
#    2:(0.01,0.01,True),
#    3:(0.001,0.001,True),
#    4:(0.0001,0.0001,False),
#    5:(0.00001,0.00001,False)
#    }

SOLVER_POS_ACCURACY = 1.0e-1  # gets to smaller values during solving
SOLVER_SPIN_ACCURACY = 1.0e-1 # gets to smaller values during solving

SOLVER_STEPS_CONVERGENCY_CHECK = 500 #200
SOLVER_CONVERGENCY_FACTOR = 0.99
SOLVER_CONVERGENCY_ERROR_INIT_VALUE = 1.0e+20

#------------------------------------------------------------------------------

class SolverSystem():
    """
    class Solversystem():
    A new iterative solver, inspired by physics.
    Using "attraction" of parts by constraints
    """

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
        self.maxPosError = 0.0
        self.maxAxisError = 0.0
        self.maxSingleAxisError = 0.0
        self.unmovedParts = []

    def clear(self):
        for r in self.rigids:
            r.clear()
        self.stepCount = 0
        self.rigids = []
        self.constraints = []
        self.objectNames = []
        self.partialSolverCurrentStage = PARTIAL_SOLVE_STAGE1
        
    def resetState(self, workList):
        # Reset the state of the system
        for rig in workList:
            rig.reset()  # Implement a reset method in the Rigid class to reset its state

    def getSolverControlData(self):
        if a2plib.SIMULATION_STATE:
            # do less accurate solving for simulations...
            solverControlData = {
                #Index:(posAccuracy,spinAccuracy,completeSolvingRequired)
                1:(0.1,0.1,True)
                }
        else:
            solverControlData = {
                #Index:(posAccuracy,spinAccuracy,completeSolvingRequired)
                1:(0.1,0.1,True),
                2:(0.01,0.01,True),
                3:(0.001,0.001,False),
                4:(0.0001,0.0001,False),
                5:(0.00001,0.00001,False)
                }
        return solverControlData


    def getRigid(self,objectName):
        """Get a Rigid by objectName."""
        rigs = [r for r in self.rigids if r.objectName == objectName]
        if len(rigs) > 0: return rigs[0]
        return None

    def removeFaultyConstraints(self, doc):
        """
        Remove constraints where referenced objects do not exist anymore.
        """
        constraints = [obj for obj in doc.Objects if hasattr(obj, 'Content') and 'ConstraintInfo' in obj.Content]

        faultyConstraintList = []
        for c in constraints:
            objectNames = [getattr(c, attr, None) for attr in ['Object1', 'Object2']]
            if any(doc.getObject(name) is None for name in objectNames):
                faultyConstraintList.append(c)

        for fc in faultyConstraintList:
            FreeCAD.Console.PrintMessage(translate("A2plus", "Remove faulty constraint '{}'").format(fc.Label) + "\n")
            doc.removeObject(fc.Name)

    def loadSystem(self, doc, matelist=None):
        self.clear()
        self.doc = doc
        self.status = "loading"

        self.removeFaultyConstraints(doc)

        self.convergencyCounter = 0
        self.lastPositionError = SOLVER_CONVERGENCY_ERROR_INIT_VALUE
        self.lastAxisError = SOLVER_CONVERGENCY_ERROR_INIT_VALUE

        # Extract constraints from matelist or document
        self.constraints = [obj for obj in (matelist if matelist is not None else doc.Objects) if 'ConstraintInfo' in obj.Content]

        # Filter out suppressed constraints
        self.constraints = [obj for obj in self.constraints if not hasattr(obj, 'Suppressed') or not obj.Suppressed]

        # Extract object names affected by constraints
        self.objectNames = list(set(getattr(c, attr) for c in self.constraints for attr in ['Object1', 'Object2'] if hasattr(c, attr)))

        # Create Rigid objects for each object name
        self.rigids = []
        for o in self.objectNames:
            ob1 = doc.getObject(o)
            fx = ob1.fixedPosition if hasattr(ob1, "fixedPosition") else False
            debugMode = ob1.debugmode if hasattr(ob1, "debugmode") else False
            rig = Rigid(o, ob1.Label, fx, ob1.Placement, debugMode)
            rig.spinCenter = ob1.Shape.BoundBox.Center
            self.rigids.append(rig)

        # Link constraints to rigids using dependencies
        deleteList = [] # a list to collect broken constraints
        for c in self.constraints:
            rigid1 = self.getRigid(c.Object1)
            rigid2 = self.getRigid(c.Object2)

            # create and update list of constrained rigids
            if rigid1 and rigid2:
                if rigid2 not in rigid1.linkedRigids:
                    rigid1.linkedRigids.append(rigid2)
                if rigid1 not in rigid2.linkedRigids:
                    rigid2.linkedRigids.append(rigid1)

                try:
                    Dependency.Create(doc, c, self, rigid1, rigid2)
                except:
                    self.status = "loadingDependencyError"
                    deleteList.append(c)

        for rig in self.rigids:
            rig.hierarchyLinkedRigids.extend(rig.linkedRigids)

        # Handle broken constraints
        if deleteList:
            msg = translate("A2plus", "The following constraints are broken:") + "\n"
            msg += "\n".join(c.Label for c in deleteList) + "\n"
            msg += translate("A2plus", "Do you want to delete them?")
            response = QtGui.QMessageBox.critical(QtGui.QApplication.activeWindow(), translate("A2plus", "Delete broken constraints?"), msg, QtGui.QMessageBox.StandardButton.Yes | QtGui.QMessageBox.StandardButton.No)
            if response == QtGui.QMessageBox.Yes:
                for c in deleteList:
                    a2plib.removeConstraint(c)

        if self.status == "loadingDependencyError":
            return

        # Calculate spin center and reference points' bounding box size for each rigid
        for rig in self.rigids:
            rig.calcSpinCenter()
            rig.calcRefPointsBoundBoxSize()

        # Retrieve DOF information
        self.retrieveDOFInfo() # function only once used here at this place in whole program
        self.status = "loaded"

    def DOF_info_to_console(self):
        doc = FreeCAD.activeDocument()

        # Clear existing dofLabels object group if it exists
        dofGroup = doc.getObject("dofLabels")
        if dofGroup is not None:
            doc.removeObject(dofGroup.Name)

        # Create a new dofLabels object group
        dofGroup = doc.addObject("App::DocumentObjectGroup", "dofLabels")

        # Load system and retrieve DOF information
        self.loadSystem(doc)
        self.retrieveDOFInfo()

        # Get object names affected by constraints
        solverObjectNames = {rig.objectName for rig in self.rigids}

        # Look for unconstrained objects and label them
        for obj in a2plib.filterShapeObs(doc.Objects):
            if obj.Name not in solverObjectNames and obj.ViewObject.Visibility:
                bbCenter = obj.Shape.BoundBox.Center
                dofLabel = doc.addObject("App::AnnotationLabel", "dofLabel")
                dofLabel.LabelText = translate("A2plus", "FREE")
                dofLabel.BasePosition = bbCenter
                dofLabel.ViewObject.BackgroundColor = a2plib.BLUE
                dofLabel.ViewObject.TextColor = a2plib.WHITE
                dofGroup.addObject(dofLabel)

        numdep = sum(rig.countDependencies() for rig in self.rigids)
        Msg(translate("A2plus", "There are {:.0f} dependencies").format(numdep / 2) + "\n")

        # Label rigids based on their DOF count
        for rig in self.rigids:
            if rig.fixed:
                label_text = translate("A2plus", "Fixed")
                bg_color = a2plib.RED
            else:
                dofCount = rig.currentDOF()
                label_text = translate("A2plus", "DOFs: {}").format(dofCount)
                if dofCount == 0:
                    bg_color = a2plib.RED
                elif dofCount < 6:
                    bg_color = a2plib.YELLOW
                else:
                    bg_color = None

            if bg_color is not None:
                ob = doc.getObject(rig.objectName)
                if ob.ViewObject.Visibility:
                    bbCenter = ob.Shape.BoundBox.Center
                    dofLabel = doc.addObject("App::AnnotationLabel", "dofLabel")
                    dofLabel.LabelText = label_text
                    dofLabel.BasePosition = bbCenter
                    dofLabel.ViewObject.BackgroundColor = bg_color
                    dofLabel.ViewObject.TextColor = a2plib.BLACK
                    dofGroup.addObject(dofLabel)

    def retrieveDOFInfo(self):
        """
        Method used to retrieve all info related to DOF handling.
        the method scans each rigid, and on each not tempfixed rigid scans the list of linkedobjects
        then for each linked object compile a dict where each linked object has its dependencies
        then for each linked object compile a dict where each linked object has its dof position
        then for each linked object compile a dict where each linked object has its dof rotation
        """
        for rig in self.rigids:
            deps_per_linked_rigids = {}

            for linkedRig in rig.linkedRigids:
                deps = [dep for dep in rig.dependencies if dep.dependedRigid == linkedRig]
                #be sure pointconstraints are at the end of the list
                point_deps = [dep for dep in deps if dep.isPointConstraint]
                non_point_deps = [dep for dep in deps if not dep.isPointConstraint]
                #add at the end the point constraints
                deps_per_linked_rigids[linkedRig] = non_point_deps + point_deps

            #dofPOSPerLinkedRigid is a dict where for each
            for linkedRig, deps in deps_per_linked_rigids.items():
                linkedRig.pointConstraints = []
                dof_pos = linkedRig.posDOF
                dof_rot = linkedRig.rotDOF
                for dep in deps:
                    dof_pos, dof_rot = dep.calcDOF(dof_pos, dof_rot, linkedRig.pointConstraints)
                rig.dofPOSPerLinkedRigids[linkedRig] = dof_pos
                rig.dofROTPerLinkedRigids[linkedRig] = dof_rot

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
            Msg(translate("A2plus", "Hierarchy:") + "\n")
            Msg(20*"=" + "\n")
            for rig in self.rigids:
                if rig.fixed: rig.printHierarchy(0)
            Msg(20*"=" + "\n")

        #self.visualizeHierarchy()

    def visualizeHierarchy(self):
        '''
        Generate an html file with constraints structure.

        The html file is in the same folder
        with the same filename of the assembly
        '''
        out_file = os.path.splitext(self.doc.FileName)[0] + '_asm_hierarchy.html'
        Msg(translate("A2plus", "Writing visual hierarchy to: '{}'").format(out_file) + "\n")
        f = open(out_file, "w")

        f.write("<!DOCTYPE html>\n")
        f.write("<html>\n")
        f.write("<head>\n")
        f.write('    <meta charset="utf-8">\n')
        f.write('    <meta http-equiv="X-UA-Compatible" content="IE=edge">\n')
        f.write('    <title>' + translate("A2plus", "A2P assembly hierarchy visualization") + '</title>\n')
        f.write("</head>\n")
        f.write("<body>\n")
        f.write('<div class="mermaid">\n')

        f.write("graph TD\n")
        for rig in self.rigids:
            rigLabel = a2plib.to_str(rig.label).replace(u' ',u'_')
            # No children, add current rogod as a leaf entry
            if len(rig.childRigids) == 0:
                message = u"{}\n".format(rigLabel)
                f.write(message)
            else:
                # Rigid have children, add them based on the dependency list
                for d in rig.dependencies:
                    if d.dependedRigid in rig.childRigids:
                        dependedRigLabel = a2plib.to_str(d.dependedRigid.label).replace(u' ',u'_')
                        if rig.fixed:
                            message = "{}({}<br>*" + translate("A2plus", "FIXED") + "*) -- {} --> {}\n".format(rigLabel, rigLabel, d.Type, dependedRigLabel)
                            f.write(message)
                        else:
                            message = u"{} -- {} --> {}\n".format(rigLabel, d.Type, dependedRigLabel)
                            f.write(message)

        f.write("</div>\n")
        f.write('    <script src="https://unpkg.com/mermaid@7.1.2/dist/mermaid.js"></script>\n')
        f.write("    <script>\n")
        f.write('        mermaid.initialize({startOnLoad: true});\n')
        f.write("    </script>\n")
        f.write("</body>")
        f.write("</html>")
        f.close()

    def calcMoveData(self, doc):
        [rig.calcMoveData(doc, self) for rig in self.rigids]

    def prepareRestart(self):
        [rig.prepareRestart() for rig in self.rigids]
        self.partialSolverCurrentStage = PARTIAL_SOLVE_STAGE1

    def detectUnmovedParts(self):
        doc = FreeCAD.activeDocument()
        self.unmovedParts = [doc.getObject(rig.objectName) for rig in self.rigids if not rig.fixed and not rig.moved]

    def solveAccuracySteps(self, doc, matelist=None):
        # Initialize accuracy level and solver control data
        self.level_of_accuracy = 1
        solver_control_data = self.getSolverControlData()
        
        # Load the system and check for loading errors
        self.loadSystem(doc, matelist)
        if self.status == "loadingDependencyError":
            return False

        # Perform initial parentship assignment
        self.assignParentship(doc)
        
        # Iteratively refine accuracy level until convergence or maximum level
        while True:
            # Calculate chain and check if the system is solved
            # self.profile_calculateChain(doc)
            systemSolved = self.calculateChain(doc)
            
            # Detect unmoved parts if accuracy level is 1
            if self.level_of_accuracy == 1:
                self.detectUnmovedParts()
                    
            # Check if one-step solving is enabled
            if a2plib.SOLVER_ONESTEP > 0:
                systemSolved = True
                break

            # If system is solved, increment accuracy level and load the system for the new level
            if systemSolved:
                self.level_of_accuracy += 1
                if self.level_of_accuracy > len(solver_control_data):
                    self.solutionToParts(doc)
                    break
                self.mySOLVER_POS_ACCURACY, self.mySOLVER_SPIN_ACCURACY, complete_solving_required = solver_control_data[self.level_of_accuracy]
                self.loadSystem(doc, matelist)
            # If system is not solved, check if complete solving is required for the current accuracy level
            else:
                _, _, complete_solving_required = solver_control_data[self.level_of_accuracy]
                if not complete_solving_required:
                    systemSolved = True
                break
        
        if self.rigids:
            # Update maximum errors
            self.maxAxisError = max(rig.maxAxisError for rig in self.rigids)
            self.maxSingleAxisError = max(rig.maxSingleAxisError for rig in self.rigids)
            self.maxPosError = max(rig.maxPosError for rig in self.rigids)
        else:
            # Handle the case when self.rigids is empty
            self.maxAxisError = 0
            self.maxSingleAxisError = 0
            self.maxPosError = 0

        # Print accuracy information if not in simulation state
        if not a2plib.SIMULATION_STATE:
            Msg(translate("A2plus", "TARGET   POS-ACCURACY :{}").format(self.mySOLVER_POS_ACCURACY) + "\n")
            Msg(translate("A2plus", "REACHED  POS-ACCURACY :{}").format(self.maxPosError) + "\n")
            Msg(translate("A2plus", "TARGET  SPIN-ACCURACY :{}").format(self.mySOLVER_SPIN_ACCURACY) + "\n")
            Msg(translate("A2plus", "REACHED SPIN-ACCURACY :{}").format(self.maxAxisError) + "\n")
            Msg(translate("A2plus", "SA      SPIN-ACCURACY :{}").format(self.maxSingleAxisError) + "\n")

        return systemSolved

    def solveSystem(self, doc, matelist=None, showFailMessage=True):
        if not a2plib.SIMULATION_STATE:
            Msg("===== " + translate("A2plus", "Start Solving System") + " =====\n")

        systemSolved = self.solveAccuracySteps(doc, matelist)
        if self.status == "loadingDependencyError":
            return systemSolved

        if systemSolved:
            self.status = "solved"
            if not a2plib.SIMULATION_STATE:
                Msg("===== " + translate("A2plus", "System solved using partial + recursive unfixing") + " =====\n")
                self.checkForUnmovedParts()
        else:
            if a2plib.SIMULATION_STATE:
                self.status = "unsolved"
                return systemSolved
            else: # a2plib.SIMULATION_STATE == False
                self.status = "unsolved"
                if showFailMessage:
                    Msg("===== " + translate("A2plus", "Could not solve system") + " =====\n")
                    msg = translate("A2plus", "Constraints inconsistent. Cannot solve System.\nPlease run the conflict finder tool!")
                    QtGui.QMessageBox.information(
                        QtGui.QApplication.activeWindow(),
                        translate("A2plus", "Constraint mismatch"),
                        msg
                    )
                return systemSolved

    def checkForUnmovedParts(self):
        """
        If there are parts constrained but have no
        constraint path to a fixed part, the solver
        ignores them and they are not moved.
        This function detects this and signals it to the user.
        """
        if self.unmovedParts:
            FreeCADGui.Selection.clearSelection()
            for obj in self.unmovedParts:
                FreeCADGui.Selection.addSelection(obj)
            msg = translate("A2plus",
                '''
                The highlighted parts were not moved. They are
                not constrained (also over constraint chains)
                to a fixed part!
                ''')
            if a2plib.SHOW_WARNING_FLOATING_PARTS:
                QtGui.QMessageBox.information(
                    QtGui.QApplication.activeWindow(),
                    translate("A2plus", "Could not move some parts"),
                    msg
                )
            else:
                print('')
                print(msg)  # Print to console output during conflict finding
                print('')

    def printList(self, name, l):
        Msg("{} = (".format(name))
        for e in l:
            Msg( "{} ".format(e.label) )
        Msg("):\n")

    def profile_calculateChain(self,doc):
        profiler = cProfile.Profile()
        profiler.enable()
        self.calculateChain(doc)
        profiler.disable()
        profiler.print_stats()
    
    def calculateChain(self, doc):
        self.stepCount = 0
        workList = []

        if a2plib.SIMULATION_STATE or not a2plib.PARTIAL_PROCESSING_ENABLED:
            # Solve complete System at once if simulation is running or partial processing is disabled
            workList = self.rigids
            solutionFound = self.calculateWorkList(doc, workList)
            return solutionFound

        # Normal partial solving if no simulation is running and partial processing is enabled
        # Load initial worklist with all fixed parts
        workList.extend(rig for rig in self.rigids if rig.fixed)

        while True:
            addList = set()
            newRigFound = False
            
            for rig in workList:
                for linkedRig in rig.linkedRigids:
                    if linkedRig not in workList and rig.isFullyConstrainedByRigid(linkedRig):
                        addList.add(linkedRig)
                        newRigFound = True
                        break
            
            if not newRigFound:
                for rig in workList:
                    addList.update(rig.getCandidates())

            if addList:
                # Update cached state for rigids being added to the work list
                for rig in addList:
                    rig.updateCachedState(rig.placement)
                workList.extend(addList)
                solutionFound = self.calculateWorkList(doc, workList)
                if not solutionFound:
                    return False
            else:
                break

            if a2plib.SOLVER_ONESTEP > 2:
                break
            
        return True

    def calculateWorkList(self, doc, workList):
        reqPosAccuracy = self.mySOLVER_POS_ACCURACY
        reqSpinAccuracy = self.mySOLVER_SPIN_ACCURACY

        for rig in workList:
            rig.enableDependencies(workList)
            rig.calcSpinBasicDataDepsEnabled()

        self.lastPositionError = SOLVER_CONVERGENCY_ERROR_INIT_VALUE
        self.lastAxisError = SOLVER_CONVERGENCY_ERROR_INIT_VALUE
        self.convergencyCounter = 0
        calcCount = 0

        while True:
            maxPosError = maxAxisError = maxSingleAxisError = 0.0
            calcCount += 1
            self.stepCount += 1
            self.convergencyCounter += 1

            # Calculate all movement vectors
            for w in workList:
                w.moved = True
                w.calcMoveData(doc, self)
                maxPosError = max(maxPosError, w.maxPosError)
                maxAxisError = max(maxAxisError, w.maxAxisError)
                maxSingleAxisError = max(maxSingleAxisError, w.maxSingleAxisError)

            # Perform the move
            for w in workList:
                w.move(doc)

            # Check accuracy and apply solution
            if (maxPosError <= reqPosAccuracy and
                maxAxisError <= reqSpinAccuracy and
                maxSingleAxisError <= reqSpinAccuracy * 10) or (a2plib.SOLVER_ONESTEP > 0):
                # The accuracy is good, we're done here

                for r in workList:
                    r.applySolution(doc, self)
                    r.tempfixed = True
                return True

            # Check for convergence
            if self.convergencyCounter > SOLVER_STEPS_CONVERGENCY_CHECK:
                if maxPosError >= SOLVER_CONVERGENCY_FACTOR * self.lastPositionError or maxAxisError >= SOLVER_CONVERGENCY_FACTOR * self.lastAxisError:
                    for rig in workList:
                        if rig.fixed or rig.tempfixed:
                            continue
                        if rig.maxAxisError > reqSpinAccuracy or rig.maxPosError > reqPosAccuracy:
                            for r in rig.linkedRigids:
                                if r.tempfixed and not r.fixed:
                                    r.tempfixed = False
                                    break
                            else:
                                if self.convergencyCounter == 0:
                                    Msg('\n')
                                    Msg('convergency-conter: {}\n'.format(self.convergencyCounter))
                                    Msg(translate("A2plus", "Calculation stopped, no convergency anymore!") + "\n")
                                # Attempt recovery
                                self.resetState(workList)  # Reset the state of the system
                                self.convergencyCounter += 1
                                if self.convergencyCounter >= MAX_CONVERGENCY_COUNTER:
                                    break  # Exit the loop to prevent excessive attempts
                else:
                    self.lastPositionError = maxPosError
                    self.lastAxisError = maxAxisError
                    self.maxSingleAxisError = maxSingleAxisError
                    self.convergencyCounter = 0

            if self.stepCount > SOLVER_MAXSTEPS:
                Msg(translate("A2plus", "Reached max calculations count: {}").format(SOLVER_MAXSTEPS) + "\n")
                return False

    def solutionToParts(self,doc):
        for rig in self.rigids:
            rig.applySolution(doc, self)

#------------------------------------------------------------------------------
def solveConstraints( doc, cache=None, useTransaction = True, matelist=None, showFailMessage=True):

    if doc is None:
        QtGui.QMessageBox.information(
                    QtGui.QApplication.activeWindow(),
                    translate("A2plus", "No active document found!"),
                    translate("A2plus", "Before running solver, you have to open an assembly file.")
                    )
        return

    if useTransaction: doc.openTransaction("a2p_systemSolving")
    ss = SolverSystem()
    systemSolved = ss.solveSystem(doc, matelist, showFailMessage )
    if useTransaction: doc.commitTransaction()
    a2plib.unTouchA2pObjects()
    return systemSolved

def autoSolveConstraints( doc, callingFuncName, cache=None, useTransaction=True, matelist=None):
    if not a2plib.getAutoSolveState():
        return
    if callingFuncName is not None:
        """
        print (
            translate("A2plus", "AutoSolveConstraints called from '{}'").format(
                callingFuncName
                )
               )
        """
    solveConstraints(doc, useTransaction)

class a2p_SolverCommand:
    def Activated(self):
        solveConstraints( FreeCAD.ActiveDocument ) #the new iterative solver

    def GetResources(self):
        return {
            'Pixmap'  : path_a2p + '/icons/a2p_Solver.svg',
            'MenuText': translate("A2plus", "Solve constraints"),
            'ToolTip' : translate("A2plus", "Solves constraints")
            }

FreeCADGui.addCommand('a2p_SolverCommand', a2p_SolverCommand())
#------------------------------------------------------------------------------

if __name__ == "__main__":
    DebugMsg(A2P_DEBUG_1, translate("A2plus", "Starting solveConstraints latest script...") + "\n")
    doc = FreeCAD.activeDocument()
    solveConstraints(doc)
