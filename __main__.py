
import os
import sys
import time

from jsmin import jsmin
from cssmin import cssmin

from __init__ import STATIC_MAP, STATIC_FILE

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
EXTENSIONS = [".js", ".css"]


def minify(folders):
    # relative dir is what folder the files are relative to for the purpose of turning them into URLs
    new_static_map = {}
    cwd = os.getcwd()

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
                # look for files with .js or .css extensions
                if ext in EXTENSIONS:
                    # inspect filename to see if this could have been minified by other sources
                    # for now, this means if there are any numbers or "min" in the filename
                    digits = [char for char in fname if char.isdigit()]
                    if digits or ".min" in fname or "-min" in fname:
                        continue

                    # find the last modified date
                    filename = os.path.join(root, name)
                    last_modified = int(os.path.getmtime(filename))

                    # add .min so it can easily be added to a gitignore file (*.min.js and *.min.css)
                    min_name = "".join([fname, "-", str(last_modified), ".min", ext])
                    min_filename = os.path.join(root, min_name)

                    # get relative filenames for use in URLs
                    rel_filename = prefix + "/" + os.path.relpath(filename, relative_path).replace(os.sep, "/")
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
    f.write("}")
    f.close()


if __name__ == "__main__":
    # parse command line arguments
    config = None
    for arg in sys.argv[1:]:
        if "=" in arg:
            key, value = arg.split("=")
            if key == "gae":
                yaml_dir = os.path.join(value, 'lib', 'yaml-3.10')
                sys.path.append(yaml_dir)
            elif key == "config":
                config = value

    try:
        import yaml
    except ImportError:
        print "Could not import YAML. Make sure it is either installed or the supplied path to GAE is correct."
        sys.exit()

    if not config:
        print "You must supply a configuration file."
        sys.exit()

    f = open(config, "r")
    data = yaml.load(f)
    f.close()

    if "static_dirs" not in data or len(data["static_dirs"]) < 1:
        print "You must supply at least one folder to look in as an argument."
        sys.exit()

    # run the minifier
    minify(data["static_dirs"])

    # now do the actual deploy to the servers
    from subprocess import call
    call(["appcfg.py", "update", "."])
