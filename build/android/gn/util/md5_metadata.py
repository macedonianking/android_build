# -*- encoding: utf-8 -*-

import os
import json

from util import build_utils
from util import md5_check


class Metadata:
    def __init__(self):
        self._input_files = {}
        self._output_files = {}
        self._inputs_md5 = None
        self._outputs_md5 = None
        pass

    @classmethod
    def from_file(cls, fp):
        obj = json.load(fp)
        ret = cls()
        ret._output_files = obj["output_files"]
        ret._input_files = obj["input_files"]
        return ret

    def to_file(self, fp):
        obj = {
            "output_files": self._output_files,
            "input_files": self._input_files,
        }
        json.dump(obj, fp=fp, indent=2, sort_keys=True)
        pass

    def add_output_file(self, path):
        stat_obj = os.stat(path)
        self._output_files[path] = {
            "mtime": stat_obj.st_mtime_ns,
            "file_size": stat_obj.st_size,
        }
        pass

    def add_output_file_in_directory(self, directory, filename_filter):
        for path in build_utils.find_in_directory(directory, filename_filter):
            self.add_output_file(path)
        pass

    def add_output_file_in_directories(self, directories, filename_filter):
        for path in build_utils.find_in_directories(directories, filename_filter):
            self.add_output_file(path)
        pass

    def add_input_file(self, path):
        self._input_files[path] = md5_check.md5_for_path(path)
        pass

    def inputs_md5(self):
        if self._inputs_md5 is None:
            self._inputs_md5 = md5_check.compute_inline_md5((path, self.input_tag(path))
                                                            for path in self.input_paths())
        return self._inputs_md5

    def input_paths(self):
        ret = [x for x in self._input_files]
        ret.sort()
        return ret

    def input_tag(self, path):
        return self._input_files.get(path, None)

    def output_paths(self):
        ret = [x for x in self._output_files]
        ret.sort()
        return ret

    def output_tag(self, path):
        return self._output_files.get(path)

    def outputs_md5(self):
        if self._outputs_md5 is None:
            self._outputs_md5 = md5_check.compute_inline_md5((path, self.output_tag(path))
                                                             for path in self.output_paths())
        return self._outputs_md5

    def is_outputs_empty(self):
        return not bool(self._output_files)


class Changes:
    def __init__(self, old_metadata: Metadata, new_metadata: Metadata):
        self._old_metadata = old_metadata
        self._new_metadata = new_metadata
        pass

    def has_changes(self):
        if not self._old_metadata:
            return True
        if self._old_metadata.inputs_md5() != self._new_metadata.inputs_md5():
            return True
        if self._old_metadata.outputs_md5() != self._new_metadata.outputs_md5():
            return True
        if self._new_metadata.is_outputs_empty():
            return True
        return False

    def is_only_outputs_changed(self):
        if not self._old_metadata:
            return False
        if self._old_metadata.inputs_md5() != self._new_metadata.inputs_md5():
            return False
        return True

