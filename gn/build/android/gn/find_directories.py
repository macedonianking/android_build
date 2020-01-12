# -*- encoding: utf-8 -*-

import argparse
import fnmatch
import os


def create_parser():
    parser = argparse.ArgumentParser(prog="find_directories.py")
    parser.add_argument("-p", "--include-pattern",
                        action="append")
    parser.add_argument("-e", "--exclude-pattern",
                        action="append")
    parser.add_argument("dirs", nargs="+")
    return parser


def parse_args():
    parser = create_parser()
    args = parser.parse_args()
    return args


def find_in_directory(directory, predicate):
    results = []
    for root, _, names in os.walk(directory):
        matched_files = [os.path.join(root, item) for item in names]
        if predicate:
            matched_files = [name for name in matched_files
                             if predicate(name)]
        results.extend(matched_files)
    return results


def match_glob(name, patterns):
    return patterns and any(fnmatch.fnmatch(name, pat)
                            for pat in patterns)


def main():
    args = parse_args()

    def predicate(filename):
        if args.include_pattern and not match_glob(filename, args.include_pattern):
            return False
        if args.exclude_pattern and match_glob(filename, args.exclude_pattern):
            return False
        return True

    for directory in args.dirs:
        for item in find_in_directory(directory, predicate):
            print(item)

    pass


if __name__ == '__main__':
    main()
    pass
