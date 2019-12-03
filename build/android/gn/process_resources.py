# -*- encoding: utf-8 -*-

import argparse
import os
import sys
import shutil
import codecs
import re
import collections
from string import Template
from jinja2 import Template

from android import build_utils

TextSymbolsEntry = collections.namedtuple(
    "RTextEntry",
    "java_type resource_type name value")


def create_resources_zip(resource_dirs, output_zip):
    """创建资源zip
    :param resource_dirs:
    :param output_zip:
    :return:
    """
    input_map = dict()
    for base_dir in resource_dirs:
        for root, _, filenames in os.walk(base_dir):
            parent_dir = os.path.relpath(root, base_dir)
            for name in filenames:
                archive_name = name
                if parent_dir != ".":
                    archive_name = os.path.join(parent_dir, name)
                    archive_name.replace("\\", "/")
                input_map[archive_name] = os.path.join(root, name)
    build_utils.do_zip(input_map.items(), output_zip)
    pass


def _parse_text_symbols_file(r_text_file):
    entries = []
    with open(r_text_file, mode="r", encoding="utf-8") as file_obj:
        for line in file_obj:
            match = re.match("(int(?:\\[\\])?) (\\w+) (\\w+) (.*)$", line)
            if not match:
                raise Exception("parse R.txt exception -> %s: %s" %
                                (r_text_file, line))
            entries.append(TextSymbolsEntry(*match.groups()))
    return entries


def _create_extra_r_java_file(package, resources_by_type, shared_resources):
    """Generates the contents of a R.java file."""
    template = Template("""/* AUTO-GENERATED FILE.  DO NOT MODIFY. */

package {{ package }};

public final class R {
    {% for resource_type in resources %}
    public static final class {{ resource_type }} {
        {% for e in resources[resource_type] %}
        {% if shared_resources %}
        public static {{ e.java_type }} {{ e.name }} = {{ e.value }};
        {% else %}
        public static final {{ e.java_type }} {{ e.name }} = {{ e.value }};
        {% endif %}
        {% endfor %}
    }
    {% endfor %}
}
""", trim_blocks=True, lstrip_blocks=True)

    return template.render(package=package,
                           resources=resources_by_type,
                           shared_resources=shared_resources)


def create_extra_r_java_files(r_dir, extra_packages, extra_r_text_files, include_all):
    """创建其他的R.java文件
    """
    if include_all:
        r_java_files = build_utils.find_in_directory(r_dir, "R.java")
        if len(r_java_files) != 1:
            raise Exception("Multiple R.java file are found: %s" %
                            str(r_java_files))
        r_java_file = r_java_files[0]
        r_java_content = codecs.open(r_java_file, mode="r",
                                     encoding="utf-8").read()

        for package in extra_packages:
            extra_r_java_file_dir = os.path.join(r_dir,
                                                 *package.split("."))
            build_utils.make_directory(extra_r_java_file_dir)
            extra_r_java_file = os.path.join(extra_r_java_file_dir, "R.java")
            extra_r_java_content = re.sub("package (.\\w)+;",
                                          "package %s;" % package,
                                          r_java_content)
            with open(extra_r_java_file, mode="w+", encoding="utf-8",
                      newline="\n") as file_obj:
                file_obj.write(extra_r_java_content)
                pass
        pass
    else:
        if len(extra_packages) != len(extra_r_text_files):
            raise Exception()

        r_text_file = os.path.join(r_dir, "R.txt")
        if not os.path.exists(r_text_file):
            return

        all_resources = {}
        for entry in _parse_text_symbols_file(r_text_file):
            all_resources[(entry.resource_type, entry.name)] = entry

        resources_by_package = collections.defaultdict(
            lambda: collections.defaultdict(list))

        for package, r_text_file in zip(extra_packages, extra_r_text_files):
            if not os.path.exists(r_text_file):
                continue
            if package in resources_by_package:
                raise Exception()
            resources_by_type = resources_by_package[package]

            for entry in _parse_text_symbols_file(r_text_file):
                resources_by_type[entry.resource_type].append(entry)
            pass

        for package in extra_packages:
            extra_r_java_dir = os.path.join(r_dir, *package.split("."))
            build_utils.make_directory(extra_r_java_dir)
            extra_r_java_file = os.path.join(extra_r_java_dir, "R.java")
            r_java_content = _create_extra_r_java_file(package,
                                                       resources_by_package[package],
                                                       False)
            with open(extra_r_java_file, mode="w+", encoding="utf-8") as file_obj:
                file_obj.write(r_java_content)
            pass
    pass


def create_parser():
    parser = argparse.ArgumentParser(prog="process_resources.py")
    parser.add_argument("--depfile")
    parser.add_argument("--android-sdk-jar",
                        help="The path to the android jar path")
    parser.add_argument("--aapt-path",
                        help="path to the Android aapt tool")
    parser.add_argument("--non-constant-id", action="store_true")

    parser.add_argument("--android-manifest", help="AndroidManifest.xml path")
    parser.add_argument("--custom-package", help="Java package for R.java")
    parser.add_argument("--shared-resources",
                        action="store_true",
                        help="Make a resource package that can be loaded by a different "
                        "application at runtime to access the package's resources.")
    parser.add_argument("--app-as-shared-lib", action="store_true",
                        help="Make a resource package that can be loaded as shared library.")

    parser.add_argument("--resource-dirs",
                        help="Directories containing resources of this target")
    parser.add_argument("--dependency-res-zips",
                        help="Resources from dependens.")

    parser.add_argument("--resource-zip-out",
                        help="Path for output zipped resources.")
    parser.add_argument("--R-dir",
                        help="Directory to hold generated R.java.")
    parser.add_argument("--srcjar-out",
                        help="Path to srcjar to contain generated R.java")
    parser.add_argument("--r-text-out",
                        help="Path to store the R.txt file generated by appt.")
    parser.add_argument("--proguard-file",
                        help="Path to proguard.txt generated file")

    parser.add_argument("--v14-skip",
                        action="store_true",
                        help="Do not generate nor verify v14 resources")
    parser.add_argument("--extra-res-packages",
                        help="Additional package names for to generate R.java files for")
    parser.add_argument("--extra-r-text-files",
                        help="For each additional package, the R.txt file should contain a "
                        "list of resources to be included in the R.java file in the format "
                        "generated by aapt.")
    parser.add_argument("--include-all-resources",
                        action="store_true",
                        help="Includes every resource ID every generated R.java files "
                        "(ignoring R.txt).")
    parser.add_argument("--all-resources-zip-out",
                        help="Path for output of all resources. This includes resources in "
                        "dependencies.")
    parser.add_argument("--base-dir", required=True)
    return parser


def parse_args(argv):
    argv = list(sys.argv[1:])
    argv = build_utils.expand_file_args(argv)
    parser = create_parser()
    args = parser.parse_args(argv)

    requires_options = ["android_sdk_jar",
                        "aapt_path",
                        "android_manifest",
                        "dependency_res_zips",
                        "resource_dirs",
                        "resource_zip_out"]
    build_utils.check_options(args, parser, required=requires_options)

    args.resource_dirs = build_utils.parse_gyp_list(args.resource_dirs)
    args.dependency_res_zips = build_utils.parse_gyp_list(
        args.dependency_res_zips)
    if args.extra_r_text_files:
        args.extra_r_text_files = build_utils.parse_gyp_list(
            args.extra_r_text_files)
    else:
        args.extra_r_text_files = []
    if args.extra_res_packages:
        args.extra_res_packages = build_utils.parse_gyp_list(
            args.extra_res_packages)
    else:
        args.extra_res_packages = []
    return args


def crunch_directory(aapt, input_dir, output_dir):
    """
    """
    crunch_commands = [aapt,
                       "crunch",
                       "-C", output_dir,
                       "-S", input_dir,
                       "--ignore-assets", build_utils.AAPT_IGNORE_PATTERN
                       ]
    build_utils.check_output(args=crunch_commands)
    pass


def combine_zips(zip_files, output_path):
    """合并总的资源文件
    """
    def path_transform(name, src_zip):
        return "%d/%s" % (zip_files.index(src_zip), name)
    build_utils.merge_zips(output_path,
                           zip_files,
                           path_transform=path_transform)


def _on_stale_md5(args):
    aapt = args.aapt_path
    base_dir = args.base_dir
    build_utils.make_directory(base_dir)
    build_utils.remove_subtree(base_dir)

    deps_dir = os.path.join(base_dir, "deps")
    build_utils.make_directory(deps_dir)
    v14_dir = os.path.join(base_dir, "v14")
    build_utils.make_directory(v14_dir)
    gen_dir = os.path.join(base_dir, "gen")
    build_utils.make_directory(gen_dir)

    input_resource_dirs = args.resource_dirs

    dep_files = args.dependency_res_zips
    dep_subdirs = []
    for z in dep_files:
        dep_subdir = os.path.join(deps_dir, os.path.basename(z))
        if os.path.exists(dep_subdir):
            raise Exception("%s already exists" % dep_subdir)
        build_utils.make_directory(dep_subdir)
        dep_subdirs.append(dep_subdir)
        build_utils.extract_all(z, dep_subdir)
        pass

    package_command = [
        aapt,
        "package",
        "-m",
        "-M", args.android_manifest,
        "--auto-add-overlay",
        "--no-version-vectors",
        "-I", args.android_sdk_jar,
        "--output-text-symbols", gen_dir,
        "-J", gen_dir,
        "--ignore-assets", build_utils.AAPT_IGNORE_PATTERN,
    ]

    for d in input_resource_dirs:
        package_command += ["-S", d]

    for d in dep_subdirs:
        package_command += ["-S", d]

    if args.non_constant_id:
        package_command.append("--non-constant-id")
    if args.custom_package:
        package_command += ["--custom-package", args.custom_package]
    if args.proguard_file:
        package_command += ["-G", args.proguard_file]
    if args.shared_resources:
        package_command += ["--shared-lib"]
    if args.app_as_shared_lib:
        package_command += ["--app-as-shared-lib"]

    build_utils.check_output(args=package_command)

    base_crunch_dir = os.path.join(base_dir, "crunch")
    build_utils.make_directory(base_crunch_dir)

    zip_resources_dirs = list(input_resource_dirs)

    for idx, input_resource_dir in enumerate(input_resource_dirs):
        crunch_dir = os.path.join(base_crunch_dir, str(idx))
        build_utils.make_directory(crunch_dir)
        crunch_directory(aapt, input_resource_dir, crunch_dir)
        zip_resources_dirs.append(crunch_dir)
        pass

    create_resources_zip(zip_resources_dirs, args.resource_zip_out)

    if args.all_resources_zip_out:
        combine_zips([args.resource_zip_out] + dep_files,
                     args.all_resources_zip_out)

    if args.extra_res_packages:
        create_extra_r_java_files(gen_dir,
                                  args.extra_res_packages,
                                  args.extra_r_text_files,
                                  False)
        pass

    if args.srcjar_out:
        build_utils.zip_dir(args.srcjar_out, gen_dir)
        pass

    if args.r_text_out:
        shutil.copyfile(os.path.join(gen_dir, "R.txt"), args.r_text_out)
        pass
    pass


def main(argv):
    args = parse_args(argv)
    # print(args)

    possible_output_paths = [
        args.resource_zip_out,
        args.r_text_out,
        args.srcjar_out,
        args.all_resources_zip_out,
    ]

    output_paths = [x for x in possible_output_paths if x]
    input_strings = args.extra_res_packages + [
        args.aapt_path,
        args.android_sdk_jar,
        args.custom_package,
        args.non_constant_id,
        args.v14_skip,
    ]
    input_paths = [args.android_manifest]
    input_paths.extend(args.dependency_res_zips)
    input_paths.extend([path for path in args.extra_r_text_files
                        if os.path.exists(path)])

    resource_names = []
    for resource_dir in args.resource_dirs:
        for resource_file in build_utils.find_in_directory(resource_dir, "*"):
            input_paths.append(resource_file)
            resource_names.append(os.path.relpath(resource_file, resource_dir))
            pass

    input_strings.extend(sorted(resource_names))
    build_utils.call_and_write_dep_file_if_stale(
        lambda: _on_stale_md5(args),
        args,
        input_paths=input_paths,
        input_strings=input_strings,
        output_paths=output_paths
    )
    pass


if __name__ == "__main__":
    main(sys.argv[1:])
    pass
