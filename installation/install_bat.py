#!/usr/bin/env python
import sys, os

directory = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
os.chdir("..")
script_path = os.path.join(directory, "ClickPoints.py")
icon_path = os.path.join(directory, "icons", "ClickPoints.ico")
if sys.platform.startswith('win'):
    with open("ClickPoints.bat", 'w') as fp:
        print("Writing ClickPoints.bat")
        fp.write("@echo off\n")
        fp.write("\"")
        fp.write(sys.executable)
        fp.write("\"")
        fp.write(" ")
        fp.write("\"")
        fp.write(script_path)
        fp.write("\"")
        fp.write(" -srcpath=%1\n")
        fp.write("IF %ERRORLEVEL% NEQ 0 pause\n")
else:
    sh_file = os.path.join(directory, "clickpoints")
    with open(sh_file, 'w') as fp:
        print("Writing ClickPoints bash file")
        fp.write("#!/bin/bash\n")
        fp.write("python")
        fp.write(" ")
        fp.write(script_path)
        fp.write(" -srcpath=\"$1\"\n")
        fp.write("if [[ $? -ne 0 ]]\n")
        fp.write("then\n")
        fp.write("\tread -n1 -r -p \"Press any key to continue...\" key\n")
        fp.write("fi\n")
        os.system("chmod +x %s" % sh_file)
        
    print("Copying ClickPoints bash file to /bin/")
    os.popen("sudo cp %s /bin/" % sh_file)
        
    desktop_file = "/home/"+os.popen('whoami').read()[:-1]+"/.local/share/applications/clickpoints.desktop"
    with open(desktop_file, 'w') as fp:
        print("Writing clickpoints.desktop")
        fp.write("[Desktop Entry]\n")
        fp.write("Type=Application\n")
        fp.write("Name=ClickPoints\n")
        fp.write("GenericName=View Images/Videos and Annotate them\n")
        fp.write("Comment=Display images and videos and annotate them\n")
        fp.write("Exec="+sh_file+" \"%f\"\n")
        fp.write("NoDisplay=false\n")
        fp.write("Terminal=true\n")
        fp.write("Icon="+icon_path+"\n")
        fp.write("Categories=Development;Science;IDE;Qt;\n")
        fp.write("MimeType=inode/directory;video/*;image/*;video/mp4;video/x-msvideo;video/mpeg;image/bmp;image/png;image/jpeg;image/tiff;image/gif;$\n")
        fp.write("InitialPreference=10\n")

    for ext in ["inode/directory", "ideo/mp4", "video/x-msvideo", "video/mpeg", "image/bmp", "image/png", "image/jpeg", "image/gif", "image/tiff"]:
        print("Setting ClickPoints as default application for %s" % ext)
        os.popen("sudo xdg-mime default clickpoints.desktop "+ext)
    os.chdir("package")
    os.popen("sudo python setup.py develop")
    os.chdir("..")
        
