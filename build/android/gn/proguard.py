# -*- coding: utf-8 -*-

import argparse
import sys

import proguard_util
from util import build_utils


def create_parser():
    parser = argparse.ArgumentParser(prog="proguard.py")
    build_utils.add_depfile_option(parser)
    parser.add_argument("--proguard-path",
                        help="Path to the proguard executable.")
    parser.add_argument("--input-paths",
                        help="Paths to the .jar files proguard should run on.")
    parser.add_argument("--output-path",
                        help="Path to the generated .jar file.")
    parser.add_argument("--proguard-configs",
                        help="Paths to proguard configuration files.")
    parser.add_argument("--mapping",
                        help="Path to proguard mapping to apply.")
    parser.add_argument("--is-test",
                        action="store_true",
                        help="If true, extra progurad options for instrumentation tests will be "
                        "added.")
    parser.add_argument("--tested-apk-info",
                        help="Path to the proguard .info file for the tested apk.")
    parser.add_argument("--classpath", action="append",
                        help="Classpath for proguard.")
    parser.add_argument("--stamp",
                        help="Path to touch on success.")
    parser.add_argument("-v", "--verbose",
                        action="store_true",
                        help="Print all proguard output.")
    return parser


def parse_args(argv):
    parser = create_parser()
    args = parser.parse_args(argv)

    classpath = []
    for arg in args.classpath:
        classpath.extend(build_utils.parse_gyp_list(arg))
    args.classpath = classpath

    return args


def main(argv):
    argv = build_utils.expand_file_args(argv)
    args = parse_args(argv)
    # print(args)

    proguard = proguard_util.ProguardCmdBuilder(args.proguard_path)
    proguard.injars(build_utils.parse_gyp_list(args.input_paths))
    proguard.configs(build_utils.parse_gyp_list(args.proguard_configs))
    proguard.outjar(args.output_path)

    if args.mapping:
        proguard.mapping(args.mapping)

    if args.tested_apk_info:
        proguard.tested_apk_info(args.tested_apk_info)

    classpath = list(set(args.classpath))
    proguard.libraryjars(classpath)
    proguard.verbose(args.verbose)

    input_paths = proguard.get_inputs()

    proguard.check_output()
    if args.depfile:
        all_dep_paths = list(input_paths)
        all_dep_paths.extend(build_utils.get_python_dependencies())
        build_utils.write_dep_file(args.depfile, all_dep_paths)
        pass
    pass


if __name__ == "__main__":
    main(sys.argv[1:])
    pass
