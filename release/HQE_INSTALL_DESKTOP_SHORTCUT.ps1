$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Pythonw = Join-Path $RepoRoot ".venv\Scripts\pythonw.exe"
$AppScript = Join-Path $RepoRoot "scripts\hqe_product_app_v2.py"
$Desktop = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $Desktop "Hunter Quant Engine.lnk"

if (-not (Test-Path -LiteralPath $Pythonw)) {
    throw "HQE pythonw.exe is missing: $Pythonw"
}
if (-not (Test-Path -LiteralPath $AppScript)) {
    throw "HQE app entry is missing: $AppScript"
}

$Shell = New-Object -ComObject WScript.Shell
$Shortcut = $Shell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $Pythonw
$Shortcut.Arguments = '"' + $AppScript + '"'
$Shortcut.WorkingDirectory = $RepoRoot
$Shortcut.Description = "Hunter Quant Engine - Paper/Data Research App"

$IconCandidates = @(
    (Join-Path $RepoRoot "assets\hqe.ico"),
    (Join-Path $RepoRoot "assets\app.ico"),
    (Join-Path $RepoRoot "assets\icon.ico")
)

foreach ($IconPath in $IconCandidates) {
    if (Test-Path -LiteralPath $IconPath) {
        $Shortcut.IconLocation = $IconPath
        break
    }
}

$Shortcut.Save()

if (-not (Test-Path -LiteralPath $ShortcutPath)) {
    throw "Desktop shortcut was not created: $ShortcutPath"
}

Write-Output "PASS: Desktop shortcut installed: $ShortcutPath"
Write-Output "REAL MONEY: NO | REAL ORDERS: NO | BROKER EXECUTION: NO"
