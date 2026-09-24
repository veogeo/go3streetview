# -*- coding: utf-8 -*-
"""
/***************************************************************************
 go3streetview
                                 A QGIS plugin
 click to open Google Street View
                             -------------------
        begin                : 2014-02-17
        copyright            : (C) 2014 by Enrico Ferreguti
        email                : enricofer@me.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""

import os 
import site
import sys

# sys.path.append(os.path.dirname(__file__))
# site.addsitedir(os.path.join(os.path.dirname(__file__), 'res'))


def classFactory(iface):
    # load go3streetview class from file go3streetview
    from .go3streetview import go3streetview
    return go3streetview(iface)
