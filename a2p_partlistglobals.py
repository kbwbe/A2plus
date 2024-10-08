#***************************************************************************
#*                                                                         *
#*   Copyright (c) 2018 kbwbe                                              *
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

from a2p_translateUtils import *

PARTINFORMATION_SHEET_NAME = "_PARTINFO_"
PARTINFORMATION_SHEET_LABEL = "#" + translate("A2p_BoM", "PARTINFO") + "#"

# BOM = BillOfMaterials...
BOM_SHEET_NAME = "_PARTSLIST_"
BOM_SHEET_LABEL = "#" + translate("A2p_BoM", "PARTSLIST") + "#"

# CutListOptimizer BillOfMaterials...
CLO_BOM_SHEET_NAME = "_PARTSLIST_CUT-LIST-OPTIMIZER_"
CLO_BOM_SHEET_LABEL = "#" + translate("A2p_BoM", "CLO_PARTSLIST") + "#"

BOM_MAX_COLS = 10
BOM_MAX_LENGTH = 150

CLO_BOM_MAX_COLS = 10
CLO_BOM_MAX_LENGTH = BOM_MAX_LENGTH

PARTLIST_COLUMN_NAMES = [
    translate("A2p_BoM", "IDENTNO"),
    translate("A2p_BoM", "DESCRIPTION"),
    translate("A2p_BoM", "SUPPLIER"),
    translate("A2p_BoM", "SUPP.IDENTNO"),
    translate("A2p_BoM", "SUPP.DESCRIPTION"),
    translate("A2p_BoM", "(FILENAME)")
]

CLO_PARTLIST_COLUMN_NAMES = [
    translate("A2p_BoM", "Length"),
    translate("A2p_BoM", "Width"),
    translate("A2p_BoM", "Qty"),
    translate("A2p_BoM", "Material"),
    translate("A2p_BoM", "Label"),
    translate("A2p_BoM", "Enabled")
]
