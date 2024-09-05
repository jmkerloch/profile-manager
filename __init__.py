"""
/***************************************************************************
 ProfileManager
                                 A QGIS plugin
 Makes creating profiles easy by giving you an UI to easly import settings from other profiles
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                             -------------------
        begin                : 2020-03-17
        copyright            : (C) 2020 by Dominik Szill / WhereGroup GmbH
        email                : dominik.szill@wheregroup.com
        git sha              : $Format:%H$
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


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load ProfileManager class from file ProfileManager.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .profile_manager import ProfileManager
    return ProfileManager(iface)
