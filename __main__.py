import argparse
import os
import sys
import time

from __init__ import STATIC_MAP, STATIC_FILE

# add library folders to enable imports from there
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

CSSMIN_DIR = os.path.join(CURRENT_DIR, "lib", "css", "src")
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
                            if os.path.exists(full_path):
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


if __name__ == "__main__":
    # parse command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=file, help="path to YAML configuration file")
    parser.add_argument("--gae", metavar="dir", help="path to Google App Engine SDK directory")
    args = parser.parse_args()

    if args.gae:
        yaml_dir = os.path.join(args.gae, 'lib', 'yaml-3.10')
        sys.path.append(yaml_dir)

    try:
        import yaml
    except ImportError:
        print "Could not import YAML. Make sure it is either installed or the supplied path to GAE is correct."
        sys.exit()

    data = yaml.load(args.config)
    args.config.close()

    if "static_dirs" not in data or len(data["static_dirs"]) < 1:
        print "You must supply at least one folder to look in as an argument."
        sys.exit()

    # run the minifier
    minify(data["static_dirs"], symbolic=data.get("symbolic_paths", []))

    # now do the actual deploy to the servers
    from subprocess import call
    call(["appcfg.py", "update", "."])
