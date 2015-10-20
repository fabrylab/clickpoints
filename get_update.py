from __future__ import division,print_function
import requests
import urllib2
#TODO: decide if its better to use only one lib? urrlib (+ easy file download)

# parameters
link_server_version=r"http://fabry_biophysics.bitbucket.org/clickpoints/version.html"
link_server_update=r"http://fabry_biophysics.bitbucket.org/clickpoints/clickpoints.zip"
path_local_version=r""

# get server version
r=requests.get(link_server_version)
server_verion=r.content
print('server version: %s' % r.content)

# get local version
#f=open(path_local_version,'r')
#local_version=f.readline()
local_version='0.0'

# check if update is necessary
if not local_version == server_verion:
    print('Update found - preparing files')
    update=True
else:
    print('no update available')
    update=False

# get files for update
updatefile = urllib2.URLopener()
updatefile.retrieve(link_server_update, "clickpoints.zip")

#TODO: continue - but my beer is waiting ...