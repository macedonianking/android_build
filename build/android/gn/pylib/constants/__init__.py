# -*- coding: utf-8 -*-

import os
import sys

is_windows = sys.platform == "win32"
if is_windows:
    _proguard_sript_name = "proguard.bat"
else:
    _proguard_sript_name = "proguard.sh"

PROGUARD_SCRIPT_PATH = os.path.join("tools",
                                    "progurad",
                                    "bin",
                                    _proguard_sript_name)
