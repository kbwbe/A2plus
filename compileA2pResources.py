#!/usr/bin/env python
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

# This script compiles the A2plus icons for py2 and py3
# For Linux only
# Start this file in A2plus main directory
# Make sure pyside-rcc is installed

import os, glob

qrc_filename = 'temp.qrc'
if os.path.exists(qrc_filename):
    os.remove(qrc_filename)


qrc = '''<RCC>
\t<qresource prefix="/">'''
for fn in glob.glob('./icons/*.svg'):
    qrc = qrc + '\n\t\t<file>%s</file>' % fn
qrc = qrc + '''\n\t</qresource>
</RCC>'''

print(qrc)

f = open(qrc_filename,'w')
f.write(qrc)
f.close()

#os.system(
#    'pyside-rcc -o a2p_Resources2.py {}'.format(
#        qrc_filename
#        )
#    )
os.system(
    'pyside-rcc -py3 -o a2p_Resources3.py {}'.format(
        qrc_filename
        )
    )

os.system(
    'pyside-lupdate *.py -ts translations/A2plus.ts -verbose'
    )
'''
os.system(
    'lrelease "translations/A2plus.ts"'
    )
'''

os.remove(qrc_filename)

"""NOTES: (adding Translations...)
# gather the strings from the .py files of the WB
pyside-lupdate *.py -ts translations/pyfiles.ts -verbose

# merge ts files if there is more then one...
# lconvert is not found on my system without path ???
/usr/lib/x86_64-linux-gnu/qt5/bin/lconvert -i translations/pyfiles.ts another.ts -o translations/A2plus

# convert .ts files to .qm files (compiled translations)
lrelease "translations/A2plus.ts"

"""
