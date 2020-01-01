# -*- encoding: utf-8 -*-

import re
import os
from xml.dom import minidom


class MavenArtifact(object):
    """A maven artifact"""

    def __init__(self, group_id, artifact_id, version):
        self.group_id = group_id
        self.artifact_id = artifact_id
        self.version = version
        pass

    def __str__(self):
        return "%s:%s:%s" % (self.group_id, self.artifact_id, self.version)

    def __eq__(self, other):
        if not isinstance(other, MavenArtifact):
            return False
        return (self.group_id == other.group_id
                and self.artifact_id == other.artifact_id
                and self.version == other.version)

    def __hash__(self):
        return hash(str(self))

    def maven_key(self):
        return "%s:%s" % (self.group_id, self.artifact_id)

    def is_snapshot(self):
        return self.version.endswith("SNAPSHOT")

    def repository_dir_path(self):
        """获取在maven仓库中的文件夹路径
        :return:
        """
        return "%s/%s/%s" % (self.group_id.replace(".", "/"),
                             self.artifact_id,
                             self.version)

    def artifact_name(self, ext):
        """获取maven仓库中文件文件名
        :param ext:
        :return:
        """
        return "%s-%s%s" % (self.artifact_id, self.version, ext)

    def repository_full_path(self, ext):
        """获取maven仓库中文件的全路径
        :param ext:
        :return:
        """
        return "%s/%s" % (self.repository_dir_path(),
                          self.artifact_name(ext))

    @staticmethod
    def parse_maven_dep(artifact):
        m = re.match("(.*?):(.*?):(.*)", artifact)
        if m:
            return MavenArtifact(group_id=m.group(1),
                                 artifact_id=m.group(2),
                                 version=m.group(3))
        raise Exception("'%s' can't be parsed" % artifact)

    pass


class PomParser:
    def __init__(self, pom_path):
        self._pom_path = pom_path
        self._dom = minidom.parse(pom_path)
        pass

    def parse(self, config):
        """解析pom树
        :param config:
        :return:
        """
        for node in self._dom.documentElement.childNodes:
            if node.nodeType not in (node.ELEMENT_NODE,):
                continue

            if node.tagName in ("groupId", "artifactId", "version", "packaging", "name", "description", "url"):
                config[node.tagName] = node.firstChild.data
            elif node.tagName == "dependencies":
                dependencies = []
                dependencies.extend(PomParser.parse_dependencies(node))
                config[node.tagName] = dependencies
            elif node.tagName == "properties":
                config["properties"] = PomParser.parse_properties(node)
            pass
        if "dependencies" not in config:
            config["dependencies"] = []
        pass

    @staticmethod
    def parse_dependencies(element):
        dep_list = []
        for node in element.childNodes:
            if node.nodeType != node.ELEMENT_NODE:
                continue
            if node.tagName != "dependency":
                continue
            dep_list.append(PomParser.parse_dependency(node))
            pass
        return dep_list

    @staticmethod
    def parse_dependency(element):
        config = {}
        for node in element.childNodes:
            if node.nodeType != node.ELEMENT_NODE:
                continue
            if node.tagName in ("groupId", "artifactId", "version", "type", "scope"):
                config[node.tagName] = node.firstChild.data
            pass
        return config

    @staticmethod
    def parse_properties(element):
        properties = {}
        for node in element.childNodes:
            if node.nodeType != node.ELEMENT_NODE:
                continue
            if node.firstChild is not None:
                properties[node.tagName] = node.firstChild.data
        return properties


class MavenM2:
    def __init__(self, m2_home):
        self._m2_home = os.path.abspath(os.path.normpath(m2_home))
        self._m2_files = os.path.join(self._m2_home, "files")
        self._m2_build = os.path.join(self._m2_home, "build")
        pass

    def m2_home(self):
        return self._m2_home

    def m2_files(self):
        return self._m2_files

    def maven_client_path(self, artifact: MavenArtifact, ext):
        return os.path.join(self.m2_files(), artifact.repository_full_path(ext=ext))


class MavenPomConfig:
    def __init__(self, pom_config):
        self.pom_config = pom_config
        pass

    def get_list(self, name, force=False, default=None):
        if default is None:
            default = []

        config = self.pom_config
        for item in name.split("."):
            if config is None and not force:
                return default
            config = config.get(item, None)
            pass
        if config is None:
            return default
        elif isinstance(config, list):
            return config
        return [config]


class MavenPom:
    def __init__(self, artifact: MavenArtifact, pom_config, parent_pom=None):
        self.artifact = artifact
        self.pom_config = pom_config
        self.parent_pom = parent_pom
        pass

    def get_managed_depend(self, group_id, artifact_id):
        project = self.pom_config["project"]
        if "pom" == project.get("packaging"):
            for dep_item in MavenPomConfig(project).get_list("dependencyManagement.dependencies.dependency"):
                if group_id == dep_item["groupId"] and artifact_id == dep_item["artifactId"]:
                    return dep_item
        if self.parent_pom:
            return self.parent_pom.get_managed_depend(group_id, artifact_id)
        return None

    def get_depends(self, wanted_list=("compile",)):
        dep_list = []
        for dep_item in MavenPomConfig(self.pom_config).get_list("project.dependencies.dependency"):
            scope = dep_item.get("scope", "compile")
            if scope not in wanted_list:
                continue
            dep_list.append(dep_item)
        return dep_list


class MavenContext:
    def __init__(self):
        self._pom_map = {}
        pass

    def maven_pom(self, artifact, force=False) -> MavenPom:
        pom = self._pom_map.get(artifact)
        if pom is None and force:
            raise Exception("pom %s can't be found" % artifact)
        return pom

    def add_maven_pom(self, maven_pom: MavenPom):
        self._pom_map[maven_pom.artifact] = maven_pom
