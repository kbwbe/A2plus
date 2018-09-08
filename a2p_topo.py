#***************************************************************************
#*                                                                         *
#*   Copyright (c) 2018 WandererFan <wandererfan@gmail.com>                *
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

import FreeCADGui,FreeCAD
import Part

from PySide import QtGui, QtCore
import os, sys, copy, time, re
from sets import Set

import a2plib
import a2p_importpart as imPart
from a2p_versionmanagement import SubAssemblyWalk, A2P_VERSION
from a2plib import (
    appVersionStr,
    AUTOSOLVE_ENABLED,
    PYVERSION
    )

#<topo>
def getParents(obj):
    '''string = find container trail from obj to root, or return immediate
    parent if one exists'''
    parents = list()
    for x in obj.InList:
        if x.hasExtension("App::GroupExtension"):
            parents.append(x.Name)
            parents.extend(getParents(x))
            break                    #can only belong to 1 group
    if not parents:
        for x in obj.InList:
            if x.isDerivedFrom("Part::Feature"):
                parents.append(x.Name)   # take the first one? seems weak
                break
    return parents

def getTopoPrefix(obj):
    ''' return (importable) obj's topoPrefix ("parent1,parent2,...") as string'''
    parents = getParents(obj)
    prefix = str()
    if parents:
        for p in reversed(parents): 
            prefix += (p + ",")
    else:
        prefix = "None,"
    return prefix

def createTopoInfo(obj):
    '''format a muxInfo string for obj'''
    prefix = getTopoPrefix(obj)
    muxString = prefix + obj.Name + "," + str(len(obj.Shape.Faces)) + \
                                    "," + str(len(obj.Shape.Edges)) + \
                                    "," + str(len(obj.Shape.Vertexes))
    return muxString

def unmapA2pFace(A2pObj, faceIdx):
    '''find the original FC object and subObject corresponding to a face
    in an A2pObj.  returns (FCobjName,subObjectName)'''
#    print "unmapA2pFace(",A2pObj.Name,", ",str(faceIdx)
    muxedPairs  = list()
    faceSum   = -1
    faceFloor = 0
    foundObj  = None
    foundNum  = -5
    if not A2pObj.muxInfo:
       print("Problem: " + A2pObj.Name +" has no muxInfo!")
       #throw an error? return (None,-1)??
    else: 
        for m in A2pObj.muxInfo:
            #muxInfo isn't pairs anymore!!! (prefix,prefix,...,objName,faceCount,edgeCount,vertexCount)!!
            #was (objName,faceCount)
            #(objName,faceNum) = unpackMuxInfo(obj)
            pieces = m.split(",")
            fcObjName = pieces[-4]
            fcFaceCount = int(pieces[-3])
            muxedPairs.append((fcObjName, fcFaceCount))
#            print "muxedPair: ", fcObjName, " / ", str(fcFaceCount)
        # this can be combined into 1 loop if it is slow.
        for p in muxedPairs:
            faceSum += p[1]
#            print "floor: ", faceFloor, " sum: ", faceSum
            if (faceIdx) <= faceSum:
                foundObj = p[0]
                foundNum = faceIdx - faceFloor    #index, not name
                break
            faceFloor = faceSum + 1
    print("unmapA2pFace returns: " + foundObj + str(foundNum))
    return (foundObj,foundNum)

def buildTopoMap(FCdoc, visible = True):
    '''builds summary of importable objects in FC doc'''
    importableObjects = list()
    importableObjects.extend(imPart.getImpPartsFromDoc(FCdoc,visible))

    if importableObjects == None or len(importableObjects) == 0:
        msg = "No importable Parts. Aborting operation"
        QtGui.QMessageBox.information(
            QtGui.QApplication.activeWindow(),
            "Import Error",
            msg
            )
        return

    topoMap = list()
    for obj in importableObjects:
        topoMap.append(createTopoInfo(obj))
    print("buildTopoMap - TopoMap for " + FCdoc.Name + ". " + str(len(topoMap)) + " entries.")
    print(topoMap)
    return topoMap

def extractMuxInfo(A2pDoc):
    '''return list of MuxInfo (topoReferences) in A2pDoc'''
    muxInfo = list()
    for obj in A2pDoc.Objects:
        if a2plib.isA2pPart(obj):
            if hasattr(obj,"muxInfo"):
                objMux = obj.muxInfo
                muxInfo.extend(objMux)
    print("extractMuxInfo - muxInfo for " + A2pDoc.Name + ". " + str(len(muxInfo)) + " entries.")
    print(muxInfo)
    return muxInfo

######################################################################################

#disposable test for topoForCurrentDoc routine. 
class a2p_topoForCurrentDocCommand():
    def GetResources(self):
        return {'Pixmap'  : ':/icons/a2p_topoCurrent.svg',
#                'Accel' : "Shift+A", # a default shortcut (optional)
                'MenuText': "get the topo info for current A2p document",
                'ToolTip' : "get the topo info for current A2p document"
                }

    def Activated(self):
#        print("a2p_topoForCurrentDocCommand.Activated()")
        if FreeCAD.ActiveDocument == None:
            msg = \
'''
This function only works on an active document.
'''
            QtGui.QMessageBox.information(
                QtGui.QApplication.activeWindow(),
                "No Document",
                msg
                )
            return

        doc = FreeCAD.activeDocument()
        topoInfo = extractMuxInfo(doc)
        #do something with topoInfo
        return
        
    def IsActive(self):
        """Here you can define if the command must be active or not (greyed) if certain conditions
        are met or not. This function is optional."""
        return True

FreeCADGui.addCommand('a2p_topoForCurrentDoc',a2p_topoForCurrentDocCommand())

#disposable test for topoForFile routine
class a2p_topoForFileCommand():
    def GetResources(self):
        return {'Pixmap'  : ':/icons/a2p_topoFile.svg',
#                'Accel' : "Shift+A", # a default shortcut (optional)
                'MenuText': "get the topo info for an fcstd file",
                'ToolTip' : "get the topo info for an fcstd file"
                }

    def Activated(self):
#        print("a2p_topoForFileCommand.Activated")
        dialog = QtGui.QFileDialog(
            QtGui.QApplication.activeWindow(),
            "Select FreeCAD document to process"
            )
        dialog.setNameFilter("Supported Formats (*.FCStd);;All files (*.*)")
        if dialog.exec_():
            if PYVERSION < 3:
                filename = unicode(dialog.selectedFiles()[0])
            else:
                filename = str(dialog.selectedFiles()[0])
        else:
            return

        importDoc = FreeCAD.openDocument(filename)
        topoInfo = buildTopoMap(importDoc)
        #do something with topoInfo
        return
            

    def IsActive(self):
        """Here you can define if the command must be active or not (greyed) if certain conditions
        are met or not. This function is optional."""
        return True

FreeCADGui.addCommand('a2p_topoForFile',a2p_topoForFileCommand())


#disposable test for unmap routine
class a2p_topoUnmapFaceCommand():
    def GetResources(self):
        return {'Pixmap'  : ':/icons/a2p_topoUnmap.svg',
#                'Accel' : "Shift+A", # a default shortcut (optional)
                'MenuText': "find original reference for A2p Face",
                'ToolTip' : "find original reference for A2p Face"
                }

    def Activated(self):
#        print("a2p_topoUnmapFaceCommand.Activated")
        s = FreeCADGui.Selection.getSelectionEx()
        if len(s) < 1:
            print("select a subObject first!")
            return
        a2pObj = s[0].Object
        subName = s[0].SubElementNames[0]
        parts = re.split('(\d.*)',subName)
        faceIdx  = int(parts[1]) - 1                  #change name to index
        pair = unmapA2pFace(a2pObj, faceIdx)
        # do something with original reference (pair)
#        print("original reference: " + pair[0] + "/Face" + str(pair[1]))

        return
            

    def IsActive(self):
        """Here you can define if the command must be active or not (greyed) if certain conditions
        are met or not. This function is optional."""
        return True

FreeCADGui.addCommand('a2p_topoUnmapFace',a2p_topoUnmapFaceCommand())


#</topo>


