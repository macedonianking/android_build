# -*- encoding: utf-8 -*-

import subprocess
import sys
import locale


def main():
    if sys.stdout.encoding != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
    print("中国")
    pass


if __name__ == "__main__":
    main()
    pass
