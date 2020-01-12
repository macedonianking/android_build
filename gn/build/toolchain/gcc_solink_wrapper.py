# -* encoding: utf-8 -*-

import argparse
import subprocess


def create_parser():
    parser = argparse.ArgumentParser(prog="gcc_solink_wrapper.py")
    parser.add_argument("--readelf",
                        help="The readelf binary to run.",
                        metavar="PATH")
    parser.add_argument("--nm",
                        help="The nm binary to run.")
    parser.add_argument("--strip",
                        help="The strip binary to run.")
    parser.add_argument("--output",
                        help="Output shared library path.")
    parser.add_argument("--sofile",
                        help="Output unstripped shared library path.")
    parser.add_argument("--tocfile",
                        help="Output top file path.")
    parser.add_argument("command",
                        nargs="+",
                        help="Link command")
    return parser


def main():
    parser = create_parser()
    args = parser.parse_args()

    # 编译生成sofile
    subprocess.check_call(args.command)

    pass


if __name__ == "__main__":
    main()
    pass
