#***************************************************************************
#*                                                                         *
#*   Copyright (c) 2018 kbwbe                                              *
#*                                                                         *
#*   Portions of code based on hamish's assembly 2                         *
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

import FreeCAD, FreeCADGui, Part
from PySide import QtGui, QtCore
import os, sys, math, copy
#from a2p_viewProviderProxies import *
from  FreeCAD import Base
from a2p_translateUtils import *

import a2plib
from a2plib import *
from a2p_solversystem import solveConstraints
import a2p_constraints

from FreeCAD import Units


CONSTRAINT_DIALOG_STORED_POSITION = QtCore.QPoint(-1,-1)

#==============================================================================
class a2p_ConstraintValueWidget(QtGui.QWidget):
#class a2p_ConstraintValueWidget(QtGui.QDialog):

    Deleted = QtCore.Signal()
    Accepted = QtCore.Signal()


    def __init__(self,parent,constraintObject, mode):
        super(a2p_ConstraintValueWidget,self).__init__(parent=parent)
        self.mode = mode # either "editConstraint" or "createConstraint"
        self.constraintObject = constraintObject  # The documentObject of a constraint!

        self.savedOffset = None
        self.savedDirectionConstraint = None
        self.savedAngle = None
        self.savedLockRotation = None
        if hasattr(self.constraintObject,'offset'):
            self.savedOffset = self.constraintObject.offset
        if hasattr(self.constraintObject,'directionConstraint'):
            self.savedDirectionConstraint = self.constraintObject.directionConstraint
        if hasattr(self.constraintObject,'angle'):
            self.savedAngle = self.constraintObject.angle
        if hasattr(self.constraintObject,'lockRotation'):
            self.savedLockRotation = self.constraintObject.lockRotation

        self.winModified = False
        self.lineNo = 0
        self.neededHight = 0
        self.isTopLevelWin = True  # Window management
        self.position = None       # Window position
        self.recentUnit = "mm"
        self.initUI()

    def initUI(self):
        #self.setMinimumHeight(self.minHeight)
        self.setWindowTitle(translate("A2plus_constraintDialog",'Constraint properties'))
        #self.resize(300,600)

        self.mainLayout = QtGui.QGridLayout() # a VBoxLayout for the whole form
        #==============================
        lbl1 = QtGui.QLabel(self)
        lbl1.setText(self.constraintObject.Label)
        lbl1.setFrameStyle(
            QtGui.QFrame.Panel |
            QtGui.QFrame.Sunken
            )
        self.mainLayout.addWidget(lbl1,self.lineNo,0,1,4)
        self.lineNo += 1

        #==============================
        if hasattr(self.constraintObject,"directionConstraint"):
            lbl3 = QtGui.QLabel(self)
            lbl3.setText(translate("A2plus_constraintDialog", "Direction"))
            lbl3.setFixedHeight(32)
            self.mainLayout.addWidget(lbl3,self.lineNo,0)

            # create items list for QComboBox
            self.directionCombo = QtGui.QComboBox(self)
            self.directionCombo.insertItem(0,translate("A2plus_constraintDialog", "aligned"))
            self.directionCombo.insertItem(1,translate("A2plus_constraintDialog", "opposed"))

            d = self.constraintObject.directionConstraint # not every constraint has a direction
            #
            # for compat with old A2plus assemblies
            if d == "none":
                self.directionCombo.insertItem(2,translate("A2plus_constraintDialog", "none"))

            # activate item of list
            if d == "aligned":
                self.directionCombo.setCurrentIndex(0)
            elif d == "opposed":
                self.directionCombo.setCurrentIndex(1)
            elif d == "none": # will only occur with old A2plus assemblies
                self.directionCombo.setCurrentIndex(2)

            self.directionCombo.setFixedHeight(32)
            self.directionCombo.currentIndexChanged[int].connect(self.flipDirection2)
            self.mainLayout.addWidget(self.directionCombo,self.lineNo,1)

            self.flipDirectionButton = QtGui.QPushButton(self)
            self.flipDirectionButton.setIcon(QtGui.QIcon(':/icons/a2p_FlipConstraint.svg'))
            self.flipDirectionButton.setText(translate("A2plus_constraintDialog", "Flip direction"))
            self.flipDirectionButton.setFixedHeight(32)
            QtCore.QObject.connect(self.flipDirectionButton, QtCore.SIGNAL("clicked()"), self.flipDirection)
            self.mainLayout.addWidget(self.flipDirectionButton,self.lineNo,2)

            self.lineNo += 1

        #==============================
        if hasattr(self.constraintObject,"offset"):
            offs = self.constraintObject.offset
            lbl4 = QtGui.QLabel(self)
            lbl4.setText(translate("A2plus_constraintDialog", "Offset"))
            lbl4.setFixedHeight(32)
            self.mainLayout.addWidget(lbl4,self.lineNo,0)

            self.offsetEdit = QtGui.QDoubleSpinBox(self)

            # the maximum is by default 99.99 and we can allow more
            self.offsetEdit.setMaximum(1e7) # allow up to 1 km
            # set minimum to negative of maximum
            self.offsetEdit.setMinimum(-1*self.offsetEdit.maximum())

            # use the number of decimals defined by thew user in FC
            params = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Units")
            self.offsetEdit.setDecimals(params.GetInt('Decimals'))

            userPreferred = Units.Quantity(offs).getUserPreferred()

            user_qty = Units.Quantity(offs).Value

            self.recentUnit = str(FreeCAD.Units.Quantity(1, FreeCAD.Units.Length))[3:]
            self.offsetEdit.setSuffix(" " + self.recentUnit)
            self.offsetEdit.setValue(user_qty)
            self.offsetEdit.setSingleStep(userPreferred[1])

            self.offsetEdit.setFixedHeight(32)
            QtCore.QObject.connect(self.offsetEdit, QtCore.SIGNAL("valueChanged(double)"), self.handleOffsetChanged)
            self.mainLayout.addWidget(self.offsetEdit,self.lineNo,1)

            self.offsetSetZeroButton = QtGui.QPushButton(self)
            self.offsetSetZeroButton.setText(translate("A2plus_constraintDialog", "Set Zero"))
            self.offsetSetZeroButton.setFixedHeight(32)
            QtCore.QObject.connect(self.offsetSetZeroButton, QtCore.SIGNAL("clicked()"), self.setOffsetZero)
            self.mainLayout.addWidget(self.offsetSetZeroButton,self.lineNo,2)

            self.flipOffsetSignButton = QtGui.QPushButton(self)
            self.flipOffsetSignButton.setText(translate("A2plus_constraintDialog", "Flip sign"))
            self.flipOffsetSignButton.setFixedHeight(32)
            QtCore.QObject.connect(self.flipOffsetSignButton, QtCore.SIGNAL("clicked()"), self.flipOffsetSign)
            self.mainLayout.addWidget(self.flipOffsetSignButton,self.lineNo,3)

            self.lineNo += 1

        #==============================
        if hasattr(self.constraintObject,"angle"):
            angle = self.constraintObject.angle
            lbl5 = QtGui.QLabel(self)
            lbl5.setText(translate("A2plus_constraintDialog", "Angle"))
            lbl5.setFixedHeight(32)
            self.mainLayout.addWidget(lbl5,self.lineNo,0)

            self.angleEdit = QtGui.QDoubleSpinBox(self)
            # get the angle unit as string
            self.angleEdit.setSuffix(" " + str(FreeCAD.Units.Quantity(1, FreeCAD.Units.Angle))[3:])

            if self.constraintObject.Type == "axisPlaneAngle":
                self.angleEdit.setMaximum(90.0)
                self.angleEdit.setMinimum(0.0)  # the solver treats negative values as positive
            else:
                self.angleEdit.setMaximum(180)
                self.angleEdit.setMinimum(0)    # the solver treats negative values as positive

            # use the number of decimals defined by the user in FC
            params = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Units")
            self.angleEdit.setDecimals(params.GetInt('Decimals'))
            self.angleEdit.setValue(angle)
            self.angleEdit.setFixedHeight(32)
            self.angleEdit.setToolTip(translate("A2plus_constraintDialog", "Angle in the range 0 - 180 degrees"))
            QtCore.QObject.connect(self.angleEdit, QtCore.SIGNAL("valueChanged(double)"), self.handleAngleChanged)
            self.mainLayout.addWidget(self.angleEdit,self.lineNo,1)

            self.roundAngleButton = QtGui.QPushButton(self)
            self.roundAngleButton.setText(translate("A2plus_constraintDialog", "Round"))
            self.roundAngleButton.setFixedHeight(32)
            self.roundAngleButton.setToolTip(translate("A2plus_constraintDialog", "Round angle to multiples of 5"))
            QtCore.QObject.connect(self.roundAngleButton, QtCore.SIGNAL("clicked()"), self.roundAngle)
            self.mainLayout.addWidget(self.roundAngleButton,self.lineNo,2)

            self.perpendicularAngleButton = QtGui.QPushButton(self)
            self.perpendicularAngleButton.setText(translate("A2plus_constraintDialog", "Perpendicular"))
            self.perpendicularAngleButton.setFixedHeight(32)
            self.perpendicularAngleButton.setToolTip(translate("A2plus_constraintDialog", "Adds/deletes 90 degrees"))
            QtCore.QObject.connect(self.perpendicularAngleButton, QtCore.SIGNAL("clicked()"), self.perpendicularAngle)
            self.mainLayout.addWidget(self.perpendicularAngleButton,self.lineNo,3)

            self.lineNo += 1

        #==============================
        if hasattr(self.constraintObject,"lockRotation"):
            lbl6 = QtGui.QLabel(self)
            lbl6.setText(translate("A2plus_constraintDialog", "Lock Rotation"))
            lbl6.setFixedHeight(32)
            self.mainLayout.addWidget(lbl6,self.lineNo,0)

            self.lockRotationCombo = QtGui.QComboBox(self)
            self.lockRotationCombo.insertItem(0,"False")
            self.lockRotationCombo.insertItem(1,"True")
            if self.constraintObject.lockRotation: # not every constraint has a direction
                self.lockRotationCombo.setCurrentIndex(1)
            else:
                self.lockRotationCombo.setCurrentIndex(0)
            self.lockRotationCombo.setFixedHeight(32)
            self.mainLayout.addWidget(self.lockRotationCombo,self.lineNo,1)

            self.flipLockRotationButton = QtGui.QPushButton(self)
            self.flipLockRotationButton.setIcon(QtGui.QIcon(':/icons/a2p_LockRotation.svg'))
            self.flipLockRotationButton.setText(translate("A2plus_constraintDialog", "Toggle"))
            self.flipLockRotationButton.setFixedHeight(32)
            QtCore.QObject.connect(self.flipLockRotationButton, QtCore.SIGNAL("clicked()"), self.flipLockRotation)
            self.mainLayout.addWidget(self.flipLockRotationButton,self.lineNo,2)

            self.lineNo += 1

        #==============================

        self.buttonPanel = QtGui.QWidget(self)
        self.buttonPanel.setFixedHeight(60)
        self.buttonPanel.setContentsMargins(4,4,4,4)
        self.buttonPanelLayout = QtGui.QHBoxLayout()

        self.deleteButton = QtGui.QPushButton(self.buttonPanel)
        self.deleteButton.setFixedHeight(32)
        self.deleteButton.setIcon(QtGui.QIcon(':/icons/a2p_DeleteConnections.svg')) #need new Icon
        self.deleteButton.setToolTip(translate("A2plus_constraintDialog", "Delete this constraint"))
        self.deleteButton.setText(translate("A2plus_constraintDialog", "Delete this constraint"))

        self.solveButton = QtGui.QPushButton(self.buttonPanel)
        self.solveButton.setFixedHeight(32)
        self.solveButton.setIcon(QtGui.QIcon(':/icons/a2p_Solver.svg'))
        self.solveButton.setToolTip(translate("A2plus_constraintDialog", "Solve constraints"))
        self.solveButton.setText(translate("A2plus_constraintDialog", "Solve"))

        self.acceptButton = QtGui.QPushButton(self.buttonPanel)
        self.acceptButton.setFixedHeight(32)
        self.acceptButton.setIcon(QtGui.QIcon(':/icons/a2p_CheckAssembly.svg')) #need new Icon
        self.acceptButton.setToolTip(translate("A2plus_constraintDialog", "Accept the settings"))
        self.acceptButton.setText(translate("A2plus_constraintDialog", "Accept"))
        #self.acceptButton.setDefault(True)

        self.buttonPanelLayout.addWidget(self.deleteButton)
        self.buttonPanelLayout.addWidget(self.solveButton)
        self.buttonPanelLayout.addWidget(self.acceptButton)
        self.buttonPanel.setLayout(self.buttonPanelLayout)

        self.mainLayout.addWidget(self.buttonPanel,self.lineNo,0,1,4)
        self.lineNo += 1

        #==============================
        self.setLayout(self.mainLayout)
        #self.updateGeometry()
        #self.neededHight = 50+(self.lineNo+1)*40
        #self.resize(self.neededHight,350)
        QtCore.QObject.connect(self.deleteButton, QtCore.SIGNAL("clicked()"), self.delete)
        QtCore.QObject.connect(self.solveButton, QtCore.SIGNAL("clicked()"), self.solve)
        QtCore.QObject.connect(self.acceptButton, QtCore.SIGNAL("clicked()"), self.accept)
        #==============================

    def setConstraintEditorData(self):
        if hasattr(self.constraintObject,"directionConstraint"):
            if self.directionCombo.currentIndex() == 0:
                self.constraintObject.directionConstraint = "aligned"
            elif self.directionCombo.currentIndex() == 1:
                self.constraintObject.directionConstraint = "opposed"
            else:
                self.constraintObject.directionConstraint = "none"

        if hasattr(self.constraintObject,"offset"):
            userValueStr = str(self.offsetEdit.value()) + " " + self.recentUnit
            self.constraintObject.offset = Units.Quantity(userValueStr).Value

        if hasattr(self.constraintObject,"angle"):
            self.constraintObject.angle = self.angleEdit.value()
        if hasattr(self.constraintObject,"lockRotation"):
            if self.lockRotationCombo.currentIndex() == 0:
                self.constraintObject.lockRotation = False
            else:
                self.constraintObject.lockRotation = True

    def solve(self):
        doc = FreeCAD.activeDocument()
        if self.constraintObject not in doc.Objects:
            QtGui.QMessageBox.information(
                QtGui.QApplication.activeWindow(),
                translate("A2plus_constraintDialog","Constraint does not exist anymore"),
                translate("A2plus_constraintDialog","Constraint has already been deleted")
                )
            a2plib.setConstraintEditorRef(None)
            self.Deleted.emit()
            return

        self.winModified = True
        self.setConstraintEditorData()
        doc = FreeCAD.activeDocument()
        if doc is not None:
            solveConstraints(doc)
            doc.recompute()

    def flipLockRotation(self):
        self.winModified = True
        if self.lockRotationCombo.currentIndex() == 0:
            self.lockRotationCombo.setCurrentIndex(1)
        else:
            self.lockRotationCombo.setCurrentIndex(0)

    def handleOffsetChanged(self):
        self.winModified = True
        # recalculate after every change
        if a2plib.getAutoSolveState():
            self.solve()

    def setOffsetZero(self):
        self.winModified = True
        self.offsetEdit.setValue(0.0)
        if a2plib.getAutoSolveState():
            self.solve()

    def flipOffsetSign(self):
        self.winModified = True
        q = self.offsetEdit.value()
        q = -q
        if abs(q) > 1e-7:
            self.offsetEdit.setValue(q)
            if a2plib.getAutoSolveState():
                self.solve()
        else:
            self.offsetEdit.setValue(0.0)
            if a2plib.getAutoSolveState():
                self.solve()

    def flipDirection2(self,idx):
        self.winModified = True
        if a2plib.getAutoSolveState():
            self.solve()

    def flipDirection(self):
        self.winModified = True
        if self.directionCombo.currentIndex() == 0:
            self.directionCombo.setCurrentIndex(1)
        else:
            self.directionCombo.setCurrentIndex(0)
        if a2plib.getAutoSolveState():
            self.solve()

    def handleAngleChanged(self):
        self.winModified = True
        # recalculate after every change
        if a2plib.getAutoSolveState():
            self.solve()

    def roundAngle(self):
        # rounds angle to 5 degrees
        self.winModified = True
        q = self.angleEdit.value() / 5
        q = round(q)
        q = q * 5
        self.angleEdit.setValue(q)
        if a2plib.getAutoSolveState():
            self.solve()

    def perpendicularAngle(self):
        if self.constraintObject.Type == "axisPlaneAngle":
            # we want to go this way: 0 -> 90 -> 0
            self.winModified = True
            q = self.angleEdit.value()
            if q>=45:
                self.angleEdit.setValue(0)
            else:
                self.angleEdit.setValue(90)
            if a2plib.getAutoSolveState():
                self.solve()
        else:
            #adds /subtracs 90 degrees
            # we want to go this way: 0 -> 90 -> 180 -> 90 -> 0
            # but: 12 -> 102 -> 12
            self.winModified = True
            q = self.angleEdit.value() + 90
            if q == 270:
                self.angleEdit.setValue(0)
            elif q > 180:
                self.angleEdit.setValue(q - 180)
            elif q <= 180:
                self.angleEdit.setValue(q)
            if a2plib.getAutoSolveState():
                self.solve()

    def restoreConstraintValues(self):
        if self.savedOffset is not None:
            self.constraintObject.offset = self.savedOffset
        if self.savedDirectionConstraint is not None:
            self.constraintObject.directionConstraint = self.savedDirectionConstraint
        if self.savedAngle is not None:
            self.constraintObject.angle = self.savedAngle
        if self.savedLockRotation is not None:
            self.constraintObject.lockRotation = self.savedLockRotation

    def delete(self):
        doc = FreeCAD.activeDocument()
        if self.constraintObject not in doc.Objects:
            QtGui.QMessageBox.information(
                QtGui.QApplication.activeWindow(),
                translate("A2plus_constraintDialog","Constraint does not exist anymore"),
                translate("A2plus_constraintDialog","Constraint has already been deleted")
                )
            a2plib.setConstraintEditorRef(None)
            self.Deleted.emit()
            return

        flags = QtGui.QMessageBox.StandardButton.Yes | QtGui.QMessageBox.StandardButton.No
        response = QtGui.QMessageBox.information(
            QtGui.QApplication.activeWindow(),
            translate("A2plus_constraintDialog","Confirmation required"),
            translate("A2plus_constraintDialog","Really delete this constraint?"),
            flags
            )
        if response == QtGui.QMessageBox.Yes:
            try:
                removeConstraint(self.constraintObject)
            except:
                pass # perhaps constraint already deleted by user
            a2plib.setConstraintEditorRef(None)
            self.Deleted.emit()

    def keyPressEvent(self,e):
        if e.key() == QtCore.Qt.Key_Enter:
            self.accept()
        if e.key() == QtCore.Qt.Key_Return:
            self.accept()

    def accept(self):
        doc = FreeCAD.activeDocument()
        if self.constraintObject not in doc.Objects:
            QtGui.QMessageBox.information(
                QtGui.QApplication.activeWindow(),
                translate("A2plus_constraintDialog","Constraint does not exist anymore"),
                translate("A2plus_constraintDialog","Constraint has already been deleted")
                )
            a2plib.setConstraintEditorRef(None)
            self.Deleted.emit()
            return

        self.setConstraintEditorData()
        self.Accepted.emit()

    def cancelOperation(self):
        doc = FreeCAD.activeDocument()
        if self.constraintObject not in doc.Objects:
            QtGui.QMessageBox.information(
                QtGui.QApplication.activeWindow(),
                translate("A2plus_constraintDialog","Constraint does not exist anymore"),
                translate("A2plus_constraintDialog","Constraint has already been deleted")
                )
            a2plib.setConstraintEditorRef(None)
            self.Deleted.emit()
            return

        if self.mode == 'createConstraint':
            flags = QtGui.QMessageBox.StandardButton.Yes | QtGui.QMessageBox.StandardButton.No
            response = QtGui.QMessageBox.information(
                QtGui.QApplication.activeWindow(),
                translate("A2plus_constraintDialog","Confirmation required"),
                translate("A2plus_constraintDialog","Exit and delete new constraint?"),
                flags
                )
            if response == QtGui.QMessageBox.Yes:
                a2plib.setConstraintEditorRef(None)
                self.Deleted.emit()
            else:
                self.restoreConstraintValues()
        else:
            if self.isWindowModified() or self.winModified:
                flags = QtGui.QMessageBox.StandardButton.Yes | QtGui.QMessageBox.StandardButton.No
                response = QtGui.QMessageBox.information(
                    QtGui.QApplication.activeWindow(),
                    translate("A2plus_constraintDialog","Information"),
                    translate("A2plus_constraintDialog","Values changed! Accept Constraint?"),
                    flags
                    )
                if response == QtGui.QMessageBox.Yes:
                    self.setConstraintEditorData()
                    a2plib.setConstraintEditorRef(None)
                    self.Accepted.emit()
                else:
                    self.restoreConstraintValues()
                    a2plib.setConstraintEditorRef(None)
                    self.Accepted.emit()
            else:
                a2plib.setConstraintEditorRef(None)
                self.Accepted.emit()

#==============================================================================
toolTipText = \
translate("A2plus_constraintDialog",
'''
Select geometry to be constrained
within 3D View !

Suitable Constraint buttons will
get activated.

Please also read tooltips of each
button.
'''
)

class a2p_ConstraintCollection(QtGui.QWidget):
    def __init__(self,parent):
        super(a2p_ConstraintCollection,self).__init__(parent=parent)
        self.constraintButtons = []
        self.activeConstraint = None
        self.position = None # Window position
        self.initUI()

    def initUI(self):
        self.setWindowTitle(translate("A2plus_constraintDialog",'Constraint Tools'))
        #self.setMinimumHeight(self.baseHeight)
        self.mainLayout = QtGui.QVBoxLayout() # a VBoxLayout for the whole form


        #-------------------------------------
        self.panel1 = QtGui.QWidget(self)
        self.panel1.setMinimumHeight(60)
        panel1_Layout = QtGui.QHBoxLayout()
        #-------------------------------------
        self.pointIdentityButton = QtGui.QPushButton(self.panel1)
        self.pointIdentityButton.setFixedSize(48,48)
        self.pointIdentityButton.setIcon(QtGui.QIcon(':/icons/a2p_PointIdentity.svg'))
        self.pointIdentityButton.setIconSize(QtCore.QSize(32,32))
        self.pointIdentityButton.setToolTip(a2p_constraints.PointIdentityConstraint.getToolTip())
        self.pointIdentityButton.setText("")
        QtCore.QObject.connect(self.pointIdentityButton, QtCore.SIGNAL("clicked()"), self.onPointIdentityButton)
        self.constraintButtons.append(self.pointIdentityButton)
        #-------------------------------------
        self.pointOnLineButton = QtGui.QPushButton(self.panel1)
        self.pointOnLineButton.setFixedSize(48,48)
        self.pointOnLineButton.setIcon(QtGui.QIcon(':/icons/a2p_PointOnLineConstraint.svg'))
        self.pointOnLineButton.setIconSize(QtCore.QSize(32,32))
        self.pointOnLineButton.setToolTip(a2p_constraints.PointOnLineConstraint.getToolTip())
        self.pointOnLineButton.setText("")
        QtCore.QObject.connect(self.pointOnLineButton, QtCore.SIGNAL("clicked()"), self.onPointOnLineButton)
        self.constraintButtons.append(self.pointOnLineButton)
        #-------------------------------------
        self.pointOnPlaneButton = QtGui.QPushButton(self.panel1)
        self.pointOnPlaneButton.setFixedSize(48,48)
        self.pointOnPlaneButton.setIcon(QtGui.QIcon(':/icons/a2p_PointOnPlaneConstraint.svg'))
        self.pointOnPlaneButton.setIconSize(QtCore.QSize(32,32))
        self.pointOnPlaneButton.setToolTip(a2p_constraints.PointOnPlaneConstraint.getToolTip())
        self.pointOnPlaneButton.setText("")
        QtCore.QObject.connect(self.pointOnPlaneButton, QtCore.SIGNAL("clicked()"), self.onPointOnPlaneButton)
        self.constraintButtons.append(self.pointOnPlaneButton)
        #-------------------------------------
        self.sphericalConstraintButton = QtGui.QPushButton(self.panel1)
        self.sphericalConstraintButton.setFixedSize(48,48)
        self.sphericalConstraintButton.setIcon(QtGui.QIcon(':/icons/a2p_SphericalSurfaceConstraint.svg'))
        self.sphericalConstraintButton.setIconSize(QtCore.QSize(32,32))
        self.sphericalConstraintButton.setToolTip(a2p_constraints.SphericalConstraint.getToolTip())
        self.sphericalConstraintButton.setText("")
        QtCore.QObject.connect(self.sphericalConstraintButton, QtCore.SIGNAL("clicked()"), self.onSpericalConstraintButton)
        self.constraintButtons.append(self.sphericalConstraintButton)
        #-------------------------------------
        panel1_Layout.addWidget(self.pointIdentityButton)
        panel1_Layout.addWidget(self.pointOnLineButton)
        panel1_Layout.addWidget(self.pointOnPlaneButton)
        panel1_Layout.addWidget(self.sphericalConstraintButton)
        panel1_Layout.addStretch(1)
        self.panel1.setLayout(panel1_Layout)
        #-------------------------------------


        #-------------------------------------
        self.panel2 = QtGui.QWidget(self)
        self.panel2.setMinimumHeight(60)
        panel2_Layout = QtGui.QHBoxLayout()
        #-------------------------------------
        self.circularEdgeButton = QtGui.QPushButton(self.panel2)
        self.circularEdgeButton.setFixedSize(48,48)
        self.circularEdgeButton.setIcon(QtGui.QIcon(':/icons/a2p_CircularEdgeConstraint.svg'))
        self.circularEdgeButton.setIconSize(QtCore.QSize(32,32))
        self.circularEdgeButton.setToolTip(a2p_constraints.CircularEdgeConstraint.getToolTip())
        self.circularEdgeButton.setText("")
        QtCore.QObject.connect(self.circularEdgeButton, QtCore.SIGNAL("clicked()"), self.onCircularEdgeButton)
        self.constraintButtons.append(self.circularEdgeButton)
        #-------------------------------------
        self.axialButton = QtGui.QPushButton(self.panel2)
        self.axialButton.setFixedSize(48,48)
        self.axialButton.setIcon(QtGui.QIcon(':/icons/a2p_AxialConstraint.svg'))
        self.axialButton.setIconSize(QtCore.QSize(32,32))
        self.axialButton.setToolTip(a2p_constraints.AxialConstraint.getToolTip())
        self.axialButton.setText("")
        QtCore.QObject.connect(self.axialButton, QtCore.SIGNAL("clicked()"), self.onAxialButton)
        self.constraintButtons.append(self.axialButton)
        #-------------------------------------
        self.axisParallelButton = QtGui.QPushButton(self.panel2)
        self.axisParallelButton.setFixedSize(48,48)
        self.axisParallelButton.setIcon(QtGui.QIcon(':/icons/a2p_AxisParallelConstraint.svg'))
        self.axisParallelButton.setIconSize(QtCore.QSize(32,32))
        self.axisParallelButton.setToolTip(a2p_constraints.AxisParallelConstraint.getToolTip())
        self.axisParallelButton.setText("")
        QtCore.QObject.connect(self.axisParallelButton, QtCore.SIGNAL("clicked()"), self.onAxisParallelButton)
        self.constraintButtons.append(self.axisParallelButton)
        #-------------------------------------
        self.axisPlaneParallelButton = QtGui.QPushButton(self.panel2)
        self.axisPlaneParallelButton.setFixedSize(48,48)
        self.axisPlaneParallelButton.setIcon(QtGui.QIcon(':/icons/a2p_AxisPlaneParallelConstraint.svg'))
        self.axisPlaneParallelButton.setIconSize(QtCore.QSize(32,32))
        self.axisPlaneParallelButton.setToolTip(a2p_constraints.AxisPlaneParallelConstraint.getToolTip())
        self.axisPlaneParallelButton.setText("")
        QtCore.QObject.connect(self.axisPlaneParallelButton, QtCore.SIGNAL("clicked()"), self.onAxisPlaneParallelButton)
        self.constraintButtons.append(self.axisPlaneParallelButton)
        #-------------------------------------
        self.axisPlaneNormalButton = QtGui.QPushButton(self.panel2)
        self.axisPlaneNormalButton.setFixedSize(48,48)
        self.axisPlaneNormalButton.setIcon(QtGui.QIcon(':/icons/a2p_AxisPlaneNormalConstraint.svg'))
        self.axisPlaneNormalButton.setIconSize(QtCore.QSize(32,32))
        self.axisPlaneNormalButton.setToolTip(a2p_constraints.AxisPlaneNormalConstraint.getToolTip())
        self.axisPlaneNormalButton.setText("")
        QtCore.QObject.connect(self.axisPlaneNormalButton, QtCore.SIGNAL("clicked()"), self.onAxisPlaneNormalButton)
        self.constraintButtons.append(self.axisPlaneNormalButton)
        #-------------------------------------
        self.axisPlaneAngleButton = QtGui.QPushButton(self.panel2)
        self.axisPlaneAngleButton.setFixedSize(48,48)
        self.axisPlaneAngleButton.setIcon(QtGui.QIcon(':/icons/a2p_AxisPlaneAngleConstraint.svg'))
        self.axisPlaneAngleButton.setIconSize(QtCore.QSize(32,32))
        self.axisPlaneAngleButton.setToolTip(a2p_constraints.AxisPlaneAngleConstraint.getToolTip())
        self.axisPlaneAngleButton.setText("")
        QtCore.QObject.connect(self.axisPlaneAngleButton, QtCore.SIGNAL("clicked()"), self.onAxisPlaneAngleButton)
        self.constraintButtons.append(self.axisPlaneAngleButton)
        #-------------------------------------
        panel2_Layout.addWidget(self.circularEdgeButton)
        panel2_Layout.addWidget(self.axialButton)
        panel2_Layout.addWidget(self.axisParallelButton)
        panel2_Layout.addWidget(self.axisPlaneParallelButton)
        panel2_Layout.addWidget(self.axisPlaneNormalButton)
        panel2_Layout.addWidget(self.axisPlaneAngleButton)
        panel2_Layout.addStretch(1)
        self.panel2.setLayout(panel2_Layout)
        #-------------------------------------


        #-------------------------------------
        self.panel3 = QtGui.QWidget(self)
        self.panel3.setMinimumHeight(60)
        panel3_Layout = QtGui.QHBoxLayout()
        #-------------------------------------
        self.planesParallelButton = QtGui.QPushButton(self.panel3)
        self.planesParallelButton.setFixedSize(48,48)
        self.planesParallelButton.setIcon(QtGui.QIcon(':/icons/a2p_PlanesParallelConstraint.svg'))
        self.planesParallelButton.setIconSize(QtCore.QSize(32,32))
        self.planesParallelButton.setToolTip(a2p_constraints.PlanesParallelConstraint.getToolTip())
        self.planesParallelButton.setText("")
        QtCore.QObject.connect(self.planesParallelButton, QtCore.SIGNAL("clicked()"), self.onPlanesParallelButton)
        self.constraintButtons.append(self.planesParallelButton)
        #-------------------------------------
        self.planeCoincidentButton = QtGui.QPushButton(self.panel3)
        self.planeCoincidentButton.setFixedSize(48,48)
        self.planeCoincidentButton.setIcon(QtGui.QIcon(':/icons/a2p_PlaneCoincidentConstraint.svg'))
        self.planeCoincidentButton.setIconSize(QtCore.QSize(32,32))
        self.planeCoincidentButton.setToolTip(a2p_constraints.PlaneConstraint.getToolTip())
        self.planeCoincidentButton.setText("")
        QtCore.QObject.connect(self.planeCoincidentButton, QtCore.SIGNAL("clicked()"), self.onPlaneCoincidentButton)
        self.constraintButtons.append(self.planeCoincidentButton)
        #-------------------------------------
        self.angledPlanesButton = QtGui.QPushButton(self.panel3)
        self.angledPlanesButton.setFixedSize(48,48)
        self.angledPlanesButton.setIcon(QtGui.QIcon(':/icons/a2p_AngleConstraint.svg'))
        self.angledPlanesButton.setIconSize(QtCore.QSize(32,32))
        self.angledPlanesButton.setToolTip(a2p_constraints.AngledPlanesConstraint.getToolTip())
        self.angledPlanesButton.setText("")
        QtCore.QObject.connect(self.angledPlanesButton, QtCore.SIGNAL("clicked()"), self.onAngledPlanesButton)
        self.constraintButtons.append(self.angledPlanesButton)
        #-------------------------------------
        self.centerOfMassButton = QtGui.QPushButton(self.panel3)
        self.centerOfMassButton.setFixedSize(48,48)
        self.centerOfMassButton.setIcon(QtGui.QIcon(':/icons/a2p_CenterOfMassConstraint.svg'))
        self.centerOfMassButton.setIconSize(QtCore.QSize(32,32))
        self.centerOfMassButton.setToolTip(a2p_constraints.CenterOfMassConstraint.getToolTip())
        self.centerOfMassButton.setText("")
        QtCore.QObject.connect(self.centerOfMassButton, QtCore.SIGNAL("clicked()"), self.onCenterOfMassButton)
        self.constraintButtons.append(self.centerOfMassButton)
        #-------------------------------------
        panel3_Layout.addWidget(self.planesParallelButton)
        panel3_Layout.addWidget(self.planeCoincidentButton)
        panel3_Layout.addWidget(self.angledPlanesButton)
        panel3_Layout.addWidget(self.centerOfMassButton)
        panel3_Layout.addStretch(1)
        self.panel3.setLayout(panel3_Layout)
        #-------------------------------------

        self.helpButton = QtGui.QPushButton(self)
        self.helpButton.setText(translate("A2plus_constraintDialog", "Help"))
        self.helpButton.setFixedSize(150,32)
        QtCore.QObject.connect(self.helpButton, QtCore.SIGNAL("clicked()"), self.showConstraintCollectionHelp)

        #-------------------------------------
        self.mainLayout.addWidget(self.panel1)
        self.mainLayout.addWidget(self.panel2)
        self.mainLayout.addWidget(self.panel3)
        self.mainLayout.addWidget(self.helpButton)
        self.mainLayout.addStretch(1)
        self.setLayout(self.mainLayout)
        #-------------------------------------
        for btn in self.constraintButtons:
            btn.setEnabled(False)
        #-------------------------------------
        self.timer = QtCore.QTimer()
        QtCore.QObject.connect(self.timer, QtCore.SIGNAL("timeout()"), self.onTimer)
        self.timer.start(100)

    def showConstraintCollectionHelp(self):
        msg = \
translate("A2plus_constraintDialog",
'''
Select geometry to be constrained
within 3D View !

Suitable Constraint buttons will
get activated.

Please also read tooltips of each
button.
'''
)
        QtGui.QMessageBox.information(
            QtGui.QApplication.activeWindow(),
            translate("A2plus_constraintDialog","Constraint tools help"),
            msg
            )

    def parseSelections(self):
        #constraint editor command is active, do not allow defining constraints
        if a2plib.getConstraintEditorRef():
            for btn in self.constraintButtons:
                btn.setEnabled(False)
            return

        selection = FreeCADGui.Selection.getSelectionEx()
        if len(selection) != 2:
            for btn in self.constraintButtons:
                btn.setEnabled(False)
        elif self.activeConstraint is not None:
            for btn in self.constraintButtons:
                btn.setEnabled(False)
        else:
            if a2p_constraints.PointIdentityConstraint.isValidSelection(selection):
                self.pointIdentityButton.setEnabled(True)
            if a2p_constraints.SphericalConstraint.isValidSelection(selection):
                self.sphericalConstraintButton.setEnabled(True)
            if a2p_constraints.PointOnLineConstraint.isValidSelection(selection):
                self.pointOnLineButton.setEnabled(True)
            if a2p_constraints.PointOnPlaneConstraint.isValidSelection(selection):
                self.pointOnPlaneButton.setEnabled(True)
            if a2p_constraints.AxisParallelConstraint.isValidSelection(selection):
                self.axisParallelButton.setEnabled(True)
            if a2p_constraints.AxialConstraint.isValidSelection(selection):
                self.axialButton.setEnabled(True)
            if a2p_constraints.AxisPlaneParallelConstraint.isValidSelection(selection):
                self.axisPlaneParallelButton.setEnabled(True)
            if a2p_constraints.AxisPlaneAngleConstraint.isValidSelection(selection):
                self.axisPlaneAngleButton.setEnabled(True)
            if a2p_constraints.AxisPlaneNormalConstraint.isValidSelection(selection):
                self.axisPlaneNormalButton.setEnabled(True)
            if a2p_constraints.CircularEdgeConstraint.isValidSelection(selection):
                self.circularEdgeButton.setEnabled(True)
            if a2p_constraints.PlanesParallelConstraint.isValidSelection(selection):
                self.planesParallelButton.setEnabled(True)
            if a2p_constraints.AngledPlanesConstraint.isValidSelection(selection):
                self.angledPlanesButton.setEnabled(True)
            if a2p_constraints.PlaneConstraint.isValidSelection(selection):
                self.planeCoincidentButton.setEnabled(True)
            if a2p_constraints.CenterOfMassConstraint.isValidSelection(selection):
                self.centerOfMassButton.setEnabled(True)

    def onTimer(self):
        self.parseSelections()
        self.timer.start(100)

    def manageConstraint(self):
        self.constraintValueBox = a2p_ConstraintValuePanel(
            #self,
            self.activeConstraint.constraintObject,
            'createConstraint'
            )
        QtCore.QObject.connect(self.constraintValueBox, QtCore.SIGNAL("Deleted()"), self.onDeleteConstraint)
        QtCore.QObject.connect(self.constraintValueBox, QtCore.SIGNAL("Accepted()"), self.onAcceptConstraint)
        a2plib.setConstraintEditorRef(self)

    @QtCore.Slot()
    def onAcceptConstraint(self):
        #self.constraintValueBox.deleteLater()
        a2plib.setConstraintEditorRef(None)
        self.activeConstraint = None
        FreeCADGui.Selection.clearSelection()

    @QtCore.Slot()
    def onDeleteConstraint(self):
        #self.constraintValueBox.deleteLater()
        a2plib.setConstraintEditorRef(None)
        self.activeConstraint = None
        FreeCADGui.Selection.clearSelection()

    def onPointIdentityButton(self):
        selection = FreeCADGui.Selection.getSelectionEx()
        self.activeConstraint = a2p_constraints.PointIdentityConstraint(selection)
        self.manageConstraint()

    def onPointOnLineButton(self):
        selection = FreeCADGui.Selection.getSelectionEx()
        self.activeConstraint = a2p_constraints.PointOnLineConstraint(selection)
        self.manageConstraint()

    def onPointOnPlaneButton(self):
        selection = FreeCADGui.Selection.getSelectionEx()
        self.activeConstraint = a2p_constraints.PointOnPlaneConstraint(selection)
        self.manageConstraint()

    def onCircularEdgeButton(self):
        selection = FreeCADGui.Selection.getSelectionEx()
        self.activeConstraint = a2p_constraints.CircularEdgeConstraint(selection)
        self.manageConstraint()

    def onAxialButton(self):
        selection = FreeCADGui.Selection.getSelectionEx()
        self.activeConstraint = a2p_constraints.AxialConstraint(selection)
        self.manageConstraint()

    def onAxisParallelButton(self):
        selection = FreeCADGui.Selection.getSelectionEx()
        self.activeConstraint = a2p_constraints.AxisParallelConstraint(selection)
        self.manageConstraint()

    def onAxisPlaneParallelButton(self):
        selection = FreeCADGui.Selection.getSelectionEx()
        self.activeConstraint = a2p_constraints.AxisPlaneParallelConstraint(selection)
        self.manageConstraint()

    def onAxisPlaneAngleButton(self):
        selection = FreeCADGui.Selection.getSelectionEx()
        self.activeConstraint = a2p_constraints.AxisPlaneAngleConstraint(selection)
        self.manageConstraint()

    def onAxisPlaneNormalButton(self):
        selection = FreeCADGui.Selection.getSelectionEx()
        self.activeConstraint = a2p_constraints.AxisPlaneNormalConstraint(selection)
        self.manageConstraint()

    def onPlanesParallelButton(self):
        selection = FreeCADGui.Selection.getSelectionEx()
        self.activeConstraint = a2p_constraints.PlanesParallelConstraint(selection)
        self.manageConstraint()

    def onPlaneCoincidentButton(self):
        selection = FreeCADGui.Selection.getSelectionEx()
        self.activeConstraint = a2p_constraints.PlaneConstraint(selection)
        self.manageConstraint()

    def onAngledPlanesButton(self):
        selection = FreeCADGui.Selection.getSelectionEx()
        self.activeConstraint = a2p_constraints.AngledPlanesConstraint(selection)
        self.manageConstraint()

    def onCenterOfMassButton(self):
        selection = FreeCADGui.Selection.getSelectionEx()
        self.activeConstraint = a2p_constraints.CenterOfMassConstraint(selection)
        self.manageConstraint()

    def onSpericalConstraintButton(self):
        selection = FreeCADGui.Selection.getSelectionEx()
        self.activeConstraint = a2p_constraints.SphericalConstraint(selection)
        self.manageConstraint()

#==============================================================================
def getMoveDistToStoredPosition(widg):
    if CONSTRAINT_DIALOG_STORED_POSITION == QtCore.QPoint(-1,-1):
        mw = FreeCADGui.getMainWindow()
        fcFrame = QtGui.QDesktopWidget.geometry(mw)
        x = fcFrame.x()
        y = fcFrame.y()
        width = fcFrame.width()
        height = fcFrame.height()

        centerX = x + width/2
        centerY = y + height/2
        fcCenter = QtCore.QPoint(centerX,centerY)

        return fcCenter- widg.rect().center()
    else:
        widgetFrame = widg.frameGeometry()
        x = widgetFrame.x()
        y = widgetFrame.y()
        widgetCorner = QtCore.QPoint(x,y)

        return CONSTRAINT_DIALOG_STORED_POSITION - widgetCorner
#==============================================================================
class a2p_ConstraintValuePanel(QtGui.QDockWidget):

    Deleted = QtCore.Signal()
    Accepted = QtCore.Signal()

    def __init__(self,constraintObject, mode):
        super(a2p_ConstraintValuePanel,self).__init__()
        self.constraintObject = constraintObject

        #
        self.cvw = a2p_ConstraintValueWidget(
            None,
            constraintObject,
            mode
            )
        self.setWidget(self.cvw)
        self.setWindowTitle(translate("A2plus_constraintDialog", "Constraint properties"))

        #self.resize(300,500)

        QtCore.QObject.connect(self.cvw, QtCore.SIGNAL("Accepted()"), self.onAcceptConstraint)
        QtCore.QObject.connect(self.cvw, QtCore.SIGNAL("Deleted()"), self.onDeleteConstraint)

        mw = FreeCADGui.getMainWindow()
        mw.addDockWidget(QtCore.Qt.RightDockWidgetArea,self)

        self.setFloating(True)
        self.activateWindow()
        self.setAllowedAreas(QtCore.Qt.NoDockWidgetArea)

        #self.resize(300,500)

        self.move(getMoveDistToStoredPosition(self))

        a2plib.setConstraintEditorRef(self)
        if mode == 'createConstraint':
            if a2plib.getAutoSolveState():
                doc = FreeCAD.activeDocument()
                if doc is not None:
                    solveConstraints(doc)
        self.cvw.activateWindow()

    def storeWindowPosition(self):
        # ConstraintDialog has Priority on storing its position
        if a2plib.getConstraintDialogRef() is not None:
            return
        frame = QtGui.QDockWidget.frameGeometry(self)
        x = frame.x()
        y = frame.y()

        global CONSTRAINT_DIALOG_STORED_POSITION
        CONSTRAINT_DIALOG_STORED_POSITION = QtCore.QPoint(x,y)

    def onAcceptConstraint(self):
        self.storeWindowPosition()
        self.Accepted.emit()
        a2plib.setConstraintEditorRef(None)
        a2plib.unTouchA2pObjects()
        self.deleteLater()

    def onDeleteConstraint(self):
        self.storeWindowPosition()
        self.Deleted.emit()
        a2plib.setConstraintEditorRef(None)
        a2plib.unTouchA2pObjects()
        self.deleteLater()

    def closeEvent(self,event):
        self.widget().cancelOperation()
        event.ignore()

#==============================================================================
class a2p_ConstraintPanel(QtGui.QDockWidget):
    def __init__(self):
        super(a2p_ConstraintPanel,self).__init__()
        self.resize(200,250)
        cc = a2p_ConstraintCollection(None)
        self.setWidget(cc)
        self.setWindowTitle(translate("A2plus_constraintDialog", "Constraint Tools"))
        #
        mw = FreeCADGui.getMainWindow()
        mw.addDockWidget(QtCore.Qt.RightDockWidgetArea,self)
        #
        self.setFloating(True)
        self.activateWindow()
        self.setAllowedAreas(QtCore.Qt.NoDockWidgetArea)
        self.move(getMoveDistToStoredPosition(self))

        a2plib.setConstraintDialogRef(self)
        #
        self.timer = QtCore.QTimer()
        QtCore.QObject.connect(self.timer, QtCore.SIGNAL("timeout()"), self.onTimer)
        self.timer.start(100)

    def onTimer(self):
        if a2plib.getConstraintEditorRef(): # is not None
            # the editor box is active, do not show self
            self.hide()
        else:
            if not self.isVisible():
                self.show()
                self.resize(200,250)
            # calculate window center position and save it
            # self.rect().center() does not work here somehow
            frame = QtGui.QDockWidget.frameGeometry(self)
            x = frame.x()
            y = frame.y()

            global CONSTRAINT_DIALOG_STORED_POSITION
            CONSTRAINT_DIALOG_STORED_POSITION = QtCore.QPoint(x,y)

        self.timer.start(100)

    def closeEvent(self,event):
        a2plib.setConstraintDialogRef(None)
        self.deleteLater()
        event.accept()

#==============================================================================
toolTipText = \
translate("A2plus_constraintDialog",
'''
Opens a dialog to
define constraints
'''
)
class a2p_ConstraintDialogCommand:

    def Activated(self):
        if a2plib.getConstraintDialogRef(): return #Dialog already active...
        p = a2p_ConstraintPanel()

    def IsActive(self):
        if a2plib.getConstraintEditorRef(): return False
        if a2plib.getConstraintDialogRef(): return False
        return True

    def GetResources(self):
        return {
             'Pixmap'  : ':/icons/a2p_DefineConstraints.svg',
             'MenuText': translate("A2plus_constraintDialog", "Define constraints"),
             'ToolTip' : toolTipText
             }

FreeCADGui.addCommand('a2p_ConstraintDialogCommand', a2p_ConstraintDialogCommand())
#==============================================================================
toolTipText = \
translate("A2plus_constraintDialog",
'''
Edit selected constraint

Select a constraint in the
treeview and hit this button
'''
)

class a2p_EditConstraintCommand:

    def Activated(self):
        self.selectedConstraint = a2plib.getSelectedConstraint()
        if self.selectedConstraint is None:
            QtGui.QMessageBox.information(
                QtGui.QApplication.activeWindow(),
                translate("A2plus_constraintDialog","Selection Error !"),
                translate("A2plus_constraintDialog","Please select exact one constraint first.")
                )
            return

        self.constraintValueBox = a2p_ConstraintValuePanel(
            self.selectedConstraint,
            'editConstraint'
            )
        QtCore.QObject.connect(self.constraintValueBox, QtCore.SIGNAL("Deleted()"), self.onDeleteConstraint)
        QtCore.QObject.connect(self.constraintValueBox, QtCore.SIGNAL("Accepted()"), self.onAcceptConstraint)
        a2plib.setConstraintEditorRef(self.constraintValueBox)

    def IsActive(self):
        if a2plib.getConstraintEditorRef(): return False
        return True

    def onAcceptConstraint(self):
        self.constraintValueBox.deleteLater()
        a2plib.setConstraintEditorRef(None)
        FreeCADGui.Selection.clearSelection()

    def onDeleteConstraint(self):
        self.constraintValueBox.deleteLater()
        a2plib.setConstraintEditorRef(None)
        FreeCADGui.Selection.clearSelection()

    def GetResources(self):
        return {
             'Pixmap'  : ':/icons/a2p_EditConstraint.svg',
             'MenuText': translate("A2plus_constraintDialog", "Edit selected constraint"),
             'ToolTip' : toolTipText
             }

FreeCADGui.addCommand('a2p_EditConstraintCommand', a2p_EditConstraintCommand())
#==============================================================================
