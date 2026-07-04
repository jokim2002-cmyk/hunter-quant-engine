@echo off
cd /d "%~dp0"

echo.
echo ================================
echo HQE TEST + COMMIT + PUSH
echo ================================

if exist ".venv\Scripts\python.exe" (
    .\.venv\Scripts\python.exe -m pytest
) else (
    py -m pytest
)

if errorlevel 1 goto error

set /p COMMIT_MSG=Enter commit message: 

if "%COMMIT_MSG%"=="" (
    echo Commit message is required.
    pause
    exit /b 1
)

git status --short
git add .
git commit -m "%COMMIT_MSG%"
if errorlevel 1 goto error

git push
if errorlevel 1 goto error

echo.
echo Done. Changes pushed to GitHub.
pause
exit /b 0

:error
echo.
echo Something failed. Check output above.
pause
exit /b 1
