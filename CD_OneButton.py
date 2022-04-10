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
"""

import os
import FreeCAD
import FreeCADGui
from PySide import QtGui, QtCore

class globaluseclass:
    def __init__(self,name):
        self.sONOFF = 'off'
        self.feat1 = ''
        self.buttonenabled = False
        self.obj1 = ''
        self.partselected = False
g = globaluseclass("g")

class onebutton:
    def readselect(self,doc,obj,sub):
        print(obj,sub)
        if g.partselected:
            g.partselected = False
            return
        sels = len(FreeCADGui.Selection.getSelectionEx())
        if sub == "":
            pass
        elif sels == 1:
            if g.obj1 == '' and g.feat1 == '' or obj == g.obj1:
                g.obj1 = obj
                g.feat1 = sub
                obj = ''
                sub = ''

            elif g.obj1 != '' and g.feat1 != '':
                if obj != '' and sub != '':
                    obj1 = FreeCAD.ActiveDocument.getObject(g.obj1)
                    obj2 = FreeCAD.ActiveDocument.getObject(obj)
                    FreeCADGui.Selection.addSelection(obj1, g.feat1)
                    FreeCADGui.Selection.addSelection(obj2, sub)
                    g.partselected = True
                    g.feat1 = ''
                    g.obj1 = ''
                    obj = ''
                    sub = ''

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
                    g.obj1 = ''
                    FreeCADGui.Selection.clearSelection()
                else:
                    pass


viewob = ViewObserver()



toolTipText = \
"""
Use left mouse button to select two features.\nDo not use the control key.
"""


class rnp_OneButton:
    def GetResources(self):
        mypath = os.path.dirname(__file__)
        return {
             'Pixmap': mypath + "/icons/CD_OneButton.svg",
             'MenuText': 'Use one mouse button to select features',
             'ToolTip': toolTipText,
             'Checkable': self.IsChecked()
             }

    def Activated(self, placeholder=None):
        if FreeCAD.activeDocument() is None:
            mApp('No file is opened.\nYou must open an assemly file first.')
            return
        FreeCADGui.Selection.clearSelection()
        if g.buttonenabled == False:
            selObv.SelObserverON()  # Checks for part and enity click
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
FreeCADGui.addCommand('rnp_OneButton', rnp_OneButton())
#==============================================================================

class mApp(QtGui.QWidget):
    """This message box was added to make this file a standalone file"""
    # for error messages
    def __init__(self, msg, msgtype='ok'):
        super().__init__()
        self.title = 'Warning'
        self.left = 100
        self.top = 100
        self.width = 400
        self.height = 300
        self.initUI(msg)

    def initUI(self, msg):
        # self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        QtGui.QMessageBox.question(self, 'Warning', msg, QtGui.QMessageBox.Ok|QtGui.QMessageBox.Ok)
        self.show()
