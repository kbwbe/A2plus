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



import FreeCAD
import FreeCADGui
import os
import zipfile
import xml.sax.saxutils as saxutils

import a2plib

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
        strippedLine = inputXML[0].lstrip(b' ')
        if not strippedLine.startswith(b'<Object name'): return [] # XML trailers ignored
        idx = 0
        for line in inputXML:
            strippedLine = line.lstrip(b' ')
            self.xmlDefs.append(strippedLine)
            idx += 1
            if strippedLine.startswith(b'</Object>'):
                remainingLines = xmlDefs[idx:]
                break
        self.scanForProperties()
        return remainingLines
            
    def scanForProperties(self):
        sourceFileFound = False
        a2pVersionFound = False
        subAssemblyImportFound = False
        collectToPartlistFound = False
        timeLastImportFound = False
        spreadSheetCellsFound = False
        a2pObjectTypeFound = False
        
        numLines = len(self.xmlDefs)
        # Readout object's name and save it (1rst line)
        if numLines > 0:
            line = self.xmlDefs[0]
            segments = line.split(b'"')
            self.name = segments[1]
        idx = 0
        while idx<numLines:
            line = self.xmlDefs[idx]
            
            if not sourceFileFound and line.startswith(b'<Property name="sourceFile"'):
                idx+=1
                line = self.xmlDefs[idx]
                segments = line.split(b'"')
                fileName = segments[1]
                self.propertyDict[b'sourceFile'] = a2plib.to_str(fileName)
                sourceFileFound = True
                
            elif not a2pVersionFound and line.startswith(b'<Property name="a2p_Version"'):
                idx+=1
                line = self.xmlDefs[idx]
                segments = line.split(b'"')
                a2pVersion = segments[1]
                self.propertyDict[b'a2p_Version'] = a2plib.to_str(a2pVersion)
                a2pVersionFound = True
                
            elif not a2pVersionFound and line.startswith(b'<Property name="assembly2Version"'):
                idx+=1
                line = self.xmlDefs[idx]
                segments = line.split(b'"')
                a2pVersion = segments[1]
                self.propertyDict[b'a2p_Version'] = a2plib.to_str(a2pVersion)
                a2pVersionFound = True
                
            # for very old a2p versions do additionally...
            elif not subAssemblyImportFound and line.startswith(b'<Property name="subassemblyImport"'):
                idx+=1
                line = self.xmlDefs[idx]
                segments = line.split(b'"')
                tmp = segments[1]
                val = True
                if tmp == b"false":
                    val = False
                self.propertyDict[b'subassemblyImport'] = val
                subAssemblyImportFound = True
                
            elif not collectToPartlistFound and line.startswith(b'<Property name="collectToPartlist"'):
                idx+=1
                line = self.xmlDefs[idx]
                segments = line.split(b'"')
                tmp = segments[1]
                val = True
                if tmp == b"false":
                    val = False
                self.propertyDict[b'collectToPartlist'] = val
                collectToPartlistFound = True
                
            elif not timeLastImportFound and line.startswith(b'<Property name="timeLastImport"'):
                idx+=1
                line = self.xmlDefs[idx]
                segments = line.split(b'"')
                tmp = segments[1]
                floatVal = float(tmp)
                self.propertyDict[b'timeLastImport'] = floatVal
                timeLastImportFound = True
                
            elif not spreadSheetCellsFound and line.startswith(b'<Property name="cells" type="Spreadsheet::PropertySheet"'):
                spreadSheetCellsFound = True
                idx += 2
                cellDict = {}
                while True:
                    line = self.xmlDefs[idx]
                    if line.startswith(b'</Cells>'): break
                    if line.startswith(b'<Cell address="'):
                        cellAdress,cellContent = self.parseCellLine(line)
                        #cellDict[cellAdress] = a2plib.to_str(cellContent)
                        cellDict[cellAdress] = saxutils.unescape(a2plib.to_str(cellContent))
                    idx += 1
                self.propertyDict[b'cells'] = cellDict
                
            elif not a2pObjectTypeFound and line.startswith(b'<Property name="objectType"'):
                idx+=1
                line = self.xmlDefs[idx]
                segments = line.split(b'"')
                objectType = segments[1]
                self.propertyDict[b'objectType'] = a2plib.to_bytes(objectType)
                a2pObjectTypeFound = True
                
            idx+=1
        self.xmlDefs = [] # we are done, free memory...
        
    
    def parseCellLine(self,line):
        '''
        parse XML cell entries within an spreadsheet object
        '''
        segments = line.split(b'"')
        cellAdress = segments[1]
        cellContent = ""
        if len(segments) >= 4:
            if len(segments[2]) > 0:
                if b"content" in segments[2]:
                    cellContent = segments[3]
        return cellAdress, cellContent
    
    def isA2pObject(self):
        if self.propertyDict.get(b'a2p_Version',None) != None: return True
        return False
    
    def isSpreadSheet(self):
        if self.propertyDict.get(b'cells',None) != None: return True
        return False
    
    def getA2pSource(self):
        if self.isA2pObject:
            return self.propertyDict[b'sourceFile']
        return None
    
    def isSubassembly(self):
        if self.isA2pObject:
            propFound = self.propertyDict.get(b'subassemblyImport',None)
            if propFound:
                return self.propertyDict[b'subassemblyImport']
            else:
                return False
        return False
    
    def collectToPartlist(self):
        if self.isA2pObject:
            propFound = self.propertyDict.get(b'collectToPartlist',None)
            if propFound:
                return self.propertyDict[b'collectToPartlist']
            else:
                return True
        return False
    
    def getTimeLastImport(self):
        if self.isA2pObject:
            propFound = self.propertyDict.get(b'timeLastImport',None)
            if propFound:
                return self.propertyDict[b'timeLastImport']
            else:
                return 0.0
        return 0.0
    
    def getCells(self):
        return self.propertyDict[b'cells']
    
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
        self.successfulOpened = False
        
    def clear(self):
        self.xmlLines = []
        self.objects = []
        self.successfulOpened = False
        
    def openDocument(self,_fileName):
        fileName = _fileName
        
        if a2plib.PYVERSION == 3:
            fileName = a2plib.to_str(fileName)
        
        self.clear()
        
        # got a fileName != None ?
        if fileName == None:
            print (u"fcDocumentReader: failed to open file with None name!")
            return

        # check whether file exists or not...
        if not os.path.exists( fileName ):
            print (u"fcDocumentReader: file {} does not exist!".format(fileName))
            return
        
        # check for fcstd file
        if not fileName.lower().endswith(a2plib.to_str('.fcstd')):
            print (u"fcDocumentReader: file {} is no FCStd file!".format(fileName))
            return
        
        # decompress the file
        f = zipfile.ZipFile(fileName,'r')
        xml = f.read('Document.xml')
        f.close()
        self.successfulOpened = True
        #
        #self.xmlLines = xml.split("\r\n") #Windows
        self.xmlLines = xml.split(b'\r\n') #Windows
        if len(self.xmlLines) <= 1:
            self.xmlLines = xml.split(b"\n") #Linux
        del(xml)
        
        # remove not needed data above first section <objects name=...
        idx = 0
        for line in self.xmlLines:
            if line.lstrip(b' ').startswith(b'<Object name'):
                break
            else:
                idx+=1
        self.xmlLines = self.xmlLines[idx:] #reduce list size instantly
        
        while len(self.xmlLines) > 0:
            if not self.xmlLines[0].strip(b' ').startswith(b'<Object name'): break
            ob = simpleXMLObject()
            self.xmlLines = ob.initialize(self.xmlLines)
            self.objects.append(ob)
        
        # remove not needed objects
        tmp = []
        for ob in self.objects:
            if ob.isA2pObject() or ob.isSpreadSheet():
                tmp.append(ob)
        self.objects = tmp
        
    def getA2pObjects(self):
        if not self.successfulOpened: return []
        out = []
        for ob in self.objects:
            value = ob.propertyDict.get(b'objectType',None)
            if value != None:
                if value == b'a2pSketch':
                    continue
            if ob.propertyDict.get(b'a2p_Version',None) != None:
                out.append(ob)
                continue
        return out
        
    def getSpreadsheetObjects(self):
        if not self.successfulOpened: return []
        out = []
        for ob in self.objects:
            if ob.propertyDict.get(b'cells',None) != None:
                out.append(ob)
        return out
            
    def getObjectByName(self,name):
        if not self.successfulOpened: return None
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

