@echo off
cd /d "%~dp0"
if exist "dist\CryptoDHLab\CryptoDHLab.exe" (
  start "" "dist\CryptoDHLab\CryptoDHLab.exe"
  exit /b 0
)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0run.ps1"
if errorlevel 1 pause
