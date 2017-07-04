#!/usr/bin/env python
# -*- coding: utf-8 -*-
# TestServer.py

# Copyright (c) 2015-2016, Richard Gerum, Sebastian Richter
#
# This file is part of ClickPoints.
#
# ClickPoints is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ClickPoints is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ClickPoints. If not, see <http://www.gnu.org/licenses/>

import os
from sys import platform as _platform
import sys

from flask import Flask
from flask import request, send_from_directory
app = Flask(__name__)

@app.route("/")
def hello():
    return "Test Server is running"

@app.route('/webhook', methods=['GET', 'POST'])
def tracking():
    if request.method == 'POST':
        data = request.get_json()
        commit_author = data['actor']['username']
        commit_hash = data['push']['changes'][0]['new']['target']['hash'][:7]
        commit_url = data['push']['changes'][0]['new']['target']['links']['html']['href']
        print('Webhook received! %s committed %s' % (commit_author, commit_hash))
    HgPull("..")
    HgPull("../../ClickpointsExamples", update=True)
    TestRevisions()#commit_hash)
    return 'OK'
   #else:
   #   return displayHTML(request)

@app.route('/log/<path:path>')
def send_log(path):
    path = os.path.join('..', '..', 'fabry_biophysics.bitbucket.org', 'clickpoints', 'tests', path.replace("/", os.path.sep))
    print(path)
    with open(path) as fp:
        return fp.read()

@app.route('/webhook')
def tracking2():
    return "Hello World!"

def HgPull(path, update=False):
    old_path = os.getcwd()
    os.chdir(path)
    os.system("hg pull")
    if update:
        os.system("hg update -C")
    os.chdir(old_path)    
    
def TestRevisions():#hash):
    while True:
        current_tip_number = int(os.popen('hg log -r -1 --template "{rev}" ').read().strip())
        #current_hash = os.popen('hg id -i').read().strip()
        #if current_hash.startswith(hash):
        #    break
        #print(os.popen('hg id -n').read().strip())
        try:
            current_number = int(os.popen('hg id -n').read().strip())
        except ValueError:
            break
        if current_number == current_tip_number:
            break
        os.system("hg update -r %d -C" % (current_number+1))
        os.system(sys.executable+" TestResultsX.py")

if __name__ == "__main__":
    #HgPull("..")
    #HgPull("../../ClickpointsExamples")
    #revision = os.popen('hg log -r-1 --template "{node}" -l 1').read()
    TestRevisions()#revision[:7])
    app.run(host='0.0.0.0')
