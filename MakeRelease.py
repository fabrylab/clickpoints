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
            print("regext", line)
            ignore_pattern.append(lambda name, pattern=line: re.match(pattern, name) is not None)
        else:
            print("WARNING: unknown syntax", syntax)

directory = os.path.dirname(__file__)
#target_directory = os.path.join(directory, "..", "tmp")
#if os.path.exists(target_directory):
#    shutil.rmtree(target_directory)
#os.mkdir(target_directory)
myzip = zipfile.ZipFile('clickpoints.zip', 'w')

def CopyDirectory(directory):
    global myzip
    old_dir = os.getcwd()
    os.chdir(directory)
    a = [file[2:] for file in os.popen("hg status -m").read().split("\n") if file != ""]
    if len(a) != 0:
        print("WARNING: uncommited changes")

    filelist = [file[2:] for file in os.popen("hg status -m -c").read().split("\n") if file != ""]
    for file in filelist:
        ignore = False
        for pattern in ignore_pattern:
            if pattern(file):
                ignore = True
                print("ignoring", file)
                break
        if ignore:
            continue
        #dst = os.path.join(target_directory, os.path.basename(directory), file)
        #print(dst)
        #folder = os.path.dirname(dst)
        #if not os.path.exists(folder):
        #    os.mkdir(folder)
        myzip.write(file, os.path.join(directory, file))
        #shutil.copyfile(file, dst)
    os.chdir(old_dir)

os.chdir("..")
CopyDirectory(".")
CopyDirectory("clickpoints")
CopyDirectory("mediahandler")
CopyDirectory("qextendedgraphicsview")

myzip.close()