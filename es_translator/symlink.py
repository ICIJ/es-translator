from os.path import isdir, isfile, islink
from sh import ln, rm

def create_symlink(source, target, options = '-s', force = True):
    if isdir(source) or isfile(source):
        if force and islink(target):
            rm(target)
        ln(options, source, target)
