# -*- encoding: utf-8 -*-


import hashlib
import os
import zipfile
import json
import itertools


def call_and_record_if_stale(function,
                             record_path=None,
                             input_paths=None,
                             input_strings=None,
                             output_paths=None,
                             force=False,
                             pass_changes=False):
    assert (record_path or output_paths)
    input_paths = input_paths or []
    input_strings = input_strings or []
    output_paths = output_paths or []
    record_path = record_path or output_paths[0] + ".md5.stamp"

    if not record_path.endswith(".md5.stamp"):
        raise Exception()

    new_metadata = _Metadata()
    new_metadata.add_strings(input_strings)
    for path in input_paths:
        if _is_zip_file(path):
            new_metadata.add_zip_file(path, _extra_zip_entries(path))
            pass
        else:
            new_metadata.add_file(path, _md5_for_path(path))
            pass

    old_metadata = None
    missing_outputs = [
        x for x in output_paths if force or not os.path.exists(x)]
    # 输出没有缺失的时候
    if not missing_outputs and os.path.exists(record_path):
        with open(record_path, mode="r", encoding="utf-8") as fp:
            old_metadata = _Metadata.from_file(fp)

    changes = Changes(old_metadata, new_metadata, force, missing_outputs)
    if not changes.has_changes():
        return

    if pass_changes:
        function(changes)
    else:
        function()

    with open(record_path, mode="w+", encoding="utf-8") as fp:
        new_metadata.to_file(fp)
    pass


class _Metadata:
    def __init__(self):
        """
        """
        self._strings_md5 = None
        self._files_md5 = None
        self._strings = []
        self._files = []
        self._file_map = None
        pass

    @classmethod
    def from_file(cls, fileobj):
        """构造对象
        """
        ret = cls()
        obj = json.load(fileobj)
        ret._files_md5 = obj["files-md5"]
        ret._strings_md5 = obj["strings-md5"]
        ret._files = obj["input-files"]
        ret._strings = obj["input-strings"]
        return ret

    def to_file(self, fileobj):
        """写入文件
        """
        obj = {
            "strings-md5": self.strings_md5(),
            "files-md5": self.files_md5(),
            "input-strings": self._strings,
            "input-files": self._files,
        }
        json.dump(obj, fp=fileobj, indent=2)
        pass

    def add_strings(self, values):
        """添加字符串
        """
        self.assert_not_queried()
        self._strings.extend([str(v) for v in values])
        pass

    def add_file(self, path, tag):
        """添加文件
        """
        self.assert_not_queried()
        self._files.append({
            "path": path,
            "tag": tag
        })
        pass

    def add_zip_file(self, path, entries):
        """添加zip文件
        """
        self.assert_not_queried()
        tag = _compute_inline_md5(itertools.chain(
            (e[0] for e in entries),
            (e[1] for e in entries)
        ))
        self._files.append({
            "path": path,
            "tag": tag,
            "entries": [{"path": sub_path, "tag": tag} for sub_path, tag in entries]
        })
        pass

    def iter_paths(self):
        """路径
        """
        return (e["path"] for e in self._files)

    def iter_subpaths(self, path):
        """子路径
        """
        entry = self._get_entry(path)
        if not entry:
            return ()
        subentries = entry.get("entries", ())
        return (e["path"] for e in subentries)

    def _get_entry(self, path, subpath=None):
        """得到对应的map
        """
        if self._file_map is None:
            self._file_map = dict()
            for entry in self._files:
                self._file_map[(entry["path"], None)] = entry
                for sub_entry in entry.get("entries", []):
                    self._file_map[(
                        entry["path"], sub_entry["path"])] = sub_entry
                pass
        return self._file_map[(path, subpath)]

    def get_tag(self, path, subpath=None):
        """得到对应的md5
        """
        entry = self._get_entry(path, subpath)
        return entry and entry["tag"]

    def strings_md5(self):
        """
        """
        if self._strings_md5 is None:
            self._strings = _compute_inline_md5(self._strings)
        return self._strings_md5

    def files_md5(self):
        """文件MD5
        """
        if self._files_md5 is None:
            self._files_md5 = _compute_inline_md5(
                self.get_tag(path) for path in sorted(self.iter_paths()))
        return self._files_md5

    def assert_not_queried(self):
        """
        """
        assert (self._files_md5 is None)
        assert (self._strings_md5 is None)
        assert (self._file_map is None)
        pass


class Changes:
    def __init__(self,
                 old_metadata: _Metadata,
                 new_metadata: _Metadata,
                 force,
                 missing_outputs):
        self.old_metadata = old_metadata
        self.new_metadata = new_metadata
        self.force = force
        self.missing_outputs = missing_outputs
        pass

    def _get_old_tag(self, path, subpath=None):
        return self.old_metadata and self.old_metadata.get_tag(path, subpath)

    def has_changes(self):
        return (self.force
                or not self.old_metadata
                or self.old_metadata.strings_md5() != self.new_metadata.strings_md5()
                or self.old_metadata.files_md5() != self.new_metadata.files_md5())

    def added_or_modifed_only(self):
        """仅仅是增加文件或者修改了文件
        """
        if (self.force
                or not self.old_metadata
                or self.old_metadata.strings_md5() != self.new_metadata.strings_md5()):
            return False

        if any(self.iter_removed_paths()):
            return False
        for path in self.iter_modified_paths():
            if any(self.iter_removed_subpaths(path)):
                return False
        return True

    def iter_removed_paths(self):
        """删除的文件
        """
        if not self.old_metadata:
            return ()

        for path in self.old_metadata.iter_paths():
            if self.new_metadata.get_tag(path) is None:
                yield path
        pass

    def iter_removed_subpaths(self, path):
        """删除的子文件
        """
        if not self.old_metadata:
            return ()

        for subpath in self.old_metadata.iter_subpaths(path):
            if self.new_metadata.get_tag(path, subpath) is None:
                yield subpath

    def iter_added_paths(self):
        """添加文件
        """
        for path in self.new_metadata.iter_paths():
            if self._get_old_tag(path) is None:
                yield path
        pass

    def iter_added_subpaths(self, path):
        """添加文件
        """
        for subpath in self.new_metadata.iter_subpaths(path):
            if self._get_old_tag(path, subpath) is None:
                yield subpath
        pass

    def iter_modified_paths(self):
        """修改的文件
        """
        for path in self.new_metadata.iter_paths():
            old_tag = self._get_old_tag(path)
            if old_tag and old_tag != self.new_metadata.get_tag(path):
                yield path
        pass

    def iter_modified_subpaths(self, path):
        """修改的子文件
        """
        for subpath in self.new_metadata.iter_subpaths(path):
            old_tag = self._get_old_tag(path, subpath)
            if old_tag and old_tag != self.new_metadata.get_tag(path, subpath):
                yield subpath
        pass


def _update_md5_for_file(md5, path, block_size=2 ** 16):
    """计算MD5
    """
    with open(path, mode="rb") as fp:
        while True:
            data = fp.read(block_size)
            if not data:
                break
            md5.update(data)
        pass
    pass


def _update_md5_for_directory(md5, dir_path):
    """计算MD5
    """
    for root, _, files in os.walk(dir_path):
        for file in files:
            _update_md5_for_file(md5, os.path.join(root, file))
    pass


def _md5_for_path(path):
    """计算路径对应的MD5
    """
    md5 = hashlib.md5()
    if os.path.isdir(path):
        _update_md5_for_directory(md5, path)
    else:
        _update_md5_for_file(md5, path)
    return md5.hexdigest()


def _compute_inline_md5(iterables):
    """计算MD5
    """
    md5 = hashlib.md5()
    for item in iterables:
        md5.update(str(item).encode(encoding="utf-8"))
    return md5.hexdigest()


def _is_zip_file(path):
    """当做zip文件处理
    """
    if path.endswith(".interface.jar"):
        return False
    return path[-4:] in (".jar", ".zip", "apk") or path.endswith(".srcjar")


def _extra_zip_entries(path):
    """抽取内容
    """
    entries = []
    with zipfile.ZipFile(path) as zip_file:
        for info in zip_file.infolist():
            if info.CRC:
                entries.append((info.filename, info.CRC + info.compress_type))
    return entries
