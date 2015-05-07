import argparse
import datetime
import os
import re
import sys
import time
from subprocess import call

from __init__ import STATIC_MAP, STATIC_FILE
import git
from lib import trello

# add library folders to enable imports from there
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

CSSMIN_DIR = os.path.join(CURRENT_DIR, "lib", "cssmin", "src")
sys.path.append(CSSMIN_DIR)
from cssmin import cssmin

JSMIN_DIR = os.path.join(CURRENT_DIR, "lib", "jsmin")
sys.path.append(JSMIN_DIR)
from jsmin import jsmin


def minify(folders, symbolic=None):
    extensions = [".js", ".css"]
    new_static_map = {}
    new_symbolic_map = {}
    cwd = os.getcwd()

    symbolic_paths = {}
    if symbolic:
        for symbol in symbolic:
            symbolic_paths[symbol["path"]] = symbol["link"]

    for folder in folders:
        relative_path = os.path.join(cwd, folder.get("rel", ""))
        prefix = folder.get("prefix", "")

        path = folder["path"]
        if not os.path.isabs(path):
            path = os.path.join(cwd, path)

        avoid = []
        for root, dirs, files in os.walk(path):
            # skip folder if it's a source folder
            if root.endswith("src") or root.endswith("plugins") or root.endswith(".git"):
                avoid.append(root)
                continue
            if [p for p in avoid if p in root]:
                continue

            for name in files:
                fname, ext = os.path.splitext(name)

                filename = os.path.join(root, name)
                rel_filename = prefix + "/" + os.path.relpath(filename, relative_path).replace(os.sep, "/")

                if rel_filename in symbolic_paths:
                    new_symbolic_map[rel_filename] = symbolic_paths[rel_filename]
                    continue

                # look for files with .js or .css extensions
                elif ext in extensions:
                    # inspect filename to see if this could have been minified by other sources
                    # for now, this means if there are any numbers or "min" in the filename
                    digits = [char for char in fname if char.isdigit()]
                    if digits or ".min" in fname or "-min" in fname:
                        continue

                    # find the last modified date
                    last_modified = int(os.path.getmtime(filename))

                    # add .min so it can easily be added to a gitignore file (*.min.js and *.min.css)
                    min_name = "".join([fname, "-", str(last_modified), ".min", ext])
                    min_filename = os.path.join(root, min_name)

                    # get relative filenames for use in URLs
                    rel_min_filename = prefix + "/" + os.path.relpath(min_filename, relative_path).replace(os.sep, "/")

                    if not os.path.exists(min_filename):
                        f = open(filename)
                        data = f.read()
                        f.close()
                        if ext == ".js":
                            minified = jsmin(data)
                        elif ext == ".css":
                            minified = cssmin(data)

                        min_file = open(min_filename, "w")
                        min_file.write(minified)
                        min_file.close()

                        # check to see if an older minified file exists
                        if rel_filename in STATIC_MAP:
                            # it does, delete it
                            rel_old_min = STATIC_MAP[rel_filename]
                            full_path = os.path.join(relative_path, rel_old_min[1:]) # remove front slash
                            # don't remove if this is the same file we just wrote
                            if full_path != min_filename and os.path.exists(full_path):
                                os.remove(full_path)

                    # add to the dict to record this, but first we need these to be relative
                    new_static_map[rel_filename] = rel_min_filename

    # generate a file with a dictionary of all the original file names to their new minified counterparts
    # make a timestamp for properly caching static assets we can't find here (images, etc.)
    f = open(os.path.join(CURRENT_DIR, STATIC_FILE), "w")
    f.write("TIMESTAMP = '" + str(int(time.time())) + "'\n")
    f.write("STATIC_MAP = {\n")
    last = len(new_static_map) - 1
    for i, key in enumerate(new_static_map):
        f.write("'" + key + "': '" + new_static_map[key] + "'")
        if i != last:
            f.write(",")
        f.write("\n")
    f.write("}\n")
    f.write("SYMBOLIC_MAP = {\n")
    if new_symbolic_map:
        last = len(new_symbolic_map) - 1
        for i, key in enumerate(new_symbolic_map):
            f.write("'" + key + "': '" + new_symbolic_map[key] + "'")
            if i != last:
                f.write(",")
            f.write("\n")
    f.write("}\n")
    f.close()


def writeFileFromTemplate(infile, outfile, variables, branch):
    f = open(infile, "r")
    content = f.read()
    f.close()

    matches = re.findall("\$\{(.*?)\}", content)
    for match in matches:
        # this will generate a key error if the variable is undefined, which we want to happen
        value = variables[match]
        if value == "_branch":
            # this is a special case where we replace it with the branch name
            value = branch
        # do a global replace for this
        content = content.replace("${" + match + "}", value)

    # actually write the file
    f = open(outfile, "w")
    f.write(content)
    f.close()


def writeFilesFromTemplates(branches_config, branch_vars, branch):
    
    if "files" in branches_config:
        files = branches_config["files"]

        for f in files:
            writeFileFromTemplate(f["input"], f["output"], branch_vars, branch)


def deploy(config, branch=None, templates_only=False, oauth2=False):
    
    branch_vars = None
    branches_config = config.get("branches", None)
    if branch and branches_config and "variables" in branches_config:
        variables = branches_config["variables"]

        branch_vars = variables.get(branch, None)
        if not branch_vars:
            default = branches_config.get("default", None)
            if default and default in variables:
                branch_vars = variables[default]

        if not branch_vars:
            raise Exception("Error: Could not find data for branch '%s' and no default was specified." % branch)

        writeFilesFromTemplates(branches_config, branch_vars, branch)

    if not templates_only:
        # run the minifier if we need to
        if "static_dirs" in config and len(config["static_dirs"]) > 0:
            minify(config["static_dirs"], symbolic=config.get("symbolic_paths", []))

        # see if a specific version is specified
        version = None
        if branch_vars and "_version" in branch_vars:
            version = branch_vars["_version"]
            if version == "_branch":
                # this is a special case where we replace it with the branch name
                version = branch

        # finish with the actual deploy to the servers
        update_args = ["appcfg.py", "update", "."]
        if version:
            update_args.append("--version=" + str(version))
        if oauth2:
            update_args.append("--oauth2")
        call(update_args)


def deployBranches(config, branches, templates_only=False, oauth2=False):
    if branches:
        for branch in branches:
            if git.currentBranch() != branch:
                git.checkout(branch)
            deploy(config, branch=branch, templates_only=templates_only, oauth2=oauth2)
    else:
        deploy(config, templates_only=templates_only, oauth2=oauth2)


def determineBranches(config, args):
    branches = []
    if args.branch:
        branches = [args.branch]
    elif args.list:
        if "branch_lists" in config and args.list in config["branch_lists"]:
            branches = config["branch_lists"][args.list]
        else:
            sys.exit("Error: Could not find definition for list '%s' in configuration." % args.list)
    if not branches and git.installed() and git.isRepository():
        branches = [git.currentBranch()]
    return branches


def notifyTrello(config, branches):
    # allow for dynamic python expressions here so variables can be pulled from somewhere else
    for key in config:
        try:
            config[key] = eval(config[key])
        except:
            pass
    
    for branch in branches:
        # only talk to Trello if one of the specified branches is being pushed
        # e.g. take action on master but not on a feature branch
        if branch in config['branches']:
            client = trello.Trello(config['api_key'], config['oauth_token'], config['board_id'])
            now = datetime.datetime.now()
            release_name = now.strftime(config['release_name'])
            release_list = client.createList(release_name, config['list_id'])
            client.moveCards(config['list_id'], release_list['id'])


if __name__ == "__main__":
    # parse command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=file, help="path to YAML configuration file")
    parser.add_argument("-g", "--gae", metavar="dir", help="path to Google App Engine SDK directory")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-b", "--branch", metavar="branch", help="deploy a single git branch")
    group.add_argument("-l", "--list", metavar="list", help="deploy a list of multiple git branches")
    group.add_argument("-t", "--templates", action="store_true", help="write files from templates for the current branch")
    parser.add_argument("--oauth2", action="store_true", help="send the oauth2 flag to appcfg")
    args = parser.parse_args()

    if args.gae:
        sys.path.append(args.gae)
    
    try:
        import dev_appserver
        dev_appserver.fix_sys_path()
    except ImportError:
        pass

    try:
        import yaml
    except ImportError:
        sys.exit("Error: Could not import YAML. Make sure it is installed, GAE is in the PYTHONPATH, or the supplied path is correct.")

    data = yaml.load(args.config)
    args.config.close()

    branches = determineBranches(data, args)

    deployBranches(data, branches, templates_only=args.templates, oauth2=args.oauth2)

    if 'trello' in data:
        notifyTrello(data['trello'], branches)
