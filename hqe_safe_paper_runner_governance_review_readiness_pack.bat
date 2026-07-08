@echo off
setlocal

call "%~dp0scripts\paper_trading\hqe_safe_paper_runner_governance_review_readiness_pack.bat" %*
exit /b %ERRORLEVEL%
