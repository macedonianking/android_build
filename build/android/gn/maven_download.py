# -*- encoding: utf-8 -*-

import argparse
import hashlib
import io
import json
import os
import re
import urllib.request
from copy import deepcopy
from http import HTTPStatus
from urllib.error import HTTPError
from urllib.request import OpenerDirector

import xmltodict

from util import build_utils
from util.maven import MavenArtifact
from util.maven import MavenM2
from util.maven import MavenPomConfig
from util.maven import MavenPom
from util.maven import MavenContext
from maven_target import MavenTargetContext

GOOGLE_MAVEN_REPO = "https://maven.aliyun.com/repository/google/"
ALIYUN_MAVEN_REPO1 = "http://maven.aliyun.com/nexus/content/repositories/central/"
MAVEN2_REPO1 = "https://repo1.maven.org/maven2/"

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.88 Safari/537.36"

LOG_STEP = "  "


def _update_md5_for_path(md5_obj, path):
    with open(path, mode="rb") as fp:
        while True:
            data = fp.read(io.DEFAULT_BUFFER_SIZE)
            if not data:
                break
            md5_obj.update(data)
            pass
    pass


def md5_for_path(path, md5="md5"):
    """获取文件摘要
    :param path:
    :param md5:
    :return:
    """
    md5_obj = getattr(hashlib, md5)()
    _update_md5_for_path(md5_obj, path)
    return md5_obj.hexdigest()


class MavenMetadata(object):
    def __init__(self):
        self._outputs_list = {}
        pass

    @classmethod
    def from_file(cls, fp):
        ret = cls()
        obj = json.load(fp)
        ret._outputs_list = obj["output_list"]
        return ret

    def to_file(self, fp):
        obj = {"output_list": self._outputs_list}
        json.dump(obj, fp=fp, sort_keys=True, indent=2)
        pass

    def add_output_file(self, path):
        path = os.path.abspath(os.path.normpath(path))
        md_obj = MavenMetadata.file_md5(path)
        self._outputs_list[path] = {"mtime": md_obj[0], "size": md_obj[1]}
        pass

    def iter_outputs(self):
        ret = list(self._outputs_list.keys())
        ret.sort()
        return ret

    def output_md5(self, path):
        md5_obj = self._outputs_list.get(path)
        if md5_obj:
            return md5_obj["mtime"], md5_obj["size"]
        return None

    @staticmethod
    def file_md5(path):
        stat_obj = os.stat(path)
        return stat_obj.st_mtime_ns, stat_obj.st_size

    def check_modified(self):
        for path in self._outputs_list:
            dst_md5 = MavenMetadata.file_md5(path)
            if not dst_md5:
                return True
            src_md5 = self.output_md5(path)
            if not src_md5:
                return True
            if src_md5 != dst_md5:
                return True
        return False


class MavenLoader:
    def __init__(self, maven_centers, maven_m2: MavenM2, opener: OpenerDirector):
        self.maven_centers = maven_centers
        self.maven_m2 = maven_m2
        self.opener = opener
        pass

    def get_opener(self) -> OpenerDirector:
        return self.opener

    def choose_maven_center(self, artifact, step):
        for maven_center in self.maven_centers:
            loader = MavenArtifactLoader(artifact, self, maven_center, step)
            if loader.check_maven_file_existed(loader.maven_server_path(ext=".pom")):
                return loader

        return None


class MavenArtifactLoader:
    MAVEN_CHECKSUM_LIST = ("md5", "asc", "sha1", "sha256")

    def __init__(self, artifact: MavenArtifact, loader: MavenLoader, maven_center, step):
        self._artifact = artifact
        self._loader = loader
        self._opener = loader.get_opener()
        if not maven_center.endswith("/"):
            maven_center += "/"
        self._maven_center = maven_center
        self._user_agent = USER_AGENT
        self.new_metadata = MavenMetadata()
        self.step = step
        self.log_prefix = LOG_STEP * step
        pass

    def maven_server_path(self, ext):
        return "%s%s" % (self._maven_center, self._artifact.repository_full_path(ext))

    def maven_server_artifact_directory(self):
        return "%s%s" % (self._maven_center, self._artifact.repository_dir_path())

    def maven_client_path(self, ext):
        return self._loader.maven_m2.maven_client_path(self._artifact, ext)

    def create_maven_request(self, url):
        request = urllib.request.Request(url)
        request.add_header("user-agent", self._user_agent)
        return request

    def download_file(self, maven_url, client_path, force=True, text=False):
        build_utils.make_directory(os.path.dirname(client_path))

        print("%sDOWNLOAD file: %s" % (self.log_prefix, maven_url))
        try:
            request = self.create_maven_request(maven_url)
            with self._opener.open(request) as response:
                if response.code != 200:
                    if force:
                        raise Exception("can't download maven_url=%s" % maven_url)
                    else:
                        return False

                with open(client_path, mode="wb") as fp:
                    while True:
                        data = response.read(io.DEFAULT_BUFFER_SIZE)
                        if not data:
                            break
                        fp.write(data)
                    pass
        except HTTPError as e:
            if force:
                raise RuntimeError(e, "%s" % maven_url)
            return False

        if text:
            with open(client_path, mode="r", encoding="utf-8") as fp:
                return fp.read(-1)
        return True

    def download_maven_file(self, ext, force=True, checksum=True, add_metadata=True):
        server_path = self.maven_server_path(ext)
        client_path = self.maven_client_path(ext)

        r = self.download_file(server_path, client_path, force=force)
        if not r:
            return False

        if add_metadata:
            self.new_metadata.add_output_file(client_path)
        if not checksum:
            return True

        md5_str = self.check_maven_url_checksum(server_path)
        md5_maven_url = server_path + "." + md5_str
        md5_file_path = client_path + "." + md5_str
        dst_md5 = self.download_file(md5_maven_url, md5_file_path, force=True, text=True)
        if dst_md5:
            dst_md5 = dst_md5.strip()

        src_md5 = md5_for_path(client_path, md5=md5_str)
        if src_md5 != dst_md5:
            raise Exception("Md5 error for '%s', src_md5=%s, dst_md5=%s" % (server_path, src_md5, dst_md5))
        return True

    def check_maven_url_checksum(self, maven_url, *, force=True, checksum_list=MAVEN_CHECKSUM_LIST):
        for checksum in checksum_list:
            url = maven_url + "." + checksum
            if self.check_maven_file_existed(url):
                return checksum
        if force:
            raise Exception("check_maven_url_checksum: can't find checksum, maven_url=%s" % maven_url)
        return None

    def check_maven_file_existed(self, maven_url):
        request = urllib.request.Request(maven_url, method="HEAD")
        try:
            with self._opener.open(request) as response:
                if response.code != 200:
                    return False
                return True
        except HTTPError as e:
            if e.code != HTTPStatus.NOT_FOUND.value:
                raise e
            return False


def read_pom_config(path):
    with open(path, mode="rb") as fp:
        return xmltodict.parse(fp)


def _read_old_metadata(path):
    if os.path.exists(path):
        with open(path, mode="r") as fp:
            try:
                return MavenMetadata.from_file(fp)
            except:
                pass
    return None


def substitute_maven_pom_variables(template_str, variables):
    subs_list = {}
    for m in re.finditer(r"\${(.*?)}", template_str):
        k = m.group(1)
        v = variables[k]
        subs_list[k] = v

    for k, v in subs_list.items():
        template_str = str.replace(template_str, "${%s}" % k, v)
    return template_str


class MavenDownload:
    def __init__(self, context: MavenContext, loader: MavenLoader, artifact: MavenArtifact, step):
        self.context = context
        self.loader = loader
        self.artifact = artifact
        self.step = step
        self.log_prefix = LOG_STEP * step
        pass

    def download(self, force=False):
        print("%sDOWNLOAD: %s" % (self.log_prefix, self.artifact))
        md5_path = self.loader.maven_m2.maven_client_path(self.artifact, ext=".metadata")
        old_metadata = _read_old_metadata(md5_path)

        if force or not old_metadata or old_metadata.check_modified():
            # 重新下载
            loader = self._download_impl(force)

            new_metadata = loader.new_metadata
            with open(md5_path, mode="w+", encoding="utf8") as fp:
                new_metadata.to_file(fp)
        else:
            # 从缓存构建
            self._initiate_impl()
            pass

    def _fulfill_dep_item(self, dep_item, parent_pom: MavenPom, properties):
        parent_dep_item = None
        if parent_pom:
            parent_dep_item = parent_pom.get_managed_depend(dep_item["groupId"], dep_item["artifactId"])

        for name in ("version",):
            last = dep_item.get(name)
            curr = last
            if curr is None and parent_dep_item:
                curr = parent_dep_item.get(name)
            if last != curr:
                dep_item[name] = curr
                # print("%s,%s : %s -> %s" % (dep_item["groupId"],
                #                             dep_item["artifactId"], name, curr))
            if "${" in curr:
                last = curr
                curr = substitute_maven_pom_variables(last, properties)
                # print("%s:%s -> %s=%s to %s" % (dep_item["groupId"],
                #                                 dep_item["artifactId"],
                #                                 name, last, curr))
                dep_item[name] = curr
        pass

    def _fulfill_effective_pom_config(self, pom_config, force=False):
        """填充pom_config为完整的pom_config"""
        config = pom_config["project"]

        parent_pom = None
        parent_artifact = self._get_parent_artifact_from_pom_config(pom_config)
        if parent_artifact and not self.context.maven_pom(parent_artifact):
            parent_download = MavenDownload(self.context, self.loader, parent_artifact, self.step + 1)
            parent_download.download(force)
            parent_pom = self.context.maven_pom(parent_artifact, force=True)
            pass

        properties = {}
        if "properties" in config:
            properties = config["properties"]

        if parent_pom and "properties" in parent_pom.pom_config["project"]:
            parent_property = parent_pom.pom_config["project"]["properties"]
            parent_property = deepcopy(parent_property)
            parent_property.update(properties)
            properties = parent_property

        config["properties"] = properties

        for dep_item in MavenPomConfig(config).get_list("dependencies.dependency"):
            self._fulfill_dep_item(dep_item, parent_pom, properties)
            pass

    def _initiate_impl(self):
        maven_m2 = self.loader.maven_m2
        pom_config = build_utils.read_json(
            maven_m2.maven_client_path(self.artifact, ext=".pom.json"))

        pom_effective_config = deepcopy(pom_config)
        self._fulfill_effective_pom_config(pom_effective_config)

        parent_artifact = self._get_parent_artifact_from_pom_config(pom_effective_config)
        parent_pom = None
        if parent_artifact:
            parent_pom = self.context.maven_pom(parent_artifact, force=True)

        maven_pom = MavenPom(self.artifact, pom_effective_config, parent_pom)
        self.context.add_maven_pom(maven_pom)
        pass

    def _get_parent_artifact_from_pom_config(self, pom_config):
        project_config = pom_config["project"]
        if "parent" in project_config:
            parent_config = project_config["parent"]
            return MavenArtifact(parent_config["groupId"],
                                 parent_config["artifactId"],
                                 parent_config["version"])
        return None

    def _download_impl(self, force=False):
        loader = self.loader.choose_maven_center(self.artifact, self.step)
        if not loader:
            raise Exception("Can't find maven center for {}".format(self.artifact))

        loader.download_maven_file(ext=".pom", force=True, checksum=True)
        pom_originals_config = read_pom_config(loader.maven_client_path(ext=".pom"))
        with open(loader.maven_client_path(".pom.json"), mode="w", encoding="utf-8") as fp:
            json.dump(obj=pom_originals_config, fp=fp, indent=2)

        pom_effective_config = deepcopy(pom_originals_config)
        self._fulfill_effective_pom_config(pom_effective_config, force)
        with open(loader.maven_client_path(".pom.effective.json"), mode="w", encoding="utf-8") as fp:
            json.dump(obj=pom_effective_config, fp=fp, indent=2)

        self._download_maven_files(pom_effective_config, loader)

        parent_pom = None
        parent_artifact = self._get_parent_artifact_from_pom_config(pom_effective_config)
        if parent_artifact:
            parent_pom = self.context.maven_pom(parent_artifact, force=True)

        maven_pom = MavenPom(self.artifact, pom_effective_config, parent_pom=parent_pom)
        self.context.add_maven_pom(maven_pom)

        return loader

    def _download_maven_files(self, pom_config, loader):
        packaging = pom_config["project"].get("packaging", "jar")
        if packaging == "jar":
            self._download_jar_maven(loader)
        elif packaging == "aar":
            self._download_aar_maven(loader)
        elif packaging == "bundle":
            self._download_bundle_maven(loader)
        elif packaging == "pom":
            self._download_pom_maven(loader)
        else:
            raise Exception(
                "Unknown packaging type: %s %s: url=%s" % (self.artifact, packaging,
                                                           loader.maven_server_artifact_directory()))
        pass

    def _download_bundle_maven(self, loader: MavenArtifactLoader):
        loader.download_maven_file(ext=".jar")
        loader.download_maven_file(ext="-javadoc.jar", force=False, checksum=True)
        loader.download_maven_file(ext="-sources.jar", force=False, checksum=True)
        pass

    def _download_jar_maven(self, loader: MavenArtifactLoader):
        loader.download_maven_file(ext=".jar")
        loader.download_maven_file(ext="-javadoc.jar", force=False, checksum=True)
        loader.download_maven_file(ext="-sources.jar", force=False, checksum=True)
        pass

    def _download_aar_maven(self, loader: MavenArtifactLoader):
        loader.download_maven_file(ext=".aar")
        pass

    def _download_pom_maven(self, loader: MavenArtifactLoader):
        pass

    pass


def create_parser():
    parser = argparse.ArgumentParser(prog="maven_download.py")
    parser.add_argument("--m2-dir", required=True,
                        help="The destination directory.")
    parser.add_argument("--src-root")
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--target-json", required=True)
    parser.add_argument("--artifact", action="append", default=[])
    return parser


def parse_args():
    parser = create_parser()
    args = parser.parse_args()
    return args


def download_maven(args, context, m2_home, root_artifacts):
    maven_center_list = [GOOGLE_MAVEN_REPO,
                         ALIYUN_MAVEN_REPO1,
                         MAVEN2_REPO1]
    pending_list = list(root_artifacts)

    loader = MavenLoader(maven_centers=maven_center_list,
                         maven_m2=m2_home,
                         opener=urllib.request.build_opener())
    while pending_list:
        artifact = pending_list.pop(0)
        download_context = MavenDownload(context, loader, artifact, 0)
        download_context.download(force=False)
        maven_pom = context.maven_pom(artifact)
        for dep_item in maven_pom.get_depends(wanted_list=("compile", "provided")):
            artifact = MavenArtifact(dep_item["groupId"], dep_item["artifactId"], dep_item["version"])
            if context.maven_pom(artifact):
                continue
            if artifact in pending_list:
                continue
            pending_list.append(artifact)
            pass


def to_gn_absolute_path(root_path, path):
    name = os.path.relpath(os.path.abspath(path), root_path)
    return "//" + name.replace("\\", "/")


def to_gn_target_name(artifact):
    return artifact.replace("-", "_").replace(":", "_").replace(".", "_")


def write_build_config(target_configs, sorted_targets, m2_home: MavenM2, root_path, target_json_path):
    build_config = {
        "deps_info": []
    }
    deps_info = build_config["deps_info"]

    for dep_name in sorted_targets:
        artifact = MavenArtifact.parse_maven_dep(dep_name)
        src_config = target_configs[artifact.maven_key()]
        dst_config = {
            "name": to_gn_target_name(str(artifact)),
            "maven_depname": str(artifact),
            "deps": []
        }

        packaging = src_config["packaging"]
        assert (packaging in ("jar", "aar", "bundle"))
        if packaging in ("jar", "bundle"):
            jar_path = m2_home.maven_client_path(artifact, ext=".jar")
            dst_config["type"] = "android_maven_jar"
            dst_config["file_path"] = to_gn_absolute_path(root_path, jar_path)

        if packaging == "aar":
            aar_path = m2_home.maven_client_path(artifact, ext=".aar")
            dst_config["type"] = "android_maven_aar"
            dst_config["file_path"] = to_gn_absolute_path(root_path, aar_path)

        for item in src_config["deps_info"]:
            dst_config["deps"].append(":" + to_gn_target_name(item))

        deps_info.append(dst_config)
        pass

    build_utils.make_directory_for_file(target_json_path)
    build_utils.write_json(build_config, target_json_path)
    pass


def generate_config(args, context, maven_m2, root_artifacts):
    target_context = MavenTargetContext(context, maven_m2, root_artifacts=root_artifacts)

    target_configs = target_context.generate_dep_configs(root_artifacts)
    build_utils.make_directory_for_file(args.output_json)
    build_utils.write_json(target_configs, args.output_json)

    root_targets = [str(x) for x in root_artifacts]

    def get_deps(dep):
        dep_artifact = MavenArtifact.parse_maven_dep(dep)
        return set(target_configs[dep_artifact.maven_key()]["deps_info"])

    sorted_targets = build_utils.get_sorted_transitive_dependencies(root_targets, get_deps)
    print(sorted_targets)

    write_build_config(target_configs, sorted_targets, maven_m2, args.src_root, args.target_json)
    pass


def main():
    args = parse_args()

    root_targets = [MavenArtifact.parse_maven_dep(x) for x in args.artifact]

    context = MavenContext()
    maven_m2 = MavenM2(args.m2_dir)

    download_maven(args, context, maven_m2, root_targets)
    generate_config(args, context, maven_m2, root_targets)
    pass


if __name__ == '__main__':
    main()
    pass
