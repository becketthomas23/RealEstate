@echo off
setlocal

REM Double-click launcher for Windows Explorer. The PowerShell script remains
REM the source of truth; this wrapper only makes its execution policy explicit.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start-local.ps1"
if errorlevel 1 (
    echo.
    echo The CRE Underwriting App did not start. Read the error above, then press any key to close this window.
    pause >nul
)
