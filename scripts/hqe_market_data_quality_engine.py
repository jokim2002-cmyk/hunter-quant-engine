from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VERSION = "HQE_MARKET_DATA_QUALITY_ENGINE_V1"
INDEX_FILE = "HQE_MARKET_DATA_CACHE_INDEX.json"

COLUMN_ALIASES = {
    "timestamp": (
        "datetime",
        "timestamp",
        "date_time",
        "time",
        "date",
    ),
    "open": ("open", "o"),
    "high": ("high", "h"),
    "low": ("low", "l"),
    "close": ("close", "c", "ltp"),
    "volume": ("volume", "vol", "v"),
}

SAFETY_LOCK = {
    "data_only": True,
    "read_only_scan": True,
    "no_real_money": True,
    "no_real_orders": True,
    "no_broker_execution": True,
    "no_auto_trading": True,
    "no_option_selling": True,
}


def utc_now_text() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def normalize_header(value: str) -> str:
    return value.strip().lower().replace(" ", "_").replace("-", "_")


def resolve_columns(fieldnames: list[str]) -> dict[str, str]:
    normalized = {
        normalize_header(field): field
        for field in fieldnames
        if field is not None
    }
    resolved: dict[str, str] = {}
    for canonical, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in normalized:
                resolved[canonical] = normalized[alias]
                break
    return resolved


def parse_timestamp(value: str) -> datetime | None:
    text = value.strip()
    if not text:
        return None

    candidates = [text, text.replace("Z", "+00:00")]
    for candidate in candidates:
        try:
            parsed = datetime.fromisoformat(candidate)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed
        except ValueError:
            pass

    formats = (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%d-%m-%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%Y%m%d %H:%M:%S",
    )
    for fmt in formats:
        try:
            return datetime.strptime(text, fmt).replace(
                tzinfo=timezone.utc
            )
        except ValueError:
            continue
    return None


def safe_float(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def discover_csv_candidates(
    repo_root: Path,
    workspace: Path,
) -> list[Path]:
    roots = (
        workspace,
        repo_root / "data" / "processed",
        repo_root / "data" / "live",
        repo_root / "data" / "raw",
    )
    found: dict[Path, Path] = {}
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*.csv"):
            if path.is_file():
                found[path.resolve()] = path
    return sorted(
        found.values(),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )


def analyze_csv(
    path: Path,
    *,
    expected_interval_minutes: int = 5,
    max_rows: int = 50000,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "path": str(path),
        "name": path.name,
        "status": "FAILED",
        "score": 0,
        "row_count": 0,
        "columns": {},
        "missing_columns": [],
        "duplicate_timestamps": 0,
        "invalid_timestamps": 0,
        "invalid_ohlc": 0,
        "negative_volume": 0,
        "same_day_gaps": 0,
        "first_timestamp": "",
        "last_timestamp": "",
        "age_minutes": None,
        "updated_at_utc": datetime.fromtimestamp(
            path.stat().st_mtime,
            timezone.utc,
        ).replace(microsecond=0).isoformat(),
    }

    try:
        with path.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as handle:
            reader = csv.DictReader(handle)
            fieldnames = list(reader.fieldnames or [])
            resolved = resolve_columns(fieldnames)
            result["columns"] = resolved

            required = ("timestamp", "open", "high", "low", "close")
            missing = [name for name in required if name not in resolved]
            result["missing_columns"] = missing
            if missing:
                result["status"] = "FAILED"
                return result

            timestamps: list[datetime] = []
            seen: set[datetime] = set()

            for index, row in enumerate(reader):
                if index >= max_rows:
                    break
                result["row_count"] += 1

                timestamp = parse_timestamp(
                    str(row.get(resolved["timestamp"], ""))
                )
                if timestamp is None:
                    result["invalid_timestamps"] += 1
                else:
                    if timestamp in seen:
                        result["duplicate_timestamps"] += 1
                    seen.add(timestamp)
                    timestamps.append(timestamp)

                open_value = safe_float(row.get(resolved["open"], ""))
                high_value = safe_float(row.get(resolved["high"], ""))
                low_value = safe_float(row.get(resolved["low"], ""))
                close_value = safe_float(row.get(resolved["close"], ""))

                prices = (
                    open_value,
                    high_value,
                    low_value,
                    close_value,
                )
                if any(value is None for value in prices):
                    result["invalid_ohlc"] += 1
                else:
                    assert open_value is not None
                    assert high_value is not None
                    assert low_value is not None
                    assert close_value is not None
                    if (
                        high_value < low_value
                        or high_value < max(open_value, close_value)
                        or low_value > min(open_value, close_value)
                        or min(prices) <= 0
                    ):
                        result["invalid_ohlc"] += 1

                volume_column = resolved.get("volume")
                if volume_column:
                    volume = safe_float(row.get(volume_column, ""))
                    if volume is not None and volume < 0:
                        result["negative_volume"] += 1

    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        return result

    timestamps.sort()
    if timestamps:
        result["first_timestamp"] = timestamps[0].isoformat()
        result["last_timestamp"] = timestamps[-1].isoformat()
        now = datetime.now(timezone.utc)
        latest = timestamps[-1].astimezone(timezone.utc)
        result["age_minutes"] = max(
            0,
            round((now - latest).total_seconds() / 60, 2),
        )

        expected_seconds = expected_interval_minutes * 60
        for previous, current in zip(timestamps, timestamps[1:]):
            if previous.date() != current.date():
                continue
            delta = (current - previous).total_seconds()
            if delta > expected_seconds * 1.5:
                result["same_day_gaps"] += max(
                    1,
                    round(delta / expected_seconds) - 1,
                )

    issues = (
        result["duplicate_timestamps"]
        + result["invalid_timestamps"]
        + result["invalid_ohlc"]
        + result["negative_volume"]
        + result["same_day_gaps"]
    )

    score = 100
    if result["row_count"] == 0:
        score -= 100
    score -= min(25, result["duplicate_timestamps"] * 2)
    score -= min(25, result["invalid_timestamps"] * 3)
    score -= min(30, result["invalid_ohlc"] * 3)
    score -= min(10, result["negative_volume"] * 2)
    score -= min(20, result["same_day_gaps"])
    score = max(0, score)

    result["score"] = score
    if result["row_count"] == 0 or score < 50:
        result["status"] = "FAILED"
    elif issues == 0 and score >= 95:
        result["status"] = "PASS"
    else:
        result["status"] = "CHECK"
    return result


def choose_best_source(
    analyses: list[dict[str, Any]],
) -> dict[str, Any]:
    eligible = [
        item
        for item in analyses
        if int(item.get("row_count", 0) or 0) > 0
        and item.get("status") != "FAILED"
    ]
    if not eligible:
        return {}
    return max(
        eligible,
        key=lambda item: (
            int(item.get("score", 0) or 0),
            int(item.get("row_count", 0) or 0),
            str(item.get("updated_at_utc", "")),
        ),
    )


def quality_snapshot(
    repo_root: Path,
    workspace: Path,
) -> dict[str, Any]:
    candidates = discover_csv_candidates(repo_root, workspace)
    analyses = [analyze_csv(path) for path in candidates]
    best = choose_best_source(analyses)

    pass_count = sum(
        1 for item in analyses if item.get("status") == "PASS"
    )
    check_count = sum(
        1 for item in analyses if item.get("status") == "CHECK"
    )
    failed_count = sum(
        1 for item in analyses if item.get("status") == "FAILED"
    )

    overall = (
        "PASS"
        if best and best.get("status") == "PASS"
        else "CHECK"
        if best
        else "NO_USABLE_DATA"
    )
    display = (
        f"Data quality: {overall} | Files: {len(analyses)} | "
        f"PASS {pass_count} | CHECK {check_count} | "
        f"FAILED {failed_count} | "
        f"Best: {best.get('name', 'none')}"
    )
    return {
        "version": VERSION,
        "generated_at_utc": utc_now_text(),
        "overall_status": overall,
        "display_text": display,
        "candidate_count": len(candidates),
        "pass_count": pass_count,
        "check_count": check_count,
        "failed_count": failed_count,
        "best_source": best,
        "analyses": analyses,
        "cache_index_path": str(workspace / INDEX_FILE),
        "real_money_enabled": False,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "option_selling_enabled": False,
        "safety_lock": SAFETY_LOCK,
    }


def write_cache_index(
    repo_root: Path,
    workspace: Path,
) -> dict[str, Any]:
    payload = quality_snapshot(repo_root, workspace)
    target = workspace / INDEX_FILE
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    temporary.replace(target)
    return payload


def guard_payload() -> dict[str, Any]:
    return {
        "version": VERSION,
        "guard_check_status": "PASS",
        "workflow": "MARKET_DATA_QUALITY_AND_CACHE_INDEX",
        "read_only_scan": True,
        "index_write_only": True,
        "real_money_enabled": False,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "option_selling_enabled": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="HQE market-data quality engine"
    )
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[1]),
    )
    parser.add_argument("--workspace", default="")
    parser.add_argument("--snapshot", action="store_true")
    parser.add_argument("--write-index", action="store_true")
    parser.add_argument("--guard-check", action="store_true")
    args = parser.parse_args()

    if args.guard_check:
        print(json.dumps(guard_payload(), indent=2, sort_keys=True))
        return 0
    if not args.workspace:
        parser.error("--workspace is required.")

    repo_root = Path(args.repo_root)
    workspace = Path(args.workspace)

    if args.snapshot:
        print(json.dumps(
            quality_snapshot(repo_root, workspace),
            indent=2,
            sort_keys=True,
        ))
        return 0
    if args.write_index:
        print(json.dumps(
            write_cache_index(repo_root, workspace),
            indent=2,
            sort_keys=True,
        ))
        return 0

    parser.error("Use --snapshot, --write-index or --guard-check.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
