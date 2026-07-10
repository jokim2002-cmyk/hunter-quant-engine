from __future__ import annotations

import argparse
import ctypes
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

from hqe_app_market_data_quality_center import (
    center_snapshot as data_quality_center_snapshot,
    launch_cache_index_worker,
)

from hqe_app_operator_dashboard import (
    operator_dashboard_snapshot,
)

from hqe_app_paper_watch_control import (
    launch_watch_control_worker,
    session_snapshot as paper_watch_session_snapshot,
)

from hqe_app_safety_evidence_center import (
    launch_safety_audit_worker,
    safety_snapshot,
)

from hqe_app_session_history_center import (
    filter_sessions,
    session_history_snapshot,
)

from hqe_app_daily_close_center import (
    daily_close_snapshot,
    launch_daily_close_worker,
    operation_status as daily_close_operation_status,
)

from hqe_app_daily_startup_center import (
    daily_readiness_snapshot,
    launch_daily_startup_worker,
    operation_status,
)

from hqe_app_market_data_center import (
    launch_market_data_worker,
    market_data_snapshot,
)

from hqe_app_fyers_auth import (
    apply_stored_fyers_environment,
    auth_status_snapshot,
    clear_auth_record,
    exchange_auth_code,
    load_auth_record,
    merge_and_save,
    open_login_browser,
)

from hqe_app_broker_data_health import (
    broker_health_snapshot,
    launch_broker_health_worker,
)

from hqe_app_daily_operations import (
    launch_operation_worker,
    operations_snapshot,
    resolve_latest_evidence,
    resolve_latest_report,
)

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
    """Return dynamic latest report/evidence candidates; never a fixed validation day."""
    candidates: list[Path] = []
    for path in (resolve_latest_report(workspace), resolve_latest_evidence(workspace)):
        if path is not None and path.exists() and path not in candidates:
            candidates.append(path)
    return candidates


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


APP_INSTANCE_MUTEX_NAME = "Local\\HunterQuantEngineAppV2"
_APP_INSTANCE_MUTEX_HANDLE = None


def acquire_app_single_instance() -> bool:
    global _APP_INSTANCE_MUTEX_HANDLE

    if os.name != "nt":
        return True

    kernel32 = ctypes.windll.kernel32
    handle = kernel32.CreateMutexW(None, False, APP_INSTANCE_MUTEX_NAME)
    if not handle:
        return True

    error_code = kernel32.GetLastError()
    if error_code == 183:
        kernel32.CloseHandle(handle)
        try:
            ctypes.windll.user32.MessageBoxW(
                None,
                "Hunter Quant Engine is already running.",
                "Hunter Quant Engine",
                0x40,
            )
        except Exception:
            pass
        return False

    _APP_INSTANCE_MUTEX_HANDLE = handle
    return True


def find_existing_paper_watch_processes() -> List[Dict[str, int]]:
    if os.name != "nt":
        return []

    script_name = "hqe_market_day_persistent_paper_watch_loop.py"
    command = [
        "powershell.exe",
        "-NoProfile",
        "-Command",
        (
            "Get-CimInstance Win32_Process | "
            "Where-Object { "
            "$_.Name -match '^python(w)?\\.exe$' -and "
            "$_.CommandLine -like '*" + script_name + "*' "
            "} | "
            "Select-Object ProcessId,ParentProcessId | "
            "ConvertTo-Json -Compress"
        ),
    ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=15,
            creationflags=CREATE_NO_WINDOW,
        )
    except (OSError, subprocess.SubprocessError, TypeError):
        # TypeError can occur in unit tests where subprocess.Popen is replaced
        # with a minimal fake. Treat unavailable process discovery as no match.
        return []

    if result.returncode != 0 or not result.stdout.strip():
        return []

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return []

    if isinstance(payload, dict):
        payload = [payload]

    processes: List[Dict[str, int]] = []
    for item in payload:
        try:
            processes.append(
                {
                    "pid": int(item["ProcessId"]),
                    "parent_pid": int(item["ParentProcessId"]),
                }
            )
        except (KeyError, TypeError, ValueError):
            continue

    return processes


def canonical_watch_pid(processes: List[Dict[str, int]]) -> Optional[int]:
    if not processes:
        return None

    process_ids = {item["pid"] for item in processes}
    roots = [
        item["pid"]
        for item in processes
        if item["parent_pid"] not in process_ids
    ]
    return min(roots) if roots else min(process_ids)


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
        if self.process is not None and self.process.poll() is None:
            return True
        return bool(find_existing_paper_watch_processes())

    def start(self) -> Dict[str, Any]:
        existing = find_existing_paper_watch_processes()
        existing_pid = canonical_watch_pid(existing)

        if existing_pid is not None:
            return {
                "started": False,
                "status": "ALREADY_RUNNING_GLOBAL",
                "pid": existing_pid,
                "process_count": len(existing),
            }

        if self.process is not None and self.process.poll() is None:
            return {
                "started": False,
                "status": "ALREADY_RUNNING_IN_APP",
                "pid": self.process.pid,
                "process_count": 1,
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
    active_page = tk.StringVar(value="Overview")
    page_title = tk.StringVar(value="Trader Overview")
    page_subtitle = tk.StringVar(
        value="Simple market-data and paper-validation control centre"
    )
    nav_buttons: dict[str, tk.Button] = {}
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

    def navigation_command(page_name: str) -> None:
        show_page(page_name)

    for item in (
        "Overview",
        "Broker Connect",
        "Paper Watch",
        "Today Report",
        "System Safety",
    ):
        button = tk.Button(
            sidebar,
            text=item,
            font=("Segoe UI", 11, "bold" if item == "Overview" else "normal"),
            bg=palette["panel_alt"] if item == "Overview" else palette["sidebar"],
            fg=palette["text"] if item == "Overview" else palette["muted"],
            activebackground=palette["panel_alt"],
            activeforeground=palette["text"],
            relief="flat",
            bd=0,
            anchor="w",
            padx=24,
            pady=11,
            cursor="hand2",
            command=lambda value=item: navigation_command(value),
        )
        button.pack(fill="x")
        nav_buttons[item] = button

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
        textvariable=page_title,
        font=("Segoe UI", 23, "bold"),
        bg=palette["background"],
        fg=palette["text"],
    ).pack(anchor="w")

    tk.Label(
        header,
        textvariable=page_subtitle,
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

    page_panel = tk.Frame(content, bg=palette["background"])

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

        current_page = active_page.get()
        if current_page != "Overview":
            root.after_idle(lambda value=current_page: show_page(value, True))

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

    daily_ops_status = tk.StringVar(value="Embedded live status loading...")
    daily_ops_refresh_job = {"id": None}
    daily_ops_last_error = {"message": ""}

    def refresh_daily_operations(show_errors: bool = False) -> None:
        try:
            snapshot = operations_snapshot(workspace)
            latest_day = snapshot.get("latest_day_number")
            latest_date = snapshot.get("latest_trading_date")
            next_day = snapshot.get("next_day_number")
            next_date = snapshot.get("next_trading_date")
            op_status = str(snapshot.get("operation_status") or "IDLE")
            op_message = str(snapshot.get("operation_message") or "")
            watch_state = "RUNNING" if controller.is_running() else "STOPPED"
            latest_text = (
                f"Day {int(latest_day):03d} • {latest_date}"
                if latest_day and latest_date else "No observed validation day"
            )
            report_state = "READY" if snapshot.get("latest_report") else "NOT READY"
            evidence_state = "READY" if snapshot.get("latest_evidence") else "NOT READY"
            daily_ops_status.set(
                "Embedded Live Status\n"
                f"Latest: {latest_text}\n"
                f"Next: Day {int(next_day):03d} • {next_date}\n"
                f"Paper Watch: {watch_state}\n"
                f"Report: {report_state} • Evidence: {evidence_state}\n"
                f"Daily operation: {op_status}"
                + (f" • {op_message}" if op_message else "")
            )
            if op_status == "FAILED" and show_errors:
                if daily_ops_last_error["message"] != op_message:
                    daily_ops_last_error["message"] = op_message
                    messagebox.showerror("HQE Daily Operations", op_message or "Operation failed safely.")
            elif op_status == "PASS":
                daily_ops_last_error["message"] = ""
        except Exception as exc:
            daily_ops_status.set("Embedded Live Status\nRefresh failed safely.")
            if show_errors:
                messagebox.showerror("HQE Daily Operations", str(exc))
        finally:
            previous = daily_ops_refresh_job.get("id")
            if previous is not None:
                try:
                    root.after_cancel(previous)
                except Exception:
                    pass
            daily_ops_refresh_job["id"] = root.after(2500, lambda: refresh_daily_operations(False))

    def run_daily_operation(operation_name: str) -> None:
        try:
            result = launch_operation_worker(repo_root(), workspace, operation_name, user_id, symbol)
            footer_status.set(str(result.get("message") or result.get("status")))
            refresh_daily_operations(True)
        except Exception as exc:
            footer_status.set("Daily operation failed safely.")
            messagebox.showerror("HQE Daily Operations", str(exc))

    def prepare_next_market_day() -> None:
        run_daily_operation("prepare_next_market_day")

    def run_day_rollover_guard() -> None:
        run_daily_operation("run_day_rollover_guard")

    def generate_daily_close_report() -> None:
        run_daily_operation("generate_daily_close_report")

    def refresh_latest_report() -> None:
        refresh_daily_operations(True)
        open_report()

    def open_latest_evidence() -> None:
        try:
            evidence = resolve_latest_evidence(workspace)
            if evidence is None or not evidence.exists():
                messagebox.showinfo("Latest Evidence", "No latest evidence file is available yet.")
                footer_status.set("Latest evidence is not available yet.")
                return
            os.startfile(str(evidence))
            footer_status.set(f"Opened latest evidence: {evidence.name}")
        except Exception as exc:
            footer_status.set("Latest evidence could not be opened.")
            messagebox.showerror("Latest Evidence", str(exc))

    broker_health_status = tk.StringVar(
        value="Broker/data health will appear after refresh."
    )

    market_data_center_status = tk.StringVar(
        value="Unified market-data status will appear after refresh."
    )

    fyers_auth_status = tk.StringVar(
        value="Fyers secure login status will appear after refresh."
    )

    def refresh_market_data_center(show_dialog: bool = False) -> dict:
        try:
            snapshot = market_data_snapshot(repo_root(), workspace)
            market_data_center_status.set(snapshot["display_text"])
            latest = snapshot["latest_data"]
            footer_status.set(latest["message"])
            if show_dialog:
                messagebox.showinfo(
                    "Unified Market Data Center",
                    snapshot["display_text"] + "\n\n" + latest["message"],
                )
            return snapshot
        except Exception as exc:
            market_data_center_status.set(
                "Unified market-data refresh failed safely."
            )
            footer_status.set(f"Market-data status error: {exc}")
            if show_dialog:
                messagebox.showerror("Unified Market Data Center", str(exc))
            return {}

    def poll_market_data_refresh() -> None:
        snapshot = refresh_market_data_center(False)
        operation = snapshot.get("operation", {})
        if operation.get("status") == "RUNNING":
            root.after(900, poll_market_data_refresh)
            return
        message = operation.get("message", "Market-data refresh finished.")
        footer_status.set(message)
        if operation.get("status") == "PASS":
            messagebox.showinfo("Market Data", message)
        elif operation.get("status") == "FAILED":
            messagebox.showerror("Market Data", message)

    def run_market_data_refresh() -> None:
        try:
            launch_market_data_worker(
                repo_root(),
                workspace,
                "refresh_fyers_data",
                "NSE:NIFTY50-INDEX",
            )
            market_data_center_status.set(
                "Fyers data-only refresh is running..."
            )
            footer_status.set(
                "Refreshing market data only. Real orders remain blocked."
            )
            root.after(900, poll_market_data_refresh)
        except Exception as exc:
            messagebox.showerror("Market Data", str(exc))
            footer_status.set(f"Market-data refresh could not start: {exc}")

    def open_latest_market_data_file() -> None:
        snapshot = refresh_market_data_center(False)
        latest_path = snapshot.get("latest_data", {}).get("path", "")
        if not latest_path:
            messagebox.showwarning(
                "Market Data",
                "No market-data CSV is available yet.",
            )
            return
        path = Path(latest_path)
        if not path.exists():
            messagebox.showerror(
                "Market Data",
                f"Latest market-data file is missing: {path}",
            )
            return
        try:
            os.startfile(path)
        except Exception as exc:
            messagebox.showerror("Market Data", str(exc))

    def open_market_data_center() -> None:
        snapshot = refresh_market_data_center(False)
        dialog = tk.Toplevel(root)
        dialog.title("HQE — Unified Market Data Center")
        dialog.geometry("680x560")
        dialog.minsize(620, 500)
        dialog.configure(bg=palette["bg"])
        dialog.transient(root)

        frame = tk.Frame(dialog, bg=palette["panel"], padx=20, pady=18)
        frame.pack(fill="both", expand=True, padx=18, pady=18)

        tk.Label(
            frame,
            text="Unified Market Data Center",
            bg=palette["panel"],
            fg=palette["text"],
            font=("Segoe UI Semibold", 17),
            anchor="w",
        ).pack(fill="x")

        detail_var = tk.StringVar(
            value=(
                snapshot.get("display_text", "Status unavailable")
                + "\n"
                + snapshot.get("latest_data", {}).get("message", "")
            )
        )

        tk.Label(
            frame,
            textvariable=detail_var,
            bg=palette["panel_alt"],
            fg=palette["muted"],
            justify="left",
            anchor="nw",
            wraplength=600,
            padx=12,
            pady=12,
        ).pack(fill="x", pady=(12, 12))

        sources = snapshot.get("sources", {})
        source_lines = [
            f"{source['display_name']}: {source['status']} / {source['mode']}"
            for source in sources.values()
        ]
        tk.Label(
            frame,
            text="\n".join(source_lines),
            bg=palette["panel"],
            fg=palette["muted"],
            justify="left",
            anchor="w",
        ).pack(fill="x", pady=(0, 14))

        def refresh_dialog() -> None:
            current = refresh_market_data_center(False)
            detail_var.set(
                current.get("display_text", "Status unavailable")
                + "\n"
                + current.get("latest_data", {}).get("message", "")
            )

        ttk.Button(
            frame,
            text="Refresh Status",
            command=refresh_dialog,
        ).pack(fill="x", pady=3)
        ttk.Button(
            frame,
            text="Refresh Fyers Data Now",
            command=run_market_data_refresh,
        ).pack(fill="x", pady=3)
        ttk.Button(
            frame,
            text="Open Latest Data File",
            command=open_latest_market_data_file,
        ).pack(fill="x", pady=3)

        tk.Label(
            frame,
            text=(
                "DATA ONLY • REAL ORDERS BLOCKED • "
                "NO AUTO TRADING • NO OPTION SELLING"
            ),
            bg=palette["panel"],
            fg=palette["muted"],
            anchor="w",
            pady=12,
        ).pack(fill="x")

    def refresh_fyers_auth_status() -> dict:
        snapshot = auth_status_snapshot()
        fyers_auth_status.set(
            f"Fyers: {snapshot['status']} | "
            f"Client: {snapshot['client_id_masked'] or 'not set'} | "
            f"Token: {'stored' if snapshot['access_token_present'] else 'missing'}"
        )
        return snapshot

    def open_fyers_auth_dialog() -> None:
        snapshot = refresh_fyers_auth_status()
        try:
            stored = load_auth_record()
        except Exception:
            stored = {
                "client_id": "",
                "secret_key": "",
                "redirect_uri": "",
                "access_token": "",
            }

        dialog = tk.Toplevel(root)
        dialog.title("HQE — Fyers Login & Token Refresh")
        dialog.geometry("620x610")
        dialog.minsize(590, 560)
        dialog.configure(bg=palette["bg"])
        dialog.transient(root)
        dialog.grab_set()

        frame = tk.Frame(dialog, bg=palette["panel"], padx=20, pady=18)
        frame.pack(fill="both", expand=True, padx=18, pady=18)

        tk.Label(
            frame,
            text="Fyers Login & Token Refresh",
            bg=palette["panel"],
            fg=palette["text"],
            font=("Segoe UI Semibold", 17),
            anchor="w",
        ).pack(fill="x")

        tk.Label(
            frame,
            text=(
                "Credentials are encrypted with Windows DPAPI. "
                "Real orders and broker execution remain permanently blocked."
            ),
            bg=palette["panel"],
            fg=palette["muted"],
            justify="left",
            wraplength=540,
            anchor="w",
        ).pack(fill="x", pady=(6, 14))

        status_var = tk.StringVar(value=snapshot["message"])
        fields = tk.Frame(frame, bg=palette["panel"])
        fields.pack(fill="x")

        def add_field(label_text: str, initial: str = "", secret: bool = False):
            tk.Label(
                fields,
                text=label_text,
                bg=palette["panel"],
                fg=palette["muted"],
                anchor="w",
            ).pack(fill="x", pady=(7, 2))
            entry = ttk.Entry(fields, show="*" if secret else "")
            entry.pack(fill="x")
            if initial:
                entry.insert(0, initial)
            return entry

        client_entry = add_field("Fyers Client ID", stored.get("client_id", ""))
        secret_entry = add_field("Fyers Secret Key", "", True)
        redirect_entry = add_field("Redirect URI", stored.get("redirect_uri", ""))
        auth_code_entry = add_field("Authorization Code", "", True)
        token_entry = add_field("Existing Access Token", "", True)

        def values() -> tuple[str, str, str]:
            return (
                client_entry.get().strip() or stored.get("client_id", ""),
                secret_entry.get().strip() or stored.get("secret_key", ""),
                redirect_entry.get().strip() or stored.get("redirect_uri", ""),
            )

        def refresh_local_status(message: str = "") -> None:
            current = refresh_fyers_auth_status()
            status_var.set(message or current["message"])
            refresh_broker_data_health(False)

        def save_settings() -> None:
            try:
                client_id, secret_key, redirect_uri = values()
                merge_and_save(
                    client_id=client_id,
                    secret_key=secret_key,
                    redirect_uri=redirect_uri,
                )
                secret_entry.delete(0, "end")
                refresh_local_status("Fyers login settings securely saved.")
            except Exception as exc:
                messagebox.showerror("Fyers Login", str(exc))

        def open_browser_login() -> None:
            try:
                client_id, secret_key, redirect_uri = values()
                merge_and_save(
                    client_id=client_id,
                    secret_key=secret_key,
                    redirect_uri=redirect_uri,
                )
                open_login_browser(client_id, secret_key, redirect_uri)
                refresh_local_status(
                    "Fyers login page opened. Paste the authorization code below."
                )
            except Exception as exc:
                messagebox.showerror("Fyers Login", str(exc))

        def finish_exchange(result: dict | None, error: str = "") -> None:
            if error:
                status_var.set(error)
                messagebox.showerror("Fyers Token Refresh", error)
                return
            auth_code_entry.delete(0, "end")
            secret_entry.delete(0, "end")
            refresh_local_status(
                (result or {}).get("message", "Fyers token securely refreshed.")
            )
            messagebox.showinfo(
                "Fyers Token Refresh",
                "Access token securely refreshed. Real orders remain blocked.",
            )

        def exchange_worker(
            client_id: str,
            secret_key: str,
            redirect_uri: str,
            auth_code: str,
        ) -> None:
            try:
                result = exchange_auth_code(
                    client_id=client_id,
                    secret_key=secret_key,
                    redirect_uri=redirect_uri,
                    auth_code=auth_code,
                )
                root.after(0, lambda: finish_exchange(result))
            except Exception as exc:
                safe_error = (
                    "Token refresh failed: "
                    + type(exc).__name__
                    + ". Check login details and authorization code."
                )
                root.after(0, lambda: finish_exchange(None, safe_error))

        def exchange_code() -> None:
            client_id, secret_key, redirect_uri = values()
            auth_code = auth_code_entry.get().strip()
            status_var.set("Refreshing Fyers access token securely...")
            threading.Thread(
                target=exchange_worker,
                args=(client_id, secret_key, redirect_uri, auth_code),
                daemon=True,
            ).start()

        def save_existing_token() -> None:
            try:
                client_id, secret_key, redirect_uri = values()
                token = token_entry.get().strip()
                if not token:
                    raise ValueError("Existing access token is required.")
                merge_and_save(
                    client_id=client_id,
                    secret_key=secret_key,
                    redirect_uri=redirect_uri,
                    access_token=token,
                )
                token_entry.delete(0, "end")
                secret_entry.delete(0, "end")
                refresh_local_status("Existing access token securely stored.")
            except Exception as exc:
                messagebox.showerror("Fyers Login", str(exc))

        def clear_login() -> None:
            if not messagebox.askyesno(
                "Clear Fyers Login",
                "Remove the securely stored Fyers login and token?",
            ):
                return
            clear_auth_record()
            for entry in (
                client_entry,
                secret_entry,
                redirect_entry,
                auth_code_entry,
                token_entry,
            ):
                entry.delete(0, "end")
            refresh_local_status("Stored Fyers login removed.")

        buttons = tk.Frame(frame, bg=palette["panel"])
        buttons.pack(fill="x", pady=(15, 8))
        ttk.Button(buttons, text="Save Login Settings", command=save_settings).pack(
            fill="x", pady=3
        )
        ttk.Button(
            buttons,
            text="Open Fyers Login Page",
            command=open_browser_login,
        ).pack(fill="x", pady=3)
        ttk.Button(buttons, text="Exchange Auth Code", command=exchange_code).pack(
            fill="x", pady=3
        )
        ttk.Button(
            buttons,
            text="Save Existing Access Token",
            command=save_existing_token,
        ).pack(fill="x", pady=3)
        ttk.Button(buttons, text="Clear Stored Login", command=clear_login).pack(
            fill="x", pady=3
        )

        tk.Label(
            frame,
            textvariable=status_var,
            bg=palette["panel_alt"],
            fg=palette["muted"],
            justify="left",
            anchor="w",
            wraplength=540,
            padx=10,
            pady=9,
        ).pack(fill="x", pady=(8, 0))

    def refresh_broker_data_health(show_dialog: bool = False) -> None:
        try:
            snapshot = broker_health_snapshot(repo_root(), workspace)
            broker_health_status.set(snapshot["display_text"])
            footer_status.set(snapshot["broker_message"])
            if show_dialog:
                messagebox.showinfo(
                    "Broker & Data Health",
                    snapshot["display_text"] + "\n\n" + snapshot["broker_message"],
                )
        except Exception as exc:
            broker_health_status.set("Broker/data health refresh failed safely.")
            footer_status.set(f"Broker/data health error: {exc}")
            if show_dialog:
                messagebox.showerror("Broker & Data Health", str(exc))

    def poll_safe_broker_data_test() -> None:
        try:
            snapshot = broker_health_snapshot(
                repo_root(), workspace, check_internet=False
            )
            broker_health_status.set(snapshot["display_text"])
            operation = snapshot["operation"]
            if operation["status"] == "RUNNING":
                root.after(900, poll_safe_broker_data_test)
                return
            footer_status.set(
                operation["message"] or "Safe broker/data test finished."
            )
            if operation["status"] == "PASS":
                messagebox.showinfo(
                    "Safe Data Test",
                    operation["message"] or "Fyers data-only test passed.",
                )
            elif operation["status"] in {"FAILED", "BLOCKED"}:
                messagebox.showerror(
                    "Safe Data Test",
                    operation["message"] or "Safe data-only test did not pass.",
                )
        except Exception as exc:
            footer_status.set(f"Safe data-test status error: {exc}")

    def run_safe_broker_data_test() -> None:
        try:
            launch_broker_health_worker(
                repo_root(),
                workspace,
                "safe_data_test",
                "NSE:NIFTY50-INDEX",
            )
            broker_health_status.set(
                "Safe Fyers data-only connection test is running..."
            )
            footer_status.set(
                "Testing market data only. Real orders remain blocked."
            )
            root.after(900, poll_safe_broker_data_test)
        except Exception as exc:
            messagebox.showerror("Safe Data Test", str(exc))
            footer_status.set(f"Safe data test could not start: {exc}")

    def open_broker_connect_center() -> None:
        script = repo_root() / "scripts" / "hqe_broker_connect_center.py"
        python_exe = repo_root() / ".venv" / "Scripts" / "pythonw.exe"
        if not python_exe.exists():
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
        try:
            report = resolve_latest_report(workspace)
            if report is None or not report.exists():
                messagebox.showinfo(
                    "Today Report",
                    "Latest daily report is not available yet. Generate the daily close report, then refresh.",
                )
                footer_status.set("Latest report is not available yet.")
                return
            os.startfile(str(report))
            footer_status.set(f"Opened latest report: {report.name}")
            refresh_daily_operations(False)
        except Exception as exc:
            footer_status.set("Latest report could not be opened.")
            messagebox.showerror("Today Report", str(exc))

    def open_workspace() -> None:
        try:
            os.startfile(str(workspace))  # type: ignore[attr-defined]
            footer_status.set("Evidence folder opened.")
        except Exception as exc:
            messagebox.showerror("Open folder", str(exc))

    def clear_page_panel() -> None:
        for child in page_panel.winfo_children():
            child.destroy()

    def set_navigation_state(page_name: str) -> None:
        active_page.set(page_name)
        for name, button in nav_buttons.items():
            selected = name == page_name
            button.configure(
                bg=palette["panel_alt"] if selected else palette["sidebar"],
                fg=palette["text"] if selected else palette["muted"],
                font=("Segoe UI", 11, "bold" if selected else "normal"),
            )

    def page_card(parent: tk.Widget, title: str, value: str) -> tk.Frame:
        card = tk.Frame(
            parent,
            bg=palette["panel"],
            highlightbackground=palette["border"],
            highlightthickness=1,
        )
        tk.Label(
            card,
            text=title,
            font=("Segoe UI", 10),
            bg=palette["panel"],
            fg=palette["muted"],
        ).pack(anchor="w", padx=18, pady=(14, 4))
        tk.Label(
            card,
            text=value,
            font=("Segoe UI", 12, "bold"),
            bg=palette["panel"],
            fg=palette["text"],
            justify="left",
            wraplength=560,
        ).pack(anchor="w", padx=18, pady=(0, 16))
        return card

    def open_operator_dashboard() -> None:
        script = repo_root() / "scripts" / "hqe_operator_live_status_dashboard.py"
        python_exe = repo_root() / ".venv" / "Scripts" / "pythonw.exe"
        if not python_exe.exists():
            python_exe = repo_root() / ".venv" / "Scripts" / "python.exe"

        try:
            subprocess.Popen(
                [
                    str(python_exe),
                    str(script),
                    "--workspace",
                    str(workspace),
                    "--launch",
                ],
                cwd=str(repo_root()),
            )
            footer_status.set("Operator live-status dashboard opened.")
        except Exception as exc:
            messagebox.showerror("Operator Live Status", str(exc))

    def show_overview_page() -> None:
        page_title.set("Trader Overview")
        page_subtitle.set(
            "Simple market-data and paper-validation control centre"
        )
        page_panel.pack_forget()
        if not body.winfo_manager():
            body.pack(fill="both", expand=True, padx=28, pady=18)

    def show_broker_page() -> None:
        page_title.set("Broker Connect")
        page_subtitle.set(
            "Choose and manage market-data broker connections inside HQE"
        )

        clear_page_panel()

        intro = page_card(
            page_panel,
            "Connection policy",
            "Broker connections are market-data only. "
            "Real orders and broker execution remain hard locked.",
        )
        intro.pack(fill="x", pady=(0, 12))

        architecture = architecture_payload(workspace)
        grid = tk.Frame(page_panel, bg=palette["background"])
        grid.pack(fill="both", expand=True)

        for index, broker in enumerate(architecture["brokers"]):
            broker_id = broker["broker_id"]
            connection = (
                broker["connection_test"]["status"]
                .replace("_", " ")
                .title()
            )
            market_data = (
                broker["market_data_status"]["status"]
                .replace("_", " ")
                .title()
            )

            card = tk.Frame(
                grid,
                bg=palette["panel"],
                highlightbackground=palette["border"],
                highlightthickness=1,
            )
            card.grid(
                row=index // 2,
                column=index % 2,
                sticky="nsew",
                padx=6,
                pady=6,
            )
            grid.grid_columnconfigure(index % 2, weight=1)

            tk.Label(
                card,
                text=broker["display_name"],
                font=("Segoe UI", 13, "bold"),
                bg=palette["panel"],
                fg=palette["text"],
            ).pack(anchor="w", padx=16, pady=(14, 4))

            tk.Label(
                card,
                text=f"Connection: {connection}\nMarket data: {market_data}",
                font=("Segoe UI", 9),
                bg=palette["panel"],
                fg=palette["muted"],
                justify="left",
            ).pack(anchor="w", padx=16, pady=(0, 10))

            ttk.Button(
                card,
                text="Select Broker",
                style="Secondary.TButton",
                command=lambda value=broker_id: select_broker(value),
            ).pack(anchor="w", padx=16, pady=(0, 14))

        ttk.Button(
            page_panel,
            text="Open Guided Broker Connect",
            style="HQE.TButton",
            command=open_broker_connect_center,
        ).pack(anchor="e", pady=(12, 0))

    def show_paper_watch_page() -> None:
        page_title.set("Paper Watch")
        page_subtitle.set(
            "Live market-data observation and paper-only validation control"
        )

        clear_page_panel()

        payload = app_status_payload(workspace)
        running = controller.is_running()
        watch_status = (
            "RUNNING IN BACKGROUND"
            if running
            else payload["paper_watch"]["watch_status"]
            .replace("_", " ")
            .upper()
        )

        status_card = page_card(
            page_panel,
            "Current paper-watch state",
            watch_status,
        )
        status_card.pack(fill="x", pady=(0, 12))

        policy_card = page_card(
            page_panel,
            "Execution safety",
            "Paper only: YES\n"
            "Real orders: NO\n"
            "Broker execution: NO\n"
            "Auto trading: NO\n"
            "Option selling: NO",
        )
        policy_card.pack(fill="x", pady=(0, 12))

        actions = tk.Frame(page_panel, bg=palette["background"])
        actions.pack(fill="x", pady=(8, 0))

        ttk.Button(
            actions,
            text="Start Paper Watch",
            style="HQE.TButton",
            command=lambda: (start_watch(), show_page("Paper Watch")),
        ).pack(side="left", padx=(0, 8))

        ttk.Button(
            actions,
            text="Stop Paper Watch",
            style="Secondary.TButton",
            command=lambda: (stop_watch(), show_page("Paper Watch")),
        ).pack(side="left", padx=8)

        ttk.Button(
            actions,
            text="Refresh Status",
            style="Secondary.TButton",
            command=lambda: show_page("Paper Watch"),
        ).pack(side="left", padx=8)

        ttk.Button(
            actions,
            text="Open Live Status Dashboard",
            style="Secondary.TButton",
            command=open_operator_dashboard,
        ).pack(side="left", padx=8)

    def show_report_page() -> None:
        page_title.set("Today Report")
        page_subtitle.set(
            "Latest paper-validation reports and market-close evidence"
        )

        clear_page_panel()

        candidates = today_report_candidates(workspace)
        available = [path for path in candidates if path.exists()]

        if available:
            latest = available[0]
            report_value = (
                f"Latest report: {latest.name}\n"
                f"Location: {latest.parent}"
            )
        else:
            report_value = (
                "No HTML report is currently available. "
                "The next valid paper workflow will create it."
            )

        report_card = page_card(
            page_panel,
            "Latest available report",
            report_value,
        )
        report_card.pack(fill="x", pady=(0, 12))

        close_evidence = (
            resolve_latest_evidence(workspace)
        )

        evidence_text = (
            f"Market-close evidence available:\n{close_evidence}"
            if close_evidence.exists()
            else "Market-close evidence is not available yet."
        )

        evidence_card = page_card(
            page_panel,
            "Validation evidence",
            evidence_text,
        )
        evidence_card.pack(fill="x", pady=(0, 12))

        actions = tk.Frame(page_panel, bg=palette["background"])
        actions.pack(fill="x", pady=(8, 0))

        ttk.Button(
            actions,
            text="Open Today Report",
            style="HQE.TButton",
            command=open_report,
        ).pack(side="left", padx=(0, 8))

        ttk.Button(
            actions,
            text="Open Evidence Folder",
            style="Secondary.TButton",
            command=open_workspace,
        ).pack(side="left", padx=8)

        ttk.Button(
            actions,
            text="Refresh Reports",
            style="Secondary.TButton",
            command=lambda: show_page("Today Report"),
        ).pack(side="left", padx=8)

    def show_safety_page() -> None:
        page_title.set("System Safety")
        page_subtitle.set(
            "Hard safety locks protecting the HQE validation environment"
        )

        clear_page_panel()

        safety_rows = (
            ("Paper / simulation only", "ENABLED"),
            ("Real money", "DISABLED"),
            ("Real broker orders", "HARD BLOCKED"),
            ("Broker execution", "HARD BLOCKED"),
            ("Automatic trading", "DISABLED"),
            ("Option selling", "DISABLED"),
            ("Candidate tuning during validation", "LOCKED"),
            ("Manual/fake trades", "PROHIBITED"),
        )

        grid = tk.Frame(page_panel, bg=palette["background"])
        grid.pack(fill="both", expand=True)

        for index, (title, state) in enumerate(safety_rows):
            card = page_card(grid, title, state)
            card.grid(
                row=index // 2,
                column=index % 2,
                sticky="nsew",
                padx=6,
                pady=6,
            )
            grid.grid_columnconfigure(index % 2, weight=1)

        tk.Label(
            page_panel,
            text=(
                "HQE currently observes data and records paper-validation "
                "evidence only. No profitability claim is made."
            ),
            font=("Segoe UI", 9),
            bg=palette["background"],
            fg=palette["muted"],
            justify="left",
        ).pack(anchor="w", pady=(14, 0))

    def show_page(page_name: str, refresh_only: bool = False) -> None:
        if page_name not in nav_buttons:
            page_name = "Overview"

        set_navigation_state(page_name)

        if page_name == "Overview":
            show_overview_page()
            return

        if body.winfo_manager():
            body.pack_forget()

        if not page_panel.winfo_manager():
            page_panel.pack(
                fill="both",
                expand=True,
                padx=28,
                pady=18,
            )

        if page_name == "Broker Connect":
            show_broker_page()
        elif page_name == "Paper Watch":
            show_paper_watch_page()
        elif page_name == "Today Report":
            show_report_page()
        elif page_name == "System Safety":
            show_safety_page()

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

    broker_health_panel = tk.Frame(
        action_panel,
        bg=palette["panel_alt"],
        highlightbackground=palette["border"],
        highlightthickness=1,
    )
    broker_health_panel.pack(fill="x", padx=18, pady=(4, 8))

    tk.Label(
        broker_health_panel,
        textvariable=broker_health_status,
        bg=palette["panel_alt"],
        fg=palette["muted"],
        justify="left",
        anchor="w",
        wraplength=300,
        padx=10,
        pady=8,
    ).pack(fill="x")

    ttk.Button(
        action_panel,
        text="Refresh Broker/Data Health",
        style="Secondary.TButton",
        command=lambda: refresh_broker_data_health(True),
    ).pack(fill="x", padx=18, pady=3)

    ttk.Button(
        action_panel,
        text="Run Safe Data Test",
        style="Secondary.TButton",
        command=run_safe_broker_data_test,
    ).pack(fill="x", padx=18, pady=3)

    ttk.Button(
        action_panel,
        text="Broker Connect Center",
        style="Secondary.TButton",
        command=open_broker_connect_center,
    ).pack(fill="x", padx=18, pady=5)

    tk.Label(
        action_panel, text="Embedded Live Status", bg=palette["panel"],
        fg=palette["accent"], font=("Segoe UI", 10, "bold"), anchor="w",
    ).pack(fill="x", padx=18, pady=(10, 2))
    tk.Label(
        action_panel, textvariable=daily_ops_status, bg=palette["panel"],
        fg=palette["muted"], justify="left", anchor="w", wraplength=255,
        font=("Segoe UI", 9),
    ).pack(fill="x", padx=18, pady=(0, 7))
    ttk.Button(action_panel, text="Prepare Next Market Day", style="Secondary.TButton", command=prepare_next_market_day).pack(fill="x", padx=18, pady=3)
    ttk.Button(action_panel, text="Run Day Rollover Guard", style="Secondary.TButton", command=run_day_rollover_guard).pack(fill="x", padx=18, pady=3)
    ttk.Button(action_panel, text="Generate Daily Close Report", style="Secondary.TButton", command=generate_daily_close_report).pack(fill="x", padx=18, pady=3)
    ttk.Button(action_panel, text="Refresh Latest Report", style="Secondary.TButton", command=refresh_latest_report).pack(fill="x", padx=18, pady=3)
    ttk.Button(action_panel, text="Open Latest Evidence", style="Secondary.TButton", command=open_latest_evidence).pack(fill="x", padx=18, pady=3)

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
    show_page("Overview")
    refresh_status()
    root.after(15000, refresh_status)
    root.after(250, lambda: refresh_daily_operations(False))
    apply_stored_fyers_environment(overwrite=True)
    root.after(300, refresh_fyers_auth_status)
    root.after(600, lambda: refresh_market_data_center(False))
    root.after(450, lambda: refresh_broker_data_health(False))

    daily_startup_status = tk.StringVar(
        value="Daily startup readiness will appear after refresh."
    )

    def refresh_daily_startup_center(show_dialog: bool = False) -> dict:
        try:
            snapshot = daily_readiness_snapshot(repo_root(), workspace)
            daily_startup_status.set(snapshot["display_text"])
            footer_status.set(
                f"Daily readiness: {snapshot['overall_status']}"
            )
            if show_dialog:
                messagebox.showinfo(
                    "Daily Startup & Checklist",
                    snapshot["display_text"],
                )
            return snapshot
        except Exception as exc:
            daily_startup_status.set("Daily readiness refresh failed safely.")
            footer_status.set(f"Daily startup status error: {exc}")
            if show_dialog:
                messagebox.showerror("Daily Startup & Checklist", str(exc))
            return {}

    def poll_daily_startup_operation() -> None:
        payload = operation_status(workspace)
        if payload["status"] == "RUNNING":
            root.after(900, poll_daily_startup_operation)
            return
        refresh_daily_startup_center(False)
        footer_status.set(
            payload["message"] or "Daily startup operation finished."
        )
        if payload["status"] == "PASS":
            messagebox.showinfo("Daily Startup", payload["message"])
        elif payload["status"] in {"FAILED", "BLOCKED"}:
            messagebox.showerror("Daily Startup", payload["message"])

    def prepare_next_market_day_from_app() -> None:
        try:
            launch_daily_startup_worker(repo_root(), workspace)
            daily_startup_status.set("Preparing next market day safely...")
            footer_status.set(
                "Next-day preparation running. Real orders remain blocked."
            )
            root.after(900, poll_daily_startup_operation)
        except Exception as exc:
            messagebox.showerror("Daily Startup", str(exc))
            footer_status.set(
                f"Next-day preparation could not start: {exc}"
            )

    def open_daily_startup_center() -> None:
        snapshot = refresh_daily_startup_center(False)
        dialog = tk.Toplevel(root)
        dialog.title("HQE — Daily Startup & Checklist")
        dialog.geometry("700x560")
        dialog.configure(bg=palette["bg"])
        dialog.transient(root)

        frame = tk.Frame(dialog, bg=palette["panel"], padx=20, pady=18)
        frame.pack(fill="both", expand=True, padx=18, pady=18)

        tk.Label(
            frame,
            text="Daily Startup & Operator Checklist",
            bg=palette["panel"],
            fg=palette["text"],
            font=("Segoe UI Semibold", 17),
            anchor="w",
        ).pack(fill="x")

        detail_var = tk.StringVar(value=snapshot.get("display_text", ""))
        tk.Label(
            frame,
            textvariable=detail_var,
            bg=palette["panel_alt"],
            fg=palette["muted"],
            justify="left",
            anchor="nw",
            wraplength=620,
            padx=12,
            pady=12,
        ).pack(fill="x", pady=(12, 12))

        checklist_var = tk.StringVar(
            value="\n".join(
                f"{'PASS' if passed else 'CHECK'} — "
                f"{name.replace('_', ' ').title()}"
                for name, passed in snapshot.get("checklist", {}).items()
            )
        )
        tk.Label(
            frame,
            textvariable=checklist_var,
            bg=palette["panel"],
            fg=palette["muted"],
            justify="left",
            anchor="nw",
        ).pack(fill="x", pady=(0, 14))

        def refresh_dialog() -> None:
            current = refresh_daily_startup_center(False)
            detail_var.set(current.get("display_text", ""))
            checklist_var.set(
                "\n".join(
                    f"{'PASS' if passed else 'CHECK'} — "
                    f"{name.replace('_', ' ').title()}"
                    for name, passed in current.get("checklist", {}).items()
                )
            )

        ttk.Button(
            frame,
            text="Run Daily Readiness",
            command=refresh_dialog,
        ).pack(fill="x", pady=3)

        ttk.Button(
            frame,
            text="Prepare Next Market Day",
            command=prepare_next_market_day_from_app,
        ).pack(fill="x", pady=3)

        tk.Label(
            frame,
            text=(
                "PAPER/DATA ONLY • REAL ORDERS BLOCKED • "
                "NO AUTO TRADING • NO OPTION SELLING"
            ),
            bg=palette["panel"],
            fg=palette["muted"],
            anchor="w",
            pady=12,
        ).pack(fill="x")

    daily_startup_panel = tk.Frame(
        action_panel,
        bg=palette["panel_alt"],
        highlightbackground=palette["border"],
        highlightthickness=1,
    )
    daily_startup_panel.pack(fill="x", padx=18, pady=(4, 8))

    tk.Label(
        daily_startup_panel,
        textvariable=daily_startup_status,
        bg=palette["panel_alt"],
        fg=palette["muted"],
        justify="left",
        anchor="w",
        wraplength=300,
        padx=10,
        pady=8,
    ).pack(fill="x")

    ttk.Button(
        action_panel,
        text="Daily Startup & Checklist",
        style="Secondary.TButton",
        command=open_daily_startup_center,
    ).pack(fill="x", padx=18, pady=3)

    root.after(750, lambda: refresh_daily_startup_center(False))


    daily_close_status = tk.StringVar(
        value="Daily close status will appear after refresh."
    )

    def refresh_daily_close_center(show_dialog: bool = False) -> dict:
        try:
            snapshot = daily_close_snapshot(repo_root(), workspace)
            daily_close_status.set(snapshot["display_text"])
            footer_status.set(
                f"Daily close: {snapshot['overall_status']}"
            )
            if show_dialog:
                messagebox.showinfo(
                    "Daily Close & Report",
                    snapshot["display_text"],
                )
            return snapshot
        except Exception as exc:
            daily_close_status.set("Daily close refresh failed safely.")
            footer_status.set(f"Daily close status error: {exc}")
            if show_dialog:
                messagebox.showerror("Daily Close & Report", str(exc))
            return {}

    def poll_daily_close_operation() -> None:
        payload = daily_close_operation_status(workspace)
        if payload["status"] == "RUNNING":
            root.after(900, poll_daily_close_operation)
            return
        refresh_daily_close_center(False)
        footer_status.set(
            payload["message"] or "Daily close operation finished."
        )
        if payload["status"] == "PASS":
            messagebox.showinfo("Daily Close & Report", payload["message"])
        elif payload["status"] in {"FAILED", "BLOCKED"}:
            messagebox.showerror("Daily Close & Report", payload["message"])

    def generate_daily_close_from_app() -> None:
        try:
            launch_daily_close_worker(repo_root(), workspace)
            daily_close_status.set("Generating daily close report safely...")
            footer_status.set(
                "Daily close report running. Real orders remain blocked."
            )
            root.after(900, poll_daily_close_operation)
        except Exception as exc:
            messagebox.showerror("Daily Close & Report", str(exc))

    def open_daily_close_artifact(kind: str) -> None:
        snapshot = refresh_daily_close_center(False)
        key = "latest_report" if kind == "report" else "latest_evidence"
        raw_path = str(snapshot.get(key, "")).strip()
        if not raw_path:
            messagebox.showwarning(
                "Daily Close & Report",
                f"No latest {kind} is available yet.",
            )
            return
        path = Path(raw_path)
        if not path.exists():
            messagebox.showerror(
                "Daily Close & Report",
                f"Latest {kind} is missing: {path}",
            )
            return
        try:
            os.startfile(path)
        except Exception as exc:
            messagebox.showerror("Daily Close & Report", str(exc))

    def open_daily_close_center() -> None:
        snapshot = refresh_daily_close_center(False)
        dialog = tk.Toplevel(root)
        dialog.title("HQE — Daily Close & Report")
        dialog.geometry("700x540")
        dialog.configure(bg=palette["bg"])
        dialog.transient(root)

        frame = tk.Frame(dialog, bg=palette["panel"], padx=20, pady=18)
        frame.pack(fill="both", expand=True, padx=18, pady=18)

        tk.Label(
            frame,
            text="End-of-Day Close & Report Center",
            bg=palette["panel"],
            fg=palette["text"],
            font=("Segoe UI Semibold", 17),
            anchor="w",
        ).pack(fill="x")

        detail_var = tk.StringVar(value=snapshot.get("display_text", ""))
        tk.Label(
            frame,
            textvariable=detail_var,
            bg=palette["panel_alt"],
            fg=palette["muted"],
            justify="left",
            anchor="nw",
            wraplength=620,
            padx=12,
            pady=12,
        ).pack(fill="x", pady=(12, 12))

        def refresh_dialog() -> None:
            current = refresh_daily_close_center(False)
            detail_var.set(current.get("display_text", ""))

        ttk.Button(
            frame,
            text="Refresh Close Status",
            command=refresh_dialog,
        ).pack(fill="x", pady=3)

        ttk.Button(
            frame,
            text="Generate Daily Close Report",
            command=generate_daily_close_from_app,
        ).pack(fill="x", pady=3)

        ttk.Button(
            frame,
            text="Open Latest Report",
            command=lambda: open_daily_close_artifact("report"),
        ).pack(fill="x", pady=3)

        ttk.Button(
            frame,
            text="Open Latest Evidence",
            command=lambda: open_daily_close_artifact("evidence"),
        ).pack(fill="x", pady=3)

        tk.Label(
            frame,
            text=(
                "PAPER/DATA ONLY • REAL ORDERS BLOCKED • "
                "NO AUTO TRADING • NO OPTION SELLING"
            ),
            bg=palette["panel"],
            fg=palette["muted"],
            anchor="w",
            pady=12,
        ).pack(fill="x")

    daily_close_panel = tk.Frame(
        action_panel,
        bg=palette["panel_alt"],
        highlightbackground=palette["border"],
        highlightthickness=1,
    )
    daily_close_panel.pack(fill="x", padx=18, pady=(4, 8))

    tk.Label(
        daily_close_panel,
        textvariable=daily_close_status,
        bg=palette["panel_alt"],
        fg=palette["muted"],
        justify="left",
        anchor="w",
        wraplength=300,
        padx=10,
        pady=8,
    ).pack(fill="x")

    ttk.Button(
        action_panel,
        text="Daily Close & Report",
        style="Secondary.TButton",
        command=open_daily_close_center,
    ).pack(fill="x", padx=18, pady=3)

    root.after(900, lambda: refresh_daily_close_center(False))


    session_history_status = tk.StringVar(
        value="Session history will appear after refresh."
    )

    def refresh_session_history_center(show_dialog: bool = False) -> dict:
        try:
            snapshot = session_history_snapshot(workspace)
            session_history_status.set(snapshot["display_text"])
            footer_status.set(snapshot["display_text"])
            if show_dialog:
                messagebox.showinfo(
                    "Session History & Evidence",
                    snapshot["display_text"],
                )
            return snapshot
        except Exception as exc:
            session_history_status.set(
                "Session history refresh failed safely."
            )
            footer_status.set(f"Session history error: {exc}")
            if show_dialog:
                messagebox.showerror(
                    "Session History & Evidence",
                    str(exc),
                )
            return {}

    def open_session_history_center() -> None:
        snapshot = refresh_session_history_center(False)
        all_sessions = list(snapshot.get("sessions", []))

        dialog = tk.Toplevel(root)
        dialog.title("HQE — Session History & Evidence")
        dialog.geometry("980x650")
        dialog.minsize(860, 560)
        dialog.configure(bg=palette["bg"])
        dialog.transient(root)

        outer = tk.Frame(dialog, bg=palette["panel"], padx=18, pady=16)
        outer.pack(fill="both", expand=True, padx=16, pady=16)

        tk.Label(
            outer,
            text="Session History & Evidence Browser",
            bg=palette["panel"],
            fg=palette["text"],
            font=("Segoe UI Semibold", 17),
            anchor="w",
        ).pack(fill="x")

        summary_var = tk.StringVar(
            value=snapshot.get("display_text", "")
        )
        tk.Label(
            outer,
            textvariable=summary_var,
            bg=palette["panel_alt"],
            fg=palette["muted"],
            anchor="w",
            padx=10,
            pady=8,
        ).pack(fill="x", pady=(10, 10))

        search_row = tk.Frame(outer, bg=palette["panel"])
        search_row.pack(fill="x", pady=(0, 10))

        search_var = tk.StringVar()
        search_entry = ttk.Entry(
            search_row,
            textvariable=search_var,
        )
        search_entry.pack(side="left", fill="x", expand=True)

        body = tk.Frame(outer, bg=palette["panel"])
        body.pack(fill="both", expand=True)

        left = tk.Frame(body, bg=palette["panel"])
        left.pack(side="left", fill="both", expand=False)

        right = tk.Frame(body, bg=palette["panel"])
        right.pack(side="left", fill="both", expand=True, padx=(12, 0))

        session_list = tk.Listbox(
            left,
            width=34,
            exportselection=False,
        )
        session_list.pack(fill="both", expand=True)

        artifact_list = tk.Listbox(
            right,
            exportselection=False,
        )
        artifact_list.pack(fill="both", expand=True)

        visible_sessions: list[dict] = []
        visible_artifacts: list[dict] = []

        def selected_session() -> dict:
            selection = session_list.curselection()
            if not selection:
                return {}
            index = int(selection[0])
            if index >= len(visible_sessions):
                return {}
            return visible_sessions[index]

        def populate_artifacts(_event=None) -> None:
            artifact_list.delete(0, "end")
            visible_artifacts.clear()
            session = selected_session()
            for artifact in session.get("artifacts", []):
                visible_artifacts.append(artifact)
                artifact_list.insert(
                    "end",
                    f"[{artifact['category']}] {artifact['name']}",
                )

        def populate_sessions(query: str = "") -> None:
            session_list.delete(0, "end")
            artifact_list.delete(0, "end")
            visible_sessions.clear()
            visible_artifacts.clear()

            for session in filter_sessions(all_sessions, query):
                visible_sessions.append(session)
                date_text = session.get("trading_date", "") or "date unknown"
                session_list.insert(
                    "end",
                    f"{session['day_label']} | {date_text} | "
                    f"{session['artifact_count']} files",
                )

            if visible_sessions:
                session_list.selection_set(0)
                populate_artifacts()

        def search_sessions() -> None:
            populate_sessions(search_var.get())

        def refresh_browser() -> None:
            nonlocal all_sessions
            current = refresh_session_history_center(False)
            all_sessions = list(current.get("sessions", []))
            summary_var.set(current.get("display_text", ""))
            populate_sessions(search_var.get())

        def open_selected_artifact() -> None:
            selection = artifact_list.curselection()
            if not selection:
                messagebox.showwarning(
                    "Session History & Evidence",
                    "Select an artifact first.",
                )
                return
            index = int(selection[0])
            if index >= len(visible_artifacts):
                return
            path = Path(visible_artifacts[index]["path"])
            if not path.exists():
                messagebox.showerror(
                    "Session History & Evidence",
                    f"Artifact is missing: {path}",
                )
                return
            try:
                os.startfile(path)
            except Exception as exc:
                messagebox.showerror(
                    "Session History & Evidence",
                    str(exc),
                )

        def open_day_folder() -> None:
            session = selected_session()
            raw_path = str(session.get("day_folder", "")).strip()
            if not raw_path:
                messagebox.showwarning(
                    "Session History & Evidence",
                    "Day folder is not available.",
                )
                return
            path = Path(raw_path)
            if not path.exists():
                messagebox.showerror(
                    "Session History & Evidence",
                    f"Day folder is missing: {path}",
                )
                return
            try:
                os.startfile(path)
            except Exception as exc:
                messagebox.showerror(
                    "Session History & Evidence",
                    str(exc),
                )

        ttk.Button(
            search_row,
            text="Search Sessions",
            command=search_sessions,
        ).pack(side="left", padx=(8, 0))

        session_list.bind("<<ListboxSelect>>", populate_artifacts)
        artifact_list.bind(
            "<Double-Button-1>",
            lambda _event: open_selected_artifact(),
        )

        button_row = tk.Frame(outer, bg=palette["panel"])
        button_row.pack(fill="x", pady=(12, 0))

        ttk.Button(
            button_row,
            text="Refresh History",
            command=refresh_browser,
        ).pack(side="left", padx=(0, 6))

        ttk.Button(
            button_row,
            text="Open Selected Artifact",
            command=open_selected_artifact,
        ).pack(side="left", padx=6)

        ttk.Button(
            button_row,
            text="Open Day Folder",
            command=open_day_folder,
        ).pack(side="left", padx=6)

        tk.Label(
            outer,
            text=(
                "READ ONLY • PAPER/DATA EVIDENCE • "
                "REAL ORDERS BLOCKED"
            ),
            bg=palette["panel"],
            fg=palette["muted"],
            anchor="w",
            pady=10,
        ).pack(fill="x")

        populate_sessions()
        search_entry.focus_set()

    session_history_panel = tk.Frame(
        action_panel,
        bg=palette["panel_alt"],
        highlightbackground=palette["border"],
        highlightthickness=1,
    )
    session_history_panel.pack(fill="x", padx=18, pady=(4, 8))

    tk.Label(
        session_history_panel,
        textvariable=session_history_status,
        bg=palette["panel_alt"],
        fg=palette["muted"],
        justify="left",
        anchor="w",
        wraplength=300,
        padx=10,
        pady=8,
    ).pack(fill="x")

    ttk.Button(
        action_panel,
        text="Session History & Evidence",
        style="Secondary.TButton",
        command=open_session_history_center,
    ).pack(fill="x", padx=18, pady=3)

    root.after(1050, lambda: refresh_session_history_center(False))


    safety_evidence_status = tk.StringVar(
        value="Safety evidence status will appear after refresh."
    )

    def refresh_safety_evidence_center(
        show_dialog: bool = False,
    ) -> dict:
        try:
            snapshot = safety_snapshot(repo_root(), workspace)
            safety_evidence_status.set(snapshot["display_text"])
            footer_status.set(snapshot["display_text"])
            if show_dialog:
                messagebox.showinfo(
                    "Safety & Kill-Switch Evidence",
                    snapshot["display_text"],
                )
            return snapshot
        except Exception as exc:
            safety_evidence_status.set(
                "Safety evidence refresh failed safely."
            )
            footer_status.set(f"Safety evidence error: {exc}")
            if show_dialog:
                messagebox.showerror(
                    "Safety & Kill-Switch Evidence",
                    str(exc),
                )
            return {}

    def poll_safety_audit() -> None:
        snapshot = refresh_safety_evidence_center(False)
        audit = snapshot.get("audit", {})
        status = str(audit.get("status", "RUNNING"))
        if status == "RUNNING":
            root.after(900, poll_safety_audit)
            return
        message = str(
            audit.get("message", "Safety audit finished.")
        )
        footer_status.set(message)
        if status == "PASS":
            messagebox.showinfo(
                "Safety & Kill-Switch Evidence",
                message,
            )
        elif status in {"CHECK_REQUIRED", "FAILED", "BLOCKED"}:
            messagebox.showerror(
                "Safety & Kill-Switch Evidence",
                message,
            )

    def run_safety_audit_from_app() -> None:
        try:
            launch_safety_audit_worker(repo_root(), workspace)
            safety_evidence_status.set(
                "Running read-only safety guard audit..."
            )
            footer_status.set(
                "Safety audit running. Real orders remain blocked."
            )
            root.after(900, poll_safety_audit)
        except Exception as exc:
            messagebox.showerror(
                "Safety & Kill-Switch Evidence",
                str(exc),
            )

    def open_latest_safety_evidence() -> None:
        snapshot = refresh_safety_evidence_center(False)
        raw_path = str(
            snapshot.get("latest_evidence_path", "")
        ).strip()
        if not raw_path:
            messagebox.showwarning(
                "Safety & Kill-Switch Evidence",
                "No safety evidence is available yet.",
            )
            return
        path = Path(raw_path)
        if not path.exists():
            messagebox.showerror(
                "Safety & Kill-Switch Evidence",
                f"Safety evidence is missing: {path}",
            )
            return
        try:
            os.startfile(path)
        except Exception as exc:
            messagebox.showerror(
                "Safety & Kill-Switch Evidence",
                str(exc),
            )

    def open_safety_evidence_center() -> None:
        snapshot = refresh_safety_evidence_center(False)

        dialog = tk.Toplevel(root)
        dialog.title("HQE — Safety & Kill-Switch Evidence")
        dialog.geometry("900x620")
        dialog.minsize(780, 520)
        dialog.configure(bg=palette["bg"])
        dialog.transient(root)

        outer = tk.Frame(
            dialog,
            bg=palette["panel"],
            padx=18,
            pady=16,
        )
        outer.pack(fill="both", expand=True, padx=16, pady=16)

        tk.Label(
            outer,
            text="Safety & Kill-Switch Evidence Center",
            bg=palette["panel"],
            fg=palette["text"],
            font=("Segoe UI Semibold", 17),
            anchor="w",
        ).pack(fill="x")

        summary_var = tk.StringVar(
            value=snapshot.get("display_text", "")
        )
        tk.Label(
            outer,
            textvariable=summary_var,
            bg=palette["panel_alt"],
            fg=palette["muted"],
            anchor="w",
            padx=10,
            pady=8,
        ).pack(fill="x", pady=(10, 10))

        evidence_list = tk.Listbox(
            outer,
            exportselection=False,
        )
        evidence_list.pack(fill="both", expand=True)

        visible_evidence: list[dict] = []

        def populate(current: dict) -> None:
            evidence_list.delete(0, "end")
            visible_evidence.clear()
            for item in current.get("evidence", []):
                visible_evidence.append(item)
                evidence_list.insert(
                    "end",
                    f"[{item['category']}] "
                    f"{item['kill_switch_state']} | "
                    f"{item['name']}",
                )

        def refresh_dialog() -> None:
            current = refresh_safety_evidence_center(False)
            summary_var.set(current.get("display_text", ""))
            populate(current)

        def open_selected() -> None:
            selection = evidence_list.curselection()
            if not selection:
                messagebox.showwarning(
                    "Safety & Kill-Switch Evidence",
                    "Select evidence first.",
                )
                return
            index = int(selection[0])
            if index >= len(visible_evidence):
                return
            path = Path(visible_evidence[index]["path"])
            if not path.exists():
                messagebox.showerror(
                    "Safety & Kill-Switch Evidence",
                    f"Evidence is missing: {path}",
                )
                return
            try:
                os.startfile(path)
            except Exception as exc:
                messagebox.showerror(
                    "Safety & Kill-Switch Evidence",
                    str(exc),
                )

        button_row = tk.Frame(outer, bg=palette["panel"])
        button_row.pack(fill="x", pady=(12, 0))

        ttk.Button(
            button_row,
            text="Refresh Safety Status",
            command=refresh_dialog,
        ).pack(side="left", padx=(0, 6))

        ttk.Button(
            button_row,
            text="Run Safety Audit",
            command=run_safety_audit_from_app,
        ).pack(side="left", padx=6)

        ttk.Button(
            button_row,
            text="Open Selected Evidence",
            command=open_selected,
        ).pack(side="left", padx=6)

        ttk.Button(
            button_row,
            text="Open Latest Safety Evidence",
            command=open_latest_safety_evidence,
        ).pack(side="left", padx=6)

        evidence_list.bind(
            "<Double-Button-1>",
            lambda _event: open_selected(),
        )

        tk.Label(
            outer,
            text=(
                "READ ONLY • REAL MONEY NO • REAL ORDERS NO • "
                "BROKER EXECUTION NO • AUTO TRADING NO"
            ),
            bg=palette["panel"],
            fg=palette["muted"],
            anchor="w",
            pady=10,
        ).pack(fill="x")

        populate(snapshot)

    safety_evidence_panel = tk.Frame(
        action_panel,
        bg=palette["panel_alt"],
        highlightbackground=palette["border"],
        highlightthickness=1,
    )
    safety_evidence_panel.pack(fill="x", padx=18, pady=(4, 8))

    tk.Label(
        safety_evidence_panel,
        textvariable=safety_evidence_status,
        bg=palette["panel_alt"],
        fg=palette["muted"],
        justify="left",
        anchor="w",
        wraplength=300,
        padx=10,
        pady=8,
    ).pack(fill="x")

    ttk.Button(
        action_panel,
        text="Safety & Kill-Switch Evidence",
        style="Secondary.TButton",
        command=open_safety_evidence_center,
    ).pack(fill="x", padx=18, pady=3)

    root.after(1200, lambda: refresh_safety_evidence_center(False))


    paper_watch_status = tk.StringVar(
        value="Paper-watch session status will appear after refresh."
    )

    def refresh_paper_watch_center(
        show_dialog: bool = False,
    ) -> dict:
        try:
            snapshot = paper_watch_session_snapshot(
                repo_root(),
                workspace,
            )
            paper_watch_status.set(snapshot["display_text"])
            footer_status.set(snapshot["display_text"])
            if show_dialog:
                messagebox.showinfo(
                    "Paper-Watch Session Control",
                    snapshot["display_text"],
                )
            return snapshot
        except Exception as exc:
            paper_watch_status.set(
                "Paper-watch status refresh failed safely."
            )
            footer_status.set(f"Paper-watch status error: {exc}")
            if show_dialog:
                messagebox.showerror(
                    "Paper-Watch Session Control",
                    str(exc),
                )
            return {}

    def poll_paper_watch_operation() -> None:
        snapshot = refresh_paper_watch_center(False)
        footer_status.set(snapshot.get("display_text", ""))
        if snapshot.get("running"):
            messagebox.showinfo(
                "Paper-Watch Session Control",
                "Paper-watch session is running.",
            )

    def run_paper_watch_operation(operation: str) -> None:
        try:
            launch_watch_control_worker(
                repo_root(),
                workspace,
                operation,
            )
            paper_watch_status.set(
                f"Paper-watch {operation} request is running safely..."
            )
            footer_status.set(
                "Paper-only process control running. Real orders blocked."
            )
            root.after(1200, poll_paper_watch_operation)
        except Exception as exc:
            messagebox.showerror(
                "Paper-Watch Session Control",
                str(exc),
            )

    def open_paper_watch_path(kind: str) -> None:
        snapshot = refresh_paper_watch_center(False)
        key = (
            "latest_log_path"
            if kind == "log"
            else "latest_evidence_path"
        )
        raw_path = str(snapshot.get(key, "")).strip()
        if not raw_path:
            messagebox.showwarning(
                "Paper-Watch Session Control",
                f"No latest {kind} is available yet.",
            )
            return
        path = Path(raw_path)
        if not path.exists():
            messagebox.showerror(
                "Paper-Watch Session Control",
                f"Latest {kind} is missing: {path}",
            )
            return
        try:
            os.startfile(path)
        except Exception as exc:
            messagebox.showerror(
                "Paper-Watch Session Control",
                str(exc),
            )

    def open_paper_watch_center() -> None:
        snapshot = refresh_paper_watch_center(False)

        dialog = tk.Toplevel(root)
        dialog.title("HQE — Paper-Watch Session Control")
        dialog.geometry("760x560")
        dialog.minsize(680, 500)
        dialog.configure(bg=palette["bg"])
        dialog.transient(root)

        outer = tk.Frame(
            dialog,
            bg=palette["panel"],
            padx=18,
            pady=16,
        )
        outer.pack(fill="both", expand=True, padx=16, pady=16)

        tk.Label(
            outer,
            text="Paper-Watch Session Control Center",
            bg=palette["panel"],
            fg=palette["text"],
            font=("Segoe UI Semibold", 17),
            anchor="w",
        ).pack(fill="x")

        summary_var = tk.StringVar(
            value=snapshot.get("display_text", "")
        )
        tk.Label(
            outer,
            textvariable=summary_var,
            bg=palette["panel_alt"],
            fg=palette["muted"],
            justify="left",
            anchor="w",
            wraplength=680,
            padx=10,
            pady=10,
        ).pack(fill="x", pady=(10, 12))

        detail_var = tk.StringVar(
            value=(
                f"Runner: {snapshot.get('runner_path', 'missing')}\n"
                f"Guard: "
                f"{snapshot.get('runner_guard', {}).get('status', 'unknown')}\n"
                f"Last message: {snapshot.get('last_message', '')}"
            )
        )
        tk.Label(
            outer,
            textvariable=detail_var,
            bg=palette["panel"],
            fg=palette["muted"],
            justify="left",
            anchor="nw",
        ).pack(fill="x", pady=(0, 12))

        def refresh_dialog() -> None:
            current = refresh_paper_watch_center(False)
            summary_var.set(current.get("display_text", ""))
            detail_var.set(
                f"Runner: {current.get('runner_path', 'missing')}\n"
                f"Guard: "
                f"{current.get('runner_guard', {}).get('status', 'unknown')}\n"
                f"Last message: {current.get('last_message', '')}"
            )

        ttk.Button(
            outer,
            text="Refresh Paper-Watch Status",
            command=refresh_dialog,
        ).pack(fill="x", pady=3)

        ttk.Button(
            outer,
            text="Start Paper Watch",
            command=lambda: run_paper_watch_operation("start"),
        ).pack(fill="x", pady=3)

        ttk.Button(
            outer,
            text="Stop Paper Watch",
            command=lambda: run_paper_watch_operation("stop"),
        ).pack(fill="x", pady=3)

        ttk.Button(
            outer,
            text="Open Latest Watch Log",
            command=lambda: open_paper_watch_path("log"),
        ).pack(fill="x", pady=3)

        ttk.Button(
            outer,
            text="Open Latest Watch Evidence",
            command=lambda: open_paper_watch_path("evidence"),
        ).pack(fill="x", pady=3)

        tk.Label(
            outer,
            text=(
                "PAPER/DATA ONLY • REAL MONEY NO • REAL ORDERS NO • "
                "BROKER EXECUTION NO • AUTO TRADING NO"
            ),
            bg=palette["panel"],
            fg=palette["muted"],
            anchor="w",
            pady=10,
        ).pack(fill="x")

    paper_watch_panel = tk.Frame(
        action_panel,
        bg=palette["panel_alt"],
        highlightbackground=palette["border"],
        highlightthickness=1,
    )
    paper_watch_panel.pack(fill="x", padx=18, pady=(4, 8))

    tk.Label(
        paper_watch_panel,
        textvariable=paper_watch_status,
        bg=palette["panel_alt"],
        fg=palette["muted"],
        justify="left",
        anchor="w",
        wraplength=300,
        padx=10,
        pady=8,
    ).pack(fill="x")

    ttk.Button(
        action_panel,
        text="Paper-Watch Session Control",
        style="Secondary.TButton",
        command=open_paper_watch_center,
    ).pack(fill="x", padx=18, pady=3)

    root.after(1350, lambda: refresh_paper_watch_center(False))


    operator_dashboard_status = tk.StringVar(
        value="Operator dashboard will appear after refresh."
    )

    operator_actions = {
        "connect": (
            locals().get("open_fyers_auth_center")
            or locals().get("open_fyers_login_center")
            or open_market_data_center
        ),
        "prepare": open_daily_startup_center,
        "watch": open_paper_watch_center,
        "close": open_daily_close_center,
        "review": open_session_history_center,
        "safety": open_safety_evidence_center,
    }

    def refresh_operator_dashboard(
        show_dialog: bool = False,
    ) -> dict:
        try:
            snapshot = operator_dashboard_snapshot(
                repo_root(),
                workspace,
            )
            operator_dashboard_status.set(snapshot["display_text"])
            footer_status.set(snapshot["display_text"])
            if show_dialog:
                messagebox.showinfo(
                    "Operator Dashboard",
                    snapshot["display_text"],
                )
            return snapshot
        except Exception as exc:
            operator_dashboard_status.set(
                "Operator dashboard refresh failed safely."
            )
            footer_status.set(f"Operator dashboard error: {exc}")
            if show_dialog:
                messagebox.showerror(
                    "Operator Dashboard",
                    str(exc),
                )
            return {}

    def open_operator_target(target: str) -> None:
        action = operator_actions.get(target)
        if action is None:
            messagebox.showwarning(
                "Operator Dashboard",
                f"No app action is available for: {target}",
            )
            return
        action()

    def open_operator_dashboard() -> None:
        snapshot = refresh_operator_dashboard(False)

        dialog = tk.Toplevel(root)
        dialog.title("HQE — Operator Dashboard")
        dialog.geometry("960x690")
        dialog.minsize(860, 610)
        dialog.configure(bg=palette["bg"])
        dialog.transient(root)

        outer = tk.Frame(
            dialog,
            bg=palette["panel"],
            padx=18,
            pady=16,
        )
        outer.pack(fill="both", expand=True, padx=16, pady=16)

        tk.Label(
            outer,
            text="Connect → Prepare → Watch → Close → Review",
            bg=palette["panel"],
            fg=palette["text"],
            font=("Segoe UI Semibold", 18),
            anchor="w",
        ).pack(fill="x")

        summary_var = tk.StringVar(
            value=snapshot.get("display_text", "")
        )
        tk.Label(
            outer,
            textvariable=summary_var,
            bg=palette["panel_alt"],
            fg=palette["muted"],
            justify="left",
            anchor="w",
            wraplength=860,
            padx=12,
            pady=10,
        ).pack(fill="x", pady=(10, 12))

        next_action_frame = tk.Frame(
            outer,
            bg=palette["panel_alt"],
            highlightbackground=palette["border"],
            highlightthickness=1,
        )
        next_action_frame.pack(fill="x", pady=(0, 12))

        next_action_var = tk.StringVar()
        tk.Label(
            next_action_frame,
            textvariable=next_action_var,
            bg=palette["panel_alt"],
            fg=palette["text"],
            justify="left",
            anchor="w",
            padx=12,
            pady=10,
        ).pack(side="left", fill="x", expand=True)

        workflow_frame = tk.Frame(outer, bg=palette["panel"])
        workflow_frame.pack(fill="x", pady=(0, 12))

        workflow_vars: list[tk.StringVar] = []
        workflow_buttons: list[ttk.Button] = []

        for column, target in enumerate(
            ("connect", "prepare", "watch", "close", "review")
        ):
            workflow_frame.grid_columnconfigure(column, weight=1)
            card = tk.Frame(
                workflow_frame,
                bg=palette["panel_alt"],
                highlightbackground=palette["border"],
                highlightthickness=1,
                padx=8,
                pady=8,
            )
            card.grid(
                row=0,
                column=column,
                sticky="nsew",
                padx=4,
            )
            variable = tk.StringVar(value=target.title())
            workflow_vars.append(variable)
            tk.Label(
                card,
                textvariable=variable,
                bg=palette["panel_alt"],
                fg=palette["muted"],
                justify="left",
                anchor="nw",
                wraplength=150,
            ).pack(fill="both", expand=True)
            button = ttk.Button(
                card,
                text=f"Open {target.title()}",
                command=lambda item=target: open_operator_target(item),
            )
            workflow_buttons.append(button)
            button.pack(fill="x", pady=(8, 0))

        progress_frame = tk.Frame(
            outer,
            bg=palette["panel_alt"],
            highlightbackground=palette["border"],
            highlightthickness=1,
            padx=12,
            pady=10,
        )
        progress_frame.pack(fill="x", pady=(0, 12))

        tk.Label(
            progress_frame,
            text="Validation Progress",
            bg=palette["panel_alt"],
            fg=palette["text"],
            font=("Segoe UI Semibold", 14),
            anchor="w",
        ).pack(fill="x")

        progress_var = tk.StringVar()
        tk.Label(
            progress_frame,
            textvariable=progress_var,
            bg=palette["panel_alt"],
            fg=palette["muted"],
            justify="left",
            anchor="w",
            padx=0,
            pady=8,
        ).pack(fill="x")

        recommended_target = {"value": "review"}

        def render(current: dict) -> None:
            summary_var.set(current.get("display_text", ""))

            next_action = current.get("next_action", {})
            recommended_target["value"] = str(
                next_action.get("target", "review")
            )
            next_action_var.set(
                f"NEXT: {next_action.get('title', 'Review')} — "
                f"{next_action.get('message', '')}"
            )

            workflow = current.get("workflow", [])
            for index, variable in enumerate(workflow_vars):
                if index >= len(workflow):
                    variable.set("Unavailable")
                    continue
                stage = workflow[index]
                variable.set(
                    f"{stage['name']}\n"
                    f"Status: {stage['status']}\n"
                    f"{stage['message']}"
                )

            progress = current.get("validation_progress", {})
            progress_var.set(
                f"Observed days: "
                f"{progress.get('observed_days', 0)}/"
                f"{progress.get('minimum_days', 20)} "
                f"({progress.get('days_percent', 0)}%)\n"
                f"Observed paper trades: "
                f"{progress.get('observed_trades', 0)}/"
                f"{progress.get('minimum_trades', 30)} "
                f"({progress.get('trades_percent', 0)}%)\n"
                f"Expiry weeks: "
                f"{progress.get('expiry_weeks', 0)}/"
                f"{progress.get('minimum_expiry_weeks', 4)} "
                f"({progress.get('expiry_weeks_percent', 0)}%)\n"
                f"Valid trade days: "
                f"{progress.get('valid_trade_days', 0)} | "
                f"No-trade days: {progress.get('no_trade_days', 0)}"
            )

        def refresh_dialog() -> None:
            render(refresh_operator_dashboard(False))

        ttk.Button(
            next_action_frame,
            text="Open Next Recommended Action",
            command=lambda: open_operator_target(
                recommended_target["value"]
            ),
        ).pack(side="right", padx=10, pady=8)

        button_row = tk.Frame(outer, bg=palette["panel"])
        button_row.pack(fill="x")

        ttk.Button(
            button_row,
            text="Refresh Dashboard",
            command=refresh_dialog,
        ).pack(side="left", padx=(0, 6))

        ttk.Button(
            button_row,
            text="Open Safety Center",
            command=lambda: open_operator_target("safety"),
        ).pack(side="left", padx=6)

        tk.Label(
            outer,
            text=(
                "PAPER/DATA ONLY • REAL ORDERS BLOCKED • "
                "THIS IS NOT A PROFITABILITY CLAIM"
            ),
            bg=palette["panel"],
            fg=palette["muted"],
            anchor="w",
            pady=12,
        ).pack(fill="x")

        render(snapshot)

    operator_dashboard_panel = tk.Frame(
        action_panel,
        bg=palette["panel_alt"],
        highlightbackground=palette["border"],
        highlightthickness=2,
    )
    operator_dashboard_panel.pack(fill="x", padx=18, pady=(6, 10))

    tk.Label(
        operator_dashboard_panel,
        text="PRIMARY DAILY WORKFLOW",
        bg=palette["panel_alt"],
        fg=palette["text"],
        font=("Segoe UI Semibold", 11),
        anchor="w",
        padx=10,
        pady=(8, 2),
    ).pack(fill="x")

    tk.Label(
        operator_dashboard_panel,
        textvariable=operator_dashboard_status,
        bg=palette["panel_alt"],
        fg=palette["muted"],
        justify="left",
        anchor="w",
        wraplength=300,
        padx=10,
        pady=6,
    ).pack(fill="x")

    ttk.Button(
        operator_dashboard_panel,
        text="Open Operator Dashboard",
        command=open_operator_dashboard,
    ).pack(fill="x", padx=10, pady=(2, 10))

    root.after(1500, lambda: refresh_operator_dashboard(False))


    market_data_quality_status = tk.StringVar(
        value="Market-data quality will appear after refresh."
    )

    def refresh_market_data_quality_center(
        show_dialog: bool = False,
    ) -> dict:
        try:
            snapshot = data_quality_center_snapshot(
                repo_root(),
                workspace,
            )
            market_data_quality_status.set(snapshot["display_text"])
            footer_status.set(snapshot["display_text"])
            if show_dialog:
                messagebox.showinfo(
                    "Market Data Quality Center",
                    snapshot["display_text"],
                )
            return snapshot
        except Exception as exc:
            market_data_quality_status.set(
                "Market-data quality refresh failed safely."
            )
            footer_status.set(f"Market-data quality error: {exc}")
            if show_dialog:
                messagebox.showerror(
                    "Market Data Quality Center",
                    str(exc),
                )
            return {}

    def open_market_data_quality_path(kind: str) -> None:
        snapshot = refresh_market_data_quality_center(False)
        quality = snapshot.get("quality", {})
        if kind == "best":
            raw_path = str(
                quality.get("best_source", {}).get("path", "")
            ).strip()
        else:
            raw_path = str(
                quality.get("cache_index_path", "")
            ).strip()
        if not raw_path:
            messagebox.showwarning(
                "Market Data Quality Center",
                f"No {kind} data path is available.",
            )
            return
        path = Path(raw_path)
        if not path.exists():
            messagebox.showerror(
                "Market Data Quality Center",
                f"Path is missing: {path}",
            )
            return
        try:
            os.startfile(path)
        except Exception as exc:
            messagebox.showerror(
                "Market Data Quality Center",
                str(exc),
            )

    def rebuild_market_data_cache_index() -> None:
        try:
            launch_cache_index_worker(repo_root(), workspace)
            market_data_quality_status.set(
                "Rebuilding data cache index safely..."
            )
            footer_status.set(
                "Data-only cache index rebuild started."
            )
            root.after(
                1200,
                lambda: refresh_market_data_quality_center(False),
            )
        except Exception as exc:
            messagebox.showerror(
                "Market Data Quality Center",
                str(exc),
            )

    def open_market_data_quality_center() -> None:
        snapshot = refresh_market_data_quality_center(False)

        dialog = tk.Toplevel(root)
        dialog.title("HQE — Market Data Quality Center")
        dialog.geometry("980x660")
        dialog.minsize(860, 580)
        dialog.configure(bg=palette["bg"])
        dialog.transient(root)

        outer = tk.Frame(
            dialog,
            bg=palette["panel"],
            padx=18,
            pady=16,
        )
        outer.pack(fill="both", expand=True, padx=16, pady=16)

        tk.Label(
            outer,
            text="Market Data Abstraction & Quality Center",
            bg=palette["panel"],
            fg=palette["text"],
            font=("Segoe UI Semibold", 17),
            anchor="w",
        ).pack(fill="x")

        summary_var = tk.StringVar(
            value=snapshot.get("display_text", "")
        )
        tk.Label(
            outer,
            textvariable=summary_var,
            bg=palette["panel_alt"],
            fg=palette["muted"],
            justify="left",
            anchor="w",
            wraplength=880,
            padx=10,
            pady=10,
        ).pack(fill="x", pady=(10, 12))

        provider_frame = tk.LabelFrame(
            outer,
            text="Provider Registry",
            bg=palette["panel"],
            fg=palette["text"],
            padx=10,
            pady=8,
        )
        provider_frame.pack(fill="x", pady=(0, 12))

        provider_var = tk.StringVar()
        tk.Label(
            provider_frame,
            textvariable=provider_var,
            bg=palette["panel"],
            fg=palette["muted"],
            justify="left",
            anchor="w",
        ).pack(fill="x")

        quality_list = tk.Listbox(
            outer,
            exportselection=False,
        )
        quality_list.pack(fill="both", expand=True)

        def render(current: dict) -> None:
            summary_var.set(current.get("display_text", ""))

            providers = current.get("providers", {}).get(
                "providers",
                [],
            )
            provider_var.set(
                "\n".join(
                    f"{item['display_name']}: "
                    f"{item['effective_status']} | "
                    f"Execution: NO"
                    for item in providers
                )
            )

            quality_list.delete(0, "end")
            analyses = current.get("quality", {}).get(
                "analyses",
                [],
            )
            for item in analyses:
                quality_list.insert(
                    "end",
                    f"[{item['status']}] score {item['score']} | "
                    f"rows {item['row_count']} | "
                    f"dup {item['duplicate_timestamps']} | "
                    f"gaps {item['same_day_gaps']} | "
                    f"{item['name']}",
                )

        def refresh_dialog() -> None:
            render(refresh_market_data_quality_center(False))

        button_row = tk.Frame(outer, bg=palette["panel"])
        button_row.pack(fill="x", pady=(12, 0))

        ttk.Button(
            button_row,
            text="Refresh Quality Scan",
            command=refresh_dialog,
        ).pack(side="left", padx=(0, 6))

        ttk.Button(
            button_row,
            text="Rebuild Cache Index",
            command=rebuild_market_data_cache_index,
        ).pack(side="left", padx=6)

        ttk.Button(
            button_row,
            text="Open Best Data File",
            command=lambda: open_market_data_quality_path("best"),
        ).pack(side="left", padx=6)

        ttk.Button(
            button_row,
            text="Open Cache Index",
            command=lambda: open_market_data_quality_path("index"),
        ).pack(side="left", padx=6)

        tk.Label(
            outer,
            text=(
                "DATA ONLY • FYERS ACTIVE • OTHER PROVIDERS DISABLED • "
                "REAL ORDERS NO"
            ),
            bg=palette["panel"],
            fg=palette["muted"],
            anchor="w",
            pady=10,
        ).pack(fill="x")

        render(snapshot)

    market_data_quality_panel = tk.Frame(
        action_panel,
        bg=palette["panel_alt"],
        highlightbackground=palette["border"],
        highlightthickness=1,
    )
    market_data_quality_panel.pack(fill="x", padx=18, pady=(4, 8))

    tk.Label(
        market_data_quality_panel,
        textvariable=market_data_quality_status,
        bg=palette["panel_alt"],
        fg=palette["muted"],
        justify="left",
        anchor="w",
        wraplength=300,
        padx=10,
        pady=8,
    ).pack(fill="x")

    ttk.Button(
        action_panel,
        text="Market Data Quality Center",
        style="Secondary.TButton",
        command=open_market_data_quality_center,
    ).pack(fill="x", padx=18, pady=3)

    root.after(
        1650,
        lambda: refresh_market_data_quality_center(False),
    )

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

    if not acquire_app_single_instance():
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
