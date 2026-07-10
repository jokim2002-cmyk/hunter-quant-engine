from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

VERSION = "HQE_APP_V2_RELEASE_PACK_V2"

INCLUDE_FILES = [
    "OPEN_HQE_APP_V2.cmd",
    "assets/HQE_PRODUCT_APP.ico",
    "scripts/hqe_product_app_v2.py",
    "scripts/hqe_broker_connect_center.py",
    "scripts/hqe_hidden_paper_watch_supervisor.py",
    "scripts/hqe_app_v2_license_activation.py",
    "scripts/hqe_app_v2_preflight.py",
]

INCLUDE_DIRS = ["src", "scripts"]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def git_head(root: Path) -> str:
    cp = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    )
    return cp.stdout.strip()


def copy_tree_filtered(source: Path, target: Path) -> None:
    def ignore(_dir: str, names: List[str]) -> List[str]:
        blocked = {"__pycache__", ".pytest_cache", ".mypy_cache"}
        return [name for name in names if name in blocked or name.endswith(".pyc")]

    shutil.copytree(source, target, dirs_exist_ok=True, ignore=ignore)


def build_pack(output_dir: Path, workspace_hint: str, repo_hint: str = "") -> Dict[str, Any]:
    root = repo_root()
    release_dir = output_dir / "HQE_APP_V2_RELEASE"

    if release_dir.exists():
        shutil.rmtree(release_dir)

    release_dir.mkdir(parents=True, exist_ok=True)
    copied: List[Path] = []

    for rel in INCLUDE_FILES:
        source = root / rel
        if not source.exists():
            raise FileNotFoundError(f"Missing required release file: {source}")
        target = release_dir / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied.append(target)

    for rel in INCLUDE_DIRS:
        source = root / rel
        if source.exists():
            target = release_dir / rel
            copy_tree_filtered(source, target)
            copied.extend(path for path in target.rglob("*") if path.is_file())

    effective_repo_hint = repo_hint.strip() or str(root)
    launcher = release_dir / "START_HQE_APP_V2.cmd"
    launcher.write_text(
        "@echo off\n"
        "setlocal EnableExtensions\n"
        "cd /d %~dp0\n"
        f"set \"HQE_REPO_HINT={effective_repo_hint}\"\n"
        f"set \"HQE_WORKSPACE={workspace_hint}\"\n"
        "set \"HQE_PYTHON=\"\n"
        "if exist \"%HQE_REPO_HINT%\\.venv\\Scripts\\python.exe\" set \"HQE_PYTHON=%HQE_REPO_HINT%\\.venv\\Scripts\\python.exe\"\n"
        "if not defined HQE_PYTHON if exist \"%~dp0.venv\\Scripts\\python.exe\" set \"HQE_PYTHON=%~dp0.venv\\Scripts\\python.exe\"\n"
        "if not defined HQE_PYTHON if exist \"%~dp0..\\.venv\\Scripts\\python.exe\" set \"HQE_PYTHON=%~dp0..\\.venv\\Scripts\\python.exe\"\n"
        "if not defined HQE_PYTHON (\n"
        "  echo HQE Python environment not found.\n"
        "  echo Checked repo hint: %HQE_REPO_HINT%\n"
        "  pause\n"
        "  exit /b 1\n"
        ")\n"
        "\"%HQE_PYTHON%\" \"%~dp0scripts\\hqe_app_v2_preflight.py\" --workspace \"%HQE_WORKSPACE%\" --repo-root \"%HQE_REPO_HINT%\"\n"
        "if errorlevel 1 (\n"
        "  echo.\n"
        "  echo HQE preflight failed. Fix the displayed issue before launch.\n"
        "  pause\n"
        "  exit /b 1\n"
        ")\n"
        "\"%HQE_PYTHON%\" \"%~dp0scripts\\hqe_product_app_v2.py\" --workspace \"%HQE_WORKSPACE%\" --user-id \"hqe-user\" --symbol \"NSE:NIFTY50-INDEX\"\n"
        "endlocal\n",
        encoding="utf-8",
    )
    copied.append(launcher)

    readme = release_dir / "README_FIRST.txt"
    readme.write_text(
        "HUNTER QUANT ENGINE - APP V2 RELEASE PACK\n"
        "=========================================\n\n"
        "1. Keep the HQE repository and its .venv available on this machine.\n"
        "2. Double-click START_HQE_APP_V2.cmd.\n"
        "3. The launcher locates the repo Python environment.\n"
        "4. Preflight must pass before the app opens.\n\n"
        "This is a source-based owner-machine release pack, not a compiled installer.\n\n"
        "SAFETY\n"
        "- Paper only\n"
        "- Data only\n"
        "- No real orders\n"
        "- No broker execution\n"
        "- No auto trading\n\n"
        "This is not a profitability claim.\n",
        encoding="utf-8",
    )
    copied.append(readme)

    manifest_files = []
    for path in sorted(copied):
        manifest_files.append({
            "path": str(path.relative_to(release_dir)).replace("\\", "/"),
            "size_bytes": path.stat().st_size,
            "sha256": sha256(path),
        })

    payload: Dict[str, Any] = {
        "version": VERSION,
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "repo_head": git_head(root),
        "release_dir": str(release_dir),
        "repo_hint": effective_repo_hint,
        "workspace_hint": workspace_hint,
        "file_count": len(manifest_files),
        "files": manifest_files,
        "distribution_status": "PASS",
        "real_money_enabled": False,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "profitability_claim": False,
    }

    manifest = release_dir / "HQE_APP_V2_RELEASE_MANIFEST.json"
    manifest.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    payload["manifest"] = str(manifest)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Build HQE App V2 release pack")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--workspace-hint", required=True)
    parser.add_argument("--repo-hint", default="")
    args = parser.parse_args()

    payload = build_pack(Path(args.output_dir), args.workspace_hint, args.repo_hint)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
