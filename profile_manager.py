"""
/***************************************************************************
 ProfileManager
                                 A QGIS plugin
 Makes creating profiles easy by giving you an UI to easly import settings from other profiles
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2020-03-17
        git sha              : $Format:%H$
        copyright            : (C) 2020 by Stefan Giese & Dominik Szill / WhereGroup GmbH
        email                : stefan.giese@wheregroup.com / dominik.szill@wheregroup.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
# Import the code for the dialog
import time
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication, QSize
from qgis.PyQt.QtWidgets import QAction, QWidget
from qgis.core import QgsUserProfileManager
from pathlib import Path
from sys import platform
from os import path, chmod
from stat import S_IWRITE
from shutil import rmtree, copytree
# Import subclasses
from .profile_manager_dialog import ProfileManagerDialog
from .datasources.Dataservices.datasource_provider import DataSourceProvider
from .datasources.Dataservices.datasource_handler import DataSourceHandler
from .profiles.profile_action_handler import ProfileActionHandler
from .userInterface.remove_sources_dialog import RemoveSourcesDialog
from .userInterface.interface_handler import InterfaceHandler
from .userInterface.message_box_factory import MessageBoxFactory
from .utils import wait_cursor
# Initialize Qt resources from file resources.py
from .resources import *


class ProfileManager:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Classwide vars
        self.dictionary_of_checked_web_sources = {}
        self.dictionary_of_checked_database_sources = {}
        self.is_cancel_button_clicked = False
        self.is_ok_button_clicked = False
        self.qgis_path = ""
        self.ini_path = ""
        self.operating_system = ""
        self.qgs_profile_manager = None
        self.message_box_factory = None
        self.data_source_handler = None
        self.data_source_provider = None
        self.profile_manager_action_handler = None
        self.interface_handler = None
        self.dlg = None

        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = path.dirname(__file__)
        # initialize locale

        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = path.join(
            self.plugin_dir,
            'i18n',
            'ProfileManager_{}.qm'.format(locale))

        if path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Profile Manager')

        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.first_start = None

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('ProfileManager', message)

    def add_action(
            self,
            icon_path,
            text,
            callback,
            enabled_flag=True,
            add_to_menu=True,
            add_to_toolbar=True,
            status_tip=None,
            whats_this=None,
            parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/profile_manager/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Profile Manager'),
            callback=self.run,
            parent=self.iface.mainWindow())

        # will be set False in run()
        self.first_start = True

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Profile Manager'),
                action)
            self.iface.removeToolBarIcon(action)

    def run(self):
        """Run method that performs all the real work"""
        # Create the dialog with elements (after translation) and keep reference
        # Only create GUI ONCE in callback, so that it will only load when the plugin is started
        with wait_cursor():
            if self.first_start:
                self.first_start = False
                self.dlg = ProfileManagerDialog(parent=self.iface.mainWindow())
                self.dlg.setFixedSize(self.dlg.size())
                self.dlg.list_profiles.setIconSize(QSize(15, 15))

            self.set_paths()

            self.qgs_profile_manager = QgsUserProfileManager(self.qgis_path)
            self.message_box_factory = MessageBoxFactory(self.dlg)

            self.data_source_handler = DataSourceHandler(self.dlg, self)
            self.data_source_provider = DataSourceProvider(self.ini_path, self.dlg)
            self.profile_manager_action_handler = ProfileActionHandler(self.dlg, self.qgis_path, self)
            self.interface_handler = InterfaceHandler(self, self.dlg)

            self.interface_handler.init_profile_selection()
            self.interface_handler.init_ui_buttons()
            self.interface_handler.init_data_source_tree(self.dlg.comboBoxNamesSource.currentText(), True)
            self.interface_handler.init_data_source_tree(self.dlg.comboBoxNamesTarget.currentText(), False)

            self.data_source_handler.set_path_to_files(
                self.dlg.comboBoxNamesSource.currentText(),
                self.dlg.comboBoxNamesTarget.currentText()
            )
            self.data_source_handler.display_plugins()

        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec()
        # See if OK was pressed
        if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            pass

    def set_paths(self):
        """Sets path to qgis root aswell as to qgis.ini"""
        home_path = Path.home()
        if platform.startswith('win32'):
            self.qgis_path = f'{home_path}/AppData/Roaming/QGIS/QGIS3/profiles'.replace("\\", "/")
            self.ini_path = (self.qgis_path + "/" + self.dlg.comboBoxNamesSource.currentText() + "/QGIS/QGIS3.ini")
            self.operating_system = "windows"
        elif platform is 'darwin':
            self.qgis_path = f'{home_path}/Library/Application Support/QGIS/QGIS3/profiles'
            self.ini_path = self.qgis_path + "/" + self.dlg.comboBoxNamesSource.currentText() + "/qgis.org/QGIS3.ini"
            self.operating_system = "mac"
            self.interface_handler.adjust_to_macOSDark()
        else:
            self.qgis_path = f'{home_path}/.local/share/QGIS/QGIS3/profiles'
            self.ini_path = self.qgis_path + "/" + self.dlg.comboBoxNamesSource.currentText() + "/QGIS/QGIS3.ini"
            self.operating_system = "unix"

    def adjust_to_operating_system(self, path_to_adjust):
        """Adjusts path to current OS"""
        if self.operating_system is "windows":
            return path_to_adjust.replace("/", "\\")
        elif self.operating_system is "unix":
            return path_to_adjust.replace("\\", "/")
        else:
            return path_to_adjust.replace("\\", "/").replace("/QGIS/QGIS3.ini", "/qgis.org/QGIS3.ini")

    def make_backup(self):
        """Creates a backup of the profile folders"""
        ts = int(time.time())

        target_path = self.adjust_to_operating_system(str(Path.home()) + "/QGISBackup/" + str(ts) + "/")

        if path.isdir(target_path):
            rmtree(target_path, onerror=self.remove_readonly)

        copytree(self.qgis_path, target_path)

    def import_action_handler(self):
        """Handles data source import"""
        with wait_cursor():
            self.get_checked_sources()
            if self.dlg.comboBoxNamesSource.currentText() == self.dlg.comboBoxNamesTarget.currentText():
                self.message_box_factory.create_message_box(self.tr("Could not edit profile"),
                                                            self.tr("Target profile can not be same as source profile"))
            else:
                source_profile_name = self.dlg.comboBoxNamesSource.currentText()
                target_profile_name = self.dlg.comboBoxNamesTarget.currentText()
                self.data_source_handler.set_path_to_files(source_profile_name,
                                                           target_profile_name)
                self.data_source_handler.set_path_to_bookmark_files(source_profile_name,
                                                                    target_profile_name)
                self.make_backup()
                self.data_source_handler.import_plugins()
                self.data_source_handler.import_sources()
                self.update_data_sources(True)

        self.message_box_factory.create_message_box(
            self.tr("Success"),
            self.tr(
                "Datasources have been successfully imported!\n\n"
                "Please refresh the QGIS Browser to see the changes!"
            ),
            self.tr("Datasource Import")
        )
        self.interface_handler.uncheck_everything()
        self.refresh_browser_model()

    def remove_source_action_handler(self):
        """Handles data source removal"""
        self.get_checked_sources()
        self.data_source_handler.set_path_to_files(self.dlg.comboBoxNamesSource.currentText(), "")

        dialog = RemoveSourcesDialog(self.dlg, self, self.adjust_to_operating_system(str(Path.home()) + "/QGISBackup/"))
        dialog.exec()
        while not self.is_cancel_button_clicked and not self.is_ok_button_clicked:
            QCoreApplication.processEvents()

        with wait_cursor():
            if self.is_ok_button_clicked:
                self.make_backup()
                self.data_source_handler.remove_sources()
                self.update_data_sources(True)

        if self.is_ok_button_clicked:
            self.message_box_factory.create_message_box(
                self.tr("Success"),
                self.tr(
                    "Datasources have been successfully removed!\n\n"
                    "Please refresh the QGIS Browser to see the changes!"
                ),
                self.tr("Datasource Removed")
            )

        self.is_cancel_button_clicked = False
        self.is_ok_button_clicked = False

        self.interface_handler.uncheck_everything()
        self.refresh_browser_model()

    def update_data_sources(self, update_plugins=False, update_source=True):
        """Updates data source in the UI"""
        source_profile = self.dlg.comboBoxNamesSource.currentText()
        target_profile = self.dlg.comboBoxNamesTarget.currentText()

        if update_source:
            self.interface_handler.init_data_source_tree(source_profile, True)
            self.interface_handler.init_data_source_tree(target_profile, False)
        else:
            self.interface_handler.init_data_source_tree(target_profile, False)

        self.data_source_handler.display_plugins(update_plugins)

    def get_checked_sources(self):
        """Gets all checked data sources"""
        self.data_source_provider.init_checked_sources()
        self.dictionary_of_checked_web_sources = self.data_source_provider.dictionary_of_checked_web_sources
        self.dictionary_of_checked_database_sources = self.data_source_provider.dictionary_of_checked_database_sources

        self.data_source_handler.set_data_sources(self.dictionary_of_checked_web_sources,
                                                  self.dictionary_of_checked_database_sources)

    def get_profile_paths(self):
        """Gets path to current chosen source and target profile"""
        source = self.adjust_to_operating_system(
            self.qgis_path + "/" + self.dlg.comboBoxNamesSource.currentText() + "/")
        target = self.adjust_to_operating_system(
            self.qgis_path + "/" + self.dlg.comboBoxNamesTarget.currentText() + "/")

        profile_paths = {
            "source": source,
            "target": target,
        }

        return profile_paths

    def get_ini_paths(self):
        """Gets path to current chosen source and target qgis.ini file"""
        if self.operating_system == "mac":
            ini_path_source = self.adjust_to_operating_system(
                self.qgis_path + "/" + self.dlg.comboBoxNamesSource.currentText() + "/qgis.org/QGIS3.ini")
            ini_path_target = self.adjust_to_operating_system(
                self.qgis_path + "/" + self.dlg.comboBoxNamesTarget.currentText() + "/qgis.org/QGIS3.ini")
        else:
            ini_path_source = self.adjust_to_operating_system(
                self.qgis_path + "/" + self.dlg.comboBoxNamesSource.currentText() + "/QGIS/QGIS3.ini")
            ini_path_target = self.adjust_to_operating_system(
                self.qgis_path + "/" + self.dlg.comboBoxNamesTarget.currentText() + "/QGIS/QGIS3.ini")

        ini_paths = {
            "source": ini_path_source,
            "target": ini_path_target,
        }

        return ini_paths

    def refresh_browser_model(self):
        """Refreshes the browser of the qgis instance from which this plugin was started"""
        self.iface.mainWindow().findChildren(QWidget, 'Browser')[0].refresh()
        self.iface.mainWindow().findChildren(QWidget, 'Browser2')[0].refresh()

    def remove_readonly(self, func, path, excinfo):
        """Removes readonly access from directory"""
        chmod(path, S_IWRITE)
        func(path)
