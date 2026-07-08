@echo off
setlocal
cd /d "%~dp0"
set REPORT_FILE=reports\paper_trading\report.txt
if not exist "%REPORT_FILE%" (
  echo Paper report not found: %REPORT_FILE%
  echo Run hqe_paper_demo.bat first.
  exit /b 1
)
start "" "%REPORT_FILE%"
exit /b %ERRORLEVEL%
