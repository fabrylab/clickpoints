import requests
import os
import sys
import glob
import re
import shutil

def PushResults(log_file, key, name, link):

    with open(log_file, "r") as f:
        tests = f.readline().strip()
        tests = [c == "." for c in tests]
        desc = "%d of %d tests passed" % (sum(tests), len(tests))
        state = "SUCCESSFUL" if sum(tests) == len(tests) else "FAILED"
    print(desc)
    print("Finished")

    revision = os.popen('hg log -r-1 --template "{node}" -l 1').read()
    print(revision)
    print(link)
    data = {
        "state": state,
        "key": key,
        "name": name,
        "url": link,#"http://fabry_biophysics.bitbucket.org/",
        "description": desc
    }

    # Construct the URL with the API endpoint where the commit status should be
    # posted (provide the appropriate owner and slug for your repo).
    api_url = ('https://api.bitbucket.org/2.0/repositories/'
               '%(owner)s/%(repo_slug)s/commit/%(revision)s/statuses/build'
               % {'owner': 'fabry_biophysics',
                  'repo_slug': 'clickpoints',
                  'revision': revision})
    print(api_url)

    # Post the status to Bitbucket. (Include valid credentials here for basic auth.
    # You could also use team name and API key.)
    r = requests.post(api_url, auth=('FabryBioPhysicsUser', '12345678'), json=data)
    print(r.text)

def RunTest(script_file):
    os.system(sys.executable+" "+script_file)

def GetMetaData(script_file):
    regex = re.compile(r"__(.*)__\s*=\s*\"(.*)\"")
    results = {}
    with open(script, "r") as fp:
        for line in fp.readlines():
            if line.strip().startswith("__"):
                match = regex.match(line)
                if not match:
                    continue
                data = match.groups()
                results[data[0]] = data[1]
    return results

def HgAdd(path, file):
    old_path = os.getcwd()
    os.chdir(path)
    os.system("hg add "+file)
    os.chdir(old_path)

def HgCommit(path, msg, push=False):
    old_path = os.getcwd()
    os.chdir(path)
    os.system("hg commit -m \"%s\"" % msg)
    if push:
        os.system("hg push")
    os.chdir(old_path)

if __name__ == '__main__':
    scripts = glob.glob("Test_*.py")
    revision = os.popen('hg log -r-1 --template "{node}" -l 1').read()
    print("Working dir", os.getcwd())
    path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "fabry_biophysics.bitbucket.org", "clickpoints", "tests")
    path = os.path.join(path, revision)
    if not os.path.exists(path):
        os.mkdir(path)
    data = []
    for script in scripts:
        metadata = GetMetaData(script)
        RunTest(script)
        log_file = 'log_'+metadata["key"]+'.txt'
        shutil.copy(log_file, os.path.join(path, log_file))
        #HgAdd(path, log_file)
        #revision = "1c448d26826ace770af9ee2e67765c0d4a25a35c"
        #print("http://fabry_biophysics.bitbucket.org/clickpoints/tests/"+revision+"/"+log_file)
        #data.append([log_file, metadata["key"], metadata["testname"], "http://fabry_biophysics.bitbucket.org/clickpoints/images/Logo.png"])
        #data.append([log_file, metadata["key"], metadata["testname"], "https://fabry_biophysics.bitbucket.org/clickpoints/tests/1c448d26826ace770af9ee2e67765c0d4a25a35c/log_DATAFILE.txt"])#"http://fabry_biophysics.bitbucket.org/clickpoints/tests/"+revision+"/"])
        data.append([log_file, metadata["key"], metadata["testname"], "http://example.com/path/to/build/info"])#"http://fabry_biophysics.bitbucket.org/clickpoints/tests/"+revision+"/"])
    #HgCommit(path, "Test results revision "+revision, push=True)
    for args in data:
        print("--------------")
        PushResults(*args)
        print("--------------")


