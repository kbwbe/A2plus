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
import numpy, os
from a2p_viewProviderProxies import *
from  FreeCAD import Base


preferences = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/A2plus")

USE_PROJECTFILE = preferences.GetBool('useProjectFolder', False)
PARTIAL_PROCESSING_ENABLED = preferences.GetBool('usePartialSolver', True)
AUTOSOLVE_ENABLED = preferences.GetBool('autoSolve', True)

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

A2P_DEBUG_LEVEL = A2P_DEBUG_NONE


#------------------------------------------------------------------------------
def setAutoSolve(enabled):
    global AUTOSOLVE_ENABLED
    AUTOSOLVE_ENABLED = enabled
    #preferences = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/A2plus")
    #preferences.SetBool('autoSolve', enabled)
#------------------------------------------------------------------------------
def getAutoSolveState():
    return AUTOSOLVE_ENABLED
#------------------------------------------------------------------------------
def setPartialProcessing(enabled):
    global PARTIAL_PROCESSING_ENABLED
    PARTIAL_PROCESSING_ENABLED = enabled
    #preferences = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/A2plus")
    #preferences.SetBool('usePartialSolver', enabled)
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
                SAVED_TRANSPARENCY.append((obj.Name, obj.ViewObject.Transparency))
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

    doc = FreeCAD.ActiveDocument
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
def findSourceFileInProject(fullPath):
    '''
    #------------------------------------------------------------------------------------
    # function to find filename in projectFolder
    # The path stored in an imported Part will be ignored
    # Assemblies will become better movable in filesystem...
    #------------------------------------------------------------------------------------
    '''
    preferences = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/A2plus")
    if not preferences.GetBool('useProjectFolder', False): return fullPath

    def findFile(name, path):
        for root, dirs, files in os.walk(path):
            if name in files:
                return os.path.join(root, name)

    projectFolder = os.path.abspath(getProjectFolder()) # get normalized path
    fileName = os.path.basename(fullPath)
    retval = findFile(fileName,projectFolder)
    DebugMsg(A2P_DEBUG_1,
        "Found file {}\n".format(retval)
        )
    return retval

#------------------------------------------------------------------------------
def checkFileIsInProjectFolder(path):
    preferences = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/A2plus")
    if not preferences.GetBool('useProjectFolder', False): return True

    nameInProject = findSourceFileInProject(path)
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
def drawVector(fromPoint,toPoint, color):
    if fromPoint == toPoint: return
    doc = FreeCAD.ActiveDocument

    l = Part.Line(fromPoint,toPoint)
    line = doc.addObject("Part::Feature","ArrowTail")
    line.Shape = l.toShape()
    line.ViewObject.LineColor = color
    line.ViewObject.LineWidth = 6
    #doc.recompute()
    c = Part.makeCone(0,1,4)
    cone = doc.addObject("Part::Feature","ArrowHead")
    cone.Shape = c
    cone.ViewObject.ShapeColor = (1.0,0.0,0.0)
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
        obj = FreeCAD.ActiveDocument.getObject(objName)
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
    if constraint.ViewObject != None: #do not this check is actually nessary ...
        constraint.ViewObject.Proxy.onDelete( constraint.ViewObject, None )
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
