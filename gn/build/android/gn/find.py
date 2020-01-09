# -*- encoding: utf-8 -*-

import argparse
import os


def create_parser():
    parser = argparse.ArgumentParser(prog="find.py")
    parser.add_argument("dirs", nargs="+")
    return parser


def main():
    parser = create_parser()
    args = parser.parse_args()

    for dir_item in args.dirs:
        for root, _, filenames in os.walk(dir_item):
            for filename in filenames:
                print(os.path.join(root, filename))
    pass


if __name__ == "__main__":
    main()
    pass
