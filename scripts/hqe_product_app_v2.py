from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import threading
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from hqe_multi_broker_data_architecture import (
    BROKER_REGISTRY,
    SAFETY_LOCK,
    architecture_payload,
)
from hqe_product_license_common import (
    app_config_dir,
    license_file_path,
    load_public_key,
    machine_id,
    public_key_path,
    verify_license_key,
)
from hqe_app_v2_license_activation import run_activation_gui


VERSION = "HQE_APP_V2_PUBLIC_TRADER_UI_V1"
DEFAULT_WORKSPACE = Path(
    r"D:\HQE_BACKTEST_RUNS\HQE_FORWARD_PAPER_VALIDATION_ACTIVE_20260708_204722"
)
DEFAULT_SYMBOL = "NSE:NIFTY50-INDEX"
DEFAULT_USER_ID = "hqe-user"

CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


def repo_root() -> Path:
    env_hint = os.environ.get("HQE_REPO_HINT", "").strip()
    if env_hint:
        hinted = Path(env_hint)
        if hinted.exists():
            return hinted
    return Path(__file__).resolve().parents[1]


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig").strip()
    except Exception:
        return ""


def read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def license_status(workspace: Path) -> Dict[str, Any]:
    mid = machine_id()
    lic_path = license_file_path(workspace)
    pub_path = public_key_path(workspace)

    if not pub_path.exists():
        return {
            "valid": False,
            "reason": "public_key_missing",
            "machine_id": mid,
        }

    if not lic_path.exists():
        return {
            "valid": False,
            "reason": "license_missing",
            "machine_id": mid,
        }

    public_key = load_public_key(pub_path)
    result = verify_license_key(
        read_text(lic_path),
        public_key,
        expected_machine_id=mid,
    )
    result["machine_id"] = mid
    return result


def internet_status(timeout_seconds: float = 1.5) -> Dict[str, Any]:
    try:
        with socket.create_connection(("1.1.1.1", 53), timeout=timeout_seconds):
            return {
                "connected": True,
                "status": "ONLINE",
                "message": "Internet connection available",
            }
    except OSError:
        return {
            "connected": False,
            "status": "OFFLINE",
            "message": "Internet connection unavailable",
        }


def paper_watch_status(workspace: Path) -> Dict[str, Any]:
    status_file = workspace / "HQE_PERSISTENT_MARKET_DAY_PAPER_WATCH_STATUS.json"
    payload = read_json(status_file)

    return {
        "status_file": str(status_file),
        "status_file_exists": status_file.exists(),
        "watch_status": payload.get("watch_status", "NOT_STARTED"),
        "cycle": payload.get("cycle", 0),
        "local_time": payload.get("local_time", ""),
        "data_ready": payload.get("data_health", {}).get(
            "data_only_connection_ready",
            False,
        ),
        "real_order_allowed": False,
    }


def today_report_candidates(workspace: Path) -> list[Path]:
    date_text = datetime.now().strftime("%Y-%m-%d")
    names = [
        f"HQE_DAILY_REPORT_{date_text}.html",
        "DAY_001_DAILY_VALIDATION_REPORT.html",
        "HQE_MASTER_SYSTEM_STATUS_DASHBOARD.html",
        "HQE_MASTER_READINESS_FREEZE_FINAL.html",
        "HQE_MASTER_EVIDENCE_INDEX.html",
    ]

    candidates = [workspace / name for name in names]
    candidates.extend(
        sorted(
            workspace.glob("*.html"),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )[:10]
    )

    unique: list[Path] = []
    seen: set[str] = set()

    for path in candidates:
        key = str(path).lower()
        if key not in seen:
            seen.add(key)
            unique.append(path)

    return unique


def app_status_payload(workspace: Path) -> Dict[str, Any]:
    brokers = architecture_payload(workspace)
    watch = paper_watch_status(workspace)
    internet = internet_status()

    fyers = next(
        broker for broker in brokers["brokers"] if broker["broker_id"] == "fyers"
    )

    return {
        "version": VERSION,
        "workspace": str(workspace),
        "internet": internet,
        "selected_broker": "fyers",
        "broker_status": fyers["connection_test"]["status"],
        "market_data_status": fyers["market_data_status"]["status"],
        "paper_watch": watch,
        "today_report_available": any(
            path.exists() for path in today_report_candidates(workspace)
        ),
        "broker_count": brokers["broker_count"],
        "safety_lock": SAFETY_LOCK,
        "real_money_enabled": False,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
    }


def guard_payload() -> Dict[str, Any]:
    return {
        "version": VERSION,
        "guard_check_status": "PASS",
        "public_trader_ui": True,
        "hidden_background_runner_supported": True,
        "visible_cmd_required_for_daily_use": False,
        "broker_ids": list(BROKER_REGISTRY),
        "paper_only": True,
        "data_only": True,
        "no_real_money": True,
        "no_real_orders": True,
        "no_broker_execution": True,
        "no_auto_trading": True,
        "no_fake_trades": True,
        "no_profitability_claim": True,
        "safety_lock": SAFETY_LOCK,
    }


class HiddenPaperWatchController:
    def __init__(
        self,
        workspace: Path,
        user_id: str,
        symbol: str,
    ) -> None:
        self.workspace = workspace
        self.user_id = user_id
        self.symbol = symbol
        self.process: Optional[subprocess.Popen[str]] = None

    def is_running(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def start(self) -> Dict[str, Any]:
        if self.is_running():
            return {
                "started": False,
                "status": "ALREADY_RUNNING",
                "pid": self.process.pid if self.process else None,
            }

        repo = repo_root()
        python_exe = repo / ".venv" / "Scripts" / "python.exe"
        script = repo / "scripts" / "hqe_market_day_persistent_paper_watch_loop.py"

        command = [
            str(python_exe),
            str(script),
            "--workspace",
            str(self.workspace),
            "--user-id",
            self.user_id,
            "--symbol",
            self.symbol,
            "--interval-seconds",
            "300",
            "--run-data-fetch",
        ]

        startupinfo = None
        if os.name == "nt":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        self.process = subprocess.Popen(
            command,
            cwd=str(repo),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
            creationflags=CREATE_NO_WINDOW,
            startupinfo=startupinfo,
        )

        return {
            "started": True,
            "status": "RUNNING_HIDDEN",
            "pid": self.process.pid,
            "broker_execution_invoked": False,
            "order_api_invoked": False,
        }

    def stop(self) -> Dict[str, Any]:
        if not self.is_running():
            return {
                "stopped": False,
                "status": "NOT_RUNNING_IN_THIS_APP_SESSION",
            }

        assert self.process is not None
        pid = self.process.pid
        self.process.terminate()

        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=5)

        return {
            "stopped": True,
            "status": "STOPPED_BY_OPERATOR",
            "pid": pid,
        }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="HQE App V2 Public Trader UI")
    parser.add_argument("--workspace", default=str(DEFAULT_WORKSPACE))
    parser.add_argument("--symbol", default=DEFAULT_SYMBOL)
    parser.add_argument("--user-id", default=DEFAULT_USER_ID)
    parser.add_argument("--guard-check", action="store_true")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--write-status", action="store_true")
    parser.add_argument("--skip-license-check", action="store_true")
    return parser


def run_gui(args: argparse.Namespace) -> int:
    try:
        import tkinter as tk
        from tkinter import messagebox, ttk
    except Exception as exc:
        print(f"Tkinter unavailable: {exc}")
        return 1

    workspace = Path(args.workspace)
    workspace.mkdir(parents=True, exist_ok=True)
    app_config_dir(workspace).mkdir(parents=True, exist_ok=True)

    controller = HiddenPaperWatchController(
        workspace,
        args.user_id,
        args.symbol,
    )

    root = tk.Tk()
    root.title("Hunter Quant Engine")
    root.geometry("1180x760")
    root.minsize(1020, 680)

    icon = repo_root() / "assets" / "HQE_PRODUCT_APP.ico"
    if icon.exists():
        try:
            root.iconbitmap(str(icon))
        except Exception:
            pass

    palette = {
        "background": "#0f172a",
        "sidebar": "#111c35",
        "panel": "#17213a",
        "panel_alt": "#1e293b",
        "text": "#f8fafc",
        "muted": "#94a3b8",
        "accent": "#38bdf8",
        "safe": "#22c55e",
        "warning": "#f59e0b",
        "danger": "#ef4444",
        "border": "#334155",
    }

    root.configure(bg=palette["background"])

    style = ttk.Style()
    style.theme_use("clam")
    style.configure(
        "HQE.TButton",
        font=("Segoe UI", 10, "bold"),
        padding=(14, 10),
        background=palette["accent"],
        foreground="#082f49",
        borderwidth=0,
    )
    style.map(
        "HQE.TButton",
        background=[("active", "#7dd3fc")],
    )
    style.configure(
        "Secondary.TButton",
        font=("Segoe UI", 10),
        padding=(12, 9),
        background=palette["panel_alt"],
        foreground=palette["text"],
        borderwidth=1,
    )
    style.map(
        "Secondary.TButton",
        background=[("active", "#334155")],
    )

    selected_broker = tk.StringVar(value="fyers")
    footer_status = tk.StringVar(value="HQE App V2 ready.")
    card_vars = {
        "internet": tk.StringVar(value="Checking..."),
        "broker": tk.StringVar(value="Checking..."),
        "data": tk.StringVar(value="Checking..."),
        "watch": tk.StringVar(value="Not started"),
    }

    main = tk.Frame(root, bg=palette["background"])
    main.pack(fill="both", expand=True)

    sidebar = tk.Frame(
        main,
        bg=palette["sidebar"],
        width=235,
        highlightbackground=palette["border"],
        highlightthickness=1,
    )
    sidebar.pack(side="left", fill="y")
    sidebar.pack_propagate(False)

    content = tk.Frame(main, bg=palette["background"])
    content.pack(side="left", fill="both", expand=True)

    tk.Label(
        sidebar,
        text="HQE",
        font=("Segoe UI", 28, "bold"),
        bg=palette["sidebar"],
        fg=palette["accent"],
    ).pack(anchor="w", padx=24, pady=(26, 0))

    tk.Label(
        sidebar,
        text="Hunter Quant Engine",
        font=("Segoe UI", 10),
        bg=palette["sidebar"],
        fg=palette["muted"],
    ).pack(anchor="w", padx=24, pady=(0, 26))

    for item in (
        "Overview",
        "Broker Connect",
        "Paper Watch",
        "Today Report",
        "System Safety",
    ):
        fg = palette["text"] if item == "Overview" else palette["muted"]
        tk.Label(
            sidebar,
            text=item,
            font=("Segoe UI", 11, "bold" if item == "Overview" else "normal"),
            bg=palette["sidebar"],
            fg=fg,
            anchor="w",
            padx=24,
            pady=11,
        ).pack(fill="x")

    tk.Label(
        sidebar,
        text="REAL TRADING LOCKED",
        font=("Segoe UI", 10, "bold"),
        bg=palette["sidebar"],
        fg=palette["safe"],
        wraplength=185,
        justify="left",
    ).pack(side="bottom", anchor="w", padx=24, pady=24)

    header = tk.Frame(content, bg=palette["background"])
    header.pack(fill="x", padx=28, pady=(24, 14))

    tk.Label(
        header,
        text="Trader Overview",
        font=("Segoe UI", 23, "bold"),
        bg=palette["background"],
        fg=palette["text"],
    ).pack(anchor="w")

    tk.Label(
        header,
        text="Simple market-data and paper-validation control centre",
        font=("Segoe UI", 10),
        bg=palette["background"],
        fg=palette["muted"],
    ).pack(anchor="w", pady=(2, 0))

    safety = tk.Frame(
        content,
        bg="#052e2b",
        highlightbackground="#166534",
        highlightthickness=1,
    )
    safety.pack(fill="x", padx=28, pady=(0, 16))

    tk.Label(
        safety,
        text=(
            "SAFE MODE ACTIVE  •  PAPER ONLY  •  DATA ONLY  •  "
            "NO REAL ORDERS  •  NO BROKER EXECUTION"
        ),
        font=("Segoe UI", 10, "bold"),
        bg="#052e2b",
        fg="#86efac",
        pady=11,
    ).pack()

    cards_frame = tk.Frame(content, bg=palette["background"])
    cards_frame.pack(fill="x", padx=28)

    card_specs = [
        ("Internet", "internet"),
        ("Selected Broker", "broker"),
        ("Market Data", "data"),
        ("Paper Watch", "watch"),
    ]

    for column, (title, key) in enumerate(card_specs):
        card = tk.Frame(
            cards_frame,
            bg=palette["panel"],
            highlightbackground=palette["border"],
            highlightthickness=1,
        )
        card.grid(row=0, column=column, sticky="nsew", padx=(0, 10))
        cards_frame.grid_columnconfigure(column, weight=1)

        tk.Label(
            card,
            text=title,
            font=("Segoe UI", 9),
            bg=palette["panel"],
            fg=palette["muted"],
        ).pack(anchor="w", padx=16, pady=(14, 3))

        tk.Label(
            card,
            textvariable=card_vars[key],
            font=("Segoe UI", 12, "bold"),
            bg=palette["panel"],
            fg=palette["text"],
            wraplength=190,
            justify="left",
        ).pack(anchor="w", padx=16, pady=(0, 15))

    body = tk.Frame(content, bg=palette["background"])
    body.pack(fill="both", expand=True, padx=28, pady=18)

    broker_panel = tk.Frame(
        body,
        bg=palette["panel"],
        highlightbackground=palette["border"],
        highlightthickness=1,
    )
    broker_panel.pack(side="left", fill="both", expand=True, padx=(0, 9))

    action_panel = tk.Frame(
        body,
        bg=palette["panel"],
        width=330,
        highlightbackground=palette["border"],
        highlightthickness=1,
    )
    action_panel.pack(side="left", fill="y", padx=(9, 0))
    action_panel.pack_propagate(False)

    tk.Label(
        broker_panel,
        text="Choose your broker",
        font=("Segoe UI", 14, "bold"),
        bg=palette["panel"],
        fg=palette["text"],
    ).pack(anchor="w", padx=18, pady=(16, 3))

    tk.Label(
        broker_panel,
        text="All broker connections remain market-data only.",
        font=("Segoe UI", 9),
        bg=palette["panel"],
        fg=palette["muted"],
    ).pack(anchor="w", padx=18, pady=(0, 12))

    broker_grid = tk.Frame(broker_panel, bg=palette["panel"])
    broker_grid.pack(fill="both", expand=True, padx=12, pady=(0, 12))

    def select_broker(broker_id: str) -> None:
        selected_broker.set(broker_id)
        definition = BROKER_REGISTRY[broker_id]
        footer_status.set(
            f"{definition.display_name} selected. "
            "Live order execution remains unavailable."
        )
        refresh_status()

    for index, definition in enumerate(BROKER_REGISTRY.values()):
        broker_card = tk.Frame(
            broker_grid,
            bg=palette["panel_alt"],
            highlightbackground=palette["border"],
            highlightthickness=1,
        )
        broker_card.grid(
            row=index // 2,
            column=index % 2,
            sticky="nsew",
            padx=6,
            pady=6,
        )
        broker_grid.grid_columnconfigure(index % 2, weight=1)
        broker_grid.grid_rowconfigure(index // 2, weight=1)

        tk.Label(
            broker_card,
            text=definition.short_name,
            font=("Segoe UI", 15, "bold"),
            bg=palette["panel_alt"],
            fg=palette["accent"],
        ).pack(anchor="w", padx=14, pady=(12, 2))

        tk.Label(
            broker_card,
            text=definition.display_name,
            font=("Segoe UI", 11, "bold"),
            bg=palette["panel_alt"],
            fg=palette["text"],
        ).pack(anchor="w", padx=14)

        label = (
            "Data adapter available"
            if definition.broker_id == "fyers"
            else "Architecture ready"
        )
        tk.Label(
            broker_card,
            text=label,
            font=("Segoe UI", 8),
            bg=palette["panel_alt"],
            fg=palette["muted"],
        ).pack(anchor="w", padx=14, pady=(2, 8))

        ttk.Button(
            broker_card,
            text="Select",
            style="Secondary.TButton",
            command=lambda value=definition.broker_id: select_broker(value),
        ).pack(anchor="w", padx=14, pady=(0, 12))

    tk.Label(
        action_panel,
        text="Daily Actions",
        font=("Segoe UI", 14, "bold"),
        bg=palette["panel"],
        fg=palette["text"],
    ).pack(anchor="w", padx=18, pady=(18, 4))

    tk.Label(
        action_panel,
        text="No terminal window is required for normal paper-watch use.",
        font=("Segoe UI", 9),
        bg=palette["panel"],
        fg=palette["muted"],
        wraplength=285,
        justify="left",
    ).pack(anchor="w", padx=18, pady=(0, 14))

    def refresh_status() -> None:
        payload = app_status_payload(workspace)
        broker_id = selected_broker.get()
        architecture = architecture_payload(workspace)
        selected = next(
            item
            for item in architecture["brokers"]
            if item["broker_id"] == broker_id
        )

        card_vars["internet"].set(payload["internet"]["status"])
        card_vars["broker"].set(
            f"{selected['display_name']}: "
            f"{selected['connection_test']['status'].replace('_', ' ').title()}"
        )
        card_vars["data"].set(
            selected["market_data_status"]["status"].replace("_", " ").title()
        )

        if controller.is_running():
            card_vars["watch"].set("Running in background")
        else:
            watch = payload["paper_watch"]["watch_status"]
            card_vars["watch"].set(watch.replace("_", " ").title())

        footer_status.set("Status refreshed.")

    def start_watch() -> None:
        result = controller.start()
        footer_status.set(result["status"].replace("_", " ").title())
        card_vars["watch"].set(
            "Running in background"
            if result.get("started") or controller.is_running()
            else result["status"].replace("_", " ").title()
        )

    def stop_watch() -> None:
        result = controller.stop()
        footer_status.set(result["status"].replace("_", " ").title())
        refresh_status()

    def open_broker_connect_center() -> None:
        script = repo_root() / "scripts" / "hqe_broker_connect_center.py"
        python_exe = repo_root() / ".venv" / "Scripts" / "python.exe"
        try:
            subprocess.Popen(
                [str(python_exe), str(script), "--workspace", str(workspace), "--launch"],
                cwd=str(repo_root()),
            )
            footer_status.set("Broker Connect Center opened.")
        except Exception as exc:
            messagebox.showerror("Broker Connect Center", str(exc))

    def open_report() -> None:
        for path in today_report_candidates(workspace):
            if path.exists():
                webbrowser.open(path.resolve().as_uri())
                footer_status.set(f"Opened report: {path.name}")
                return

        messagebox.showinfo(
            "Today Report",
            "No HTML report is available yet. Run the paper workflow first.",
        )
        footer_status.set("No report available yet.")

    def open_workspace() -> None:
        try:
            os.startfile(str(workspace))  # type: ignore[attr-defined]
            footer_status.set("Evidence folder opened.")
        except Exception as exc:
            messagebox.showerror("Open folder", str(exc))

    ttk.Button(
        action_panel,
        text="Refresh All Status",
        style="HQE.TButton",
        command=refresh_status,
    ).pack(fill="x", padx=18, pady=5)

    ttk.Button(
        action_panel,
        text="Start Paper Watch",
        style="HQE.TButton",
        command=start_watch,
    ).pack(fill="x", padx=18, pady=5)

    ttk.Button(
        action_panel,
        text="Stop Paper Watch",
        style="Secondary.TButton",
        command=stop_watch,
    ).pack(fill="x", padx=18, pady=5)

    ttk.Button(
        action_panel,
        text="Broker Connect Center",
        style="Secondary.TButton",
        command=open_broker_connect_center,
    ).pack(fill="x", padx=18, pady=5)

    ttk.Button(
        action_panel,
        text="Open Today Report",
        style="Secondary.TButton",
        command=open_report,
    ).pack(fill="x", padx=18, pady=5)

    ttk.Button(
        action_panel,
        text="Open Evidence Folder",
        style="Secondary.TButton",
        command=open_workspace,
    ).pack(fill="x", padx=18, pady=5)

    tk.Label(
        action_panel,
        text=(
            "Real trading controls are intentionally absent. "
            "This app cannot place, modify or cancel broker orders."
        ),
        font=("Segoe UI", 8),
        bg=palette["panel"],
        fg=palette["muted"],
        wraplength=285,
        justify="left",
    ).pack(side="bottom", anchor="w", padx=18, pady=18)

    footer = tk.Frame(
        content,
        bg=palette["panel_alt"],
        highlightbackground=palette["border"],
        highlightthickness=1,
    )
    footer.pack(fill="x", side="bottom")

    tk.Label(
        footer,
        textvariable=footer_status,
        font=("Segoe UI", 9),
        bg=palette["panel_alt"],
        fg=palette["muted"],
        anchor="w",
        padx=18,
        pady=9,
    ).pack(fill="x")

    def close_app() -> None:
        if controller.is_running():
            stop = messagebox.askyesno(
                "HQE Paper Watch",
                "Paper watch is running. Stop it before closing HQE?",
            )
            if stop:
                controller.stop()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", close_app)
    refresh_status()
    root.after(15000, refresh_status)
    root.mainloop()
    return 0


def main() -> int:
    args = build_parser().parse_args()
    workspace = Path(args.workspace)

    if args.guard_check:
        print(json.dumps(guard_payload(), indent=2, sort_keys=True))
        return 0

    if args.status or args.write_status:
        payload = app_status_payload(workspace)
        if args.write_status:
            workspace.mkdir(parents=True, exist_ok=True)
            path = workspace / "HQE_APP_V2_PUBLIC_TRADER_UI_STATUS.json"
            path.write_text(
                json.dumps(payload, indent=2, sort_keys=True),
                encoding="utf-8",
            )
            payload["status_file"] = str(path)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    if not args.skip_license_check:
        status = license_status(workspace)
        if not status.get("valid"):
            activation_result = run_activation_gui(
                workspace=workspace,
                initial_reason=str(status.get("reason", "license_required")),
            )
            if not activation_result:
                print(
                    json.dumps(
                        {
                            "status": "LICENSE_REQUIRED",
                            "reason": status.get("reason"),
                            "machine_id": status.get("machine_id"),
                        },
                        indent=2,
                        sort_keys=True,
                    )
                )
                return 2

    return run_gui(args)


if __name__ == "__main__":
    raise SystemExit(main())
