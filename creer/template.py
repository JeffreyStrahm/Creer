from mako.template import Template, exceptions
from mako.lookup import TemplateLookup
from time import gmtime, strftime
from creer.utilities import uncapitalize, camel_case_to_underscore, list_dirs, copy_dict
import creer.merge as merge
import creer.githash as githash
import os
import json

templates_folder = "_templates"
template_header = ("Generated by Creer at " + strftime("%I:%M%p on %B %d, %Y UTC", gmtime()) + ", git hash: '" + githash.get() + "'").replace("\n", "").replace("\n", "") # yuk

def build_all(prototype, input, output, clean=False):
    generated_files = []
    game = prototype['game']
    game_name = game['name']
    game_objects = prototype['game_objects']
    ai = prototype['ai']

    for input_directory in input:
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
                    if d == templates_folder:
                        if i > 0:
                            output_path = os.path.join(dirs[i-1], *dirs[i+1:])
                        else:
                            output_path = os.path.join(*dirs[i+1:])
                        break

                print("templating", output_path)
                with open(filepath, "r") as read_file:
                    lookup = TemplateLookup(directories=[os.path.dirname(filepath)])
                    filecontents_template = Template(read_file.read(), lookup=lookup)

                filepath_template = Template(output_path, lookup=lookup)

                base_parameters = {
                    'game': game,
                    'game_name': game_name,
                    'game_objs': game_objects,
                    'ai': ai,
                    'uncapitalize': uncapitalize,
                    'camel_case_to_underscore': camel_case_to_underscore,
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
                        system_path = os.path.join(output, templated_path)

                        merge_data = {}
                        if not clean and os.path.isfile(system_path): # then we need to have merge data in the existing file with the new one we would be creating
                            with open(system_path) as f:
                                content = f.readlines()
                                merge_data = merge.generate_data(content)

                        print("  -> generating", system_path)

                        def this_merge(pre_comment, key, alt):
                            return merge.with_data(merge_data, pre_comment, key, alt)
                        p['merge'] = this_merge

                        
                        generated_files.append({
                            'contents': filecontents_template.render(**p),
                            'path': system_path,
                        })
                    except:
                        raise Exception(exceptions.text_error_template().render())

    return generated_files