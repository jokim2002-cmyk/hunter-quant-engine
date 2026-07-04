@echo off
cd /d "%~dp0"

echo.
echo ================================
echo HQE PULL + TEST
echo ================================

git pull --ff-only
if errorlevel 1 goto error

if exist ".venv\Scripts\python.exe" (
    .\.venv\Scripts\python.exe -m pytest
) else (
    py -m pytest
)

if errorlevel 1 goto error

echo.
echo Done. HQE is synced and tests passed.
pause
exit /b 0

:error
echo.
echo Something failed. Check output above.
pause
exit /b 1
