# -*- coding: utf-8 -*-

import os
import argparse
import sys
import shutil

from util import build_utils


def create_parser():
    parser = argparse.ArgumentParser(prog="protoc_java.py")
    build_utils.add_depfile_option(parser)
    parser.add_argument("--protoc",
                        help="Path to protoc binary.")
    parser.add_argument("--proto-path",
                        help="Path to proto directory.")
    parser.add_argument("--java-out-dir",
                        help="Path to output directory for java files.")
    parser.add_argument("--srcjar",
                        help="Path to output srcjar.")
    parser.add_argument("--base-dir",
                        help="The base working directory.")
    parser.add_argument("--stamp", help="File to touch on success.")
    parser.add_argument("paths", nargs="+",
                        help="The paths of .proto files.")
    return parser


def parse_args(argv):
    parser = create_parser()
    args = parser.parse_args(argv)
    build_utils.check_options(args, parser,
                              required=("protoc", "proto_path"))
    if not args.java_out_dir and not args.srcjar:
        raise Exception("One of --java-out-dir or --srcjar must be specified.")

    return args


def main(argv):
    args = parse_args(argv)

    base_dir = args.base_dir
    build_utils.delete_directory(base_dir)
    build_utils.make_directory(base_dir)

    # generator_args = [
    #     "optional_field_style=reftypes",
    #     "store_unknown_fields=true"
    # ]
    out_arg = "--java_out=" + base_dir
    cmds = [
        args.protoc,
        "--proto_path", args.proto_path,
        out_arg
    ] + args.paths
    build_utils.check_output(cmds)

    if args.java_out_dir:
        build_utils.delete_directory(args.java_out_dir)
        shutil.copytree(base_dir, args.java_out_dir)
    else:
        build_utils.zip_dir(args.srcjar, base_dir)

    if args.depfile:
        all_dep_paths = build_utils.get_python_dependencies()
        build_utils.write_dep_file(args.depfile, all_dep_paths)
    pass


if __name__ == "__main__":
    main(sys.argv[1:])
    pass
