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
        HgPull("../../mediahandler", update=True)
        HgPull("../../qextendedgraphicsview", update=True)
        HgPull("../../../ClickpointsExamples", update=True)
        TestRevisions()#commit_hash)
        return 'OK'
   #else:
   #   return displayHTML(request)

@app.route('/log/<path:path>')
def send_log(path):
    return send_from_directory('log', path)

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
        current_number = int(os.popen('hg id -n').read().strip())
        if current_number == current_tip_number:
            break
        os.system("hg update -r %d -C" % (current_number+1))
        os.system(sys.executable+" TestResultsX.py")

if __name__ == "__main__":
    HgPull("..")
    HgPull("../../mediahandler")
    HgPull("../../qextendedgraphicsview")
    HgPull("../../../ClickpointsExamples")
    #revision = os.popen('hg log -r-1 --template "{node}" -l 1').read()
    TestRevisions()#revision[:7])
    app.run(host='0.0.0.0')
