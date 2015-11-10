import _winreg,sys, ntpath, os

def set_reg(name, value, type= _winreg.REG_SZ):
    try:
        _winreg.CreateKey(_winreg.HKEY_CLASSES_ROOT, REG_PATH)
        registry_key = _winreg.OpenKey(_winreg.HKEY_CLASSES_ROOT, REG_PATH, 0,
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

def get_reg(name):
    try:
        registry_key = _winreg.OpenKey(_winreg.HKEY_CLASSES_ROOT, REG_PATH, 0,
                                       _winreg.KEY_READ)
        value, regtype = _winreg.QueryValueEx(registry_key, name)
        _winreg.CloseKey(registry_key)
        return value
    except WindowsError:
        return None

install= False
uninstall=True

extension = [".png",".jpg",".jpeg",".tiff",".tif",".bmp",".gif",".avi",".mp4"]

if install:
    ### add to DIRECTORYS
    # create entry under HKEY_CLASSES_ROOT\Directory to show in dropdown menu for folders
    REG_PATH = r"Directory\shell\ClickPoint\\"
    set_reg(None,"ClickPoints")
    set_reg("icon", os.path.join(os.path.abspath(os.path.dirname(__file__))+r"\icons\ClickPoints.ico"))
    REG_PATH = r"Directory\shell\ClickPoint\command\\"
    set_reg(None,ntpath.join(os.path.abspath(os.path.dirname(__file__))+r"\ClickPoints.bat %1"))


    ### add for specific file types
    # create entry under HKEY_CLASSES_ROOT\SystemFileAssociations to show in dropdown menu for specific file types
    for ext in extension:
        print(ext)
        REG_PATH = r"SystemFileAssociations\\" + ext + r"\shell\ClickPoint\\"
        set_reg(None,"ClickPoints")
        set_reg("icon", os.path.join(os.path.abspath(os.path.dirname(__file__))+r"\icons\ClickPoints.ico"))
        REG_PATH = r"SystemFileAssociations\\" + ext + r"\shell\ClickPoint\command\\"
        set_reg(None,ntpath.join(os.path.abspath(os.path.dirname(__file__))+r"\ClickPoints.bat %1"))

if uninstall:
    ### remove from DIRECTORY
    REG_PATH = r"Directory\shell\ClickPoint\\"
    del_reg(_winreg.HKEY_CLASSES_ROOT,REG_PATH)

    for ext in extension:
        print(ext)
        REG_PATH = r"SystemFileAssociations\\" + ext + r"\shell\ClickPoint\command\\"
        del_reg(_winreg.HKEY_CLASSES_ROOT,REG_PATH)
        REG_PATH = r"SystemFileAssociations\\" + ext + r"\shell\ClickPoint\\"
        del_reg(_winreg.HKEY_CLASSES_ROOT,REG_PATH)

