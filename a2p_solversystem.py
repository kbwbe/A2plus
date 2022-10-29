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

SOLVER_STEPS_CONVERGENCY_CHECK = 150 #200
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
        constraints = [ obj for obj in doc.Objects if 'ConstraintInfo' in obj.Content]

        faultyConstraintList = []
        for c in constraints:
            constraintOK = True
            for attr in ['Object1','Object2']:
                objectName = getattr(c, attr, None)
                o = doc.getObject(objectName)
                if o is None:
                    constraintOK = False
            if not constraintOK:
                faultyConstraintList.append(c)

        if len(faultyConstraintList) > 0:
            for fc in faultyConstraintList:
                FreeCAD.Console.PrintMessage(translate("A2plus", "Remove faulty constraint '{}'").format(fc.Label) + "\n")
                doc.removeObject(fc.Name)

    def loadSystem(self,doc, matelist=None):
        self.clear()
        self.doc = doc
        self.status = "loading"

        self.removeFaultyConstraints(doc)

        self.convergencyCounter = 0
        self.lastPositionError = SOLVER_CONVERGENCY_ERROR_INIT_VALUE
        self.lastAxisError = SOLVER_CONVERGENCY_ERROR_INIT_VALUE
        #
        self.constraints = []
        constraints =[]             # temporary list
        if matelist is not None:        # Transfer matelist to the temp list
            for obj in matelist:
                if 'ConstraintInfo' in obj.Content:
                    constraints.append(obj)
        else:
            # if there is not a list of my mates get the list from the doc
            constraints = [ obj for obj in doc.Objects if 'ConstraintInfo' in obj.Content]
        # check for Suppressed mates here and transfer mates to self.constraints
        for obj in constraints:
            if hasattr(obj,'Suppressed'):
                #if the mate is suppressed do not add it
                if obj.Suppressed == False:
                    self.constraints.append(obj)
        #
        # Extract all the objectnames which are affected by constraints..
        self.objectNames = []
        for c in self.constraints:
            for attr in ['Object1','Object2']:
                objectName = getattr(c, attr, None)
                if objectName is not None and not objectName in self.objectNames:
                    self.objectNames.append( objectName )
        #
        # create a Rigid() dataStructure for each of these objectnames...
        for o in self.objectNames:
            ob1 = doc.getObject(o)
            if hasattr(ob1, "fixedPosition"):
                fx = ob1.fixedPosition
            else:
                fx = False
            if hasattr(ob1, "debugmode"):
                debugMode = ob1.debugmode
            else:
                debugMode = False
            rig = Rigid(
                o,
                ob1.Label,
                fx,
                ob1.Placement,
                debugMode
                )
            rig.spinCenter = ob1.Shape.BoundBox.Center
            self.rigids.append(rig)
        #
        # link constraints to rigids using dependencies
        deleteList = [] # a list to collect broken constraints
        for c in self.constraints:
            rigid1 = self.getRigid(c.Object1)
            rigid2 = self.getRigid(c.Object2)

            # create and update list of constrained rigids
            if rigid2 is not None and not rigid2 in rigid1.linkedRigids: rigid1.linkedRigids.append(rigid2);
            if rigid1 is not None and not rigid1 in rigid2.linkedRigids: rigid2.linkedRigids.append(rigid1);

            try:
                Dependency.Create(doc, c, self, rigid1, rigid2)
            except:
                self.status = "loadingDependencyError"
                deleteList.append(c)


        for rig in self.rigids:
            rig.hierarchyLinkedRigids.extend(rig.linkedRigids)

        if len(deleteList) > 0:
            msg = translate("A2plus", "The following constraints are broken:") + "\n"
            for c in deleteList:
                msg += "{}\n".format(c.Label)
            msg += translate("A2plus", "Do you want to delete them?")

            flags = QtGui.QMessageBox.StandardButton.Yes | QtGui.QMessageBox.StandardButton.No
            response = QtGui.QMessageBox.critical(
                QtGui.QApplication.activeWindow(),
                translate("A2plus", "Delete broken constraints?"),
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

        self.retrieveDOFInfo() # function only once used here at this place in whole program
        self.status = "loaded"

    def DOF_info_to_console(self):
        doc = FreeCAD.activeDocument()

        dofGroup = doc.getObject("dofLabels")
        if dofGroup is None:
            dofGroup=doc.addObject("App::DocumentObjectGroup", "dofLabels")
        else:
            for lbl in dofGroup.Group:
                doc.removeObject(lbl.Name)
            doc.removeObject("dofLabels")
            dofGroup=doc.addObject("App::DocumentObjectGroup", "dofLabels")

        self.loadSystem( doc )

        # look for unconstrained objects and label them
        solverObjectNames = []
        for rig in self.rigids:
            solverObjectNames.append(rig.objectName)
        shapeObs = a2plib.filterShapeObs(doc.Objects)
        for so in shapeObs:
            if so.Name not in solverObjectNames:
                ob = doc.getObject(so.Name)
                if ob.ViewObject.Visibility == True:
                    bbCenter = ob.Shape.BoundBox.Center
                    dofLabel = doc.addObject("App::AnnotationLabel","dofLabel")
                    dofLabel.LabelText = translate("A2plus", "FREE")
                    dofLabel.BasePosition.x = bbCenter.x
                    dofLabel.BasePosition.y = bbCenter.y
                    dofLabel.BasePosition.z = bbCenter.z
                    #
                    dofLabel.ViewObject.BackgroundColor = a2plib.BLUE
                    dofLabel.ViewObject.TextColor = a2plib.WHITE
                    dofGroup.addObject(dofLabel)


        numdep = 0
        self.retrieveDOFInfo() #function only once used here at this place in whole program
        for rig in self.rigids:
            dofCount = rig.currentDOF()
            ob = doc.getObject(rig.objectName)
            if ob.ViewObject.Visibility == True:
                bbCenter = ob.Shape.BoundBox.Center
                dofLabel = doc.addObject("App::AnnotationLabel","dofLabel")
                if rig.fixed:
                    dofLabel.LabelText = translate("A2plus", "Fixed")
                else:
                    dofLabel.LabelText = translate("A2plus", "DOFs: {}").format(dofCount)
                dofLabel.BasePosition.x = bbCenter.x
                dofLabel.BasePosition.y = bbCenter.y
                dofLabel.BasePosition.z = bbCenter.z

                if rig.fixed:
                    dofLabel.ViewObject.BackgroundColor = a2plib.RED
                    dofLabel.ViewObject.TextColor = a2plib.BLACK
                elif dofCount == 0:
                    dofLabel.ViewObject.BackgroundColor = a2plib.RED
                    dofLabel.ViewObject.TextColor = a2plib.BLACK
                elif dofCount < 6:
                    dofLabel.ViewObject.BackgroundColor = a2plib.YELLOW
                    dofLabel.ViewObject.TextColor = a2plib.BLACK
                dofGroup.addObject(dofLabel)


            rig.beautyDOFPrint()
            numdep+=rig.countDependencies()
        Msg( translate("A2plus", "There are '{}' dependencies").format(numdep/2) + "\n")

    def retrieveDOFInfo(self):
        """
        Method used to retrieve all info related to DOF handling.
        the method scans each rigid, and on each not tempfixed rigid scans the list of linkedobjects
        then for each linked object compile a dict where each linked object has its dependencies
        then for each linked object compile a dict where each linked object has its dof position
        then for each linked object compile a dict where each linked object has its dof rotation
        """
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

    def calcMoveData(self,doc):
        for rig in self.rigids:
            rig.calcMoveData(doc, self)

    def prepareRestart(self):
        for rig in self.rigids:
            rig.prepareRestart()
        self.partialSolverCurrentStage = PARTIAL_SOLVE_STAGE1

    def detectUnmovedParts(self):
        doc = FreeCAD.activeDocument()
        self.unmovedParts = []
        for rig in self.rigids:
            if rig.fixed: continue
            if not rig.moved:
                self.unmovedParts.append(
                    doc.getObject(rig.objectName)
                    )

    def solveAccuracySteps(self,doc, matelist=None):
        self.level_of_accuracy=1
        self.mySOLVER_POS_ACCURACY = self.getSolverControlData()[self.level_of_accuracy][0]
        self.mySOLVER_SPIN_ACCURACY = self.getSolverControlData()[self.level_of_accuracy][1]

        self.loadSystem(doc, matelist)
        if self.status == "loadingDependencyError":
            return
        self.assignParentship(doc)
        while True:
            systemSolved = self.calculateChain(doc)
            if self.level_of_accuracy == 1:
                self.detectUnmovedParts()   # do only once here. It can fail at higher accuracy levels
                                            # where not a final solution is required.
            if a2plib.SOLVER_ONESTEP > 0:
                systemSolved = True
                break
            if systemSolved:
                self.level_of_accuracy+=1
                if self.level_of_accuracy > len(self.getSolverControlData()):
                    self.solutionToParts(doc)
                    break
                self.mySOLVER_POS_ACCURACY = self.getSolverControlData()[self.level_of_accuracy][0]
                self.mySOLVER_SPIN_ACCURACY = self.getSolverControlData()[self.level_of_accuracy][1]
                self.loadSystem(doc, matelist)
            else:
                completeSolvingRequired = self.getSolverControlData()[self.level_of_accuracy][2]
                if not completeSolvingRequired: systemSolved = True
                break
        self.maxAxisError = 0.0
        self.maxSingleAxisError = 0.0
        self.maxPosError = 0.0
        for rig in self.rigids:
            if rig.maxPosError > self.maxPosError:
                self.maxPosError = rig.maxPosError
            if rig.maxAxisError > self.maxAxisError:
                self.maxAxisError = rig.maxAxisError
            if rig.maxSingleAxisError > self.maxSingleAxisError:
                self.maxSingleAxisError = rig.maxSingleAxisError
        if not a2plib.SIMULATION_STATE:
            Msg(translate("A2plus", "TARGET   POS-ACCURACY :{}").format(self.mySOLVER_POS_ACCURACY) + "\n")
            Msg(translate("A2plus", "REACHED  POS-ACCURACY :{}").format(self.maxPosError) + "\n")
            Msg(translate("A2plus", "TARGET  SPIN-ACCURACY :{}").format(self.mySOLVER_SPIN_ACCURACY) + "\n")
            Msg(translate("A2plus", "REACHED SPIN-ACCURACY :{}").format(self.maxAxisError) + "\n")
            Msg(translate("A2plus", "SA      SPIN-ACCURACY :{}").format(self.maxSingleAxisError) + "\n")

        return systemSolved

    def solveSystem(self,doc,matelist=None, showFailMessage=True):
        if not a2plib.SIMULATION_STATE:
            Msg("===== " + translate("A2plus", "Start Solving System") + " =====\n")

        systemSolved = self.solveAccuracySteps(doc,matelist)
        if self.status == "loadingDependencyError":
            return systemSolved
        if systemSolved:
            self.status = "solved"
            if not a2plib.SIMULATION_STATE:
                Msg("===== " + translate("A2plus", "System solved using partial + recursive unfixing") + " =====\n")
                self.checkForUnmovedParts()
        else:
            if a2plib.SIMULATION_STATE == True:
                self.status = "unsolved"
                return systemSolved

            else: # a2plib.SIMULATION_STATE == False
                self.status = "unsolved"
                if showFailMessage == True:
                    Msg("===== " + translate("A2plus", "Could not solve system") + " =====\n")
                    msg = \
translate("A2plus",
'''
Constraints inconsistent. Cannot solve System.
Please run the conflict finder tool!
'''
)
                    QtGui.QMessageBox.information(
                        QtGui.QApplication.activeWindow(),
                        translate("A2plus", "Constraint mismatch"),
                        msg
                        )
                return systemSolved

    def checkForUnmovedParts(self):
        """
        If there are parts, which are constrained but have no
        constraint path to a fixed part, the solver will
        ignore them and they are not moved.
        This function detects this and signals it to the user.
        """
        if len(self.unmovedParts) != 0:
            FreeCADGui.Selection.clearSelection()
            for obj in self.unmovedParts:
                FreeCADGui.Selection.addSelection(obj)
                msg = translate("A2plus",
'''
The highlighted parts were not moved. They are
not constrained (also over constraint chains)
to a fixed part!
''')
            if a2plib.SHOW_WARNING_FLOATING_PARTS: #dialog is not needet during conflict finding
                QtGui.QMessageBox.information(
                    QtGui.QApplication.activeWindow(),
                    translate("A2plus", "Could not move some parts"),
                    msg
                    )
            else:
                print ('')
                print (msg) # during conflict finding do a print to console output
                print ('')

    def printList(self, name, l):
        Msg("{} = (".format(name))
        for e in l:
            Msg( "{} ".format(e.label) )
        Msg("):\n")

    def calculateChain(self, doc):
        self.stepCount = 0
        workList = []

        if a2plib.SIMULATION_STATE == True:
            # Solve complete System at once if simulation is running
            workList = self.rigids
            solutionFound = self.calculateWorkList(doc, workList)
            if not solutionFound: return False
            return True
        elif a2plib.PARTIAL_PROCESSING_ENABLED == False:
            # Solve complete System at once
            workList = self.rigids
            solutionFound = self.calculateWorkList(doc, workList)
            if not solutionFound: return False
            return True
        else:
            # Normal partial solving if no simulation is running
            # load initial worklist with all fixed parts...
            for rig in self.rigids:
                if rig.fixed:
                    workList.append(rig);
            #self.printList("Initial-Worklist", workList)

            while True:
                addList = []
                newRigFound = False
                for rig in workList:
                    for linkedRig in rig.linkedRigids:
                        if linkedRig in workList: continue
                        if rig.isFullyConstrainedByRigid(linkedRig):
                            addList.append(linkedRig)
                            newRigFound = True
                            break
                if not newRigFound:
                    for rig in workList:
                        addList.extend(rig.getCandidates())
                addList = set(addList)
                #self.printList("AddList", addList)
                if len(addList) > 0:
                    workList.extend(addList)
                    solutionFound = self.calculateWorkList(doc, workList)
                    if not solutionFound: return False
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
            maxSingleAxisError = 0.0

            calcCount += 1
            self.stepCount += 1
            self.convergencyCounter += 1
            # First calculate all the movement vectors
            for w in workList:
                w.moved = True
                w.calcMoveData(doc, self)
                if w.maxPosError > maxPosError:
                    maxPosError = w.maxPosError
                if w.maxAxisError > maxAxisError:
                    maxAxisError = w.maxAxisError
                if w.maxSingleAxisError > maxSingleAxisError:
                    maxSingleAxisError = w.maxSingleAxisError

            # Perform the move
            for w in workList:
                w.move(doc)

            # The accuracy is good, apply the solution to FreeCAD's objects
            if (maxPosError <= reqPosAccuracy and   # relevant check
                maxAxisError <= reqSpinAccuracy and # relevant check
                maxSingleAxisError <= reqSpinAccuracy * 10  # additional check for insolvable assemblies
                                                            # sometimes spin can be solved but singleAxis not..
                ) or (a2plib.SOLVER_ONESTEP > 0):
                # The accuracy is good, we're done here
                goodAccuracy = True
                # Mark the rigids as tempfixed and add its constrained rigids to pending list to be processed next
                for r in workList:
                    r.applySolution(doc, self)
                    r.tempfixed = True

            if self.convergencyCounter > SOLVER_STEPS_CONVERGENCY_CHECK:
                if (
                    maxPosError  >= SOLVER_CONVERGENCY_FACTOR * self.lastPositionError or
                    maxAxisError >= SOLVER_CONVERGENCY_FACTOR * self.lastAxisError
                    ):
                    foundRigidToUnfix = False
                    # search for unsolved dependencies...
                    for rig in workList:
                        if rig.fixed or rig.tempfixed: continue
                        #if rig.maxAxisError >= maxAxisError or rig.maxPosError >= maxPosError:
                        if rig.maxAxisError > reqSpinAccuracy or rig.maxPosError > reqPosAccuracy:
                            for r in rig.linkedRigids:
                                if r.tempfixed and not r.fixed:
                                    r.tempfixed = False
                                    #Msg("unfixed Rigid {}\n".format(r.label))
                                    foundRigidToUnfix = True

                    if foundRigidToUnfix:
                        self.lastPositionError = SOLVER_CONVERGENCY_ERROR_INIT_VALUE
                        self.lastAxisError = SOLVER_CONVERGENCY_ERROR_INIT_VALUE
                        self.convergencyCounter = 0
                        continue
                    else:
                        Msg('\n')
                        Msg('convergency-conter: {}\n'.format(self.convergencyCounter))
                        Msg(translate("A2plus", "Calculation stopped, no convergency anymore!") + "\n")
                        return False

                self.lastPositionError = maxPosError
                self.lastAxisError = maxAxisError
                self.maxSingleAxisError = maxSingleAxisError
                self.convergencyCounter = 0

            if self.stepCount > SOLVER_MAXSTEPS:
                Msg(translate("A2plus", "Reached max calculations count: {}").format(SOLVER_MAXSTEPS) + "\n")
                return False
        return True

    def solutionToParts(self,doc):
        for rig in self.rigids:
            rig.applySolution(doc, self);

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
