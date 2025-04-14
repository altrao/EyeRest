; EyeRest App Installer
; NSIS script for Windows installer

!define APP_NAME "EyeRest"
!define APP_VERSION "1.0"
!define APP_PUBLISHER "EyeRest"
!define APP_WEB_SITE "https://github.com/altrao/EyeRest"
!define APP_EXE "EyeRest.exe"

; Compression
SetCompressor /SOLID lzma
SetCompressorDictSize 32

; Modern UI
!include "MUI2.nsh"

; Installer attributes
Name "${APP_NAME}"
OutFile "EyeRestSetup.exe"
InstallDir "$PROGRAMFILES\${APP_NAME}"
InstallDirRegKey HKLM "Software\${APP_NAME}" "Install_Dir"
RequestExecutionLevel admin

; Interface settings
!define MUI_ABORTWARNING
!define MUI_ICON "..\icon.ico"
!define MUI_UNICON "..\icon.ico"

; Pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "..\LICENSE.txt"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

; Languages
!insertmacro MUI_LANGUAGE "English"

; Installer sections
Section "Main Application" SecMain
  SectionIn RO
  
  SetOutPath "$INSTDIR"
  File ".\dist\EyeRest.exe"
  File "..\icon.ico"
  
  ; Create shortcuts
  CreateDirectory "$SMPROGRAMS\${APP_NAME}"
  CreateShortcut "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}" "" "$INSTDIR\icon.ico"
  CreateShortcut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}" "" "$INSTDIR\icon.ico"
  
  ; Write registry keys
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "DisplayName" "${APP_NAME}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "UninstallString" '"$INSTDIR\uninstall.exe"'
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "DisplayIcon" '"$INSTDIR\icon.ico"'
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "DisplayVersion" "${APP_VERSION}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "Publisher" "${APP_PUBLISHER}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "URLInfoAbout" "${APP_WEB_SITE}"
  
  ; Create uninstaller
  WriteUninstaller "$INSTDIR\uninstall.exe"
SectionEnd

; Uninstaller section
Section "Uninstall"
  ; Remove files
  RMDir /r "$INSTDIR"
  
  ; Remove shortcuts
  Delete "$DESKTOP\${APP_NAME}.lnk"
  RMDir /r "$SMPROGRAMS\${APP_NAME}"
  
  ; Remove registry keys
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}"
  DeleteRegKey HKLM "Software\${APP_NAME}"
SectionEnd

; Functions
Function .onInit
  ; Check if already installed
  ReadRegStr $R0 HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "UninstallString"
  StrCmp $R0 "" done
  
  MessageBox MB_OKCANCEL|MB_ICONEXCLAMATION \
    "${APP_NAME} is already installed. $\n$\nClick `OK` to remove the \
    previous version or `Cancel` to cancel this upgrade." \
    IDOK uninst
  Abort
  
  uninst:
    ClearErrors
    ExecWait '$R0 _?=$INSTDIR'
    
    IfErrors no_remove_uninstaller
      Delete $R0
      RMDir $INSTDIR
    no_remove_uninstaller:
    
  done:
FunctionEnd
