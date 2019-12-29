# -*- encoding: utf-8 -*-

import argparse
import io
import os
import urllib.request
from urllib.request import OpenerDirector
from urllib.error import HTTPError
import hashlib

from util import build_utils
from util.maven import MavenArtifact
from util.maven import PomParser
from http import HTTPStatus

GOOGLE_MAVEN_REPO = "https://maven.aliyun.com/repository/google/"
ALIYUN_MAVEN_REPO1 = "http://maven.aliyun.com/nexus/content/repositories/central/"
MAVEN2_REPO1 = "https://repo1.maven.org/maven2/"

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.88 Safari/537.36"


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


class MavenConfig:
    def __init__(self, artifact: MavenArtifact, config: dict):
        self._artifact = artifact
        self._config = config
        pass

    def _fulfill_template(self, template):
        if "${" not in template:
            return template
        if "properties" not in self._config:
            return template
        for key, value in self._config["properties"].items():
            template = template.replace("${%s}" % key, value)
            if "${" not in template:
                break
        return template

    def deps_list(self):
        dep_list = []
        for dep_item in self._config["dependencies"]:
            if "scope" in dep_item and dep_item["scope"] == "test":
                continue

            artifact_str = "%s:%s:%s" % (self._fulfill_template(dep_item["groupId"]),
                                         self._fulfill_template(dep_item["artifactId"]),
                                         self._fulfill_template(dep_item["version"]))
            if artifact_str not in dep_list:
                dep_list.append(artifact_str)
        return dep_list


class MavenDownloadContext:
    MAVEN_CHECKSUM_LIST = ("md5", "asc", "sha1", "sha256")

    def __init__(self, artifact: MavenArtifact, m2_files_dir, maven_url, opener: urllib.request.OpenerDirector):
        self._artifact = artifact
        self._m2_files_dir = m2_files_dir
        self._maven_center = maven_url
        self._maven_opener = opener
        self._user_agent = USER_AGENT

        self._base_dir = os.path.join(m2_files_dir, artifact.group_id, artifact.artifact_id, artifact.version)
        self._base_dir = os.path.normpath(self._base_dir)
        self._pom_config = {}
        self._maven_config = None
        pass

    def select_maven_center(self, maven_list):
        maven_center = None
        for maven_url in maven_list:
            if self.check_maven_url_exists(self.maven_server_url(".pom", maven_url)):
                maven_center = maven_url
                break
        if maven_center is None:
            raise Exception("maven center can't be found for '%s'" % str(self._artifact))
        self._maven_center = maven_center
        print("MAVEN CENTER: %s -> %s" % (str(self._artifact), maven_center))
        pass

    def download(self):
        build_utils.make_directory(self._base_dir)

        self.download_maven_file(ext=".pom", force=True, checksum=True)
        pom_config = self._pom_config
        pom_parser = PomParser(self.maven_client_path(".pom"))
        pom_parser.parse(pom_config)
        if "packaging" not in pom_config:
            pom_config["packaging"] = "jar"

        self._maven_config = MavenConfig(self._artifact, pom_config)
        pom_config_path = self.maven_client_path(ext=".pom.json")
        build_utils.write_json(pom_config, pom_config_path)

        self._download_maven_files(pom_config)
        pass

    def _download_maven_files(self, pom_config):
        packaging = pom_config["packaging"]
        if packaging == "jar":
            self._download_jar_maven(pom_config)
        elif packaging == "aar":
            self._download_aar_maven(pom_config)
        else:
            print("Unknown packaging type: %s" % packaging)
        pass

    def _download_jar_maven(self, pom_config):
        self.download_maven_file(ext=".jar")
        self.download_maven_file(ext="-javadoc.jar", force=False, checksum=True)
        self.download_maven_file(ext="-sources.jar", force=False, checksum=True)
        pass

    def _download_aar_maven(self, pom_config):
        self.download_maven_file(ext=".aar")
        pass

    def maven_server_url(self, ext, maven_center=None):
        if maven_center is None:
            maven_center = self._maven_center
        if maven_center is None:
            raise Exception("maven center not specified")
        return "%s%s" % (maven_center, self._artifact.repository_full_path(ext))

    def maven_client_path(self, ext):
        return os.path.join(self._base_dir, self._artifact.artifact_name(ext=ext))

    def download_pom_file(self):
        pom_url = self.maven_server_url(".pom")
        pom_path = self.maven_client_path(".pom")

        # 下载对应文件的摘要文件
        md5_method = self.check_maven_url_checksum(pom_url)
        pom_md5_url = pom_url + "." + md5_method
        pom_md5_path = pom_path + "." + md5_method
        dst_md5 = self.download_file(pom_md5_url, pom_md5_path, text=True)

        self.download_file(pom_url, pom_path)
        src_md5 = md5_for_path(pom_path, md5=md5_method)
        if src_md5 != dst_md5:
            raise Exception("Md5 error for '%s', src_md5=%s, dst_md5=%s" % (pom_url, src_md5, dst_md5))

        pass

    def create_maven_request(self, url):
        request = urllib.request.Request(url)
        request.add_header("user-agent", self._user_agent)
        return request

    def download_maven_file(self, ext, force=True, checksum=True):
        maven_url = self.maven_server_url(ext)
        file_path = self.maven_client_path(ext)

        r = self.download_file(maven_url, file_path, force=force)
        if not r:
            return False

        if not checksum:
            return True

        # 下载对应文件的摘要文件
        md5_str = self.check_maven_url_checksum(maven_url)
        md5_maven_url = maven_url + "." + md5_str
        md5_file_path = file_path + "." + md5_str
        dst_md5 = self.download_file(md5_maven_url, md5_file_path, force=True, text=True)
        if dst_md5:
            dst_md5 = dst_md5.strip()

        src_md5 = md5_for_path(file_path, md5=md5_str)
        if src_md5 != dst_md5:
            raise Exception("Md5 error for '%s', src_md5=%s, dst_md5=%s" % (maven_url, src_md5, dst_md5))

        return True

    def download_file(self, maven_url, client_path, force=True, text=False):
        """下载对应的maven url到文件里面
        :param maven_url:
        :param client_path:
        :param force: 已经要下载成功
        :param text:
        :return:
        """
        build_utils.make_directory(os.path.dirname(client_path))

        print("DOWNLOAD file: %s" % maven_url)
        try:
            request = self.create_maven_request(maven_url)
            with self._maven_opener.open(request) as response:
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

    def check_maven_url_checksum(self, maven_url, *, force=True, checksum_list=MAVEN_CHECKSUM_LIST):
        """检查对应的摘要算法
        :param maven_url:
        :param force:
        :param checksum_list:
        :return:
        """
        for checksum in checksum_list:
            url = maven_url + "." + checksum
            if self.check_maven_url_exists(url):
                return checksum
        if force:
            raise Exception("check_maven_url_checksum: can't find checksum, maven_url=%s" % maven_url)
        return None

    def check_maven_url_exists(self, maven_url):
        """获取对应的资源的摘要方式
        :param maven_url:
        :return:
        """
        request = urllib.request.Request(maven_url, method="HEAD")
        try:
            with self._maven_opener.open(request) as response:
                if response.code != 200:
                    return False
                return True
        except HTTPError as e:
            if e.code != HTTPStatus.NOT_FOUND.value:
                raise e
            return False

    def maven_dep_list(self):
        return self._maven_config.deps_list()


def create_parser():
    parser = argparse.ArgumentParser(prog="maven_download.py")
    parser.add_argument("--m2-dir", required=True,
                        help="The destination directory.")
    parser.add_argument("--artifact")
    return parser


def main():
    parser = create_parser()
    args = parser.parse_args()

    context_map = {}
    pending_list = [args.artifact]
    maven_center_list = [GOOGLE_MAVEN_REPO,
                         ALIYUN_MAVEN_REPO1,
                         MAVEN2_REPO1]

    opener = urllib.request.build_opener()
    maven_properties = {}

    while pending_list:
        artifact_str = pending_list.pop(0)
        print("Download %s" % artifact_str)

        artifact = MavenArtifact.parse_maven_dep(artifact_str)
        maven_properties["version.%s" % artifact.artifact_id] = artifact.version
        context = MavenDownloadContext(artifact=artifact, m2_files_dir=args.m2_dir,
                                       maven_url=GOOGLE_MAVEN_REPO,
                                       opener=opener)
        context_map[artifact_str] = context
        context.select_maven_center(maven_center_list)
        context.download()

        dep_list = context.maven_dep_list()
        if dep_list:
            print("%s DEPS:" % artifact_str)
            for dep_item in dep_list:
                print("    -> %s" % dep_item)
            pending_list.extend(dep_item for dep_item in context.maven_dep_list()
                                if dep_item not in pending_list and dep_item not in context_map)
        pass
    pass


if __name__ == '__main__':
    main()
    pass
