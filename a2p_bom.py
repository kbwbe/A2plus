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

import FreeCADGui,FreeCAD
from PySide import QtGui, QtCore
import Spreadsheet
import os

import a2plib
from a2p_fcdocumentreader import FCdocumentReader
from xdg.Menu import __getFileName


#------------------------------------------------------------------------------
class partLister(object):
    '''
    Extract quantities and descriptions of assembled parts from
    document.xml
    Is able to analyse subassemblies by recursion
    '''
    def __init__(self,importPath,workingDir): #add workingDir to be able to open relative pathes
        self.importPath = importPath
        self.basicFileName = None
        self.workingDir = None
        self.partListEntries = {}
        #
        fileNameInProject = a2plib.findSourceFileInProject(
            self.importPath,
            workingDir
            )
        self.workingDir,self.basicFileName = os.path.split(fileNameInProject)
        self.docReader = FCdocumentReader()
        self.docReader.openDocument(fileNameInProject)
        
    def createPartListEntries(self,assemblyDir):
        pass
        
#------------------------------------------------------------------------------

















