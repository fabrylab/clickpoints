'''
Setup script to add Clickpoints to windows registry
under base key HKEY_CURRENT_USER

Args:
    mode (string): choose install/uninstall
    |  install
    |  uninstall

'''


import _winreg,sys, ntpath, os
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


if __name__ == '__main__':
    mode= sys.argv[1]
    assert isinstance(mode,str)
    print("running install registry script - mode: %s" % mode)

    # file extentions for which to add to Clickpoint shortcut
    extension = [".png",".jpg",".jpeg",".tiff",".tif",".bmp",".gif",".avi",".mp4"]

    if mode == 'install':
        ### add to DIRECTORYS
        # create entry under HKEY_CURRENT_USER to show in dropdown menu for folders
        print("setup for directory")
        reg_path = r"Software\Classes\Directory\shell\1ClickPoint\\"
        set_reg(_winreg.HKEY_CURRENT_USER,reg_path,None,"ClickPoints")
        set_reg(_winreg.HKEY_CURRENT_USER,reg_path,"icon", os.path.join(os.path.abspath(os.path.dirname(__file__))+r"\icons\ClickPoints.ico"))
        reg_path = r"Software\Classes\Directory\shell\1ClickPoint\command\\"
        set_reg(_winreg.HKEY_CURRENT_USER,reg_path,None,ntpath.join(os.path.abspath(os.path.dirname(__file__))+"\ClickPoints.bat \"%1\""))


        # ### add for specific file types
        # # create entry under HKEY_CLASSES_ROOT\SystemFileAssociations to show in dropdown menu for specific file types
        for ext in extension:
            print("install for extension:%s" % ext)
            reg_path = r"SOFTWARE\Classes\SystemFileAssociations\\" + ext + r"\shell\1ClickPoint\\"
            set_reg(_winreg.HKEY_CURRENT_USER,reg_path,None,"ClickPoints")
            set_reg(_winreg.HKEY_CURRENT_USER,reg_path,"icon", os.path.join(os.path.abspath(os.path.dirname(__file__))+r"\icons\ClickPoints.ico"))
            reg_path = r"SOFTWARE\Classes\SystemFileAssociations\\"  + ext + r"\shell\1ClickPoint\command\\"
            set_reg(_winreg.HKEY_CURRENT_USER,reg_path,None,ntpath.join(os.path.abspath(os.path.dirname(__file__))+"\ClickPoints.bat \"%1\""))

    elif mode == 'uninstall':
        ### remove from DIRECTORY
        print("remove for directory")
        reg_path = r"Software\Classes\Directory\shell\1ClickPoint\command\\"
        del_reg(_winreg.HKEY_CURRENT_USER,reg_path)
        reg_path = r"Software\Classes\Directory\shell\1ClickPoint\\"
        del_reg(_winreg.HKEY_CURRENT_USER,reg_path)

        for ext in extension:
            print("remove for extension:%s" % ext)
            reg_path = r"SOFTWARE\Classes\SystemFileAssociations\\"  + ext + r"\shell\1ClickPoint\command\\"
            del_reg(_winreg.HKEY_CURRENT_USER,reg_path)
            reg_path = r"SOFTWARE\Classes\SystemFileAssociations\\"  + ext + r"\shell\1ClickPoint\\"
            del_reg(_winreg.HKEY_CURRENT_USER,reg_path)

    else:
        raise Exception('Uknown mode: %s' % mode)