@echo off
::install super script for clickpoints
::assuming python was added to system PATH variable

::generate Clickpoints.bat
python install_bat.py 
echo DONE

::generate entries in w indows registry
echo Register Clickpoints ...
python install_registry.py install
echo DONE

pause
