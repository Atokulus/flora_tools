import os
import xml.etree.ElementTree

from flora_tools.toolchain.include_paths import *
from flora_tools.toolchain.platforms import *


class EclipsePatcher:
    def __init__(self, flora_path, platform: Platform):
        self.flora_path = flora_path
        self.platform = platform
        self.et = None

    def patch(self):
        self.load_element_tree()
        for node in self.include_path_option_nodes:
            self.insert_include_paths(node)
        self.insert_symbols()
        self.insert_linked_resources()
        self.store_element_tree()
        print("Patched {} eclipse project.".format(self.platform))

    def insert_symbols(self):
        for target in Target:
            symbols = Platform.get_symbols(self.platform, target)
            xpath = SYMBOLS_XPATH[target]

            node = self.et.find(xpath)
            if node is not None:
                for symbol in symbols:
                    if node.find("./{}[@value='{}']".format(OPTION_ITEM_TAG['name'], symbol)) is None:
                        include_path_tag = xml.etree.ElementTree.SubElement(node, OPTION_ITEM_TAG['name'])
                        include_path_tag.attrib['builtIn'] = OPTION_ITEM_TAG['builtIn']
                        include_path_tag.attrib['value'] = symbol

    def insert_include_paths(self, node):
        for path in INCLUDE_PATHS:
            self.insert_include_path(node, path)

    def insert_linked_resources(self):
        if self.et is not None:

            xpath = './/sourceEntries'
            source_entries_tags = self.et.findall(xpath)

            for source_entries in source_entries_tags:
                xpath = './entry[@name="lib"]'
                entry = source_entries.find(xpath)

                if entry is None:
                    entry = xml.etree.ElementTree.SubElement(source_entries, 'entry', attrib={
                        'excluding': 'protocol/glossy|protocol/old',
                        'flags': 'VALUE_WORKSPACE_PATH|RESOLVED',
                        'kind': 'sourcePath',
                        'name': 'lib',
                    })

            project_et = xml.etree.ElementTree.parse(
                os.path.join(self.flora_path, Platform.get_project_path(self.platform)))
            # xpath = './/linkedResources/link[/name/text()="lib"]' # Not working yet in ElementTree library
            xpath = './/linkedResources/link'
            links = project_et.findall(xpath)

            link_found = False
            for link in links:
                if link.find('name').text in ['lib']:
                    link_found = True

            if not link_found:
                xpath = './/linkedResources'
                link_resources = project_et.find(xpath)
                link = xml.etree.ElementTree.SubElement(link_resources, 'link')
                name = xml.etree.ElementTree.SubElement(link, 'name')
                name.text = 'lib'
                type = xml.etree.ElementTree.SubElement(link, 'type')
                type.text = '2'
                location = xml.etree.ElementTree.SubElement(link, 'location')
                location.text = '$%7BPARENT-2-PROJECT_LOC%7D/lib'

                if project_et is not None:
                    xml_string = xml.etree.ElementTree.tostring(project_et.getroot(), encoding="unicode")

                    file = open(
                        "{}".format(os.path.join(self.flora_path, Platform.get_project_path(self.platform)), 'w'))
                    file.writelines([
                        '<?xml version = "1.0" encoding = "UTF-8"?>',
                    ])
                    file.write(xml_string)
                    file.close()

    @staticmethod
    def insert_include_path(node, path):
        value = OPTION_ITEM_TAG['value'].format(path)
        if node.find("./{}[@value='{}']".format(OPTION_ITEM_TAG['name'], value)) is None:
            include_path_tag = xml.etree.ElementTree.SubElement(node, OPTION_ITEM_TAG['name'])
            include_path_tag.attrib['builtIn'] = OPTION_ITEM_TAG['builtIn']
            include_path_tag.attrib['value'] = value

    def load_element_tree(self):
        self.et = xml.etree.ElementTree.parse(os.path.join(self.flora_path, Platform.get_cproject_path(self.platform)))

    def store_element_tree(self):
        if self.et is not None:
            xml_string = xml.etree.ElementTree.tostring(self.et.getroot(), encoding="unicode")

            file = open("{}".format(os.path.join(self.flora_path, Platform.get_cproject_path(self.platform))), 'w')
            file.writelines([
                '<?xml version = "1.0" encoding = "UTF-8"?>',
                '<?fileVersion 4.0.0?>'
            ])
            file.write(xml_string)
            file.close()

            # self.et.write("{}".format(Platform.get_cproject_path(self.platform)), encoding='UTF-8', xml_declaration=True)

    @property
    def include_path_option_nodes(self):
        nodes = []
        for search in INCLUDE_XPATH:
            nodes.extend(self.et.findall(search))
        return nodes
