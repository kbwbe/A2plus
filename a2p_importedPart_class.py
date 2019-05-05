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
import Part
import os
import copy
import numpy
from FreeCAD import  Base
from PySide import QtGui
import a2plib

#==============================================================================
class Proxy_importPart:
    '''
    The a2p importPart object
    '''
    def __init__(self,obj):
        obj.Proxy = self
        Proxy_importPart.setProperties(self,obj)
        self.type = "a2p_importPart"
        
    def setProperties(self,obj):
        propList = obj.PropertiesList
        if not "a2p_Version" in propList:
            obj.addProperty("App::PropertyString", "a2p_Version", "importPart")
        if not "sourceFile" in propList:
            obj.addProperty("App::PropertyFile", "sourceFile", "importPart")
        if not "sourcePart" in propList:
            obj.addProperty("App::PropertyString", "sourcePart", "importPart")
        if not "muxInfo" in propList:
            obj.addProperty("App::PropertyStringList","muxInfo","importPart")
        if not "timeLastImport" in propList:
            obj.addProperty("App::PropertyFloat", "timeLastImport","importPart")
        if not "fixedPosition" in propList:
            obj.addProperty("App::PropertyBool","fixedPosition","importPart")
        if not "subassemblyImport" in propList:
            obj.addProperty("App::PropertyBool","subassemblyImport","importPart")
        if not "updateColors" in propList:
            obj.addProperty("App::PropertyBool","updateColors","importPart")

        self.type = "a2p_importPart"

    def onDocumentRestored(self,obj):
        Proxy_importPart.setProperties(self,obj)

    def __getstate__(self):
        return None

    def __setstate__(self,state):
        return None
    
    def execute(self, obj):
        # if a group containing LCS's exists, then move it
        # according to the imported part
        if hasattr(obj,"lcsLink"):
            if len(obj.lcsLink) > 0:
                lcsGroup = obj.lcsLink[0]
                lcsGroup.Placement = obj.Placement
                lcsGroup.purgeTouched() #untouch the lcsGroup, otherwise it stays touched.


#==============================================================================
class ImportedPartViewProviderProxy:
    '''
    A ViewProvider for the a2p importPart object
    '''
    def __init__(self,vobj):
        vobj.Proxy = self

    def claimChildren(self):
        if hasattr(self,'Object'):
            try:
                children = list()
                for obj in self.Object.InList:
                    if a2plib.isA2pObject(obj):
                        children.append(obj)
                if hasattr(self.Object,'lcsLink'):
                    for obj in self.Object.lcsLink:
                        children.append(obj)
                return children
            except:
                #FreeCAD has already deleted self.Object !!
                return[]
        else:
            return []

    def onDelete(self, viewObject, subelements): # subelements is a tuple of strings
        if FreeCAD.activeDocument() != viewObject.Object.Document:
            return False # only delete objects in the active Document anytime !!
        obj = viewObject.Object
        doc = obj.Document

        deleteList = []
        for c in doc.Objects:
            if 'ConstraintInfo' in c.Content: # a related Constraint
                if obj.Name in [ c.Object1, c.Object2 ]:
                    deleteList.append(c)
        if len(deleteList) > 0:
            for c in deleteList:
                a2plib.removeConstraint(c) #also deletes the mirrors...
                
        if hasattr(obj,"lcsLink"):
            if len(obj.lcsLink)>0:
                lscGroup = doc.getObject(obj.lcsLink[0].Name)
                lscGroup.deleteContent(doc)
                doc.removeObject(lscGroup.Name)
                
        return True # If False is returned the object won't be deleted

    def getIcon(self):
        if hasattr(self,"Object"):
            if hasattr(self.Object,"subassemblyImport"):
                if self.Object.subassemblyImport:
                    return ":/icons/a2p_Asm.svg"
            if hasattr(self.Object,"sourceFile"):
                if self.Object.sourceFile == 'converted':
                    return ":/icons/a2p_ConvertPart.svg"
        return ":/icons/a2p_Obj.svg"

    def __getstate__(self):
        return None

    def __setstate__(self, state):
        return None
    
    def attach(self, vobj):
        self.object_Name = vobj.Object.Name
        self.Object = vobj.Object

    def setupContextMenu(self, ViewObject, popup_menu):
        pass

#==============================================================================
class Proxy_muxAssemblyObj(Proxy_importPart):
    '''
    A wrapper for compatibilty reasons...
    '''
    pass
#==============================================================================
class Proxy_convertPart(Proxy_importPart):
    '''
    A wrapper for compatibilty reasons...
    '''
    pass
#==============================================================================
