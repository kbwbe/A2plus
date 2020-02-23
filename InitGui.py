# -*- coding: utf-8 -*-
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

__title__ = 'A2plus assembly Workbench - InitGui file'
__author__ = 'kbwbe'

A2P_VERSION = 'V0.4.44'



import sys
PyVersion = sys.version_info[0]
if PyVersion == 2:
    import a2p_Resources2
else:
    import a2p_Resources3


class A2plusWorkbench (Workbench):

    def __init__(self):
        global A2P_VERSION
        import a2plib
        self.__class__.Icon = a2plib.pathOfModule() + "/icons/a2p_Workbench.svg"
        self.__class__.MenuText = 'A2plus '+A2P_VERSION
        self.__class__.ToolTip  = 'An other assembly workbench for FreeCAD.'

    def Initialize(self):
        import sys
        PyVersion = sys.version_info[0]
        if PyVersion == 2:
            import a2p_Resources2
        else:
            import a2p_Resources3
        import a2plib
        import a2p_importpart
        import a2p_recursiveUpdatePlanner
        import a2p_convertPart
        import a2p_solversystem
        import a2p_MuxAssembly
        import a2p_partinformation
        import a2p_constraintDialog
        import a2p_constraintcommands
        import a2p_bom # bom == bill of materials == partslist

        if a2plib.getRecursiveUpdateEnabled():
            partCommands = [
                'a2p_ImportPart',
                'a2p_ImportShapeReferenceCommand',
                'a2p_updateImportedParts',
                'a2p_recursiveUpdateImportedPartsCommand',
                'a2p_movePart',
                'a2p_MovePartUnderConstraints',
                'a2p_duplicatePart',
                'a2p_ConvertPart',
                'a2p_editImportedPart',
                'a2p_SaveAndExit_Command',
                ]
        else:
            partCommands = [
                'a2p_ImportPart',
                'a2p_ImportShapeReferenceCommand',
                'a2p_updateImportedParts',
                'a2p_movePart',
                'a2p_MovePartUnderConstraints',
                'a2p_duplicatePart',
                'a2p_ConvertPart',
                'a2p_editImportedPart',
                'a2p_SaveAndExit_Command',
                ]
        
        if a2plib.SHOW_CONSTRAINTS_ON_TOOLBAR:
            constraintCommands = [
                'a2p_ConstraintDialogCommand',
                'a2p_EditConstraintCommand',
                'a2p_DeleteConnectionsCommand',
                'a2p_PointIdentityConstraintCommand',
                'a2p_PointOnLineConstraintCommand',
                'a2p_PointOnPlaneConstraintCommand',
                'a2p_SphericalSurfaceConstraintCommand',
                'a2p_CircularEdgeConnection',
                'a2p_AxialConstraintCommand',
                'a2p_AxisParallelConstraintCommand',
                'a2p_AxisPlaneParallelCommand',
                'a2p_AxisPlaneNormalCommand',
                'a2p_AxisPlaneAngleCommand',
                'a2p_PlanesParallelConstraintCommand',
                'a2p_PlaneCoincidentConstraintCommand',
                'a2p_AngledPlanesConstraintCommand',
                'a2p_CenterOfMassConstraintCommand',
                ]
        else:
            constraintCommands = [
                'a2p_ConstraintDialogCommand',
                'a2p_EditConstraintCommand',
                'a2p_DeleteConnectionsCommand',
                ]
        
        solverCommands = [
            'a2p_SolverCommand',
            'a2p_ToggleAutoSolveCommand',
            'a2p_FlipConstraintDirectionCommand',
            'a2p_Show_Hierarchy_Command'
            ]
        viewCommands = [
            'a2p_isolateCommand',
            'a2p_ViewConnectionsCommand',
            'a2p_Restore_Transparency',
            'a2p_ToggleTransparencyCommand',            
            'a2p_Show_PartLabels_Command',
            'a2p_Show_DOF_info_Command',
            ]
        miscCommands = [
            'a2p_SimpleAssemblyShapeCommand',
            'a2p_repairTreeViewCommand',
            'a2p_CreatePartInformationSheet_Command',
            'a2p_CreatePartlist',
            ]

        self.appendToolbar(
               'A2p_Part',
               partCommands
               )
        self.appendToolbar(
               'A2p_Constraint',
               constraintCommands
               )
        self.appendToolbar(
               'A2p_Solver',
               solverCommands
               )
        self.appendToolbar(
               'A2p_View',
               viewCommands
               )
        self.appendToolbar(
               'A2p_Misc',
               miscCommands
               )

        self.appendMenu(
            'A2plus',
            partCommands
            )
        self.appendMenu(
            ['A2plus', 'Constraint'],
            constraintCommands
            )
        self.appendMenu(
            ['A2plus', 'Solver'],
            solverCommands
            )
        self.appendMenu(
            ['A2plus', 'View'],
            viewCommands
            )
        self.appendMenu(
            ['A2plus', 'Misc'],
            miscCommands
            )            
            
        menuEntries = [
            'a2p_absPath_to_relPath_Command',
            'a2p_MigrateProxiesCommand'
            ]
        self.appendMenu(
            ['A2plus', 'Misc'],
            menuEntries
            )
        FreeCADGui.addIconPath(':/icons')
        
        FreeCADGui.addPreferencePage(
            a2plib.pathOfModule() +
            '/GuiA2p/Resources/ui/a2p_prefs.ui','A2plus'
            )


    def Activated(self):
        import a2p_observers
        FreeCAD.addDocumentObserver(a2p_observers.redoUndoObserver)

    def Deactivated(self):
        import a2p_observers
        FreeCAD.removeDocumentObserver(a2p_observers.redoUndoObserver)

    def ContextMenu(self, recipient):
        import FreeCAD, FreeCADGui
        selection = [s  for s in FreeCADGui.Selection.getSelection() if s.Document == FreeCAD.ActiveDocument ]
        if len(selection) == 1:
            obj = selection[0]
            if 'sourceFile' in  obj.Content:
                self.appendContextMenu(
                    "A2plus",
                    [
                      'a2p_movePart',
                      'a2p_duplicatePart',
                      'a2p_editImportedPart',
                      'a2p_ConvertPart',
                      'a2p_DeleteConnectionsCommand',
                      'a2p_ToggleTransparencyCommand'
                      ]
                    )

Gui.addWorkbench(A2plusWorkbench())
