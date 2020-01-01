# -*- coding: utf-8 -*-

import argparse
import ast
import contextlib
import fnmatch
import json
import os
import pathlib
import pipes
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import zipfile

from util import md5_check

_ROOT_DIR = os.path.abspath(os.path.join(__file__, ".."))

AAPT_IGNORE_PATTERN = ('!OWNERS:!.svn:!.git:!.ds_store:!*.scc:.*:<dir>_*:' +
                       '!CVS:!thumbs.db:!picasa.ini:!*~:!*.d.stamp')

CLASSPATH_SEP = ":"
if sys.platform == "win32":
    CLASSPATH_SEP = ";"

_HERMETIC_TIMESTAMP = (2001, 1, 1, 0, 0, 0)
_HERMETIC_ATTR = (0o644 << 16)


def add_depfile_option(parser: argparse.ArgumentParser):
    """添加depfile的选项
    """
    parser.add_argument("--depfile",
                        help="Path to depfile. Must be specified as the target's "
                             "first output.")
    pass


def check_options(args, parser: argparse.ArgumentParser, required=None):
    """检查必须的选项
    """
    if not required:
        return
    for option_name in required:
        if getattr(args, option_name) is None:
            parser.error("--%s is required" % option_name.replace("_", "-"))
    pass


def read_json(path):
    with open(path, mode="r", encoding="utf-8")as fp:
        return json.load(fp=fp)


def write_json(obj, path, only_if_change=False):
    old_dump = None
    if os.path.exists(path):
        with open(path, mode="r", encoding="utf-8") as fp:
            old_dump = fp.read()
            pass

    new_dump = json.dumps(obj, indent=2)

    if not only_if_change or old_dump != new_dump:
        with open(path, mode="w+", encoding="utf-8") as fp:
            fp.write(new_dump)
        pass


def get_sorted_transitive_dependencies(deps_configs, func):
    """依赖项的顺序
    :param deps_configs:
    :param func:
    """
    all_deps = set(deps_configs)
    unchecked_deps = list(deps_configs)
    while unchecked_deps:
        dep_item = unchecked_deps.pop(0)
        new_deps = func(dep_item).difference(all_deps)
        all_deps.update(new_deps)
        unchecked_deps.extend(new_deps)
        pass

    unsorted_deps = dict(map(lambda dep: (dep, func(dep)), all_deps))
    results = []
    while unsorted_deps:
        last_n = len(unsorted_deps)
        for config, dependencies in unsorted_deps.items():
            if not dependencies.difference(results):
                results.append(config)
                del unsorted_deps[config]
                break
            pass
        curr_n = len(unsorted_deps)
        if last_n == curr_n:
            for config, dependencies in unsorted_deps.items():
                print("%s : " % config)
                for item in dependencies:
                    print("\t --> %s" % item)
            raise Exception()
    return results


def get_python_dependencies():
    """得到当前模块的依赖项
    """
    module_paths = [m.__file__ for m in sys.modules.values()
                    if m is not None and hasattr(m, "__file__")]
    module_paths = []
    for m in sys.modules.values():
        if m and hasattr(m, "__file__") and m.__file__:
            module_paths.append(m.__file__)
            pass
        pass
    abs_module_paths = [os.path.normpath(os.path.abspath(path))
                        for path in module_paths]

    non_sys_module_paths = [path for path in abs_module_paths
                            if path.startswith(_ROOT_DIR)]
    return sorted(list(non_sys_module_paths))


def write_dep_file(path, inputs):
    """写依赖文件
    """
    with open(path, mode="w+", encoding="utf-8") as fp:
        print("%s : \\\n    " % path, file=fp, end="")
        print(" \\\n    ".join(inputs), file=fp, end="")
    pass


def write_sources_file(path, sources):
    with open(path, mode="w+", encoding="utf-8") as fp:
        for line in sources:
            print(line, file=fp)
        pass
    pass


def touch(path):
    path_obj = pathlib.Path(path)
    path_obj.touch()
    pass


def expand_file_args(args):
    """扩展参数
    """
    new_args = list(args)
    file_jsons = dict()
    r = re.compile(r"@FileArg\((.*?)\)")
    for i, arg in enumerate(args):
        match = r.search(arg)
        if not match:
            continue

        lookup_path = match.group(1).replace("$", "").split(":")
        file_path = lookup_path[0]
        if file_path not in file_jsons:
            file_jsons[file_path] = read_json(file_path)

        expansion = file_jsons[file_path]
        for path in lookup_path[1:]:
            expansion = expansion[path]

        new_args[i] = arg[:match.start()] + str(expansion)
        pass

    return new_args


@contextlib.contextmanager
def temp_dir():
    dirname = tempfile.mkdtemp()
    try:
        yield dirname
    finally:
        shutil.rmtree(dirname)


def make_directory(path):
    os.makedirs(path, exist_ok=True)
    pass


def make_directory_for_file(path):
    make_directory(os.path.dirname(path))
    pass


def delete_directory(directory):
    if os.path.exists(directory):
        shutil.rmtree(directory)
    pass


def remove_subtree(base_dir):
    """
    """
    if not os.path.isdir(base_dir):
        return
    filenames = [os.path.join(base_dir, name)
                 for name in os.listdir(base_dir)]
    for path in filenames:
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)
    pass


def find_in_directory(directory, filename_filter):
    """在文件夹中查找文件
    """
    files = []
    for root, _, filenames in os.walk(os.path.normpath(directory)):
        filtered_names = fnmatch.filter(filenames, filename_filter)
        files.extend([os.path.join(root, name) for name in filtered_names])
    return files


def find_in_directories(directories, filename_filter):
    files = []
    for dir_path in directories:
        files.extend(find_in_directory(dir_path, filename_filter))
    return files


def matches_glob(path, filters):
    """符合规则
    """
    return filters and any(fnmatch.fnmatch(path, pat)
                           for pat in filters)


def merge_zips(output, inputs, exclude_patterns=None, path_transform=None):
    """合并多个zip文件到output_file中
    """
    path_transform = path_transform or (lambda p, f: p)
    added_names = set()

    with zipfile.ZipFile(output, "w") as out_zip:
        for in_file in inputs:
            with zipfile.ZipFile(in_file, "r") as in_zip:
                in_zip._expected_crc = None
                for info in in_zip.infolist():
                    if info.filename.endswith("/"):
                        continue
                    dst_name = path_transform(info.filename, in_file)
                    if (dst_name not in added_names) and not matches_glob(dst_name, exclude_patterns):
                        out_zip.writestr(dst_name, in_zip.read(info.filename))
                        added_names.add(dst_name)
    pass


def parse_gn_list(gn_string):
    """解析列表
    """
    return ast.literal_eval(gn_string)


def parse_gyp_list(gn_string):
    """解析列表
    """
    gn_string = gn_string.replace("##", "$")
    if gn_string.startswith("["):
        return parse_gn_list(gn_string)
    return shlex.split(gn_string)


def call_and_write_dep_file_if_stale(function,
                                     args,
                                     record_path=None,
                                     input_strings=None,
                                     input_paths=None,
                                     output_paths=None,
                                     force=False,
                                     pass_changes=False,
                                     depfile_deps=None):
    if not output_paths:
        raise Exception()

    input_strings = list(input_strings or [])
    input_paths = list(input_paths or [])
    output_paths = list(output_paths or [])

    python_deps = None
    if hasattr(args, "depfile"):
        python_deps = get_python_dependencies()
        input_strings += python_deps
        output_paths += [args.depfile]
        pass

    stamp_file = hasattr(args, "stamp") and args.stamp
    if stamp_file:
        output_paths += [stamp_file]

    def on_stale(changes):
        stale_args = (changes,) if pass_changes else ()
        function(*stale_args)

        if python_deps is not None:
            all_depfile_deps = list(python_deps)
            if depfile_deps:
                all_depfile_deps.extend(depfile_deps)
            write_dep_file(args.depfile, all_depfile_deps)
            pass

        if stamp_file:
            touch(stamp_file)
        pass

    md5_check.call_and_record_if_stale(on_stale,
                                       record_path=record_path,
                                       input_strings=input_strings,
                                       input_paths=input_paths,
                                       output_paths=output_paths,
                                       force=force,
                                       pass_changes=True)
    pass


def do_zip(inputs, output, base_dir=None):
    input_paths = []
    for item in inputs:
        if isinstance(item, str):
            # 单独的路径
            archive_name = os.path.relpath(item, base_dir)
            archive_name = archive_name.replace("\\", "/")
            input_paths.append((archive_name, item))
        else:
            input_paths.append(item)
    input_paths.sort(key=lambda x: x[0])

    with zipfile.ZipFile(output, mode="w") as zip_file:
        for archive_name, path in input_paths:
            zip_file.write(path, archive_name)
        pass
    pass


def zip_dir(output, base_dir):
    inputs = []
    for root, _, filenames in os.walk(base_dir):
        inputs.extend(os.path.join(root, name) for name in filenames)
    do_zip(inputs, output, base_dir)
    pass


def check_zip_path(name):
    pass


def extract_all(zip_path,
                base_dir=None,
                no_clobber=True,
                pattern=None,
                predicate=None):
    """解压文件
    @param no_clobber: 不能覆盖
    """
    if base_dir is None:
        base_dir = os.getcwd()
    elif not os.path.exists(base_dir):
        make_directory(base_dir)

    with zipfile.ZipFile(zip_path) as zip_file:
        for name in zip_file.namelist():
            if name.endswith("/"):
                continue
            if pattern is not None:
                if not fnmatch.fnmatch(name, pattern):
                    continue
            if predicate and not predicate(name):
                continue
            if no_clobber:
                output_path = os.path.join(base_dir, name)
                if os.path.exists(output_path):
                    raise Exception("%s already exists" % output_path)
            zip_file.extract(name, base_dir)  # 释放一个成员
            pass
    pass


def add_to_zip_hermetic(zip_file: zipfile.ZipFile, zip_path,
                        src_path=None,
                        data=None,
                        compress=None):
    """添加到文件
    """
    zip_info = zipfile.ZipInfo(zip_path, date_time=_HERMETIC_TIMESTAMP)
    zip_info.external_attr = _HERMETIC_ATTR

    if src_path is not None:
        with open(src_path, mode="rb") as fp:
            data = fp.read()

    if len(data) < 16:
        compress = False

    compress_type = zip_file.compression
    if compress is not None:
        compress_type = zipfile.ZIP_DEFLATED if compress else zipfile.ZIP_STORED
    zip_file.writestr(zip_info, data, compress_type)
    pass


def join_classpath(paths):
    if sys.platform == "win32":
        return ";".join(paths)
    else:
        return ":".join(paths)


def is_windows():
    return sys.platform == "win32"


class CalledProcessError(Exception):
    def __init__(self, cwd, args, output):
        super(CalledProcessError, self).__init__()

        self.cwd = cwd
        self.args = args
        self.output = output
        pass

    def __str__(self):
        copyable_command = "cd {}; {}".format(self.cwd, " ".join(
            pipes.quote(arg) for arg in self.args))
        return "{}\n{}".format(copyable_command, self.output)

    pass


def check_output(args,
                 cwd=None, env=None,
                 print_stdout=False, print_stderr=True,
                 stdout_filter=None,
                 stderr_filter=None,
                 fail_func=lambda return_code, stderr: return_code != 0):
    """执行子进程获取到输出
    """
    if cwd is None:
        cwd = os.getcwd()

    child = subprocess.Popen(args, cwd=cwd, env=env,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,
                             text=True)
    stdout, stderr = child.communicate()

    if stdout_filter is not None:
        stdout = stdout_filter(stdout)
    if stderr_filter is not None:
        stderr = stderr_filter(stderr)

    if fail_func(child.returncode, stderr):
        raise CalledProcessError(cwd, args, stdout + stderr)

    return stdout


def check_stdout_encoding():
    """check stdout & stderr encoding
    """
    if sys.stdout.encoding != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
    if sys.stderr.encoding != "utf-8":
        sys.stderr.reconfigure(encoding="utf-8")
    pass


def to_gn_absolute_path(root_dir, path):
    name = os.path.relpath(os.path.abspath(path), os.path.abspath(root_dir))
    return "//" + name.replace("\\", "/")

def to_gn_target_name(artifact):
    return artifact.replace("-", "_").replace(":", "_").replace(".", "_")