@echo off
setlocal
cd /d "%~dp0"
echo === HQE repo snapshot ===
echo.
echo Branch:
git branch --show-current
if errorlevel 1 exit /b %ERRORLEVEL%
echo.
echo Latest commits:
git log --oneline -5
if errorlevel 1 exit /b %ERRORLEVEL%
echo.
echo Working tree status:
git status --short
exit /b %ERRORLEVEL%
