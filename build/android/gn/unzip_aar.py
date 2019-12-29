# -*- encoding: utf-8 -*-

import argparse
import zipfile
import os
import sys

from util import build_utils
from util import md5_metadata

AAR_EXTRACT_GLOB = ("res/*",
                    "*.jar",
                    "assets/*",
                    "AndroidManifest.xml",
                    "annotations.zip",
                    "proguard.txt",
                    "public.txt",
                    "R.txt")


def create_parser():
    parser = argparse.ArgumentParser(prog="unzip_aar.py")
    parser.add_argument("--depfile")
    parser.add_argument("--output-path")
    parser.add_argument("--aar-path", help="The input aar file path.")
    parser.add_argument("--output-dir", help="The output directory.")
    return parser


def parse_args(argv):
    parser = create_parser()
    args = parser.parse_args(argv)
    return args


def create_extract_list(old_metadata, new_metadata, src_map):
    ret_map = dict(src_map)
    if not old_metadata:
        return ret_map
    if old_metadata.inputs_md5() != new_metadata.inputs_md5():
        return ret_map

    for zip_name, out_path in src_map.items():
        if not os.path.exists(out_path):
            continue
        out_stat_obj = os.stat(out_path)
        if (out_stat_obj.st_mtime_ns, out_stat_obj.st_size) != old_metadata.output_tag(out_path):
            continue
        del ret_map[zip_name]
    return ret_map


def on_stale_md5(aar_path, output_dir, zip_map):
    if len(zip_map) <= 0:
        return

    with zipfile.ZipFile(aar_path, mode="r") as zip_obj:
        for name, path in zip_map.items():
            zip_obj.extract(name, path=output_dir)
    pass


def unzip_aar(aar_path, output_dir, output_path):
    build_utils.make_directory(output_dir)

    aar_map = {}
    with zipfile.ZipFile(aar_path, mode="r") as in_zip:
        for name in in_zip.namelist():
            if name.endswith("/"):
                continue
            if build_utils.matches_glob(name, AAR_EXTRACT_GLOB):
                aar_map[name] = os.path.normpath(os.path.join(output_dir, name))

    output_file_set = set(aar_map.values())
    for path in (os.path.normpath(x) for x in build_utils.find_in_directory(output_dir, "*")):
        if path not in output_file_set:
            os.remove(path)

    old_metadata = None
    if os.path.isfile(output_path):
        try:
            with open(output_path) as file_obj:
                old_metadata = md5_metadata.Metadata.from_file(file_obj)
        except Exception:
            os.remove(output_path)

    new_metadata = md5_metadata.Metadata()
    new_metadata.add_input_file(aar_path)

    zip_map = create_extract_list(old_metadata, new_metadata, aar_map)
    on_stale_md5(aar_path, output_dir, zip_map)

    new_metadata.add_output_file_in_directory(output_dir, "*")
    build_utils.make_directory(os.path.dirname(output_path))
    with open(output_path, mode="w") as file_obj:
        new_metadata.to_file(file_obj)
    pass


def main(argv):
    args = parse_args(argv)
    unzip_aar(args.aar_path, args.output_dir, args.output_path)
    pass


if __name__ == '__main__':
    main(sys.argv[1:])
    pass
