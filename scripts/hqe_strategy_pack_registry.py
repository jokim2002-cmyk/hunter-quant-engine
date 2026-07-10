from __future__ import annotations

import argparse
import copy
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any

VERSION = "HQE_STRATEGY_PACK_REGISTRY_V1"

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

SAFE_NAME = re.compile(r"[^a-z0-9_-]+")


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def safe_slug(value: str) -> str:
    cleaned = SAFE_NAME.sub(
        "_",
        value.strip().lower().replace(" ", "_"),
    )
    cleaned = cleaned.strip("_")
    if len(cleaned) < 3:
        raise ValueError("Strategy id must contain at least 3 safe characters.")
    return cleaned[:64]


def pack_locations(
    repo_root: Path,
    workspace: Path,
) -> dict[str, Path]:
    return {
        "builtin": repo_root / "strategy_packs" / "builtin",
        "imported": workspace / "strategy_packs" / "imported",
        "drafts": workspace / "strategy_packs" / "drafts",
        "exports": workspace / "strategy_packs" / "exports",
    }


def load_pack(path: Path) -> dict[str, Any]:
    from hqe_strategy_pack_schema import validate_strategy_pack

    payload = read_json(path)
    validation = validate_strategy_pack(payload)
    return {
        "path": str(path),
        "source": "",
        "payload": payload,
        "valid": bool(validation["valid"]),
        "errors": list(validation["errors"]),
        "warnings": list(validation["warnings"]),
        "fingerprint": str(validation["fingerprint"]),
    }


def discover_strategy_packs(
    repo_root: Path,
    workspace: Path,
) -> list[dict[str, Any]]:
    locations = pack_locations(repo_root, workspace)
    records: list[dict[str, Any]] = []

    for source, root in locations.items():
        if source == "exports" or not root.exists():
            continue
        for path in sorted(root.glob("*.json")):
            record = load_pack(path)
            record["source"] = source
            payload = record["payload"]
            record["strategy_id"] = str(payload.get("strategy_id", ""))
            record["name"] = str(payload.get("name", path.stem))
            record["version"] = str(payload.get("version", ""))
            record["status"] = str(payload.get("status", ""))
            record["category"] = str(payload.get("category", ""))
            records.append(record)

    source_priority = {
        "drafts": 3,
        "imported": 2,
        "builtin": 1,
    }
    records.sort(
        key=lambda item: (
            item.get("strategy_id", ""),
            item.get("version", ""),
            source_priority.get(str(item.get("source")), 0),
        ),
        reverse=True,
    )
    return records


def registry_snapshot(
    repo_root: Path,
    workspace: Path,
) -> dict[str, Any]:
    records = discover_strategy_packs(repo_root, workspace)
    valid = [record for record in records if record["valid"]]
    invalid = [record for record in records if not record["valid"]]
    locked = [
        record
        for record in valid
        if record.get("status") == "locked_validation"
    ]
    return {
        "version": VERSION,
        "pack_count": len(records),
        "valid_count": len(valid),
        "invalid_count": len(invalid),
        "locked_count": len(locked),
        "packs": records,
        "display_text": (
            f"Strategy packs: {len(records)} | "
            f"Valid: {len(valid)} | Invalid: {len(invalid)} | "
            f"Locked: {len(locked)}"
        ),
        "real_money_enabled": False,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "option_selling_enabled": False,
    }


def import_strategy_pack(
    source_path: Path,
    repo_root: Path,
    workspace: Path,
) -> Path:
    del repo_root
    from hqe_strategy_pack_schema import validate_strategy_pack

    payload = read_json(source_path)
    validation = validate_strategy_pack(payload)
    if not validation["valid"]:
        raise ValueError(
            "Strategy pack is invalid: "
            + "; ".join(validation["errors"])
        )

    locations = pack_locations(Path("."), workspace)
    target_dir = locations["imported"]
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / (
        f"{safe_slug(str(payload['strategy_id']))}_"
        f"{str(payload['version']).replace('.', '_')}.json"
    )
    payload["fingerprint"] = validation["fingerprint"]
    target.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return target


def export_strategy_pack(
    source_path: Path,
    repo_root: Path,
    workspace: Path,
) -> Path:
    del repo_root
    record = load_pack(source_path)
    if not record["valid"]:
        raise ValueError(
            "Cannot export invalid strategy pack: "
            + "; ".join(record["errors"])
        )
    payload = record["payload"]
    target_dir = pack_locations(Path("."), workspace)["exports"]
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / source_path.name
    shutil.copy2(source_path, target)
    return target


def clone_pack_as_draft(
    source_path: Path,
    repo_root: Path,
    workspace: Path,
    *,
    new_strategy_id: str,
    new_name: str,
) -> Path:
    del repo_root
    from hqe_strategy_pack_schema import (
        bump_patch_version,
        pack_fingerprint,
        validate_strategy_pack,
    )

    record = load_pack(source_path)
    if not record["valid"]:
        raise ValueError(
            "Cannot clone invalid strategy pack: "
            + "; ".join(record["errors"])
        )

    payload = copy.deepcopy(record["payload"])
    payload["strategy_id"] = safe_slug(new_strategy_id)
    payload["name"] = new_name.strip() or payload["strategy_id"]
    payload["version"] = bump_patch_version(
        str(payload.get("version", "1.0.0"))
    )
    payload["status"] = "draft"
    validation = payload.setdefault("validation", {})
    validation["locked_candidate"] = False
    validation["candidate_id"] = ""
    payload.setdefault("notes", []).append(
        "Cloned as editable paper-only draft."
    )
    payload["fingerprint"] = pack_fingerprint(payload)

    checked = validate_strategy_pack(payload)
    if not checked["valid"]:
        raise ValueError(
            "Cloned draft is invalid: "
            + "; ".join(checked["errors"])
        )

    target_dir = pack_locations(Path("."), workspace)["drafts"]
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / (
        f"{payload['strategy_id']}_"
        f"{payload['version'].replace('.', '_')}.json"
    )
    target.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return target


def guard_payload() -> dict[str, Any]:
    return {
        "version": VERSION,
        "guard_check_status": "PASS",
        "workflow": "STRATEGY_PACK_REGISTRY_IMPORT_EXPORT",
        "json_only": True,
        "real_money_enabled": False,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "option_selling_enabled": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="HQE strategy-pack registry"
    )
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[1]),
    )
    parser.add_argument("--workspace", default="")
    parser.add_argument("--snapshot", action="store_true")
    parser.add_argument("--guard-check", action="store_true")
    args = parser.parse_args()

    if args.guard_check:
        print(json.dumps(guard_payload(), indent=2, sort_keys=True))
        return 0
    if not args.workspace:
        parser.error("--workspace is required.")
    if args.snapshot:
        print(json.dumps(
            registry_snapshot(
                Path(args.repo_root),
                Path(args.workspace),
            ),
            indent=2,
            sort_keys=True,
        ))
        return 0
    parser.error("Use --snapshot or --guard-check.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
