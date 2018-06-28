#***************************************************************************
#*                                                                         *
#*   Copyright (c) 2018 kbwbe                                              *
#*                                                                         *
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

import FreeCAD, FreeCADGui, Part, Draft, math, MeshPart, Mesh, Drawing, time
import Spreadsheet
#from PyQt4 import QtGui,QtCore
from PySide import QtCore, QtGui

from FreeCAD import Base
from a2plib import appVersionStr
App=FreeCAD
Gui=FreeCADGui

class TopoNamer():
    '''
    Class TopoNamer:
    executes basic naming of edges and faces according to the objects-history
    Namesystem aims assembly-purposes...
    
    tn.executeNaming()  is the most important func which delivers the topoInfo-Data  
    '''

    def __init__(self,ob):
        self.faceNameList = []
        self.edgeNameList = []
        self.faceKeyList = []
        self.edgeKeyList = []

        self.finalFaceNames = []
        self.finalFaceKeys = []
        self.finalEdgeNames = []
        self.finalEdgeKeys = []
        
        self.topoInfo = []

        self.rootObject = ob

    def dirAndPosToString(self,dir1,pos1):
        tempStr = '#DIR'
        x = ("#%0.2f" % dir1.x)
        y = ("#%0.2f" % dir1.y)
        z = ("#%0.2f" % dir1.z)
        tempStr = tempStr + x +y +z
        tempStr = tempStr.replace('-0.00','0.00')
        #
        tempStr += '#AT'
        x = ("#%011.2f" % pos1.x)
        y = ("#%011.2f" % pos1.y)
        z = ("#%011.2f" % pos1.z)
        tempStr = tempStr + x +y +z
        #
        tempStr = tempStr.replace('-0000000.00','00000000.00')
        return tempStr

    def generatePlaneFaceKey(self,face,prevPlacement, opposed=False):
        normal = face.normalAt(0.5,0.5) #Relative to base-element
        normal.normalize()
        if opposed: normal.multiply(-1.0)
        pointOnPlane = face.Vertexes[0].Point #Relative to base-element
    
        base = App.Vector(0,0,0)
        rotation = prevPlacement.Rotation
        center = App.Vector(0,0,0)
    
        normalRotPlacement = App.Placement(base,rotation,center)
        rotatedNormal = normalRotPlacement.multVec(normal)
        rotatedNormal.normalize()
    
        absolutePointOnPlane = prevPlacement.multVec(pointOnPlane) #asolute Coordinates
        dot = absolutePointOnPlane.dot(rotatedNormal)
        copyOfNormal = App.Vector(rotatedNormal)
        closestPointVec = copyOfNormal.multiply(dot) #multiply modifies underlaying vec
    
        key = 'PLAN'+self.dirAndPosToString(rotatedNormal,closestPointVec)
        return key
    
    def generateRotationFaceKey(self,face,prevPlacement, opposed=False):
        axis = face.Surface.Axis
        axis.normalize()
        if opposed: axis.multiply(-1.0)
        pointOnAxis = face.Surface.Center
    
        base = App.Vector(0,0,0)
        rotation = prevPlacement.Rotation
        center = App.Vector(0,0,0)
    
        axisRotPlacement = App.Placement(base,rotation,center)
        rotatedAxis = axisRotPlacement.multVec(axis)
        rotatedAxis.normalize()
    
        absolutePointOnAxis = prevPlacement.multVec(pointOnAxis) #asolute Coordinates
        dot = absolutePointOnAxis.dot(rotatedAxis)
        copyOfAxis = App.Vector(rotatedAxis)
        projection = copyOfAxis.multiply(dot)
        closestPointVec = absolutePointOnAxis.sub(projection)
    
        key = 'ROTA'+self.dirAndPosToString(rotatedAxis,closestPointVec)
        return key
    
    def generateSphereFaceKey(self,face,prevPlacement):
        center = face.Surface.Center
        absoluteCenter = prevPlacement.multVec(center) #asolute Coordinates
        key = 'SPER#AT'
        x = ("#%011.2f" % absoluteCenter.x)
        y = ("#%011.2f" % absoluteCenter.y)
        z = ("#%011.2f" % absoluteCenter.z)
        key = key+x+y+z
        return key

    def isPlaneFace(self,face):
        if str(face.Surface) == '<Plane object>':
            return True
        return False
    
    def isRotationFace(self,face):
        if str( face.Surface ).startswith('Sphere'): return False
        if str(face.Surface).startswith('<SurfaceOfRevolution'): return False
        #
        if hasattr(face.Surface,'Radius'):
            return True
        return False
    
    def isSphericalFace(self,face):
        return str( face.Surface ).startswith('Sphere')

    def createBasicFaceKey(self,obj,face,prevPlacement,opposed = False):
        faceKey = ""
    
        if self.isPlaneFace(face):
            faceKey = self.generatePlaneFaceKey(face,prevPlacement, opposed)
        elif self.isRotationFace(face):
            faceKey = self.generateRotationFaceKey(face,prevPlacement, opposed)
        elif self.isSphericalFace(face):
            faceKey = self.generateSphereFaceKey(face,prevPlacement)
        else:
            faceKey = 'NONE'
        return faceKey

    def generateRotationFaceKeyFromCenteredAxis(self,axis,center):
        absolutePointOnAxis = center
        rotatedAxis = axis   

        dot = absolutePointOnAxis.dot(rotatedAxis)
        copyOfAxis = App.Vector(rotatedAxis)
        projection = copyOfAxis.multiply(dot)
        closestPointVec = absolutePointOnAxis.sub(projection)
    
        key = 'ROTA'+self.dirAndPosToString(rotatedAxis,closestPointVec)
        return key

    def generatePlaneFaceKeyFromPosNormal(self,pos,normal):
        rotatedNormal = normal
    
        absolutePointOnPlane = pos #asolute Coordinates
        dot = absolutePointOnPlane.dot(rotatedNormal)
        copyOfNormal = App.Vector(rotatedNormal)
        closestPointVec = copyOfNormal.multiply(dot) #multiply modifies underlaying vec
    
        key = 'PLAN'+self.dirAndPosToString(rotatedNormal,closestPointVec)
        return key

    def doCircleNaming(self,edge):
        center = edge.Curve.Center
        axis   = edge.Curve.Axis;
        axis.normalize()
        opposedAxis = App.Vector(axis).multiply(-1.0) #opposed copy of axis 
        #
        # Look for cylinder, which could have been generating the circle
        faceName1 = self.generateRotationFaceKeyFromCenteredAxis(axis,center)
        faceName2 = self.generateRotationFaceKeyFromCenteredAxis(opposedAxis,center)
        try:
            cylinderNameIndex = self.faceKeyList.index(faceName1)
        except:        
            try:
                cylinderNameIndex = self.faceKeyList.index(faceName2)
            except:
                cylinderNameIndex = -1
        #
        # return if no cylinder was found
        if cylinderNameIndex==-1: 
            return None
        else:
            cylinderName = self.faceNameList[cylinderNameIndex]
        #
        # Look for a plane, which could have been generating the circle
        faceName1 = self.generatePlaneFaceKeyFromPosNormal(center,axis)
        faceName2 = self.generatePlaneFaceKeyFromPosNormal(center,opposedAxis)
        try:
            planeNameIndex = self.faceKeyList.index(faceName1)
        except:        
            try:
                planeNameIndex = self.faceKeyList.index(faceName2)
            except:
                planeNameIndex = -1
        #
        # return if no plane was found
        if planeNameIndex==-1: 
            return None
        else:
            planeName = self.faceNameList[planeNameIndex]
        #
        cylNaming = "Circle#"+cylinderName+'#'+planeName
        return cylNaming



    def evalCircleEdgeNames(self,ob):
        for i, edge in enumerate(ob.Shape.Edges):
            try:
                if isinstance(edge.Curve, Part.Circle):
                    edgeName = self.doCircleNaming(edge)
                    if edgeName != None:
                        self.finalEdgeNames[i] = edgeName
            except:
                continue

    def evalFaceNamesRecursive(self,ob,prevPlacement, clonePrefix=''): #recursive func...
        prefix = ob.Name
        inversePlacement = ob.Placement.inverse()
        pl2 = inversePlacement.multiply(prevPlacement)
        #
        if len(ob.OutList) == 0:
            if appVersionStr() > "000.016":
                if str(ob) == "<GeoFeature object>": return
            
            for i,face in enumerate(ob.Shape.Faces):
                name = clonePrefix+ prefix+'#Face'+str(i+1)
                self.faceNameList.append(name)
                key = self.createBasicFaceKey(ob,face,pl2)
                self.faceKeyList.append(key)
            return
        #
        for subOb in ob.OutList:
            if subOb.Name.startswith('Spread'): continue
            if ob.Name.startswith('Sketch'):
                pl = subOb.Placement.multiply(pl2)
            else:
                pl = subOb.Placement.multiply(prevPlacement)
            if ob.Name.startswith('Clone'):
                cloneExtend = ob.Name+'#'
            else:
                cloneExtend = ''
            self.evalFaceNamesRecursive(subOb,pl,cloneExtend+clonePrefix)
        #
        # look for newly created faces and append them...
        for i,face in enumerate(ob.Shape.Faces):
            key1 = self.createBasicFaceKey(ob,face,pl2)
            key2 = self.createBasicFaceKey(ob,face,pl2,True)
            if key1 in self.faceKeyList:
                continue
            if key2 in self.faceKeyList:
                continue
            else:
                name = clonePrefix + prefix+'#Face'+str(i+1)
                self.faceNameList.append(name)
                self.faceKeyList.append(key1)

    def isLine(self,edge):
        try:
            if isinstance(edge.Curve, Part.Line):
                return True
        except:
            return False
        return False

    def isCircle(self,edge):
        try:
            if isinstance(edge.Curve, Part.Circle):
                return True
        except:
            return False
        return False

    def generateLineEdgeKey(self,edge,prevPlacement, opposed=False):
        
        if appVersionStr() <= '000.016':
            direction = edge.Curve.EndPoint.sub(edge.Curve.StartPoint) #fc0.16 works, not fc0.17
        else:
            direction = edge.lastVertex(True).Point - edge.firstVertex(True).Point
        
        direction.normalize()
        if opposed: direction.multiply(-1.0)
        
        
        if appVersionStr() <= '000.016':
            pointOnLine = edge.Curve.StartPoint #Relative to base-element
        else:
            pointOnLine = edge.firstVertex(True).Point #Relative to base-element
    
        base = App.Vector(0,0,0)
        rotation = prevPlacement.Rotation
        center = App.Vector(0,0,0)
    
        directionRotPlacement = App.Placement(base,rotation,center)
        rotatedDirection = directionRotPlacement.multVec(direction)
        rotatedDirection.normalize()
    
        absolutePointOnLine = prevPlacement.multVec(pointOnLine) #asolute Coordinates
        dot = absolutePointOnLine.dot(rotatedDirection)
        copyOfDirection = App.Vector(rotatedDirection)
        projection = copyOfDirection.multiply(dot) #multiply modifies underlaying vec
        
        closestPointVec = absolutePointOnLine - projection
    
        key = 'LINE'+self.dirAndPosToString(rotatedDirection,closestPointVec)
        return key
    
    def generateCircleEdgeKey(self,edge,prevPlacement, opposed=False):
        axis = edge.Curve.Axis
        axis.normalize()
        if opposed: axis.multiply(-1.0)
        pointOnAxis = edge.Curve.Center
    
        base = App.Vector(0,0,0)
        rotation = prevPlacement.Rotation
        center = App.Vector(0,0,0)
    
        axisRotPlacement = App.Placement(base,rotation,center)
        rotatedAxis = axisRotPlacement.multVec(axis)
        rotatedAxis.normalize()
    
        absolutePointOnAxis = prevPlacement.multVec(pointOnAxis) #asolute Coordinates
        key = 'CIRC'+self.dirAndPosToString(rotatedAxis,absolutePointOnAxis)
        return key
    
    def createBasicEdgeKey(self,obj,edge,prevPlacement, opposed=False):
        edgeKey = "NONE"
    
        if self.isLine(edge):
            edgeKey = self.generateLineEdgeKey(edge,prevPlacement, opposed)
        elif self.isCircle(edge):
            edgeKey = self.generateCircleEdgeKey(edge,prevPlacement, opposed)
            pass
        else:
            edgeKey = 'NONE'
        return edgeKey

    def evalEdgeNamesRecursive(self,ob,prevPlacement, clonePrefix=''): #recursive func...
        prefix = ob.Name
        inversePlacement = ob.Placement.inverse()
        pl2 = inversePlacement.multiply(prevPlacement)
        #
        if len(ob.OutList) == 0:
            if appVersionStr() > "000.016":
                if str(ob) == "<GeoFeature object>": return
            
            for i,edge in enumerate(ob.Shape.Edges):
                name = clonePrefix+prefix+'#Edge'+str(i+1)
                self.edgeNameList.append(name)
                key = self.createBasicEdgeKey(ob,edge,pl2)
                self.edgeKeyList.append(key)
            return
        #
        for subOb in ob.OutList:
            if subOb.Name.startswith('Spread'): continue
            if ob.Name.startswith('Sketch'):
                pl = subOb.Placement.multiply(pl2)
            else:
                pl = subOb.Placement.multiply(prevPlacement)
            if ob.Name.startswith('Clone'):
                cloneExtend = ob.Name+"#"    
            else:
                cloneExtend = ''
            self.evalEdgeNamesRecursive(subOb,pl,cloneExtend+clonePrefix)
        #
        # look for newly created edges and append them...
        for i,edge in enumerate(ob.Shape.Edges):
            key1 = self.createBasicEdgeKey(ob,edge,pl2)
            key2 = self.createBasicEdgeKey(ob,edge,pl2,True)
            if key1 in self.edgeKeyList:
                continue
            if key2 in self.edgeKeyList:
                continue
            else:
                name = clonePrefix+prefix+'#Edge'+str(i+1)
                self.edgeNameList.append(name)
                self.edgeKeyList.append(key1)


    def executeNaming(self):
        self.faceNameList = []
        self.edgeNameList = []
        self.faceKeyList = []
        self.edgeKeyList = []
        #
        self.finalFaceNames = []
        self.finalFaceKeys = []
        self.finalEdgeNames = []
        self.finalEdgeKeys = []

        self.topoInfo = []

        pl = App.Placement()        
        self.evalFaceNamesRecursive(self.rootObject,pl)
        self.evalEdgeNamesRecursive(self.rootObject,pl)
        #
        # fill basic FaceMap
        for i,face in enumerate(self.rootObject.Shape.Faces):
            key1 = self.createBasicFaceKey(self.rootObject,face,pl)
            key2 = self.createBasicFaceKey(self.rootObject,face,pl,True) #opposed=True!
            try:
                idx = self.faceKeyList.index(key1)
                faceName = self.faceNameList[idx]
            except:
                try:
                    idx = self.faceKeyList.index(key2)
                    faceName = self.faceNameList[idx]
                except:
                    faceName = "Face%d" % (i+1)
            self.finalFaceKeys.append(key1)
            self.finalFaceNames.append(faceName)
        #
        # fill basic EdgeMap
        for i,edge in enumerate(self.rootObject.Shape.Edges):
            key1 = self.createBasicEdgeKey(self.rootObject,edge,pl)
            key2 = self.createBasicEdgeKey(self.rootObject,edge,pl,True)
            try:
                idx = self.edgeKeyList.index(key1)
                edgeName = self.edgeNameList[idx]
            except:
                try:
                    idx = self.edgeKeyList.index(key2)
                    edgeName = self.edgeNameList[idx]
                except:
                    edgeName = "Edge%d" % (i+1)
            self.finalEdgeKeys.append(key1)
            self.finalEdgeNames.append(edgeName)
        #
        # refine circleEdge-names in EdgeMap
        self.evalCircleEdgeNames(self.rootObject)
        #
        for name in self.finalFaceNames:
            self.topoInfo.append('FACE#'+name)
        for name in self.finalEdgeNames:
            self.topoInfo.append('EDGE#'+name)
        #
        #self.printData()
        return self.topoInfo
    
    def printData(self):
        print "'RootObject has Name: ",self.rootObject.Name, ' and Label: ',self.rootObject.Label
        print
        print "Faces in history..."
        for i,name in enumerate(self.faceNameList):
            print 'idx=',i+1,' ',name,'     ',self.faceKeyList[i]
        print
        print "Edges in history..."
        for i,name in enumerate(self.edgeNameList):
            print 'idx=',i+1,' ',name,'     ',self.edgeKeyList[i]
        print
        print "Final Faces..."
        for i,name in enumerate(self.finalFaceNames):
            print 'idx=',i+1,' ',name,'     ',self.finalFaceKeys[i]
        print 
        print "Final Edges..."   
        for i,name in enumerate(self.finalEdgeNames):
            print 'idx=',i+1,' ',name,'     ',self.finalEdgeKeys[i]





