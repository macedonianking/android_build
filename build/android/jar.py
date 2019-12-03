# -*- coding: utf-8 -*-

import os
import subprocess

from android import build_utils


def jar(class_files, classes_dir, jar_path, manifest_file=None, predicate=None):
    class_files_rel = [os.path.relpath(f, classes_dir) for f in class_files
                       if not predicate or predicate(f)]

    cmd = ["jar", "cf0",
           os.path.relpath(jar_path, classes_dir)]
    if manifest_file:
        cmd[1] += "m"
        cmd += [os.path.relpath(manifest_file, class_files)]

    if not class_files_rel:
        empty_file = os.path.join(classes_dir, ".empty")
        build_utils.touch(empty_file)
        class_files_rel.append(os.path.relpath(empty_file, classes_dir))
    cmd += class_files_rel
    subprocess.check_call(cmd, cwd=classes_dir)
    pass


def jar_directory(classes_dir, jar_path, manifest_file=None, predicate=None):
    class_files = build_utils.find_in_directory(classes_dir, "*.class")
    if predicate:
        class_files = [f for f in class_files
                       if predicate(f)]
    jar(class_files, classes_dir, jar_path,
        manifest_file=manifest_file, predicate=predicate)
    pass
