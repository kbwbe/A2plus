#***************************************************************************
#*                                                                         *
#*   Copyright (c) 2020 kbwbe                                              *
#*                                                                         *
#*   Based on Work of Dan Miel (Thank you)                         *
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

import a2plib
import a2p_solversystem

#==============================================================================

toolTipMessage = \
'''
Conflict finder tool:

Resolves conflicting constraints by
trying to solve them one after another
'''

class a2p_SearchConstraintConflictsCommand:
    '''
    Search conflicting constraints by solving them one after each other.
    '''
    def Activated(self):
        doc = FreeCAD.activeDocument()
        
        workList = []
        constraints = [ obj for obj in doc.Objects if 'ConstraintInfo' in obj.Content]
        
        if len(constraints) == 0:
            flags = QtGui.QMessageBox.StandardButton.Yes
            QtGui.QMessageBox.information(
                QtGui.QApplication.activeWindow(), 
                u'Searching for conflicting constraints', 
                u'There are no a2p constraints within this document.', 
                flags
                )
            return
        
        for c in constraints:
            workList.append(c)
            solved = a2p_solversystem.solveConstraints(doc,matelist = workList, showFailMessage=False)
            if solved == False:
                cMirrorName = c.ViewObject.Proxy.mirror_name
                cmirror = doc.getObject(cMirrorName)
                ob1 = doc.getObject(c.Object1)
                ob2 = doc.getObject(c.Object2)
                message = \
u'''
The following constraint-pair is conflicting
with previously defined constraints:

constraint : {}
with mirror: {}

The constraint-pair belongs to the objects:

object1: {}
object2: {}

Do you want to delete this constraint-pair?
'''.format(
    c.Label,
    cmirror.Label,
    ob1.Label,
    ob2.Label
    )                
                flags = QtGui.QMessageBox.StandardButton.Yes | QtGui.QMessageBox.StandardButton.No
                response = QtGui.QMessageBox.information(
                    QtGui.QApplication.activeWindow(), 
                    u'Searching for conflicting constraints', 
                    message, 
                    flags
                    )
                if response == QtGui.QMessageBox.Yes:
                    a2plib.removeConstraint(c)
                return
       
    def IsActive(self):
        if FreeCAD.activeDocument() is None: return False
        return True
                    
    def GetResources(self):
        return {
            'Pixmap'  : a2plib.pathOfModule()+'/icons/a2p_SearchConstraintConflicts.svg',
            'MenuText': 'Indentify conflicting constraints',
            'ToolTip': toolTipMessage
            }
FreeCADGui.addCommand('a2p_SearchConstraintConflictsCommand', a2p_SearchConstraintConflictsCommand())
#==============================================================================


