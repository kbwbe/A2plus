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
# helpers for writing XML information to FCStd.a2p files
#===========================================================================



import FreeCAD, FreeCADGui, os
import zipfile
import a2plib
import a2p_versionmanagement

class SimpleXMLhandler():
    def __init__(self):
        self.XML = []
    
    def clear(self):
        self.XML = []
        
    def writeHeader(self):
        self.clear()
        self.XML += '''<?xml version='1.0' encoding='utf-8'?>'''
        self.XML += '''\n<!-- FreeCAD A2plus Document -->'''

        self.XML +=  '''\n<Document SchemaVersion="1" A2PlusVersion="%s" FileVersion="1">''' % (
                a2plib.to_bytes(a2p_versionmanagement.A2P_VERSION)
                )

    def writeFooter(self):
        self.XML += '''\n</Document>'''
        
    def writeProperty(self,propname,propvalue):
        self.XML += '''\n\t<Property name="%s">''' % propname
        self.XML += '''\n\t\t<String value="%s"/>''' % propvalue
        self.XML += '''\n\t</Property>'''
        
    def createInformationXML(self,
                      sourcePartCreationTime = 0.0,
                      isSubAssembly = False,
                      transparency = 0,
                      ):
        self.writeHeader()
        self.writeProperty("sourcePartCreationTime", sourcePartCreationTime)
        self.writeProperty("isSubAssembly", isSubAssembly)
        self.writeProperty("transparency", transparency)
        self.writeFooter()
        return self.XML
        
    def retrieveData(self,xmlString):
        xmlLines = xmlString.split("\n")
        for line in xmlLines:
            print(line)
        
        
        
