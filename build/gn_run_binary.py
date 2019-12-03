# -*- coding: utf-8 -*-

import sys
import subprocess


def main():
    path = './' + sys.argv[1]
    args = [path] + sys.argv[2:]

    subprocess.check_call(args)
    pass


if __name__ == "__main__":
    main()
    pass
