@echo off
setlocal
cd /d "D:\Hunter_Quant_Engine_PC_TRANSFER"
start "" "D:\Hunter_Quant_Engine_PC_TRANSFER\.venv\Scripts\python.exe" "D:\Hunter_Quant_Engine_PC_TRANSFER\scripts\hqe_product_app_v2.py" --workspace "D:\HQE_BACKTEST_RUNS\HQE_FORWARD_PAPER_VALIDATION_ACTIVE_20260708_204722" --user-id "hqe-user" --symbol "NSE:NIFTY50-INDEX"
endlocal
