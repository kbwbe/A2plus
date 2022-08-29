#! /bin/sh

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

#==============================================================================
# Script for preparing translations file of A2plus Workbench
#
# The script has to be started within the A2plus/translations folder
#==============================================================================

# 1) Scan UI files for strings
echo "1. Scan UI files for strings"
    lupdate ../GuiA2p/Resources/ui/*.ui -ts uifiles.ts

# 2) Scan .py files for strings
echo "2. Scan .py files for strings"
    pylupdate5 ../*.py -ts pyfiles.ts -verbose

# 3) Combine both scans above
echo "3. Combine both scans above"
    lconvert -i uifiles.ts pyfiles.ts -o A2plus.ts

# 4) Remove temporary files
echo "4. Remove temporary files"
    rm uifiles.ts
echo "                          uifiles.ts"
    rm pyfiles.ts
echo "                          pyfiles.ts"

# 5) Message for user
echo "5. You have fresh A2plus.ts file now"

