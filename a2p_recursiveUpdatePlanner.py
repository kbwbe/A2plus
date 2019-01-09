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
import os
import string

import a2plib
from a2p_fcdocumentreader import FCdocumentReader


#==============================================================================
def createUpdateFileList(
            importPath,
            parentAssemblyDir,
            modificationTime,
            filesToUpdate,
            recursive=False
            ):
    fileNameInProject = a2plib.findSourceFileInProject(
        importPath,
        parentAssemblyDir
        )
    workingDir,basicFileName = os.path.split(fileNameInProject)
    docReader1 = FCdocumentReader()
    
    docReader1.openDocument(fileNameInProject)
    needToUpdate = False
    subAsmNeedsUpdate = False
    for ob in docReader1.getA2pObjects():
        if ob.isSubassembly() and recursive:
            subAsmNeedsUpdate, filesToUpdate = createUpdateFileList(
                                                ob.getA2pSource(),
                                                workingDir,
                                                modificationTime,
                                                filesToUpdate,
                                                recursive
                                                )
        if subAsmNeedsUpdate:
            needToUpdate = True
        if ob.getModificationTime() > modificationTime:
            needToUpdate = True
            
    if needToUpdate:
        if fileNameInProject not in filesToUpdate:
            filesToUpdate.append(fileNameInProject)
        
    return needToUpdate, filesToUpdate
#==============================================================================
            
    
            
            
