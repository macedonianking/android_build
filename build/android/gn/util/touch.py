# -*- coding: utf-8 -*-

import argparse

from util import build_utils


def main():
    parser = argparse.ArgumentParser(prog="touch.py")
    parser.add_argument("file")
    args = parser.parse_args()
    build_utils.touch(args.file)
    pass


if __name__ == "__main__":
    main()
    pass
