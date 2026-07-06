@echo off
setlocal
cd /d "%~dp0"
set REPORT_DIR=reports\paper_trading
if not exist "%REPORT_DIR%" mkdir "%REPORT_DIR%"
start "" "%REPORT_DIR%"
exit /b %ERRORLEVEL%
