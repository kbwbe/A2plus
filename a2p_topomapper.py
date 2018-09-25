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
- create unique toponame for each vertex in a single body
- create unique toponame for each edge in a single body

Work in progress:
- create unique toponame for each face in a single body

Issues: globalPlacement ignored ATM

Usage: 
- open fc document with a single body inside
- execute "a2p_toponamer.py" as makro ATM
- look at console output for created toponames
'''




import FreeCAD, FreeCADGui, Part
from FreeCAD import Base
import a2plib

def filterShapeObs(_list):
    lst = []
    for ob in _list:
        if hasattr(ob,"Shape"):
            if len(ob.Shape.Faces) > 0:
                lst.append(ob)
    S = set(lst)
    lst = []
    lst.extend(S)
    return lst


class BodyTopoMapper(object):
    
    def __init__(self,bodyObject):
        self.body = bodyObject
        self.shapeSequence = []
        self.vertexNameDict = {}
        self.vertexNames = []
        self.edgeNameDict = {}
        self.edgeNames = []
        self.faceNameDict = {}
        self.faceNames = []
        #
        self.calcShapeSequence()
        self.setupVertexDict()
        self.setupVertexNames()
        self.setupEdgeDict()
        self.setupEdgeNames()
        self.setupFaceDict()
        
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
            key += keyPartial
        return key
    
    def setupEdgeNames(self):
        self.edgeNames = []
        if len(self.shapeSequence) == 0: return
        feature = self.shapeSequence[-1]
        print ("=== index/edgeName Map of last feature ===")
        for i,edge in enumerate(feature.Shape.Edges):
            edgeKeys = self.calcEdgeKeys(edge)
            for edgeKey in edgeKeys:
                edgeName = self.edgeNameDict.get(edgeKey,None)
                if edgeName != None:
                    self.edgeNames.append(edgeName)
                    print(str(i+1)+' '+edgeName)
                    break
            
    def setupVertexNames(self):
        self.vertexNames = []
        if len(self.shapeSequence) == 0: return
        feature = self.shapeSequence[-1]
        print ("=== index/VertexName Map of last feature ===")
        for i,vertex in enumerate(feature.Shape.Vertexes):
            vertexKey = self.calcVertexKey(vertex)
            vertexName = self.vertexNameDict[vertexKey]
            self.vertexNames.append(vertexName)
            print(str(i+1)+' '+vertexName)
            
    def calcEdgeKeys(self,edge):
        keys = []

        if hasattr(edge.Curve,'Axis'): #circular edge
            keys.append(
                'CIRC;'+
                self.calcVertexKey(edge.Curve.Center)+
                self.calcAxisKey(edge.Curve.Axis)+
                self.calcFloatKey(edge.Curve.Radius)
                )
        else:
            endPoint1 = edge.Vertexes[0]
            endPoint2 = edge.Vertexes[-1]
            direction1 = endPoint2.Point.sub(endPoint1.Point)
            direction2 = endPoint1.Point.sub(endPoint2.Point)
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

    def calcFaceKeys(self,face):
        keys = []
        # A sphere...
        if str( face.Surface ).startswith('Sphere'):
            keys.append(
                'SPH;'+
                self.calcVertexKey(face.Surface.Center)+
                self.calcFloatKey(face.Surface.Radius)
                )
        # a cylindric face...
        elif all( hasattr(face.Surface,a) for a in ['Axis','Center','Radius'] ):
            axisKey = self.calcAxisKey(face.Surface.Axis)
            radiusKey = self.calcFloatKey(face.Surface.Radius)
            for v in face.Vertexes:
                keys.append(
                    'CYL;'+
                    self.calcVertexKey(v)+
                    axisKey+
                    radiusKey
                    )
        elif str( face.Surface ) == '<Plane object>':
            pt = face.Vertexes[0].Point
            uv=face.Surface.parameter(pt)
            u=uv[0]
            v=uv[1]
            normal=face.normalAt(u,v)
            normalKey = self.calcAxisKey(normal)
            for v in face.Vertexes:
                keys.append(
                    'PLANE;'+
                    self.calcVertexKey(v)+
                    normalKey
                    )
        else:
            keys.append("NOTRACE")

        return keys #FIXME

    def setupEdgeDict(self):
        totalNumEdges = 0
        for feature in self.shapeSequence:
            numNewlyCreatedEdges = len(feature.Shape.Edges) - totalNumEdges
            totalNumEdges = len(feature.Shape.Edges)
            edgeNamePrefix = self.body.Name + ';' + feature.Name + ';'
            edgeNameSuffix = str(numNewlyCreatedEdges)
            i = 0 # do not enumerate the following, count new Edges !
            for edge in feature.Shape.Edges:
                edgeKeys = self.calcEdgeKeys(edge) # usually more than one key per edge
                entryFound=False
                # if one key matches, it is the old edge name
                for k in edgeKeys:
                    tmp = self.edgeNameDict.get(k,False)
                    if tmp != False:
                        entryFound = True
                        break
                if not entryFound:
                    edgeName = edgeNamePrefix + str(i) + ';' + edgeNameSuffix
                    i+=1
                else:
                    edgeName = tmp # the old edge name...
                for k in edgeKeys:
                    self.edgeNameDict[k] = edgeName
                
    def setupFaceDict(self):
        totalNumFaces = 0
        for feature in self.shapeSequence:
            numNewlyCreatedFaces = len(feature.Shape.Faces) - totalNumFaces
            totalNumFaces = len(feature.Shape.Faces)
            faceNamePrefix = self.body.Name + ';' + feature.Name + ';'
            faceNameSuffix = str(numNewlyCreatedFaces)
            i = 0 # do not enumerate the following, count new Faces !
            for face in feature.Shape.Faces:
                faceKeys = self.calcFaceKeys(face) # usually more than one key per face
                entryFound=False
                # if one key matches, it is the old face name
                for k in faceKeys:
                    tmp = self.faceNameDict.get(k,False)
                    if tmp != False:
                        entryFound = True
                        break
                if not entryFound:
                    faceName = faceNamePrefix + str(i) + ';' + faceNameSuffix
                    i+=1
                else:
                    faceName = tmp # the old face name...
                for k in faceKeys:
                    self.faceNameDict[k] = faceName
                

    def setupVertexDict(self):
        totalNumVertexes = 0
        for feature in self.shapeSequence:
            numNewlyCreatedVertexes = len(feature.Shape.Vertexes) - totalNumVertexes
            totalNumVertexes = len(feature.Shape.Vertexes)
            vertexNamePrefix = self.body.Name + ';' + feature.Name + ';'
            vertexNameSuffix = str(numNewlyCreatedVertexes)
            i = 0 # do not enumerate the following, count new vertexes !
            for vertex in feature.Shape.Vertexes:
                vertexKey = self.calcVertexKey(vertex)
                vertexName = vertexNamePrefix + str(i) + ';' + vertexNameSuffix
                vertexFound = self.vertexNameDict.get(vertexKey,False)
                if vertexFound == False:
                    self.vertexNameDict[vertexKey] = vertexName
                    i+=1 # new vertex counting per feature

    def calcShapeSequence(self):
        self.shapeSequence = []
        S = set(self.body.OutList)
        shapedObs = []
        for ob in S:
            dependsOn = None
            if hasattr(ob,"Shape"):
                if len(ob.Shape.Faces) > 0:
                    tmp = filterShapeObs(ob.OutList)
                    if len(tmp)>0:
                        dependsOn = tmp[0]
                    shapedObs.append((ob,dependsOn))
        #start with baseFeature
        recentFeature = None
        foundNew = False
        for ob,dependsOn in shapedObs:
            if not dependsOn: # dependsOn == None...
                recentFeature = ob
                foundNew = True
                break
        while foundNew:
            self.shapeSequence.append(recentFeature)
            foundNew = False
            for ob,dependsOn in shapedObs:
                if recentFeature == dependsOn:
                    recentFeature = ob
                    foundNew = True
                    break
        print("")
        print("=== Feature creation history ===")
        for s in self.shapeSequence:
            print (s.Name)
        print("")


if __name__ == "__main__":
    print ("a2p_topomapper v0.0.0")
    print ("")
    doc = FreeCAD.activeDocument()
    obs = doc.Objects
    for ob in obs:
        if "Body" in ob.Name:
            topoMap = BodyTopoMapper(ob)











































