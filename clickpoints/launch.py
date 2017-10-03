
def main():
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == "register" or sys.argv[1] == "install":
            from .includes.RegisterRegistry import install
            return install()
        elif sys.argv[1] == "unregister" or sys.argv[1] == "uninstall":
            from .includes.RegisterRegistry import install
            return install("uninstall")
        elif sys.argv[1] == "-v" or sys.argv[1] == "--version":
            import clickpoints
            print(clickpoints.__version__)
            return
        elif sys.argv[1] == "ffmpeg":
            import imageio
            import glob
            import os
            # check for ffmpeg
            try:
                # check if imageio already has an exe file
                imageio.plugins.ffmpeg.get_exe()
                print("ffmpeg found from imageio")
            except imageio.core.fetching.NeedDownloadError:
                # try to find an ffmpeg.exe in the ClickPoints folder
                files = glob.glob(os.path.join(os.path.dirname(__file__), "..", "ffmpeg*.exe"))
                files.extend(glob.glob(os.path.join(os.path.dirname(__file__), "..", "external", "ffmpeg*.exe")))
                # if an ffmpeg exe has been found, set the environmental variable accordingly
                if len(files):
                    print("ffmpeg found", files[0])
                    os.environ['IMAGEIO_FFMPEG_EXE'] = files[0]
                # if not, try to download it
                else:
                    print("try to download ffmpeg")
                    imageio.plugins.ffmpeg.download()
            return

    from clickpoints import print_status
    # print
    print_status()

    """ some magic to prevent PyQt5 from swallowing exceptions """
    # Back up the reference to the exceptionhook
    sys._excepthook = sys.excepthook
    # Set the exception hook to our wrapping function
    sys.excepthook = lambda *args: sys._excepthook(*args)

    from qtpy import QtCore, QtWidgets, QtGui
    import sys
    import ctypes
    from clickpoints.Core import ClickPointsWindow
    from clickpoints.includes import LoadConfig

    from clickpoints import define_paths

    define_paths()

    app = QtWidgets.QApplication(sys.argv)

    # set an application id, so that windows properly stacks them in the task bar
    if sys.platform[:3] == 'win':
        myappid = 'fabrybiophysics.clickpoints'  # arbitrary string
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    # load config and exec addon code
    config = LoadConfig()

    # init and open the ClickPoints window
    window = ClickPointsWindow(config, app)
    window.show()
    app.exec_()

# start the main function as entry point
if __name__ == '__main__':
    main()