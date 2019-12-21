# -*- encoding: utf-8 -*-

import urllib.request
import re
import os
import argparse

MAVEN_REPO = "https://maven.aliyun.com/repository/google/"


class MavenArtifact(object):
    """A maven artifact"""

    def __init__(self, group_id, artifact_id, version):
        self.group_id = group_id
        self.artifact_id = artifact_id
        self.version = version
        pass

    def __eq__(self, other):
        if not isinstance(other, MavenArtifact):
            return False
        return (self.group_id == other.group_id
                and self.artifact_id == other.artifact_id
                and self.version == other.version)

    def get_repository_directory(self):
        return "%s/%s/%s" % (self.group_id.replace(".", "/"),
                             self.artifact_id,
                             self.version)
        pass

    def get_artifact_name(self, ext, prefix=None, suffix=None):
        if prefix and not prefix.startswith("-"):
            prefix = "-" + prefix
        if suffix and not suffix.startswith("."):
            suffix = "." + suffix
        if prefix is None:
            prefix = ""
        if suffix is None:
            suffix = ""
        return "%s-%s%s%s%s" % (self.artifact_id, self.version, prefix, ext, suffix)

    def get_repository_path(self, ext, prefix=None, suffix=None):
        return "%s/%s" % (self.get_repository_directory(),
                          self.get_artifact_name(ext, prefix=prefix, suffix=suffix))

    @staticmethod
    def parse_maven_dep(artifact):
        m = re.match("(.*?):(.*?):(.*)", artifact)
        if m:
            return MavenArtifact(group_id=m.group(1),
                                 artifact_id=m.group(2),
                                 version=m.group(3))
        raise Exception("'%s' can't be parsed" % artifact)
        pass

    pass


def download_file(path, url):
    print("download_file: url=%s" % url)
    with urllib.request.urlopen(url) as response:
        with open(path, mode="wb") as dst_file:
            while True:
                data = response.read(10240)
                if not data:
                    break
                dst_file.write(data)
    pass


def download_artifact_item(maven_repo,
                           artifact: MavenArtifact,
                           base_dir,
                           *, prefix=None, suffix=None, ext=None):
    url = maven_repo + artifact.get_repository_path(prefix=prefix,
                                                    suffix=suffix,
                                                    ext=ext)
    dst_path = os.path.join(base_dir,
                            artifact.get_artifact_name(prefix=prefix,
                                                       suffix=suffix,
                                                       ext=ext))
    download_file(dst_path, url)
    pass


def download_maven_file(base_dir, maven_dep, type):
    artifact = MavenArtifact.parse_maven_dep(maven_dep)
    dst_dir = os.path.join(base_dir, artifact.group_id,
                           artifact.artifact_id,
                           artifact.version)
    os.makedirs(dst_dir, exist_ok=True)
    download_artifact_item(MAVEN_REPO, artifact, dst_dir, ext=".pom")
    download_artifact_item(MAVEN_REPO, artifact, dst_dir, ext=".pom.md5")
    if type == "aar":
        download_artifact_item(MAVEN_REPO, artifact, dst_dir, ext=".aar.md5")
        download_artifact_item(MAVEN_REPO, artifact, dst_dir, ext=".aar")
    elif type == "jar":
        download_artifact_item(MAVEN_REPO, artifact, dst_dir, ext=".jar.md5")
        download_artifact_item(MAVEN_REPO, artifact, dst_dir, ext=".jar")
        download_artifact_item(MAVEN_REPO, artifact, dst_dir, ext="-sources.jar")
        download_artifact_item(MAVEN_REPO, artifact, dst_dir, ext="-sources.jar.md5")
    pass


def create_parser():
    parser = argparse.ArgumentParser(prog="download_maven.py")
    parser.add_argument("--base-dir", required=True,
                        help="The destination directory.")
    parser.add_argument("maven_deps", nargs="+")
    return parser


def main():
    parser = create_parser()
    args = parser.parse_args()

    dep_pattern = re.compile("(.*?)@(.*)")
    for dep_item in args.maven_deps:
        m = dep_pattern.match(dep_item)
        if m is None:
            parser.error("'{}' is not maven dep.".format(dep_item))
        download_maven_file(args.base_dir, m.group(1), m.group(2))
        pass
    pass


if __name__ == '__main__':
    main()
    pass
