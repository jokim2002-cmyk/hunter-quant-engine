param(
    [string]$UserId = "jokim-local",
    [string]$Workspace = "D:\HQE_BACKTEST_RUNS\HQE_FORWARD_PAPER_VALIDATION_ACTIVE_20260708_204722",
    [string]$CredentialFile = "D:\HQE_BACKTEST_RUNS\HQE_LOCAL_LOGIN\hqe_local_login_credentials.json"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$LoginScript = Join-Path $RepoRoot "scripts\hqe_local_login_shell.py"

Write-Host "HQE Module 147 Local Login Shell"
Write-Host "Safety: paper-only, local gate only, no broker/order/API execution."
Write-Host "Credential file: $CredentialFile"
Write-Host "Workspace: $Workspace"
Write-Host ""

if (-not (Test-Path $CredentialFile)) {
    Write-Host "No local credential found. Creating salted-hash credential now."
    & $PythonExe $LoginScript --init --user-id $UserId --credential-file $CredentialFile --workspace $Workspace
    Write-Host ""
}

& $PythonExe $LoginScript --login --user-id $UserId --credential-file $CredentialFile --workspace $Workspace

