import sys, os

script_path = os.path.join(os.path.dirname(__file__), "ClickPointsQT.py")
icon_path = os.path.join(os.path.dirname(__file__), "icons", "ClickPoints.ico")
if sys.platform.startswith('win'):
    with open("ClickPoints.bat", 'w') as fp:
        print("Writing ClickPoints.bat")
        fp.write(sys.executable)
        fp.write(" ")
        fp.write(script_path)
        fp.write(" -srcpath=%1\n")
        fp.write("IF %ERRORLEVEL% NEQ 0 pause\n")
else:
    with open("ClickPoints.sh", 'w') as fp:
        print("Writing ClickPoints.sh")
        fp.write("#!/bin/bash\n")
        fp.write("python")
        fp.write(" ")
        fp.write(script_path)
        fp.write(" -srcpath=\"$1\"\n")
        
    with open("/home/"+os.popen('whoami').read()[:-1]+"/.local/share/applications/ClickPoints.desktop", 'w') as fp:
        print("Writing ClickPoints.desktop")
        fp.write("[Desktop Entry]\n")
        fp.write("Type=Application\n")
        fp.write("Name=ClickPoints\n")
        fp.write("GenericName=Image View and Annotate\n")
        fp.write("Comment=Display images and videos and annotate them\n")
        fp.write("Exec=python "+script_path+" -srcpath=\"%f\"\n")
        fp.write("NoDisplay=true\n")
        fp.write("Icon="+icon_path+"\n")
        fp.write("Categories=Graphics;2DGraphics;RasterGraphics;Video;Qt;\n")
        fp.write("MimeType=video/x-msvideo;video/mpeg;image/bmp;image/png;image/jpeg;image/tiff;image/gif;$\n")