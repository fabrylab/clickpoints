from __future__ import print_function, division
import os
import shutil
import fnmatch
import re
import zipfile

ignore_pattern = []

with open(".releaseignore") as fp:
    syntax = "glob"
    for line in fp.readlines():
        line = line.strip()
        if line == "":
            continue
        if line[0] == "#":
            continue
        if line.startswith("syntax"):
            syntax = line.split(" ", 1)[1]
            continue
        if syntax == "glob":
            ignore_pattern.append(lambda name, pattern=line: fnmatch.fnmatch(name, pattern))
        elif syntax == "regexp":
            ignore_pattern.append(lambda name, pattern=line: re.match(pattern, name) is not None)
        else:
            print("WARNING: unknown syntax", syntax)

def CheckIgnoreMatch(file):
    for pattern in ignore_pattern:
        if pattern(file):
            return True
    return False

def CopyDirectory(directory):
    global myzip, file_list
    old_dir = os.getcwd()
    os.chdir(directory)
    uncommited = os.popen("hg status -m").read().strip()
    if uncommited != "":
        print("WARNING: uncommited changes in", directory)

    filelist = [file[2:] for file in os.popen("hg status -m -c").read().split("\n") if file != ""]
    for file in filelist:
        if CheckIgnoreMatch(file):
            continue
        myzip.write(file, os.path.join(directory, file))
        file_list.write(os.path.join(directory, file)+"\n")
    os.chdir(old_dir)

directory = os.path.dirname(__file__)
file_list = open("files_tmp.txt", "w")
myzip = zipfile.ZipFile('clickpoints.zip', 'w')

os.chdir("..")
CopyDirectory(".")
CopyDirectory("clickpoints")
CopyDirectory("mediahandler")
CopyDirectory("qextendedgraphicsview")

file_list.close()
myzip.write(os.path.join("clickpoints", "files_tmp.txt"), "files.txt")
os.remove(os.path.join("clickpoints", "files_tmp.txt"))
myzip.close()