# -*- encoding: utf-8 -*-

import argparse
import json
import sys

from util import build_utils


def create_parser():
    parser = argparse.ArgumentParser(prog="maven_download.py")
    parser.add_argument("--depname", action="append", default=[])
    return parser


def parse_args():
    parser = create_parser()
    args = parser.parse_args()
    return args


def main():
    args = parse_args()
    depname_list = args.depname

    config = {
        "deps": []
    }
    config["deps"].extend(":" + build_utils.to_gn_target_name(x) for x in depname_list)
    json.dump(config, fp=sys.stdout)
    pass


if __name__ == '__main__':
    main()
    pass
