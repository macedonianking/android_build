# -*- coding: utf-8 -*-

import argparse
import sys

from util import build_utils


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="zipzip.py")
    parser.add_argument("--depfile")
    parser.add_argument("--inputs", action="append", default=[])
    parser.add_argument("--output")
    parser.add_argument("--base-dir")
    return parser


def parse_args(argv):
    argv = build_utils.expand_file_args(argv)
    parser = create_parser()
    args = parser.parse_args(argv)

    input_list = []
    for item in args.inputs:
        input_list.extend(build_utils.parse_gyp_list(item))
    args.inputs = input_list

    return args


def main(argv):
    args = parse_args(argv)

    input_paths = []
    output_paths = []
    input_strings = []

    inputs = args.inputs
    input_paths.extend(inputs)
    output = args.output
    output_paths.append(output)

    input_strings.append(args.base_dir )

    def on_stale_md5():
        build_utils.remove_subtree(args.base_dir)
        build_utils.make_directory(args.base_dir)
        for path in inputs:
            build_utils.extract_all(path, base_dir=args.base_dir)

        zip_files = build_utils.find_in_directory(args.base_dir, "*")
        build_utils.do_zip(zip_files, output, args.base_dir)
        pass

    build_utils.call_and_write_dep_file_if_stale(on_stale_md5,
                                                 args,
                                                 input_strings=input_strings,
                                                 input_paths=input_paths,
                                                 output_paths=output_paths)
    pass


if __name__ == "__main__":
    main(sys.argv[1:])
    pass
