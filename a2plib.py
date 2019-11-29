#***************************************************************************
#*                                                                         *
#*   Copyright (c) 2018 kbwbe                                              *
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
from FreeCAD import Base
import  Part
from PySide import QtGui
from PySide import QtCore
import os
import sys
import copy
import platform
import numpy
import zipfile

from a2p_viewProviderProxies import *

PYVERSION =  sys.version_info[0]

preferences = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/A2plus")

USE_PROJECTFILE = preferences.GetBool('useProjectFolder', False)
PARTIAL_PROCESSING_ENABLED = preferences.GetBool('usePartialSolver', True)
AUTOSOLVE_ENABLED = preferences.GetBool('autoSolve', True)
RELATIVE_PATHES_ENABLED = preferences.GetBool('useRelativePathes',True)
FORCE_FIXED_POSITION = preferences.GetBool('forceFixedPosition',True)
SHOW_CONSTRAINTS_ON_TOOLBAR= preferences.GetBool('showConstraintsOnToolbar',True)
RECURSIVE_UPDATE_ENABLED = preferences.GetBool('enableRecursiveUpdate',False)
USE_SOLID_UNION = preferences.GetBool('useSolidUnion',True)

SAVED_TRANSPARENCY = []

DEBUGPROGRAM = 1

path_a2p = os.path.dirname(__file__)
path_a2p_resources = os.path.join( path_a2p, 'GuiA2p', 'Resources', 'resources.rcc')
resourcesLoaded = QtCore.QResource.registerResource(path_a2p_resources)
assert resourcesLoaded



wb_globals = {}

RED = (1.0,0.0,0.0)
GREEN = (0.0,1.0,0.0)
BLUE = (0.0,0.0,1.0)
YELLOW = (1.0,1.0,0.0)
WHITE = (1.0,1.0,1.0)
BLACK = (0.0,0.0,0.0)

# DEFINE DEBUG LEVELS FOR CONSOLE OUTPUT
A2P_DEBUG_NONE      = 0
A2P_DEBUG_1         = 1
A2P_DEBUG_2         = 2
A2P_DEBUG_3         = 3

A2P_DEBUG_LEVEL = A2P_DEBUG_NONE

PARTIAL_SOLVE_STAGE1 = 1    #solve all rigid fully constrained to tempfixed rigid, enable only involved dep, then set them as tempfixed
CONSTRAINT_DIALOG_REF = None
CONSTRAINT_EDITOR__REF = None
CONSTRAINT_VIEWMODE = False

#------------------------------------------------------------------------------
# Detect the operating system...
#------------------------------------------------------------------------------
tmp = platform.system()
tmp = tmp.upper()
#print("loading A2plus on operating system '{}'".format(tmp))
tmp = tmp.split(' ')

OPERATING_SYSTEM = 'UNKNOWN'
if "WINDOWS" in tmp:
    OPERATING_SYSTEM = "WINDOWS"
elif "LINUX" in tmp:
    OPERATING_SYSTEM = "LINUX"
else:
    OPERATING_SYSTEM = "OTHER"

#------------------------------------------------------------------------------
def openImportDocFromFile(filename):
    '''
    Open the importDocument from it's file or get it's fc document if it is
    already open.
    '''
    # look only for filenames, not paths, as there are problems on WIN10 (Address-translation??)
    importDoc = None
    importDocIsOpen = False
    requestedFile = os.path.split(filename)[1]
    for d in FreeCAD.listDocuments().values():
        recentFile = os.path.split(d.FileName)[1]
        if requestedFile == recentFile:
            importDoc = d # file is already open...
            importDocIsOpen = True
            break

    if not importDocIsOpen:
        if filename.lower().endswith('.fcstd'):
            importDoc = FreeCAD.openDocument(filename)
        elif filename.lower().endswith('.stp') or filename.lower().endswith('.step'):
            import ImportGui
            fname =  os.path.splitext(os.path.basename(filename))[0]
            FreeCAD.newDocument(fname)
            newname = FreeCAD.ActiveDocument.Name
            FreeCAD.setActiveDocument(newname)
            ImportGui.insert(filename,newname)
            importDoc = FreeCAD.ActiveDocument
        else:
            msg = "A part can only be imported from a FreeCAD '*.FCStd' file"
            QtGui.QMessageBox.information( QtGui.QApplication.activeWindow(), "Value Error", msg )
            
    return importDoc, importDocIsOpen
#------------------------------------------------------------------------------
def writeA2pFile(fileName,shape,toponames, facecolors, xml):
    docPath, docFileName = os.path.split(fileName)
                    
    zipFileName = os.path.join(docPath,docFileName+'.a2p')
    zip = zipfile.ZipFile(zipFileName,'w',zipfile.ZIP_DEFLATED)

    brepFileName = os.path.join(docPath,docFileName+'.brep')
    shape.exportBrep(brepFileName)
    zip.write(brepFileName,'shape.brep')
    os.remove(brepFileName)
    
    vertexNames = []
    edgeNames = []
    faceNames = []
    for tn in toponames:
        if tn.startswith('V'):vertexNames.append(tn)
        if tn.startswith('E'):edgeNames.append(tn)
        if tn.startswith('F'):faceNames.append(tn)
        
    tempFile = os.path.join(docPath,docFileName+'.temp')
    with open(tempFile,'w') as f:
        for tn in vertexNames:
            f.write(tn+'\r\n')
    f.close()
    zip.write(tempFile,'vertexnames')
    os.remove(tempFile)
        
    tempFile = os.path.join(docPath,docFileName+'.temp')
    with open(tempFile,'w') as f:
        for tn in edgeNames:
            f.write(tn+'\r\n')
    f.close()
    zip.write(tempFile,'edgenames')
    os.remove(tempFile)

    tempFile = os.path.join(docPath,docFileName+'.temp')
    with open(tempFile,'w') as f:
        for tn in faceNames:
            f.write(tn+'\r\n')
    f.close()
    zip.write(tempFile,'facenames')
    os.remove(tempFile)
    
    diffuseFileName = os.path.join(docPath,docFileName+'.diffuse')
    with open(diffuseFileName,'w') as f:
        for color in facecolors:
            f.write(a2plib.diffuseElementToTextline(color))
    f.close()
    zip.write(diffuseFileName,'diffusecolor')
    os.remove(diffuseFileName)
    
    xmlFileName = os.path.join(docPath,docFileName+'.xml')
    if PYVERSION > 2:
        with open(xmlFileName,'w') as f:
            f.writelines(xml)
    else:
        with open(xmlFileName,'w') as f:
            for line in xml:
                f.write(to_bytes(line))
    f.close()
    zip.write(xmlFileName,'information.xml')
    os.remove(xmlFileName)

    zip.close()
    return zipFileName
#------------------------------------------------------------------------------
def readA2pFile(fileName):
    zip = zipfile.ZipFile(fileName,'r')
    shape = Part.Shape()
    shape.importBrepFromString(to_str(zip.open("shape.brep").read()))
    
    vertexNames = []
    lines = zip.open("vertexnames").readlines()
    for line in lines:
        tx = to_str(line).strip("\r\n")
        vertexNames.append(tx)
        
    edgeNames = []
    lines = zip.open("edgenames").readlines()
    for line in lines:
        tx = to_str(line).strip("\r\n")
        edgeNames.append(tx)
        
    faceNames = []
    lines = zip.open("facenames").readlines()
    for line in lines:
        tx = to_str(line).strip("\r\n")
        faceNames.append(tx)
        
    diffuseColor = []
    lines = zip.open("diffusecolor").readlines()
    for line in lines:
        diffuseColor.append(diffuseElementFromTextline(line))
    
    xmlContent = zip.open("information.xml").readlines()
    properties = {}
    idx = 0
    while True:
        l = xmlContent[idx]
        line = to_str(l).strip("\t").strip(' ').strip('\r\n')
        if line.startswith("<Property name"):
            segments = line.split('"')
            propname = segments[1]
            idx += 1
            l = xmlContent[idx]
            line = to_str(l).strip("\t").strip(' ').strip('\r\n')
            segments = line.split('"')
            propvalue = segments[1]
            properties[propname] = propvalue
        idx += 1
        if idx == len(xmlContent): break
    
    zip.close()
    
    return shape, vertexNames, edgeNames, faceNames, diffuseColor, properties
#------------------------------------------------------------------------------
def to_bytes(tx):
    if PYVERSION > 2:
        if isinstance(tx, str):
            value = tx.encode("utf-8")
        else:
            value = tx
    else:
        if isinstance(tx,unicode):
            value = tx.encode("utf-8")
        else:
            value = tx
    return value # Instance of bytes
#------------------------------------------------------------------------------
def to_str(tx):
    if PYVERSION > 2:
        if isinstance(tx, bytes):
            value = tx.decode("utf-8")
        else:
            value = tx
    else:
        if isinstance(tx, unicode):
            value = tx
        else:
            value = tx.decode("utf-8")
    return value # Instance of unicode string
#------------------------------------------------------------------------------
def doNotImportInvisibleShapes():
    preferences = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/A2plus")
    return preferences.GetBool('doNotImportInvisibleShapes',True)
#------------------------------------------------------------------------------
def getPerFaceTransparency():
    preferences = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/A2plus")
    return preferences.GetBool('usePerFaceTransparency',False)
#------------------------------------------------------------------------------
def getRecalculateImportedParts():
    preferences = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/A2plus")
    return preferences.GetBool('recalculateImportedParts',False)
#------------------------------------------------------------------------------
def getRecursiveUpdateEnabled():
    preferences = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/A2plus")
    return preferences.GetBool('enableRecursiveUpdate',False)
#------------------------------------------------------------------------------
def getForceFixedPosition():
    preferences = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/A2plus")
    return preferences.GetBool('forceFixedPosition',False)
#------------------------------------------------------------------------------
def getUseSolidUnion():
    preferences = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/A2plus")
    return preferences.GetBool('useSolidUnion',False)
#------------------------------------------------------------------------------
def getConstraintEditorRef():
    global CONSTRAINT_EDITOR__REF
    return CONSTRAINT_EDITOR__REF
#------------------------------------------------------------------------------
def setConstraintEditorRef(ref):
    global CONSTRAINT_EDITOR__REF
    CONSTRAINT_EDITOR__REF = ref
#------------------------------------------------------------------------------
def setConstraintViewMode(active):
    global CONSTRAINT_VIEWMODE 
    CONSTRAINT_VIEWMODE = active
#------------------------------------------------------------------------------
def getConstraintViewMode():
    global CONSTRAINT_VIEWMODE 
    return CONSTRAINT_VIEWMODE
#------------------------------------------------------------------------------
def getConstraintDialogRef():
    global CONSTRAINT_DIALOG_REF
    return CONSTRAINT_DIALOG_REF
#------------------------------------------------------------------------------
def setConstraintDialogRef(ref):
    global CONSTRAINT_DIALOG_REF
    CONSTRAINT_DIALOG_REF = ref
#------------------------------------------------------------------------------
def getUseTopoNaming():
    preferences = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/A2plus")
    return preferences.GetBool('useTopoNaming',False)
#------------------------------------------------------------------------------
def getRelativePathesEnabled():
    global RELATIVE_PATHES_ENABLED
    return RELATIVE_PATHES_ENABLED
#------------------------------------------------------------------------------
def setAutoSolve(enabled):
    global AUTOSOLVE_ENABLED
    AUTOSOLVE_ENABLED = enabled
#------------------------------------------------------------------------------
def getAutoSolveState():
    return AUTOSOLVE_ENABLED
#------------------------------------------------------------------------------
def setPartialProcessing(enabled):
    global PARTIAL_PROCESSING_ENABLED
    PARTIAL_PROCESSING_ENABLED = enabled
#------------------------------------------------------------------------------
def isPartialProcessing():
    return PARTIAL_PROCESSING_ENABLED
#------------------------------------------------------------------------------
def filterShapeObs(_list):
    lst = []
    for ob in _list:
        if ob.hasExtension('App::GeoFeatureGroupExtension'):continue #Part Containers within FC0.19.18405 seem to have a shape property..
        if hasattr(ob,"Shape"):
            if len(ob.Shape.Faces) > 0 and len(ob.Shape.Vertexes) > 0:
                lst.append(ob)
    S = set(lst)
    lst = []
    lst.extend(S)
    return lst
#------------------------------------------------------------------------------
def setTransparency():
    global SAVED_TRANSPARENCY
    # Save Transparency of Objects and make all transparent
    doc = FreeCAD.ActiveDocument

    if len(SAVED_TRANSPARENCY) > 0:
        # Transparency is already saved, no need to set transparency again
        return

    shapedObs = filterShapeObs(doc.Objects) # filter out partlist, spreadsheets etc..
    sel = FreeCADGui.Selection

    for obj in shapedObs:
        if hasattr(obj,'ViewObject'):                                # save "all-in" *MK
            if hasattr(obj.ViewObject,'DiffuseColor'):
                SAVED_TRANSPARENCY.append(
                    (obj.Name, obj.ViewObject.Transparency, obj.ViewObject.ShapeColor, obj.ViewObject.DiffuseColor)
                )
            else:
                SAVED_TRANSPARENCY.append(
                    (obj.Name, obj.ViewObject.Transparency, obj.ViewObject.ShapeColor, None)
                )

        obj.ViewObject.Transparency = 80
        sel.addSelection(obj) # Transparency workaround. Transparency is taken when once been selected
        sel.clearSelection()
#------------------------------------------------------------------------------
def restoreTransparency():
    global SAVED_TRANSPARENCY
    # restore transparency of objects...
    doc = FreeCAD.ActiveDocument

    sel = FreeCADGui.Selection

    for setting in SAVED_TRANSPARENCY:
        obj = doc.getObject(setting[0])
        if obj is not None:                                          # restore "all-in" *MK
            obj.ViewObject.Transparency = setting[1]
            obj.ViewObject.ShapeColor = setting[2]
            obj.ViewObject.DiffuseColor = setting[3]                 # diffuse always at last
            sel.addSelection(obj)
            sel.clearSelection()

    SAVED_TRANSPARENCY = []
#------------------------------------------------------------------------------
def isTransparencyEnabled():
    global SAVED_TRANSPARENCY
    return (len(SAVED_TRANSPARENCY) > 0)
#------------------------------------------------------------------------------
def getSelectedConstraint():
    # Check that constraint is selected
    selection = [s for s in FreeCADGui.Selection.getSelection() if s.Document == FreeCAD.ActiveDocument ]
    if len(selection) == 0: return None
    connectionToView = selection[0]

    if not 'ConstraintInfo' in connectionToView.Content and not 'ConstraintNfo' in connectionToView.Content:
        return None

    return connectionToView
#------------------------------------------------------------------------------
def appVersionStr():
    version = int(FreeCAD.Version()[0])
    subVersion = int(float(FreeCAD.Version()[1]))
    return "%03d.%03d" %(version,subVersion)
#------------------------------------------------------------------------------
def numpyVecToFC(nv):
    assert len(nv) == 3
    return Base.Vector(nv[0],nv[1],nv[2])
#------------------------------------------------------------------------------
def fit_plane_to_surface1( surface, n_u=3, n_v=3 ):
    uv = sum( [ [ (u,v) for u in numpy.linspace(0,1,n_u)] for v in numpy.linspace(0,1,n_v) ], [] )
    P = [ surface.value(u,v) for u,v in uv ] #positions at u,v points
    N = [ numpy.cross( *surface.tangent(u,v) ) for u,v in uv ] 
    plane_norm = sum(N) / len(N) #plane's normal, averaging done to reduce error
    plane_pos = P[0]
    error = sum([ abs( numpy.dot(p - plane_pos, plane_norm) ) for p in P ])
    return numpyVecToFC(plane_norm), numpyVecToFC(plane_pos), error
#------------------------------------------------------------------------------
def isLine(param):
    if hasattr(Part,"LineSegment"):
        return isinstance(param,(Part.Line,Part.LineSegment))
    else:
        return isinstance(param,Part.Line)
#------------------------------------------------------------------------------
def getObjectFaceFromName( obj, faceName ):
    assert faceName.startswith('Face')
    ind = int( faceName[4:]) -1
    return obj.Shape.Faces[ind]
#------------------------------------------------------------------------------
def getProjectFolder():
    '''
    #------------------------------------------------------------------------------------
    # A new Parameter is required: projectFolder...
    # All Parts will be searched below this projectFolder-Value...
    #------------------------------------------------------------------------------------
    '''
    preferences = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/A2plus")
    if not preferences.GetBool('useProjectFolder', False): return ""
    return preferences.GetString('projectFolder', '~')

#------------------------------------------------------------------------------
def pathToOS(path):
    if path == None: return None
    p = to_str(path)
    if OPERATING_SYSTEM == 'WINDOWS':
        p = p.replace(u'/',u'\\')
    else:
        p = p.replace(u'\\',u'/')
    return p # unicode string

#------------------------------------------------------------------------------
def findFile(_name, _path):
    '''
    Searches a file within a directory and it's subdirectories
    '''
    name = to_str(_name)
    path = to_str(_path)
    for root, dirs, files in os.walk(path):
        if name in files:
            return os.path.join(root, name)
    return None
            
#------------------------------------------------------------------------------
def findSourceFileInProject(_pathImportPart, _assemblyPath):
    '''
    #------------------------------------------------------------------------------------
    # interpret the sourcefile name of imported part
    # if working with preference "useProjectFolder:
    # - path of sourcefile is ignored
    # - filename is looked up beneath projectFolder
    #
    # if not working with preference "useProjectFolder":
    # - path of sourcefile is checked for being relative to assembly or absolute
    # - path is interpreted in appropriate way
    #------------------------------------------------------------------------------------
    '''
    pathImportPart = _pathImportPart
    assemblyPath = _assemblyPath
    
    pathImportPart = to_bytes(pathImportPart)
    assemblyPath = to_bytes(assemblyPath)
    
    preferences = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/A2plus")
    if not preferences.GetBool('useProjectFolder', False): 
        # not working with useProjectFolder preference,
        # check whether path is relative or absolute...
        if (
            pathImportPart.startswith(b'../') or
            pathImportPart.startswith(b'..\\') or
            pathImportPart.startswith(b'./') or
            pathImportPart.startswith(b'.\\')
            ):
            # relative path
            # calculate the absolute path
            p1 = to_str(assemblyPath)
            p2 = to_str(pathImportPart)
            joinedPath = os.path.join(p1,p2)
            
            absolutePath = os.path.normpath(joinedPath)
            absolutePath = pathToOS(absolutePath)
            return to_str(absolutePath)
        else:
            pathImportPart = pathToOS(pathImportPart)
            return to_str(pathImportPart)

    projectFolder = os.path.abspath(getProjectFolder()) # get normalized path
    fileName = os.path.basename(pathImportPart)
    retval = findFile(fileName,projectFolder)
    retval = pathToOS(retval)
    if retval:
        return to_str(retval)
    else:
        return None
#------------------------------------------------------------------------------
def checkFileIsInProjectFolder(path):
    preferences = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/A2plus")
    if not preferences.GetBool('useProjectFolder', False): return True

    projectFolder = os.path.abspath(getProjectFolder()) # get normalized path
    fileName = os.path.basename(path)
    nameInProject = findFile(fileName,projectFolder)
    
    if nameInProject == path:
        return True
    else:
        return False

#------------------------------------------------------------------------------
def pathOfModule():
    return os.path.dirname(__file__)

#------------------------------------------------------------------------------
def Msg(tx):
    FreeCAD.Console.PrintMessage(tx)

#------------------------------------------------------------------------------
def DebugMsg(level, tx):
    if A2P_DEBUG_LEVEL >= level:
        FreeCAD.Console.PrintMessage(tx)

#------------------------------------------------------------------------------
def drawSphere(center, color):
    doc = FreeCAD.ActiveDocument
    s = Part.makeSphere(2.0,center)
    sphere = doc.addObject("Part::Feature","Sphere")
    sphere.Shape = s
    sphere.ViewObject.ShapeColor = color
    doc.recompute()
#------------------------------------------------------------------------------
def drawVector(fromPoint,toPoint, color):
    if fromPoint == toPoint: return
    doc = FreeCAD.ActiveDocument

    l = Part.LineSegment()
    l.StartPoint = fromPoint
    l.EndPoint = toPoint
    line = doc.addObject("Part::Feature","Line")
    line.Shape = l.toShape()
    line.ViewObject.LineColor = color
    line.ViewObject.LineWidth = 1

    
    c = Part.makeCone(0,1,4)
    cone = doc.addObject("Part::Feature","ArrowHead")
    cone.Shape = c
    cone.ViewObject.ShapeColor = color
    #
    mov = Base.Vector(0,0,0)
    zAxis = Base.Vector(0,0,-1)
    rot = FreeCAD.Rotation(zAxis,toPoint.sub(fromPoint))
    cent = Base.Vector(0,0,0)
    conePlacement = FreeCAD.Placement(mov,rot,cent)
    cone.Placement = conePlacement.multiply(cone.Placement)
    cone.Placement.move(toPoint)
    doc.recompute()
#------------------------------------------------------------------------------
def findUnusedObjectName(base, counterStart=1, fmt='%03i', document=None):
    if document == None:
        document = FreeCAD.ActiveDocument
    i = counterStart
    usedNames = [ obj.Name for obj in document.Objects ]

    if base[-4:-3] == '_':
        base2 = base[:-4]
    else:
        base2 = base
    base2 = base2 + '_'

    objName = '%s%s' % (base2, fmt%i)
    while objName in usedNames:
        i += 1
        objName = '%s%s' % (base2, fmt%i)
    return objName

#------------------------------------------------------------------------------
def findUnusedObjectLabel(base, counterStart=1, fmt='%03i', document=None):
    if document == None:
        document = FreeCAD.ActiveDocument
    i = counterStart
    usedLabels = [ obj.Label for obj in document.Objects ]

    if base[-4:-3] == '_':
        base2 = base[:-4]
    else:
        base2 = base
    base2 = base2 + '_'

    objLabel = '%s%s' % (base2, fmt%i)
    while objLabel in usedLabels:
        i += 1
        objLabel = '%s%s' % (base2, fmt%i)
    return objLabel

#------------------------------------------------------------------------------
class ConstraintSelectionObserver:

    def __init__(self, selectionGate, parseSelectionFunction,
                  taskDialog_title, taskDialog_iconPath, taskDialog_text,
                  secondSelectionGate=None):
        self.selections = []
        self.parseSelectionFunction = parseSelectionFunction
        self.secondSelectionGate = secondSelectionGate
        FreeCADGui.Selection.addObserver(self)
        FreeCADGui.Selection.removeSelectionGate()
        FreeCADGui.Selection.addSelectionGate( selectionGate )
        wb_globals['selectionObserver'] = self
        self.taskDialog = SelectionTaskDialog(taskDialog_title, taskDialog_iconPath, taskDialog_text)
        FreeCADGui.Control.showDialog( self.taskDialog )

    def addSelection( self, docName, objName, sub, pnt ):
        self.selections.append( SelectionRecord( docName, objName, sub ))
        if len(self.selections) == 2:
            self.stopSelectionObservation()
            self.parseSelectionFunction( self.selections)
        elif self.secondSelectionGate != None and len(self.selections) == 1:
            FreeCADGui.Selection.removeSelectionGate()
            FreeCADGui.Selection.addSelectionGate( self.secondSelectionGate )

    def stopSelectionObservation(self):
        FreeCADGui.Selection.removeObserver(self)
        del wb_globals['selectionObserver']
        FreeCADGui.Selection.removeSelectionGate()
        FreeCADGui.Control.closeDialog()

#------------------------------------------------------------------------------
class SelectionRecord:
    def __init__(self, docName, objName, sub):
        self.Document = FreeCAD.getDocument(docName)
        self.ObjectName = objName
        self.Object = self.Document.getObject(objName)
        self.SubElementNames = [sub]

#------------------------------------------------------------------------------
class SelectionTaskDialog:

    def __init__(self, title, iconPath, textLines ):
        self.form = SelectionTaskDialogForm( textLines )
        self.form.setWindowTitle( title )
        if iconPath != None:
            self.form.setWindowIcon( QtGui.QIcon( iconPath ) )

    def reject(self):
        wb_globals['selectionObserver'].stopSelectionObservation()

    def getStandardButtons(self): #http://forum.freecadweb.org/viewtopic.php?f=10&t=11801
        return 0x00400000 #cancel button
#------------------------------------------------------------------------------
class SelectionTaskDialogForm(QtGui.QWidget):

    def __init__(self, textLines ):
        super(SelectionTaskDialogForm, self).__init__()
        self.textLines = textLines
        self.initUI()

    def initUI(self):
        vbox = QtGui.QVBoxLayout()
        for line in self.textLines.split('\n'):
            vbox.addWidget( QtGui.QLabel(line) )
        self.setLayout(vbox)

#------------------------------------------------------------------------------
class SelectionExObject:
    'allows for selection gate functions to interface with classification functions below'
    def __init__(self, doc, Object, subElementName):
        self.doc = doc
        self.Object = Object
        self.ObjectName = Object.Name
        self.SubElementNames = [subElementName]
#------------------------------------------------------------------------------
def getObjectEdgeFromName( obj, name ):
    assert name.startswith('Edge')
    ind = int( name[4:]) -1
    return obj.Shape.Edges[ind]
#------------------------------------------------------------------------------
def CircularEdgeSelected( selection ):
    if len( selection.SubElementNames ) == 1:
        subElement = selection.SubElementNames[0]
        if subElement.startswith('Edge'):
            edge = getObjectEdgeFromName( selection.Object, subElement)
            if not hasattr(edge, 'Curve'): #issue 39
                return False
            if hasattr( edge.Curve, 'Radius' ):
                return True
    return False
#------------------------------------------------------------------------------
def ClosedEdgeSelected( selection ):
    if len( selection.SubElementNames ) == 1:
        subElement = selection.SubElementNames[0]
        if subElement.startswith('Edge'):
            edge = getObjectEdgeFromName( selection.Object, subElement)
            if edge.isClosed():
                return True
            else:
                return False
    return False
#------------------------------------------------------------------------------
def AxisOfPlaneSelected( selection ): #adding Planes/Faces selection for Axial constraints
    if len( selection.SubElementNames ) == 1:
        subElement = selection.SubElementNames[0]
        if subElement.startswith('Face'):
            face = getObjectFaceFromName( selection.Object, subElement)
            if str(face.Surface) == '<Plane object>':
                return True
    return False
#------------------------------------------------------------------------------
def printSelection(selection):
    entries = []
    for s in selection:
        for e in s.SubElementNames:
            entries.append(' - %s:%s' % (s.ObjectName, e))
            if e.startswith('Face'):
                ind = int( e[4:]) -1
                face = s.Object.Shape.Faces[ind]
                entries[-1] = entries[-1] + ' %s' % str(face.Surface)
    return '\n'.join( entries[:5] )
#------------------------------------------------------------------------------
def updateObjectProperties( c ):
    return
    '''
    if c.Type == 'axial' or c.Type == 'circularEdge':
        if not hasattr(c, 'lockRotation'):
            c.addProperty("App::PropertyBool","lockRotation","ConstraintInfo")
    '''
#------------------------------------------------------------------------------
def planeSelected( selection ):
    if len( selection.SubElementNames ) == 1:
        subElement = selection.SubElementNames[0]
        if subElement.startswith('Face'):
            face = getObjectFaceFromName( selection.Object, subElement)
            if str(face.Surface) == '<Plane object>':
                return True
            elif str(face.Surface) == '<BSplineSurface object>':
                normal,pos,error = fit_plane_to_surface1(face.Surface)
                if abs(error) < 1e-9:
                    return True
    return False
#------------------------------------------------------------------------------
def vertexSelected( selection ):
    if len( selection.SubElementNames ) == 1:
        return selection.SubElementNames[0].startswith('Vertex')
    return False
#------------------------------------------------------------------------------
def cylindricalFaceSelected( selection ):
    if len( selection.SubElementNames ) == 1:
        subElement = selection.SubElementNames[0]
        if subElement.startswith('Face'):
            face = getObjectFaceFromName( selection.Object, subElement)
            if hasattr(face.Surface,'Radius'):
                return True
            elif str(face.Surface).startswith('<SurfaceOfRevolution'):
                return True
    return False
#------------------------------------------------------------------------------
def LinearEdgeSelected( selection ):
    if len( selection.SubElementNames ) == 1:
        subElement = selection.SubElementNames[0]
        if subElement.startswith('Edge'):
            edge = getObjectEdgeFromName( selection.Object, subElement)
            if not hasattr(edge, 'Curve'): #issue 39
                return False
            if isLine(edge.Curve):
                return True
    return False
#------------------------------------------------------------------------------
def sphericalSurfaceSelected( selection ):
    if len( selection.SubElementNames ) == 1:
        subElement = selection.SubElementNames[0]
        if subElement.startswith('Face'):
            face = getObjectFaceFromName( selection.Object, subElement)
            return str( face.Surface ).startswith('Sphere ')
    return False
#------------------------------------------------------------------------------
def getObjectVertexFromName( obj, name ):
    assert name.startswith('Vertex')
    ind = int( name[6:]) -1
    return obj.Shape.Vertexes[ind]
#------------------------------------------------------------------------------
def removeConstraint( constraint ):
    'required as constraint.Proxy.onDelete only called when deleted through GUI'
    doc = constraint.Document
    if constraint.ViewObject != None:
        constraint.ViewObject.Proxy.onDelete( constraint.ViewObject, None ) # also removes mirror...
    doc.removeObject( constraint.Name )
#------------------------------------------------------------------------------
def getPos(obj, subElementName):
    pos = None
    if subElementName.startswith('Face'):
        face = getObjectFaceFromName(obj, subElementName)
        surface = face.Surface
        if str(surface) == '<Plane object>':
            pos = getObjectFaceFromName(obj, subElementName).Faces[0].BoundBox.Center
            # axial constraint for Planes
            # pos = surface.Position
        elif str(surface) == "<Cylinder object>":
            pos = surface.Center
        elif all( hasattr(surface,a) for a in ['Axis','Center','Radius'] ):
            pos = surface.Center
        elif str(surface).startswith('<SurfaceOfRevolution'):
            pos = getObjectFaceFromName(obj, subElementName).Edges[0].Curve.Center
        elif str(surface).startswith('<BSplineSurface'):
            axis,pos,error = fit_plane_to_surface1(surface)
    elif subElementName.startswith('Edge'):
        edge = getObjectEdgeFromName(obj, subElementName)
        if isLine(edge.Curve):
            if appVersionStr() <= "000.016":
                pos = edge.Curve.StartPoint
            else:
                pos = edge.firstVertex(True).Point
        elif hasattr( edge.Curve, 'Center'): #circular curve
            pos = edge.Curve.Center
    elif subElementName.startswith('Vertex'):
        return  getObjectVertexFromName(obj, subElementName).Point
    return pos # maybe none !!
#------------------------------------------------------------------------------
def getPlaneNormal(surface):
    axis = None
    if hasattr(surface,'Axis'):
        axis = surface.Axis
    elif str(surface).startswith('<BSplineSurface'):
        axis,pos,error = fit_plane_to_surface1(surface)
    return axis # may be none!
#------------------------------------------------------------------------------
def getAxis(obj, subElementName):
    axis = None
    if subElementName.startswith('Face'):
        face = getObjectFaceFromName(obj, subElementName)
        surface = face.Surface
        if hasattr(surface,'Axis'):
            axis = surface.Axis
        elif str(surface).startswith('<SurfaceOfRevolution'):
            axis = face.Edges[0].Curve.Axis
        elif str(surface).startswith('<BSplineSurface'):
            axis,pos,error = fit_plane_to_surface1(surface)
            
    elif subElementName.startswith('Edge'):
        edge = getObjectEdgeFromName(obj, subElementName)
        if isLine(edge.Curve):
            axis = edge.Curve.tangent(0)[0]
        elif hasattr( edge.Curve, 'Axis'): #circular curve
            axis =  edge.Curve.Axis
    return axis # may be none!
#------------------------------------------------------------------------------
def isA2pPart(obj):
    result = False
    if hasattr(obj,"Content"):
        if 'importPart' in obj.Content:
            result = True
    elif hasattr(obj,"a2p_Version"):          # keep old assembly item identification in,
        result = True                         #  -> otherwise toggle transparency won't work
    elif hasattr(obj,"subassemblyImport"):    # another possible assembly item
        result = True
    elif hasattr(obj,"assembly2Version"):    # another possible assembly item (very old a2p versions)
        result = True
    return result
#------------------------------------------------------------------------------
def isEditableA2pPart(obj):
    if not isA2pPart(obj): return False
    if hasattr(obj,"sourceFile"):
        if obj.sourceFile == "converted": return False
        if obj.sourceFile == "": return False
    return True
#------------------------------------------------------------------------------
def isA2pConstraint(obj): 
    result = False
    if hasattr(obj,"Content"):
        if ('ConstraintInfo' in obj.Content) or ('ConstraintNfo'in obj.Content):
            result = True
    return result
#------------------------------------------------------------------------------
def isA2pObject(obj):
    result = False
    if isA2pPart(obj) or isA2pConstraint(obj):
        result = True
    return result
#------------------------------------------------------------------------------
def makeDiffuseElement(color,trans):
    return (color[0],color[1],color[2],trans/100.0)
#------------------------------------------------------------------------------
def diffuseElementFromTextline(line):
    values = to_str(line).split(' ')
    diffuseElement = []
    for val in values:
        diffuseElement.append(float(val.strip("\r\n")))
    return tuple(diffuseElement)
#------------------------------------------------------------------------------
def diffuseElementToTextline(elem):
    if len(elem) == 3:
        return '%0.5f %0.5f %0.5f\r\n' % (elem[0],elem[1],elem[2])
    else:
        return '%0.5f %0.5f %0.5f %0.5f\r\n' % (elem[0],elem[1],elem[2],elem[3])
#------------------------------------------------------------------------------
def copyObjectColors(ob1,ob2):
    '''
    copies colors from ob2 to ob1
    Transparency of updated object is not touched until
    user activates perFaceTransparency within preferences.
    '''
    if ob1.updateColors != True:
        ob1.ViewObject.DiffuseColor = [ob1.ViewObject.ShapeColor] # set syncron
        return
    
    # obj1.updateColors == True from now
    newDiffuseColor = copy.copy(ob2.ViewObject.DiffuseColor)
    ob1.ViewObject.ShapeColor = ob2.ViewObject.ShapeColor
    ob1.ViewObject.DiffuseColor = newDiffuseColor # set diffuse last

    if not getPerFaceTransparency():
        # touch transparency one to trigger update of 3D View
        # per face transparency probably gets lost
        if ob1.ViewObject.Transparency > 0:
            t = ob1.ViewObject.Transparency
            ob1.ViewObject.Transparency = 0
            ob1.ViewObject.Transparency = t
        else:
            ob1.ViewObject.Transparency = 1
            ob1.ViewObject.Transparency = 0

    # select/deselect object once to trigger update of 3D View
    FreeCADGui.Selection.addSelection(ob1)
    FreeCADGui.Selection.removeSelection(ob1)
#------------------------------------------------------------------------------
def isConstrainedPart(doc,obj):
    if not isA2pPart(obj): return False
    constraints = [ ob for ob in doc.Objects if 'ConstraintInfo' in ob.Content]
    for c in constraints:
        if c.Object1 == obj.Name:
            return True
        if c.Object2 == obj.Name:
            return True
    return False
#------------------------------------------------------------------------------
def objectExists(name):
    doc = FreeCAD.activeDocument()
    try:
        ob = doc.getObject(name)
        if ob != None: return True
    except:
        pass
    return False
#------------------------------------------------------------------------------
def deleteConstraintsOfDeletedObjects():
    doc = FreeCAD.activeDocument()
    deleteList = []
    missingObjects = []
    for c in doc.Objects:
        if 'ConstraintInfo' in c.Content:
            if not objectExists(c.Object1):
                deleteList.append(c)
                missingObjects.append(c.Object1)
                continue
            if not objectExists(c.Object2):
                deleteList.append(c)
                missingObjects.append(c.Object2)
    if len(deleteList) != 0:
        for c in deleteList:
            removeConstraint(c)

        missingObjects = set(missingObjects)
    
        msg = u"Not existing part(s):\n  - {}".format(
            u'\n  - '.join( objName for objName in missingObjects)
            )
        QtGui.QMessageBox.information(
            QtGui.QApplication.activeWindow(), 
            u"Constraints of missing parts removed!", 
            msg 
            )
#------------------------------------------------------------------------------
def a2p_repairTreeView():
    doc = FreeCAD.activeDocument()
    if doc == None: return
    
    deleteConstraintsOfDeletedObjects()

    constraints = [ obj for obj in doc.Objects if 'ConstraintInfo' in obj.Content]
    for c in constraints:
        if c.Proxy != None:
            c.Proxy.disable_onChanged = True
        if not hasattr(c,"ParentTreeObject"):
            c.addProperty("App::PropertyLink","ParentTreeObject","ConstraintInfo")
            c.setEditorMode("ParentTreeObject", 1)
        parent = doc.getObject(c.Object1)
        c.ParentTreeObject = parent
        parent.Label = parent.Label # trigger an update...
        if c.Proxy != None:
            c.Proxy.disable_onChanged = False
    #
    mirrors = [ obj for obj in doc.Objects if 'ConstraintNfo' in obj.Content]
    for m in mirrors:
        if m.Proxy != None:
            m.Proxy.disable_onChanged = True
        if not hasattr(m,"ParentTreeObject"):
            m.addProperty("App::PropertyLink","ParentTreeObject","ConstraintNfo")
            m.setEditorMode("ParentTreeObject", 1)
        parent = doc.getObject(m.Object2)
        m.ParentTreeObject = parent
        parent.Label = parent.Label # trigger an update...
        if m.Proxy != None:
            m.Proxy.disable_onChanged = False
#------------------------------------------------------------------------------
