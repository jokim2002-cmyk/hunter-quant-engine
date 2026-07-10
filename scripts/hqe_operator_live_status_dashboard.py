from __future__ import annotations

import argparse
import json
import os
import subprocess
import tkinter as tk
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from tkinter import ttk
from typing import Any, Dict, Optional

VERSION = "HQE_OPERATOR_LIVE_STATUS_DASHBOARD_V1_IST"
REFRESH_MS = 5000
INDIA_TZ = ZoneInfo("Asia/Kolkata")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_time(value: Any) -> Optional[datetime]:
    if not value:
        return None
    text = str(value).strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}


def newest_file(root: Path, pattern: str) -> Optional[Path]:
    files = [path for path in root.glob(pattern) if path.is_file()]
    if not files:
        return None
    return max(files, key=lambda path: path.stat().st_mtime_ns)


def newest_dir(root: Path, pattern: str) -> Optional[Path]:
    dirs = [path for path in root.glob(pattern) if path.is_dir()]
    if not dirs:
        return None
    return max(dirs, key=lambda path: path.stat().st_mtime_ns)


def freshness_label(timestamp: Optional[datetime]) -> str:
    if timestamp is None:
        return "UNKNOWN"
    age = max(0.0, (utc_now() - timestamp).total_seconds())
    if age <= 120:
        return "FRESH"
    if age <= 600:
        return "RECENT"
    return "STALE"


def format_ist(timestamp: Optional[datetime]) -> str:
    if timestamp is None:
        return "UNKNOWN"
    return timestamp.astimezone(INDIA_TZ).strftime("%d-%m-%Y %I:%M:%S %p IST")


def first_present(payload: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        value = payload.get(key)
        if value not in (None, ""):
            return value
    return default


def derive_status(workspace: Path) -> Dict[str, Any]:
    watch_path = workspace / "HQE_PERSISTENT_MARKET_DAY_PAPER_WATCH_STATUS.json"
    fetch_path = workspace / "MODULE_173_FYERS_HISTORICAL_5M_DATA_ONLY_FETCHER_STATUS.json"
    watch = read_json(watch_path)
    fetch = read_json(fetch_path)

    dry_run_dir = newest_dir(workspace, "HQE_APP_V2_CONTROLLED_DRY_RUNS_*")
    dry_run = {}
    if dry_run_dir:
        dry_run = read_json(dry_run_dir / "HQE_APP_V2_CONTROLLED_DRY_RUN_SUMMARY.json")

    timestamps = [
        parse_time(first_present(watch, "generated_at_utc", "updated_at_utc", "last_update_utc")),
        parse_time(first_present(fetch, "generated_at_utc", "updated_at_utc", "last_fetch_utc")),
    ]
    timestamps = [item for item in timestamps if item is not None]
    latest = max(timestamps) if timestamps else None

    watch_text = str(
        first_present(
            watch,
            "status",
            "watch_status",
            "decision",
            "state",
            default="UNKNOWN",
        )
    )

    running_tokens = ("RUNNING", "ACTIVE", "WATCHING", "STARTED")
    is_running = any(token in watch_text.upper() for token in running_tokens)

    decision = first_present(
        dry_run,
        "decision",
        default=first_present(watch, "decision", default="NO_DECISION"),
    )

    broker = first_present(
        fetch,
        "broker",
        "broker_name",
        "provider",
        default="Fyers",
    )

    symbol = first_present(
        watch,
        "symbol",
        "market_symbol",
        default="NSE:NIFTY50-INDEX",
    )

    latest_evidence = str(dry_run_dir) if dry_run_dir else "NOT_FOUND"

    return {
        "version": VERSION,
        "workspace": str(workspace),
        "watch_status": "RUNNING" if is_running else watch_text,
        "data_freshness": freshness_label(latest),
        "latest_update_utc": latest.isoformat() if latest else "UNKNOWN",
        "latest_update_ist": format_ist(latest),
        "broker": str(broker),
        "symbol": str(symbol),
        "latest_decision": str(decision),
        "latest_evidence_folder": latest_evidence,
        "real_money_enabled": False,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "profitability_claim": False,
    }


def open_path(path: Path) -> None:
    if not path.exists():
        return
    if os.name == "nt":
        os.startfile(str(path))  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


class OperatorDashboard(tk.Tk):
    def __init__(self, workspace: Path) -> None:
        super().__init__()
        self.workspace = workspace
        self.title("Hunter Quant Engine — Operator Live Status")
        self.geometry("980x620")
        self.minsize(900, 560)

        self.values: Dict[str, tk.StringVar] = {
            key: tk.StringVar(value="Loading...")
            for key in (
                "watch_status",
                "data_freshness",
                "latest_update_ist",
                "broker",
                "symbol",
                "latest_decision",
                "latest_evidence_folder",
            )
        }

        self._build()
        self.refresh_status()

    def _build(self) -> None:
        root = ttk.Frame(self, padding=18)
        root.pack(fill="both", expand=True)

        title = ttk.Label(
            root,
            text="HQE Operator Live Status Dashboard",
            font=("Segoe UI", 20, "bold"),
        )
        title.pack(anchor="w")

        subtitle = ttk.Label(
            root,
            text="Paper/Data Only • Real Orders Locked • Auto Trading Locked",
            font=("Segoe UI", 10),
        )
        subtitle.pack(anchor="w", pady=(4, 16))

        grid = ttk.Frame(root)
        grid.pack(fill="x")

        cards = [
            ("Paper Watch", "watch_status"),
            ("Data Freshness", "data_freshness"),
            ("Last Update (IST)", "latest_update_ist"),
            ("Broker", "broker"),
            ("Symbol", "symbol"),
            ("Latest Decision", "latest_decision"),
        ]

        for index, (label, key) in enumerate(cards):
            row = index // 2
            column = index % 2
            frame = ttk.LabelFrame(grid, text=label, padding=14)
            frame.grid(
                row=row,
                column=column,
                sticky="nsew",
                padx=6,
                pady=6,
            )
            ttk.Label(
                frame,
                textvariable=self.values[key],
                font=("Segoe UI", 12, "bold"),
                wraplength=390,
            ).pack(anchor="w")
            grid.columnconfigure(column, weight=1)

        evidence = ttk.LabelFrame(root, text="Latest Evidence Folder", padding=14)
        evidence.pack(fill="x", pady=(14, 8))
        ttk.Label(
            evidence,
            textvariable=self.values["latest_evidence_folder"],
            wraplength=880,
        ).pack(anchor="w")

        buttons = ttk.Frame(root)
        buttons.pack(fill="x", pady=(10, 8))

        ttk.Button(
            buttons,
            text="Refresh Now",
            command=self.refresh_status,
        ).pack(side="left", padx=(0, 8))

        ttk.Button(
            buttons,
            text="Open Workspace",
            command=lambda: open_path(self.workspace),
        ).pack(side="left", padx=8)

        ttk.Button(
            buttons,
            text="Open Latest Evidence",
            command=self.open_evidence,
        ).pack(side="left", padx=8)

        safety = ttk.LabelFrame(root, text="Safety Locks", padding=14)
        safety.pack(fill="x", pady=(10, 0))

        ttk.Label(
            safety,
            text=(
                "REAL MONEY: NO    |    REAL ORDERS: NO    |    "
                "BROKER EXECUTION: NO    |    AUTO TRADING: NO"
            ),
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor="w")

        ttk.Label(
            safety,
            text="This is not a profitability claim.",
        ).pack(anchor="w", pady=(6, 0))

    def open_evidence(self) -> None:
        value = self.values["latest_evidence_folder"].get()
        path = Path(value)
        if path.exists():
            open_path(path)

    def refresh_status(self) -> None:
        payload = derive_status(self.workspace)
        for key, variable in self.values.items():
            variable.set(str(payload.get(key, "UNKNOWN")))
        self.after(REFRESH_MS, self.refresh_status)


def main() -> int:
    parser = argparse.ArgumentParser(description="HQE operator live status dashboard")
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--snapshot-only", action="store_true")
    args = parser.parse_args()

    workspace = Path(args.workspace)
    if not workspace.exists():
        raise SystemExit(f"Workspace not found: {workspace}")

    payload = derive_status(workspace)

    if args.snapshot_only:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    app = OperatorDashboard(workspace)
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
