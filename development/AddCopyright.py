from __future__ import print_function, division
import os, sys
import shutil
import glob
import fnmatch
import re
import zipfile

with open("CopyrightNotice.txt", "r") as fp:
    notice = fp.read()

for root, dirs, files in os.walk(os.path.join(os.path.dirname(__file__), "..")):
    for file in files:
        # not this file
        if file == os.path.split(__file__)[1] or file == "ClickPoints.py":
            continue
        if file.endswith(".py"):
            print(file)
            full_filename = os.path.join(root, file)
            with open(full_filename+".tmp", "w") as fp2:
                fp2.write(notice.format(file))
                with open(full_filename, "r") as fp1:
                    start = False
                    for line in fp1.readlines():
                        if not start and not (line.startswith("#") or line.strip() == ""):
                            start = True
                        if start:
                            fp2.write(line)
                            continue


            shutil.move(full_filename+".tmp", full_filename)
