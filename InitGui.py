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

A2P_VERSION = 'V0.4.20'



import sys
PyVersion = sys.version_info[0]
if PyVersion == 2:
    import a2p_Resources2
else:
    import a2p_Resources3


class a2pWorkbench (Workbench):

    def __init__(self):
        global A2P_VERSION
        import a2plib
        self.__class__.Icon = a2plib.pathOfModule() + "/icons/a2p_Workbench.svg"
        self.__class__.MenuText = 'A2plus '+A2P_VERSION
        self.__class__.ToolTip  = 'An other assembly workbench for FreeCAD'


    def checkFC_Version(self):
        import FreeCAD
        from PySide import QtGui

        # FC requirement constants
        FC_MINOR_VER_REQUIRED = 17
        FC_COMMIT_REQUIRED = 13528
        FC_MINOR_VER_RECOMMENDED = 18
        FC_COMMIT_RECOMMENDED = 15997
        
        ver = FreeCAD.Version()
        try:
            gitver = int(ver[2].split()[0])
        except:
            gitver = 'Unknown'

        if (
            int(ver[0]) == 0 and
            int(ver[1]) == FC_MINOR_VER_RECOMMENDED and
            gitver == 'Unknown'
            ):
            return # do nothing, version is 0.18 stable and ok.

        if (
            int(ver[0]) == 0 and
            int(ver[1]) > FC_MINOR_VER_RECOMMENDED
            ):
            return # do nothing, version is > 0.18 stable and ok.
        
        if (
            int(ver[0]) == 0 and
            int(ver[1]) == FC_MINOR_VER_RECOMMENDED and
            gitver != 'Unknown' and
            gitver >= FC_COMMIT_RECOMMENDED
            ):
            return # do nothing, version is good 0.18pre and ok.
        
        if (
            int(ver[0]) == 0 and
            int(ver[1]) >= FC_MINOR_VER_REQUIRED and
            gitver != 'Unknown' and
            gitver >= FC_COMMIT_REQUIRED
            ):
            fc_msg = '''
While FreeCAD version ({}.{}.{}) will
work with the A2P workbench, it is recommended
to use {}.{}.{} or above.\n\n'''.format(
                                    int(ver[0]),
                                    int(ver[1]),
                                    gitver,
                                    0,
                                    FC_MINOR_VER_RECOMMENDED,
                                    FC_COMMIT_RECOMMENDED
                                    )
            print(fc_msg)
            return # version is 0.17stable and ok
        
        
        fc_msg = '''
Your FreeCAD version is not recommended
for work with the A2P workbench.
Please use {}.{}.{} or above.\n\n'''.format(
                                    0,
                                    FC_MINOR_VER_REQUIRED,
                                    FC_COMMIT_REQUIRED
                                    )
        print(fc_msg)



    def Initialize(self):
        #self.checkFC_Version()
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
                'a2p_ImportReferencedShapeCommand',
                'a2p_updateImportedParts',
                'a2p_recursiveUpdateImportedPartsCommand',
                'a2p_movePart',
                'a2p_duplicatePart',
                'a2p_ConvertPart',
                'a2p_editImportedPart',
                'a2p_SaveAndExit_Command',
                ]
        else:
            partCommands = [
                'a2p_ImportPart',
                'a2p_updateImportedParts',
                'a2p_movePart',
                'a2p_duplicatePart',
                'a2p_ConvertPart',
                'a2p_editImportedPart',
                'a2p_SaveAndExit_Command',
                ]
        
        if a2plib.SHOW_CONSTRAINTS_ON_TOOLBAR:
            constraintCommands = [
                'a2p_ConstraintDialogCommand',
                'a2p_EditConstraintCommand',
                'a2p_PointIdentityConstraintCommand',
                'a2p_PointOnLineConstraintCommand',
                'a2p_PointOnPlaneConstraintCommand',
                'a2p_SphericalSurfaceConstraintCommand',
                'a2p_CircularEdgeConnection',
                'a2p_AxialConstraintCommand',
                'a2p_AxisParallelConstraintCommand',
                'a2p_AxisPlaneParallelCommand',
                'a2p_AxisPlaneVerticalCommand',
                'a2p_PlanesParallelConstraintCommand',
                'a2p_PlaneCoincidentConstraintCommand',
                'a2p_AngledPlanesConstraintCommand',
                'a2p_CenterOfMassConstraintCommand',
                
                'a2p_DeleteConnectionsCommand',
                ]
        else:
            constraintCommands = [
                'a2p_ConstraintDialogCommand',
                'a2p_EditConstraintCommand',
                'a2p_DeleteConnectionsCommand',
                ]
        
        solverCommands = [
            'a2p_SolverCommand',
            #'a2p_newSolverCommand',
            'a2p_ToggleAutoSolveCommand',
            'a2p_FlipConstraintDirectionCommand',
            'a2p_Show_DOF_info_Command',
            'a2p_Show_Hierarchy_Command'
            #'a2p_TogglePartialProcessingCommand',
            ]
        viewCommands = [
            'a2p_ViewConnectionsCommand',
            'a2p_ToggleTransparencyCommand',
            'a2p_isolateCommand',
            ]
        miscCommands = [
            'a2p_SimpleAssemblyShapeCommand',
            'a2p_repairTreeViewCommand',
            'a2p_CreatePartInformationSheet_Command',
            'a2p_CreatePartlist',
            'a2p_Show_PartLabels_Command',
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

        commandslist = list()
        commandslist.extend(partCommands)
        commandslist.extend(constraintCommands)
        commandslist.extend(solverCommands)
        commandslist.extend(viewCommands)
        commandslist.extend(miscCommands)

        self.appendMenu(
            'A2plus',
            commandslist
            )

        menuEntries = [
            'a2p_repairTreeViewCommand',
            'a2p_absPath_to_relPath_Command'
            ]
        self.appendMenu(
            'A2plus',
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
                    "A2p",
                    [
                      'a2p_movePart',
                      'a2p_duplicatePart',
                      'a2p_editImportedPart',
                      'a2p_ConvertPart',
                      'a2p_DeleteConnectionsCommand',
                      'a2p_ToggleTransparencyCommand'
                      ]
                    )

Gui.addWorkbench(a2pWorkbench())
