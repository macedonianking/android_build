# -*- encoding: utf-8 -*-

import re
import argparse


def main():
    parser = argparse.ArgumentParser(prog="test")
    parser.add_argument("-a", nargs="+", default=[])
    args = parser.parse_args(["-a", "a", "b"])
    print(args.a)
    pass


if __name__ == "__main__":
    main()
    pass
