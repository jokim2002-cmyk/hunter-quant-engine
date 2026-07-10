from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

VERSION = "HQE_APP_V2_INSTALLER_PACK_V1"
DEFAULT_APP_VERSION = "2.0.0-owner-preview.1"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_head(root: Path) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout.strip()


def copy_release_tree(source: Path, target: Path) -> None:
    if not source.exists():
        raise FileNotFoundError(f"Release directory not found: {source}")

    def ignore(_directory: str, names: List[str]) -> List[str]:
        blocked = {"__pycache__", ".pytest_cache", ".mypy_cache"}
        return [
            name
            for name in names
            if name in blocked or name.endswith(".pyc")
        ]

    shutil.copytree(source, target, dirs_exist_ok=True, ignore=ignore)


def installer_ps1(app_version: str, repo_hint: str, workspace_hint: str) -> str:
    return f'''$ErrorActionPreference = "Stop"

$PackageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProductRoot = Join-Path $env:LOCALAPPDATA "HunterQuantEngine"
$VersionsRoot = Join-Path $ProductRoot "AppV2"
$InstallRoot = Join-Path $VersionsRoot "{app_version}"
$CurrentFile = Join-Path $ProductRoot "CURRENT_VERSION.txt"
$Desktop = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $Desktop "Hunter Quant Engine.lnk"

$RepoHint = "{repo_hint}"
$WorkspaceHint = "{workspace_hint}"

Write-Host "Installing Hunter Quant Engine App V2 {app_version}..."
Write-Host "Install root: $InstallRoot"

New-Item -ItemType Directory -Force -Path $InstallRoot | Out-Null

Get-ChildItem -LiteralPath $PackageRoot -Force |
    Where-Object {{ $_.Name -notin @(
        "INSTALL_HQE_APP_V2.ps1",
        "INSTALL_HQE_APP_V2.cmd",
        "UNINSTALL_HQE_APP_V2.ps1",
        "UNINSTALL_HQE_APP_V2.cmd"
    ) }} |
    ForEach-Object {{
        Copy-Item -LiteralPath $_.FullName -Destination $InstallRoot -Recurse -Force
    }}

$LaunchCmd = Join-Path $InstallRoot "LAUNCH_HQE_APP_V2.cmd"
if (-not (Test-Path $LaunchCmd)) {{
    throw "Installed launcher missing: $LaunchCmd"
}}

Set-Content -Path $CurrentFile -Value "{app_version}" -Encoding UTF8

$Shell = New-Object -ComObject WScript.Shell
$Shortcut = $Shell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $LaunchCmd
$Shortcut.WorkingDirectory = $InstallRoot
$IconPath = Join-Path $InstallRoot "assets\HQE_PRODUCT_APP.ico"
if (Test-Path $IconPath) {{
    $Shortcut.IconLocation = $IconPath
}}
$Shortcut.Description = "Hunter Quant Engine App V2 - Paper/Data Only"
$Shortcut.Save()

$InstallEvidence = @{{
    version = "{app_version}"
    installed_at_utc = [DateTime]::UtcNow.ToString("o")
    install_root = $InstallRoot
    desktop_shortcut = $ShortcutPath
    repo_hint = $RepoHint
    workspace_hint = $WorkspaceHint
    real_money_enabled = $false
    real_orders_enabled = $false
    broker_execution_enabled = $false
    auto_trading_enabled = $false
}} | ConvertTo-Json -Depth 5

Set-Content -Path (Join-Path $InstallRoot "HQE_APP_V2_INSTALL_EVIDENCE.json") -Value $InstallEvidence -Encoding UTF8

Write-Host ""
Write-Host "HQE APP V2 INSTALL: PASS" -ForegroundColor Green
Write-Host "Desktop shortcut: $ShortcutPath"
Write-Host "Real money: NO"
Write-Host "Real orders: NO"
Write-Host "Broker execution: NO"
Write-Host "Auto trading: NO"
'''


def uninstall_ps1(app_version: str) -> str:
    return f'''$ErrorActionPreference = "Stop"

$ProductRoot = Join-Path $env:LOCALAPPDATA "HunterQuantEngine"
$InstallRoot = Join-Path (Join-Path $ProductRoot "AppV2") "{app_version}"
$CurrentFile = Join-Path $ProductRoot "CURRENT_VERSION.txt"
$Desktop = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $Desktop "Hunter Quant Engine.lnk"

if (Test-Path $ShortcutPath) {{
    Remove-Item -LiteralPath $ShortcutPath -Force
}}

if (Test-Path $InstallRoot) {{
    Remove-Item -LiteralPath $InstallRoot -Recurse -Force
}}

if (Test-Path $CurrentFile) {{
    $Current = (Get-Content $CurrentFile -Raw).Trim()
    if ($Current -eq "{app_version}") {{
        Remove-Item -LiteralPath $CurrentFile -Force
    }}
}}

Write-Host "HQE APP V2 UNINSTALL: PASS" -ForegroundColor Green
Write-Host "Removed version: {app_version}"
'''


def launch_cmd(repo_hint: str, workspace_hint: str) -> str:
    return (
        "@echo off\n"
        "setlocal EnableExtensions\n"
        "cd /d %~dp0\n"
        f"set \"HQE_REPO_HINT={repo_hint}\"\n"
        f"set \"HQE_WORKSPACE={workspace_hint}\"\n"
        "set \"HQE_PYTHON=\"\n"
        "if exist \"%HQE_REPO_HINT%\\.venv\\Scripts\\python.exe\" set \"HQE_PYTHON=%HQE_REPO_HINT%\\.venv\\Scripts\\python.exe\"\n"
        "if not defined HQE_PYTHON (\n"
        "  echo HQE Python environment not found.\n"
        "  echo Expected: %HQE_REPO_HINT%\\.venv\\Scripts\\python.exe\n"
        "  pause\n"
        "  exit /b 1\n"
        ")\n"
        "\"%HQE_PYTHON%\" \"%~dp0scripts\\hqe_app_v2_preflight.py\" --workspace \"%HQE_WORKSPACE%\" --repo-root \"%HQE_REPO_HINT%\"\n"
        "if errorlevel 1 (\n"
        "  echo.\n"
        "  echo HQE preflight failed.\n"
        "  pause\n"
        "  exit /b 1\n"
        ")\n"
        "\"%HQE_PYTHON%\" \"%~dp0scripts\\hqe_product_app_v2.py\" --workspace \"%HQE_WORKSPACE%\" --user-id \"hqe-user\" --symbol \"NSE:NIFTY50-INDEX\"\n"
        "endlocal\n"
    )


def wrapper_cmd(script_name: str) -> str:
    return (
        "@echo off\n"
        "powershell.exe -NoProfile -ExecutionPolicy Bypass "
        f"-File \"%~dp0{script_name}\"\n"
        "if errorlevel 1 pause\n"
    )


def package_files(root: Path) -> Iterable[Path]:
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.name != "HQE_APP_V2_INSTALLER_MANIFEST.json"
    )


def build_installer_pack(
    release_dir: Path,
    output_dir: Path,
    app_version: str,
    repo_hint: str,
    workspace_hint: str,
) -> Dict[str, Any]:
    package_dir = output_dir / f"HQE_APP_V2_{app_version}_OWNER_INSTALLER"

    if package_dir.exists():
        shutil.rmtree(package_dir)

    package_dir.mkdir(parents=True, exist_ok=True)
    copy_release_tree(release_dir, package_dir)

    generated = {
        "INSTALL_HQE_APP_V2.ps1": installer_ps1(app_version, repo_hint, workspace_hint),
        "INSTALL_HQE_APP_V2.cmd": wrapper_cmd("INSTALL_HQE_APP_V2.ps1"),
        "UNINSTALL_HQE_APP_V2.ps1": uninstall_ps1(app_version),
        "UNINSTALL_HQE_APP_V2.cmd": wrapper_cmd("UNINSTALL_HQE_APP_V2.ps1"),
        "LAUNCH_HQE_APP_V2.cmd": launch_cmd(repo_hint, workspace_hint),
    }

    for name, content in generated.items():
        (package_dir / name).write_text(content, encoding="utf-8")

    version_payload = {
        "app_name": "Hunter Quant Engine",
        "app_version": app_version,
        "package_version": VERSION,
        "repo_head": git_head(repo_root()),
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "repo_hint": repo_hint,
        "workspace_hint": workspace_hint,
        "install_scope": "CURRENT_USER_NO_ADMIN",
        "real_money_enabled": False,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "profitability_claim": False,
    }

    (package_dir / "HQE_APP_V2_VERSION.json").write_text(
        json.dumps(version_payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    manifest_items = [
        {
            "path": str(path.relative_to(package_dir)).replace("\\", "/"),
            "size_bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
        for path in package_files(package_dir)
    ]

    payload = {
        **version_payload,
        "installer_status": "PASS",
        "package_dir": str(package_dir),
        "file_count": len(manifest_items),
        "files": manifest_items,
    }

    manifest = package_dir / "HQE_APP_V2_INSTALLER_MANIFEST.json"
    manifest.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    payload["manifest"] = str(manifest)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Build HQE App V2 owner installer pack")
    parser.add_argument("--release-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--app-version", default=DEFAULT_APP_VERSION)
    parser.add_argument("--repo-hint", required=True)
    parser.add_argument("--workspace-hint", required=True)
    args = parser.parse_args()

    payload = build_installer_pack(
        Path(args.release_dir),
        Path(args.output_dir),
        args.app_version,
        args.repo_hint,
        args.workspace_hint,
    )

    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
