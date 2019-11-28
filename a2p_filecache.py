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

class FileCache():
    def __init__(self):
        self.cache = {}
        
    def addFile(self,fileName,timeStamp, topoNames):
        self.cache[fileName] = (timeStamp,topoNames)
        
    def load(self,fileName, objectTimeStamp):
        cacheEntry = self.cache.get(fileName,None)
        if cacheEntry is not None:
            if cacheEntry[0] > objectTimeStamp:
                print("cache already loaded")
                return
            
        #Nothing found, file needs to be loaded..
        doc = FreeCAD.activeDocument()
        assemblyPath = os.path.normpath(os.path.split(doc.FileName)[0])
        fileNameWithinProjectFile = a2plib.findSourceFileInProject(fileName, assemblyPath)
        if fileNameWithinProjectFile == None:
            QtGui.QMessageBox.critical(
                QtGui.QApplication.activeWindow(),
                u"File error ! ",
                u"Cannot find {}".format(fileNameWithinProjectFile)
                )
            return None
        
        #A valid sourcefile is found, search for corresponding a2p-file
        zipFile = a2p_importpart.getOrCreateA2pFile(fileNameWithinProjectFile)
        if zipFile is None: 
            QtGui.QMessageBox.critical(
                QtGui.QApplication.activeWindow(),
                u"File error ! ",
                u"Cannot create a2p file for {}".format(fileNameWithinProjectFile)
                )
            return None
        
        #A valid a2p file exist, read it...
        shape, muxInfo, diffuseColor, properties = a2plib.readA2pFile(zipFile)
        print ("a2p file has been loaded")
        
fileCache = FileCache()
        
