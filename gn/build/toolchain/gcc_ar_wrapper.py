# -*- encoding: utf-8 -*-

import sys
import os
import argparse
import subprocess


def create_parser():
    parser = argparse.ArgumentParser(prog="gcc_ar_wrapper.py")
    parser.add_argument("--ar",
                        required=True,
                        help="The ar binary to run.",
                        metavar="PATH")
    parser.add_argument("--output",
                        required=True,
                        help="Output archive file.",
                        metavar="ARCHIVE")
    parser.add_argument("operations",
                        help="Operation on the archive")
    parser.add_argument("inputs",
                        nargs="+",
                        help="Input files")
    return parser


def main():
    parser = create_parser()
    args = parser.parse_args()

    if os.path.exists(args.output):
        os.remove(args.output)

    cmds = [args.ar,
            args.operations,
            args.output]
    cmds.extend(args.inputs)
    subprocess.check_call(cmds)
    pass


if __name__ == "__main__":
    main()
    pass
