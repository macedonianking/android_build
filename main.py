# -*- encoding: utf-8 -*-

import sys
import argparse
import os

from util import md5_metadata


def main():
    data = md5_metadata.Metadata()
    data.add_output_file_in_directory("src", "*")
    with open("test.json", "w") as fp:
        data.to_file(fp)
    pass


if __name__ == "__main__":
    main()
    pass
