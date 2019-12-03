# -*- coding: utf-8 -*-

import argparse
import os
import sys
import json
import subprocess
import zipfile

from android import build_utils


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dex.py")
    build_utils.add_depfile_option(parser)
    parser.add_argument("--android-sdk-tools",
                        help="Android build tools directory.")
    parser.add_argument("--output-directory",
                        default=os.getcwd(),
                        help="Path to the output build directory.")
    parser.add_argument("--dex-path",
                        help="dex output path")
    parser.add_argument("--configuration-name",
                        help="The build CONFIGURATION_NAME.")
    parser.add_argument("--proguard-enabled",
                        help="\"true\" if proguard is enabled.")
    parser.add_argument("--debug-build-proguard-enabled",
                        help="true if proguard is enabled for debug build.")
    parser.add_argument("--proguard-enabled-input-path",
                        help="Path to dex in Release mode when proguard "
                        "is enabled.")
    parser.add_argument("--no-locals", default="0",
                        help="Exclude locales from the dex list.")
    parser.add_argument("--incremental",
                        action="store_true",
                        help="Enable incremental builds when possible.")
    parser.add_argument("--inputs", help="A list of additional input paths.")
    parser.add_argument("--excluded-paths",
                        help="A list of paths to exclude from the dex file.")
    parser.add_argument("--main-dex-list-path",
                        help="A file containing a list of the classes to "
                        "include in the main dex.")
    parser.add_argument("--multidex-configuration-path",
                        help="A json file containing multidex build configuration.")
    parser.add_argument("--multi-dex", action="store_true", default=False)
    parser.add_argument("--base-dir")
    parser.add_argument("paths", nargs="*", default=[])

    return parser


def parse_options(parser, argv):
    argv = build_utils.expand_file_args(argv)
    args = parser.parse_args(argv)

    required_options = ("android_sdk_tools",)
    build_utils.check_options(args, parser,  required=required_options)

    if args.multidex_configuration_path:
        with open(args.multidex_configuration_path) as multidex_config_file:
            multidex_config = json.load(multidex_config_file)
            args.multi_dex = multidex_config.get("enabled", False)
            pass

    if args.multi_dex and not args.main_dex_list_path:
        print("multidex cannot be enabled without --main-dex-list-path")
        args.multi_dex = False
    elif args.main_dex_list_path and not args.multi_dex:
        print("--main-dex-list-path is unused if --multi-dex is not enabled")

    if args.inputs:
        args.inputs = build_utils.parse_gyp_list(args.inputs)
    if args.excluded_paths:
        args.excluded_paths = build_utils.parse_gyp_list(args.excluded_paths)
    return args


def remove_unwanted_files_from_zip(dex_path):
    """删除.dex.zip中非dex的文件
    """
    tmp_dex_path = "%s.dex.zip" % dex_path
    with zipfile.ZipFile(dex_path, "r") as iz, \
            zipfile.ZipFile(tmp_dex_path, "w", zipfile.ZIP_DEFLATED) as oz:
        for i in iz.namelist():
            if i.endswith(".dex"):
                oz.writestr(i, iz.read(i))
        pass

    os.remove(dex_path)
    os.rename(tmp_dex_path, dex_path)
    pass


def _run_dx(args, dex_cmd, paths):
    base_dir = args.base_dir
    build_utils.make_directory(base_dir)
    build_utils.remove_subtree(base_dir)

    if args.multi_dex:
        dex_cmd += ["--main-dex-list=%s" % args.main_dex_list_path]

    dex_cmd += paths
    build_utils.check_output(dex_cmd, print_stderr=False)

    if args.dex_path.endswith(".zip"):
        remove_unwanted_files_from_zip(args.dex_path)
    pass


def _on_stale_md5(args, dex_cmd, paths):
    _run_dx(args, dex_cmd, paths)
    build_utils.write_json([os.path.relpath(p, args.output_directory) for p in paths],
                           args.dex_path + ".inputs")
    pass


def main(argv):
    parser = create_parser()
    args = parse_options(parser, argv)

    paths = args.paths
    if ((args.proguard_enabled == 'true' and args.configuration_name == "Release")
            or (args.debug_build_proguard_enabled == 'true' and args.configuration_name == "Debug")):
        paths = [args.proguard_enabled_input_path]
        pass

    paths = list(paths)
    if args.inputs:
        paths += args.inputs

    if args.excluded_paths:
        excluded_paths = args.excluded_paths
        paths = [p for p in paths
                 if os.path.relpath(p, args.output_directory) not in excluded_paths]

    input_paths = list(paths)
    dx_name = "dx"
    if build_utils.is_windows():
        dx_name = "dx.bat"
    dx_binary = os.path.join(args.android_sdk_tools, dx_name)
    dex_cmd = [dx_binary,
               "--dex",
               "--num-threads=8",
               "--force-jumbo",
               "--output", args.dex_path]

    if args.no_locals != "0":
        dex_cmd .append("--no-locals")

    if args.multi_dex:
        input_paths.append(args.main_dex_list_path)
        dex_cmd += [
            "--multi-dex",
            "--minimal-main-dex"
        ]

    output_paths = [
        args.dex_path,
        args.dex_path + ".inputs"
    ]

    _on_stale_md5(args, dex_cmd, paths)
    if args.depfile:
        all_dep_paths = list(input_paths)
        all_dep_paths.extend(build_utils.get_python_dependencies())
        build_utils.write_dep_file(args.depfile, all_dep_paths)
    pass


if __name__ == "__main__":
    main(sys.argv[1:])
    pass
