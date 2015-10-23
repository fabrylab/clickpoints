@echo off

:: register WinPython to HKEY_CURRENT_USER
:: around a few corners but without UAV Elevation

SET pyversion=python-2.7.10.amd64
SET basepath=%~dp0

echo Try to run python script with Pathon path:
echo %basepath%%pyversion%
echo.

:: need the python script as we can't use setx for HKEY_CURRENT_USER PATH variable
:: we add it add fron to circumvent the 1024 chars limit
"%basepath%%pyversion%\python.exe" register_winpy.py

:: but python cant send the reload SIGNAL for HKEY_CURRENT_USER
:: to skip a reboot we make a fake change with setx 
setx A A

