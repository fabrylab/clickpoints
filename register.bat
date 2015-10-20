@echo off
:: register win python Clickpoint version
:: make sure the version entry is correct
SET pyversion=python-2.7.10.amd64
SET basepath=%~dp0

echo "Setting up PATH entry for:"
echo base path=%basepath%
echo pyversion=%pyversion%
echo.

SET regpath=%basepath%%pyversion%
echo %regpath%

setx path "%PATH%";"%regpath%" /M
