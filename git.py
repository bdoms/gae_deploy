
import os
import sys
import subprocess


def installed():
    """ detects if the system has git or not """
    try:
        subprocess.call(["git", "rev-parse"])
        return True
    except OSError:
        return False

def isRepository():
    return subprocess.check_output(["git", "rev-parse", "--is-inside-work-tree"]).replace("\n", "") == "true"

def currentBranch():
    """ gets the name of the current branch """
    return subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"]).replace("\n", "")

def checkout(branch):
    """ returns True if successful, False if there was an error """
    # git is stupid and puts out the success message for the checkout command on stderr instead of stdout
    process = subprocess.Popen(["git", "checkout", branch], stderr=subprocess.PIPE)
    out, err = process.communicate()
    branch_switch = "Switched to branch '%s'" % branch
    branch_on = "Already on '%s'" % branch
    if branch_switch not in err and branch_on not in err:
        raise Exception("Could not switch to branch '%s'. Reason:\n%s" % (branch, err))
