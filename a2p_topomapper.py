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
'''
Experimental mapper for a2p related topological naming.

Recent capabilities:
- create unique toponame for each vertex in a single document
- create unique toponame for each edge in a single document
- create unique toponame for each face in a single document (not complete ready)

Usage: 
- open fc document with a single body inside
- execute "a2p_toponamer.py" as makro ATM
- look at console output for created toponames
- compare vertex/edgenames with 'tmp' object in treeview
'''



from PySide import QtGui, QtCore
import FreeCAD, FreeCADGui, Part
from FreeCAD import Base
import a2plib
import os

class TopoMapper(object):
    def __init__(self,doc):
        self.doc = doc
        self.fileName = self.doc.FileName
        self.shapeDict = {}
        self.vertexNames = []
        self.edgeNames = []
        self.faceNames = []
        self.treeNodes = {}
        self.topLevelShapes = []
        self.doneObjects = []
        self.totalNumVertexes = 0
        self.totalNumEdges = 0
        self.totalNumFaces = 0
        
    def calcFloatKey(self,val):
            return "%014.3f;" % val
        
    def calcVertexKey(self,inOb):
        '''
        create a unique key defined by vertex-position,
        accepts also vectors as input
        '''
        try:
            coords = (
                inOb.Point.x,
                inOb.Point.y,
                inOb.Point.z
                )
        except:
            coords = (
                inOb.x,
                inOb.y,
                inOb.z,
                )
        key = ''
        for value in coords:
            keyPartial = "%014.3f;" % value
            if keyPartial == "-000000000.000;": keyPartial = "0000000000.000;"
            key += keyPartial
        return key
    
    def calcAxisKey(self,axis):
        '''
        create a unique key defined by axis-direction
        '''
        coords = (
            axis.x,
            axis.y,
            axis.z
            )
        key = ''
        for value in coords:
            keyPartial = "%012.9f;" % value
            if keyPartial == "-0.000000000;": keyPartial = "00.000000000;"
            key += keyPartial
        return key

    def calcEdgeKeys(self, edge, pl):
        keys = []
        if hasattr(edge,"Curve") and hasattr(edge.Curve,'Axis'): #circular edge #hasattr(edge,"Curve") because of spheres...
            axisStart = pl.multVec(edge.Curve.Center)
            axisEnd   = pl.multVec(edge.Curve.Center.add(edge.Curve.Axis))
            axis = axisEnd.sub(axisStart)
            keys.append(
                'CIRC;'+
                self.calcVertexKey(pl.multVec(edge.Curve.Center))+
                self.calcAxisKey(axis)+
                self.calcFloatKey(edge.Curve.Radius)
                )
        else:
            endPoint1 = pl.multVec(edge.Vertexes[0].Point)
            endPoint2 = pl.multVec(edge.Vertexes[-1].Point)
            direction1 = endPoint2.sub(endPoint1)
            direction2 = endPoint1.sub(endPoint2)
            try:
                direction1.normalize()
                direction2.normalize()
            except:
                pass
            keys.append(
                self.calcVertexKey(endPoint1)+
                self.calcAxisKey(direction1)
                )
            keys.append(
                self.calcVertexKey(endPoint2)+
                self.calcAxisKey(direction2)
                )
        return keys
    
    def calcFaceKeys(self, face, pl):
        keys = []
        # A sphere...
        if str( face.Surface ).startswith('Sphere'):
            keys.append(
                'SPH;'+
                self.calcVertexKey(pl.multVec(face.Surface.Center))+
                self.calcFloatKey(face.Surface.Radius)
                )
        # a cylindric face...
        elif all( hasattr(face.Surface,a) for a in ['Axis','Center','Radius'] ):
            axisStart = pl.multVec(face.Surface.Center)
            axisEnd   = pl.multVec(face.Surface.Center.add(face.Surface.Axis))
            axisKey = self.calcAxisKey(axisEnd.sub(axisStart))
            radiusKey = self.calcFloatKey(face.Surface.Radius)
            for v in face.Vertexes:
                keys.append(
                    'CYL;'+
                    self.calcVertexKey(pl.multVec(v.Point))+
                    axisKey+
                    radiusKey
                    )
        elif str( face.Surface ) == '<Plane object>':
            pt = face.Vertexes[0].Point
            uv=face.Surface.parameter(pt)
            u=uv[0]
            v=uv[1]
            normal=face.normalAt(u,v)
            normalStart = pl.multVec(pt)
            normalEnd = pl.multVec(pt.add(normal))
            normal = normalEnd.sub(normalStart)
            normalKey = self.calcAxisKey(normal)
            for vert in face.Vertexes:
                keys.append(
                    'PLANE;'+
                    self.calcVertexKey(pl.multVec(vert.Point))+
                    normalKey
                    )
        else:
            keys.append("NOTRACE")
        return keys #FIXME
    
    
    def filterShapeObs(self,_list):
        lst = []
        for ob in _list:
            if hasattr(ob,"Shape"):
                if len(ob.Shape.Faces) > 0:
                    lst.append(ob)
        S = set(lst)
        lst = []
        lst.extend(S)
        return lst

    def populateShapeDict(self,objName):
        self.doneObjects.append(objName)
        ob = self.doc.getObject(objName)
        shape = ob.Shape
        pl = ob.getGlobalPlacement().multiply(ob.Placement.inverse())
        #
        # Populate vertex entries...
        vertexes = shape.Vertexes
        numNewlyCreatedVertexes = len(shape.Vertexes) - self.totalNumVertexes
        self.totalNumVertexes = len(shape.Vertexes)
        vertexNamePrefix = 'V;'+objName + ';'
        vertexNameSuffix = str(numNewlyCreatedVertexes)
        i = 1 # do not enumerate the following, count new vertexes !
        for vertex in vertexes:
            vertexKey = self.calcVertexKey(pl.multVec(vertex.Point))
            vertexName = vertexNamePrefix + str(i) + ';' + vertexNameSuffix
            vertexFound = self.shapeDict.get(vertexKey,False)
            if vertexFound == False:
                self.shapeDict[vertexKey] = vertexName
                i+=1 # new vertex counting per feature
        #
        # populate edge entries...
        edges = shape.Edges
        numNewlyCreatedEdges = len(edges) - self.totalNumEdges
        self.totalNumEdges = len(edges)
        edgeNamePrefix = 'E;' + objName + ';'
        edgeNameSuffix = str(numNewlyCreatedEdges)
        i = 1 # do not enumerate the following, count new Edges !
        for edge in edges:
            edgeKeys = self.calcEdgeKeys(edge, pl) # 2 keys for a linear edge, 1 key per circular egde
            entryFound=False
            for k in edgeKeys:
                tmp = self.shapeDict.get(k,False)
                if tmp != False:
                    entryFound = True
                    break
            if not entryFound:
                edgeName = edgeNamePrefix + str(i) + ';' + edgeNameSuffix
                i+=1
            else:
                edgeName = tmp # the old edge name...
            for k in edgeKeys:
                self.shapeDict[k] = edgeName
        #
        # populate face entries...
        faces = shape.Faces
        self.totalNumFaces = 0
        numNewlyCreatedFaces = len(faces) - self.totalNumFaces
        self.totalNumFaces = len(faces)
        faceNamePrefix = 'F;' + objName + ';'
        faceNameSuffix = str(numNewlyCreatedFaces)
        i = 1 # do not enumerate the following, count new Faces !
        for face in faces:
            faceKeys = self.calcFaceKeys(face, pl) # one key per vertex of a face
            entryFound=False
            # if one key matches, it is the old face name
            for k in faceKeys:
                tmp = self.shapeDict.get(k,False)
                if tmp != False:
                    entryFound = True
                    break
            if not entryFound:
                faceName = faceNamePrefix + str(i) + ';' + faceNameSuffix
                i+=1
            else:
                faceName = tmp # the old face name...
            for k in faceKeys:
                self.shapeDict[k] = faceName
        
    def processTopoData(self,objName,level=0):
        level+=1
        inList, outList = self.treeNodes[objName]
        for ob in outList:
            self.processTopoData(ob.Name,level)
        if (
            not objName.startswith("Body") and
            objName not in self.doneObjects
            ):
            self.populateShapeDict(objName)
        
    def makePlacedShape(self,obj):
        '''return a copy of obj.Shape with proper placement applied'''
        tempShape = obj.Shape.copy()
        plmGlobal = obj.Placement
        try:
            plmGlobal = obj.getGlobalPlacement();
        except:
            pass
        tempShape.Placement = plmGlobal
        return tempShape
    
    def createTopoNames(self,withColor=False):
        #-------------------------------------------
        # Create treenodes of the importable Objects with a shape
        #-------------------------------------------
        self.treeNodes = {}
        shapeObs = self.filterShapeObs(self.doc.Objects)
        S = set(shapeObs)
        for ob in S:
            self.treeNodes[ob.Name] = (
                    self.filterShapeObs(ob.InList),
                    self.filterShapeObs(ob.OutList)
                    )
        #-------------------------------------------
        # Top level shapes have nodes with empty inList
        #-------------------------------------------
        self.topLevelShapes = []
        for objName in self.treeNodes.keys():
            inList,outList = self.treeNodes[objName]
            if len(inList) == 0:
                self.topLevelShapes.append(objName)
                #
                # Reset the counts for each toplevel shape
                self.totalNumVertexes = 0
                self.totalNumEdges = 0
                self.totalNumFaces = 0
                #
                self.processTopoData(objName) # analyse each toplevel object...
        #
        #-------------------------------------------
        # MUX the toplevel shapes
        #-------------------------------------------
        faces = []
        faceColors = []
        
        for objName in self.topLevelShapes:

            ob = self.doc.getObject(objName)

            colorFlag = ( len(ob.ViewObject.DiffuseColor) < len(ob.Shape.Faces) )
            shapeCol = ob.ViewObject.ShapeColor
            diffuseCol = ob.ViewObject.DiffuseColor
            tempShape = self.makePlacedShape(ob)

            # now start the loop with use of the stored values..(much faster)
            for i, face in enumerate(tempShape.Faces):
                faces.append(face)
                a2plib.DebugMsg(a2plib.A2P_DEBUG_3,"a2p MUX: i(Faces)={}\n{}\n".format(i,face))
    
                if withColor:
                    if colorFlag:
                        faceColors.append(shapeCol)
                    else:
                        faceColors.append(diffuseCol[i])

        shell = Part.makeShell(faces)
        #
        muxInfo = []
        #-------------------------------------------
        # map vertexnames to the MUX
        #-------------------------------------------
        muxInfo.append("[VERTEXES]")
        for i,v in enumerate(shell.Vertexes):
            k = self.calcVertexKey(v)
            name = self.shapeDict.get(k,"None")
            muxInfo.append(name)
            '''
            print(
                "{} {}   {}".format(
                    i+1,
                    name,
                    k
                    )
                )
            '''
        #-------------------------------------------
        # map edgenames to the MUX
        #-------------------------------------------
        muxInfo.append("[EDGES]")
        pl = FreeCAD.Placement()
        for i,edge in enumerate(shell.Edges):
            keys = self.calcEdgeKeys(edge, pl)
            name = self.shapeDict.get(keys[0],"None")
            muxInfo.append(name)
            '''
            print(
                "{} {}   {}".format(
                    i+1,
                    name,
                    keys[0]
                    )
                  )
            '''
        #-------------------------------------------
        # map facenames to the MUX
        #-------------------------------------------
        muxInfo.append("[FACES]")
        pl = FreeCAD.Placement()
        for i,face in enumerate(shell.Faces):
            keys = self.calcFaceKeys(face, pl)
            name = self.shapeDict.get(keys[0],"None")
            muxInfo.append(name)

        if withColor:
            return muxInfo, shell, faceColors
        else:
            return muxInfo, shell
        

if __name__ == "__main__":
    doc = FreeCAD.activeDocument()
    tm = TopoMapper(doc)
    tm.createTopoNames()












































