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
import os, sys
from a2p_viewProviderProxies import *
from  FreeCAD import Base

from a2plib import *
from a2p_solversystem import solveConstraints
import a2p_constraints


#==============================================================================
class a2p_ConstraintValueWidget(QtGui.QWidget):
    def __init__(self,constraintObject):
        super(a2p_ConstraintValueWidget,self).__init__()
        self.constraintObject = constraintObject # The documentObject of a constraint!
        self.lineNo = 0
        self.initUI()

    def initUI(self):
        
        self.setMinimumHeight(100)
        self.mainLayout = QtGui.QGridLayout() # a VBoxLayout for the whole form
        
        #==============================
        lbl1 = QtGui.QLabel(self)
        lbl1.setText(self.constraintObject.Label)
        lbl1.setFrameStyle(
            QtGui.QFrame.Panel | 
            QtGui.QFrame.Sunken
            )
        self.mainLayout.addWidget(lbl1,self.lineNo,0,1,2)
        self.lineNo += 1
        
        #==============================
        if hasattr(self.constraintObject,"directionConstraint"):   
            lbl3 = QtGui.QLabel(self)
            lbl3.setText("Direction")
            self.mainLayout.addWidget(lbl3,self.lineNo,0)
            
            self.directionCombo = QtGui.QComboBox(self)
            self.directionCombo.insertItem(0,"aligned")
            self.directionCombo.insertItem(1,"opposed")
            d = self.constraintObject.directionConstraint # not every constraint has a direction
            if d == "aligned":
                self.directionCombo.setCurrentIndex(0)
            elif d == "opposed":
                self.directionCombo.setCurrentIndex(1)
            self.mainLayout.addWidget(self.directionCombo,self.lineNo,1)
            self.lineNo += 1
        
        #==============================
        if hasattr(self.constraintObject,"offset"):   
            offs = self.constraintObject.offset    
            lbl4 = QtGui.QLabel(self)
            lbl4.setText("Offset")
            self.mainLayout.addWidget(lbl4,self.lineNo,0)
            
            self.offsetEdit = QtGui.QLineEdit(self)
            self.offsetEdit.setText("{}".format(offs))
            self.mainLayout.addWidget(self.offsetEdit,self.lineNo,1)
            self.lineNo += 1
            
        #==============================
        if hasattr(self.constraintObject,"angle"):   
            angle = self.constraintObject.angle    
            lbl5 = QtGui.QLabel(self)
            lbl5.setText("Angle")
            self.mainLayout.addWidget(lbl5,self.lineNo,0)
            
            self.angleEdit = QtGui.QLineEdit(self)
            self.angleEdit.setText("{}".format(angle))
            self.mainLayout.addWidget(self.angleEdit,self.lineNo,1)
            self.lineNo += 1
            
        #==============================
        if hasattr(self.constraintObject,"lockRotation"):   
            lbl6 = QtGui.QLabel(self)
            lbl6.setText("lockRotation")
            self.mainLayout.addWidget(lbl6,self.lineNo,0)
            
            self.lockRotationCombo = QtGui.QComboBox(self)
            self.lockRotationCombo.insertItem(0,"False")
            self.lockRotationCombo.insertItem(1,"True")
            if self.constraintObject.lockRotation: # not every constraint has a direction
                self.lockRotationCombo.setCurrentIndex(1)
            else:
                self.lockRotationCombo.setCurrentIndex(0)
            self.mainLayout.addWidget(self.lockRotationCombo,self.lineNo,1)
            self.lineNo += 1
        

        self.setLayout(self.mainLayout)
        
#==============================================================================
class a2p_ConstraintPanel(QtGui.QWidget):
    def __init__(self):
        super(a2p_ConstraintPanel,self).__init__()
        self.constraintButtons = []
        self.activeConstraint = None
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle('Create constraints')
        self.setMinimumHeight(300)
        
        self.mainLayout = QtGui.QVBoxLayout() # a VBoxLayout for the whole form
        
        #-------------------------------------
        self.panel1 = QtGui.QWidget(self)
        self.panel1.setMinimumHeight(32)
        panel1_Layout = QtGui.QHBoxLayout()
        #-------------------------------------
        self.pointLabel = QtGui.QLabel('Point Constraints')
        self.pointLabel.setMinimumWidth(145)
        #-------------------------------------
        self.pointIdentityButton = QtGui.QPushButton(self.panel1)
        self.pointIdentityButton.setFixedSize(32,32)
        self.pointIdentityButton.setIcon(QtGui.QIcon(':/icons/a2p_PointIdentity.svg'))
        self.pointIdentityButton.setToolTip("pointIdentity")
        self.pointIdentityButton.setText("")
        QtCore.QObject.connect(self.pointIdentityButton, QtCore.SIGNAL("clicked()"), self.onPointIdentityButton)
        self.constraintButtons.append(self.pointIdentityButton)
        #-------------------------------------
        self.pointOnLineButton = QtGui.QPushButton(self.panel1)
        self.pointOnLineButton.setFixedSize(32,32)
        self.pointOnLineButton.setIcon(QtGui.QIcon(':/icons/a2p_PointOnLineConstraint.svg'))
        self.pointOnLineButton.setToolTip("pointOnLineConstraint")
        self.pointOnLineButton.setText("")
        QtCore.QObject.connect(self.pointOnLineButton, QtCore.SIGNAL("clicked()"), self.onPointOnLineButton)
        self.constraintButtons.append(self.pointOnLineButton)
        #-------------------------------------
        self.pointOnPlaneButton = QtGui.QPushButton(self.panel1)
        self.pointOnPlaneButton.setFixedSize(32,32)
        self.pointOnPlaneButton.setIcon(QtGui.QIcon(':/icons/a2p_PointOnPlaneConstraint.svg'))
        self.pointOnPlaneButton.setToolTip("pointOnPlaneConstraint")
        self.pointOnPlaneButton.setText("")
        QtCore.QObject.connect(self.pointOnPlaneButton, QtCore.SIGNAL("clicked()"), self.onPointOnPlaneButton)
        self.constraintButtons.append(self.pointOnPlaneButton)
        #-------------------------------------
        panel1_Layout.addWidget(self.pointLabel)
        panel1_Layout.addWidget(self.pointIdentityButton)
        panel1_Layout.addWidget(self.pointOnLineButton)
        panel1_Layout.addWidget(self.pointOnPlaneButton)
        panel1_Layout.addStretch(1)
        self.panel1.setLayout(panel1_Layout)
        #-------------------------------------
        

        #-------------------------------------
        self.panel2 = QtGui.QWidget(self)
        self.panel2.setMinimumHeight(32)
        panel2_Layout = QtGui.QHBoxLayout()
        #-------------------------------------
        self.axisLabel = QtGui.QLabel('Axis Constraints')
        self.axisLabel.setMinimumWidth(145)
        #-------------------------------------
        self.circularEdgeButton = QtGui.QPushButton(self.panel2)
        self.circularEdgeButton.setFixedSize(32,32)
        self.circularEdgeButton.setIcon(QtGui.QIcon(':/icons/a2p_CircularEdgeConstraint.svg'))
        self.circularEdgeButton.setToolTip("circularEdgeConstraint")
        self.circularEdgeButton.setText("")
        QtCore.QObject.connect(self.circularEdgeButton, QtCore.SIGNAL("clicked()"), self.onCircularEdgeButton)
        self.constraintButtons.append(self.circularEdgeButton)
        #-------------------------------------
        self.axialButton = QtGui.QPushButton(self.panel2)
        self.axialButton.setFixedSize(32,32)
        self.axialButton.setIcon(QtGui.QIcon(':/icons/a2p_AxialConstraint.svg'))
        self.axialButton.setToolTip("axialCoincidentConstraint")
        self.axialButton.setText("")
        QtCore.QObject.connect(self.axialButton, QtCore.SIGNAL("clicked()"), self.onAxialButton)
        self.constraintButtons.append(self.axialButton)
        #-------------------------------------
        self.axisParallelButton = QtGui.QPushButton(self.panel2)
        self.axisParallelButton.setFixedSize(32,32)
        self.axisParallelButton.setIcon(QtGui.QIcon(':/icons/a2p_AxisParallelConstraint.svg'))
        self.axisParallelButton.setToolTip("axisParallelConstraint")
        self.axisParallelButton.setText("")
        QtCore.QObject.connect(self.axisParallelButton, QtCore.SIGNAL("clicked()"), self.onAxisParallelButton)
        self.constraintButtons.append(self.axisParallelButton)
        #-------------------------------------
        self.axisPlaneParallelButton = QtGui.QPushButton(self.panel2)
        self.axisPlaneParallelButton.setFixedSize(32,32)
        self.axisPlaneParallelButton.setIcon(QtGui.QIcon(':/icons/a2p_AxisPlaneParallelConstraint.svg'))
        self.axisPlaneParallelButton.setToolTip("axisPlaneParallelConstraint")
        self.axisPlaneParallelButton.setText("")
        QtCore.QObject.connect(self.axisPlaneParallelButton, QtCore.SIGNAL("clicked()"), self.onAxisPlaneParallelButton)
        self.constraintButtons.append(self.axisPlaneParallelButton)
        #-------------------------------------
        panel2_Layout.addWidget(self.axisLabel)
        panel2_Layout.addWidget(self.circularEdgeButton)
        panel2_Layout.addWidget(self.axialButton)
        panel2_Layout.addWidget(self.axisParallelButton)
        panel2_Layout.addWidget(self.axisPlaneParallelButton)
        panel2_Layout.addStretch(1)
        self.panel2.setLayout(panel2_Layout)
        #-------------------------------------


        #-------------------------------------
        self.panel3 = QtGui.QWidget(self)
        self.panel3.setMinimumHeight(32)
        panel3_Layout = QtGui.QHBoxLayout()
        #-------------------------------------
        self.planesLabel = QtGui.QLabel('Plane Constraints')
        self.planesLabel.setMinimumWidth(145)
        #-------------------------------------
        self.planesParallelButton = QtGui.QPushButton(self.panel3)
        self.planesParallelButton.setFixedSize(32,32)
        self.planesParallelButton.setIcon(QtGui.QIcon(':/icons/a2p_PlanesParallelConstraint.svg'))
        self.planesParallelButton.setToolTip("planesParallelConstraint")
        self.planesParallelButton.setText("")
        QtCore.QObject.connect(self.planesParallelButton, QtCore.SIGNAL("clicked()"), self.onPlanesParallelButton)
        self.constraintButtons.append(self.planesParallelButton)
        #-------------------------------------
        self.planeCoincidentButton = QtGui.QPushButton(self.panel3)
        self.planeCoincidentButton.setFixedSize(32,32)
        self.planeCoincidentButton.setIcon(QtGui.QIcon(':/icons/a2p_PlaneCoincidentConstraint.svg'))
        self.planeCoincidentButton.setToolTip("planesCoincidentConstraint")
        self.planeCoincidentButton.setText("")
        QtCore.QObject.connect(self.planeCoincidentButton, QtCore.SIGNAL("clicked()"), self.onPlaneCoincidentButton)
        self.constraintButtons.append(self.planeCoincidentButton)
        #-------------------------------------
        self.angledPlanesButton = QtGui.QPushButton(self.panel3)
        self.angledPlanesButton.setFixedSize(32,32)
        self.angledPlanesButton.setIcon(QtGui.QIcon(':/icons/a2p_AngleConstraint.svg'))
        self.angledPlanesButton.setToolTip("angledPlanesConstraint")
        self.angledPlanesButton.setText("")
        QtCore.QObject.connect(self.angledPlanesButton, QtCore.SIGNAL("clicked()"), self.onAngledPlanesButton)
        self.constraintButtons.append(self.angledPlanesButton)
        #-------------------------------------
        panel3_Layout.addWidget(self.planesLabel)
        panel3_Layout.addWidget(self.planesParallelButton)
        panel3_Layout.addWidget(self.planeCoincidentButton)
        panel3_Layout.addWidget(self.angledPlanesButton)
        panel3_Layout.addStretch(1)
        self.panel3.setLayout(panel3_Layout)
        #-------------------------------------


        #-------------------------------------
        self.finalPanel = QtGui.QWidget(self)
        self.finalPanel.setMinimumHeight(40)
        finalPanel_Layout = QtGui.QHBoxLayout()
        #-------------------------------------
        self.solveButton = QtGui.QPushButton(self.finalPanel)
        self.solveButton.setFixedSize(32,32)
        self.solveButton.setIcon(QtGui.QIcon(':/icons/a2p_solver.svg'))
        self.solveButton.setToolTip("solve Constraints")
        self.solveButton.setText("")
        #-------------------------------------
        finalPanel_Layout.addStretch(1)
        finalPanel_Layout.addWidget(self.solveButton)
        self.finalPanel.setLayout(finalPanel_Layout)
        #-------------------------------------
        
        #-------------------------------------
        self.mainLayout.addWidget(self.panel1)
        self.mainLayout.addWidget(self.panel2)
        self.mainLayout.addWidget(self.panel3)
        self.mainLayout.addStretch(1)
        self.mainLayout.addWidget(self.finalPanel)
        self.setLayout(self.mainLayout)       
        #-------------------------------------
        
        #-------------------------------------
        self.selectionTimer = QtCore.QTimer()
        QtCore.QObject.connect(self.selectionTimer, QtCore.SIGNAL("timeout()"), self.parseSelections)
        self.selectionTimer.start(100)
        
        #-------------------------------------
        QtCore.QObject.connect(self.solveButton, QtCore.SIGNAL("clicked()"), self.solve)
        
        
    def parseSelections(self):
        selection = FreeCADGui.Selection.getSelectionEx()
        if len(selection) != 2:
            for btn in self.constraintButtons:
                btn.setEnabled(False)
        else:
            s1, s2 = selection
            if s1.ObjectName != s2.ObjectName:
                #=============================
                if vertexSelected(s1):
                    if vertexSelected(s2):
                        self.pointIdentityButton.setEnabled(True)
                    elif LinearEdgeSelected(s2):
                        self.pointOnLineButton.setEnabled(True)
                    elif planeSelected(s2):
                        self.pointOnPlaneButton.setEnabled(True)
                #=============================
                elif LinearEdgeSelected(s1) or cylindricalPlaneSelected(s1):
                    if LinearEdgeSelected(s2) or cylindricalPlaneSelected(s2):
                        self.axisParallelButton.setEnabled(True)
                        self.axialButton.setEnabled(True) #
                    elif planeSelected(s2):
                        self.axisPlaneParallelButton.setEnabled(True)
                #=============================
                elif CircularEdgeSelected(s1):
                    if planeSelected(s2):
                        self.pointOnPlaneButton.setEnabled(True)
                    elif CircularEdgeSelected(s2):
                        self.circularEdgeButton.setEnabled(True)
                #=============================
                elif planeSelected(s1):
                    if planeSelected(s2):
                        self.planesParallelButton.setEnabled(True)
                        self.planeCoincidentButton.setEnabled(True)
                        self.angledPlanesButton.setEnabled(True)
                #=============================
        if self.activeConstraint:
            self.solveButton.setEnabled(True)
        else:
            self.solveButton.setEnabled(False)
        self.selectionTimer.start(100)

    def manageConstraint(self):
        try:
            self.constraintValueBox.deleteLater()
        except:
            pass
        self.constraintValueBox = a2p_ConstraintValueWidget(
            self.activeConstraint.constraintObject
            )
        self.mainLayout.addWidget(self.constraintValueBox)

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

    def solve(self):
        self.activeConstraint = None
        doc = FreeCAD.activeDocument()
        if doc != None:
            solveConstraints(doc)
        
    
#==============================================================================
class a2p_ConstraintTaskDialog:
    '''
    Form for definition of constraints
    ''' 
    def __init__(self):
        self.form = a2p_ConstraintPanel()
        
    def accept(self):
        return True

    def reject(self):
        return True

    def getStandardButtons(self):
        retVal = (
            #0x02000000 + # Apply
            0x00400000 + # Cancel
            0x00200000 + # Close
            0x00000400   # Ok
            )
        return retVal
#==============================================================================
toolTipText = \
'''
Open a dialog to
define constraints
'''

class a2p_ConstraintDialogCommand:
    def Activated(self):
        
        d = a2p_ConstraintTaskDialog()
        FreeCADGui.Control.showDialog(d)

    def GetResources(self):
        return {
             #'Pixmap' : ':/icons/a2p_PointIdentity.svg',
             'MenuText': 'Define constraints',
             'ToolTip': toolTipText
             }

FreeCADGui.addCommand('a2p_ConstraintDialogCommand', a2p_ConstraintDialogCommand())
#==============================================================================
















