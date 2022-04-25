# -*- coding: utf-8 -*-
#***************************************************************************
#*                                                                         *
#*   Copyright (c) 2020 Dan Miel                                           *
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
"""
This is to be used in conjunction with A2plus Assembly Workbench.

Enables two features to be selected without using the control key.
The create dialog for constraints is then shown without selecting the icons.
"""

import os
import FreeCAD
import FreeCADGui
from PySide import QtGui, QtCore
import a2p_constraints
import a2p_constraintDialog
class globaluseclass:
    def __init__(self, name):
        self.sONOFF = 'off'
        self.feat1 = ''
        self.feat2 = ''
        self.buttonenabled = False
        self.obj1 = ''
        self.partselected = False
        self.cvp = None
        self.preBasePt1 = None
        self.preBasePt2 = None
        self.part1 = None
        self.part2 = None
g = globaluseclass("g")

class onebutton:
 
    def readselect(self, doc, partname, sub):
        if g.partselected:
            g.partselected = False
            return
        sels = len(FreeCADGui.Selection.getSelectionEx())
           
        if sub == "":
            pass
        elif sels == 1:
            if g.part1 is None and g.feat1 == '' or g.part1 is not None and partname == g.part1.Name:
                g.part1 = FreeCAD.ActiveDocument.getObject(partname)
                g.feat1 = sub
 
            elif g.part1 is not None and g.feat1 != '':
                if partname != '' and sub != '':                   
                    try:
                        g.feat2 = sub
                        g.part2 = FreeCAD.ActiveDocument.getObject(partname)
                        FreeCADGui.Selection.addSelection(g.part1, g.feat1)
                        FreeCADGui.Selection.addSelection(g.part2, g.feat2)
                        g.partselected = True
                        if g.part1.fixedPosition and g.part2.fixedPosition:
                            mApp('Both parts are fixed')
                            return
                        g.preBasePt1 = g.part1.Placement.Base
                        g.preBasePt2 = g.part2.Placement.Base
                    except:
                        print('Part selection error')

                    
                    c = None
                    selection = FreeCADGui.Selection.getSelectionEx()
                        
                    if a2p_constraints.CircularEdgeConstraint.isValidSelection(FreeCADGui.Selection.getSelectionEx()):
                        c = a2p_constraints.CircularEdgeConstraint(selection)
                    elif a2p_constraints.PointIdentityConstraint.isValidSelection(FreeCADGui.Selection.getSelectionEx()):                            
                        c = a2p_constraints.PointIdentityConstraint(selection)
                    elif a2p_constraints.PointOnLineConstraint.isValidSelection(FreeCADGui.Selection.getSelectionEx()):                            
                        c = a2p_constraints.PointOnLineConstraint(selection)                        
                    elif a2p_constraints.AxialConstraint.isValidSelection(FreeCADGui.Selection.getSelectionEx()):                            
                        c = a2p_constraints.AxialConstraint(selection)
                    elif a2p_constraints.PointOnPlaneConstraint.isValidSelection(FreeCADGui.Selection.getSelectionEx()):                            
                        c = a2p_constraints.PointOnPlaneConstraint(selection)
                    elif a2p_constraints.PlaneConstraint.isValidSelection(FreeCADGui.Selection.getSelectionEx()):                            
                        c = a2p_constraints.PlaneConstraint(selection)
                        
                    if c is not None:
                        g.cvp = a2p_constraintDialog.a2p_ConstraintValuePanel(
                            c.constraintObject,
                            'createConstraint'
                            )

                    g.feat1 = ''
                    g.feat2 = ''
                    g.part1 = None
                    g.part2 = None

class SelObserver:
    def __init__(self):
        pass
    def SelObserverON(self):
        if g.sONOFF != 'on':
            FreeCADGui.Selection.addObserver(selObv)
            g.sONOFF = 'on'
            # print('SelObserverON')
    def SelObserverOFF(self):
        try:
            FreeCADGui.Selection.removeObserver(selObv)
            g.sONOFF = 'off'
            # print('SelObserverOFF')
        except:
            print('SelObserverOFF by except')
    def addSelection(self, doc, obj, sub, pnt):  # Selection object
        onebutton.readselect(onebutton, doc, obj, sub)
    def removeSelection(self, doc, obj, sub):    # Delete the selected object
        pass
    def setSelection(self, doc):
        pass


selObv = SelObserver()


"""This class looks for mouse clicks in space to unselect parts."""
class ViewObserver:
    def __init__(self):
        self.view = None
        self.o = None
        self.c = None
    def vostart(self):
        self.view = FreeCADGui.activeDocument().activeView()
        self.o = ViewObserver()
        self.c = self.view.addEventCallback("SoMouseButtonEvent", self.o.logPosition)

    def vooff(self):
        try:
            self.view.removeEventCallback("SoMouseButtonEvent", self.c)
        except Exception as e:
            print(str(e))

    def logPosition(self, myinfo):
        down = (myinfo["State"] == "DOWN")
        up = (myinfo["State"] == "UP")
        pos = myinfo["Position"]
        if up:
            pass
        if (down):
            if myinfo['Button'] == 'BUTTON1':
                pos = FreeCADGui.ActiveDocument.ActiveView.getCursorPos()
                partinfo = FreeCADGui.activeDocument().activeView().getObjectInfo(pos)
                if partinfo is None:
                    g.feat1 = ''
                    g.feat2 = ''
                    g.part1 is None
                    g.part2 is None
                    FreeCADGui.Selection.clearSelection()
                else:
                    pass


viewob = ViewObserver()



toolTipText = \
"""
Use the left mouse button to select two features, do not use the control key.
When two features have been selected, a default constraint dialog will show.
If the dialog box is not for the constraint you want, click the delete constraint button and then select the constraint you want from the standard icons.
"""


class rnp_OneButtonDefault:
    def GetResources(self):
        mypath = os.path.dirname(__file__)
        return {
             'Pixmap': mypath + "/icons/CD_OneButtonDefault.svg",
             'MenuText': 'Use one mouse button to select features',
             'ToolTip': toolTipText,
             'Checkable': self.IsChecked()
             }

    def Activated(self, placeholder=None):
        if FreeCAD.activeDocument() is None:
            mApp('No file is opened.\nYou must open an assembly file first.')
            return
        FreeCADGui.Selection.clearSelection()
        if g.buttonenabled == False:
            selObv.SelObserverON()  # Checks for part and entity click
            viewob.vostart()        # Checks for click in background
            g.buttonenabled = True
        else:
            g.buttonenabled = False
            selObv.SelObserverOFF()
            viewob.vooff()

    def Deactivated(self):
        """This function is executed when the workbench is deactivated."""
        selObv.SelObserverOFF()
        viewob.vooff()

    def IsChecked(self):
        return(g.buttonenabled)

    def IsActive(self):
        return(True)
FreeCADGui.addCommand('rnp_OneButtonDefault', rnp_OneButtonDefault())
#==============================================================================

class mApp(QtGui.QWidget):
    """This message box was added to make this file a standalone file"""
    # for error messages
    def __init__(self, msg, msgtype ='ok'):
        super().__init__()
        self.title = 'Warning'
        self.initUI(msg)

    def initUI(self, msg):
        self.setGeometry(100, 100, 400, 300)
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        QtGui.QMessageBox.question(self, 'Warning', msg, QtGui.QMessageBox.Ok|QtGui.QMessageBox.Ok)
        self.show()


