# -*- coding: utf-8 -*-

import codecs
import argparse
import os
import sys
import jinja2

from android import build_utils
from android import host_paths


class RecordingFileSystemLoader(jinja2.FileSystemLoader):
    """A FileSystemLoader that stores a list of loaded templates.
    """

    def __init__(self, searchpath):
        jinja2.FileSystemLoader.__init__(self, searchpath)
        self.loaded_templates = set()
        pass

    def get_source(self, environment, template):
        contents, filename, uptodate = jinja2.FileSystemLoader.get_source(
            self, environment, template)
        self.loaded_templates.add(os.path.relpath(filename))
        return contents, filename, uptodate

    def get_loaded_templates(self):
        return list(self.loaded_templates)


def process_file(env, input_filename, loader_base_dir, output_filename,
                 variables):
    """
    env:
    input_filename:输入文件
    """
    input_rel_path = os.path.relpath(input_filename, loader_base_dir)
    template = env.get_template(input_rel_path.replace("\\", "/"))
    output = template.render(variables)
    with codecs.open(output_filename, 'w', 'utf-8') as output_file:
        output_file.write(output)
    pass


def process_files(env, input_filenames, loader_base_dir, inputs_base_dir,
                  outputs_zip, variables):
    with build_utils.temp_dir() as temp_dir:
        for input_filename in input_filenames:
            relpath = os.path.relpath(os.path.abspath(input_filename),
                                      os.path.abspath(inputs_base_dir))
            if relpath.startswith(os.pardir):
                raise Exception('input file %s is not contained in inputs base dir %s'
                                % (input_filename, inputs_base_dir))

            output_filename = os.path.join(temp_dir, relpath)
            parent_dir = os.path.dirname(output_filename)
            build_utils.make_directory(parent_dir)
            process_file(env, input_filename, loader_base_dir, output_filename,
                         variables)

        build_utils.zip_dir(outputs_zip, temp_dir)
    pass


def create_parser():
    parser = argparse.ArgumentParser(prog="jinja_template.py")
    build_utils.add_depfile_option(parser)
    parser.add_argument('--inputs',
                        help='The template files to process.')
    parser.add_argument('--output',
                        help='The output file to generate. Valid '
                        'only if there is a single input.')
    parser.add_argument('--outputs-zip',
                        help='A zip file containing the processed '
                        'templates. Required if there are multiple inputs.')
    parser.add_argument('--inputs-base-dir',
                        help='A common ancestor directory of '
                        'the inputs. Each output\'s path in the output zip will '
                        'match the relative path from INPUTS_BASE_DIR to the '
                        'input. Required if --output-zip is given.')
    parser.add_argument('--loader-base-dir', help='Base path used by the template '
                        'loader. Must be a common ancestor directory of '
                        'the inputs. Defaults to DIR_SOURCE_ROOT.',
                        default=host_paths.DIR_SOURCE_ROOT)
    parser.add_argument('--variables',
                        default='',
                        help='Variables to be made available in the '
                        'template processing environment, as a GYP list (e.g. '
                        '--variables "channel=beta mstone=39")')
    return parser


def main():
    parser = create_parser()
    args = parser.parse_args()

    build_utils.check_options(args, parser, required=['inputs'])
    inputs = build_utils.parse_gyp_list(args.inputs)

    if (args.output is None) == (args.outputs_zip is None):
        args.error('Exactly one of --output and --output-zip must be given')
    if args.output and len(inputs) != 1:
        args.error('--output cannot be used with multiple inputs')
    if args.outputs_zip and not args.inputs_base_dir:
        args.error(
            '--inputs-base-dir must be given when --output-zip is used')

    variables = {}
    for v in build_utils.parse_gyp_list(args.variables):
        if '=' not in v:
            args.error('--variables argument must contain "=": ' + v)
        name, _, value = v.partition('=')
        variables[name] = value

    loader = RecordingFileSystemLoader(args.loader_base_dir)
    env = jinja2.Environment(loader=loader,
                             undefined=jinja2.StrictUndefined,
                             line_comment_prefix='##')
    if args.output:
        # 只处理单个文件
        process_file(env,
                     inputs[0],
                     args.loader_base_dir,
                     args.output,
                     variables)
    else:
        # 处理多个文件
        process_files(env,
                      inputs,
                      args.loader_base_dir,
                      args.inputs_base_dir,
                      args.outputs_zip, variables)

    if args.depfile:
        deps = loader.get_loaded_templates() + build_utils.get_python_dependencies()
        build_utils.write_dep_file(args.depfile, deps)
    pass


if __name__ == '__main__':
    main()
    pass
