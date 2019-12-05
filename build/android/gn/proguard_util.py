# -*- coding: utf-8 -*-

import os
import re

from util import build_utils


class _ProguardOututFilter(object):
    IGNORE_RE = re.compile(
        r"(?:Pro.*version|Note:|Reading|Preparing|.*:.*(?:MANIFEST\.MF|\.empty))"
    )

    def __init__(self):
        self._last_line_ignored = False
        pass

    def __call__(self, output):
        ret = []
        for line in output.splitlines(True):
            if not line.startswith(" "):
                self._last_line_ignored = bool(self.IGNORE_RE.match(line))
            elif "You should check if you need to specify" in line:
                self._last_line_ignored = True

            if not self._last_line_ignored:
                ret.append(line)
        return "".join(ret)
    pass


class ProguardCmdBuilder(object):
    def __init__(self, proguard_jar):
        assert(os.path.exists(proguard_jar))
        self._proguard_jar_path = proguard_jar
        self._tested_apk_info_path = None
        self._tested_apk_info = None
        self._mapping = None
        self._libraries = None
        self._injars = None
        self._configs = None
        self._outjar = None
        self._cmd = None
        self._verbose = None
        pass

    def outjar(self, path):
        assert(self._cmd is None)
        assert(self._outjar is None)
        self._outjar = path
        pass

    def tested_apk_info(self, tested_apk_info_path):
        assert(self._cmd is None)
        assert(self._tested_apk_info is None)
        self._tested_apk_info_path = tested_apk_info_path

    def mapping(self, path):
        assert(self._cmd is None)
        assert(self._mapping is None)
        assert(os.path.exists(path))
        pass

    def libraryjars(self, paths):
        assert(self._cmd is None)
        assert(self._libraries is None)
        for p in paths:
            assert(os.path.exists(p))
        self._libraries = list(paths)
        pass

    def injars(self, paths):
        assert(self._cmd is None)
        assert(self._injars is None)
        for p in paths:
            assert(os.path.exists(p))
        self._injars = list(paths)
        pass

    def configs(self, paths):
        assert(self._cmd is None)
        assert(self._configs is None)
        for p in paths:
            assert(os.path.exists(p))
        self._configs = list(paths)
        pass

    def verbose(self, verbose):
        assert(self._cmd is None)
        self._verbose = verbose
        pass

    def build(self):
        if self._cmd:
            return self._cmd
        assert(self._injars is not None)
        assert(self._outjar is not None)
        assert(self._configs is not None)
        cmd = ["java", "-jar", self._proguard_jar_path,
               "-forceprocessing"
               ]
        if self._tested_apk_info_path:
            assert(len(self._configs) == 1)
            tested_apk_info = build_utils.read_json(self._tested_apk_info_path)
            self._configs += tested_apk_info["configs"]
            self._injars = [p for p in self._injars
                            if p not in tested_apk_info["inputs"]]
            if not self._libraries:
                self._libraries = []
            self._libraries += tested_apk_info["inputs"]
            self._mapping = tested_apk_info["mapping"]
            cmd += [
                "-dontobfuscate",
                "-dontoptimize",
                "-dontshrink",
                "-dontskipnonpubliclibraryclassmembers",
            ]

        if self._mapping:
            cmd += [
                "-applymapping", self._mapping
            ]

        if self._libraries:
            cmd += [
                "-libraryjars",
                build_utils.CLASSPATH_SEP.join(self._libraries)
            ]

        cmd += [
            "-injars",
            build_utils.CLASSPATH_SEP.join(self._injars)
        ]

        for config_file in self._configs:
            cmd += ["-include", config_file]

        cmd += [
            "-outjar", self._outjar,
            "-dump", self._outjar + ".dump",
            "-printseeds", self._outjar + ".seeds",
            "-printusage", self._outjar + ".usage",
            "-printmapping", self._outjar + ".mapping",
        ]

        if self._verbose:
            cmd.append("-verbose")

        self._cmd = cmd
        return self._cmd

    def get_inputs(self):
        self.build()
        inputs = [self._proguard_jar_path] + self._configs + self._injars
        if self._mapping:
            inputs.append(self._mapping)
        if self._libraries:
            inputs.extend(self._libraries)
        if self._tested_apk_info_path:
            inputs.append(self._tested_apk_info_path)
        return inputs
    pass

    def check_output(self):
        self.build()
        open(self._outjar + ".dump", "w").close()
        open(self._outjar + ".seeds", "w").close()
        open(self._outjar + ".usage", "w").close()
        open(self._outjar + ".mapping", "w").close()
        stdout_filter = None
        stderr_filter = None
        if not self._verbose:
            stdout_filter = _ProguardOututFilter()
            stderr_filter = _ProguardOututFilter()

        build_utils.check_output(args=self.build(),
                                 print_stdout=True,
                                 print_stderr=True,
                                 stdout_filter=stdout_filter,
                                 stderr_filter=stderr_filter)
        this_info = {
            "inputs": self._injars,
            "configs": self._configs,
            "mapping": self._outjar + ".mapping"
        }
        build_utils.write_json(this_info, self._outjar + ".info")
        pass
