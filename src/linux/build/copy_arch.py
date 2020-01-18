# -*- encoding: utf-8 -*-

import argparse
import sys
import os
import fnmatch
import shutil


def create_parser():
    parser = argparse.ArgumentParser(prog="copy_arch.py")
    parser.add_argument("--depfile", help="The depfile path.")
    parser.add_argument("--cpu-arch")
    parser.add_argument("--arch-dir",
                        help="The input arch base directory")
    parser.add_argument("--output-dir",
                        help="The output directory.")
    return parser


def parse_args(argv):
    parser = create_parser()
    args = parser.parse_args(argv)
    return args


def find_directory(directory, pattern):
    results = []
    for root, _, names in os.walk(directory):
        matched_names = [name for name in names
                         if fnmatch.fnmatch(name, pattern)]
        results.extend(os.path.normpath(os.path.join(root, x))
                       for x in matched_names)
        pass
    return results


def write_depfile(depfile, depends):
    with open(depfile, mode="w+", encoding="utf-8") as fp:
        fp.write(depfile)
        fp.write(" : ")
        fp.write("\n   ".join(depends))
        pass


def main(argv):
    args = parse_args(argv)

    input_dir = os.path.join(args.arch_dir, args.cpu_arch)
    output_dir = args.output_dir
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
        pass
    os.makedirs(output_dir, exist_ok=True)

    matched_files = find_directory(input_dir, "*.h")
    for src_path in matched_files:
        dst_path = os.path.relpath(src_path, input_dir)
        dst_path = os.path.join(output_dir, dst_path)
        shutil.copy(src_path, dst_path)

    if args.depfile:
        write_depfile(args.depfile, matched_files)
        pass


if __name__ == '__main__':
    main(sys.argv[1:])
    pass
