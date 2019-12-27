# -*- encoding: utf-8 -*-

import urllib.request
import io
import argparse


def create_parser():
    parser = argparse.ArgumentParser(prog="gn_download.py")
    parser.add_argument("--url")
    parser.add_argument("--output")
    return parser


def main():
    parser = create_parser()
    args = parser.parse_args()

    with urllib.request.urlopen(args.url) as response:
        assert (response.code == 200)
        with open(args.output, mode="wb") as dst_fp:
            while True:
                data = response.read(io.DEFAULT_BUFFER_SIZE)
                if not data:
                    break
                dst_fp.write(data)
    pass


if __name__ == '__main__':
    main()
    pass
