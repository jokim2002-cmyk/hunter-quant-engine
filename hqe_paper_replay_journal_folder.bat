@echo off
setlocal
cd /d "%~dp0"

echo.
echo === HQE Paper Replay Journal Folder ===
echo Opens local/generated fake paper replay journal folder.
echo No broker. No live market data. No real orders.
echo.

set "JOURNAL_DIR=reports\paper_trading\journal\demo-replay-journal"

if not exist "%JOURNAL_DIR%" (
    echo INFO: Journal folder does not exist yet.
    echo Run hqe_paper_replay_journal.bat first to generate demo replay journal files.
    echo Creating folder now so it can be opened safely.
    mkdir "%JOURNAL_DIR%"
)

start "" "%JOURNAL_DIR%"

echo Opened: %JOURNAL_DIR%
endlocal
