# -*- encoding: utf-8 -*-

import argparse
import os
import xml.dom.minidom
import itertools

from util import build_utils

_ROOT_TYPES = ("android_apk", "deps_dex", "java_binary", "resources_rewriter")
_RESOURCES_TYPES = ("android_resources", "android_assets")

ANDROID_NS = "http://schemas.android.com/apk/res/android"


class AndroidManifest:
    def __init__(self, path):
        doc = xml.dom.minidom.parse(path)
        manifest_els = doc.getElementsByTagName("manifest")
        self.path = path
        self.manifest = manifest_els[0]
        pass

    def get_instrumentation(self):
        instrumentation_els = self.manifest.getElementsByTagName(
            "instrumentation")
        if len(instrumentation_els) == 0:
            return None
        if len(instrumentation_els) != 1:
            raise Exception(
                "More than one <instrumentation> element found in %s" % self.path)
        return instrumentation_els[0]

    def check_instrumentation(self, expected_package):
        instr = self.get_instrumentation()
        if not instr:
            raise Exception(
                "No <instrumentation> elements found in %s" % self.path)
        instrumentation_package = instr.getAttributeNS(ANDROID_NS,
                                                       "targetPackage")
        if instrumentation_package != expected_package:
            raise Exception("Wrong instrumented package. Expected %s, got %s" % (
                expected_package, instrumentation_package))
        pass

    def get_package_name(self):
        """获取包名
        """
        return self.manifest.getAttribute("package")

    pass


class Deps:
    def __init__(self, direct_deps_config_paths):
        self.all_deps_config_paths = get_all_deps_configs_in_order(
            direct_deps_config_paths)
        self.direct_deps_configs = resolve_groups([get_dep_config(path)
                                                   for path in direct_deps_config_paths])
        self.all_deps_configs = [get_dep_config(path)
                                 for path in self.all_deps_config_paths]
        self.direct_deps_config_paths = direct_deps_config_paths
        pass

    def all(self, wanted_type=None):
        """所有的依赖项
        """
        if wanted_type is None:
            return self.all_deps_configs
        return deps_of_type(wanted_type, self.all_deps_configs)

    def direct(self, wanted_type=None):
        """直接依赖项，直接内联了group的依赖项
        """
        if wanted_type is None:
            return self.direct_deps_configs
        return deps_of_type(wanted_type, self.direct_deps_configs)

    def all_config_paths(self):
        """所有依赖项的路径
        """
        return self.all_deps_config_paths

    def remove_non_direct_dep(self, path):
        """移除一个非直接依赖项
        """
        if path in self.direct_deps_config_paths:
            raise Exception("'%s' is in direct deps config paths")
        self.all_deps_config_paths.remove(path)
        self.all_deps_configs.remove(get_dep_config(path))
        pass

    pass


def _merge_assets(all_assets):
    """Merges all assets from the given deps.

    Returns:
        A tuple of lists: (compressed, uncompressed)
        Each tuple entry is a list of "srcPath:zipPath". srcPath is the path of the 
        asset to add, and zipPath is the location within the zip (excluding assets/
        prefix).
    """
    compressed = {}
    uncompressed = {}
    for asset_dep in all_assets:
        entry = asset_dep["assets"]
        disable_compression = entry.get("disable_compression", False)
        dest_map = uncompressed if disable_compression else compressed
        other_map = compressed if disable_compression else uncompressed
        outputs = entry.get("outputs", [])
        for src, dest in itertools.zip_longest(entry["sources"], outputs):
            if not dest:
                dest = os.path.basename(src)
            other_map.pop(dest, 0)
            dest_map[dest] = src

    def create_list(asset_map):
        ret = ["%s:%s" % (src, dest) for dest, src in asset_map.items()]
        ret.sort()
        return ret

    return create_list(compressed), create_list(uncompressed)


def create_parser() -> argparse.ArgumentParser:
    """创建参数的解析器
    """
    parser = argparse.ArgumentParser(prog="write_build_config.py")
    parser.add_argument("--build-config")
    build_utils.add_depfile_option(parser)
    parser.add_argument("--type")
    parser.add_argument("--possible-deps-configs",
                        nargs="*", metavar="CONFIG")  # 依赖项

    # android resources
    parser.add_argument("--srcjar")
    parser.add_argument("--package-name")
    parser.add_argument("--r-text")
    parser.add_argument("--android-manifest")
    parser.add_argument("--resources-zip")
    parser.add_argument("--is-locale-resource",
                        action="store_true")

    # android_assets
    parser.add_argument("--asset-sources", nargs="*")
    parser.add_argument("--asset-renaming-sources", nargs="*")
    parser.add_argument("--asset-renaming-destinations", nargs="*")
    parser.add_argument("--disable-asset-compression", action="store_true")

    # java_library
    parser.add_argument("--jar-path")
    parser.add_argument("--supports-android", action="store_true")
    parser.add_argument("--requires-android", action="store_true")
    parser.add_argument("--bypass-platform-checks", action="store_true")
    parser.add_argument("--srczip-path",
                        help="Specifies the path to the *.srczip")

    # android library options.
    parser.add_argument("--dex-path", help="Path to target's dex output.")

    # native library options
    parser.add_argument("--native-libs", help="List of top-level native libs.")
    parser.add_argument("--readelf-path",
                        help="Path to the toolchain's readelf")

    # android_apk
    parser.add_argument("--apk-path")
    parser.add_argument("--incremental-apk-path")
    parser.add_argument("--incremental-install-script-path")

    parser.add_argument("--tested-apk-config")
    parser.add_argument("--proguard-enabled", action="store_true",
                        help="Whether proguard is enabled for this apk.")
    parser.add_argument("--proguard-info",
                        help="Path to the proguard .info output for this apk.")
    parser.add_argument("--has-alternative-locale-resource",
                        action="store_true",
                        help="Whether there is alternative-locale-resource in direct deps.")
    return parser


_dep_config_cache = dict()


def get_dep_config(path):
    if path not in _dep_config_cache:
        _dep_config_cache[path] = build_utils.read_json(path)["deps_info"]
    return _dep_config_cache[path]


def _filter_unwanted_deps_configs(config_type, configs):
    """去掉错误的依赖类型
    """
    configs = [c for c in configs if c not in _ROOT_TYPES]
    # if config_type in _RESOURCES_TYPES:
    #     configs = [c for c in configs
    #                if get_dep_config(c)["type"] in _RESOURCES_TYPES]
    return configs


def get_all_deps_configs_in_order(deps_configs):
    """得到所有的依赖项
    """

    def get_deps(dep):
        return set(get_dep_config(dep)["deps_configs"])

    return build_utils.get_sorted_transitive_dependencies(deps_configs, get_deps)


def deps_of_type(wanted_type, configs):
    """过滤自己想要的类型
    """
    return [c for c in configs if c["type"] == wanted_type]


def resolve_groups(configs):
    """
    :param configs:
    """
    while True:
        groups = deps_of_type("group", configs)
        if not groups:
            break
        for config in groups:
            index = configs.index(config)
            configs[index:index + 1] = [get_dep_config(c)
                                        for c in config["deps_configs"]]
    return configs


def as_interface_jar(path):
    return path[:-3] + "interface.jar"


def main():
    parser = create_parser()
    args = parser.parse_args()

    requires_options_map = {
        "java_library": ["build_config", "jar_path", "srczip_path"],
        "java_binary": ["build_config", "jar_path"],
        "android_resources": ["build_config", "resources_zip"],
        "android_assets": ["build_config"],
        "android_native_libraries": ["build_config", "native_libs"],
        "android_apk": ["build_config", "apk_path", "dex_path"],
        "deps_dex": ["build_config", "dex_path"],
        "group": ["build_config"]
    }

    # 检查必须的选项
    requires_options = requires_options_map.get(args.type)
    if requires_options is None:
        raise Exception("Unknown type: %s" % args.type)

    build_utils.check_options(args, parser, required=requires_options)

    if type == "java_library":
        if args.supports_android and not args.dex_path:
            raise Exception(
                "--dex-path must be set if --supports-android is enabled")
        if args.requires_android and not args.supports_android:
            raise Exception(
                "--supports-android must be set is --requires-android is enabled")
        pass

    if args.possible_deps_configs is None:
        args.possible_deps_configs = []

    possible_deps_config_paths = args.possible_deps_configs

    allow_unknown_deps = (args.type in (
        "android_apk", "android_resources", "android_assets", "android_native_libraries"))
    unknown_deps = [
        c for c in possible_deps_config_paths if not os.path.exists(c)]
    if not allow_unknown_deps and unknown_deps:
        raise Exception("Unknown deps: %s" % str(unknown_deps))

    # 直接依赖
    direct_deps_config_paths = [c for c in possible_deps_config_paths
                                if c not in unknown_deps]
    direct_deps_config_paths = _filter_unwanted_deps_configs(args.type,
                                                             direct_deps_config_paths)
    deps = Deps(direct_deps_config_paths)
    all_inputs = deps.all_config_paths() + build_utils.get_python_dependencies()

    if args.has_alternative_locale_resource:
        # 移除其他的资源
        alternative = [c["path"] for c in deps.direct("android_resources")
                       if c["is_locale_resource"]]
        if len(alternative) != 1:
            raise Exception()
        unwanted = [c["path"] for c in deps.all("android_resources")
                    if c["is_locale_resource"]]
        for path in unwanted:
            if path != alternative[0]:
                deps.remove_non_direct_dep(unwanted)
        pass

    config = {
        "deps_info": {
            "name": os.path.basename(args.build_config),
            "path": args.build_config,
            "type": args.type,
            "deps_configs": direct_deps_config_paths
        }
    }
    deps_info = config["deps_info"]

    direct_library_deps = deps.direct("java_library")
    all_library_deps = deps.all("java_library")
    direct_resources_deps = deps.direct("android_resources")
    all_resources_deps = deps.all("android_resources")
    all_resources_deps.reverse()
    all_native_libraries_deps = deps.all("android_native_libraries")

    if args.type == "android_apk" and args.tested_apk_config:
        tested_apk_deps = Deps([args.tested_apk_config])
        tested_apk_resource_deps = tested_apk_deps.all("android_resources")
        direct_resources_deps = [d for d in direct_resources_deps
                                 if d not in tested_apk_resource_deps]
        all_resources_deps = [d for d in all_resources_deps
                              if d not in tested_apk_resource_deps]
        pass

    if args.type in ("java_library", "java_binary") and not args.bypass_platform_checks:
        deps_info["requires_android"] = args.requires_android
        deps_info["supports_android"] = args.supports_android

        deps_requires_android = [d["name"] for d in all_library_deps
                                 if d["requires_android"]]
        deps_not_supports_android = [d["name"] for d in all_library_deps
                                     if not d["supports_android"]]
        if not args.requires_android and deps_requires_android:
            raise Exception("Some deps requires building for the android platform: %s"
                            % " ".join(deps_requires_android))
        if args.supports_android and deps_not_supports_android:
            raise Exception("Some deps not supports running on the android platform: %s"
                            % " ".join(deps_not_supports_android))
        pass

    if args.type in ("java_library", "java_binary", "android_apk"):
        javac_classpath = [c["jar_path"] for c in direct_library_deps]
        java_full_classpath = [c["jar_path"] for c in all_library_deps]
        config["resources_deps"] = [c["path"] for c in all_resources_deps]
        deps_info["jar_path"] = args.jar_path
        deps_info["srczip_path"] = args.srczip_path
        if args.type == "android_apk" or args.supports_android:
            deps_info["dex_path"] = args.dex_path
        if args.type == "android_apk":
            deps_info["apk_path"] = args.apk_path
            deps_info["incremental_apk_path"] = args.incremental_apk_path
            deps_info["incremental_install_script_path"] = args.incremental_install_script_path

        config["javac"] = {}
        pass

    if args.type in ("java_binary", "java_library"):
        config["javac"]["srcjars"] = [c["srcjar"]
                                      for c in direct_resources_deps]
    if args.type == "android_apk":
        config["javac"]["srcjars"] = []

    if args.type == "android_assets":
        all_assets_sources = []
        if args.asset_renaming_sources:
            all_assets_sources.extend(args.asset_renaming_sources)
        if args.asset_sources:
            all_assets_sources.extend(args.asset_sources)
        deps_info["assets"] = {
            "sources": all_assets_sources,
        }

        all_assets_outputs = []
        if args.asset_renaming_destinations:
            all_assets_outputs.extend(args.asset_renaming_destinations)
        deps_info["assets"]["outputs"] = all_assets_outputs
        deps_info["assets"]["disable_compression"] = args.disable_asset_compression
        pass

    if args.type == "android_resources":
        deps_info["resources_zip"] = args.resources_zip
        deps_info["r_text"] = args.r_text
        deps_info["is_locale_resource"] = args.is_locale_resource
        if args.srcjar:
            deps_info["srcjar"] = args.srcjar
        if args.android_manifest:
            manifest = AndroidManifest(args.android_manifest)
            deps_info["package_name"] = manifest.get_package_name()
        if args.package_name:
            deps_info["package_name"] = args.package_name
        pass

    if args.type == "android_native_libraries":
        deps_info["native_libs"] = build_utils.parse_gyp_list(args.native_libs)
        pass

    if args.type in ("android_resources", "android_apk", "resources_rewriter"):
        config["resources"] = {}
        config["resources"]["dependency_zips"] = [d["resources_zip"]
                                                  for d in all_resources_deps]
        config["resources"]["extra_package_names"] = []
        config["resources"]["extra_r_text_files"] = []
        pass

    if args.type in ("android_apk", "android_resources", "resources_rewriter"):
        config["resources"]["extra_package_names"] = [c["package_name"] for c in all_resources_deps
                                                      if "package_name" in c]
        config["resources"]["extra_r_text_files"] = [c["r_text"] for c in all_resources_deps
                                                     if "r_text" in c]

    if args.type in ("android_apk", "deps_dex"):
        deps_dex_paths = [c["dex_path"] for c in all_library_deps]

    proguard_enabled = args.proguard_enabled
    if args.type == "android_apk":
        deps_info["proguard_enabled"] = proguard_enabled

    if proguard_enabled:
        deps_info["proguard_info"] = args.proguard_info
        config["proguard"] = {}
        proguard_config = config["proguard"]
        proguard_config["input_paths"] = [args.jar_path] + java_full_classpath

    if args.type in ("android_apk", "deps_dex"):
        config["final_dex"] = {}
        dex_config = config["final_dex"]
        dex_config["dependency_dex_files"] = deps_dex_paths
        pass

    if args.type in ("android_apk", "java_library", "java_binary"):
        config["javac"]["classpath"] = javac_classpath
        config["javac"]["interface_classpath"] = [as_interface_jar(path)
                                                  for path in javac_classpath]
        config["java"] = {
            "full_classpath": java_full_classpath
        }

    if args.type == "android_apk":
        dependency_jars = [c["jar_path"] for c in all_library_deps]
        all_interface_jars = [as_interface_jar(p)
                              for p in dependency_jars + [args.jar_path]]
        all_srczips = [c["srczip_path"] for c in all_library_deps]
        all_srczips.append(args.srczip_path)
        config["dist_jar"] = {
            "dependency_jars": dependency_jars,
            "all_interface_jars": all_interface_jars,
            "all_srczips": all_srczips,
        }

        manifest = AndroidManifest(args.android_manifest)
        deps_info["package_name"] = manifest.get_package_name()

        if not args.tested_apk_config and manifest.get_instrumentation():
            manifest.check_instrumentation(manifest.get_package_name())

        library_paths = []
        java_libraries_list_holder = [None]
        libraries = build_utils.parse_gyp_list(args.native_libs or '[]')
        for d in all_native_libraries_deps:
            libraries.extend(d["native_libs"])

        if libraries:
            all_deps = [path for path in libraries]
            library_paths = [path for path in all_deps]
            java_libraries_list_holder[0] = ("{%s}" % ",".join(
                ['"%s"' % s[3:-3] for s in library_paths]))
            pass

        all_inputs.extend(library_paths)
        config["native"] = {
            "libraries": library_paths,
            "java_libraries_list": java_libraries_list_holder[0]
        }

        config["assets"], config["uncompressed_assets"] = _merge_assets(
            deps.all("android_assets"))
        pass

    build_utils.write_json(config, args.build_config)
    if args.depfile:
        build_utils.write_dep_file(args.depfile, all_inputs)
    pass


if __name__ == "__main__":
    main()
    pass
