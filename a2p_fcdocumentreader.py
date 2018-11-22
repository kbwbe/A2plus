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

import FreeCAD, FreeCADGui

import zipfile
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

#------------------------------------------------------------------------------
class A2p_xmldoc_Property(object):
    '''
    BaseClass for xml-Properties
    '''
    def __init__(self,treeElement, name,_type):
        self.treeElement = treeElement
        self.name = name
        self.type = _type
        
    def __str__(self):
        return "PropertyName: {}, Type: {}".format(self.name,self.type)

#------------------------------------------------------------------------------
class A2p_xmldoc_PropertyString(A2p_xmldoc_Property):
    
    def getStringValue(self):
        s = self.treeElement.find('String')
        return s.attrib['value']
    
#------------------------------------------------------------------------------
class A2p_xmldoc_PropertyBool(A2p_xmldoc_Property):
    
    def getBool(self):
        s = self.treeElement.find('Bool')
        if s.attrib['value'] == 'true':
            return True
        else:
            return False
    
#------------------------------------------------------------------------------
class A2p_xmldoc_PropertyFile(A2p_xmldoc_Property):
    
    def getStringValue(self):
        s = self.treeElement.find('String')
        return s.attrib['value']
    
#------------------------------------------------------------------------------
class A2p_xmldoc_PropertySheet(A2p_xmldoc_Property):
    
    def getCellValues(self):
        '''returns a dict:  cellAddress:value '''
        cellEntries = self.treeElement.findall('Cells/Cell')
        cellDict = {}
        for ce in cellEntries:
            try:
                cellDict[ce.attrib['address']] = ce.attrib['content']
            except:
                pass # no content attribute, perhaps backgroundcolor or somethin else...
        return cellDict

#------------------------------------------------------------------------------
class A2p_xmldoc_Object(object):
    '''
    class prototype to store FC objects found in document.xml
    '''
    def __init__(self,name,_type, tree):
        self.tree = tree
        self.dataElement = None
        self.name = name
        self.type = _type
        self.propertyDict = {}
        self.loadPropertyDict(self.tree)
        self.label = self.propertyDict['Label'].getStringValue()
        
    def __str__(self):
        return u"ObjName: {}, Label: {}, Type: {}".format(
            self.name,
            self.label, 
            self.type
            )
    
    def loadPropertyDict(self,tree):
        for elem in tree.iterfind('ObjectData/Object'):
            if elem.attrib['name'] == self.name:
                self.dataElement = elem
                for e in elem.findall('Properties/Property'):
                    if e.attrib['type'] == 'App::PropertyString':
                        p = A2p_xmldoc_PropertyString(
                            e,
                            e.attrib['name'],
                            e.attrib['type']
                            )
                        self.propertyDict[e.attrib['name']] = p
                    elif e.attrib['type'] == 'App::PropertyBool':
                        p = A2p_xmldoc_PropertyBool(
                            e,
                            e.attrib['name'],
                            e.attrib['type']
                            )
                        self.propertyDict[e.attrib['name']] = p
                    elif e.attrib['type'] == 'App::PropertyFile':
                        p = A2p_xmldoc_PropertyFile(
                            e,
                            e.attrib['name'],
                            e.attrib['type']
                            )
                        self.propertyDict[e.attrib['name']] = p
                    elif e.attrib['type'] == 'Spreadsheet::PropertySheet':
                        p = A2p_xmldoc_PropertySheet(
                            e,
                            e.attrib['name'],
                            e.attrib['type']
                            )
                        self.propertyDict[e.attrib['name']] = p
                    else:
                        pass # unsupported property type
#------------------------------------------------------------------------------
class A2p_xmldoc_SpreadSheet(A2p_xmldoc_Object):
    
    def getCells(self):
        return self.propertyDict['cells'].getCellValues()

#------------------------------------------------------------------------------
class A2p_xmldoc_FeaturePython(A2p_xmldoc_Object):
    
    def isA2pObject(self):
        if self.propertyDict.get('a2p_Version',None) != None: return True
        return False
    
    def getA2pSource(self):
        if self.isA2pObject:
            return self.propertyDict['sourceFile'].getStringValue()
        return None
    
    def isSubassembly(self):
        if self.isA2pObject:
            propFound = self.propertyDict.get('subassemblyImport',None)
            if propFound:
                return propFound.getBool()
            else:
                return False
        return False

#------------------------------------------------------------------------------
class FCdocumentReader(object):
    '''
    class for extracting the XML-Documentdata from a fcstd-file given by
    filepath. Some data can be extracted without opening the whole document
    within FreeCAD
    '''
    def __init__(self):
        self.tree = None
        self.root = None
        self.objects = []
        
    def clear(self):
        self.realPath = ''
        self.tree = None
        self.root = None
        self.objects = []
        
    def openDocument(self,fileName):
        self.clear()
        #
        # decompress the file
        f = zipfile.ZipFile(fileName,'r')
        xml = f.read('Document.xml')
        f.close()
        #
        # load the ElementTree
        self.tree = ET.ElementTree(ET.fromstring(xml))
        #
        self.loadObjects()
    
    def loadObjects(self):
        self.objects = []
        for elem in self.tree.iterfind('Objects/Object'):
            if elem.attrib['type'].startswith('Spreadsheet'): 
                ob = A2p_xmldoc_SpreadSheet(
                        elem.attrib['name'],
                        elem.attrib['type'],
                        self.tree
                        )
                self.objects.append(ob)
            if elem.attrib['type'].startswith('Part::FeaturePython'): 
                ob = A2p_xmldoc_FeaturePython(
                        elem.attrib['name'],
                        elem.attrib['type'],
                        self.tree
                        )
                self.objects.append(ob)
            else:
                pass # unhandled object types
            
    def getA2pObjects(self):
        out = []
        for ob in self.objects:
            if ob.propertyDict.get('a2p_Version',None) != None:
                out.append(ob)
                continue
            elif ob.propertyDict.get('assembly2Version',None) != None: # for very old a2p projects...
                out.append(ob)
                continue
            
        return out
        
    def getSpreadsheetObjects(self):
        out = []
        for ob in self.objects:
            if ob.type.startswith('Spreadsheet'):
                out.append(ob)
        return out
            
    def getObjectByName(self,name):
        for ob in self.objects:
            if ob.name == name:
                return ob
        return None
#------------------------------------------------------------------------------
        
if __name__ == "__main__":
    doc = FreeCAD.activeDocument() 
    dr = FCdocumentReader()
    dr.openDocument(doc.FileName)
     
    for ob in dr.getSpreadsheetObjects():
        if ob.name == '_PARTINFO_':
            cellDict = ob.getCells()
            for k in cellDict.keys():
                print(u"Address: {}, content {}".format(
                        k,
                        cellDict[k]
                        )
                      )
    for ob in dr.getA2pObjects():
        print(u"sourcefile: {}".format(
                ob.getA2pSource()
                )
              )
        

























