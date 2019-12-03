# -* encoding: utf-8 -*-

import argparse
import subprocess


def create_parser():
    parser = argparse.ArgumentParser(prog="gcc_solink_wrapper.py")
    parser.add_argument("--readelf",
                        required=True,
                        help="The readelf binary to run.",
                        metavar="PATH")
    parser.add_argument("--nm",
                        required=True,
                        help="The nm bianry to run.")
    parser.add_argument("--strip",
                        help="The strip binary to run.")
    parser.add_argument("--output",
                        required=True,
                        help="Output shared library path.")
    parser.add_argument("--sofile",
                        required=True,
                        help="Output unstripped shared library path.")
    parser.add_argument("--tocfile",
                        required=True,
                        help="Output top file path.")
    parser.add_argument("command",
                        nargs="+",
                        help="Link command")
    return parser


def main():
    parser = create_parser()
    args = parser.parse_args()

    # 编译生成sofile
    subprocess.check_call(args.command,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE)

    
    pass


if __name__ == "__main__":
    main()
    pass
