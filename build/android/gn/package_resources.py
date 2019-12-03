# -*- coding: utf-8 -*-

"""Package resources into an apk.

See https://android.googlesource.com/platform/tools/base/+/master/legacy/ant-tasks/src/main/java/com/android/ant/AaptExecTask.java
and
https://android.googlesource.com/platform/sdk/+/master/files/ant/build.xml
"""

import argparse
import os
import shutil
import re
import zipfile

from android import build_utils

DENSITY_SPLITS = {
    'hdpi': (
        'hdpi-v4',  # Order matters for output file names.
        'ldrtl-hdpi-v4',
        'sw600dp-hdpi-v13',
        'ldrtl-hdpi-v17',
        'ldrtl-sw600dp-hdpi-v17',
        'hdpi-v21',
    ),
    'xhdpi': (
        'xhdpi-v4',
        'ldrtl-xhdpi-v4',
        'sw600dp-xhdpi-v13',
        'ldrtl-xhdpi-v17',
        'ldrtl-sw600dp-xhdpi-v17',
        'xhdpi-v21',
    ),
    'xxhdpi': (
        'xxhdpi-v4',
        'ldrtl-xxhdpi-v4',
        'sw600dp-xxhdpi-v13',
        'ldrtl-xxhdpi-v17',
        'ldrtl-sw600dp-xxhdpi-v17',
        'xxhdpi-v21',
    ),
    'xxxhdpi': (
        'xxxhdpi-v4',
        'ldrtl-xxxhdpi-v4',
        'sw600dp-xxxhdpi-v13',
        'ldrtl-xxxhdpi-v17',
        'ldrtl-sw600dp-xxxhdpi-v17',
        'xxxhdpi-v21',
    ),
    'tvdpi': (
        'tvdpi-v4',
        'sw600dp-tvdpi-v13',
        'ldrtl-sw600dp-tvdpi-v17',
    ),
}


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="package_resource.py")
    parser.add_argument("--depfile")
    parser.add_argument("--base-dir", required=True)
    parser.add_argument("--android-sdk-jar",
                        help="Path to the Android SDK jar.")
    parser.add_argument("--aapt-path",
                        help="Path to the Android aapt tool.")
    parser.add_argument("--configuration-name")
    parser.add_argument("--android-manifest")
    parser.add_argument("--version-name", help="Version name for apk.")
    parser.add_argument("--version-code", help="Version code for apk.")
    parser.add_argument("--shared-resources",
                        action="store_true",
                        help="Make a resource package that can be loaded by a different "
                        "application at runtime to access the packge's resources")
    parser.add_argument("--app-as-shared-lib",
                        action="store_true",
                        help="Make a resource package that can be loaded as shared library.")
    parser.add_argument("--resource-zips",
                        default=[],
                        help="zip files containing resources to be packaged.")
    parser.add_argument("--no-compress",
                        help="disables compression for the given comma separated list of extensions")
    parser.add_argument("--asset-dir",
                        help="directories containing assets to be packaged.")
    parser.add_argument("--create-density-splits",
                        action="store_true",
                        help="Enables density splits")
    parser.add_argument("--language-splits", default='[]',
                        help="GYP list of languages to create splits for.")
    parser.add_argument("--apk-path",
                        help="Path to output (partial) apk.")
    return parser


def parse_args():
    parser = create_parser()
    args = parser.parse_args()
    required_options = ("android_sdk_jar",
                        "aapt_path",
                        "configuration_name",
                        "android_manifest",
                        "version_code",
                        "version_name",
                        "apk_path")
    build_utils.check_options(args, parser, required=required_options)

    args.resource_zips = build_utils.parse_gyp_list(args.resource_zips)
    args.language_splits = build_utils.parse_gyp_list(args.language_splits)
    return args


def _construct_most_aapt_args(args):
    """创建aapt处理参数
    """
    package_command = [
        args.aapt_path,
        "package",
        "--version-code", args.version_code,
        "--version-name", args.version_name,
        "-M", args.android_manifest,
        "--no-crunch",
        "-f",
        "--auto-add-overlay",
        "-I", args.android_sdk_jar,
        "-F", args.apk_path,
        "--ignore-assets", build_utils.AAPT_IGNORE_PATTERN,
    ]

    if args.no_compress:
        for ext in args.no_compress.split(","):
            package_command += ["-0", ext]

    if args.shared_resources:
        package_command.append("--shared-lib")

    if args.app_as_shared_lib:
        package_command.append("--app-as-shared-lib")

    if args.asset_dir and os.path.exists(args.asset_dir):
        package_command += ["-A", args.asset_dir]

    if args.create_density_splits:
        for config in DENSITY_SPLITS.items():
            package_command.extend(("--split", ",".join(config)))

    if args.language_splits:
        for lang in args.language_splits:
            package_command.extend(("--split", lang))

    if 'Debug' in args.configuration_name:
        package_command += ["--debug-mode"]

    return package_command


def _generate_density_split_paths(apk_path):
    for density, config in DENSITY_SPLITS.items():
        src_path = "%s_%s" % (apk_path, "_".join(config))
        dst_path = "%s_%s" % (apk_path, density)
        yield src_path, dst_path


def _generate_language_split_output_paths(apk_path, languages):
    for lang in languages:
        yield "%s_%s" % (apk_path, lang)


def move_images_to_non_mdpi_folders(res_root):
    """move images from drawable-*-mdpi-* folders to drawable-* folders.
    """
    for src_dir_name in os.listdir(res_root):
        src_components = src_dir_name.split("-")
        if src_components[0] != "drawable" or "mdpi" not in src_components:
            continue
        src_dir = os.path.join(res_root, src_dir_name)
        if not os.path.isdir(src_dir):
            continue
        dst_components = [c for c in src_components if c != "mdpi"]
        assert(src_components != dst_components)
        dst_dir_name = "-".join(dst_components)
        dst_dir = os.path.join(res_root, dst_dir_name)
        build_utils.make_directory(dst_dir)
        for src_file_name in os.listdir(src_dir):
            if not src_file_name.endswith(".png"):
                continue
            src_file = os.path.join(src_dir, src_file_name)
            dst_file = os.path.join(dst_dir, src_file_name)
            assert(not os.path.lexists(dst_file))
            shutil.move(src_file, dst_file)
        pass
    pass


def package_args_for_extracted_zips(d):
    """资源文件夹生成编译命令
    """
    subdirs = [os.path.join(d, s) for s in os.listdir(d)]
    subdirs = [s for s in subdirs if os.path.isdir(s)]
    is_multi = '0' in [os.path.basename(s) for s in subdirs]
    if is_multi:  # 存在多个资源文件夹
        res_dirs = sorted(subdirs, key=lambda p: int(os.path.basename(p)))
    else:
        res_dirs = [d]
    package_command = []
    for d in res_dirs:
        move_images_to_non_mdpi_folders(d)
        package_command += ["-S", d]
    return package_command


def check_for_missed_configs(apk_path, check_density, languages):
    """查找那些没有单独打包的资源配置
    """
    triggers = []
    if check_density:
        triggers.extend(re.compile("-%s" % x) for x in DENSITY_SPLITS)
    if languages:
        triggers.extend(re.compile(r"-%s\b" % x) for x in languages)
    with zipfile.ZipFile(apk_path, mode="r") as zip_file:
        for name in zip_file.namelist():
            for trigger in triggers:
                if trigger.search(name) and "mipmap-" not in name:
                    raise Exception("Found config in main apk that should have been "
                                    "put in a split: %s\nYou need to update "
                                    "package_resources.py to include this new config(trigger=%s)"
                                    % (apk_path, name))
    pass


def rename_density_splits(apk_path):
    for src_name, dst_name in _generate_density_split_paths(apk_path):
        shutil.move(src_name, dst_name)
    pass


def _on_stale_md5(package_command, args):
    base_dir = args.base_dir
    build_utils.make_directory(base_dir)
    build_utils.remove_subtree(base_dir)

    if args.resource_zips:
        for z in args.resource_zips:
            subdir = os.path.join(base_dir, os.path.basename(z))
            if os.path.exists(subdir):
                raise Exception(
                    "Resource zip name conflict: " + os.path.basename(z))
            build_utils.extract_all(z, base_dir=subdir)
            package_command += package_args_for_extracted_zips(subdir)
            pass

    build_utils.check_output(args=package_command)

    if args.create_density_splits or args.language_splits:
        check_for_missed_configs(args.apk_path,
                                 args.create_density_splits,
                                 args.language_splits)

    if args.create_density_splits:
        rename_density_splits(args.apk_path)
    pass


def main():
    args = parse_args()
    # print(args)

    package_command = _construct_most_aapt_args(args)

    output_paths = [args.aapt_path]

    if args.create_density_splits:
        for _, dst_path in _generate_density_split_paths(args.apk_path):
            output_paths.append(dst_path)
    output_paths.extend(_generate_language_split_output_paths(args.apk_path,
                                                              args.language_splits))

    input_paths = [args.android_manifest] + args.resource_zips

    input_strings = []
    input_strings.extend(package_command)

    if args.asset_dir and os.path.exists(args.asset_dir):
        asset_paths = []
        for root, _, filenames in os.walk(args.asset_dir):
            asset_paths.extend(os.path.join(root, name) for name in filenames)
        input_paths.extend(asset_paths)
        input_strings.extend(sorted(asset_paths))
        pass

    _on_stale_md5(package_command, args)
    if args.depfile:
        build_utils.write_dep_file(args.depfile,
                                   build_utils.get_python_dependencies())
    pass


if __name__ == "__main__":
    main()
    pass
