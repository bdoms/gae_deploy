import argparse
import base64
import datetime
import hashlib
import os
import pprint
import re
import sys
import time
from subprocess import call

from __init__ import STATIC_MAP, STATIC_FILE
from lib import git, slack, trello

# add library folders to enable imports from there
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

CSSMIN_DIR = os.path.join(CURRENT_DIR, "lib", "cssmin", "src")
sys.path.append(CSSMIN_DIR)
from cssmin import cssmin

JSMIN_DIR = os.path.join(CURRENT_DIR, "lib", "jsmin")
sys.path.append(JSMIN_DIR)
from jsmin import jsmin

CONFIGS = ["app", "cron", "dos", "dispatch", "index", "queue"]


def minify(folders, symbolic=None):
    extensions = [".js", ".css"]
    new_static_map = {}
    new_symbolic_map = {}
    new_integrity_map = {}
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

                    minified = None
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

                    # calculate integrity and record it
                    # see https://developer.mozilla.org/en-US/docs/Web/Security/Subresource_Integrity
                    if minified is None:
                        min_file = open(min_filename)
                        minified = min_file.read()
                        min_file.close()

                    integrity = base64.b64encode(hashlib.sha512(minified.encode("utf-8")).digest())
                    new_integrity_map[rel_filename] = "sha512-" + integrity.decode("utf-8")

    # generate a file with a dictionary of all the original file names to their new minified counterparts
    # make a timestamp for properly caching static assets we can't find here (images, etc.)
    f = open(os.path.join(CURRENT_DIR, STATIC_FILE), "w")

    f.write("TIMESTAMP = '" + str(int(time.time())) + "'\n")
    f.write("STATIC_MAP = " + pprint.pformat(new_static_map, width=1) + "\n")
    f.write("SYMBOLIC_MAP = " + pprint.pformat(new_symbolic_map, width=1) + "\n")
    f.write("INTEGRITY_MAP = " + pprint.pformat(new_integrity_map, width=1) + "\n")

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


def deploy(config, branch=None, services=None, templates_only=False):
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

        update_args = ["gcloud", "app", "deploy"]

        # see if this branch should be promoted - must explicitly promote to override default version
        if branch_vars and "_promote" in branch_vars:
            update_args.append("--promote")
            print("Deploy: Version is being promoted to default.")
        else:
            update_args.append("--no-promote")

        # see if a specific version is specified
        version = None
        if branch_vars and "_version" in branch_vars:
            version = branch_vars["_version"]
            if version == "_branch":
                # this is a special case where we replace it with the branch name
                version = branch
            update_args.extend(["--version", str(version)])
        else:
            print("Deploy: Version not specified. Using default version.")

        project = config.get("project", None)
        if project:
            update_args.extend(["--project", project])
        elif branch_vars and "_project" in branch_vars:
            project = branch_vars["_project"]
            if project == "_branch":
                # this is a special case where we replace it with the branch name
                version = branch
            update_args.extend(["--project", project])
        else:
            print("Deploy: Project not specified. Using default project.")

        if not services:
            # services not on command line, so get from the config
            services = config.get("services", [])

        update_args.extend([service + ".yaml" for service in services])

        # update the default module, as well as indexes, cron, task queue, dispatch, etc.
        # these must be included explicitly now with the change to GCS
        for service in CONFIGS:
            f = service + ".yaml"
            if f not in update_args and os.path.exists(f):
                update_args.append(f)

        # finish with the actual deploy to the servers
        call(update_args)


def deployBranches(config, branches, services=None, templates_only=False):
    if branches:
        for branch in branches:
            if git.currentBranch() != branch:
                git.checkout(branch)
            deploy(config, branch=branch, services=services, templates_only=templates_only)
    else:
        deploy(config, services=services, templates_only=templates_only)


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

    moved_cards = []
    for branch in branches:
        # only talk to Trello if one of the specified branches is being pushed
        # e.g. take action on master but not on a feature branch
        if branch in config['branches']:
            client = trello.Trello(config['api_key'], config['oauth_token'], config['board_id'])
            now = datetime.datetime.now()
            release_name = now.strftime(config['release_name'])
            release_list = client.createList(release_name, config['list_id'])
            moved_cards = client.moveCards(config['list_id'], release_list['id'])

    return moved_cards


def notifySlack(config, branches, trello_cards=None):
    # allow for dynamic python expressions here so variables can be pulled from somewhere else
    for key in config:
        try:
            config[key] = eval(config[key])
        except:
            pass

    branch_names = config.get('names', {})
    branch_urls = config.get('urls', {})
    default_url = config.get('url')

    for branch in branches:
        # only talk to Slack if one of the specified branches is being pushed
        # e.g. take action on master but not on a feature branch
        if branch in config['branches']:
            username = git.currentUser()
            branch_name = branch_names.get(branch)
            text = 'New release'
            if branch_name:
                text += ' of ' + branch_name
            text += ' deployed by ' + username

            attachments = []
            if trello_cards:
                text += ':'
                for card in trello_cards:
                    fallback = '#' + str(card['idShort']) + ' - ' + card['name']
                    card_text = '<' + card['url'] + '|#' + str(card['idShort']) + '> ' + card['name']
                    attachment = {'fallback': fallback, 'text': card_text}
                    # just pick the first label to color since Slack only supports one
                    if 'labels' in card:
                        for label in card['labels']:
                            attachment['color'] = trello.COLORS.get(label['color'], '')
                            break
                    attachments.append(attachment)

            branch_url = branch_urls.get(branch, default_url)
            if branch_url:
                client = slack.Slack(branch_url)
                client.postMessage(text, attachments=attachments)
            else:
                print('Deploy: Could not find valid Slack URL for branch "' + branch + '"')


if __name__ == "__main__":
    # parse command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("config", help="path to YAML configuration file")
    parser.add_argument("-g", "--gae", metavar="dir", help="path to Google App Engine SDK directory")
    parser.add_argument("-s", "--services", nargs='+', metavar="services", help="deploy specific service(s)")
    parser.add_argument("-n", "--notify", action="store_true", help="skip deploying but notify third parties as if a deploy occurred")
    parser.add_argument("-t", "--templates", action="store_true", help="write files from templates for the current branch")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-b", "--branch", metavar="branch", help="deploy a single git branch")
    group.add_argument("-l", "--list", metavar="list", help="deploy a list of multiple git branches")
    args = parser.parse_args()

    # check installed first
    try:
        import yaml
    except ImportError:
        yaml = None

    if not yaml:
        # add GAE path if it exists
        if args.gae:
            sys.path.append(args.gae)

        # add third party libraries to the path, including YAML
        try:
            import dev_appserver
            dev_appserver.fix_sys_path()
        except ImportError:
            pass

        # try again
        try:
            import yaml
        except ImportError:
            yaml = None

    if not yaml:
        sys.exit("Error: Could not import YAML. Make sure it is installed, GAE is in the PYTHONPATH, or the supplied path is correct.")

    with open(args.config) as f:
        data = yaml.load(f)

    branches = determineBranches(data, args)

    if args.notify:
        print("Skipping deployment and notifying third parties.")
    else:
        deployBranches(data, branches, services=args.services, templates_only=args.templates)

    if not args.templates:
        cards = None
        if 'trello' in data:
            cards = notifyTrello(data['trello'], branches)

        if 'slack' in data:
            notifySlack(data['slack'], branches, trello_cards=cards)
