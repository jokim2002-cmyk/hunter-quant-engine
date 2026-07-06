@echo off
setlocal
cd /d "%~dp0"

echo.
echo === HQE Paper Replay Journal Index ===
echo Prints local/generated fake paper replay journal index.
echo No broker. No live market data. No real orders.
echo.

set "INDEX_JSON=reports\paper_trading\journal\index.json"

if not exist "%INDEX_JSON%" (
    echo INFO: Replay journal index does not exist yet.
    echo Run hqe_paper_replay_journal.bat first to generate demo replay journal files.
    exit /b 1
)

type "%INDEX_JSON%"

echo.
echo.
echo Printed: %INDEX_JSON%
echo Paper PnL is simulation only.
endlocal
