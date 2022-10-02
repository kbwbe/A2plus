#! /usr/bin/env python3
#
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
import sys
#import glob

#==============================================================================
# Script for create translations file for A2plus Workbench
#
# The script has to be started within the A2plus/translations Folder
#==============================================================================
def create_ts():

    print("1. Scan UI files for strings")
    os.system(
        """
        lupdate ../GuiA2p/Resources/ui/*.ui -ts uifiles.ts
        """
        )

    print("2. Scan .py files for strings")
    os.system(
        """
        pylupdate5 -verbose ../*.py -ts pyfiles.ts
        """
        )

    print("3. Combine both scans above")
    os.system(
        """
        lconvert -i uifiles.ts pyfiles.ts -o A2plus.ts -sort-contexts -no-obsolete -verbose
        """
        )

    print("4. Remove temporary files")
    os.system(
        """
        rm uifiles.ts
        """
        )
    print("                          uifiles.ts")
    os.system(
        """
        rm pyfiles.ts
        """
        )
    print("                          pyfiles.ts")
    print("5. You have fresh A2plus.ts file now")


#==============================================================================
# Script for merging different translations of A2plus Workbench
#
# The script has to be started within the A2plus/translations Folder
#==============================================================================
def merge_ts():

#    for file in glob.glob('*_*.ts'):
#        os.system(
#            '''
#            lrelease {}
#            '''.format(file)
#            )
#        print("You have fresh '" + file + "' file now")


# It's work without 'for':
    os.system(
        '''
        lrelease *_*.ts
        '''
        )
    print("You have fresh all A2plus_*.qm files now")


#==============================================================================
# Script for update all translations of A2plus Workbench
#
# The script has to be started within the A2plus/translations folder
#==============================================================================
def update_ts():

#    for file in glob.glob('*.ts'):
#        os.system(
#            '''
#            pylupdate5 -verbose ../GuiA2p/Resources/ui/*.ui ../*.py -ts {}
#            '''.format(file)
#            )
#        print("You have fresh '" + file + "' file now")

# It's work without 'for':
    os.system(
        '''
        pylupdate5 -verbose ../GuiA2p/Resources/ui/*.ui ../*.py -ts *.ts
        '''
        )


par = ''
if __name__ == '__main__':
    if len(sys.argv) > 1:
        par = sys.argv[1]

    if par=='-c':
        print("Script for create translations file for A2plus Workbench:")
        create_ts()
    elif par == '-h':
        print("Script for preparing translations file for A2plus Workbench")
        print("Copyright (c) 2019 kbwbe")
        print("")
        print("Commands:")
        print("         -c    - create A2plus.ts file from *.ui file and from all *.py files")
        print("         -h    - this help")
        print("         -m    - merge all A2plus_*.ts files to A2plus_*.qm files")
        print("         -u    - update all A2plus_*.ts files")
    elif par == '-m':
        print("Script for merging different translations of A2plus Workbench:")
        merge_ts()
    elif par == '-u':
        print("Script for update all translations of A2plus Workbench:")
        update_ts()
    else:
        print(f"Parameter '{par}' not present.")
        print("Use 'python3 update_ts.py -h' for information")

