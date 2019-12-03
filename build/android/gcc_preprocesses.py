# -*- coding: utf-8 -*-

import argparse
import sys
import subprocess

from android import build_utils


def create_parser():
    parser = argparse.ArgumentParser(prog="gcc_preprocesses.py")
    parser.add_argument("--depfile")
    parser.add_argument("--include-path")
    parser.add_argument("--template")
    parser.add_argument("--output", help="Path to to touch on success")
    parser.add_argument("--defines", default=[], action="append")
    parser.add_argument("--stamp")
    return parser


def do_gcc(args):
    gcc_cmd = ["gcc"]
    for item in args.defines:
        gcc_cmd.append("-D" + item)
    gcc_cmd += [
        "-E",
        "-D", "ANDROID",
        "-x", "c-header",  # treat sources as C header file
        "-P",  # disable line markers, i.e. '#line 309'
        "-I", args.include_path,
        "-o", args.output,
        args.template
    ]
    subprocess.check_call(gcc_cmd)
    pass


def main(argv):
    argv = build_utils.expand_file_args(argv)
    parser = create_parser()
    args = parser.parse_args(argv)

    defines = []
    for arg in args.defines:
        defines.extend(build_utils.parse_gyp_list(arg))
    args.defines = defines

    do_gcc(args)

    if args.depfile:
        build_utils.write_dep_file(args.depfile,
                                   build_utils.get_python_dependencies())
    if args.stamp:
        build_utils.touch(args.stamp)
    pass


if __name__ == "__main__":
    main(sys.argv[1:])
    pass
