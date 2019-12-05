# -*- coding: utf-8 -*-

import argparse
import subprocess
import os
import shutil

from util import build_utils


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="finalize_apk.py")
    parser.add_argument("--depfile")
    parser.add_argument("--rezip-apk-jar-path",
                        help="Path to the RezipApk jar file.")
    parser.add_argument("--zipalign-path",
                        help="Path to the zipalign tool.")
    parser.add_argument("--page-align-shared-libraries",
                        action="store_true",
                        help="Page align shared libraries.")
    parser.add_argument("--unsigned-apk-path",
                        help="Path to the input unsigned APK.")
    parser.add_argument("--final-apk-path",
                        help="Path to output signed and aligned APK.")
    parser.add_argument("--key-path",
                        help="Path to the keystore for signing.")
    parser.add_argument("--key-passwd",
                        help="Keystore password.")
    parser.add_argument("--key-name",
                        help="Keystore name.")
    parser.add_argument("--stamp",
                        help="Path to touch on success.")
    parser.add_argument("--load-library-from-zip",
                        type=int,
                        help="If non-zero, build the APK such that the library can be loaded "
                        + "directly from the zip file using the crasing linker. The library "
                        + "will be renamed, uncompressed and page aligned.")
    parser.add_argument("--base-dir",
                        required=True,
                        help="The path to the build directory")
    return parser


def parse_args():
    parser = create_parser()
    args = parser.parse_args()
    return args


def rename_inflate_and_add_page_alignment(rezip_apk_jar_path, in_zip_file,
                                          out_zip_file):
    rezip_apk_cmd = [
        "java",
        "-classpath",
        rezip_apk_jar_path,
        "RezipApk",
        "renamealign",
        in_zip_file,
        out_zip_file,
    ]
    subprocess.check_call(rezip_apk_cmd)
    pass


def record_and_align_apk(rezip_apk_jar_path,
                         in_zip_file, out_zip_file):
    rezip_apk_cmd = [
        "java",
        "-classpath",
        rezip_apk_jar_path,
        "RezipApk",
        "reorder",
        in_zip_file,
        out_zip_file,
    ]
    subprocess.check_call(rezip_apk_cmd)
    pass


def jar_signer(key_path, key_name, key_passwd,
               unsigned_path, signed_path):
    shutil.copy(unsigned_path, signed_path)
    sign_cmd = [
        "jarsigner",
        "-sigalg", "MD5withRSA",
        "-digestalg", "SHA1",
        "-keystore", key_path,
        "-storepass", key_passwd,
        signed_path,
        key_name
    ]
    subprocess.check_call(sign_cmd,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE)


def align_apk(zipalign_path, package_align, unaligned_path, final_path):
    align_cmd = [
        zipalign_path,
        "-f",
    ]

    if package_align:
        align_cmd += ["-p"]

    align_cmd += [
        "4",
        unaligned_path,
        final_path,
    ]

    subprocess.check_call(align_cmd)
    pass


def _finalize_apk(args):
    base_dir = args.base_dir
    build_utils.make_directory(base_dir)
    build_utils.remove_subtree(base_dir)

    input_apk_basename = os.path.basename(args.unsigned_apk_path)
    (input_apk_name, input_apk_extension) = os.path.splitext(input_apk_basename)

    apk_to_sign_tmp = os.path.join(base_dir, input_apk_basename)
    if args.load_library_from_zip:
        apk_to_sign = apk_to_sign_tmp
        rename_inflate_and_add_page_alignment(args.rezip_apk_jar_path,
                                              args.unsigned_apk_path,
                                              apk_to_sign)
    else:
        apk_to_sign = args.unsigned_apk_path

    signed_apk_path = os.path.join(base_dir,
                                   "%s-signed%s" % (input_apk_name, input_apk_extension))
    jar_signer(args.key_path, args.key_name, args.key_passwd,
               apk_to_sign, signed_apk_path)

    if args.load_library_from_zip:
        record_and_align_apk(args.rezip_apk_jar_path,
                             signed_apk_path, args.finalize_apk)
    else:
        align_apk(args.zipalign_path,
                  args.page_align_shared_libraries,
                  signed_apk_path,
                  args.final_apk_path)
    pass


def main():
    args = parse_args()
    # print(args)

    input_paths = [
        args.unsigned_apk_path,
        args.key_path
    ]

    if args.load_library_from_zip:
        input_paths.append(args.rezip_apk_jar_path)

    input_strings = [
        args.load_library_from_zip,
        args.key_name,
        args.key_passwd,
        args.page_align_shared_libraries
    ]

    _finalize_apk(args)
    if args.depfile:
        python_deps = build_utils.get_python_dependencies()
        build_utils.write_dep_file(args.depfile, python_deps)

    pass


if __name__ == "__main__":
    main()
    pass
