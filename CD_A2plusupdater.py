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
#

import sys
import os
import FreeCADGui
import FreeCAD
from PySide import QtUiTools
from PySide.QtGui import *
from PySide import QtGui, QtCore
import a2plib
import a2p_solversystem
from a2p_solversystem import solveConstraints
import CD_importpart
import CD_checkconstraints
import CD_ConstraintDiagnostics


class globaluseclass:

    def __init__(self, name):
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
        #self.usedfeatures = []
        self.clist = []
        self.partobj = None
        self.test = []
        self.cylfaces = []
        self.notcylfaces = []
        self.repaired = 0
g = globaluseclass("g")


class sideFuncs1():
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
sideFuncs = sideFuncs1()



class   classFuncs():
    def __init__(self):
        pass


    def runinorder(self):
        partname = 'fff'
        partname = self.selectfiles()
        if partname == 'No':
            return
        if partname == 'fff':
            return
        self.secondrun(partname,False)


    def selectfiles(self):
        ret =sideFuncs.opendoccheck()
        if ret == 'Nostart':
            return('No')
        doc = FreeCAD.activeDocument()
        partslist = FreeCADGui.Selection.getSelection()
        if len(partslist) == 0:
            mApp('1 No parts were selected to update.\nSelect one part and try again.')
            return('No')
        if len(partslist) > 1:
            mApp('I have limited the number of parts that can be updaated to 1.\nSelect one part and try again.')
            return('No')
        CD_ConstraintDiagnostics.statusform.show()
        CD_ConstraintDiagnostics.statusform.txtboxstatus.setText('Updating Assembly.')
        CD_ConstraintDiagnostics.statusform.update()

        for num in range(0,len(partslist)):
            partobj = partslist[num]
            partname = self.firstrun(partobj)
            self.secondrun(False)

    def firstrun(self,partobj):
        g.resetvars()  # reset Variables
        partname = 'none'
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
            newobj = None
            CD_importpart.updateImportedParts(doc, True)
        newobj = g.partobj
        FreeCADGui.updateGui()
        g.shape2 = newobj.Shape
        getfacelists()
        self.runpostchange()
        doc.recompute()
        FreeCADGui.updateGui()
        CD_ConstraintDiagnostics.statusform.Closeme()

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
            CD_ConstraintDiagnostics.form1.show()
            CD_ConstraintDiagnostics.form1.loadtable(clist)
        else:
            mApp('Update complete. All surfaces found')
        print('update complete')

        print('Repaired constraints = ' + (str(g.repaired - len(g.notfoundfeatures))))

    def getfeatstomove(self):
        doc = FreeCAD.activeDocument()
        clist = selectforpart(g.partlabel)
        g.clist = clist
        featname = ''
        di = {}
        for cobj in clist:
            # get feature info before update
            partname = g.partname
            featname = ''
            subElement = ""
            subElement = ""
            subobj1 = doc.getObject(cobj.Object1)
            subobj2 = doc.getObject(cobj.Object2)
            frompart = [g.partlabel, g.partname]
            for i in range(0,len(frompart)):
                partname = frompart[i]
                if subobj1.Label == partname:
                    subElement = "SubElement1"
                    featname = cobj.SubElement1
                if subobj2.Label == partname:
                    subElement = "SubElement2"
                    featname = cobj.SubElement2
                if featname != '':
                    break
            dir = 'N'
            if hasattr(cobj,'directionConstraint'):
                dir = cobj.directionConstraint
            # dict is basic info for constraint
            # these next functions adds info for the subelements
            if 'Face' in featname:
                # add face info
                facenum = int(featname[4:])
                di = self.getfacebynum(facenum-1,g.shape1)
            if 'Edge' in featname:
                # add edge info
                num = int(featname[4:])
                num = num - 1
                di = self.getedgebynum(num,g.shape1)
            if 'V' in featname:
                # add Vertex info
                num = int(featname[6:])
                num = num - 1
                di = self.getvertexbynum(num, g.shape1)
            dict = {'Name':cobj.Name,'cname':cobj.Name,'featname':featname,'subElement':subElement,'dir':dir,'newname':''}
            dict.update(di)

            g.alldicts[cobj.Name] = dict # Save the info to a larger dictionary


    def getfacebynum (self,facenum,shape):
        """Get face info."""
        face = shape.Faces[facenum]
        area = rondnum(face.Area)
        surftype = face.Surface
        facepoints = []
        points = []
        center = -1


        edge1 = face.Edges[0]

        eeee = face.Edges
        numofpoints = len(face.Vertexes)
        for f0 in face.Vertexes:         # Search the Vertexes of the face
            point = FreeCAD.Vector(f0.Point.x,f0.Point.y,f0.Point.z)
            x,y,z = point
            loc = rondlist([x,y,z])
            facepoints.append(loc)
        volume = rondnum(face.Volume)
        radius = -1

        surftype = face.Surface
        surfstr = str(surftype)

        if'Cylinder' in surfstr:
            surfstr = 'Cylinder'
            radius = rondnum(surftype.Radius)
            center = rondlist(face.Edges[0].CenterOfMass)

        if'Plane' in surfstr:
            surfstr = 'Plane'
        dict ={'surftype':surfstr,'area':area,'facepoints':facepoints,'center':center,'radius':radius,'edges':eeee}

        return(dict)



    def getedgebynum (self,num,shape):

        pnt1 = None
        pnt2 = None
        edge = shape.Edges[num]
        length = edge.Length
        length = rondnum(edge.Length)
        center = edge.CenterOfMass
        center = rondlist(center)
        pnt1 = edge.Vertexes[0]         # Basepoints
        x1 = pnt1.Point.x
        y1 = pnt1.Point.y
        z1 = pnt1.Point.z
        startpoint = rondlist([x1,y1,z1])
        a = FreeCAD.Vector(x1,y1,z1)
        b = FreeCAD.Vector()
        try:
            pnt2 = edge.Vertexes[1]     # Basepoints
            x2 = pnt2.Point.x
            y2 = pnt2.Point.y
            z2 = pnt2.Point.z
            endpoint = [x2,y2,z2]
            b=FreeCAD.Vector(x2,y2,z2)
            endpoint = rondlist([x2,y2,z2])
        except:
            endpoint = ["-","-","-"]


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
        dict = {'curvetype':curvetype,'obj':edge,'length':length,'startpoint':startpoint,'center':center,'endpoint':endpoint,'radius':radius,'vector':vector}

        return(dict)


    def getvertexbynum(self,num,shape):
        v=shape.Vertexes[num]
        x=v.Point.x
        y=v.Point.y
        z=v.Point.z
        xyz = [x,y,z]

        xyz= rondlist([x,y,z])
        return({'xyz':xyz})

        ## post functions***********************************

    def findfeats_attempt1(self):
        """Try to find features after the update."""
        doc = FreeCAD.activeDocument()
        for k,dict in g.alldicts.items():
            dict = dict
            newfeat = ''
            featname =dict.get('featname')
            if featname in g.foundfeatures:
                newfeat = g.dictOldNew.get(featname)
            else:
                if 'Face' in featname:
                    newfeat = self.findnewface_attempt1(dict)
                if 'Edge' in featname:
                    newfeat = self.findnewedge_attempt1(dict)
                if 'Vertex' in featname:
                    newfeat = self.findnewvertex_attempt1(dict)
                if newfeat =='' or newfeat == 'No':
                    g.notfoundfeatures.append([dict.get('Name'),dict])
                    pass
                else:
                    if newfeat in g.foundfeatures == False:
                        g.foundfeatures.append(newfeat) #
                        g.dictOldNew[featname] = newfeat

                    self.swapfeature(newfeat,dict)
            doc.recompute()


        if len(g.notfoundfeatures) > 0:
            self.findfeats_attempt2()


    def swapfeature(self,newfeat,dict):
        """Add the new feature to the constraint."""
        cname = dict.get('cname')
        g.partlog.append('Found ' + newfeat)
        cobj = FreeCAD.ActiveDocument.getObject(cname)
        mobj = FreeCAD.ActiveDocument.getObject(cname+'_mirror')
        SubElement = dict.get('subElement')
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
        dir = dict.get('dir')
        if hasattr(cobj,'directionConstraint'):
            cobj.directionConstraint = dir
        if hasattr(mobj,'directionConstraint'):
            mobj.directionConstraint = dir
        return

    # If not found on first attempt try again
    def findfeats_attempt2(self):
        newfeat = ''
        notfoundtemp = g.notfoundfeatures


        g.notfoundfeatures = []
        for ea in notfoundtemp:
            dict = ea[1]
            featname = dict.get('featname')
            if featname in g.foundfeatures:
                newfeat = g.dictOldNew.get(featname)
            else:
                if 'Face' in featname:
                    newfeat = self.findnewface_attempt2(dict)
                if 'Edge' in featname:
                    newfeat = self.findnewedge_attempt2(dict)
                if newfeat == 'No' or newfeat == '':
                    g.notfoundfeatures.append([dict.get('Name'),dict])
                    newfeat = 'None'
                else:
                    if newfeat in g.foundfeatures == False:
                        g.foundfeatures.append(newfeat)
                        g.dictOldNew[featname] = newfeat
            self.swapfeature(newfeat,dict)


    def findnewface_attempt1(self,dict):
        # First attempt to find a face. Perfect fit is area the same all points the same
        face = ''
        # newfeat = ''
        # surftype = dict.get('surftype')
        if dict.get('surftype') == 'Cylinder':
                face = self.findCylinderattempt1(dict)
        else:
            for num in range(0,len(g.shape2.Faces)):
                testdict = self.getfacebynum(num,g.shape2)
                if testdict.get('surftype') != 'Cylinder':
                    if dict.get('area') == testdict.get('area')\
                        and dict.get('facepoints') == testdict.get('facepoints'):
                        face = 'Face' + str(num +1)
                        break
        return(face)



    def findnewface_attempt2(self,dict):
        face = ''
        # second attempt ignores area; looks for points
        face = ''
        if dict.get('surftype') == 'Cylinder':
            face = self.findCylinderattempt2(dict)


        else:

            for num in range(0,len(g.shape2.Faces)):
                testdict = self.getfacebynum(num,g.shape2)
                if dict.get('surftype') != 'Cylinder':

                    points = dict.get('facepoints')
                    testpoints = testdict.get('facepoints')

                    # points = points[1]
                    # testpoints =testpoints [1]
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

                dedges = dict.get('edges')
                edge = dedges[0]
                pnt1 = edge.Vertexes[0]             # Basepoints
                x = pnt1.Point.x
                y = pnt1.Point.y
                z = pnt1.Point.z
                dlist = [rondnum(edge.Length),x,y,z]
                for num in range(0,len(g.shape2.Faces)):

                    testdict = self.getfacebynum(num,g.shape2)
                    if dict.get('surftype') != 'Cylinder':
                        ed = testdict.get('edges')
                        ary = []
                        for e in ed:
                            pnt1 = e.Vertexes[0]    # Basepoints
                            x = pnt1.Point.x
                            y = pnt1.Point.y
                            z = pnt1.Point.z
                            tlist = [e.Length,x,y,z]
                            if dlist == tlist:
                                face = 'Face' + str(num+1)
                                break
        return(face)


    def findCylinderattempt1(self,dict):
        face = ''
        for num in g.cylfaces:
            testdict = self.getfacebynum(num,g.shape2)
            if dict.get('facepoints') == testdict.get('facepoints') and\
               dict.get('radius') == testdict.get('radius'):
                face = 'Face' + str(num +1)

                break
        return(face)


    def findCylinderattempt2(self,dict):
        #First attempt to find a face. Perfect fit is area the same all points the same
        face = ''
        ver1 = dict.get('center')
        for num in g.cylfaces:
            testdict = self.getfacebynum(num,g.shape2)
            ver2 = testdict.get('center')
            if ver1 == ver2:
                face = 'Face' + str(num+1)
                break
        return(face)


    def findnewedge_attempt1(self,dict):
        edge = ''
        if dict.get('curvetype') == 'circle':
            center1 = dict.get('center')
            for num in range(0,len(g.shape2.Edges)):
                testdict = self.getedgebynum(num,g.shape2)
                center2 = testdict.get('center')
                if dict.get('radius') ==  testdict.get('radius')\
                        and dict.get('center') == testdict.get('center'):
                        edge ='Edge' + str(num +1)
                        break




        else:
            for num in g.notcylfaces:
                testdict = self.getfacebynum(num,g.shape2)
                if dict.get('length') == testdict.get('length')\
                   and dict.get('center') == testdict.get('center'):
                    edge ='Edge' + str(num +1)
                    break

        return(edge)


    def findnewedge_attempt2(self,dict):
        edge = ''
        if dict.get('curvetype') == 'circle':
            center1 = dict.get('center')
            for num in range(0,len(g.shape2.Edges)):

                testdict = self.getedgebynum(num,g.shape2)

                center2 = testdict.get('center')
                if center1 == center2:
                        edge ='Edge' + str(num +1)
                        break


        for num in range(0,len(g.shape2.Edges)):
            testdict = self.getedgebynum(num,g.shape2)
            if dict.get('curvetype') == 'circle':
                if testdict.get('curvetype') == 'circle':

                    if dict.get('startpoint') == testdict.get('startpoint'):
                        edge ='Edge' + str(num +1)
                        break

        return(edge)


        #pnts = g.shape2.Vertexes
        #mypoint = dict.get('mypoint')
        #ent = None
        #for p in g.shape2.Vertexes:
        #    if p.Point == mypoint.Point:
        #        ent = p
        #        break
        #mApp('found mypoint')
        #allegdes = []
        #for e in g.shape2.edges:
        #    if e.Vertex[0].isSame(ent) or e.Vertex[1].isSame(ent):
        #        alledges.append(e)
        #        FreeCADGui.Selection.addSelection(e)
        #return(edge)




    def findnewvertex_attempt1(self,dict):
        vertex = ''
        featname = dict.get('featname')
        for num in range(0,len(g.shape2.Vertexes)):
            test = self.getvertexbynum(num,g.shape2)
            if dict.get('xyz') == test.get('xyz'):
                vertex = Vertex + str(num +1)
        return(vertex)

funcs = classFuncs()

def getfacelists():
    g.cylfaces = []
    g.notcylfaces= []

    for num in range(0,len(g.shape2.Faces)):
        if str(g.shape2.Faces[num].Surface) == '<Cylinder object>':
            g.cylfaces.append(num)
        elif str(g.shape2.Faces[num].Surface) == '<Plane object>':
            g.notcylfaces.append(num)



def selectforpart(partlabel,selectType = 'std'):
    #find the constraints for the part selected
    doc = FreeCAD.activeDocument()
    clist = []
    pnamelist =[]
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


def rondnum(num,rndto = g.roundto,mmorin='mm'):
    # round a number to digits in global
    # left in mm for accuracy.
    rn = round(num,rndto)
    if mmorin == 'in':
        rn = rn/25.4

    return(rn)


def rondlist(list,inch = False):
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


    return([x,y,z])



class mApp(QWidget):
    # for error messages
    def __init__(self,msg,msgtype = 'ok'):
        super().__init__()
        self.title = 'PyQt5 messagebox'
        self.left = 600
        self.top = 100
        self.width = 320
        self.height = 200
        self.initUI(msg)

    def initUI(self,msg,msgtype = 'ok'):
        self.setWindowTitle(self.title)
        self.setGeometry(800, 300, 300, 400)
        if msgtype == 'ok':
            buttonReply = QMessageBox.question(self, 'PyQt5 message', msg, QMessageBox.Ok | QMessageBox.Ok)
        if msgtype == 'yn':
            buttonReply = QMessageBox.question(self, 'PyQt5 message', msg, QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if buttonReply == QMessageBox.Yes:
            return('y')
        else:
            return('n')





toolTipText = \
'''
Updates the A2plus.assembly when parts are modified.
To update the assembly, select the part that you have modified and press the icon.
When the update has finished run the A2plus solver to vereify if there are broken constraints.
This is an attempt to reduce the number of broken constraints caused
when modifying a part from FreeCAD’s A2plus assembly program. This records the
constraint’s mating surfaces immediately before the update and tries to
reconnect them after the update.
If this fails you can undo this update by using the undo button
and running the standard A2plus updater.
'''

class rnp_Update_A2pParts:

    def Activated(self):
        #funcs.runinorder()
        funcs.selectfiles()

    def Deactivated():
        """This function is executed when the workbench is deactivated"""
        FreeCADGui.Selection.clearSelection()
        return



    def GetResources(self):
        mypath = os.path.dirname(__file__)
        return {
             'Pixmap' : mypath + "/icons/updateA2.svg",
             'MenuText': 'Updates parts from the A2plus program that has been modified',
             'ToolTip': 'Updates modifed parts.'
             }

FreeCADGui.addCommand('rnp_Update_A2pParts',rnp_Update_A2pParts())
#==============================================================================

#2020-08-06 Changed Lines 162 to 172 to open the viewer if the are missing features.


