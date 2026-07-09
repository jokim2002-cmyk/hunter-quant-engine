param(
  [string]$Workspace = "D:\HQE_BACKTEST_RUNS\HQE_FORWARD_PAPER_VALIDATION_ACTIVE_20260708_204722",
  [string]$ShortcutName = "HQE App"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot
$Py = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Py)) { throw "Python venv not found: $Py" }

$Assets = Join-Path $RepoRoot "assets"
New-Item -ItemType Directory -Force $Assets | Out-Null
$Icon = Join-Path $Assets "HQE_PRODUCT_APP.ico"

& $Py scripts\hqe_product_app_icon.py --output $Icon
if ($LASTEXITCODE -ne 0) { throw "Icon generation failed" }

New-Item -ItemType Directory -Force $Workspace | Out-Null
$AppCmd = Join-Path $Workspace "HQE_PRODUCT_APP.cmd"
$AppCmdContent = @"
@echo off
title HQE Product App
cd /d "$RepoRoot"
"$Py" "scripts\hqe_product_app.py" --workspace "$Workspace"
"@
Set-Content -Path $AppCmd -Value $AppCmdContent -Encoding ASCII

# Install public license verify key if owner has generated it.
$OwnerPublic = "D:\HQE_PRODUCT_LICENSE_OWNER\hqe_license_public_key.json"
$ConfigDir = Join-Path $Workspace "HQE_PRODUCT_APP_CONFIG"
New-Item -ItemType Directory -Force $ConfigDir | Out-Null
if (Test-Path $OwnerPublic) {
  Copy-Item $OwnerPublic (Join-Path $ConfigDir "hqe_license_public_key.json") -Force
}

$Desktop = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $Desktop ($ShortcutName + ".lnk")
$Wsh = New-Object -ComObject WScript.Shell
$Shortcut = $Wsh.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $AppCmd
$Shortcut.WorkingDirectory = $RepoRoot
$Shortcut.IconLocation = $Icon
$Shortcut.Description = "HQE Product App - paper-only validation dashboard"
$Shortcut.Save()

Write-Host "HQE_PRODUCT_APP_INSTALLED"
Write-Host "Shortcut:" $ShortcutPath
Write-Host "Launcher:" $AppCmd
Write-Host "Icon:" $Icon
Write-Host "Workspace:" $Workspace
