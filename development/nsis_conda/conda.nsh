!include LogicLib.nsh
!include Locate.nsh
!include FileFunc.nsh
!include StrStr.nsh


!define CONDA_URL https://repo.continuum.io/miniconda/Miniconda3-latest-Windows-x86_64.exe
var ROOT_ENV  # Conda root environment
var ENVS      # Path to all environments
var CONDA     # Conda executable


!macro InstallConda
  Call SetRootEnv

  # Downloading miniconda
  SetOutPath "$TEMP\conda_installer"
  DetailPrint "Downloading Conda ..."
  inetc::get /NOCANCEL /RESUME "" ${CONDA_URL} conda_setup.exe
  !insertmacro _FinishMessage "Conda download"

  # Installing miniconda
  DetailPrint "Running Conda installer ..."
  ExecDos::exec /DETAILED '"$TEMP\conda_installer\conda_setup.exe" /S /D=$ROOT_ENV"' "" ""
  !insertmacro _FinishMessage "Conda installation"

  # Clean up
  SetOutPath "$TEMP"
  RMDir /r "$TEMP\conda_installer"

!macroend


!macro UpdateConda
  Call SetRootEnv

  DetailPrint "Updating Conda ..."
  ExecDos::exec /DETAILED '"$CONDA" update -y -q conda' "" ""
  !insertmacro _FinishMessage "Conda update"
!macroend


!macro InstallOrUpdateConda
  Call SetRootEnv

  ${If} ${FileExists} "$ROOT_ENV\Scripts\conda.exe"
    !insertmacro UpdateConda
  ${Else}
    !insertmacro InstallConda
  ${EndIf}
!macroend


!macro InstallApp package args
  Call SetRootEnv

  DetailPrint "Downloading and installing application files ... (please be patient, this will take a while)"
  Push ${package}
  Call Prefix
  Pop $0
  StrCpy $INSTDIR "$0"  # So we can use `$INSTDIR` later, if needed

  ExecDos::exec /DETAILED '"$CONDA" create -y -q ${args} -p "$0" ${package}' "" ""
  !insertmacro _FinishMessage "Application files installation"
!macroend


!macro UpdateApp package args
  Call SetRootEnv

  DetailPrint "Downloading and installing application update ... (please be patient, this will take a while)"
  Push ${package}
  Call Prefix
  Pop $0
  StrCpy $INSTDIR "$0"  # So we can use `$INSTDIR` later, if needed

  ExecDos::exec /DETAILED '"$CONDA" install -y -q ${args} -p "$0" ${package}' "" ""
  !insertmacro _FinishMessage "Application update"
!macroend


!macro InstallOrUpdateApp package args
  Call SetRootEnv

  Push ${package}
  Call Prefix
  Pop $0

  ${If} ${FileExists} "$0"
    !insertmacro UpdateApp ${package} "${args}"
  ${Else}
    !insertmacro InstallApp ${package} "${args}"
  ${EndIf}
!macroend


!macro DeleteApp package
  Call un.SetRootEnv

  DetailPrint "Deleting application files ..."

  Push ${package}
  Call un.Prefix
  Pop $0
  ExecDos::exec /DETAILED '"$CONDA" remove -y -q -p "$0" --all --offline' "" ""
!macroend


!macro WriteUninstaller package
  # Creates an uninstaller in the package's environment

  Call SetRootEnv

  Push ${package}
  Call Prefix
  Pop $0

  WriteUninstaller "$0\uninstall.exe"
!macroend


!macro CreateShortcut title package cmd args ico
  DetailPrint "Creating Windows Start Menu shortcut ..."

  Push ${package}
  Call Prefix
  Pop $0  # Prefix

  # Copy icon into PREFIX\Menu
  SetOutPath "$0\Menu"
  File ${ico}

  Push $R1
  Push $R2
  ${Select} ${cmd}
    ${Case} "PY_CONSOLE"
      StrCpy $R1 "$0\python.exe"
      StrCpy $R2 "$0\${args}"
    ${Case} "PY_GUI"
      StrCpy $R1 "$0\pythonw.exe"
      StrCpy $R2 "$0\${args}"
    ${CaseElse}
      StrCpy $R1 "$0\${cmd}"
      StrCpy $R2 "${args}"
  ${EndSelect}

  SetOutPath "$PROFILE"  # Shortcut working dir
  CreateShortcut "$SMPROGRAMS\${title}.lnk" "$R1" "$R2" "$0\Menu\${ico}" 0 "" "" "Open ${title}"

  Pop $R2
  Pop $R1
!macroend


!macro DeleteShortcut title
  DetailPrint "Deleting Windows Start Menu shortcut ..."
  Delete "$SMPROGRAMS\${title}.lnk"
!macroend


!macro _FinishMessage action
  Pop $R0
  ${If} $R0 = 0
    DetailPrint "${action} successfully completed."
  ${Else}
    MessageBox MB_OK|MB_ICONEXCLAMATION "${action} could not be completed."
    DetailPrint "${action} could not be completed (exit code $R0)."
    Abort
  ${EndIf}
!macroend


!macro EnvName un
  Function ${un}EnvName
    # Return the app's environment name for a given package spec taken from the stack

    Pop $0  # Package spec, e.g. appdirs=1.4.0=py33_0
    StrCpy $1 0
    loop:
        IntOp $1 $1 + 1
        StrCpy $2 $0 1 $1
        StrCmp $2 '=' found
        StrCmp $2 '' stop loop
    found:
        IntOp $1 $1 + 0
    stop:
    StrCpy $2 $0 $1
    Push "_app_own_environment_$2"
  FunctionEnd
!macroend
!insertmacro EnvName ""
!insertmacro EnvName un.


!macro Prefix un
  Function ${un}Prefix
    # Return the prefix/path to the app's environment for a given package spec on the stack

    Call ${un}EnvName
    Pop $0  # Env name
    Push "$ENVS\$0"
  FunctionEnd
!macroend
!insertmacro Prefix ""
!insertmacro Prefix un.


!macro _SearchRootEnv un
  Function ${un}_SearchRootEnv
    # Return the conda root env by searching for conda.exe in the users's profile folder

    DetailPrint "Searching for conda..."
    Push $1
    Push $0
    Push $2
    Push $3
    Push $4
    Push $5
    Push $6
    Push $7

    ${locate::Open} "$PROFILE" "/L=F /M=conda.exe" $0
    ${IfNot} $0 = 0
      ${Do}
        ${locate::Find} $0 $1 $2 $3 $4 $5 $6

        ${If} $1 == ""
          DetailPrint "Cannot find conda"
          ${ExitDo}
        ${EndIf}

        # Skip package download folders
        ${${un}StrStr} $7 $1 "pkgs"
        ${If} $7 == ""
          DetailPrint "Conda found at $1"  # $1 == PREFIX\Scripts\conda.exe
          ${GetParent} $1 $1               # $1 == PREFIX\Scripts
          ${GetParent} $1 $1               # $1 == PREFIX
          ${ExitDo}
        ${EndIf}
      ${Loop}
    ${Else}
      DetailPrint "Error searching for conda"
    ${EndIf}

    ${locate::Close} $0
    ${locate::Unload}
    Pop $7
    Pop $6
    Pop $5
    Pop $4
    Pop $3
    Pop $2
    Pop $0
    Exch $1
  FunctionEnd
!macroend
!insertmacro _SearchRootEnv ""
!insertmacro _SearchRootEnv "un."


!macro SetRootEnv un
  Function ${un}SetRootEnv
    # Set the conda root environment prefix `$ROOT_ENV`, environments folder `$ENV` and conda
    # executable `$CONDA`

    # List of paths to search
    nsArray::SetList paths \
      "$LOCALAPPDATA\Continuum\Miniconda3" \
      "$LOCALAPPDATA\Continuum\Anaconda3" \
      "$LOCALAPPDATA\Continuum\Miniconda" \
      "$LOCALAPPDATA\Continuum\Anaconda" \
      "$PROFILE\Miniconda3" \
      "$PROFILE\Anaconda3" \
      "$PROFILE\Miniconda" \
      "$PROFILE\Anaconda" /end

    # If it already exists, assume we've run this function before
    ${If} ${FileExists} "$ROOT_ENV\Scripts\conda.exe"
      Return
    ${EndIf}

    # Try to find it in the list of known locations
    ${If} $ROOT_ENV == ""
      ${DoUntil} ${Errors}
        nsArray::Iterate paths
        Pop $0  # key
        Pop $1  # value
        ${If} ${FileExists} "$1\Scripts\conda.exe"
          StrCpy $ROOT_ENV $1
          DetailPrint "Conda root at standard prefix $ROOT_ENV"
          ${ExitDo}
        ${EndIf}
      ${Loop}
    ${EndIf}

    # If not found, search for conda executable in user profile folder
    ${If} $ROOT_ENV == ""
      Call ${un}_SearchRootEnv
      Pop $ROOT_ENV
      DetailPrint "Conda root found at prefix $ROOT_ENV"
    ${EndIf}

    # Else set it to the first default location (i.e. not installed yet)
    ${If} $ROOT_ENV == ""
      nsArray::Get paths 0
      Pop $ROOT_ENV
      DetailPrint "Conda root prefix set to default $ROOT_ENV"
    ${EndIf}

    StrCpy $ENVS  "$ROOT_ENV\envs"
    StrCpy $CONDA "$ROOT_ENV\Scripts\conda"
  FunctionEnd
!macroend
!insertmacro SetRootEnv ""
!insertmacro SetRootEnv un.