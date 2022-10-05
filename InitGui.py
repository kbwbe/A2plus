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


A2P_VERSION = 'V0.4.59d'

import sys
import FreeCAD
import FreeCADGui
translate = FreeCAD.Qt.translate

import a2p_Resources3


class A2plusWorkbench (Workbench):

    def __init__(self):
        global A2P_VERSION
        translate = FreeCAD.Qt.translate
#        from a2p_translateUtils import translate
        import a2plib
        self.__class__.Icon = a2plib.pathOfModule() + "/icons/a2p_Workbench.svg"
        self.__class__.MenuText = 'A2plus'
        self.__class__.ToolTip  = translate("A2plus", "An other assembly workbench for FreeCAD.")

    def QT_TRANSLATE_NOOP(context, text):
        return text

    def Initialize(self):
#        from a2p_translateUtils import QT_TRANSLATE_NOOP
#        from a2p_translateUtils import translate
#        from a2p_translateUtils import tr_

        import sys
        import a2p_Resources3

        # add translations path
        FreeCADGui.addLanguagePath(a2plib.getLanguagePath())
        FreeCADGui.updateLocale()
#        print(translate("A2plus_appendMenu", "languagePath of A2plus Workbench is:"), "{}".format(a2plib.getLanguagePath()))
        FreeCAD.Console.PrintMessage(translate("A2plus", "Initializing A2plus Workbench ") + A2P_VERSION + ".\n")

        # add icons path
        FreeCADGui.addIconPath(':/icons')

        import a2p_importpart
        import a2p_recursiveUpdatePlanner
        import a2p_convertPart
        import a2p_solversystem
        import a2p_MuxAssembly
        import a2p_partinformation
        import a2p_constraintDialog
        import a2p_constraintcommands
        import a2p_bom # bom == bill of materials == partslist
        import a2p_constraintServices
        import a2p_searchConstraintConflicts
        import CD_A2plusupdater  # for Constraint Diagnostic function
        import CD_checkconstraints
        import CD_OneButton
        
        # Create list of commands for toolbar A2p_Part and menu A2plus
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

        if a2plib.getRecursiveUpdateEnabled():
            partCommands.insert(3, 'a2p_recursiveUpdateImportedPartsCommand')

        # Create list of commands for toolbar A2p_constraint
        constraintCommands = [
            'a2p_ConstraintDialogCommand',
            'a2p_EditConstraintCommand',
            'a2p_reAdjustConstraintDirectionsCommand',
            'a2p_DeleteConnectionsCommand',
            ]

        if a2plib.SHOW_CONSTRAINTS_ON_TOOLBAR:
            constraintCommands1 = [
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
            constraintCommands.extend(constraintCommands1)

        # Create list of commands for toolbar A2p_Solver
        solverCommands = [
            'a2p_SolverCommand',
            'a2p_ToggleAutoSolveCommand',
            'a2p_FlipConstraintDirectionCommand',
            'a2p_Show_Hierarchy_Command',
            'a2p_SearchConstraintConflictsCommand'
            ]

        if a2plib.GRAPHICALDEBUG:
            solverCommands.append(
                'a2p_cleanUpDebug3dCommand'
                )

        # Create list of commands for toolbar A2p_View
        viewCommands = [
            'a2p_isolateCommand',
            'a2p_ViewConnectionsCommand',
            'a2p_Restore_Transparency',
            'a2p_ToggleTransparencyCommand',
            'a2p_Show_PartLabels_Command',
            'a2p_Show_DOF_info_Command',
            ]

        # Create list of commands for toolbar A2p_Misc
        miscCommands = [
            'a2p_SimpleAssemblyShapeCommand',
            'a2p_repairTreeViewCommand',
            'a2p_CreatePartInformationSheet_Command',
            'a2p_CreatePartlist',
            ]

        # Create list of commands for toolbar A2p_Diagnostics
        DiagnosticCommands = [
            'rnp_Constraint_Viewer',
            'rnp_Update_A2pParts',
            'rnp_Constraint_Checker',
            'rnp_OneButton',
            ]

        menuEntries = [
            'a2p_absPath_to_relPath_Command',
            'a2p_MigrateProxiesCommand'
            ]
       

        # Create toolbars
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
        self.appendToolbar(
           'A2p_Diagnostics',
           DiagnosticCommands
           )


        # Create menus
        self.appendMenu(
            'A2plus',
            partCommands
            )
        self.appendMenu(
            ['A2plus', QT_TRANSLATE_NOOP("Workbench", "Constraint")],
            constraintCommands
            )
        self.appendMenu(
            ['A2plus', QT_TRANSLATE_NOOP("Workbench", "Solver")],
            solverCommands
            )
        self.appendMenu(
            ['A2plus', QT_TRANSLATE_NOOP("Workbench", "View")],
            viewCommands
            )
        miscCommands.extend(menuEntries)
        self.appendMenu(
            ['A2plus', QT_TRANSLATE_NOOP("Workbench", "Misc")],
            miscCommands
            )
        self.appendMenu(
           ['A2plus', QT_TRANSLATE_NOOP("Workbench", "Diagnostic")],
           DiagnosticCommands
           )

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
