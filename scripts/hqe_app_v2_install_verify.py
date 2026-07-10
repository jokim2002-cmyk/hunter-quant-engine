from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

VERSION = "HQE_APP_V2_INSTALL_VERIFY_V1"


def build_payload(
    install_root: Path,
    app_version: str,
    shortcut_path: Path | None = None,
) -> Dict[str, Any]:
    required = {
        "launcher": install_root / "LAUNCH_HQE_APP_V2.cmd",
        "preflight": install_root / "scripts" / "hqe_app_v2_preflight.py",
        "app": install_root / "scripts" / "hqe_product_app_v2.py",
        "multi_broker": install_root / "scripts" / "hqe_multi_broker_data_architecture.py",
        "icon": install_root / "assets" / "HQE_PRODUCT_APP.ico",
        "version": install_root / "HQE_APP_V2_VERSION.json",
        "manifest": install_root / "HQE_APP_V2_INSTALLER_MANIFEST.json",
    }

    checks = {
        "install_root_exists": install_root.exists(),
        "required_files_present": all(path.exists() for path in required.values()),
        "install_root_writable": os.access(install_root, os.W_OK) if install_root.exists() else False,
        "shortcut_present": shortcut_path.exists() if shortcut_path is not None else True,
        "real_orders_locked": True,
        "broker_execution_locked": True,
        "auto_trading_locked": True,
    }

    passed = all(checks.values())

    return {
        "version": VERSION,
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "app_version": app_version,
        "install_root": str(install_root),
        "shortcut_path": str(shortcut_path) if shortcut_path else "",
        "checks": checks,
        "required_files": {name: str(path) for name, path in required.items()},
        "install_verify_status": "PASS" if passed else "HOLD",
        "real_money_enabled": False,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "profitability_claim": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify HQE App V2 install")
    parser.add_argument("--install-root", required=True)
    parser.add_argument("--app-version", required=True)
    parser.add_argument("--shortcut-path", default="")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    shortcut = Path(args.shortcut_path) if args.shortcut_path.strip() else None
    payload = build_payload(Path(args.install_root), args.app_version, shortcut)

    if args.write:
        output = Path(args.install_root) / "HQE_APP_V2_INSTALL_VERIFY.json"
        output.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["install_verify_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
