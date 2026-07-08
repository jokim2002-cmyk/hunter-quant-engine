@echo off
setlocal

call "%~dp0scripts\paper_trading\hqe_safe_paper_runner_execution_review_phase_close_pack.bat" %*
exit /b %ERRORLEVEL%
