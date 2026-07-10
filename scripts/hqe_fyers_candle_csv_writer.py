from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List
from zoneinfo import ZoneInfo

VERSION = "HQE_FYERS_CANDLE_CSV_WRITER_V1"
INDIA_TZ = ZoneInfo("Asia/Kolkata")
HEADER = ("datetime", "open", "high", "low", "close", "volume", "source")


def read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}


def epoch_to_ist_iso(value: Any) -> str:
    epoch = float(value)
    if epoch > 10_000_000_000:
        epoch /= 1000
    moment = datetime.fromtimestamp(epoch, tz=timezone.utc).astimezone(INDIA_TZ)
    return moment.replace(microsecond=0).isoformat()


def map_candle(row: Iterable[Any]) -> Dict[str, Any]:
    values = list(row)
    if len(values) < 6:
        raise ValueError("FYERS candle row must contain at least 6 values")
    return {
        "datetime": epoch_to_ist_iso(values[0]),
        "open": values[1],
        "high": values[2],
        "low": values[3],
        "close": values[4],
        "volume": values[5],
        "source": "fyers_history_api",
    }


def normalize_candles(candles: Iterable[Iterable[Any]]) -> List[Dict[str, Any]]:
    unique: Dict[str, Dict[str, Any]] = {}
    for raw in candles:
        mapped = map_candle(raw)
        unique[mapped["datetime"]] = mapped
    return [unique[key] for key in sorted(unique)]


def atomic_write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        csv_writer = csv.DictWriter(handle, fieldnames=HEADER)
        csv_writer.writeheader()
        csv_writer.writerows(rows)
    temporary.replace(path)


def write_from_fetch_status(status_path: Path, output_path: Path) -> Dict[str, Any]:
    payload = read_json(status_path)
    history = payload.get("history_result") or {}
    response = history.get("response_redacted") or {}
    candles = response.get("candles") or []
    if not isinstance(candles, list):
        candles = []

    rows = normalize_candles(candles)
    returned_rows = int(history.get("rows") or len(candles))

    result = {
        "version": VERSION,
        "status_path": str(status_path),
        "output_path": str(output_path),
        "api_status": response.get("s"),
        "api_code": response.get("code"),
        "returned_rows": returned_rows,
        "raw_candle_count": len(candles),
        "written_rows": len(rows),
        "duplicate_rows_removed": len(candles) - len(rows),
        "first_candle_ist": rows[0]["datetime"] if rows else None,
        "latest_candle_ist": rows[-1]["datetime"] if rows else None,
        "write_status": "NO_CANDLES_TO_WRITE",
        "row_count_match": returned_rows == len(rows),
    }

    if response.get("s") == "ok" and int(response.get("code") or 0) == 200 and rows:
        atomic_write_csv(output_path, rows)
        result["write_status"] = "CANDLES_WRITTEN_ATOMICALLY"

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Write FYERS candle response to CSV")
    parser.add_argument("--status-json", required=True)
    parser.add_argument("--output-csv", required=True)
    parser.add_argument("--result-json")
    args = parser.parse_args()

    result = write_from_fetch_status(Path(args.status_json), Path(args.output_csv))

    if args.result_json:
        Path(args.result_json).write_text(
            json.dumps(result, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
