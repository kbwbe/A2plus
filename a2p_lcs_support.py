#***************************************************************************
#*                                                                         *
#*   Copyright (c) 2019 kbwbe                                              *
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


#==============================================================================
def LCS_Group_deleteContent(_self,doc):
    '''
    LCS_Group featurepython extending function deleteContent
    '''
    if len(_self.Group) > 0:
        deleteList = []
        deleteList.extend(_self.Group)
        _self.Group = []
        for ob in deleteList:
            doc.removeObject(ob.Name) # delete the imported LCS'

#==============================================================================
class LCS_Group(object):
    def __init__(self, obInstance):
        obInstance.addExtension('App::GeoFeatureGroupExtensionPython', self)
        obInstance.addProperty("App::PropertyString","Owner").Owner = ''
        obInstance.setEditorMode('Owner', 1)
        obInstance.setEditorMode('Placement', 1)  #read-only # KBWBE: does not work...
        obInstance.deleteContent = LCS_Group_deleteContent # add a function to this featurepython class
        
    def execute(self, obj):
        pass
        
#==============================================================================
class VP_LCS_Group(object):
    def __init__(self,vobj):
        vobj.addExtension('Gui::ViewProviderGeoFeatureGroupExtensionPython', self)
        vobj.Proxy = self

    def attach(self, vobj):
        self.ViewObject = vobj
        self.Object = vobj.Object

    def onDelete(self, viewObject, subelements): # subelements is a tuple of strings
        if FreeCAD.activeDocument() != viewObject.Object.Document:
            return False # only delete objects in the active Document anytime !!
        obj = viewObject.Object
        doc = obj.Document
        try:
            if obj.Owner != '':
                owner = doc.getObject(obj.Owner)
                owner.lcsLink = [] # delete link entry within owning A2p part.
        except:
            pass
        obj.deleteContent(doc) # Clean up this group complete with all content
        return True

    def getIcon(self):
        return ":/icons/a2p_LCS_group.svg"

    def __getstate__(self):
        return None

    def __setstate__(self,state):
        return None

#==============================================================================
def getListOfLCS(targetDoc,sourceDoc):
    lcsOut = []
    for sourceOb in sourceDoc.Objects:
        if (
                sourceOb.Name.startswith("Local_CS") or
                sourceOb.Name.startswith("App__Placement") or
                sourceOb.Name.startswith("a2pLCS") or
                sourceOb.Name.startswith("PartDesign__CoordinateSystem")
                ):
            newLCS = targetDoc.addObject("PartDesign::CoordinateSystem","a2pLCS")
            pl = sourceOb.getGlobalPlacement()
            newLCS.Placement = pl
            newLCS.setEditorMode('Placement', 1)  #read-only # KBWBE: does not work...
            lcsOut.append(newLCS)
    return lcsOut
