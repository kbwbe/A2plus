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

It is used during first level import of fcstd documents to a2p

Working principle:
- History of toplevel shapes within the fcstd doc is analyzed starting from
  the very first basefeature (found recursively from toplevel shapes)

- The algorithm analyses the vertexes/edges/faces of each shape in history
- Each topo element is described by geometrical values (position,axis,etc)
- A dictionary is build, the geometrical values are used as keys and the
  values are the names of the topo-elements.
- during processing of a new shape/feature, it's keys are calculated and looked
  up in the dictionary. If a key already exists, the algo assumes, that the
  geometry belongs to a former analysed shape. If the key does not exist,
  a new key/name pair is added to the dictionary.
- When all shapes are processed, there exists a dict with (multiple) entries
  of all geometry.
- Some geometry causes multiple keys. So for plane faces there are stored
  two keys per vertex. One with positive axis value, one with neg.axis value.
  This is necessary because normals can flip during build history.

Key-generation:
    keys for vertexes: "xvalue;yvalue;zvalue"

    keys for edges: (different ones for different edge types)
        straight lines
            2 keys are uses, each consists of:
                - vertexkey of the endpoint
                - an axiskey pointing to the other endpoint
        circles:
            two keys are used for each vertex on the curve
                - key consisting of center-vertex and positive axis data + radius
                - key consisting of center-vertex and negative axis data + radius
                - both marked with "CIRC" at the beginning

        other edge types are put to dict with dummy entries.

    keys for faces:
        Plane faces are described by vertex/normal for each vertex.
        Additionally a second entry by vertex/neg.normal for each vertex.

        Spheres are described by center-vertex + radius

        Cylindrical faces are described by vertex/pos.axis+radius and second one
        with neg.axis per vertex.

Newer shapes in history can delete geo elements of previous ones. If the algorithm
finds one relicting key of an old shape in the dict, it assumes that the geo element
belongs to the old shape. Newly created geo elements, which belong together, then get
the old name, otherwise a new name is defined and put to the dict.

Example:
A new feature cuts away an endpoint of a line, but one still exists:
the newly linesegment belongs logically to the old existing one. The new vertex gets the existing name.
So if a constraint was linked to the old linesegment, we can map it to the new linesegment and the
assembly keeps consistent.

After building the dict, the compound shape of total doc is analysed. Keys of this are build
and looked up in the dict to get the names.

A List of names (same indexes as vertexes[n],edges[],faces[] is generated for output.

All this helps A2plus to identify the correct subelements for constraints, if imported
parts are been edited.
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
        self.isPartDesignDocument = False

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
        # workaround for hasattr(edge,"Curve"), which does not work with spheres on conda builds
        curveAttributeExists = False
        try:
            if hasattr(edge,"Curve"): # throws exception on Conda build (spheres),
                curveAttributeExists = True
        except:
            pass
        #circular edge #hasattr(edge,"Curve") because of spheres...
        if (
            curveAttributeExists and
            hasattr(edge.Curve,'Axis') and
            hasattr(edge.Curve,'Radius')
            ):
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
            axis = axisEnd.sub(axisStart)
            axisKey = self.calcAxisKey(axis)
            negativeAxis = Base.Vector(axis)
            negativeAxis.multiply(-1.0)
            negativeAxisKey = self.calcAxisKey(negativeAxis)
            radiusKey = self.calcFloatKey(face.Surface.Radius)
            #
            for v in face.Vertexes:
                vertexKey = self.calcVertexKey(pl.multVec(v.Point))
                keys.append(
                    'CYL;'+
                    vertexKey+
                    axisKey+
                    radiusKey
                    )
                keys.append(
                    'CYL;'+
                    vertexKey+
                    negativeAxisKey+
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
            negativeNormal = Base.Vector(normal)
            negativeNormal.multiply(-1.0)
            normalKey = self.calcAxisKey(normal)
            negativeNormalKey = self.calcAxisKey(negativeNormal)
            for vert in face.Vertexes:
                vertexKey = self.calcVertexKey(pl.multVec(vert.Point))
                keys.append(
                    'PLANE;'+
                    vertexKey+
                    normalKey
                    )
                keys.append(
                    'PLANE;'+
                    vertexKey+
                    negativeNormalKey
                    )
        else:
            keys.append("NOTRACE")
        return keys #FIXME


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
        vertexNameSuffix = str(numNewlyCreatedVertexes)+';' #only correct for PartDesign, PartWB gives false counts
        i = 1 # do not enumerate the following, count new vertexes !
        for vertex in vertexes:
            vertexKey = self.calcVertexKey(pl.multVec(vertex.Point))
            if self.isPartDesignDocument:
                vertexName = vertexNamePrefix + str(i) + ';' + vertexNameSuffix
            else:
                vertexName = vertexNamePrefix + str(i) + ';'
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
        edgeNameSuffix = str(numNewlyCreatedEdges)+';' #only correct for PartDesign, PartWB gives false counts
        i = 1 # do not enumerate the following, count new Edges !
        for edge in edges:
            edgeKeys = self.calcEdgeKeys(edge, pl) # 2 keys for a linear edge, 1 key per circular edge
            entryFound=False
            for k in edgeKeys:
                tmp = self.shapeDict.get(k,False)
                if tmp != False:
                    entryFound = True
                    break
            if not entryFound:
                if self.isPartDesignDocument:
                    edgeName = edgeNamePrefix + str(i) + ';' + edgeNameSuffix
                else:
                    edgeName = edgeNamePrefix + str(i) + ';'
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
        faceNameSuffix = str(numNewlyCreatedFaces)+';' #only correct for PartDesign, PartWB gives false counts
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
                if self.isPartDesignDocument:
                    faceName = faceNamePrefix + str(i) + ';' + faceNameSuffix
                else:
                    faceName = faceNamePrefix + str(i) + ';'
                i+=1
            else:
                faceName = tmp # the old face name...
            for k in faceKeys:
                self.shapeDict[k] = faceName

    def processTopoData(self,objName,level=0):
        '''
        Recursive function which populates the
        shapeDict with geometricKey/toponame entries
        '''
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
        '''
        return a copy of obj.Shape with proper placement applied
        '''
        tempShape = obj.Shape.copy()
        plmGlobal = obj.Placement
        try:
            plmGlobal = obj.getGlobalPlacement();
        except:
            pass
        tempShape.Placement = plmGlobal
        return tempShape

    def addedByPathWB(self,obName):
        '''
        function detects, whether special object belongs to
        a milling job of Path WB
        
        It is looking for "Stock" and contents of Model-group
        '''
        ob = self.doc.getObject(obName)
        if ob.Name.startswith('Stock'):
            for o in ob.InList:
                if o.Name.startswith('Job'):
                    return True
        for o in ob.InList:
            if o.Name.startswith('Model'):
                for o1 in o.InList:
                    if o1.Name.startswith('Job'):
                        return True
        return False

    def getTopLevelObjects(self):
        #-------------------------------------------
        # Create treenodes of the importable Objects with a shape
        #-------------------------------------------
        self.treeNodes = {}
        shapeObs = a2plib.filterShapeObs(self.doc.Objects)
        S = set(shapeObs)
        for ob in S:
            self.treeNodes[ob.Name] = (
                    a2plib.filterShapeObs(ob.InList),
                    a2plib.filterShapeObs(ob.OutList)
                    )
        #-------------------------------------------
        # nodes with empty inList are top level shapes for sure
        # (cloned objects could be missing)
        #-------------------------------------------
        self.topLevelShapes = []
        for objName in self.treeNodes.keys():
            inList,dummy = self.treeNodes[objName]
            if len(inList) == 0:
                self.topLevelShapes.append(objName)
            else:
                #-------------------------------------------
                # search for missing non top-level clone-basefeatures
                # Maybe a clone as basefeature of a body..
                #-------------------------------------------
                numBodies = 0
                numClones = 0
                invalidObjects = False
                if len(inList) % 2 == 0: # pairs of Clone/Bodies
                    for o in inList:
                        if o.Name.startswith('Clone'):
                            numClones += 1
                        elif o.Name.startswith('Body'):
                            numBodies += 1
                        else:
                            invalidObjects = True
                            break
                    if not invalidObjects:
                        if numBodies == numClones:
                            self.topLevelShapes.append(objName)
        
        #-------------------------------------------
        # search for missing clone-basefeatures
        #-------------------------------------------
        addList = []
        for n in self.topLevelShapes:
            if (
                n.startswith('Clone') or
                n.startswith('Part__Mirroring')
                ):
                dummy,outList = self.treeNodes[n]
                if len(outList) == 1:
                    addList.append(outList[0].Name)
        if len(addList) > 0:
            self.topLevelShapes.extend(addList)
        #-------------------------------------------
        # Got some shapes created by PathWB? filter out...
        # also filter out invisible shapes...
        #-------------------------------------------
        tmp = []
        for n in self.topLevelShapes:
            if self.addedByPathWB(n): continue
            #
            if a2plib.doNotImportInvisibleShapes():
                ob = self.doc.getObject(n)
                if hasattr(ob,"ViewObject"):
                    if hasattr(ob.ViewObject,"Visibility"):
                        if ob.ViewObject.Visibility == False:
                            print(
                                "Import ignored invisible shape! {}".format(
                                    ob.Name
                                    )
                                  )
                            continue
            tmp.append(n)
        self.topLevelShapes = tmp
        #-------------------------------------------
        # return complete topLevel document objects for external use
        #-------------------------------------------
        outObs = []
        for objName in self.topLevelShapes:
            outObs.append(self.doc.getObject(objName))
        return outObs

    def detectPartDesignDocument(self):
        self.isPartDesignDocument = False
        for ob in self.doc.Objects:
            if ob.Name.startswith('Body'):
                self.isPartDesignDocument = True
                break

    def createTopoNames(self, desiredShapeLabel = None):
        '''
        creates a combined shell of all toplevel objects and
        assigns toponames to its geometry if toponaming is
        enabled.
        '''
        self.detectPartDesignDocument()
        self.getTopLevelObjects()
        
        # filter topLevelShapes if there is a desiredShapeLabel 
        # means: extract only one desired shape out of whole file...
        if desiredShapeLabel: #is not None
            tmp = []
            for objName in self.topLevelShapes:
                o = self.doc.getObject(objName)
                if o.Label == desiredShapeLabel:
                    tmp.append(o.Name)
            self.topLevelShapes = tmp
        
        #-------------------------------------------
        # analyse the toplevel shapes
        #-------------------------------------------
        if a2plib.getUseTopoNaming():
            for n in self.topLevelShapes:
                self.totalNumVertexes = 0
                self.totalNumEdges = 0
                self.totalNumFaces = 0
                self.processTopoData(n) # analyse each toplevel object...
        #
        #-------------------------------------------
        # MUX the toplevel shapes
        #-------------------------------------------
        faces = []
        faceColors = []
        transparency = 0
        shape_list = []
        
        for objName in self.topLevelShapes:
            ob = self.doc.getObject(objName)
            needDiffuseExtension = ( len(ob.ViewObject.DiffuseColor) < len(ob.Shape.Faces) )
            shapeCol = ob.ViewObject.ShapeColor
            diffuseCol = ob.ViewObject.DiffuseColor
            tempShape = self.makePlacedShape(ob)
            transparency = ob.ViewObject.Transparency
            shape_list.append(ob.Shape)
            
            if needDiffuseExtension:
                diffuseElement = a2plib.makeDiffuseElement(shapeCol,transparency)
                for i in range(0,len(tempShape.Faces)):
                    faceColors.append(diffuseElement)
            else:
                faceColors.extend(diffuseCol) #let python libs extend faceColors, much faster
            faces.extend(tempShape.Faces) #let python libs extend faces, much faster

        shell = Part.makeShell(faces)
        try:
            if a2plib.getUseSolidUnion():
                if len(shape_list) > 1:
                    shape_base=shape_list[0]
                    shapes=shape_list[1:]
                    solid = shape_base.fuse(shapes)
                    #solid = ob.Shape
                else:   #one shape only
                    solid = shape_list[0]
            else:
                solid = Part.Solid(shell)
        except:
            # keeping a shell if solid is failing
            solid = shell
        #-------------------------------------------
        # if toponaming is used, assign toponames to
        # shells geometry
        #-------------------------------------------
        muxInfo = []
        if a2plib.getUseTopoNaming():
            #-------------------------------------------
            # map vertexnames to the MUX
            #-------------------------------------------
            muxInfo.append("[VERTEXES]")
            for i,v in enumerate(solid.Vertexes):
                k = self.calcVertexKey(v)
                name = self.shapeDict.get(k,"None")
                muxInfo.append(name)
            #-------------------------------------------
            # map edgenames to the MUX
            #-------------------------------------------
            muxInfo.append("[EDGES]")
            pl = FreeCAD.Placement()
            for i,edge in enumerate(solid.Edges):
                keys = self.calcEdgeKeys(edge, pl)
                name = self.shapeDict.get(keys[0],"None")
                muxInfo.append(name)
            #-------------------------------------------
            # map facenames to the MUX
            #-------------------------------------------
            muxInfo.append("[FACES]")
            pl = FreeCAD.Placement()
            for i,face in enumerate(solid.Faces):
                keys = self.calcFaceKeys(face, pl)
                name = self.shapeDict.get(keys[0],"None")
                muxInfo.append(name)


        return muxInfo, solid, faceColors, transparency
    