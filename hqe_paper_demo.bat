@echo off
setlocal
cd /d "%~dp0"
.\.venv\Scripts\python.exe -m src.paper_trading.paper_trading_demo_cli
exit /b %ERRORLEVEL%
