# -*- coding: utf-8 -*-

import argparse
import sys

from util import build_utils


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="zipzip.py")
    parser.add_argument("--depfile")
    parser.add_argument("--inputs")
    parser.add_argument("--output")
    parser.add_argument("--base-dir")
    return parser


def main(argv):
    parser = create_parser()
    args = parser.parse_args(argv)

    inputs = build_utils.parse_gyp_list(args.inputs)
    output = args.output
    build_utils.remove_subtree(args.base_dir)
    build_utils.make_directory(args.base_dir)
    for path in inputs:
        build_utils.extract_all(path, base_dir=args.base_dir)

    zip_files = build_utils.find_in_directory(args.base_dir, "*")
    build_utils.do_zip(zip_files, output, args.base_dir)

    if args.depfile:
        build_utils.write_dep_file(args.depfile,
                                   build_utils.get_python_dependencies())
    pass


if __name__ == "__main__":
    main(sys.argv[1:])
    pass