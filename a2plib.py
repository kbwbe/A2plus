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

import FreeCAD, FreeCADGui, Part
from PySide import QtGui, QtCore
import numpy, os, sys
from a2p_viewProviderProxies import *
from  FreeCAD import Base

PYVERSION =  sys.version_info[0]

preferences = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/A2plus")

USE_PROJECTFILE = preferences.GetBool('useProjectFolder', False)
PARTIAL_PROCESSING_ENABLED = preferences.GetBool('usePartialSolver', True)
AUTOSOLVE_ENABLED = preferences.GetBool('autoSolve', True)
RELATIVE_PATHES_ENABLED = preferences.GetBool('useRelativePathes',True)

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

# DEFINE DEBUG LEVELS FOR CONSOLE OUTPUT
A2P_DEBUG_NONE      = 0
A2P_DEBUG_1         = 1
A2P_DEBUG_2         = 2
A2P_DEBUG_3         = 3

A2P_DEBUG_LEVEL = A2P_DEBUG_3

PARTIAL_SOLVE_STAGE1 = 1    #solve all rigid fully constrained to tempfixed rigid, enable only involved dep, then set them as tempfixed
PARTIAL_SOLVE_STAGE2 = 2    #solve all rigid constrained only to tempfixed rigids, it doesn't matter if fully constrained or not. 
                            #in case more than one tempfixed rigid
PARTIAL_SOLVE_STAGE3 = 3    #repeat stage 1 and stage2 as there are rigids that match
PARTIAL_SOLVE_STAGE4 = 4    #look for block of rigids, if a rigid is fully constrained to one rigid, solve them and create a superrigid (disabled at the moment)
PARTIAL_SOLVE_STAGE5 = 5    #take all remaining rigid and dependencies not done and try to solve them all together
PARTIAL_SOLVE_END = 6


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
def setTransparency():
    global SAVED_TRANSPARENCY
    # Save Transparency of Objects and make all transparent
    doc = FreeCAD.ActiveDocument

    if len(SAVED_TRANSPARENCY) > 0:
        # Transparency is already saved, no need to set transparency again
        return

    for obj in doc.Objects:
        if hasattr(obj,'ViewObject'):
            if hasattr(obj.ViewObject,'Transparency'):
#                if hasattr(obj.ViewObject,'DiffuseColor'):
                if ( len(obj.ViewObject.DiffuseColor) == 1 ) :
                    DebugMsg(A2P_DEBUG_3,"a2p setTransparency:  ONE ShapeColor and Transparency detected:\n{}" \
                        .format(obj.ViewObject.DiffuseColor))
                else:
                    DebugMsg(A2P_DEBUG_3,"a2p setTransparency: muxed assembly detected:\n{}" \
                       .format(obj.ViewObject.DiffuseColor))
                DebugMsg(A2P_DEBUG_3,"A2P setTransparency: Saving transparency!\n")
                SAVED_TRANSPARENCY.append(
                    (obj.Name, obj.ViewObject.Transparency, obj.ViewObject.DiffuseColor)
                    )
                obj.ViewObject.Transparency = 80
#------------------------------------------------------------------------------
def restoreTransparency():
    global SAVED_TRANSPARENCY
    # restore transparency of objects...
    doc = FreeCAD.ActiveDocument

    for setting in SAVED_TRANSPARENCY:
        obj = doc.getObject(setting[0])
        if obj is not None:
            obj.ViewObject.Transparency = setting[1]
            obj.ViewObject.DiffuseColor = setting[2]
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
    subVersion = int(FreeCAD.Version()[1])
    return "%03d.%03d" %(version,subVersion)
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
def findFile(name, path):
    '''
    Searches a file within a directory and it's subdirectories
    '''
    for root, dirs, files in os.walk(path):
        if PYVERSION < 3:
            if name.encode('utf-8') in files:
                return os.path.join(root, name)
        else:
            if name in files:
                return os.path.join(root, name)
#------------------------------------------------------------------------------
def findSourceFileInProject(pathImportPart, assemblyPath):
    '''
    #------------------------------------------------------------------------------------
    # interprete the sourcefile name of imported part
    # if working with preference "useProjectFolder:
    # - path of sourcefile is ignored
    # - filename is looked up beneath projectFolder
    #
    # if not working with preference "useProjectFolder":
    # - path of sourcefile is checked for being relative to assembly or absolute
    # - path is interpreted in appropiate way
    #------------------------------------------------------------------------------------
    '''
    preferences = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/A2plus")
    if not preferences.GetBool('useProjectFolder', False): 
        # not working with useProjectFolder preference,
        # check wether path is relative or absolute...
        if (
            pathImportPart.startswith('../') or
            pathImportPart.startswith('..\\') or
            pathImportPart.startswith('./') or
            pathImportPart.startswith('.\\')
            ):
            # relative path
            # calculate the absolute path
            absolutePath = os.path.normpath(  os.path.join(assemblyPath,pathImportPart) )
            return absolutePath
        else:
            #absolute path
            return pathImportPart

    projectFolder = os.path.abspath(getProjectFolder()) # get normalized path
    fileName = os.path.basename(pathImportPart)
    retval = findFile(fileName,projectFolder)
    return retval
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
    return False
#------------------------------------------------------------------------------
def vertexSelected( selection ):
    if len( selection.SubElementNames ) == 1:
        return selection.SubElementNames[0].startswith('Vertex')
    return False
#------------------------------------------------------------------------------
def cylindricalPlaneSelected( selection ):
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
def getAxis(obj, subElementName):
    axis = None
    if subElementName.startswith('Face'):
        face = getObjectFaceFromName(obj, subElementName)
        surface = face.Surface
        if hasattr(surface,'Axis'):
            axis = surface.Axis
        elif str(surface).startswith('<SurfaceOfRevolution'):
            axis = face.Edges[0].Curve.Axis
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
    return result

def isA2pConstraint(obj): 
    result = False
    if hasattr(obj,"Content"):
        if ('ConstraintInfo' in obj.Content) or ('ConstraintNfo'in obj.Content):
            result = True
    return result

def isA2pObject(obj):
    result = False
    if isA2pPart(obj) or isA2pConstraint(obj):
        result = True
    return result
#------------------------------------------------------------------------------

