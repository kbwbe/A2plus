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
import CD_ConstraintViewer

translate = FreeCAD.Qt.translate

class globaluseclass:
    def __init__(self):
        self.checkingnum = 0
        self.roundto = 3
        #self.labelexist = False
        #self.movedconsts = []
        #self.allErrors = {}
        self.errorList = []
        self.conflicterror = False
g = globaluseclass()


class mApp(QtGui.QWidget):

    # for error messages
    def __init__(self, msg):
        super().__init__()
        self.title = translate("A2plus", "Information")
        self.initUI(msg)

    def initUI(self, msg, msgtype = 'ok'):
        self.setWindowTitle(self.title)
        self.setGeometry(100, 100, 320, 200)
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        if msgtype == 'ok':
            buttonReply = QtGui.QMessageBox.question(self, translate("A2plus", "Information"), msg, QtGui.QMessageBox.Ok | QtGui.QMessageBox.Ok)
        if msgtype == 'yn':
            buttonReply = QtGui.QMessageBox.question(self, translate("A2plus", "Information"), msg, QtGui.QMessageBox.Yes | QtGui.QMessageBox.No, QtGui.QMessageBox.No)
        if buttonReply == QtGui.QMessageBox.Yes:
            pass
            # print('Yes clicked.')
        else:
            pass
            # print('No clicked.')

        self.show()

class formMain(QtGui.QMainWindow):

    def __init__(self, name):
        self.name = name
        super(formMain, self).__init__()
        self.setWindowTitle(translate("A2plus", "Constraint Checker"))
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        self.setGeometry(300, 100, 600, 140)
        self.setStyleSheet("font:11pt arial MS")

        self.txtboxReport = QtGui.QTextEdit(self)
        self.txtboxReport.setGeometry(5, 50, 650, 90) # xy, wh


        self.lblviewlabel = QtGui.QLabel(self)
        self.lblviewlabel.setText(translate("A2plus", "To view the constraints, press 'Open Viewer'"))
        self.lblviewlabel.move(5, 5)
        self.lblviewlabel.setFixedWidth(350)
        self.lblviewlabel.setFixedHeight(20)
        self.lblviewlabel.setStyleSheet("font: 13pt arial MS")

        self.btnOpenViewer = QtGui.QPushButton(self)
        self.btnOpenViewer.move(365, 5)
        self.btnOpenViewer.setFixedWidth(100)
        self.btnOpenViewer.setFixedHeight(28)
        self.btnOpenViewer.setToolTip(translate("A2plus", "View the listed constraints in the the Constraint Viewer."))
        self.btnOpenViewer.setText(translate("A2plus", "Open Viewer"))
        self.btnOpenViewer.clicked.connect(lambda:self.openViewer())

        self.btnCloseForm = QtGui.QPushButton(self)
        self.btnCloseForm.move(475, 5)
        self.btnCloseForm.setFixedWidth(100)
        self.btnCloseForm.setFixedHeight(28)
        self.btnCloseForm.setToolTip(translate("A2plus", "Close this form."))
        self.btnCloseForm.setText(translate("A2plus", "Close"))
        self.btnCloseForm.clicked.connect(lambda:self.Closeme())

    def openViewer(self):
        CD_ConstraintViewer.form1.loadtable(g.errorList)
        #clist = []
        #doc = FreeCAD.activeDocument()
        #for (k, v) in g.allErrors.items():
        #    cobj = doc.getObject(k)
        #    clist.append(cobj)

        #CD_ConstraintViewer.form1.show()
        #CD_ConstraintViewer.form1.loadtable(clist)


    def resizeEvent(self, event):
        # resize table
        formx = self.width()
        formy = self.height()
        self.txtboxReport.resize(formx - 20, formy - 60)

    def showme(self, msg):
        self.txtboxReport.setText(msg)
        self.show()

    def Closeme(self):
        self.close()

    def closeEvent(self, event):
        form1.Closeme()
        self.close()

form1 = formMain('form1')

class classCheckConstraints():
    def __init__(self):
        self.name = None
        self.dir_errors = []
        self.rigids = []
        self.floaters = []
    def startcheck(self):
        ''' Check for opened file '''
        if FreeCAD.activeDocument() is None:
            msg = translate("A2plus", "A A2plus file must be opened to start this checker") + "\n" + translate("A2plus", "Please open a file and try again")
            mApp(msg)
            return

        ''' Getting rigids for a check '''
        doc = FreeCAD.activeDocument()
        ss = a2p_solversystem.SolverSystem()
        ss.loadSystem(doc)
        ss.assignParentship(doc)
        rigids = ss.rigids
        for e in rigids: # get rigid part
            if e.disatanceFromFixed is None:
                self.floaters.append(e.label)
            self.rigids.append(e.label)
        constraints = self.getallconstraints()
        if len(constraints) == 0:
            mApp(translate("A2plus", "Cannot find any constraints in this file."))
            return()

        statusform.showme(translate("A2plus", "Checking constraints"))
        self.dir_errors = a2p_constraintServices.redAdjustConstraintDirections(FreeCAD.activeDocument())
        print(self.dir_errors)
        self.checkformovement(constraints, True)
        if len(g.errorList) != 0:
            form1.openViewer()
            #msg = ''
            #for e in g.allErrors:
            #    line = str(g.allErrors.get(e))
            #    msg = msg + line + '\n'
            #form1.showme(msg)
        else:
            FreeCAD.Console.PrintMessage("")
            FreeCAD.Console.PrintMessage(translate("A2plus", "No constraint errors found") + "\n")
        statusform.Closeme()


    def checkformovement(self, constraintlist, putPartBack = True):
        doc = FreeCAD.activeDocument()
        g.errorList = []
        self.Bothpartsfixed = False

        for checkingnum in range(0, len(constraintlist)):
            self.errortype = ''
            self.p1fix = False
            self.p2fix = False
            self.setfix = 0
            cobj = constraintlist[checkingnum]
            statusform.setWindowTitle(translate("A2plus", "Checking ") + str(checkingnum) + translate("A2plus", " of ") + str(len(constraintlist)))
            

            subobj1 = cobj.getPropertyByName('Object1')
            subobj2 = cobj.getPropertyByName('Object2')
            part1 = doc.getObject(subobj1) # Save Position and fixed
            part2 = doc.getObject(subobj2)
            
            ''' Get if part is fixed '''
            if hasattr(part1, "fixedPosition"):
                self.p1fix = part1.fixedPosition
            if hasattr(part2, "fixedPosition"):
                self.p2fix = part2.fixedPosition

            if cobj.Name in self.dir_errors: 
                errortype = 'Feature Missing'
                self.addError(cobj, errortype)
                continue

            if self.p1fix and self.p2fix:
                """ If both are fixed report and skip solving"""
                self.addError(cobj, 'Both fixed')
                continue
            
            if part1.Label in self.floaters and part2.Label in self.floaters:
                # If both parts are in floaters list report as Floaters
                self.addError(cobj,'Floating parts')
                continue
            if self.p1fix == False and self.p2fix == False:
                """ If neither part is fixed, fix part 1"""
                if part1.Label in self.rigids:
                    part1.fixedPosition = True
                    self.setfix = 1
                else:
                    part2.fixedPosition = True
                    self.setfix = 2

            preBasePt1 = part1.Placement.Base
            preBasePt2 = part2.Placement.Base
            preRotPt1 = part1.Placement.Rotation.Axis
            preRotPt2 = part2.Placement.Rotation.Axis
            preAnglePt1 = part1.Placement.Rotation.Angle
            preAnglePt2 = part2.Placement.Rotation.Angle

            a2p_solversystem.solveConstraints(FreeCAD.activeDocument(), None, False, [cobj], showFailMessage = False) # solve a single constraint
            if self.setfix == 1:
                part1.fixedPosition = self.p1fix
            if self.setfix == 2:
                part2.fixedPosition = self.p2fix
            self.setfix = 0

            # Recording location after move
            postBasePt1 = part1.Placement.Base  # Round vectors to 4 places
            postBasePt2 = part2.Placement.Base
 
            ''' Checking if part moved '''
            v1 = FreeCAD.Vector(rondlist(preBasePt1))
            v2 = FreeCAD.Vector(rondlist(postBasePt1)) 
            v3 = FreeCAD.Vector(rondlist(preBasePt2))
            v4 = FreeCAD.Vector(rondlist(postBasePt2))
            if v1 != v2 or v3 != v4:
                self.errortype = 'Conflict. '
                self.addError(cobj, self.errortype)
            errortype = ''


            if putPartBack:
                # Places part back in original location if putPartBack is True
                part1.Placement.Base = preBasePt1
                part1.Placement.Rotation.Axis = preRotPt1
                part1.Placement.Rotation.Angle = preAnglePt1
                part2.Placement.Base = preBasePt2
                part2.Placement.Rotation.Axis = preRotPt2
                part2.Placement.Rotation.Angle = preAnglePt2
            

    def addError(self, cobj, errortype):
            g.errorList.append([cobj, errortype])

    def getallconstraints(self):
        doc = FreeCAD.activeDocument()
        constraints = []
        for obj in doc.Objects:
            if 'ConstraintInfo' in obj.Content:
                if not 'mirror' in obj.Name:
                    constraints.append(obj)
        return(constraints)
CheckConstraints = classCheckConstraints()


class formReport(QtGui.QDialog):
    """ Form shows while updating edited parts. """
    def __init__(self, name):
        self.name = name
        super(formReport, self).__init__()
        self.setWindowTitle(translate("A2plus", "Checking Constraints"))
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        self.setGeometry(300, 100, 300, 40) # xy , wh
        self.setStyleSheet("font: 10pt arial MS") 

    def showme(self, msg):
        self.setWindowTitle(msg)
        self.show()
    def Closeme(self):
        self.close()

    def closeEvent(self, event):
        self.close()
statusform = formReport('statusform')


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


def rondnum(num, mmorin = 'mm'):
    # round a number to digits in global
    # left in mm for accuracy.
    rn = round(num, g.roundto)
    if mmorin == 'in':
        rn = rn / 25.4
    return(rn)


toolTipText = \
    translate("A2plus", "This checks all constraints. After checking it will list all constraints that it found problems with.") + "/n" +\
    translate("A2plus", "The list can then be opened in the Constraint viewer.")

class rnp_Constraint_Checker:

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
             'Pixmap' : mypath + "/icons/CD_ConstraintChecker.svg",
             'MenuText': translate("A2plus", "Checks constraints"),
             'ToolTip': translate("A2plus", "Checks constraints")
             }

FreeCADGui.addCommand('rnp_Constraint_Checker', rnp_Constraint_Checker())
#==============================================================================
