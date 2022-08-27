#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#***************************************************************************
#*                                                                         *
#*   Copyright (c) 2019 kbwbe                                              *
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

import os
import glob

#==============================================================================
# Script for preparing translations of A2plus Workbench
#
# The script has to be started within the A2plus/translations Folder
#==============================================================================

# 1) Scan ui-Files for strings
print('1. Scan ui-Files for strings')
os.system(
    """
    lupdate ../GuiA2p/Resources/ui/*.ui -ts uifiles.ts
    """
    )
# 2) Scan .py-Files for strings
print("2. Scan .py-Files for strings")
os.system(
    """
    pylupdate5 ../*.py -ts pyfiles.ts -verbose
    """
    )
# 3) combine both scans above
print("3. Combine both scans above")
os.system(
    """
    lconvert -i uifiles.ts pyfiles.ts -o A2plus.ts
    """
    )

# 4) remove temporary files
print("4. Remove temporary files")
print("                          uifiles.ts")
os.system(
    """
    rm uifiles.ts
    """
    )
print("                          pyfiles.ts")
os.system(
    """
    rm pyfiles.ts
    """
    )
