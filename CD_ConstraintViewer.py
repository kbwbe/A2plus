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
# This is to be used with A2plus Assembly WorkBench
# Tries to find constraints that are conflicting with each other.

import os
import sys
import FreeCAD
import FreeCADGui
import subprocess

from PySide import QtGui, QtCore
from PySide import QtUiTools
from PySide.QtGui import *
import a2plib
import CD_checkconstraints
import a2p_solversystem
import CD_featurelabels

class globaluseclass:
    def __init__(self):
        self.checkingnum = 0
        self.roundto = 4
        self.labelexist = False
g = globaluseclass()

class mApp(QtGui.QWidget):

    # for error messages
    def __init__(self, msg, msgtype = 'ok'):
        super().__init__()
        self.initUI(msg)

    def initUI(self, msg, msgtype = 'ok'):
        self.setGeometry(100, 200, 320, 200)
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        if msgtype == 'ok':
            buttonReply = QtGui.QMessageBox.question(self, 'Information', msg, QtGui.QMessageBox.Ok|QtGui.QMessageBox.Ok)
        if msgtype == 'yn':
            buttonReply = QtGui.QMessageBox.question(self, 'Information', msg, QtGui.QMessageBox.Yes|QtGui.QMessageBox.No, QtGui.QMessageBox.No)
        if buttonReply == QtGui.QMessageBox.Yes:
            pass
            # print('Yes clicked.')
        else:
            pass
            # print('No clicked.')
        self.show()


class ShowPartProperties(QtGui.QWidget):

    def __init__(self):
        QtGui.QWidget.__init__(self)
        self.drt()
        self.oldcell = ''

    def drt(self):
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        self.setGeometry(100, 50, 700, 280)#xy,wh
        self.setWindowTitle("Constraint Viewer")
        self.setStyleSheet("font: 11pt arial MS")
        bar = QtGui.QMenuBar(self)
        
        labelMenu = bar.addMenu("Labels")
        labelMenu.addAction("Open Dialog")
        labelMenu.addAction("Delete labels")
        labelMenu.triggered[QtGui.QAction].connect(self.process_menus)
        
        infoMenu = bar.addMenu("Info")
        infoMenu.addAction("Places of accuracy = " + str(g.roundto))
        infoMenu.triggered[QtGui.QAction].connect(self.process_menus)
        
        helpMenu = bar.addMenu("Help")
        helpMenu.addAction("Open Help")
        helpMenu.triggered[QtGui.QAction].connect(self.process_menus)

        """ Main Table """
        self.tm = QtGui.QTableWidget(self)
        self.tm.setGeometry(10, 120, 650, 50)  # xy,wh
        self.tm.setWindowTitle("Broken Constraints")
        self.tm.setEditTriggers(QtGui.QTableWidget.NoEditTriggers)
        self.tm.setRowCount(0)
        self.tm.setColumnCount(10)
        self.tm.setMouseTracking(True)
        self.tm.cellClicked.connect(self.cell_was_clicked)
        self.tm.setHorizontalHeaderLabels(['Direction',
                                           'Suppress',
                                           'Run',
                                           'Constraint name',
                                           'Prt1 feat',
                                           'Prt2 feat',
                                           'F1',
                                           'Part1',
                                           'F2',
                                           'Part2'
                                           ]
                                          ) 
        self.tm.horizontalHeader().sectionClicked.connect(self.fun)

        """ Creating function buttons """
        self.btns = []
        btnLabels = [
            ['Import from part', 'Select a part and import \nall of the constraints for that part'],
            ['Import from Tree', 'Copy selected constraints from the Tree']
            ]
        self.createButtonColumn(5, btnLabels)

        btnLabels = [
            ['Clear Table', 'Clear the table'],
            ['Attach to', 'Select the feature to change in table.\nselect surface to change to.\n']
            ]
        self.createButtonColumn(140, btnLabels)

        btnLabels = [
            ['Clear Tree', 'Remove search color from tree.\n'],
            ['Find in Tree', 'Finds the constraint in the tree\nfor the select row in table.']
            ]
        self.createButtonColumn(280, btnLabels)

        btnLabels = [
            ['Std Solver','Same as the solver above.\n'],
            ['Find w label', 'Press to toggle a label for selected feature.']
            ]
        self.createButtonColumn(420, btnLabels)


    def createButtonColumn(self, xloc, btnLabels):
        for row in range(0, len(btnLabels)):
            btny = 30 +(26*row)
            self.btn = QtGui.QPushButton(str(btnLabels[row][0]), self)
            self.btn.move(xloc, btny)
            self.btn.setFixedWidth(130)
            self.btn.setFixedHeight(25)
            self.btn.setToolTip(btnLabels[row][1])
            self.btn.released.connect(self.button_pushed) # pressed
            self.btns.append(self.btn)

    def button_pushed(self):
        index = self.btns.index(self.sender())
        buttext = self.btns[index].text()
        if buttext == 'Import from part':
            conflicts.selectforpart()
        if buttext == 'Import from Tree':
            conflicts.selectforTree()
        if 'Find in Tree' in buttext:
            searchterm = lastclc.cname
            search.startsearch(searchterm, 0)
        if 'Clear Tree' in buttext:
            search.reset1()
        if 'Clear Table' in buttext:
            self.clearTable()
        if buttext == 'Attach to':
            """ attaches leg to selected surface"""
            sidefuncs.swapselectedleg()
        if buttext == 'Std Solver':
            self.stdSolve()
        if buttext == 'Find w label':
            """ createlabel for single part """
            if g.labelexist:
                CD_featurelabels.labels.deletelabels()
                g.labelexist = False
                return
            fname = lastclc.text
            if lastclc.column == 4:
                pname = self.tm.item(lastclc.row, 7).text()
            elif lastclc.column == 5:
                pname = self.tm.item(lastclc.row, 9).text()
            else:
                mApp('A part feature must be selected in the table')
                return
            sels = FreeCAD.ActiveDocument.getObjectsByLabel(pname)
            for e in sels:
                try:
                    partobj = e  # line is used to check if part is selected
                except:
                    mApp('The table has lost focus. \nPlease reselect in the table.')
                    return
                s = FreeCADGui.Selection.getSelectionEx()[0]
                try:
                    ent = s.SubObjects[0]
                except:
                    mApp('The selected text in the table is not a proper feature name.\n' + fname + '   ' + pname)
                    return
                CD_featurelabels.labels.labelForTable(ent, fname)
                g.labelexist = True

        if buttext == 'Find Constraint':
            search.startsearch(lastclc.cname, 0)

    def clearTable(self):
        self.tm.setRowCount(0)

    def process_menus(self, q):
        """ process the menu according to the button text"""
        if q.text() == "Open Dialog":
            CD_featurelabels.form1.showme()
        if q.text() == "Delete labels":
            CD_featurelabels.labels.deletelabels()
        if q.text() == "Open Help":
            pdf_file = os.path.join(os.path.dirname(os.path.dirname(__file__)),'CD_Help for Diagnostic tools.pdf')
            # pdf_file = a2plib.pathOfModule() + "\CD_Help for Diagnostic tools.pdf"
            # For Linux Mint 21 64-bit
            if sys.platform in ['linux', 'linux2', 'darwin', 'cygwin']:
                import webbrowser
                webbrowser.open_new_tab(pdf_file)
            # For Windows 10 Pro 64-bit
            elif sys.platform == 'win32':
                subprocess.Popen([pdf_file], shell = True)
            # For others OS
            else:
                print("Found platform %s, OS %s" % (sys.platform, os.name))

    def process_misc_menus(self, q):
        menutext = q.text()
        if menutext == "Solve without error checking":
            conflicts.solveNOerrorchecking()

    def stdSolve(self):
        doc = FreeCAD.activeDocument()
        a2p_solversystem.solveConstraints(doc)

    def fun4(self, Ncol):
        self.tm = self.tm.sort_values(self.tm.headers[Ncol], ascending = QtGui.AscendingOrder)

    def fun(self, i):
        # click in column header to sort column
        self.tm.sortByColumn(i)

    def loadtable(self, listObjects):
        # fill the table with information from a list of constraints
        self.tm.setRowCount(0)
        doc = FreeCAD.activeDocument()
        row = 0
        for object in reversed(listObjects):
            try:
                cname = object.Name
                constraint = doc.getObject(cname)
            except:
                continue
            ob1 = doc.getObject(constraint.Object1)
            if hasattr(ob1, 'fixedPosition') == False:
                fixed1 = 'N'
            else:
                fixed1 = str(ob1.fixedPosition)
                fixed1 = fixed1[0:1]
            ob2 = doc.getObject(constraint.Object2)
            if hasattr(ob2, 'fixedPosition') == False:
                fixed2 = 'N'
            else:
                ob2 = doc.getObject(constraint.Object2)
                fixed2 = str(ob2.fixedPosition)
                fixed2 = fixed2[0:1]

            part1 = doc.getObject(constraint.Object1)
            part2 = doc.getObject(constraint.Object2)

            if hasattr(constraint, "directionConstraint"):
                direction = constraint.directionConstraint
            else:
                direction = 'None'
            self.tm.insertRow(0)
            fn1 = constraint.SubElement1
            fn2 = constraint.SubElement2
            if len(fn1 ) == 0:
                fn1 = 'None'
            if len(fn2) == 0:
                fn2 = 'None'
            direction = QtGui.QTableWidgetItem(direction)
            sup = QtGui.QTableWidgetItem(str(constraint.Suppressed))
            run = QtGui.QTableWidgetItem(str('Run'))
            name = QtGui.QTableWidgetItem(cname)
            fixed1 = QtGui.QTableWidgetItem(fixed1[0])
            Part1 = QtGui.QTableWidgetItem(part1.Label)
            fname1 = QtGui.QTableWidgetItem(fn1)
            fixed2 = QtGui.QTableWidgetItem(fixed2[0])
            Part2 = QtGui.QTableWidgetItem(part2.Label)
            fname2 = QtGui.QTableWidgetItem(fn2)
            self.tm.setItem(0, 0, direction)
            self.tm.setItem(0, 1, sup)
            self.tm.setItem(0, 2, run)
            self.tm.setItem(0, 3, name)
            self.tm.setItem(0, 4, fname1)
            self.tm.setItem(0, 5, fname2)
            self.tm.setItem(0, 6, fixed1)
            self.tm.setItem(0, 7, Part1)
            self.tm.setItem(0, 8, fixed2)
            self.tm.setItem(0, 9, Part2)

            if self.tm.item(0, 4).text() == 'None':
                self.tm.item(0, 4).setBackground(QtGui.QBrush(QtGui.QColor('yellow')))

            if self.tm.item(0, 5).text() == 'None':
                self.tm.item(0, 5).setBackground(QtGui.QBrush(QtGui.QColor('yellow')))
            row = row+1

            if cname in CD_checkconstraints.g.allErrors:
                if CD_checkconstraints.g.allErrors[cname].get('errortype') == 'Direction':
                    self.tm.item(0, 3).setBackground(QtGui.QBrush(QtGui.QColor('yellow')))
        header = self.tm.horizontalHeader()
        header.setResizeMode(QtGui.QHeaderView.ResizeToContents)
        self.current_hover = [0, 0]
        self.hoveronoff(True)

        self.oldcell = self.tm.item(2, 1)
        self.tm.current_hover = [0, 0]
        for row in range(self.tm.rowCount()):
            self.tm.setRowHeight(row, 15)

    def hoveronoff(self,val):
        self.tm.setMouseTracking(val)

    def cell_was_clicked(self, row, column):
        header = self.tm.horizontalHeaderItem(column).text()
        item = self.tm.item(row, 3)
        lastclc.cellpicked(row,column)
        cname = item.text()
        try:
            constraint = FreeCAD.ActiveDocument.getObject(cname)
            partobj1 = FreeCAD.ActiveDocument.getObject(constraint.Object1)
            partobj2 = FreeCAD.ActiveDocument.getObject(constraint.Object2)
        except:
            mApp('Constraint is not in file. Was it deleted?')
            return
        FreeCADGui.Selection.clearSelection()
        if header == 'Run':
            conflicts.checkforfixandsolve([constraint])
            FreeCADGui.Selection.addSelection(partobj1, constraint.SubElement1)
            FreeCADGui.Selection.addSelection(partobj2, constraint.SubElement2)
        if header == 'Constraint name':
            FreeCADGui.Selection.addSelection(partobj1, constraint.SubElement1)
            FreeCADGui.Selection.addSelection(partobj2, constraint.SubElement2)
        if header == 'Prt1 feat':
            FreeCADGui.Selection.addSelection(partobj1, constraint.SubElement1)
            g.lastclickedFeat = FreeCADGui.Selection.getSelection()
        if header == 'Prt2 feat':
            FreeCADGui.Selection.addSelection(partobj2, constraint.SubElement2)
            g.lastclickedFeat = FreeCADGui.Selection.getSelection()
            FreeCADGui.Selection.setPreselection
        if header == 'Part1':
            FreeCADGui.Selection.addSelection(partobj1)
        if header == 'Part2':
            FreeCADGui.Selection.addSelection(partobj2)

        if header == 'Suppress':
            if constraint.Suppressed == False:
                constraint.Suppressed = True
            else:
                constraint.Suppressed = False
            tx = str(constraint.Suppressed)
            item2 = self.tm.item(row, column)
            item2.setText(tx)
        if header == 'Direction':
            item2 = self.tm.item(row, column)
            if item2.text() != 'None':
                direction = constraint.directionConstraint
                if direction =='opposed':
                    newdir = 'aligned'
                else:
                    newdir ='opposed'
                constraint.directionConstraint = newdir
                direction = constraint.directionConstraint
                item2 = self.tm.item(row, column)
                #item2.setText(direction[0])
                item2.setText(direction)
                conflicts.checkforfixandsolve([constraint])

    def showme(self):
        if FreeCADGui.activeDocument() is None:
            msg = 'A file must be opened to start this selector\nPlease open a file and try again'
            mApp(msg)
            return()
        self.clearTable()
        self.show()
        lastclc.clear

    def Closeme(self):
        #close window and ensure that obsever is off
        selObv.SelObserverOFF()
        self.close()

    def closeEvent(self, event):
        selObv.SelObserverOFF()
        form1.Closeme()
        self.close()

    def resizeEvent(self, event):
        """ resize table """
        formx = self.width()
        formy = self.height()
        self.tm.resize(formx -20, formy -120)
form1=ShowPartProperties()




class classconflictreport():
    def __init__(self):
        self.name = None


    def selectforTree(self):
        doc = FreeCAD.activeDocument()
        clist = []
        sels = FreeCADGui.Selection.getSelectionEx()
        if len(sels) == 0:
            form1.clearTable()
            mApp('Nothing was selected in the Tree.')
            return
        for sel in sels:
            cname = sel.Object.Name
            cname = cname.replace('_mirror', '')
            cobj = doc.getObject(cname)
            if 'ConstraintInfo' in cobj.Content:
                clist.append(cobj)
            if len(clist) == 0:
                form1.clearTable()
                mApp('There were no constraints selected in the Tree.\nSelect one or more constraints and try again.')
                return
        form1.loadtable(clist)


    #select a part in the Gui and the attached constraints are sent to the form.
    def selectforpart(self):
        pnamelist = []
        doc = FreeCAD.activeDocument()
        clist = []
        sels = FreeCADGui.Selection.getSelectionEx()
        if len(sels) == 0:
            mApp('No parts were selected in the window.')
            return
        if len(sels) == 1:
            pnamelist.append(sels[0].Object.Label)
        else:
            for sel in sels:
                pnamelist.append(sel.Object.Label)
        for obj in FreeCAD.ActiveDocument.Objects: # Select constraints
            if 'ConstraintInfo' in obj.Content and '_mirror' not in obj.Name:
                    subobj1 = doc.getObject(obj.Object1)
                    subobj2 = doc.getObject(obj.Object2)
                    part1name = subobj1.Label
                    part2name = subobj2.Label
                    if len(sels) == 1:
                        if part1name in pnamelist or part2name in pnamelist:
                            clist.append(obj)
                    else:
                        if part1name in pnamelist and part2name in pnamelist:
                            clist.append(obj)
        if len(clist) == 0:
            if len(sels) == 1:
                msg = 'There are no constraints for this part.'
            else:
                msg = 'There are no constraints between these parts.'
            mApp(msg)
            return
        form1.loadtable(clist)

    def checkforfixandsolve(self, constraintlist):
        ''' Checks to see if both parts are fixed, then solves constraint. '''
        if len(constraintlist) == 0:
            return
        doc = FreeCAD.activeDocument()
        cobj = constraintlist[0]
        cobj = constraintlist[g.checkingnum]
        subobj1 = cobj.getPropertyByName('Object1')
        subobj2 = cobj.getPropertyByName('Object2')
        part1 = doc.getObject(subobj1) # Save Position and fixed
        part2 = doc.getObject(subobj2)
        self.p1fix = False
        self.p2fix = False
        ''' Get if both parts are fixed '''
        if hasattr(part1, "fixedPosition"):
            self.p1fix = part1.fixedPosition
        if hasattr(part2, "fixedPosition"):
            self.p2fix = part2.fixedPosition
        if self.p1fix and self.p2fix:
            mApp('Both parts are fixed.')
            return
        ''' if neither is fixed '''
        if self.p1fix == False and self.p2fix == False:
            part1.fixedPosition = True
        a2p_solversystem.solveConstraints(doc, matelist = constraintlist, showFailMessage = False)
        if hasattr(part1, "fixedPosition"):
            part1.fixedPosition = self.p1fix
        return
conflicts = classconflictreport()

class classsidefunctions():
    def __init__(self, name):
        self.name = name
        self.sel1 = ''

    def swapselectedleg(self):
        #starts observer to select a new feature when replacing manually.
        if lastclc.column < 4 or lastclc.column > 5:
            mApp('Surfaces can only be replaced in columns/nPart1 feat or Part2 feat')
            return
        if len(FreeCADGui.Selection.getSelectionEx()) == 0 and lastclc.text != 'None':
            mApp('No feature has been selected')
            return
        selObv.SelObserverON()


    def turnoffobserv(self):
        #Turns observer off and selects both features
        selObv.SelObserverOFF()
        self.swap1leg()

    def swap1leg(self):
        """ This is used to swap one surface for another manually """
        feat2name = ""
        if len(FreeCADGui.Selection.getSelectionEx()) == 0:
            return
        sel = FreeCADGui.Selection.getSelectionEx()[0]
        if lastclc.text == 'None':
            feat2name = sel.SubElementNames[0]
        else:
            feat2name = sel.SubElementNames[0]
        cname = lastclc.cname
        FreeCADGui.Selection.clearSelection()
        d = {'cname' : cname,
             'SubElement' : lastclc.SubElement,
             'dir' : lastclc.dir,
             'newfeat' : feat2name
             }
        self.swapfeature(d)
        cobj = FreeCAD.ActiveDocument.getObject(cname)
        partobj1 = FreeCAD.ActiveDocument.getObject(cobj.Object1)
        partobj2 = FreeCAD.ActiveDocument.getObject(cobj.Object2)
        if sel.Object.Name != partobj1.Name and sel.Object.Name != partobj2.Name:
            mApp('The constraint can only be moved to another surface of the same part')
            return
        FreeCADGui.Selection.addSelection(partobj1, cobj.SubElement1)
        FreeCADGui.Selection.addSelection(partobj2, cobj.SubElement2)
        """ Adds new feature name to table """
        form1.tm.item(lastclc.row, lastclc.column).setText(feat2name)

    def swapfeature(self, newfeaturedict):
        #changes a legs mating feature
        newfeat = newfeaturedict.get('newfeat')
        cname = newfeaturedict.get('cname')
        cobj = FreeCAD.ActiveDocument.getObject(cname)
        mobj = FreeCAD.ActiveDocument.getObject(cname+'_mirror')
        SubElement = newfeaturedict.get('SubElement')

        if SubElement == 'SubElement1':
            cobj.SubElement1 = newfeat
            mobj.SubElement1 = newfeat
        if SubElement == 'SubElement2':
            cobj.SubElement2 = newfeat
            mobj.SubElement2 = newfeat
        direction = newfeaturedict.get('dir')
        if hasattr(cobj, 'directionConstraint'):
            cobj.directionConstraint = direction
        if hasattr(mobj, 'directionConstraint'):
            mobj.directionConstraint = direction
        return

sidefuncs = classsidefunctions('sidefuncs')


class SelObserver:
    def __init__(self):
        pass
    def SelObserverON(self):
        FreeCADGui.Selection.addObserver(selObv)        
    def SelObserverOFF(self):
        #print('SelObserverOFF')
        try:
            FreeCADGui.Selection.removeObserver(selObv)
        except:
            print('removeObserver failed in C checker')

    def setPreselection(self, doc, obj, sub): # Preselection object
        pass
    
    def addSelection(self, doc, obj, sub, pnt): # Selection object
        sidefuncs.turnoffobserv()

    def removeSelection(self, doc, obj, sub): # Delete the selected object
        pass
    
    def setSelection(self, doc):
        #this is sent from menu
        #funcs.constraintselected('table') #funcs does not exist ??!!
        pass
selObv = SelObserver()


class classsearch():
    ''' This is for searching in tree for constraint name '''
    def __init__(self):
        self.founditems = []
    def startsearch(self, searchterm, colnum):
        mw = FreeCADGui.getMainWindow()
        tab = mw.findChild(QtGui.QTabWidget, u'combiTab')
        tree = tab.widget(0).findChildren(QtGui.QTreeWidget)[0]
        top = tree.topLevelItem(0)
        for idx in range(top.childCount()):
            self.searchTreeItem(tree, top.child(idx), searchterm, colnum)

    def searchTreeItem(self, tree, item, searchterm, colnum):
        for idx in range(item.childCount()):
            itm = item.child(idx)
            if searchterm in itm.text(colnum):
                itm.setBackground(0, QtGui.QColor(255, 255, 0, 100))
                self.expandParent(tree, itm)
            self.searchTreeItem(tree, item.child(idx), searchterm, colnum)

    def expandParent(self, tree, item):
        parent = item.parent()
        if parent:
            tree.expandItem(parent)
            self.expandParent(tree, parent)

    def resetAll(self, item):
        for idx in range(item.childCount()):
            itm = item.child(idx)
            self.founditems.append(itm)
            itm.setBackground(0, QtGui.QBrush())
            self.resetAll(itm)


    def reset1(self):
        mw = FreeCADGui.getMainWindow()
        tab = mw.findChild(QtGui.QTabWidget, u'combiTab')
        tree = tab.widget(0).findChildren(QtGui.QTreeWidget)[0]
        top = tree.topLevelItem(0)
        for idx in range(top.childCount()):
            self.resetAll(top.child(idx))
search = classsearch()


def rondlist(inputList, inch = False):
    x = inputList[0]
    y = inputList[1]
    z = inputList[2]
    x = rondnum(x)
    y = rondnum(y)
    z = rondnum(z)
    if inch:
        x = x/25.4
        y = y/25.4
        z = z/25.4
    return([x, y, z])

def rondnum(num, mmorin = 'mm'):
    """" round a number to digits in global
        left in mm for accuracy. """
    rn = round(num, g.roundto)
    if mmorin == 'in':
        rn = rn / 25.4
    return(rn)

class classlastclickeditem:
    def __init__(self, Name):
        self.row = -1
        self.column = -1
        self.header = ''
        self.cname = ''
        self.cobj = None
        self.dir = 'N'
        self.text = ''
        self.SubElement = ''

    def clear(self):
        self.row = -1
        self.column = -1
        self.header = ''
        self.cname = ''
        self.cobj = None
        self.dir= 'N'

    def cellpicked(self, row, column):
        item = form1.tm.item(row, column)
        self.item = item
        self.row = row
        self.column = column
        self.text = item.text()
        self.header = form1.tm.horizontalHeaderItem(column).text()
        citem = form1.tm.item(self.row, 3)
        cname = citem.text()
        self.cname = cname
        self.cobj = FreeCAD.ActiveDocument.getObject(self.cname)
        if hasattr(self.cobj, 'directionConstraint'):
            self.dir = self.cobj.directionConstraint
        if self.column == 4:
            self.SubElement = 'SubElement1'
        if self.column == 5:
            self.SubElement = 'SubElement2'
        return(self.SubElement)
    
lastclc = classlastclickeditem("lastclc")


toolTipText = \
'''
Constraint Viewer. You can view the features the constraint is attached to,
 run a single constraint or change the the feature the constraint is attached to.
See the help for more information.
'''

class rnp_Constraint_Viewer:

    def Activated(self):
        form1.showme()

    def Deactivated(self):
        """This function is executed when the workbench is deactivated"""
        return

    def GetResources(self):
        mypath = os.path.dirname(__file__)
        return {
             'Pixmap' : mypath + "/icons/CD_ConstraintViewer.svg",
             'MenuText': 'View and edit selected constraints',
             'ToolTip': toolTipText
             }

FreeCADGui.addCommand('rnp_Constraint_Viewer', rnp_Constraint_Viewer())
#==============================================================================
