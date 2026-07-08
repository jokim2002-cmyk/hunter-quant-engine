@echo off
setlocal
cd /d "%~dp0"
echo === HQE git status before tests ===
call ".\hqe_status.bat"
if errorlevel 1 exit /b %ERRORLEVEL%
echo.
echo === HQE full test suite ===
call ".\hqe_test.bat"
if errorlevel 1 exit /b %ERRORLEVEL%
echo.
echo === HQE git status after tests ===
call ".\hqe_status.bat"
exit /b %ERRORLEVEL%
