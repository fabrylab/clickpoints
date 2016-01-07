from __future__ import print_function, division
import os, sys
import shutil
import fnmatch
import re
import zipfile

def LoadIgnorePatterns(file):
    ignore_pattern = []
    with open(file) as fp:
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
    return ignore_pattern

def CheckIgnoreMatch(file):
    for pattern in ignore_pattern:
        if pattern(file):
            return True
    return False

def CopyDirectory(directory, dest_directory):
    global myzip, file_list
    old_dir = os.getcwd()
    os.chdir(directory)

    filelist = [file[2:] for file in os.popen("hg status -m -c").read().split("\n") if file != ""]
    for file in filelist:
        if CheckIgnoreMatch(file):
            continue
        print(file, os.path.join(directory, file))
        dest_path = os.path.normpath(os.path.join(dest_directory, file))
        if file != "files.txt":
            myzip.write(file, dest_path)
        file_list.write(dest_path+"\n")
    os.chdir(old_dir)

def CheckForUncommitedChanges(directory):
    old_dir = os.getcwd()
    os.chdir(directory)
    uncommited = os.popen("hg status -m").read().strip()
    if uncommited != "":
        print("ERROR: uncommited changes in repository", directory)
        sys.exit(1)
    os.system("hg pull -u")
    os.chdir(old_dir)

from optparse import OptionParser

parser = OptionParser()
parser.add_option("-v", "--version", action="store", type="string", dest="version")
parser.add_option("-t", "--test", action="store_false", dest="release", default=False)
parser.add_option("-r", "--release", action="store_true", dest="release")
(options, args) = parser.parse_args()
if options.version is None:
    options.version = args[0]

print("MakeRelease started ...")
# go to parent directory ClickPointsProject
os.chdir("..")
os.chdir("..")
path_to_clickpointsproject = os.getcwd()

# define paths to website, zipfile and version file
path_to_website = r"..\fabry_biophysics.bitbucket.org\clickpoints"
zip_file = 'clickpoints_v%s.zip'
version_file = os.path.join("clickpoints", "version.txt")

paths = [".", "clickpoints", "mediahandler", "qextendedgraphicsview"]
path_destinations = ["installation", ".", "includes", "includes"]

""" Checks """
# check for new version name as command line argument
new_version = ""
try:
    new_version = sys.argv[1]
except IndexError:
    pass
if new_version == "":
    print("ERROR: no version number supplied. Use 'MakeRelease.py 0.9' to release as version 0.9")
    sys.exit(1)
zip_file = zip_file % new_version

# get old version name
with open(version_file, "r") as fp:
    old_version = fp.read().strip()

# check if new version name differs
if options.release and old_version == new_version:
    print("ERROR: new version is the same as old version")
    sys.exit(1)

# check for uncommited changes
if options.release:
    for path in paths:
        CheckForUncommitedChanges(path)
    CheckForUncommitedChanges(path_to_website)

""" Let's go """
# write new version to version.txt
with open(version_file, "w") as fp:
    fp.write(new_version)

# Create filelist and zip file
file_list = open("files.txt", "w")
myzip = zipfile.ZipFile(zip_file, 'w', compression=zipfile.ZIP_DEFLATED)

# Gather files repository files and add them to zip file
ignore_pattern = LoadIgnorePatterns(os.path.join("clickpoints", ".releaseignore"))
for path, path_dest in zip(paths, path_destinations):
    CopyDirectory(path, path_dest)

print("finished zip")
# Close
file_list.close()
myzip.write("files.txt", "installation/files.txt")
myzip.close()

# Copy files to website
print("Move Files")
shutil.move(zip_file, os.path.join(path_to_website, zip_file))
shutil.copy(version_file, os.path.join(path_to_website, "version.html"))

if options.release:
    # Commit changes to ClickPoints
    os.chdir("clickpoints")
    os.system("hg commit -m \"set version to %s\"" % new_version)
    os.chdir("..")

    # Commit changes in ClickPointsRelease
    os.system("hg commit -m \"Release v%s\"" % new_version)
    os.system("hg tag \"v%s\"" % new_version)

    # Commit changes in website
    os.chdir(path_to_website)
    os.system("hg add "+zip_file)
    os.system("hg commit -m \"Release v%s\"" % new_version)

    # Push everything
    os.system("hg push")
    os.chdir(path_to_clickpointsproject)
    os.system("hg push")
    os.chdir("clickpoints")
    os.system("hg push")

print("MakeRelease completed!")