!define PRODUCT_NAME "{{appname}}"
!define PRODUCT_VERSION "{{version}}"
!define INSTALLER_NAME "{{installer_name}}"
!define PRODUCT_ICON "{{icon}}"
 
SetCompressor lzma

RequestExecutionLevel admin

{% block modernui %}
; Modern UI installer stuff 
!include "MUI2.nsh"
!define MUI_ABORTWARNING
!define MUI_ICON "${NSISDIR}\Contrib\Graphics\Icons\modern-install.ico"

;; ClickPoints
!define MUI_HEADERIMAGE
!define MUI_HEADERIMAGE_BITMAP "header.bmp" ; optional
!define MUI_WELCOMEFINISHPAGE_BITMAP "panel.bmp"
;; end ClickPoints

; UI pages
{% block ui_pages %}
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
{% endblock ui_pages %}
!insertmacro MUI_LANGUAGE "English"
{% endblock modernui %}

Name "${PRODUCT_NAME} ${PRODUCT_VERSION}"
OutFile "${INSTALLER_NAME}"
InstallDir "C:\Software\${PRODUCT_NAME}"
ShowInstDetails show

Section -SETTINGS
  SetOutPath "$INSTDIR"
  SetOverwrite ifnewer
SectionEnd

{% block sections %}

Section "!${PRODUCT_NAME}" sec_app
  SectionIn RO
  SetShellVarContext all
  File ${PRODUCT_ICON}
  SetOutPath "$INSTDIR"
  
  ; Install files
  {% for destination, group in grouped_files %}
    SetOutPath "{{destination}}"
    {% for file in group %}
      File "{{ file }}"
    {% endfor %}
  {% endfor %}
  
  ; Install directories
  {% for dir, destination in install_dirs %}
    SetOutPath "{{ pjoin(destination, dir) }}"
    File /r "{{dir}}\*.*"
  {% endfor %}
  
  ; Install shortcuts
  ; The output path becomes the working directory for shortcuts
  SetOutPath "%HOMEDRIVE%\%HOMEPATH%"
    CreateShortCut "$SMPROGRAMS\ClickPoints.lnk" \
      '"$INSTDIR\ClickPoints.bat"' "" "$INSTDIR\ClickPoints.ico"
  SetOutPath "$INSTDIR"
  
  ; Install clickpoints package
  DetailPrint "Installing ClickPoints module..."
  nsExec::ExecToLog 'python "$INSTDIR\package\setup_nodependencies.py" develop'
  WriteUninstaller $INSTDIR\uninstall.exe
  ; Add ourselves to Add/remove programs
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" \
                   "DisplayName" "${PRODUCT_NAME}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" \
                   "UninstallString" '"$INSTDIR\uninstall.exe"'
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" \
                   "InstallLocation" "$INSTDIR"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" \
                   "DisplayIcon" "$INSTDIR\${PRODUCT_ICON}"
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" \
                   "NoModify" 1
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" \
                   "NoRepair" 1
                   
                   
  ;; ClickPoints                
  ClearErrors
  FileOpen $0 "$INSTDIR\ClickPoints.bat" w
  IfErrors done
  FileWrite $0 "@echo off$\r$\n"  
  FileWrite $0 'python "$INSTDIR\ClickPoints.py" -srcpath=%1$\r$\n'
  FileWrite $0 "IF %ERRORLEVEL% NEQ 0 pause$\r$\n"
  FileClose $0
  done:
  
  !define PATH_BAT '$INSTDIR\ClickPoints.bat "%1"'
  !define PATH_ICON "$INSTDIR\${PRODUCT_ICON}"
   
  WriteRegStr HKCU "Software\Classes\Applications\ClickPoints.bat\shell\open\command\" "" '${PATH_BAT}'
  WriteRegStr HKCU "Software\Classes\Applications\ClickPoints.bat\DefaultIcon\" "" "${PATH_ICON}"
  
  WriteRegStr HKCU "Software\Classes\Directory\shell\1${PRODUCT_NAME}" "" "${PRODUCT_NAME}"
  WriteRegStr HKCU "Software\Classes\Directory\shell\1${PRODUCT_NAME}" "icon" "${PATH_ICON}"
  WriteRegStr HKCU "Software\Classes\Directory\shell\1${PRODUCT_NAME}\command" "" '${PATH_BAT}'
  
  {% for extension in extension_list %}
  WriteRegStr HKCU "SOFTWARE\Classes\SystemFileAssociations\{{extension}}\shell\1ClickPoint\" "" "ClickPoints"
  WriteRegStr HKCU "SOFTWARE\Classes\SystemFileAssociations\{{extension}}\shell\1ClickPoint\" "icon" "${PATH_ICON}"
  WriteRegStr HKCU "SOFTWARE\Classes\SystemFileAssociations\{{extension}}\shell\1ClickPoint\command" "" '${PATH_BAT}'
  WriteRegStr HKCU "SOFTWARE\Classes\{{extension}}\OpenWithList\ClickPoints.bat\" "" ""  
  {% endfor %}  
  ;; end ClickPoints

  ; Check if we need to reboot
  IfRebootFlag 0 noreboot
    MessageBox MB_YESNO "A reboot is required to finish the installation. Do you wish to reboot now?" \
                /SD IDNO IDNO noreboot
      Reboot
  noreboot:
SectionEnd

Section "Uninstall"
  SetShellVarContext all
  Delete $INSTDIR\uninstall.exe
  Delete "$INSTDIR\${PRODUCT_ICON}"
  Delete $INSTDIR\ClickPoints.bat
  
  ; Uninstall files
  {% for file, destination in install_files %}
    Delete "{{pjoin(destination, file)}}"
  {% endfor %}
  ; Uninstall directories
  {% for dir, destination in install_dirs %}
    RMDir /r "{{pjoin(destination, dir)}}"
  {% endfor %}
  ; Uninstall shortcuts
      Delete "$SMPROGRAMS\ClickPoints.lnk"
  RMDir $INSTDIR
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}"
  
  ; uninstall clickpoints package
  DetailPrint "Uninstalling ClickPoints module..."
  nsExec::ExecToLog 'pip uninstall clickpoints'
  
  ;; ClickPoints
  DeleteRegKey HKCU "Software\Classes\Applications\ClickPoints.bat"
  
  DeleteRegKey HKCU "Software\Classes\Directory\shell\1${PRODUCT_NAME}"
  
  {% for extension in extension_list %}
  DeleteRegKey HKCU "SOFTWARE\Classes\SystemFileAssociations\{{extension}}\shell\1ClickPoint\"
  DeleteRegKey HKCU "SOFTWARE\Classes\{{extension}}\OpenWithList\ClickPoints.bat\" 
  {% endfor %} 
  ;; end ClickPoints
  
SectionEnd

{% endblock sections %}

; Functions

Function .onMouseOverSection
    ; Find which section the mouse is over, and set the corresponding description.
    FindWindow $R0 "#32770" "" $HWNDPARENT
    GetDlgItem $R0 $R0 1043 ; description item (must be added to the UI)

    {% block mouseover_messages %}
    StrCmp $0 ${sec_app} "" +2
      SendMessage $R0 ${WM_SETTEXT} 0 "STR:${PRODUCT_NAME}"
    
    {% endblock mouseover_messages %}
FunctionEnd
