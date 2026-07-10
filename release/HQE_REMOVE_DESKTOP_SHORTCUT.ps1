$ErrorActionPreference = "Stop"

$Desktop = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $Desktop "Hunter Quant Engine.lnk"

if (Test-Path $ShortcutPath) {
    Remove-Item $ShortcutPath -Force
    Write-Output "PASS: Desktop shortcut removed."
} else {
    Write-Output "PASS: Desktop shortcut was not installed."
}
