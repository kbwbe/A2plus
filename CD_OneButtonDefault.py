# -*- coding: utf-8 -*-
#***************************************************************************
#*                                                                         *
#*   Copyright (c) 2022 Dan Miel                                           *
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
from numpy.core.numeric import False_
import a2p_constraints
import a2p_constraintDialog

class globaluseclass:
    def __init__(self, name):
        self.sONOFF = 'off'
        self.feat1 = ''
        self.feat2 = ''
        self.buttonenabled = False
        self.HiddenFeaturesEnabled = False
        self.cvp = None
        self.part1obj = ''
        self.part2obj = ''
g = globaluseclass("g")

class onebutton:
    def __init__(self, name):
        self.h = ''
    def readselect(self):
        sels = len(FreeCADGui.Selection.getSelectionEx())
        if sels == 1:
            sel = FreeCADGui.Selection.getSelectionEx()[0]
            tobj = sel.Object
            try:
                tfeat = sel.SubElementNames[0]
            except:
                # The entire part was selected
                return
            if g.part1obj =='':
                g.part1obj = tobj
            if tobj == g.part1obj:
                g.feat1 = tfeat
                return()
            if g.part1obj != '' and g.part2obj == '':
                try:
                    g.part2obj = tobj
                    g.feat2 = tfeat
                    FreeCADGui.Selection.addSelection(g.part1obj, g.feat1)
                    FreeCADGui.Selection.addSelection(g.part2obj, g.feat2)
                    if g.part1obj.fixedPosition and tobj.fixedPosition:
                        mApp('Both parts are fixed')
                        return
                except Exception as e:
                    print('Error4 = ' + str(e))
                c = None
                g.cvp = None
                selection = FreeCADGui.Selection.getSelectionEx()
                if a2p_constraints.CircularEdgeConstraint.isValidSelection(FreeCADGui.Selection.getSelectionEx()):
                    c = a2p_constraints.CircularEdgeConstraint(selection)
                elif a2p_constraints.PointIdentityConstraint.isValidSelection(FreeCADGui.Selection.getSelectionEx()):
                    c = a2p_constraints.PointIdentityConstraint(selection)
                elif a2p_constraints.AxisPlaneNormalConstraint.isValidSelection(FreeCADGui.Selection.getSelectionEx()):
                    c = a2p_constraints.AxisPlaneNormalConstraint(selection)
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
                g.part1obj = ''
                g.part2obj = ''

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
        except Exception as e:
            print('Error2 = ' + str(e))
    def addSelection(self, doc, obj, sub, pnt):  # Selection object
        if g.HiddenFeaturesEnabled:
            pass
        else:
            onebutton.readselect(self)
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

    def vooff1(self):
        try:
            self.view.removeEventCallback("SoMouseButtonEvent", self.c)
        except Exception as e:
            #print('Error1 = ' + str(e))
            pass
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
                    g.part1obj = ''
                    g.part2obj = ''
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
             'MenuText': 'Auto mouse. Use one mouse button to select features. See help in the constraint viewer for more help.',
             'ToolTip': toolTipText,
             'Checkable': self.IsChecked()
             }

    def Activated(self, placeholder=None):
        if FreeCAD.activeDocument() is None:
            mApp('No file is opened.You must open an assembly file first.')
            return
        FreeCADGui.Selection.clearSelection()
        if g.buttonenabled == False:
            selObv.SelObserverON()  # Checks for part and entity click
            viewob.vostart()        # Checks for click in background
            g.buttonenabled = True
        else:
            g.buttonenabled = False
            selObv.SelObserverOFF()
            viewob.vooff1()
            formtv.closeEvent('button')
 
    def Deactivated(self):
        """This function is executed when the workbench is deactivated."""
        selObv.SelObserverOFF()
        viewob.vooff1()

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

    ''' The following is code for hidden surfaces ******************************'''

#This class collects the feature below the mouse curser.
class HidViewObserver:
    def __init__(self):
        self.view = None
        self.o = None
        self.c = None
    def vostart(self):
        
        self.view = FreeCADGui.activeDocument().activeView()
        self.o = HidViewObserver()
        self.c = self.view.addEventCallback("SoMouseButtonEvent", self.o.logPosition)
    def vooff2(self):

        try:
            self.view.removeEventCallback("SoMouseButtonEvent", self.c)
        except Exception as e:
            print('Error3 = ' + str(e))

    def logPosition(self, myinfo):
        down = (myinfo["State"] == "DOWN")
        up = (myinfo["State"] == "UP")
        pos = myinfo["Position"]
        if up:
            pass
        if (down):
            if myinfo['Button'] == 'BUTTON1':
                listObjects = FreeCADGui.ActiveDocument.ActiveView.getObjectsInfo((int(pos[0]), int(pos[1])))
                if listObjects is not None:
                    formtv.loadtable2(listObjects)


            else:
                pass
Hidviewob = HidViewObserver()


class TableViewer(QtGui.QMainWindow):
    #Form for showing and selecting hidden parts
    def __init__(self, parent = None):
        super(TableViewer, self).__init__(parent)
        self.setGeometry(200, 300, 250, 200)#xy,wh
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        self.seltable = QtGui.QTableWidget(self)
        self.cleartable()
        self.seltable.setColumnCount(2)
        self.seltable.setHorizontalHeaderLabels(['Part', 'Feature'])
        self.tableheader = self.seltable.horizontalHeader()
        self.tableheader.setResizeMode(QtGui.QHeaderView.ResizeToContents)
        self.hoveronoff(True)
        self.seltable.setMouseTracking(True)
        self.current_hover = [0, 0]
        self.seltable.cellEntered.connect(self.cellHover)
        self.seltable.cellClicked.connect(self.cell_was_clicked)
        self.seltable.setEditTriggers(QtGui.QTableWidget.NoEditTriggers)
        
        self.partname = ''
        self.feature = ''
        self.selectedpart = ''
    def cleartable(self):
        self.seltable.setRowCount(0)

    def hoveronoff(self, bool):
        self.seltable.setMouseTracking(bool)

    def loadtable2(self, listObjects):
        ''' Write parts and features to table '''
        self.seltable.setRowCount(0)
        self.showGobj()
        for e in reversed(listObjects):
            self.seltable.insertRow(0)
            column1 = QtGui.QTableWidgetItem(e.get('Object'))
            column2 = QtGui.QTableWidgetItem(e.get('Component'))
            self.seltable.setItem(0, 0, column1)
            self.seltable.setItem(0, 1, column2)
        self.setCentralWidget(self.seltable)

        
        self.tableheader.setResizeMode(0, QtGui.QHeaderView.Stretch)
        for row in range(self.seltable.rowCount()):
            self.seltable.setRowHeight(row, 15)
        self.seltable.horizontalHeader().sectionClicked.connect(self.sortcolumn)
        
        self.showme()

    def showme(self):
        self.show()

    def closeme(self):
        g.HiddenFeaturesEnabled = False
        self.close()

    def closeEvent(self, event):
        Hidviewob.vooff2()
        g.HiddenFeaturesEnabled = False
        self.close()
        self.cleartable() 

    def sortcolumn(self, i):
        # click in column header to sort column
        self.seltable.sortByColumn(i)

    def cell_was_clicked(self, row, column):
        self.cleartable()
        FreeCADGui.Selection.clearSelection()
        FreeCADGui.Selection.addSelection(self.selectedpart, self.feature)  # select the feature specified in table
        if g.buttonenabled:
            onebutton.readselect(self)

    def cellHover(self, row):
        item = self.seltable.item(row, 0)
        item2 = self.seltable.item(row, 1)
        if 'None' in str(type(item)):
            return
        self.partname = item.text()
        self.feature = item2.text()
        self.selectedpart = FreeCAD.ActiveDocument.getObject(self.partname)
        FreeCADGui.Selection.clearSelection()
        FreeCADGui.Selection.addSelection(self.selectedpart, self.feature)  # select the face specified in table
        self.showGobj()

    def showGobj(self):
        if g.part1obj != '':
            FreeCADGui.Selection.addSelection(g.part1obj, g.feat1)


formtv = TableViewer()


toolTipText = \
"""
Click on a part to open a table listing of all features below the mouse curser.
Moving the mouse along the cells will highlight the features.
Click in cell to select feature.
"""


class rnp_SelectHiddenLayers:
    def GetResources(self):
        mypath = os.path.dirname(__file__)
        return {
             'Pixmap': mypath + "/icons/CD_HiddenFeatures.svg",
             'MenuText': 'Select features that are not visible. See help in the constraint viewer for more help.',
             'ToolTip': toolTipText
             }

    def Activated(self, placeholder = None):
        if FreeCAD.activeDocument() is None:
            mApp('No file is opened.\nYou must open an assembly file first.')
            return
        if g.HiddenFeaturesEnabled == False:
            g.HiddenFeaturesEnabled = True
            formtv.showme()
            Hidviewob.vostart()
        else:
            formtv.closeEvent('OneButton')
      
    def Deactivated(self):
        """This function is executed when the workbench is deactivated."""
        try:
            Hidviewob.vooff2()
        except:
            pass

    def IsChecked(self):
        return(g.HiddenFeaturesEnabled)

    def IsActive(self):
        return(True)
FreeCADGui.addCommand('rnp_SelectHiddenLayers', rnp_SelectHiddenLayers())
#==============================================================================
