# -*- coding: utf-8 -*-

import argparse
import os
import subprocess
import sys

import jar
from util import build_utils


def normalize_paths(paths):
    return [os.path.normpath(x) for x in paths]


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="javac.py")
    parser.add_argument("--depfile")
    parser.add_argument("--src-gendirs")
    parser.add_argument("--java-srcjars", action="append", default=[])
    parser.add_argument("--bootclasspath", action="append", default=[])
    parser.add_argument("--classpath", action="append", default=[])
    parser.add_argument("--javac-includes", default="")
    parser.add_argument("--jar-excluded-classes", default="")
    parser.add_argument("--jar-path")
    parser.add_argument("--stamp")
    parser.add_argument("--manifest-entry", nargs="*")
    parser.add_argument("--base-dir", required=True)
    parser.add_argument("--java-dirs")
    parser.add_argument("java_files", nargs="*")
    return parser


def parse_options(argv):
    parser = create_parser()
    args = parser.parse_args(argv)
    build_utils.check_options(args, parser, required=("jar_path", "base_dir"))

    bootclasspath = []
    for arg in args.bootclasspath:
        bootclasspath += build_utils.parse_gyp_list(arg)
    args.bootclasspath = bootclasspath

    classpath = []
    for arg in args.classpath:
        classpath += build_utils.parse_gyp_list(arg)
    args.classpath = classpath

    java_srcjars = []
    for arg in args.java_srcjars:
        java_srcjars += build_utils.parse_gyp_list(arg)
    args.java_srcjars = java_srcjars

    if args.src_gendirs:
        args.src_gendirs = build_utils.parse_gyp_list(args.src_gendirs)

    args.javac_includes = build_utils.parse_gyp_list(args.javac_includes)
    args.jar_excluded_classes = build_utils.parse_gyp_list(
        args.jar_excluded_classes)
    return args


def _filter_java_files(paths, filters):
    return [p for p in paths if not filters or build_utils.matches_glob(p, filters)]


def _on_stale_md5(args, javac_cmd, java_files):
    base_dir = args.base_dir
    build_utils.make_directory(base_dir)
    build_utils.remove_subtree(base_dir)

    excluded_jar_path = args.jar_path.replace(".jar", ".excluded.jar")
    java_sources_file = os.path.join(base_dir, "sources.txt")

    classes_dir = os.path.join(base_dir, "classes")
    os.makedirs(classes_dir)

    if args.java_srcjars:
        java_dir = os.path.join(base_dir, "java")
        os.makedirs(java_dir)
        for srcjar in args.java_srcjars:
            build_utils.extract_all(srcjar,
                                    base_dir=java_dir,
                                    pattern="*.java")
        jar_srcs = build_utils.find_in_directory(java_dir, "*.java")
        jar_srcs = _filter_java_files(jar_srcs, args.javac_includes)
        java_files.extend(jar_srcs)
        pass

    if java_files:
        build_utils.write_sources_file(java_sources_file, [os.path.normpath(x)
                                                           for x in java_files])
        cmd = javac_cmd + ["-d", classes_dir, "@" + java_sources_file]

        subprocess.check_call(cmd)
        pass

    glob = args.jar_excluded_classes

    def includes_jar_predicate(x):
        return not build_utils.matches_glob(x, glob)

    def excludes_jar_predicate(x):
        return build_utils.matches_glob(x, glob)

    jar.jar_directory(classes_dir, args.jar_path,
                      predicate=includes_jar_predicate)
    jar.jar_directory(classes_dir, excluded_jar_path,
                      predicate=excludes_jar_predicate)
    pass


def main(argv):
    argv = build_utils.expand_file_args(argv)
    args = parse_options(argv)
    # print(args)

    java_files = list(args.java_files)
    if args.src_gendirs:
        java_files.extend(build_utils.find_in_directories(args.src_gendirs,
                                                          "*.java"))

    java_files = _filter_java_files(java_files, args.javac_includes)

    javac_cmd = ["javac"]
    javac_cmd.extend([
        "-g",
        "-encoding", "utf-8",
        "-classpath", build_utils.CLASSPATH_SEP.join(args.classpath),
        "-sourcepath", "",
        "-source", "1.8",
        "-target", "1.8",
    ])

    if args.bootclasspath:
        javac_cmd.extend([
            "-bootclasspath",
            build_utils.CLASSPATH_SEP.join(args.bootclasspath)
        ])

    _on_stale_md5(args, javac_cmd, java_files)
    all_inputs = build_utils.get_python_dependencies()
    build_utils.write_dep_file(args.depfile, all_inputs)
    pass


if __name__ == "__main__":
    main(sys.argv[1:])
    pass
