from configparser import RawConfigParser
from collections import defaultdict
from re import compile, search
from urllib.parse import unquote

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QTreeWidgetItem
from qgis.core import Qgis, QgsMessageLog


class DataSourceProvider:

    def __init__(self, path, profile_manager):
        self.dlg = profile_manager
        self.parser = RawConfigParser()
        self.parser.optionxform = str
        self.ini_path = path
        self.service_name_regex = compile(r'\\(.*?)\\')
        self.gpkg_service_name_regex = compile(r'\\(.+).\\')

    def update_path(self, path):
        """Sets .ini path"""
        self.ini_path = path

    def get_data_sources_tree(self, compile_string, tree_name, is_source):
        """Returns a tree of checkable items for all data sources matching the search string.

        The tree contains a checkable item per data source found.

        Args:
            compile_string (str): Regex for searching corresponding data sources in ini file
            tree_name (str): Name of the parent tree item (e.g. "WMS")
            is_source (bool): Flag to indicate if items should be checkable

        Returns:
            QTreeWidgetItem: Tree widget item representing the data sources or None if none were found
        """
        self.parser.clear()
        self.parser.read(self.ini_path)

        search_string = compile(compile_string)
        data_sources_parent = QTreeWidgetItem([tree_name])
        if is_source:
            data_sources_parent.setFlags(data_sources_parent.flags() | Qt.ItemIsTristate | Qt.ItemIsUserCheckable)

        children = []
        try:
            # the connections are inside the qgis section
            qgis_keys = self.parser['qgis']
        except KeyError:
            QgsMessageLog.logMessage(f"No entry for 'qgis' found", "Profile Manager", Qgis.Info)
            return None

        for key in qgis_keys:
            if search_string.search(key):
                source_name_raw = search(self.service_name_regex, key)
                source_name = source_name_raw.group(0).replace("\\", "")

                source_name = unquote(source_name, 'latin-1')  # needed for e.g. %20 in connection names

                data_sources_child = QTreeWidgetItem([source_name])
                if is_source:
                    data_sources_child.setFlags(data_sources_child.flags() | Qt.ItemIsUserCheckable)
                    data_sources_child.setCheckState(0, Qt.Unchecked)

                children.append(data_sources_child)

        QgsMessageLog.logMessage(
            f"{len(children)} items for 'qgis'->'{compile_string}' found", "Profile Manager", Qgis.Info
        )
        if children:
            data_sources_parent.addChildren(children)
            return data_sources_parent
        else:
            return None

    def get_db_sources_tree(self, compile_string, tree_name, service_block, is_source):
        """Returns a tree of items for all data sources matching the search string.

        Args:
            compile_string (str): Regex for searching corresponding data sources in ini file
            tree_name (str): Name of the parent tree item (e.g. "WMS")
            service_block (str): Name of the block in the ini file to process
            is_source (bool): Flag to indicate if items should be checkable

        Returns:
            QTreeWidgetItem: Tree widget item representing the data sources or None if none were found
        """
        self.parser.clear()
        self.parser.read(self.ini_path)

        search_string = compile(compile_string)

        data_base_sources_parent = QTreeWidgetItem([tree_name])
        if is_source:
            data_base_sources_parent.setFlags(
                data_base_sources_parent.flags() | Qt.ItemIsTristate | Qt.ItemIsUserCheckable)

        children = []
        try:
            service_block_keys = self.parser[service_block]
        except KeyError:
            QgsMessageLog.logMessage(f"No entry for '{service_block}' found", "Profile Manager", Qgis.Info)
            return None

        for key in service_block_keys:
            if search_string.search(key):
                if tree_name == "GeoPackage":
                    db_name_raw = search(self.gpkg_service_name_regex, key)
                    db_name = db_name_raw.group(0).replace("\\GPKG\\connections\\", "").replace("\\", "")
                else:
                    db_name_raw = search(self.service_name_regex, key)
                    db_name = db_name_raw.group(0).replace("\\", "")

                db_name = unquote(db_name, 'latin-1')

                data_base_sources_child = QTreeWidgetItem([db_name])
                if is_source:
                    data_base_sources_child.setFlags(data_base_sources_child.flags() | Qt.ItemIsUserCheckable)
                    data_base_sources_child.setCheckState(0, Qt.Unchecked)

                children.append(data_base_sources_child)

        QgsMessageLog.logMessage(f"{len(children)} items for {service_block} found", "Profile Manager", Qgis.Info)
        if children:
            data_base_sources_parent.addChildren(children)
            return data_base_sources_parent
        else:
            return None

    def get_checked_sources(self):
        """"Collects all items checked in the data source import dialog and sorts them into dicts.

        Returns:
            tuple[dict[list], dict[list]]: The checked web sources and the checked database sources as dicts of lists
        """

        dictionary_of_checked_web_sources = defaultdict(list)
        dictionary_of_checked_database_sources = defaultdict(list)

        for item in self.dlg.treeWidgetSource.findItems("", Qt.MatchContains | Qt.MatchRecursive):
            if item.childCount() == 0 and item.checkState(0) == Qt.Checked:
                parent_text = item.parent().text(0)  # the provider group in the tree
                item_text = item.text(0)  # a specific data source in the provider's group
                if parent_text in ["SpatiaLite", "PostgreSQL", "MSSQL", "DB2", "Oracle"]:
                    dictionary_of_checked_database_sources[parent_text].append(item_text)
                # GeoPackage connections are stored under [providers] in the ini
                elif parent_text == "GeoPackage":
                    dictionary_of_checked_database_sources["providers"].append(item_text)
                else:
                    dictionary_of_checked_web_sources[parent_text].append(item_text)

        return dictionary_of_checked_web_sources, dictionary_of_checked_database_sources
