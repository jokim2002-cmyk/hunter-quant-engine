@echo off
cd /d "%~dp0"
.\.venv\Scripts\python.exe scripts\refresh_fyers_token.py
pause
