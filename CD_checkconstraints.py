#***************************************************************************
#*                                                                         *
#*   Copyright (c) 2020 Dan Miel                                           *
#*                                                                         *
#*   This program is free software; you can redistribute it and/or modify  *
#*   it under the terms of the GNU Lesser General Public License (LGPL)    *
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
# This is to be used with A2plus Assembly WorkBench
# Tries to find constraints that are conflicting with each other.


import os
import FreeCAD
import FreeCADGui
from PySide import QtGui, QtCore
from PySide.QtGui import *
import a2p_solversystem
import a2p_constraintServices
import CD_ConstraintDiagnostics

class globaluseclass:
    def __init__(self):
        self.checkingnum = 0
        self.roundto = 6
        self.labelexist = False
        self.movedconsts = []
        self.test = []
        self.allErrors = {}
g = globaluseclass()


class mApp(QtGui.QWidget):

    # for error messages
    def __init__(self, msg):
        super().__init__()
        self.title = 'PyQt5 messagebox'
        self.left = 100
        self.top = 100
        self.width = 320
        self.height = 200
        self.initUI(msg)

    def initUI(self, msg, msgtype = 'ok'):
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        if msgtype == 'ok':
            buttonReply = QtGui.QMessageBox.question(self, 'PyQt5 message', msg, QtGui.QMessageBox.Ok | QtGui.QMessageBox.Ok)
        if msgtype == 'yn':
            buttonReply = QtGui.QMessageBox.question(self, 'PyQt5 message', msg, QtGui.QMessageBox.Yes | QtGui.QMessageBox.No, QtGui.QMessageBox.No)
        if buttonReply == QtGui.QMessageBox.Yes:
            pass
            #print('Yes clicked.')
        else:
            pass
            #print('No clicked.')

        self.show()

class formMain(QtGui.QMainWindow):

    def __init__(self, name):
        self.name = name
        super(formMain, self).__init__()
        self.setWindowTitle('Constraint Checker')
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        self.setGeometry(300, 100, 600, 140)
        self.setStyleSheet("font:11pt arial MS")

        self.txtboxReport = QtGui.QTextEdit(self)
        self.txtboxReport.move(5, 5)
        self.txtboxReport.setFixedWidth(600)
        self.txtboxReport.setFixedHeight(75)

        self.lblviewlabel = QtGui.QLabel(self)
        self.lblviewlabel.setText('To view the constraints, press "Open Viewer"')
        self.lblviewlabel.move(5, 90)
        self.lblviewlabel.setFixedWidth(250)
        self.lblviewlabel.setFixedHeight(20)
        self.lblviewlabel.setStyleSheet("font: 13pt arial MS")

        self.btnOpenViewer = QtGui.QPushButton(self)
        self.btnOpenViewer.move(365, 90)
        self.btnOpenViewer.setFixedWidth(100)
        self.btnOpenViewer.setFixedHeight(28)
        self.btnOpenViewer.setToolTip("View constraints the assembly.")
        self.btnOpenViewer.setText("Open Viewer")
        self.btnOpenViewer.clicked.connect(lambda:self.openViewer())

        self.btnCloseForm = QtGui.QPushButton(self)
        self.btnCloseForm.move(475, 90)
        self.btnCloseForm.setFixedWidth(100)
        self.btnCloseForm.setFixedHeight(28)
        self.btnCloseForm.setToolTip("Close this form.")
        self.btnCloseForm.setText("Close")
        self.btnCloseForm.clicked.connect(lambda:self.Closeme())

    def openViewer(self):
        clist = []
        doc = FreeCAD.activeDocument()
        for (k, v) in g.allErrors.items():
            cobj = doc.getObject(k)
            clist.append(cobj)

        CD_ConstraintDiagnostics.form1.show()
        CD_ConstraintDiagnostics.form1.loadtable(clist)


    def resizeEvent(self):
        #resize table
        formx = self.width()
        formy = self.height()
        self.txtboxReport.resize(formx - 20, formy - 120)

    def showme(self, msg):
        self.txtboxReport.setText(msg)
        self.show()


    def Closeme(self):
        self.close()

    def closeEvent(self, event):
        form1.Closeme()
        self.close()

form1 = formMain('form1')


class classfilecheck():
    def __init__(self):
        pass
    def opendoccheck(self):
        doc = None
        doc = FreeCAD.activeDocument()

        if doc is None:
            msg = 'A file must be selected to start this selector\nPlease open a file and try again'
            mApp(msg)
            return('Nostart')

        return()
filecheck = classfilecheck()


class   classCheckConstraints():
    def __init__(self):
        self.name = None

        self.dictAllPlacements = {}
        self.ConstraintsAll = []
        self.ConstraintsBad = []

        self.Listofallparts = []
        self.worklist = []
        self.test = []
        self.dir_errors = []
        self.rigids = []


    def startcheck(self, constraints = 'all'):
        if filecheck.opendoccheck() == 'Nostart':
            return
        doc = FreeCAD.activeDocument()
       
        if constraints == 'all':
            constraints = self.getallconstraints()
        if len(constraints) == 0:
            return

        #ConstraintDiagnostics.statusform.showme('messg')
        CD_ConstraintDiagnostics.statusform.show()
        CD_ConstraintDiagnostics.statusform.txtboxstatus.setText('Running Checker.')

        CD_ConstraintDiagnostics.statusform.update()


        ss = a2p_solversystem.SolverSystem()

        ss.loadSystem(doc)
        ss.assignParentship(doc)
        rigids = ss.rigids

        for e in rigids: # get rigid parts
            self.rigids.append(e.objectName)




        self.dir_errors = a2p_constraintServices.redAdjustConstraintDirections(doc, constraints)
        self.checkformovement(constraints, True)
        if len(g.allErrors) != 0:
            msg = ''
            for e in g.allErrors:
                line = str(g.allErrors.get(e))
                msg = msg + line + '\n'
            form1.showme(msg)
        else:
            print('Zero errors')
        CD_ConstraintDiagnostics.statusform.Closeme()


    def checkformovement(self, constraintlist, putPartBack = True):
        doc = FreeCAD.activeDocument()
        partmoved = ''
        partsmoved = []
        typemoved = ''
        Bothpartsfixed = False

        for checkingnum in range(0, len(constraintlist)):
            cobj = constraintlist[checkingnum]

            if cobj.Name in self.dir_errors:
                errortype = ''
                len1 = 0
                len2 = 0

                if len(cobj.SubElement1) == 0:
                    errortype = 'Feat 1 missing'
                if len(cobj.SubElement2) == 0:
                    errortype = 'Feat 2 missing'
                if errortype == '':
                    errortype = 'Direction'
                self.addError(cobj, errortype, '')
                continue
            subobj1 = cobj.getPropertyByName('Object1')
            subobj2 = cobj.getPropertyByName('Object2')
            part1 = doc.getObject(subobj1) # Save Position and fixed
            part2 = doc.getObject(subobj2)
            p1fix = False
            p2fix = False
            if hasattr(part1, "fixedPosition"):
                p1fix = part1.fixedPosition
            if hasattr(part2, "fixedPosition"):
                p2fix = part2.fixedPosition

            if hasattr(part1, "fixedPosition") and hasattr(part2, "fixedPosition"):
                if part1.fixedPosition and part2.fixedPosition:
                    Bothpartsfixed = True
                    self.addError(cobj, 'Both fixed', '')
                elif part1.fixedPosition or part2.fixedPosition:
                    pass
                if part1.Label not in partsmoved and part2.Label not in partsmoved:
                    part1.fixedPosition = True
                elif part1.Label not in partsmoved:
                    part1.fixedPosition = True
                else:
                    part2.fixedPosition = True


            elif hasattr(part1, "fixedPosition") and hasattr(part2, "fixedPosition") == False:
                if part1.Label not in partsmoved:
                    part1.fixedPosition = True
            elif hasattr(part1, "fixedPosition") == False and hasattr(part2, "fixedPosition"):
                    if part2.Label not in partsmoved and part1.Label not in partsmoved:
                        part2.fixedPosition = True


            #recording the location of part before move***
            preBase1 = part1.Placement.Base
            preBase2 = part2.Placement.Base
            preRot1 = part1.Placement.Rotation.Axis
            preRot2 = part2.Placement.Rotation.Axis
            preAngle1 = part1.Placement.Rotation.Angle
            preAngle2 = part2.Placement.Rotation.Angle




            preBasePt1 = part1.Placement.Base
            preBasePt2 = part2.Placement.Base
            preRotPt1 = part1.Placement.Rotation.Axis
            preRotPt2 = part2.Placement.Rotation.Axis
            preAnglePt1 = part1.Placement.Rotation.Angle
            preAnglePt2 = part2.Placement.Rotation.Angle
            #xx

            solved = self.solvelist([cobj]) # solve a single constraint
            if hasattr(part1, "fixedPosition"):
                part1.fixedPosition = p1fix # reset parts fixed
            if hasattr(part2, "fixedPosition"):
                part2.fixedPosition = p2fix


            # Recording location after move
            postBasePt1 = part1.Placement.Base # Round vectors to 6 places
            postBasePt2 = part2.Placement.Base
            postRotPt1 = part1.Placement.Rotation.Axis
            postRotPt2 = part2.Placement.Rotation.Axis
            postAnglePt1 = part1.Placement.Rotation.Angle
            postAnglePt2 = part2.Placement.Rotation.Angle
            localmove = False

            moved = self.partMoved(preBasePt1, postBasePt1, 'xyz', cobj,part1.Label)
            if moved:
                localmove = True
                pass

            moved = self.partMoved(preBasePt2, postBasePt2, 'xyz', cobj, part2.Label)
            if moved:
                localmove = True
                pass

            moved = self.partMoved(preRotPt1, postRotPt1, 'Rotate', cobj, part1.Label)
            if moved:
                localmove = True
                pass

            moved = self.partMoved(preRotPt2, postRotPt2, 'Rotate', cobj, part2.Label)
            if moved:
                localmove = True
                pass

            moved = self.partMoved(preAnglePt1, postAnglePt1,'Angle',cobj,part1.Label)

            if moved:
                localmove = True
                pass
            moved = self.partMoved(preAnglePt2, postAnglePt2, 'Angle', cobj, part2.Label)
            if moved:
                localmove = True
                pass
            partsmoved.append(part1.Label)
            partsmoved.append(part2.Label)


            if putPartBack:
                #Places part back in origial location if put back is True
                part1.Placement.Base = preBase1
                part1.Placement.Rotation.Axis = preRot1
                part1.Placement.Rotation.Angle = preAngle1
                part2.Placement.Base = preBase2
                part2.Placement.Rotation.Axis = preRot2
                part2.Placement.Rotation.Angle = preAngle2



    def partMoved(self, vec1, vec2, movetype, cobj):

        if cobj.Name in g.allErrors.keys():
            return(False)
        errortype = ''
        foundError = False
        moved = ''

        if movetype == 'Angle':
            dis1 = rondnum(vec1)
            dis2 = rondnum(vec2)
            if dis1 != dis2:
                foundError = True
                errortype = 'Conflict'
                moved = movetype

        else:

            v1 = FreeCAD.Vector(rondlist(vec1))
            v2 = FreeCAD.Vector(rondlist(vec2))
            x, y, z = vec1
            v1 = [x, y, z]
            v1 = FreeCAD.Vector(rondlist(v1))

            x, y, z = vec2
            v2 = [x, y, z]
            v2 = FreeCAD.Vector(rondlist(v2))
            if v1 != v2:
                self.test.append(cobj.Name)
                self.test.append([v1])
                self.test.append([v2])
                foundError = True
                errortype = 'Conflict'
                moved = movetype
        if foundError:
            self.addError(cobj, errortype, moved)
        return(foundError)
    def addError(self, cobj, errortype, movetype):
        dict = {'Name':cobj.Name, 'errortype':errortype, 'movetype':movetype}
        g.allErrors[cobj.Name] = dict
    def getallconstraints(self):
        doc = FreeCAD.activeDocument()
        constraints = []
        for obj in doc.Objects:
            if 'ConstraintInfo' in obj.Content:
                if not 'mirror' in obj.Name:
                    constraints.append(obj)

        if len(constraints) == 0:
            mApp('Cannot find any contraints in this file.')
            return(None)
        return(constraints)


    def solveNOoerrorchecking(self):
        cons = self.getallconstraints()
        print(cons)

        self.checkformovement(cons, False)

    def solvelist(self, list):
        # add 1 at a time then solve allSolve
        workList = []
        solved = 'no run'
        doc = FreeCAD.activeDocument()
        for c in list:
            print(c.Name)
            workList.append(c)
            solved = a2p_solversystem.solveConstraints(doc, None, False, matelist = workList, showFailMessage = False)
        return(solved)
CheckConstraints = classCheckConstraints()



def rondlist(list, inch = False):
    x = list[0]
    y = list[1]
    z = list[2]
    x = rondnum(x)
    y = rondnum(y)
    z = rondnum(z)
    if inch:
        x = x/25.4
        y = y/25.4
        z = z/25.4


    return([x, y, z])


def rondnum(num, rndto = g.roundto, mmorin = 'mm'):
    # round a number to digits in global
    # left in mm for accuracy.
    rn = round(num, g.roundto)
    if mmorin == 'in':
        rn = rn / 25.4

    return(rn)




toolTipText = \
'''
Select geometry to be constrained
within 3D View !

Suitable Constraint buttons will
get activated.

Please also read tooltips of each
button.
'''


toolTipText = \
'''
check constraints.
'''

class rnp_Constraint_Checkeralone:

    def Activated(self):
        CheckConstraints.startcheck()

    def onDeleteConstraint(self):
        pass

    def Deactivated():
        pass
        #"""This function is executed when the workbench is deactivated"""


    def GetResources(self):
        mypath = os.path.dirname(__file__)
        return {
             'Pixmap' : mypath + "/icons/ConflictCheckeralone.svg",
             'MenuText': 'Checks constraints',
             'ToolTip': 'Checks constraints'
             }

FreeCADGui.addCommand('rnp_Constraint_Checkeralone', rnp_Constraint_Checkeralone())
#==============================================================================




