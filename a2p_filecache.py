#***************************************************************************
#*                                                                         *
#*   Copyright (c) 2019 kbwbe                                              *
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

import FreeCAD
import FreeCADGui
from PySide import QtGui
from PySide import QtCore
import a2plib
import a2p_importpart
import os
from reportlab.pdfbase.pdfmetrics import _dynFaceNames

class FileCache():
    def __init__(self):
        self.cache = {}
        
    def load(self,fileName, objectTimeStamp):
        #Search cache for entry
        cacheKey = os.path.split(fileName)[1]
        cacheEntry = self.cache.get(cacheKey,None)
        if cacheEntry is not None:
            if cacheEntry[0] >= objectTimeStamp:
                print(u"cache hit!")
                return #entry found, nothing to do
        
        doc = FreeCAD.activeDocument()
        assemblyPath = os.path.normpath(os.path.split(doc.FileName)[0])
        fileNameWithinProjectFile = a2plib.findSourceFileInProject(fileName, assemblyPath)
        if fileNameWithinProjectFile == None:
            QtGui.QMessageBox.critical(
                QtGui.QApplication.activeWindow(),
                u"File error ! ",
                u"Cannot find {}".format(fileNameWithinProjectFile)
                )
            return

        #A valid sourcefile is found, search for corresponding a2p-file
        zipFile = a2p_importpart.getOrCreateA2pFile(fileNameWithinProjectFile)
        if zipFile is None: 
            QtGui.QMessageBox.critical(
                QtGui.QApplication.activeWindow(),
                u"File error ! ",
                u"Cannot create a2p file for {}".format(fileNameWithinProjectFile)
                )
            return
        
        #A valid a2p file exists, read it...
        shape, vertexNames, edgeNames, faceNames, diffuseColor, properties = \
            a2plib.readA2pFile(zipFile)
        sourcePartCreationTime = float(properties["sourcePartCreationTime"])
        self.cache[cacheKey] = (sourcePartCreationTime,
                                vertexNames,
                                edgeNames,
                                faceNames
                                )
        print(u"file loaded to cache")
        
fileCache = FileCache()
        
