# -*- coding: utf-8 -*-

import argparse
import itertools
import os
import shutil
import sys
import zipfile

from util import build_utils

# Taken from aapt's Package.cpp:
_NO_COMPRESS_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.gif', '.wav', '.mp2',
                           '.mp3', '.ogg', '.aac', '.mpg', '.mpeg', '.mid',
                           '.midi', '.smf', '.jet', '.rtttl', '.imy', '.xmf',
                           '.mp4', '.m4a', '.m4v', '.3gp', '.3gpp', '.3g2',
                           '.3gpp2', '.amr', '.awb', '.wma', '.wmv', '.webm')


def _split_asset_path(path):
    path_parts = path.split(":")
    src_path = path_parts[0]
    if len(path_parts) > 1:
        dest_path = path_parts[1]
    else:
        dest_path = os.path.basename(src_path)
    return src_path, dest_path


def _expand_paths(paths):
    """解决assets的路径问题
    """
    ret = []
    for path in paths:
        src_path, dest_path = _split_asset_path(path)
        if os.path.isdir(src_path):
            for f in build_utils.find_in_directory(src_path, "*"):
                ret.append((f, os.path.join(dest_path, f[len(src_path) + 1:])))
        else:
            ret.append((src_path, dest_path))
    ret.sort(key=lambda t: t[1])
    return ret


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="apkbuilder.py")
    parser.add_argument("--depfile")
    parser.add_argument("--assets", default='[]',
                        help='GYP-list of files to add as assets in the form '
                             '"srcPath:zipPath", where ":zipPath" is optional.')
    parser.add_argument("--write-asset-list",
                        action="store_true",
                        help="Whether to create an assets/assets_list file.")
    parser.add_argument("--uncompressed-assets",
                        help="same as --assets, expect disable compression.",
                        default='[]')
    parser.add_argument("--resource-apk",
                        help="An .ap_ file built using aapt.",
                        required=True)
    parser.add_argument("--output-apk", help="Path to the output file.",
                        required=True)
    parser.add_argument("--dex-file",
                        help="Path to the classes.dex to use.")
    parser.add_argument("--native-libs", action="append",
                        default=[],
                        help="GYP-list of native libraries to include. "
                             "Can be specified multiple times.")
    parser.add_argument("--secondary-native-libs",
                        action="append",
                        help="GYP-list of native libraries for secondary "
                             "android-abi. Can be specified multiple times.",
                        default=[])
    parser.add_argument("--android-abi",
                        help="Android architecture to use for native libraries.")
    parser.add_argument("--secondary-android-abi",
                        help="The secondary Android architecture to use for "
                             "secondary native libraries.")
    parser.add_argument("--native-lib-placeholders",
                        help="GYP-list of native library placeholders to add.",
                        default='[]')
    parser.add_argument("--emma-device-jar",
                        help="Path to emma_device.jar to include.")
    parser.add_argument("--srczip-path",
                        help="Path to srczip file to include.")
    parser.add_argument("--uncompress-shared-libraries",
                        action="store_true",
                        help="Uncompress shared libraries.")
    return parser


def parse_args(argv):
    argv = build_utils.expand_file_args(argv)
    parser = create_parser()
    args = parser.parse_args(argv)

    args.assets = build_utils.parse_gyp_list(args.assets)
    args.uncompressed_assets = build_utils.parse_gyp_list(
        args.uncompressed_assets)
    args.native_lib_placeholders = build_utils.parse_gyp_list(
        args.native_lib_placeholders)
    all_libs = []
    for item in args.native_libs:
        all_libs.extend(build_utils.parse_gyp_list(item))
    args.native_libs = all_libs

    secondary_libs = []
    for item in args.secondary_native_libs:
        secondary_libs.extend(build_utils.parse_gyp_list(item))
    args.secondary_native_libs = secondary_libs

    if not args.android_abi and (args.native_libs or args.native_lib_placeholders):
        raise Exception("Must specify --android-abi with --native-libs")
    if not args.secondary_android_abi and args.secondary_native_libs:
        raise Exception("Must specify --secondary-android-abi with"
                        " --secondary-native-libs")

    return args


def _create_assets_list(path_tuples):
    dests = sorted(t[1] for t in path_tuples)
    return "\n".join(dests) + "\n"


def _add_assets(apk, path_tuples, disable_compression=False):
    """添加assets文件到zip文件里面
    """
    for target_compress in (False, True):
        for src_path, dest_path in path_tuples:
            compress = not disable_compression and (
                    os.path.splitext(src_path[1]) not in _NO_COMPRESS_EXTENSIONS
            )
            if target_compress == compress:
                apk_path = "assets/" + dest_path
                try:
                    apk.getinfo(apk_path)
                    raise Exception("Multiple targets specified the asset path: %s"
                                    % apk_path)
                except KeyError:
                    build_utils.add_to_zip_hermetic(apk, apk_path, src_path=src_path,
                                                    compress=compress)

    pass


def _add_native_libraries(out_apk, native_libs, android_abi, uncompress):
    """添加native libraries to APK.
    """
    for path in native_libs:
        basename = os.path.basename(path)
        apk_path = "lib/%s/%s" % (android_abi, basename)

        compress = None
        if (uncompress and os.path.splitext(path)[1].endswith(".so")):
            compress = False

        build_utils.add_to_zip_hermetic(out_apk, apk_path,
                                        src_path=path,
                                        compress=compress)
    pass


def main(argv):
    args = parse_args(argv)
    # print(args)

    native_libs = sorted(args.native_libs)
    input_paths = [args.resource_apk, __file__] + native_libs

    secondary_native_libs = []
    if args.secondary_native_libs:
        secondary_native_libs = sorted(args.secondary_native_libs)
        input_paths += secondary_native_libs

    if args.dex_file:
        input_paths.append(args.dex_file)

    if args.emma_device_jar:
        input_paths.append(args.emma_device_jar)

    input_strings = [args.android_abi,
                     args.native_lib_placeholders,
                     args.uncompress_shared_libraries]

    if args.secondary_android_abi:
        input_strings.append(args.secondary_android_abi)

    _assets = _expand_paths(args.assets)
    _uncompressed_assets = _expand_paths(args.uncompressed_assets)

    for src_path, dest_path in itertools.chain(_assets, _uncompressed_assets):
        input_paths.append(src_path)
        input_strings.append(dest_path)
        pass

    def on_stale_md5(args):
        tmp_apk = args.output_apk + ".tmp"
        try:
            with zipfile.ZipFile(args.resource_apk) as resource_apk, \
                    zipfile.ZipFile(tmp_apk, "w", zipfile.ZIP_DEFLATED) as out_apk:
                def copy_resource(zipinfo):
                    compress = zipinfo.compress_type != zipfile.ZIP_STORED
                    build_utils.add_to_zip_hermetic(out_apk, zipinfo.filename,
                                                    data=resource_apk.read(
                                                        zipinfo.filename),
                                                    compress=compress)

                resource_infos = resource_apk.infolist()

                assert (resource_infos[0].filename == "AndroidManifest.xml")
                # 1.AndroidManifest.xml
                copy_resource(resource_infos[0])

                # 2.Assets
                if args.write_asset_list:
                    data = _create_assets_list(
                        itertools.chain(_assets, _uncompressed_assets))
                    build_utils.add_to_zip_hermetic(out_apk, "assets/assets_list",
                                                    data=data)
                _add_assets(out_apk, _assets, disable_compression=False)
                _add_assets(out_apk, _uncompressed_assets,
                            disable_compression=True)

                # 3. Dex files.
                if args.dex_file and args.dex_file.endswith(".zip"):
                    with zipfile.ZipFile(args.dex_file, mode="r") as dex_zip:
                        for dex in (d for d in dex_zip.namelist() if d.endswith(".dex")):
                            build_utils.add_to_zip_hermetic(out_apk, dex,
                                                            data=dex_zip.read(dex))
                elif args.dex_file:
                    build_utils.add_to_zip_hermetic(out_apk, "classes.dex",
                                                    src_path=args.dex_file)

                # 4.Native libraries
                _add_native_libraries(out_apk,
                                      native_libs,
                                      args.android_abi,
                                      args.uncompress_shared_libraries)
                if args.secondary_native_libs:
                    _add_native_libraries(out_apk,
                                          args.secondary_native_libs,
                                          args.secondary_android_abi,
                                          args.uncompress_shared_libraries)

                for name in sorted(args.native_lib_placeholders):
                    apk_path = "lib/%s/%s" % (args.android_abi, name)
                    build_utils.add_to_zip_hermetic(out_apk, apk_path,
                                                    data='')

                # 5. Resources
                for info in resource_infos[1:]:
                    copy_resource(info)

                # 6. Java resources. Used only when coverage is enabled, so order
                # doesn't matter
                if args.emma_device_jar:
                    with zipfile.ZipFile(args.emma_device_jar, "r") as emma_device_jar:
                        for apk_path in emma_device_jar.namelist():
                            apk_path_lower = apk_path.lower()
                            if apk_path_lower.startswith("meta-inf/"):
                                continue
                            if apk_path_lower.endswith("/"):
                                continue

                            if apk_path_lower.endswith(".class"):
                                continue

                            build_utils.add_to_zip_hermetic(out_apk, apk_path,
                                                            data=emma_device_jar.read(apk_path))

                # 7. srczip files.
                if args.srczip_path:
                    with zipfile.ZipFile(args.srczip_path, "r") as srczip_file:
                        for apk_path in srczip_file.namelist():
                            apk_path_lower = apk_path.lower()
                            if apk_path_lower.startswith("meta-inf/manifest.mf"):
                                continue
                            if apk_path_lower.endswith("/"):
                                continue
                            if apk_path_lower.endswith(".class"):
                                continue

                            build_utils.add_to_zip_hermetic(out_apk, apk_path,
                                                            data=srczip_file.read(apk_path))
                pass

            shutil.move(tmp_apk, args.output_apk)
            pass
        finally:
            if os.path.exists(tmp_apk):
                os.remove(tmp_apk)
        pass

    on_stale_md5(args)
    if args.depfile:
        python_deps = build_utils.get_python_dependencies()
        build_utils.write_dep_file(args.depfile, python_deps)
    pass


if __name__ == "__main__":
    main(sys.argv[1:])
    pass
