param(
  [string]$RepoRoot = "D:\Hunter_Quant_Engine_PC_TRANSFER",
  [string]$Workspace = "D:\HQE_BACKTEST_RUNS\HQE_FORWARD_PAPER_VALIDATION_ACTIVE_20260708_204722"
)

$ErrorActionPreference = "Stop"

Write-Host "HQE NEW PC INSTALLER"
Write-Host "Safety: PAPER ONLY / DATA ONLY / NO REAL ORDERS / NO BROKER EXECUTION"

if (-not (Test-Path $RepoRoot)) {
  throw "RepoRoot not found. Copy or clone Hunter_Quant_Engine_PC_TRANSFER to: $RepoRoot"
}

Set-Location $RepoRoot

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
  py -m venv .venv
}

$Py = Join-Path $RepoRoot ".venv\Scripts\python.exe"
& $Py -m pip install --upgrade pip

if (Test-Path "requirements.txt") {
  & $Py -m pip install -r requirements.txt
}

New-Item -ItemType Directory -Force $Workspace | Out-Null

powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\INSTALL_HQE_PRODUCT_APP_LOCAL.ps1" -Workspace $Workspace

Write-Host "HQE_NEW_PC_INSTALL_COMPLETE"
Write-Host "Next: open Desktop shortcut 'HQE App', copy Machine ID, send it to owner, activate with user key."
