@echo off
cd /d "%~dp0"

echo.
echo ================================
echo HQE STATUS
echo ================================
git status --short
echo.
git log --oneline -5
echo.
git remote -v

pause
