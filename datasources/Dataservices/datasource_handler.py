from PyQt5.QtWidgets import QMessageBox
from .datasource_distributor import DatasourceDistributor
from ..Bookmarks.bookmark_handler import import_bookmarks
from ..Customizations.customization_handler import import_customizations
from ..Favourites.favourites_handler import import_favourites
from ..Functions.function_handler import import_expression_functions
from ..Models.model_handler import import_models
from ..Models.script_handler import import_scripts
from ..Plugins.plugin_handler import PluginHandler
from ..Styles.style_handler import import_styles
from ...utils import adjust_to_operating_system

class DataSourceHandler:

    def __init__(self, profile_manager_dialog, profile_manager):
        self.profile_manager = profile_manager
        self.dlg = profile_manager_dialog
        self.qgis_path = self.profile_manager.qgis_profiles_path
        self.dictionary_of_checked_web_sources = {}
        self.dictionary_of_checked_data_base_sources = {}
        self.source_profile_path = ""
        self.target_profile_path = ""
        self.source_qgis_ini_file = ""
        self.target_qgis_ini_file = ""
        self.source_bookmark_file = ""
        self.target_bookmark_file = ""
        self.datasource_distributor = DatasourceDistributor(self.profile_manager)
        self.plugin_handler = PluginHandler(self.profile_manager)

    def set_data_sources(self, dictionary_of_checked_web_sources, dictionary_of_checked_data_base_sources):
        """Sets data sources"""
        self.dictionary_of_checked_web_sources = dictionary_of_checked_web_sources
        self.dictionary_of_checked_data_base_sources = dictionary_of_checked_data_base_sources

    def import_sources(self):
        """Handles the whole data import action.

        Returns:
            boolean: If errors were encountered.
        """
        had_errors = False

        self.setup_datasource_distributor()

        self.datasource_distributor.import_sources()

        if self.dlg.bookmark_check.isChecked():
            error_message = import_bookmarks(self.source_bookmark_file, self.target_bookmark_file)
            if error_message:
                had_errors = True
                QMessageBox.critical(None, "Error while importing bookmarks", error_message)

        if self.dlg.favourites_check.isChecked():
            error_message = import_favourites(self.source_qgis_ini_file, self.target_qgis_ini_file)
            if error_message:
                had_errors = True
                QMessageBox.critical(None, "Error while importing favourites", error_message)

        if self.dlg.models_check.isChecked():
            import_models(self.source_profile_path, self.target_profile_path)  # currently has no error handling

        if self.dlg.scripts_check.isChecked():
            import_scripts(self.source_profile_path, self.target_profile_path)  # currently has no error handling

        if self.dlg.styles_check.isChecked():
            error_message = import_styles(self.source_profile_path, self.target_profile_path)
            if error_message:
                had_errors = True
                QMessageBox.critical(None, "Error while importing styles", error_message)

        if self.dlg.functions_check.isChecked():
            error_message = import_expression_functions(self.source_qgis_ini_file, self.target_qgis_ini_file)
            if error_message:
                had_errors = True
                QMessageBox.critical(None, "Error while importing expression functions", error_message)

        if self.dlg.ui_check.isChecked():
            import_customizations(self.source_profile_path, self.target_profile_path)  # currently has no error handling

        self.plugin_handler.import_selected_plugins()

        return had_errors

    def import_plugins(self):
        self.setup_datasource_distributor()
        self.plugin_handler.import_selected_plugins()

    def display_plugins(self, only_for_target_profile=False):
        """Displays plugins in treeWidget"""
        self.plugin_handler.set_path_files()
        self.plugin_handler.populate_plugins_list(only_for_target_profile=only_for_target_profile)

    def remove_sources(self):
        """Handles data removal"""
        self.setup_datasource_distributor()
        self.plugin_handler.remove_plugins()
        self.datasource_distributor.remove_sources()

    def set_path_to_files(self, source_profile_name, target_profile_name):
        """Sets file paths"""
        ini_paths = self.profile_manager.get_ini_paths()
        self.source_qgis_ini_file = ini_paths['source']
        self.target_qgis_ini_file = ini_paths['target']

        self.source_profile_path = adjust_to_operating_system(self.qgis_path + '/' + source_profile_name + '/')
        self.target_profile_path = adjust_to_operating_system(self.qgis_path + '/' + target_profile_name + '/')

    def set_path_to_bookmark_files(self, source_profile_name, target_profile_name):
        """Sets file paths"""
        self.source_bookmark_file = adjust_to_operating_system(
            self.qgis_path + '/' + source_profile_name + '/' + 'bookmarks.xml')
        self.target_bookmark_file = adjust_to_operating_system(
            self.qgis_path + '/' + target_profile_name + '/' + 'bookmarks.xml')

    def setup_datasource_distributor(self):
        """Sets up data source distributor"""
        self.datasource_distributor.dictionary_of_checked_web_sources = self.dictionary_of_checked_web_sources
        self.datasource_distributor.dictionary_of_checked_database_sources = \
            self.dictionary_of_checked_data_base_sources
        self.datasource_distributor.source_qgis_ini_file = self.source_qgis_ini_file
        self.datasource_distributor.target_qgis_ini_file = self.target_qgis_ini_file
