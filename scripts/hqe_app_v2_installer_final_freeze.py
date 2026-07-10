from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

VERSION = "HQE_APP_V2_INSTALLER_FINAL_FREEZE_V1"


def read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build_payload(
    package_dir: Path,
    install_root: Path,
    shortcut_path: Path,
    app_version: str,
) -> Dict[str, Any]:
    manifest = read_json(package_dir / "HQE_APP_V2_INSTALLER_MANIFEST.json")
    evidence = read_json(install_root / "HQE_APP_V2_INSTALL_EVIDENCE.json")
    verify = read_json(install_root / "HQE_APP_V2_INSTALL_VERIFY.json")

    required = {
        "package_manifest": package_dir / "HQE_APP_V2_INSTALLER_MANIFEST.json",
        "install_launcher": install_root / "LAUNCH_HQE_APP_V2.cmd",
        "silent_launcher": install_root / "LAUNCH_HQE_APP_V2_SILENT.vbs",
        "install_evidence": install_root / "HQE_APP_V2_INSTALL_EVIDENCE.json",
        "install_verify": install_root / "HQE_APP_V2_INSTALL_VERIFY.json",
        "desktop_shortcut": shortcut_path,
    }

    checks = {
        "required_files_present": all(path.exists() for path in required.values()),
        "installer_manifest_pass": manifest.get("installer_status") == "PASS",
        "silent_launch_enabled": (
            manifest.get("silent_launch_enabled") is True
            and evidence.get("silent_launch_enabled") is True
        ),
        "install_verify_pass": verify.get("install_verify_status") == "PASS",
        "version_matches": (
            manifest.get("app_version") == app_version
            and evidence.get("version") == app_version
            and verify.get("app_version") == app_version
        ),
        "real_orders_locked": (
            manifest.get("real_orders_enabled") is False
            and evidence.get("real_orders_enabled") is False
            and verify.get("real_orders_enabled") is False
        ),
        "broker_execution_locked": (
            manifest.get("broker_execution_enabled") is False
            and evidence.get("broker_execution_enabled") is False
            and verify.get("broker_execution_enabled") is False
        ),
        "auto_trading_locked": (
            manifest.get("auto_trading_enabled") is False
            and evidence.get("auto_trading_enabled") is False
            and verify.get("auto_trading_enabled") is False
        ),
    }

    passed = all(checks.values())

    return {
        "version": VERSION,
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "app_version": app_version,
        "package_dir": str(package_dir),
        "install_root": str(install_root),
        "shortcut_path": str(shortcut_path),
        "checks": checks,
        "required_files": {name: str(path) for name, path in required.items()},
        "installer_final_freeze_status": "PASS" if passed else "HOLD",
        "decision": (
            "HQE_APP_V2_OWNER_INSTALLER_FINAL_FROZEN"
            if passed
            else "HQE_APP_V2_INSTALLER_FREEZE_WAITING_FOR_EVIDENCE"
        ),
        "real_money_enabled": False,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "profitability_claim": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="HQE App V2 installer final freeze")
    parser.add_argument("--package-dir", required=True)
    parser.add_argument("--install-root", required=True)
    parser.add_argument("--shortcut-path", required=True)
    parser.add_argument("--app-version", required=True)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    install_root = Path(args.install_root)
    payload = build_payload(
        Path(args.package_dir),
        install_root,
        Path(args.shortcut_path),
        args.app_version,
    )

    if args.write:
        output = install_root / "HQE_APP_V2_INSTALLER_FINAL_FREEZE.json"
        output.write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["installer_final_freeze_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
