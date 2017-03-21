!define PRODUCT_NAME "{{appname}}"
!define PRODUCT_NAME_PATH "{{appname_path}}"
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
InstallDir "C:\Software\${PRODUCT_NAME_PATH}"
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
    SetOutPath "{{ destination }}"
    File /r "{{dir}}\*.*"
  {% endfor %}

  ; Set Environment variable
  
  ; include for some of the windows messages defines
   !include "winmessages.nsh"
   ; HKLM (all users) vs HKCU (current user) defines
   !define env_hklm 'HKLM "SYSTEM\CurrentControlSet\Control\Session Manager\Environment"'
   !define env_hkcu 'HKCU "Environment"'
   ; set variable for local machine
   ;WriteRegExpandStr ${env_hklm} CLICKPOINTS_PATH $INSTDIR\python-3.6.0.amd64;
   ; and current user
   WriteRegExpandStr ${env_hkcu} CLICKPOINTS_PATH "$INSTDIR\python-3.6.0.amd64;$INSTDIR\python-3.6.0.amd64\Scripts;"
   ; make sure windows knows about the change
   SendMessage ${HWND_BROADCAST} ${WM_WININICHANGE} 0 "STR:Environment" /TIMEOUT=5000
  
  ; Write Uninstaller
  WriteUninstaller $INSTDIR\uninstall.exe

  ; Check if we need to reboot
  IfRebootFlag 0 noreboot
    MessageBox MB_YESNO "A reboot is required to finish the installation. Do you wish to reboot now?" \
                /SD IDNO IDNO noreboot
      Reboot
  noreboot:
SectionEnd

Function .onInit
  # set required size of section 'test' to 100 bytes
  SectionSetSize ${sec_app} {{folder_size}}
FunctionEnd

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
    RMDir /r "{{destination, dir}}"
  {% endfor %}
  
   ; delete variable
   DeleteRegValue ${env_hklm} CLICKPOINTS_PATH
   DeleteRegValue ${env_hkcu} CLICKPOINTS_PATH
   ; make sure windows knows about the change
   SendMessage ${HWND_BROADCAST} ${WM_WININICHANGE} 0 "STR:Environment" /TIMEOUT=5000  
  
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
