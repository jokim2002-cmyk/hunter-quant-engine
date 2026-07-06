@echo off
setlocal
cd /d "%~dp0"
echo === HQE daily workflow ===
echo.
echo Step 1: quick local check
call ".\hqe_quick_check.bat"
if errorlevel 1 exit /b %ERRORLEVEL%
echo.
echo Step 2: paper demo and report
call ".\hqe_paper_demo_report.bat"
exit /b %ERRORLEVEL%
