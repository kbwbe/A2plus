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

import FreeCADGui,FreeCAD
from PySide import QtGui, QtCore
import Spreadsheet
import os

import a2plib
from a2p_fcdocumentreader import FCdocumentReader


#------------------------------------------------------------------------------
def createPartList(
        importPath,
        parentAssemblyDir,
        partListEntries,
        recursive=False
        ):
    '''
    Extract quantities and descriptions of assembled parts from
    document.xml
    Is able to analyse subassemblies by recursion
    '''
    fileNameInProject = a2plib.findSourceFileInProject(
        importPath,
        parentAssemblyDir
        )
    workingDir,basicFileName = os.path.split(fileNameInProject)
    docReader = FCdocumentReader()
    docReader.openDocument(fileNameInProject)
    for ob in docReader.getA2pObjects():
        print(u'{}, Subassembly? = {}'.format(ob,ob.isSubassembly()))
        if ob.isSubassembly and recursive:
            createPartList(
                ob.getA2pSource(),
                workingDir,
                partListEntries,
                recursive
                )




#------------------------------------------------------------------------------
class a2p_CreatePartlist():

    def Activated(self):
        doc = FreeCAD.activeDocument()

        if doc == None:
            QtGui.QMessageBox.information(  QtGui.QApplication.activeWindow(),
                                        "No active document found!",
                                        "You have to open an fcstd file first."
                                    )
            return
        
        completeFilePath = doc.FileName
        p,f = os.path.split(completeFilePath)
        
        createPartList(
            doc.FileName,
            p,
            {},
            recursive=True
            )
        

    def GetResources(self):
        return {
            'Pixmap'  :     a2plib.pathOfModule()+'/icons/a2p_partsList.svg',
            'MenuText':     'create a spreadsheet with a partlist of this file',
            'ToolTip':      'create a spreadsheet with a partlist of this file'
            }
        
FreeCADGui.addCommand('a2p_CreatePartlist', a2p_CreatePartlist())
#------------------------------------------------------------------------------

















