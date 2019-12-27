# -*- encoding: utf-8 -*-

import sys
import argparse
import os
import fnmatch

from util import md5_metadata


def main():
    print(fnmatch.fnmatch("res/a/b.txt", "res/*"))
    pass


if __name__ == "__main__":
    main()
    pass
