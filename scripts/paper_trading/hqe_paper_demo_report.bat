@echo off
setlocal
cd /d "%~dp0"
call ".\hqe_paper_demo.bat"
if errorlevel 1 exit /b %ERRORLEVEL%
call ".\hqe_paper_report.bat"
exit /b %ERRORLEVEL%
