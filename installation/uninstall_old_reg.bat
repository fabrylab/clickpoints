@echo off
::uninstall script for old registry entries (Anya and Aym)
::assuming python was added to system PATH variable

::generate Clickpoints.bat
python uninstall_registry_old.py
echo DONE
