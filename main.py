# -*- encoding: utf-8 -*-

import re

from string import Template


def main():
    _library_pattern = re.compile(".*?\\[(?P<library_name>.+)\\]")
    sources = "SHARED LIBRARY [libhello.so]\nSHARED LIBRARY [libfoo.so]"
    for pat in _library_pattern.finditer(sources):
        print(pat.group(1))
        pass


if __name__ == "__main__":
    main()
    pass
