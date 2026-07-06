@echo off
setlocal
cd /d "%~dp0"

echo.
echo === HQE Paper Replay Journal All-In-One ===
echo Runs fake paper replay, prints summary, lists runs, and opens the journal folder.
echo No broker. No live market data. No real orders.
echo.

call hqe_paper_replay_journal.bat
if errorlevel 1 exit /b 1

echo.
call hqe_paper_replay_journal_summary.bat
if errorlevel 1 exit /b 1

echo.
call hqe_paper_replay_journal_runs.bat
if errorlevel 1 exit /b 1

echo.
call hqe_paper_replay_journal_folder.bat
if errorlevel 1 exit /b 1

echo.
echo === Paper replay journal workflow complete ===
echo Paper PnL is simulation only.
endlocal
