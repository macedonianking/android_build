# -*- coding: utf-8 -*-

import argparse
import sys
import os
import zipfile
import re

from android import build_utils


def create_parser():
    parser = argparse.ArgumentParser(prog="aidl.py")
    build_utils.add_depfile_option(parser)
    parser.add_argument("--aidl-path", help="Path to aidl binary.")
    parser.add_argument("--imports", help="Files to import.")
    parser.add_argument("--includes",
                        help="Directories to add as import search paths.")
    parser.add_argument("--srcjar", help="Path for srcjar output.")
    parser.add_argument("--base-dir", help="The base working directory.")
    parser.add_argument("paths", nargs="+", help="The paths to aidl files.")
    return parser


def parse_args(argv):
    parser = create_parser()
    args = parser.parse_args(argv)
    args.imports = build_utils.parse_gyp_list(args.imports)

    includes = []
    if args.includes:
        includes.extend(build_utils.parse_gyp_list(args.includes))
    args.includes = includes

    return args


def main(argv):
    args = parse_args(argv)

    base_dir = args.base_dir
    build_utils.delete_directory(base_dir)
    build_utils.make_directory(base_dir)

    for f in args.paths:
        classname = os.path.splitext(os.path.basename(f))[0]
        output = os.path.join(base_dir, classname + ".java")
        aidl_cmd = [args.aidl_path]
        for s in args.imports:
            aidl_cmd += ["-p", s]
        if args.includes:
            for s in args.includes:
                aidl_cmd += ["-I", s]
        aidl_cmd += [
            f,
            output
        ]
        build_utils.check_output(aidl_cmd)
        pass

    with zipfile.ZipFile(args.srcjar, "w") as srcjar:
        for f in build_utils.find_in_directory(base_dir, "*.java"):
            with open(f, "r") as fileobj:
                data = fileobj.read()
                pass

            pkg_name = re.compile(r"^\s*package\s+(.*?)\s*;",
                                  re.M).search(data).group(1)
            arcname = "%s/%s" % (pkg_name.replace(".", "/"),
                                 os.path.basename(f))
            srcjar.writestr(arcname, data)
        pass

    if args.depfile:
        all_dep_paths = build_utils.get_python_dependencies()
        build_utils.write_dep_file(args.depfile, all_dep_paths)
    pass


if __name__ == "__main__":
    main(sys.argv[1:])
    pass
