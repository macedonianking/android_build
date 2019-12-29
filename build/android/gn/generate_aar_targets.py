# -*- encoding: utf-8 -*-

import argparse
import sys
import os
import fnmatch

import unzip_aar

from util import build_utils


def create_parser():
    parser = argparse.ArgumentParser(prog="generate_aar_targets.py")
    parser.add_argument("--name", help="The root target name")
    parser.add_argument("--aar-path", help="The path to the aar archive directory.")
    parser.add_argument("--aar-output-dir", help="The output aar output directory.")
    parser.add_argument("--build-config", help="The output build config path.")
    parser.add_argument("--target-directory", help="The build target directory.")
    return parser


def parse_args(args):
    parser = create_parser()
    return parser.parse_args(args)


def _find_directory(directory, filename_filter):
    ret = []
    for name in os.listdir(directory):
        if fnmatch.fnmatch(name, filename_filter):
            ret.append(os.path.join(directory, name))
    return ret


def generate_targets_from_aar_directory(name, deps, aar_output_dir, target_directory):
    build_config = {"name": name,
                    "target_list": [
                    ]}
    target_list = build_config["target_list"]

    android_manifest_path = os.path.join(aar_output_dir, "AndroidManifest.xml")
    resources_dir = os.path.join(aar_output_dir, "res")
    android_resources_target = {
        "name": name + "__android_resources",
        "type": "android_resources",
        "android_manifest": os.path.relpath(android_manifest_path, target_directory),
        "resource_dirs": [
            os.path.relpath(resources_dir, target_directory),
        ]
    }
    if deps:
        android_resources_target["deps"] = deps
    target_list.append(android_resources_target)

    jar_target_name_prefix = "%s__classes_jar" % name
    index = 0
    for jar_file in _find_directory(aar_output_dir, "classes*.jar"):
        jar_target_name = jar_target_name_prefix + str(index)
        target_config = {
            "type": "java_prebuilt",
            "name": jar_target_name,
            "jar_path": os.path.relpath(jar_file, target_directory),
            "supports_android": True,
        }
        if deps:
            target_config["deps"] = deps
        target_list.append(target_config)
        pass

    return build_config


def main(argv):
    args = parse_args(argv)
    unzip_record_path = args.build_config + ".unzip_aar.md5"
    build_config_record_path = args.build_config + ".aar_targets.md5"

    unzip_aar.unzip_aar(args.aar_path, args.aar_output_dir, unzip_record_path)
    build_config = generate_targets_from_aar_directory(args.name, [], args.aar_output_dir, args.target_directory)

    build_utils.write_json(build_config, args.build_config)
    pass


if __name__ == '__main__':
    main(sys.argv[1:])
    pass
