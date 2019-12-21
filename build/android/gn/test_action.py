# -*- coding: utf-8 -*-

import argparse
from util import build_utils


def create_parser():
    parser = argparse.ArgumentParser(prog="test_action.py")
    build_utils.add_depfile_option(parser)
    parser.add_argument("--input", help="The path to the input file.")
    parser.add_argument("--output", help="The output file path.")
    parser.add_argument("options", nargs="*")
    return parser


def main():
    parser = create_parser()
    args = parser.parse_args()
    print(args.options)

    build_utils.touch(args.depfile)

    # if args.depfile:
    #     build_utils.write_dep_file(args.depfile,
    #                                build_utils.get_python_dependencies())
    pass


if __name__ == "__main__":
    main()
    pass
