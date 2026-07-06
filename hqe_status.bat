@echo off
setlocal
cd /d "%~dp0"
git status --short
exit /b %ERRORLEVEL%
