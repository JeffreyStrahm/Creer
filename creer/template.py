from mako.template import Template, exceptions
from mako.lookup import TemplateLookup
from binaryornot.check import is_binary
from time import gmtime, strftime
from creer.utilities import uncapitalize, camel_case_to_underscore, camel_case_to_hyphenate, list_dirs, copy_dict, sort_dict_keys, upcase_first, lowercase_first, is_primitive_type
import creer.merge as merge
import creer.githash as githash
import os
import json

templates_folder = "_creer"
template_header = ("Generated by Creer at " + strftime("%I:%M%p on %B %d, %Y UTC", gmtime()) + ", git hash: '" + githash.get() + "'").replace("\n", "").replace("\n", "") # yuk

def build_all(prototype, inputs, output, do_merge=False, tagless=False):
    generated_files = []
    game = prototype['game']
    game_name = game['name']
    game_objects = prototype['game_objects']
    ai = prototype['ai']

    if not inputs:
        inputs = default_input()

    if not output:
        output = "../" if do_merge else "./output"

    for input_directory in inputs:
        full_path = os.path.join(input_directory, templates_folder)
        for root, dirnames, filenames in os.walk(full_path):
            for filename in filenames:
                extensionless, extension = os.path.splitext(filename)

                if extension == '.noCreer': # noCreer files are not to be templated
                    continue

                filepath = os.path.join(root, filename)

                dirs = list_dirs(filepath)
                output_path = ""
                for i, d in enumerate(dirs):
                    if d == templates_folder: # slice it off
                        if output:
                            if i > 0:
                                output_path = os.path.join(dirs[i-1], *dirs[i+1:])
                            else:
                                output_path = os.path.join(*dirs[i+1:])
                        else:
                            output_dirs = list(dirs)
                            output_dirs.pop(i)
                            output_path = os.path.join(*output_dirs)
                        break

                binary = is_binary(filepath) # don't template binary files, assume they are needed to work (like images)

                if binary:
                    print("binary file", output_path)
                else:
                    print("templating", output_path)
                    with open(filepath, "r") as read_file:
                        lookup = TemplateLookup(directories=[os.path.dirname(filepath)])
                        filecontents_template = Template(read_file.read(), lookup=lookup)

                filepath_template = Template(output_path, lookup=lookup)

                base_parameters = {
                    'game': game,
                    'game_name': game_name,
                    'game_objs': game_objects,
                    'game_obj_names': sort_dict_keys(game_objects),
                    'ai': ai,
                    'uncapitalize': uncapitalize,
                    'camel_case_to_underscore': camel_case_to_underscore, # depreciated
                    'underscore': camel_case_to_underscore,
                    'hyphenate': camel_case_to_hyphenate,
                    'sort_dict_keys': sort_dict_keys,
                    'upcase_first': upcase_first,
                    'lowercase_first': lowercase_first,
                    'is_primitive_type': is_primitive_type,
                    'header': template_header,
                    'json': json,
                    'shared': {},
                }
                parameters = []

                if 'obj_key' in extensionless: # then we are templating for all the game + game objects
                    parameters.append(copy_dict(base_parameters, {
                        'obj_key': "Game",
                        'obj': game,
                    }))

                    for obj_key, obj in game_objects.items():
                        parameters.append(copy_dict(base_parameters, {
                            'obj_key': obj_key,
                            'obj': obj
                        }))
                else:
                    parameters.append(base_parameters)

                for p in parameters:
                    try:
                        templated_path = filepath_template.render(**p)
                        system_path = os.path.join(output, templated_path) if output else templated_path

                        if binary:
                            # copy the file, don't actually template it
                            print("  -> copying", system_path)
                            generated_files.append({
                                'copy-from': filepath,
                                'copy-dest': system_path
                            })
                            continue

                        merge_data = {}
                        if do_merge and os.path.isfile(system_path): # then we need to have merge data in the existing file with the new one we would be creating
                            with open(system_path) as f:
                                content = f.readlines()
                                merge_data = merge.generate_data(content)

                        print("  -> generating", system_path)

                        def this_merge(pre_comment, key, alt, optional=False, help=True):
                            return merge.with_data(merge_data, pre_comment, key, alt,
                                optional=optional,
                                add_tags=(not tagless),
                                help=help,
                            )
                        p['merge'] = this_merge

                        contents = filecontents_template.render(**p)
                        endl = "\r\n" if "\r\n" in contents else "\n"
                        generated_files.append({
                            'contents': contents.rstrip() + endl,
                            'path': system_path,
                        })
                    except:
                        raise Exception(exceptions.text_error_template().render())

    return generated_files


def default_input():
    defaulted = []
    for name in os.listdir(".."):
        path = "../" + name
        if os.path.isdir(path) and os.path.isdir(path + "/" + templates_folder):
            defaulted.append(path)
    return defaulted
