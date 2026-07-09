param(
  [string]$OutputDir = "D:\HQE_PRODUCT_RELEASES"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot
New-Item -ItemType Directory -Force $OutputDir | Out-Null
$Zip = Join-Path $OutputDir ("HQE_PRODUCT_APP_RELEASE_" + (Get-Date -Format "yyyyMMdd_HHmmss") + ".zip")

$Include = @(
  "scripts",
  "tests",
  "docs",
  "assets",
  "README.md",
  "requirements.txt"
)

$Temp = Join-Path $env:TEMP ("HQE_PRODUCT_RELEASE_" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Force $Temp | Out-Null

foreach ($Item in $Include) {
  if (Test-Path $Item) {
    Copy-Item $Item -Destination $Temp -Recurse -Force
  }
}

Compress-Archive -Path (Join-Path $Temp "*") -DestinationPath $Zip -Force
Remove-Item $Temp -Recurse -Force

Write-Host "HQE_PRODUCT_RELEASE_ZIP_READY"
Write-Host $Zip
