@echo off
::install super script for clickpoints
::assuming python was added to system PATH variable

::generate Clickpoints.bat
python install_bat.py 
echo DONE
echo.

:: register ClickPoints PATH to user PATH variable
:: for convinient CMD acces via ClickPoints.bat
::echo Adding ClickPoints to User PATH
::SET basepath=%~dp0
::IF %basepath:~-1%==\ SET basepath=%basepath:~0,-1%
::setx path "%PATH%";"%basepath%"
::echo DONE
::echo.

::generate entries in w indows registry
echo Register Clickpoints ...
python install_registry.py install
echo DONE
echo.

pause
