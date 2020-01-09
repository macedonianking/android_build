# -*- encoding: utf-8 -*-

import argparse
import sys
import os
import fnmatch

import unzip_aar

from util import build_utils

from util.maven import MavenArtifact
from util.maven import MavenM2


def create_parser():
    parser = argparse.ArgumentParser(prog="generate_aar_targets.py")
    parser.add_argument("--name", help="The root target name")
    parser.add_argument("--maven-depname", help="The maven depname for the aar file.")
    parser.add_argument("--root-dir", help="The project root directory")
    parser.add_argument("--m2-home", help="The build target directory.")
    parser.add_argument("--aar-path", help="The path to the aar archive directory.")
    parser.add_argument("--json-path", help="The output build config path.")
    return parser


def parse_args(args):
    parser = create_parser()
    args = parser.parse_args(args)

    required_options = [
        "name",
        "maven_depname",
        "root_dir",
        "m2_home",
        "aar_path",
        "json_path",
    ]
    build_utils.check_options(args, parser, required=required_options)
    return args


def _find_directory(directory, filename_filter):
    ret = []
    for name in os.listdir(directory):
        if fnmatch.fnmatch(name, filename_filter):
            ret.append(os.path.join(directory, name))
    return ret


def generate_targets_from_aar_directory(name, aar_output_dir, root_dir):
    build_config = {"name": name,
                    "target_list": [
                    ]}
    target_list = build_config["target_list"]

    android_manifest_path = os.path.join(aar_output_dir, "AndroidManifest.xml")
    resources_dir = os.path.join(aar_output_dir, "res")
    if os.path.exists(resources_dir):
        android_resources_target = {
            "name": name + "__android_resources",
            "type": "android_resources",
            "android_manifest": build_utils.to_gn_absolute_path(root_dir, android_manifest_path),
            "resource_dirs": [
                build_utils.to_gn_absolute_path(root_dir, resources_dir),
            ]
        }
        target_list.append(android_resources_target)

    jar_target_name_prefix = "%s__classes_jar" % name
    for index, jar_file in enumerate(_find_directory(aar_output_dir, "classes*.jar")):
        jar_target_name = jar_target_name_prefix + str(index)
        target_config = {
            "type": "java_prebuilt",
            "name": jar_target_name,
            "jar_path": build_utils.to_gn_absolute_path(root_dir, jar_file),
            "supports_android": True,
        }
        target_list.append(target_config)
        pass

    return build_config


def main(argv):
    args = parse_args(argv)

    artifact = MavenArtifact.parse_maven_dep(args.maven_depname)
    maven_m2 = MavenM2(args.m2_home)

    base_dir = os.path.join(maven_m2.m2_build(), artifact.repository_dir_path())
    build_utils.make_directory_for_file(base_dir)

    unzip_record_path = args.json_path + ".unzip_aar.md5"

    unzip_aar.unzip_aar(args.aar_path, base_dir, unzip_record_path)
    build_config = generate_targets_from_aar_directory(args.name,
                                                       base_dir,
                                                       args.root_dir)

    build_utils.make_directory_for_file(args.json_path)
    build_utils.write_json(build_config, args.json_path)
    pass


if __name__ == '__main__':
    main(sys.argv[1:])
    pass
