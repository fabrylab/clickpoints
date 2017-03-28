@echo off
:: install super script for ClickPoints
:: assuming python was added to system PATH variable

@ECHO OFF & CLS & ECHO.
NET FILE 1>NUL 2>NUL & IF ERRORLEVEL 1 (ECHO You must right-click and select & ECHO "RUN AS ADMINISTRATOR"  to run this batch. Exiting... & ECHO. & PAUSE & EXIT /D)
:: ... proceed here with admin rights ...

:: switch path back after UAC elevation
cd /d %~dp0

:: add WinPython for ClickPoints to PATH (if installed)
set PATH=%CLICKPOINTS_PATH%;%PATH%

:: generate Clickpoints.bat
python install_bat.py 
echo DONE
echo.

:: register ClickPoints PATH to user PATH variable
:: for convenient CMD access via ClickPoints.bat
::echo Adding ClickPoints to User PATH
::SET basepath=%~dp0
::IF %basepath:~-1%==\ SET basepath=%basepath:~0,-1%
::setx path "%PATH%";"%basepath%"
::echo DONE
::echo.

:: generate entries in windows registry
echo Register ClickPoints ...
python install_registry.py install
echo DONE
echo.

:: install ClickPoints python package
cd ..
cd package
python setup.py develop --no-deps
cd ..

pause
