#***************************************************************************
#*                                                                         *
#*   Copyright (c) 2018 kbwbe                                              *
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
import Spreadsheet, os
#from PyQt4 import QtGui,QtCore
from PySide import QtCore, QtGui
from FreeCAD import Base
from a2plib import *
App=FreeCAD
Gui=FreeCADGui

A2P_VERSION = 'V0.1'


class SubAssemblyWalk():
    '''
    Class for walking through subassemblies, 
    creating missing properties,
    checking for necessary update of importparts...
    
    start it with method executeWalk(self)
    '''
    
    def __init__(self,startFile):
        self.startFile = startFile
        self.docsToBeClosed = []
        
    def checkForSubAssembly(self,subFileName):
        filename = findSourceFileInProject(subFileName) # path within subfile will be ignored..
        if filename == None:
            FreeCAD.Console.PrintMessage(
                "SubassemblyCheck failed for {} ".format( subFileName ) 
                )
            return False

        doc_already_open = filename in [ d.FileName for d in FreeCAD.listDocuments().values() ]
        if doc_already_open:
            doc = [ d for d in FreeCAD.listDocuments().values() if d.FileName == filename][0]
        else:
            doc = FreeCAD.openDocument(filename)
        
        for obj in doc.Objects:
            if hasattr(obj, 'sourceFile'):
                if not doc_already_open:
                    FreeCAD.closeDocument(doc.Name)
                return True
        
        if not doc_already_open:
            FreeCAD.closeDocument(doc.Name)
        return False
        
    def openSubAssembly(self,subFile): #recursive func!! This can consumpt the total memory of your computer
        filename = findSourceFileInProject(subFile) # path within subfile will be ignored..
        if filename == None:
            FreeCAD.Console.PrintMessage( "Missing file {} ignored".format(subFile) )
            return False
        
        doc_already_open = filename in [ d.FileName for d in FreeCAD.listDocuments().values() ]
        if doc_already_open:
            doc = [ d for d in FreeCAD.listDocuments().values() if d.FileName == filename][0]
        else:
            doc = FreeCAD.openDocument(filename)
        
        needUpdate = False
        
        for obj in doc.Objects:
            if hasattr(obj, 'sourceFile'):
                
                # This Section: Add missing but necessary properties of this Version
                if not hasattr( obj, 'a2p_Version'):
                    obj.addProperty("App::PropertyString", "a2p_Version","importPart").a2p_Version = 'V0.0'
                    obj.setEditorMode("a2p_Version",1)
                    needUpdate = True
                    
                if not hasattr( obj, 'muxInfo'):
                    obj.addProperty("App::PropertyStringList", "muxInfo","importPart").muxInfo = []
                    needUpdate = True

                if not hasattr(obj, 'subassemblyImport'):
                    obj.addProperty("App::PropertyBool","subassemblyImport","importPart").subassemblyImport = False
                    obj.setEditorMode("subassemblyImport",1)
                    obj.subassemblyImport = self.checkForSubAssembly(obj.sourceFile)
                    needUpdate = True
                    
                if obj.subassemblyImport == True:
                    # This Section: Open subassemblies which this assembly depends on...    
                    replacement = findSourceFileInProject(obj.sourceFile) # work in any case with files within projectFolder!
                    if replacement == None:
                        QtGui.QMessageBox.critical(  QtGui.QApplication.activeWindow(), 
                                                     "Source file not found", 
                                                     "update of %s aborted!\nUnable to find %s" % (
                                                         obj.Name, 
                                                         obj.sourceFile
                                                         ) 
                                                   )
                    else:
                        if obj.sourceFile != replacement:
                            obj.sourceFile = replacement # update Filepath, perhaps location changed due to new projectFile!
                        result = self.openSubAssembly(obj.sourceFile)
                        if result == True:
                            needUpdate = True
                            
                if obj.a2p_Version != A2P_VERSION:
                    needUpdate = True
                    
                if os.path.getmtime( obj.sourceFile ) > obj.timeLastImport:
                    needUpdate = True
                    
        if not needUpdate:
            if doc not in self.docsToBeClosed:
                self.docsToBeClosed.append(doc)
                
        return needUpdate
                
        
        
    
    def executeWalk(self):
        self.docsToBeClosed = []
        self.openSubAssembly(self.startFile)
        for doc in self.docsToBeClosed:
            if doc.FileName != self.startFile:
                FreeCAD.closeDocument(doc.Name)
































































        
        