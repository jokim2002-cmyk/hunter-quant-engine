@echo off
setlocal
cd /d "D:\Hunter_Quant_Engine_PC_TRANSFER"
start "" "D:\Hunter_Quant_Engine_PC_TRANSFER\.venv\Scripts\python.exe" "D:\Hunter_Quant_Engine_PC_TRANSFER\scripts\hqe_product_app_v2.py" --workspace "C:\Users\Admin\AppData\Local\Temp\pytest-of-Admin\pytest-643\test_launcher_written0" --user-id "hqe-user" --symbol "NSE:NIFTY50-INDEX"
endlocal
