# -*- coding: utf-8 -*-
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


#===========================================================================
# Classes for reading "document.xml" file directly from compressed .fcstd file
#
# This file is a temporary replacement for a2p docreader using xml.etree.ElementTree.
# Elementree depends on libexpat. There is a conflict within the libexpat,
# libcoin-buildin and the OS system one on various OS.
#===========================================================================



import FreeCAD, FreeCADGui, os
import zipfile

#===========================================================================
class simpleXMLObject(object):
    def __init__(self):
        self.xmlDefs = []
        self.name = None
        self.propertyDict = {}
        
    def clear(self):
        self.xmlDefs = []
        self.name = None
        self.propertyDict = {}
        
    def initialize(self,xmlDefs):
        remainingLines = []
        inputXML = xmlDefs
        #if len(inputXML) == 0: return xmlDefs #todo: raise error
        strippedLine = inputXML[0].lstrip(' ')
        if not strippedLine.startswith('<Object name'): return [] # XML trailers ignored
        idx = 0
        for line in inputXML:
            strippedLine = line.lstrip(' ')
            self.xmlDefs.append(strippedLine)
            idx += 1
            if strippedLine.startswith('</Object>'):
                remainingLines = xmlDefs[idx:]
                break
        self.scanForProperties()
        return remainingLines
            
    def scanForProperties(self):
        sourceFileFound = False
        a2pVersionFound = False
        subAssemblyImportFound = False
        timeLastImportFound = False
        spreadSheetCellsFound = False
        
        numLines = len(self.xmlDefs)
        # Readout object's name and save it (1rst line)
        if numLines > 0:
            line = self.xmlDefs[0]
            segments = line.split('"')
            self.name = segments[1]
            
        idx = 0
        while idx<numLines:
            line = self.xmlDefs[idx]
            
            if not sourceFileFound and line.startswith('<Property name="sourceFile"'):
                idx+=1
                line = self.xmlDefs[idx]
                segments = line.split('"')
                fileName = segments[1]
                self.propertyDict['sourceFile'] = fileName
                sourceFileFound = True
                
            elif not a2pVersionFound and line.startswith('<Property name="a2p_Version"'):
                idx+=1
                line = self.xmlDefs[idx]
                segments = line.split('"')
                a2pVersion = segments[1]
                self.propertyDict['a2p_Version'] = a2pVersion
                a2pVersionFound = True
                
            elif not a2pVersionFound and line.startswith('<Property name="assembly2Version"'):
                idx+=1
                line = self.xmlDefs[idx]
                segments = line.split('"')
                a2pVersion = segments[1]
                self.propertyDict['a2p_Version'] = a2pVersion
                a2pVersionFound = True
                
            # for very old a2p versions do additionally...
            elif not subAssemblyImportFound and line.startswith('<Property name="subassemblyImport"'):
                idx+=1
                line = self.xmlDefs[idx]
                segments = line.split('"')
                tmp = segments[1]
                val = True
                if tmp == "false":
                    val = False
                self.propertyDict['subassemblyImport'] = val
                subAssemblyImportFound = True
                
            elif not timeLastImportFound and line.startswith('<Property name="timeLastImport"'):
                idx+=1
                line = self.xmlDefs[idx]
                segments = line.split('"')
                tmp = segments[1]
                floatVal = float(tmp)
                self.propertyDict['timeLastImport'] = floatVal
                timeLastImportFound = True
                
            elif not spreadSheetCellsFound and line == '<Property name="cells" type="Spreadsheet::PropertySheet">':
                spreadSheetCellsFound = True
                idx += 2
                cellDict = {}
                while True:
                    line = self.xmlDefs[idx]
                    if line.startswith('</Cells>'): break
                    if line.startswith('<Cell address="'):
                        cellAdress,cellContent = self.parseCellLine(line)
                        cellDict[cellAdress] = cellContent
                    idx += 1
                self.propertyDict['cells'] = cellDict
            idx+=1
        self.xmlDefs = [] # we are done, free memory...
    
    def parseCellLine(self,line):
        '''
        parse XML cell entries within an spreadsheet object
        '''
        segments = line.split('"')
        cellAdress = segments[1]
        cellContent = ""
        if len(segments) >= 4:
            if len(segments[2]) > 0:
                if "content" in segments[2]:
                    cellContent = segments[3]
        return cellAdress, cellContent
    
    def isA2pObject(self):
        if self.propertyDict.get('a2p_Version',None) != None: return True
        return False
    
    def isSpreadSheet(self):
        if self.propertyDict.get('cells',None) != None: return True
        return False
    
    def getA2pSource(self):
        if self.isA2pObject:
            return self.propertyDict['sourceFile']
        return None
    
    def isSubassembly(self):
        if self.isA2pObject:
            propFound = self.propertyDict.get('subassemblyImport',None)
            if propFound:
                return self.propertyDict['subassemblyImport']
            else:
                return False
        return False
    
    def getTimeLastImport(self):
        if self.isA2pObject:
            propFound = self.propertyDict.get('timeLastImport',None)
            if propFound:
                return self.propertyDict['timeLastImport']
            else:
                return 0.0
        return 0.0
    
#==============================================================================
class FCdocumentReader(object):
    '''
    class for extracting the XML-Documentdata from a fcstd-file given by
    filepath. Some data can be extracted without opening the whole document
    within FreeCAD
    
    As xml.etree.ElementTree is not working within FC due to broken libexpat.so
    (ATM), this file is a workaround as there is not much data to be extracted.
    '''
    def __init__(self):
        self.xmlLines = []
        self.objects = []
        
    def clear(self):
        self.xmlLines = []
        self.objects = []
        
    def openDocument(self,fileName):
        self.clear()
        # check whether file exists or not...
        if not os.path.exists( fileName ):
            print (u"fcDocumentReader: file {} does not exist!".format(fileName))
            return
        # decompress the file
        f = zipfile.ZipFile(fileName,'r')
        xml = f.read('Document.xml')
        f.close()
        #
        self.xmlLines = xml.split("\r\n") #Windows
        if len(self.xmlLines) <= 1:
            self.xmlLines = xml.split("\n") #Linux
        del(xml)
        
        # remove not needed data above first section <objects name=...
        idx = 0
        for line in self.xmlLines:
            if line.lstrip(' ').startswith('<Object name'):
                break
            else:
                idx+=1
        self.xmlLines = self.xmlLines[idx:] #reduce list size instantly
        
        while len(self.xmlLines) > 0:
            if not self.xmlLines[0].strip(' ').startswith('<Object name'): break
            ob = simpleXMLObject()
            self.xmlLines = ob.initialize(self.xmlLines)
            self.objects.append(ob)
        
        # remove not needed objects
        tmp = []
        for ob in self.objects:
            if ob.isA2pObject() or ob.isSpreadSheet():
                tmp.append(ob)
        self.objects = tmp
        
        for ob in self.objects:
            print(ob.name)
            print(ob.propertyDict)
            print("")
            
        print(
            "Number of objects: {}".format(
                len(self.objects)
                )
            )
        
    def getA2pObjects(self):
        out = []
        for ob in self.objects:
            if ob.propertyDict.get('a2p_Version',None) != None:
                out.append(ob)
                continue
        return out
        
    def getSpreadsheetObjects(self):
        out = []
        for ob in self.objects:
            if ob.propertyDict.get('cells',None) != None:
                out.append(ob)
        return out
            
    def getObjectByName(self,name):
        for ob in self.objects:
            if ob.name == name:
                return ob
        return None

#==============================================================================

if __name__ == "__main__":
    doc = FreeCAD.activeDocument()
    fileName = doc.FileName
    
    dr = FCdocumentReader()
    dr.openDocument(fileName)

