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


#==============================================================================
class a2p_ConstraintPanel(QtGui.QWidget):
    def __init__(self):
        super(a2p_ConstraintPanel,self).__init__()
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle('Create constraints')
        self.setMinimumHeight(400)
        
        mainLayout = QtGui.QVBoxLayout() # a VBoxLayout for the whole form
        #-------------------------------------
        self.panel1 = QtGui.QWidget(self)
        self.panel1.setMinimumHeight(48)
        panel1_Layout = QtGui.QHBoxLayout()
        #-------------------------------------
        self.pointIdentityButton = QtGui.QPushButton(self.panel1)
        self.pointIdentityButton.setFixedSize(32,32)
        self.pointIdentityButton.setIcon(QtGui.QIcon(':/icons/a2p_PointIdentity.svg'))
        self.pointIdentityButton.setToolTip("pointIdentity")
        self.pointIdentityButton.setText("")
        #-------------------------------------
        self.pointOnLineButton = QtGui.QPushButton(self.panel1)
        self.pointOnLineButton.setFixedSize(32,32)
        self.pointOnLineButton.setIcon(QtGui.QIcon(':/icons/a2p_PointOnLineConstraint.svg'))
        self.pointOnLineButton.setToolTip("pointOnLine")
        self.pointOnLineButton.setText("")
        #-------------------------------------
        panel1_Layout.addWidget(self.pointIdentityButton)
        panel1_Layout.addWidget(self.pointOnLineButton)
        self.panel1.setLayout(panel1_Layout)
        #-------------------------------------


        
        #-------------------------------------
        mainLayout.addLayout(panel1_Layout)
        self.setLayout(mainLayout)       
        #-------------------------------------
    
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
















