# -*- encoding: utf-8 -*-

import argparse
import io
import os
import urllib.request

from util import build_utils
from util.maven import MavenArtifact
from util.maven import PomParser

MAVEN_REPO = "https://maven.aliyun.com/repository/google/"


class MavenDownloadContext:
    MAVEN_CHECKSUM_LIST = ("md5", "sha1", "sha256")

    def __init__(self, artifact: MavenArtifact, m2_files_dir, maven_url, opener: urllib.request.OpenerDirector):
        self._artifact = artifact
        self._m2_files_dir = m2_files_dir
        self._maven_url = maven_url
        self._maven_opener = opener

        self._base_dir = os.path.join(m2_files_dir, artifact.group_id, artifact.artifact_id, artifact.version)
        self._base_dir = os.path.normpath(self._base_dir)
        self._pom_config = {}
        pass

    def download(self):
        build_utils.make_directory(self._base_dir)

        self.download_pom_file()
        pom_config = self._pom_config
        pom_parser = PomParser(self.maven_client_path(".pom"))
        pom_parser.parse(pom_config)

        pom_config_path = self.maven_client_path(ext=".json")
        build_utils.write_json(pom_config, pom_config_path)

        pass

    def maven_server_url(self, ext):
        return "%s%s" % (self._maven_url, self._artifact.repository_full_path(ext))

    def maven_client_path(self, ext):
        return os.path.join(self._base_dir, self._artifact.artifact_name(ext=ext))

    def download_pom_file(self):
        pom_url = self.maven_server_url(".pom")
        pom_path = self.maven_client_path(".pom")

        # 下载对应文件的摘要文件
        md5_method = self.check_maven_url_checksum(pom_url)
        pom_md5_url = pom_url + "." + md5_method
        pom_md5_path = pom_path + "." + md5_method
        checksum = self.download_file(pom_md5_url, pom_md5_path, text=True)

        self.download_file(pom_url, pom_path)
        pass

    def download_file(self, maven_url, client_path, text=False):
        """下载对应的maven url到文件里面
        :param maven_url:
        :param client_path:
        :param text:
        :return:
        """
        build_utils.make_directory(os.path.dirname(client_path))

        with self._maven_opener.open(maven_url) as response:
            if response.code != 200:
                raise Exception("can't download maven_url=%s" % maven_url)

            with open(client_path, mode="wb") as fp:
                while True:
                    data = response.read(io.DEFAULT_BUFFER_SIZE)
                    if not data:
                        break
                    fp.write(data)
                pass

        if text:
            with open(client_path, mode="r", encoding="utf-8") as fp:
                return fp.read(-1)

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
        with self._maven_opener.open(maven_url) as response:
            if response.code != 200:
                return False
            return True


def create_parser():
    parser = argparse.ArgumentParser(prog="maven_download.py")
    parser.add_argument("--m2-dir", required=True,
                        help="The destination directory.")
    parser.add_argument("--artifact")
    return parser


def main():
    parser = create_parser()
    args = parser.parse_args()

    artifact = MavenArtifact.parse_maven_dep(args.artifact)

    opener = urllib.request.build_opener()
    context = MavenDownloadContext(artifact=artifact, m2_files_dir=args.m2_dir,
                                   maven_url=MAVEN_REPO,
                                   opener=opener)
    context.download()
    pass


if __name__ == '__main__':
    main()
    pass
