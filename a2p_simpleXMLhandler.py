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



import FreeCAD
import FreeCADGui
import os

class SimpleXMLhandler():
    def __init__(self):
        self.XML = []
    
    def clear(self):
        self.XML = []
        
    def writeHeader(self):
        self.clear()
        self.XML += '''<?xml version='1.0' encoding='utf-8'?>'''
        self.XML += '''\n<!-- FreeCAD A2plus Document -->'''
        self.XML +=  '''\n<Document SchemaVersion="1" A2PlusVersion="V0.5" FileVersion="1">''' 

    def writeFooter(self):
        self.XML += '''\n</Document>'''
        
    def writeProperty(self,propname,propvalue):
        self.XML += '''\n\t<Property name="%s">''' % propname
        self.XML += '''\n\t\t<String value="%s"/>''' % propvalue
        self.XML += '''\n\t</Property>'''
        
    def createInformationXML(self,
                      importDocLabel,
                      importDocFileName,
                      sourcePartCreationTime = 0.0,
                      isSubAssembly = False,
                      transparency = 0,
                      ):
        self.writeHeader()
        self.writeProperty("importDocLabel", importDocLabel)
        self.writeProperty("importDocFileName", importDocFileName)
        self.writeProperty("sourcePartCreationTime", sourcePartCreationTime)
        self.writeProperty("isSubAssembly", isSubAssembly)
        self.writeProperty("transparency", transparency)
        self.writeFooter()
        return self.XML
