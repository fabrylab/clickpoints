'''
register winpy to user PATH
via registry
this was not feasable via setx as there is no easy way to acces user PATH
without system PATH variable

This should work without UAC elevation
'''
from __future__ import division, print_function

import sys
import os
import _winreg

# can't use imports here - sorry ;)
def set_reg(basekey,reg_path,name, value, type= _winreg.REG_SZ):
    try:
        _winreg.CreateKey(basekey, reg_path)
        registry_key = _winreg.OpenKey(basekey, reg_path, 0,
                                       _winreg.KEY_WRITE)
        _winreg.SetValueEx(registry_key, name, 0, type, value)
        _winreg.CloseKey(registry_key)
        return True
    except WindowsError:
        return False

def del_reg(basekey,reg_path):
    try:
        _winreg.DeleteKey(basekey,reg_path)
        return True
    except WindowsError:
        return False

def get_reg(basekey,reg_path,name):
    try:
        registry_key = _winreg.OpenKey(basekey, reg_path, 0,
                                       _winreg.KEY_READ)
        value, regtype = _winreg.QueryValueEx(registry_key, name)
        _winreg.CloseKey(registry_key)
        return value
    except WindowsError:
        return None

""" WARNING
Must be executed in WinPython basepath
"""

# status update
print("register WinPython")
print("Python interpreter: ",sys.executable)
python_path = os.path.dirname(sys.executable)

# check user PATH variable for existing entry
reg_path = r"Environment"
path_value=get_reg(_winreg.HKEY_CURRENT_USER,reg_path,'Path')

if not python_path in path_value:
    print('no registry entry found - writing to PATH ...')
    newPath=python_path+";"+path_value
    set_reg(_winreg.HKEY_CURRENT_USER,reg_path,'Path',newPath)
else:
    print('PATH already contains WinPython path: ',python_path)

print('Good to Go!')






