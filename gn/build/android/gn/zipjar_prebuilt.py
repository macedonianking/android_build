# -*- encoding: utf-8 -*-

import argparse

from util import build_utils


def create_parser():
    parser = argparse.ArgumentParser(prog="zipjar_prebuilt.py")
    build_utils.add_depfile_option(parser)
    parser.add_argument("--zipjar-path",
                        help="The path to output zipjar path")
    parser.add_argument("--jar-path",
                        help="The input jar path.")
    parser.add_argument("--base-dir",
                        help="The working directory.")
    return parser


def parse_args():
    parser = create_parser()
    args = parser.parse_args()
    return args


def main():
    args = parse_args()

    input_strings = [args.base_dir]
    input_paths = [args.jar_path]
    output_paths = [args.zipjar_path]

    build_utils.call_and_write_dep_file_if_stale(lambda: on_stale_md5(args),
                                                 args,
                                                 input_strings=input_strings,
                                                 input_paths=input_paths,
                                                 output_paths=output_paths)
    pass


def on_stale_md5(args):
    build_utils.remove_subtree(args.base_dir)
    build_utils.make_directory(args.base_dir)

    def predicate(name):
        if name.endswith(".class"):
            return False
        if name.startswith("META-INF/maven"):
            return False
        if name in ("META-INF/MANIFEST.MF",):
            return False
        return True

    build_utils.extract_all(args.jar_path, args.base_dir,
                            predicate=predicate)
    zip_files = build_utils.find_in_directory(args.base_dir, "*")
    build_utils.do_zip(zip_files, args.zipjar_path, args.base_dir)
    if args.depfile:
        dep_files = build_utils.get_python_dependencies()
        build_utils.write_dep_file(args.depfile, dep_files)


if __name__ == '__main__':
    main()
    pass
