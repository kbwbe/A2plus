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
from PySide import QtGui, QtCore
import os, copy, time
import a2plib
from a2p_versionmanagement import SubAssemblyWalk, A2P_VERSION
from a2plib import (
    appVersionStr,
    AUTOSOLVE_ENABLED
    )

def makeFaceList(doc, objList): 
    '''build a list of all the Faces in obj with docName, objName, subObjName, faceIndex'''
    print "topNaming list trial"
    print "objIndex/docName/parentGroup/objName/Facennn"
    docName = doc.Name
    objIndex = 0
    for obj in objList:
        if hasattr(obj,"Shape"):
            iFace = 1
            if obj.getParentGeoFeatureGroup():
                parentName = obj.getParentGeoFeatureGroup().Name
            else:
                parentName = "None"
            for f in obj.Shape.Faces:
                print str(objIndex), "/",docName, "/",parentName, "/", obj.Name, "/Face", str(iFace)
                iFace += 1
        else: 
            #constraints come here. we should just skip them??
            print str(objIndex), "/", docName, "/",obj.Name, "/No Shape"
        objIndex += 1
    print "trial complete"

