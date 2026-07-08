@echo off
setlocal

call "%~dp0scripts\paper_trading\hqe_safe_improved_recorded_data_paper_runner_execution_plan_pack.bat" %*
exit /b %ERRORLEVEL%
