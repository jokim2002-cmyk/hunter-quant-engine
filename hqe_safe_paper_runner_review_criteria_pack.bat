@echo off
setlocal

call "%~dp0scripts\paper_trading\hqe_safe_paper_runner_review_criteria_pack.bat" %*
exit /b %ERRORLEVEL%
