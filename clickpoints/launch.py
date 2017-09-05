
def main():
    import sys
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