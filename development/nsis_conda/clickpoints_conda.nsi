# conda execute
# env:
#  - nsis 3.*
#  - inetc
#  - conda_macros
# channels:
#  - nsis
# run_with: makensis

SetCompressor lzma

!include conda.nsh
;!include inetc.nsh
!include MUI2.nsh

Name "ClickPoints"
OutFile "ClickPoints.exe"
RequestExecutionLevel user

; Modern UI installer stuff 
!include "MUI2.nsh"

;; ClickPoints
!define MUI_HEADERIMAGE
!define MUI_HEADERIMAGE_BITMAP "header.bmp" ; optional
!define MUI_WELCOMEFINISHPAGE_BITMAP "panel.bmp"
;; end ClickPoints

; UI pages
!insertmacro MUI_PAGE_WELCOME
!define MUI_COMPONENTSPAGE_NODESC
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"
# ... other required NSIS stuff

Section "Conda package manager"
  !insertmacro InstallOrUpdateConda
SectionEnd

Section "ClickPoints Application files"
  !insertmacro InstallOrUpdateApp "clickpoints" "-c rgerum -c conda-forge"
  !insertmacro WriteUninstaller "clickpoints"
SectionEnd

Section "Start Menu shortcut"
  Call SetRootEnv
  ; Here we don't use the CreateShortcut macro of conda_macros because we want a console that does not close when an exception occurs
  ; therefore we create a bat file and link to that
  Push $R1
  Push $R2
  StrCpy $R1 "$ENVS\_app_own_environment_clickpoints"
  
  FileOpen $0 "$R1\ClickPoints.bat" w
  IfErrors done
  FileWrite $0 "@echo off$\r$\n"
  FileWrite $0 '"$R1\Scripts\clickpoints.exe" -srcpath=%1$\r$\n'
  FileWrite $0 "IF %ERRORLEVEL% NEQ 0 pause$\r$\n"
  FileClose $0
  done:
  
  SetOutPath "$PROFILE"  # Shortcut working dir
  CreateShortcut "$SMPROGRAMS\ClickPoints.lnk" "$R1\ClickPoints.bat" "$R2" "$R1\Lib\site-packages\clickpoints\icons\ClickPoints.ico" 0 "" "" "Open ClickPoints"

  Pop $R2
  Pop $R1
  
  ; this would be the useage of the CreateShortcut macro
  ;!insertmacro CreateShortcut "ClickPoints" \
  ;  "clickpoints" "ClickPoints.bat" ""\
  ;  "..\..\clickpoints\icons\ClickPoints.ico"
  ;  ;Lib\site-packages\clickpoints
SectionEnd

Section "File Assiciations";
  Call SetRootEnv

  DetailPrint "Linking file extensions ..."

  ExecDos::exec /DETAILED '$ENVS\_app_own_environment_clickpoints\Scripts\clickpoints.exe register' "" ""
  !insertmacro _FinishMessage "File extensions linked"
SectionEnd

Section "un.ClickPoints";
  Call un.SetRootEnv
  ExecDos::exec /DETAILED '$R1\clickpoints unregister' "" ""
  
  !insertmacro DeleteApp "clickpoints"
  !insertmacro DeleteShortcut "ClickPoints"
SectionEnd
