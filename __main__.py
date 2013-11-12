
import os
import sys
import time

from jsmin import jsmin
from cssmin import cssmin

from __init__ import STATIC_MAP, STATIC_FILE

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
EXTENSIONS = [".js", ".css"]


def minify(folders, relative_dirs=None):
    # relative dir is what folder the files are relative to for the purpose of turning them into URLs
    new_static_map = {}
    cwd = os.getcwd()

    if not relative_dirs:
        relative_dirs = [""] * len(folders)

    for i, folder in enumerate(folders):
        relative_path = os.path.join(cwd, relative_dirs[i])

        path = folder
        if not os.path.isabs(folder):
            path = os.path.join(cwd, folder)

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
                    rel_filename = "/" + os.path.relpath(filename, relative_path).replace(os.sep, "/")
                    rel_min_filename = "/" + os.path.relpath(min_filename, relative_path).replace(os.sep, "/")

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
    folders = []
    rel_dir = ""
    rel_dirs = None
    for arg in sys.argv[1:]:
        if "=" in arg:
            key, value = arg.split("=")
            if key == "rel":
                if "," in value:
                    rel_dirs = value.split(",")
                else:
                    rel_dir = value
        else:
            folders.append(arg)

    if not folders:
        print "You must supply at least one folder to look in as an argument."
        sys.exit()

    if not rel_dirs:
        if rel_dir:
            rel_dirs = [rel_dir] * len(folders)

    elif len(rel_dirs) != len(folders):
        print "Number of relative directories must match the number of folders."
        sys.exit()

    # run the minifier
    minify(folders, relative_dirs=rel_dirs)

    # now do the actual deploy to the servers
    #from subprocess import call
    #call(["appcfg.py", "update", "."])

