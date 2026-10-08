@echo off
rem GPO computer startup script: install Sysmon or apply the current sysmon.xml.
rem Prepared by deploy/endpoints/windows/prepare-share.ps1, which replaces FILESERVER_SHARE.
rem Idempotent: installs when missing, otherwise re-applies the config only when it changed.
setlocal

set "SHARE=FILESERVER_SHARE\sysmon"
set "EXE=%SHARE%\Sysmon64.exe"
set "CFG=%SHARE%\sysmon.xml"
set "LOCAL=C:\ProgramData\esm\sysmon.xml"

if not exist "%EXE%" (echo [ERR] missing %EXE% & exit /b 1)
if not exist "%CFG%" (echo [ERR] missing %CFG% & exit /b 2)
if not exist "C:\ProgramData\esm" mkdir "C:\ProgramData\esm"

sc query sysmon64 >nul 2>&1
if errorlevel 1 (
  echo [INFO] installing Sysmon
  "%EXE%" -accepteula -i "%CFG%"
  if errorlevel 1 (echo [ERR] Sysmon installation failed & exit /b 3)
  copy /Y "%CFG%" "%LOCAL%" >nul
  echo [OK] Sysmon installed
  exit /b 0
)

fc /b "%CFG%" "%LOCAL%" >nul 2>&1
if errorlevel 1 (
  echo [INFO] applying the updated Sysmon configuration
  "%EXE%" -c "%CFG%"
  copy /Y "%CFG%" "%LOCAL%" >nul
) else (
  echo [OK] Sysmon configuration is up to date
)
exit /b 0
