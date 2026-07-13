$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Exe = Join-Path $RepoRoot "dist\HunterQuantEngine.exe"
$Pythonw = Join-Path $RepoRoot ".venv\Scripts\pythonw.exe"
$AppScript = Join-Path $RepoRoot "scripts\hqe_product_app_v2.py"
$Desktop = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $Desktop "Hunter Quant Engine.lnk"

if (Test-Path -LiteralPath $Exe) {
    $TargetPath = $Exe
    $Arguments = ""
} else {
    if (-not (Test-Path -LiteralPath $Pythonw)) {
        throw "HQE pythonw.exe is missing: $Pythonw"
    }
    if (-not (Test-Path -LiteralPath $AppScript)) {
        throw "HQE app entry is missing: $AppScript"
    }
    $TargetPath = $Pythonw
    $Arguments = '"' + $AppScript + '"'
}

$Shell = New-Object -ComObject WScript.Shell
$Shortcut = $Shell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $TargetPath
$Shortcut.Arguments = $Arguments
$Shortcut.WorkingDirectory = $RepoRoot
$Shortcut.Description = "Hunter Quant Engine - Paper/Data Research App"

$IconCandidates = @(
    (Join-Path $RepoRoot "assets\HQE_PRODUCT_APP.ico"),
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
Write-Output "TARGET: $TargetPath"
Write-Output "REAL MONEY: NO | REAL ORDERS: NO | BROKER EXECUTION: NO"
