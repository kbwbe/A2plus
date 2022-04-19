# -*- coding: utf-8 -*-
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
"""
This is to be used in conjunction with A2plus Assembly Workbench.

It records the features which are linked to the constraints and searches
for mating features after the part is replaced in the assembly.
"""

import os
import FreeCADGui
import FreeCAD
from PySide import QtUiTools
from PySide.QtGui import *
from PySide import QtGui, QtCore
import a2p_importpart
import a2plib
import CD_ConstraintViewer


class globaluseclass:

    def __init__(self):
        self.roundto = 5
        self.partlabel = ''
        self.partname = ''
        self.notfoundfeatures = []
        self.foundfeatures = []
        self.dictOldNew = {}
        self.alldicts = {}
        self.clist = []
        self.partobj = None
        self.test = []
        self.cylfaces = []
        self.notcylfaces = []
        self.partlog = []

    def resetvars(self):
        self.partlabel = ''
        self.partname = ''
        self.notfoundfeatures = []
        self.foundfeatures = []
        self.dictOldNew = {}
        self.alldicts = {}
        self.clist = []
        self.partobj = None
        self.test = []
        self.cylfaces = []
        self.notcylfaces = []
        self.repaired = 0
g = globaluseclass()


class sideFuncs1():
    def __init__(self):
        pass
    def opendoccheck(self):
        doc = FreeCAD.activeDocument()
        if doc is None:
            msg = 'A file must be selected to start this selector\nPlease open a file and try again'
            mApp(msg)
            return('Nostart')

        return()
sideFuncs = sideFuncs1()



class classFuncs():
    def __init__(self):
        pass

    def selectfiles(self):
        ret = sideFuncs.opendoccheck()
        if ret == 'Nostart':
            return('No')
        partslist = FreeCADGui.Selection.getSelection()
        if len(partslist) == 0:
            mApp('No parts were selected to update.\nSelect one part and try again.')
            return('No')
        if len(partslist) > 1:
            mApp('I have limited the number of parts that can be updated to 1.\nSelect one part and try again.')
            return('No')
        statusform.show()
        statusform.txtboxstatus.setText('Updating Assembly.')
        statusform.update()

        for num in range(0, len(partslist)):
            partobj = partslist[num]
            self.firstrun(partobj)
            self.secondrun(False)

    def firstrun(self, partobj):
        g.resetvars()  # reset Variables
        g.partobj = partobj
        g.partlabel =partobj.Label
        partname = partobj.Name
        g.partname = partobj.Name
        g.shape1 = partobj.Shape
        self.getfeatstomove()
        FreeCADGui.updateGui()
        return(partname)

    def secondrun(self, newpart = False):
        doc = FreeCAD.activeDocument()

        if newpart is False:
            savedAutoSolveState = a2plib.getAutoSolveState()
            a2plib.setAutoSolve(False)
            a2p_importpart.updateImportedParts(doc, True)
            a2plib.setAutoSolve(savedAutoSolveState)

        newobj = g.partobj
        FreeCADGui.updateGui()
        g.shape2 = newobj.Shape
        getfacelists()
        self.runpostchange()
        doc.recompute()
        FreeCADGui.updateGui()
        statusform.Closeme()

    def runpostchange(self):

        doc = FreeCAD.activeDocument()
        self.findfeats_attempt1()
        doc.recompute()
        FreeCADGui.updateGui()
        doc = FreeCAD.activeDocument()
        FreeCADGui.updateGui()

        clist = []
        for e in g.notfoundfeatures:
            cobj = FreeCAD.ActiveDocument.getObject(e[0])
            clist.append(cobj)
        if len(clist) != 0:
            CD_ConstraintViewer.form1.show()
            CD_ConstraintViewer.form1.loadtable(clist)
        else:
            mApp('Update complete. All surfaces found')
        print('update complete')
        print('Total Constraints ' + str(len(g.clist)))
        print('Repaired constraints ' + (str(g.repaired )))
        print('Features not found ' + str(len(g.notfoundfeatures)))

    def getfeatstomove(self):
        doc = FreeCAD.activeDocument()
        clist = selectforpart(g.partlabel)
        g.clist = clist
        featname = ''
        di = {}
        for cobj in clist:
            """ get feature info before update."""
            partname = g.partname
            featname = ''
            subElement = ""
            subElement = ""
            subobj1 = doc.getObject(cobj.Object1)
            subobj2 = doc.getObject(cobj.Object2)
            frompart = [g.partlabel, g.partname]
            for i in range(0, len(frompart)):
                partname = frompart[i]
                if subobj1.Label == partname:
                    subElement = "SubElement1"
                    featname = cobj.SubElement1
                if subobj2.Label == partname:
                    subElement = "SubElement2"
                    featname = cobj.SubElement2
                if featname != '':
                    break

            direction = 'N'
            if hasattr(cobj, 'directionConstraint'):
                direction = cobj.directionConstraint

            """ dict is basic info for constraint
             these next functions adds info for the subelements"""
            if 'Face' in featname:
                """ add face info """
                facenum = int(featname[4:])
                di = self.getfacebynum(facenum-1, g.shape1)
            if 'Edge' in featname:
                """ add edge info """
                num = int(featname[4:])
                num = num - 1
                di = self.getedgebynum(num, g.shape1)
            if 'V' in featname:
                """ add Vertex info """
                num = int(featname[6:])
                num = num - 1
                di = self.getvertexbynum(num, g.shape1)
            d = {'Name': cobj.Name,
                 'cname': cobj.Name,
                 'featname': featname,
                 'subElement': subElement,
                 'dir': direction,
                 'newname': ''
                 }
            d.update(di)
            g.alldicts[cobj.Name] = d # Save the info to a larger dictionary


    def getfacebynum (self, facenum, shape):
        """Get face info."""
        face = shape.Faces[facenum]
        area = rondnum(face.Area)
        facepoints = []
        center = -1

        eeee = face.Edges
        # numofpoints = len(face.Vertexes)
        for f0 in face.Vertexes:         # Search the Vertexes of the face
            point = FreeCAD.Vector(f0.Point.x, f0.Point.y, f0.Point.z)
            x, y, z = point
            loc = rondlist([x, y, z])
            facepoints.append(loc)
        # volume = rondnum(face.Volume)
        radius = -1
        surftype = face.Surface
        surfstr = str(surftype)
        if 'Cylinder' in surfstr:
            surfstr = 'Cylinder'
            radius = rondnum(surftype.Radius)
            center = rondlist(face.Edges[0].CenterOfMass)
        if 'Plane' in surfstr:
            surfstr = 'Plane'
        d = {'surftype': surfstr,
             'area': area,
             'facepoints': facepoints,
             'center': center,
             'radius': radius,
             'edges': eeee
            }
        return(d)



    def getedgebynum (self, num, shape):

        pnt2 = None
        edge = shape.Edges[num]
        length = rondnum(edge.Length)
        center = edge.CenterOfMass
        center = rondlist(center)
        pnt1 = edge.Vertexes[0] # Basepoints
        x1 = pnt1.Point.x
        y1 = pnt1.Point.y
        z1 = pnt1.Point.z
        startpoint = rondlist([x1, y1, z1])
        try:
            pnt2 = edge.Vertexes[1]     # Basepoints
            x2 = pnt2.Point.x
            y2 = pnt2.Point.y
            z2 = pnt2.Point.z
            endpoint = [x2, y2, z2]
            endpoint = rondlist([x2, y2, z2])
        except:
            endpoint = ["-", "-", "-"]

        radius = -1
        vector = None
        curvetype = ''
        center = -1
        tstr = str(edge.Curve)
        if 'Line' in tstr:
            curvetype ='line'
        if 'Circle' in tstr:
            curvetype ='circle'
            radius = rondnum(edge.Curve.Radius)
            center = rondlist(edge.CenterOfMass)
        if 'Spline' in tstr:
            curvetype ='spline'  # A2 is not using these
        d = {'curvetype':curvetype,
                'obj':edge,
                'length':length,
                'startpoint':startpoint,
                'center':center,
                'endpoint':endpoint,
                'radius':radius,
                'vector':vector
                }

        return(d)

    def getvertexbynum(self, num, shape):
        v = shape.Vertexes[num]
        x = v.Point.x
        y = v.Point.y
        z = v.Point.z
        xyz = rondlist([x, y, z])
        return({'xyz':xyz})

        ## post functions***********************************

    def findfeats_attempt1(self):
        """Try to find features after the update."""
        doc = FreeCAD.activeDocument()
        for k, d in g.alldicts.items():
            newfeat = ''
            featname = d.get('featname')
            if featname in g.foundfeatures:
                newfeat = g.dOldNew.get(featname)
            else:
                if 'Face' in featname:
                    newfeat = self.findnewface_attempt1(d)
                if 'Edge' in featname:
                    newfeat = self.findnewedge_attempt1(d)
                if 'Vertex' in featname:
                    newfeat = self.findnewvertex_attempt1(d)
                if newfeat =='' or newfeat == 'No':
                    g.notfoundfeatures.append([d.get('Name'), d])
                    pass
                else:
                    if newfeat in g.foundfeatures == False:
                        g.foundfeatures.append(newfeat)
                        g.dOldNew[featname] = newfeat
                    self.swapfeature(newfeat, d)
            doc.recompute()

        if len(g.notfoundfeatures) > 0:
            self.findfeats_attempt2()

    def swapfeature(self, newfeat, d):
        """Add the new feature to the constraint."""
        cname = d.get('cname')
        g.partlog.append('Found ' + newfeat)
        cobj = FreeCAD.ActiveDocument.getObject(cname)
        mobj = FreeCAD.ActiveDocument.getObject(cname+'_mirror')
        SubElement = d.get('subElement')
        if SubElement == 'SubElement1':
            if cobj.SubElement1 != newfeat:
                cobj.SubElement1 = newfeat
                mobj.SubElement1 = newfeat
                g.repaired = g.repaired + 1
        if SubElement == 'SubElement2':
            if cobj.SubElement2 != newfeat:
                cobj.SubElement2 = newfeat
                mobj.SubElement2 = newfeat
                g.repaired = g.repaired + 1
        direction = d.get('dir')
        if hasattr(cobj, 'directionConstraint'):
            cobj.directionConstraint = direction
        if hasattr(mobj, 'directionConstraint'):
            mobj.directionConstraint = direction
        return

    # If not found on first attempt try again
    def findfeats_attempt2(self):
        newfeat = ''
        notfoundtemp = g.notfoundfeatures

        g.notfoundfeatures = []
        for ea in notfoundtemp:
            d = ea[1]
            featname = d.get('featname')
            if featname in g.foundfeatures:
                newfeat = g.dOldNew.get(featname)
            else:
                if 'Face' in featname:
                    newfeat = self.findnewface_attempt2(d)
                if 'Edge' in featname:
                    newfeat = self.findnewedge_attempt2(d)
                if newfeat == 'No' or newfeat == '':
                    g.notfoundfeatures.append([d.get('Name'), d])
                    newfeat = 'None'
                else:
                    if newfeat in g.foundfeatures == False:
                        g.foundfeatures.append(newfeat)
                        g.dOldNew[featname] = newfeat
            self.swapfeature(newfeat, d)


    def findnewface_attempt1(self, d):
        # First attempt to find a face. Perfect fit is area the same all points the same
        face = ''
        if d.get('surftype') == 'Cylinder':
                face = self.findCylinderattempt1(d)
        else:
            for num in range(0, len(g.shape2.Faces)):
                testd = self.getfacebynum(num, g.shape2)
                if testd.get('surftype') != 'Cylinder':
                    if d.get('area') == testd.get('area')\
                        and d.get('facepoints') == testd.get('facepoints'):
                        face = 'Face' + str(num +1)
                        break
        return(face)



    def findnewface_attempt2(self, dict_):
        """ second attempt ignores area; looks for points(perhaps this should be first
        if holes are added area would change)"""
        face = ''
        if dict_.get('surftype') == 'Cylinder':
            face = self.findCylinderattempt2(dict_)
        else:
            for num in range(0, len(g.shape2.Faces)):
                testdict_ = self.getfacebynum(num, g.shape2)
                if dict_.get('surftype') != 'Cylinder':
                    points = dict_.get('facepoints')
                    testpoints = testdict_.get('facepoints')
                    if len(points) < len(testpoints):
                        list1 = points
                        list2 = testpoints
                    else:
                        list1 = testpoints
                        list2 = points
                    match = 0
                    for vert in list1:
                        if vert in list2:
                            match = match+1
                            if match == len(list1):
                                face = 'Face' + str(num+1)
                                break

            if face == '':
                dedges = dict_.get('edges')
                edge = dedges[0]
                pnt1 = edge.Vertexes[0] # Basepoints
                x = pnt1.Point.x
                y = pnt1.Point.y
                z = pnt1.Point.z
                dlist = [rondnum(edge.Length), x, y, z]
                for num in range(0, len(g.shape2.Faces)):
                    testdict_ = self.getfacebynum(num, g.shape2)
                    if dict_.get('surftype') != 'Cylinder':
                        ed = testdict_.get('edges')
                        for e in ed:
                            pnt1 = e.Vertexes[0] # Basepoints
                            x = pnt1.Point.x
                            y = pnt1.Point.y
                            z = pnt1.Point.z
                            tlist = [e.Length, x, y, z]
                            if dlist == tlist:
                                face = 'Face' + str(num+1)
                                break
        return(face)


    def findCylinderattempt1(self, dict_):
        face = ''
        for num in g.cylfaces:
            testdict = self.getfacebynum(num, g.shape2)
            if dict_.get('facepoints') == testdict.get('facepoints') and\
               dict_.get('radius') == testdict.get('radius'):
                face = 'Face' + str(num +1)
                break
        return(face)

    def findCylinderattempt2(self, dict_):
        #First attempt to find a face. Perfect fit is area = same all points = same
        face = ''
        ver1 = dict_.get('center')
        for num in g.cylfaces:
            testdict_ = self.getfacebynum(num, g.shape2)
            ver2 = testdict_.get('center')
            if ver1 == ver2:
                face = 'Face' + str(num+1)
                break
        return(face)


    def findnewedge_attempt1(self, dict_):
        edge = ''
        if dict_.get('curvetype') == 'circle':
            for num in range(0, len(g.shape2.Edges)):
                testdict_ = self.getedgebynum(num, g.shape2)
                if dict_.get('radius') == testdict_.get('radius')\
                        and dict_.get('center') == testdict_.get('center'):
                        edge = 'Edge' + str(num +1)
                        break
        else:
            for num in g.notcylfaces:
                testdict_ = self.getfacebynum(num, g.shape2)
                if dict_.get('length') == testdict_.get('length')\
                   and dict_.get('center') == testdict_.get('center'):
                    edge ='Edge' + str(num +1)
                    break
        return(edge)


    def findnewedge_attempt2(self, dict_):
        edge = ''
        if dict_.get('curvetype') == 'circle':
            center1 = dict_.get('center')
            for num in range(0, len(g.shape2.Edges)):
                testdict_ = self.getedgebynum(num, g.shape2)
                center2 = testdict_.get('center')
                if center1 == center2:
                        edge ='Edge' + str(num +1)
                        break
        for num in range(0, len(g.shape2.Edges)):
            testdict_ = self.getedgebynum(num, g.shape2)
            if dict_.get('curvetype') == 'circle':
                if testdict_.get('curvetype') == 'circle':
                    if dict_.get('startpoint') == testdict_.get('startpoint'):
                        edge ='Edge' + str(num +1)
                        break
        return(edge)

    def findnewvertex_attempt1(self, dict_):
        vertex = ''
        for num in range(0, len(g.shape2.Vertexes)):
            test = self.getvertexbynum(num, g.shape2)
            if dict_.get('xyz') == test.get('xyz'):
                vertex = 'Vertex' + str(num +1)
        return(vertex)

funcs = classFuncs()

def getfacelists():
    g.cylfaces = []
    g.notcylfaces = []
    for num in range(0, len(g.shape2.Faces)):
        if str(g.shape2.Faces[num].Surface) == '<Cylinder object>':
            g.cylfaces.append(num)
        elif str(g.shape2.Faces[num].Surface) == '<Plane object>':
            g.notcylfaces.append(num)



def selectforpart(partlabel, selectType = 'std'):
    #find the constraints for the part selected
    doc = FreeCAD.activeDocument()
    clist = []
    pnamelist = []
    pnamelist.append(partlabel)
    for obj in FreeCAD.ActiveDocument.Objects: # Select constraints
        if 'ConstraintInfo' in obj.Content:
            if '_mirror' not in obj.Name:
                subobj1 = doc.getObject(obj.Object1)
                subobj2 = doc.getObject(obj.Object2)
                part1name = subobj1.Label
                part2name = subobj2.Label
                if selectType == 'betweenonly':
                    clist.append(obj)
                else:
                    if part1name in pnamelist or part2name in pnamelist:
                        clist.append(obj)
    return(clist)


def rondnum(num, rndto = g.roundto, mmorin = 'mm'):
    # round a number to digits in global
    # left in mm for accuracy.
    rn = round(num, rndto)
    if mmorin == 'in':
        rn = rn/25.4
    return(rn)


def rondlist(inpList, inch = False):
    x = inpList[0]
    y = inpList[1]
    z = inpList[2]
    x = rondnum(x)
    y = rondnum(y)
    z = rondnum(z)
    if inch:
        x = x/25.4
        y = y/25.4
        z = z/25.4
    return([x, y, z])



class mApp(QtGui.QWidget):
    # for error messages
    def __init__(self, msg, msgtype = 'ok'):
        super().__init__()
        #self.title = 'Information'
        self.initUI(msg)

    def initUI(self, msg, msgtype = 'ok'):
        #self.setWindowTitle(self.title)
        self.setGeometry(800, 300, 300, 400)
        if msgtype == 'ok':
            buttonReply = QtGui.QMessageBox.question(self, 'Information', msg, QtGui.QMessageBox.Ok | QtGui.QMessageBox.Ok)
        if msgtype == 'yn':
            buttonReply = QtGui.QMessageBox.question(self, 'Information', msg, QtGui.QMessageBox.Yes | QtGui.QMessageBox.No, QtGui.QMessageBox.No)
        if buttonReply == QtGui.QMessageBox.Yes:
            return('y')
        else:
            return('n')


class formReport(QtGui.QDialog):
    """ Form shows while updating edited parts. """
    def __init__(self, name):
        self.name = name
        super(formReport, self).__init__()
        self.setWindowTitle('Constraint Checker')
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        self.setGeometry(300, 100, 300, 200) # xy , wh
        self.setStyleSheet("font: 10pt arial MS")
        self.txtboxstatus = QtGui.QTextEdit(self)
        self.txtboxstatus.move(5,30)
        self.txtboxstatus.setFixedWidth(250)
        self.txtboxstatus.setFixedHeight(60)
        self.lblviewlabel = QtGui.QLabel(self)
        self.lblviewlabel.setText('Status"')
        self.lblviewlabel.move(5, 5)
        self.lblviewlabel.setFixedWidth(250)
        self.lblviewlabel.setFixedHeight(20)
        self.lblviewlabel.setStyleSheet("font: 13pt arial MS")

    def showme(self, msg):
        print('showing editing part')
        self.show()

    def Closeme(self):
        self.close()

    def closeEvent(self, event):
        self.close()

statusform = formReport('statusform')


toolTipText = \
'''
Updates the A2plus.assembly when parts are modified.
To update the assembly, select the part that you have modified and press the icon.
When the update has finished run the A2plus solver to vereify if there are broken constraints.
This is an attempt to reduce the number of broken constraints caused
when modifying a part from FreeCAD A2plus assembly program. This records the
constraints mating surfaces immediately before the update and tries to
reconnect them after the update.
If this fails you can undo this update by using the undo button
and running the standard A2plus updater.
'''

class rnp_Update_A2pParts:
    def Activated(self):
        #funcs.runinorder()
        funcs.selectfiles()

    def Deactivated(self):
        """This function is executed when the workbench is deactivated"""
        FreeCADGui.Selection.clearSelection()
        return

    def GetResources(self):
        mypath = os.path.dirname(__file__)
        return {
             'Pixmap': mypath + "/icons/updateA2.svg",
             'MenuText': 'Updates parts from the A2plus program that has been modified',
             'ToolTip': 'Updates modified parts.'
             }

FreeCADGui.addCommand('rnp_Update_A2pParts', rnp_Update_A2pParts())
#==============================================================================

#2020-08-06 Changed Lines 162 to 172 to open the viewer if there are missing features.


