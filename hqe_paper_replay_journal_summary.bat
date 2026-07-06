@echo off
setlocal
cd /d "%~dp0"

echo.
echo === HQE Paper Replay Journal Summary ===
echo Prints local/generated fake paper replay journal summary.
echo No broker. No live market data. No real orders.
echo.

set "SUMMARY_JSON=reports\paper_trading\journal\demo-replay-journal\summary.json"

if not exist "%SUMMARY_JSON%" (
    echo INFO: Replay journal summary does not exist yet.
    echo Run hqe_paper_replay_journal.bat first to generate demo replay journal files.
    exit /b 1
)

type "%SUMMARY_JSON%"

echo.
echo.
echo Printed: %SUMMARY_JSON%
echo Paper PnL is simulation only.
endlocal
