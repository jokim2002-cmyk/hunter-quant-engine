@echo off
setlocal
cd /d "%~dp0"
echo HQE safe local shortcuts
echo ========================
echo.
echo Daily checks:
echo   .\hqe_quick_check.bat       - git status, full tests, git status
echo   .\hqe_daily.bat             - quick check, demo, open report
echo   .\hqe_test.bat              - full pytest suite
echo   .\hqe_status.bat            - git status --short
echo   .\hqe_snapshot.bat          - branch, recent commits, git status
echo.
echo Paper trading demo:
echo   .\hqe_paper_demo.bat        - run safe paper demo
echo   .\hqe_paper_report.bat      - open latest generated paper report
echo   .\hqe_paper_demo_report.bat - run demo and open report
echo   .\hqe_paper_replay_journal.bat - run fake paper replay and save journal bundle
echo   .\hqe_paper_replay_journal_folder.bat - open replay journal folder
echo   .\hqe_paper_replay_journal_summary.bat - print replay journal summary
echo   .\hqe_paper_replay_journal_index.bat - print replay journal index
echo   .\hqe_paper_replay_journal_all.bat - run replay journal, print summary/index, open folder
echo   .\hqe_paper_folder.bat      - open paper report folder
echo   .\hqe_paper_report_text.bat - print paper report in terminal
echo.
echo Docs:
echo   README_SHORTCUTS.md
echo   docs\PAPER_TRADING_DEMO_CLI.md
echo.
echo Safety:
echo   paper demo only, no broker/FYERS, no live data, no real orders
exit /b 0
