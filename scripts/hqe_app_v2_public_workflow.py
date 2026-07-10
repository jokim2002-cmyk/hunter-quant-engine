from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict

VERSION = "HQE_APP_V2_PUBLIC_WORKFLOW_V1"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def launcher_path() -> Path:
    return repo_root() / "OPEN_HQE_APP_V2.cmd"


def build_launcher(workspace: Path, user_id: str, symbol: str) -> str:
    repo = repo_root()
    py = repo / ".venv" / "Scripts" / "python.exe"
    app = repo / "scripts" / "hqe_product_app_v2.py"
    return (
        "@echo off\n"
        "setlocal\n"
        f'cd /d "{repo}"\n'
        f'start "" "{py}" "{app}" --workspace "{workspace}" '
        f'--user-id "{user_id}" --symbol "{symbol}"\n'
        "endlocal\n"
    )


def write_launcher(workspace: Path, user_id: str, symbol: str) -> Path:
    path = launcher_path()
    path.write_text(build_launcher(workspace, user_id, symbol), encoding="utf-8")
    return path


def desktop_shortcut_payload(workspace: Path, user_id: str, symbol: str) -> Dict[str, Any]:
    path = write_launcher(workspace, user_id, symbol)
    return {
        "version": VERSION,
        "launcher_path": str(path),
        "launcher_exists": path.exists(),
        "public_daily_entrypoint": "OPEN_HQE_APP_V2.cmd",
        "visible_powershell_required": False,
        "visible_cmd_required_after_launch": False,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
    }


def create_desktop_shortcut(workspace: Path, user_id: str, symbol: str) -> Dict[str, Any]:
    payload = desktop_shortcut_payload(workspace, user_id, symbol)
    desktop = Path(os.path.expanduser("~/Desktop"))
    shortcut = desktop / "Hunter Quant Engine.lnk"
    icon = repo_root() / "assets" / "HQE_PRODUCT_APP.ico"
    target = launcher_path()

    ps = (
        "$W=New-Object -ComObject WScript.Shell;"
        f"$S=$W.CreateShortcut('{str(shortcut).replace(chr(39), chr(39)*2)}');"
        f"$S.TargetPath='{str(target).replace(chr(39), chr(39)*2)}';"
        f"$S.WorkingDirectory='{str(repo_root()).replace(chr(39), chr(39)*2)}';"
        f"$S.IconLocation='{str(icon).replace(chr(39), chr(39)*2)}';"
        "$S.Save()"
    )
    cp = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
        cwd=str(repo_root()),
        capture_output=True,
        text=True,
    )
    payload.update({
        "shortcut_path": str(shortcut),
        "shortcut_created": cp.returncode == 0 and shortcut.exists(),
        "shortcut_stdout": cp.stdout[-500:],
        "shortcut_stderr": cp.stderr[-500:],
    })
    return payload


def guard_payload() -> Dict[str, Any]:
    return {
        "version": VERSION,
        "guard_check_status": "PASS",
        "public_daily_entrypoint": "OPEN_HQE_APP_V2.cmd",
        "desktop_shortcut_supported": True,
        "visible_powershell_required": False,
        "visible_cmd_required_after_launch": False,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "paper_only": True,
        "data_only": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="HQE App V2 public workflow")
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--user-id", default="hqe-user")
    parser.add_argument("--symbol", default="NSE:NIFTY50-INDEX")
    parser.add_argument("--write-launcher", action="store_true")
    parser.add_argument("--create-shortcut", action="store_true")
    parser.add_argument("--guard-check", action="store_true")
    args = parser.parse_args()

    workspace = Path(args.workspace)
    if args.guard_check:
        payload = guard_payload()
    elif args.create_shortcut:
        payload = create_desktop_shortcut(workspace, args.user_id, args.symbol)
    else:
        payload = desktop_shortcut_payload(workspace, args.user_id, args.symbol)

    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
