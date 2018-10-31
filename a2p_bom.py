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
from a2p_partlistglobals import PARTLIST_COLUMN_NAMES


BOM_SHEET_NAME  = '_PARTSLIST_'  #BOM = BillOfMaterials...
BOM_SHEET_LABEL = '#PARTSLIST#'


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
    
    It works with a dict. Structure of an entry is:
    filename: [Quantity,[information,information,....] ]
    '''
    fileNameInProject = a2plib.findSourceFileInProject(
        importPath,
        parentAssemblyDir
        )
    workingDir,basicFileName = os.path.split(fileNameInProject)
    docReader1 = FCdocumentReader()
    docReader1.openDocument(fileNameInProject)
    for ob in docReader1.getA2pObjects():
        print(u'{}, Subassembly? = {}'.format(ob,ob.isSubassembly()))
        if ob.isSubassembly() and recursive:
            partListEntries = createPartList(
                                        ob.getA2pSource(),
                                        workingDir,
                                        partListEntries,
                                        recursive
                                        )
            
        # Process information of this a2p object
        if not ob.isSubassembly() or not recursive:
            # Try to get spreadsheetdata _PARTINFO_ from linked source
            linkedSource = ob.getA2pSource()
            linkedSource = a2plib.findSourceFileInProject(
                            linkedSource,
                            workingDir
                            ) 
            # Is it already processed minimum one time ?
            entry = partListEntries.get(linkedSource,None)
            if entry != None:
                partListEntries.get(linkedSource)[0]+=1 #count sourcefile usage
                continue # only needed to count imports of this file, information exists yet

            # There is no entry in dict, need to read out information from importFile...
            docReader2 = FCdocumentReader()
            docReader2.openDocument(linkedSource)
            # Initialize a default parts information...
            partInformation = []
            for i in range(0,len(PARTLIST_COLUMN_NAMES)):
                partInformation.append("*")
            # last entry of partinformations is reserved for filename
            partInformation[-1] = os.path.split(linkedSource)[1] #without complete path...
            # if there is a proper spreadsheat, then read it...
            for ob in docReader2.getSpreadsheetObjects():
                if ob.name == '_PARTINFO_':
                    cells = ob.getCells()
                    for addr in cells.keys():
                        if addr[:1] == 'B': #column B contains the information
                            idx = int(addr[1:])-1
                            if idx < len(PARTLIST_COLUMN_NAMES): # don't read further!
                                partInformation[idx] = cells[addr]
            # put information to dict and count usage of sourcefiles..
            entry = partListEntries.get(linkedSource,None)
            if entry == None:
                partListEntries[linkedSource] = [
                    1,
                    partInformation
                    ]
            else:
                partListEntries.get(linkedSource)[0]+=1 #count sourcefile usage
                
    return partListEntries


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
        
        flags = QtGui.QMessageBox.StandardButton.Yes | QtGui.QMessageBox.StandardButton.No
        msg = u"Partslist/BOM: Do recursively over all included subassemblies ?"
        response = QtGui.QMessageBox.information(QtGui.QApplication.activeWindow(), u"PARTSLIST/BOM mode?", msg, flags )
        if response == QtGui.QMessageBox.Yes:
            subAssyRecursion = True
        else:
            subAssyRecursion = False
        
        
        
        partListEntries = createPartList(
            doc.FileName,
            p,
            {},
            recursive=subAssyRecursion
            )
        
        for k in partListEntries.keys():
            print partListEntries[k]

        # delete old BOM if one exists...
        try:
            doc.removeObject(BOM_SHEET_NAME)
        except:
            pass
        # create a spreadsheet with a special reserved name...
        ss = doc.addObject('Spreadsheet::Sheet',BOM_SHEET_NAME)
        ss.Label = BOM_SHEET_LABEL
        
        # Write Column headers to spreadsheet
        ss.set('A1',u'POS')
        ss.set('B1',u'QTY')
        idx1 = ord('C')
        idx2 = idx1 + len(PARTLIST_COLUMN_NAMES)
        i=0
        for c in xrange(idx1,idx2):
            ss.set(chr(c)+"1",PARTLIST_COLUMN_NAMES[i])
            i+=1
        # Set the background color of the column headers
        ss.setBackground('A1:'+chr(idx2-1)+'1', (0.000000,1.000000,0.000000,1.000000))
        # Set the columnwith to proper values
        ss.setColumnWidth('A',75)
        i=0
        for c in xrange(idx1,idx2):
            ss.setColumnWidth(chr(c),250)
            i+=1
        # fill entries for partsList...
        idx3 = ord('A')
        for idx, k in enumerate(partListEntries.keys()):
            ss.set('A'+str(idx+2),str(idx+1))
            ss.set('B'+str(idx+2),str(partListEntries[k][0]))
            values = partListEntries[k][1]
            for j,tx in enumerate(values):
                tx2 = tx.encode('UTF-8')
                ss.set(chr(idx3+2+j)+str(idx+2),tx2)
        
        # recompute to finish..
        doc.recompute()
        

    def GetResources(self):
        return {
            'Pixmap'  :     a2plib.pathOfModule()+'/icons/a2p_partsList.svg',
            'MenuText':     'create a spreadsheet with a partlist of this file',
            'ToolTip':      'create a spreadsheet with a partlist of this file'
            }
        
FreeCADGui.addCommand('a2p_CreatePartlist', a2p_CreatePartlist())
#------------------------------------------------------------------------------

















