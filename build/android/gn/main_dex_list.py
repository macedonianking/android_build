# -*- coding: utf-8 -*-

import sys
import argparse
import os
import tempfile
import shutil

from android import build_utils
from android.pylib import constants


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="main_dex_list.py")
    build_utils.add_depfile_option(parser)
    parser.add_argument("--proguard-jar-path",
                        required=True,
                        help="Specifies the proguard executable jar path.")
    parser.add_argument("--android-sdk-tools",
                        required=True,
                        help="Android sdk build tools directory.")
    parser.add_argument("--main-dex-rules-path", action="append", default=[],
                        dest="main_dex_rules_paths",
                        help="A file containing a list of proguard rules to use "
                        "in determining the class to include in the main dex.")
    parser.add_argument("--main-dex-list-path", required=True,
                        help="The main dex list file to generate.")
    parser.add_argument("--enabled-configurations",
                        help="The build configurations for which a main dex list "
                        "should be generated.")
    parser.add_argument("--configuration-name",
                        help="The current build configuration.")
    parser.add_argument("--multidex-configuration-path",
                        help="A JSON file containing multidex buld configuration.")
    parser.add_argument("--inputs",
                        help="JARs for which a main dex list should be generated.")
    parser.add_argument("--base-dir",
                        required=True,
                        help="The base working  directory.")
    parser.add_argument("paths", nargs="*", default=[],
                        help="JARs for which a main dex list should be generated.")
    return parser


def main(argv):
    argv = build_utils.expand_file_args(argv)
    parser = create_parser()
    args = parser.parse_args(argv)
    # print(args)

    if args.multidex_configuration_path:
        multidex_config = build_utils.read_json(
            args.multidex_configuration_path)
        if not multidex_config.get("enabled", False):
            return 0

    if args.inputs:
        args.paths.extend(build_utils.parse_gyp_list(args.inputs))

    shrinked_android_jar = os.path.abspath(
        os.path.join(args.android_sdk_tools, 'lib', 'shrinkedAndroid.jar'))
    dx_jar = os.path.abspath(
        os.path.join(args.android_sdk_tools, 'lib', 'dx.jar'))
    rules_file = os.path.abspath(
        os.path.join(args.android_sdk_tools, 'mainDexClasses.rules'))

    proguard_cmd = [
        "java", "-jar", args.proguard_jar_path,
        '-forceprocessing',
        '-dontwarn', '-dontoptimize', '-dontobfuscate', '-dontpreverify',
        '-libraryjars', shrinked_android_jar,
        '-include', rules_file,
    ]
    for m in args.main_dex_rules_paths:
        proguard_cmd.extend(["-include", m])
        pass

    main_dex_list_cmd = [
        "java", "-cp", dx_jar,
        "com.android.multidex.MainDexListBuilder",
    ]

    input_paths = list(args.paths)
    input_paths += [
        shrinked_android_jar,
        dx_jar,
        rules_file,
    ]
    input_paths += args.main_dex_rules_paths

    input_strings = [
        proguard_cmd,
        main_dex_list_cmd,
    ]

    output_paths = [
        args.main_dex_list_path,
    ]

    _on_stale_md5(args, proguard_cmd, main_dex_list_cmd, args.paths,
                  args.main_dex_list_path)
    if args.depfile:
        all_dep_paths = list(input_paths)
        all_dep_paths.extend(build_utils.get_python_dependencies())
        build_utils.write_dep_file(args.depfile, all_dep_paths)
    pass


def _on_stale_md5(args, proguard_cmd, main_dex_list_cmd,  paths, main_dex_list_path):
    base_dir = args.base_dir
    if os.path.exists(base_dir):
        shutil.rmtree(base_dir)
        pass

    build_utils.make_directory(base_dir)
    paths_arg = build_utils.CLASSPATH_SEP.join(paths)
    main_dex_list = ''
    try:
        temp_jar_path = os.path.join(base_dir, "proguard.jar")
        proguard_cmd += [
            '-injars', paths_arg,
            '-outjars', temp_jar_path
        ]
        build_utils.check_output(proguard_cmd, print_stderr=False)

        main_dex_list_cmd += [
            temp_jar_path, paths_arg
        ]
        main_dex_list = build_utils.check_output(main_dex_list_cmd)
    except build_utils.CalledProcessError as e:
        if 'output jar is empty' in e.output:
            pass
        elif "input doesn't contain any classes" in e.output:
            pass
        else:
            raise

    with open(main_dex_list_path, 'w') as main_dex_list_file:
        main_dex_list_file.write(main_dex_list)
    pass


if __name__ == "__main__":
    main(sys.argv[1:])
    pass
