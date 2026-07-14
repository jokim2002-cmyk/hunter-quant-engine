from __future__ import annotations

import argparse
import ctypes
import inspect
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

from hqe_app_operator_acceptance_center import (
    launch_operator_acceptance,
    operator_acceptance_center_snapshot,
)

from hqe_app_release_candidate_audit_center import (
    launch_rc_audit_worker,
    rc_audit_center_snapshot,
)

from hqe_app_release_center import (
    launch_desktop_shortcut_install,
    launch_release_operation,
    release_center_snapshot,
)

from hqe_app_paper_validation_report_center import (
    launch_report_pack_worker,
    paper_validation_center_snapshot,
)

from hqe_app_backtest_product_center import (
    backtest_center_snapshot,
    create_backtest_job,
    preview_backtest_job,
    run_backtest_job,
)

from hqe_app_strategy_builder_center import (
    build_preview as build_strategy_preview,
    builder_center_snapshot,
    clear_paper_selection,
    save_builder_draft,
    select_paper_pack,
)

from hqe_app_strategy_pack_center import (
    clone_pack as clone_strategy_pack,
    export_pack as export_strategy_pack,
    import_pack as import_strategy_pack,
    strategy_pack_center_snapshot,
)

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

from hqe_trader_report_renderer import ensure_trader_report

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
from hqe_current_day_session_guard import current_day_report_status
from hqe_recorded_replay_today_report import recorded_replay_status
from hqe_automatic_daily_current_day_workflow import launch_app_background_worker
from hqe_paper_watch_auth_readiness_gate import paper_watch_auth_gate




# HQE desktop mode: hide child console windows on Windows.
if (
    os.name == "nt"
    and not getattr(
        subprocess,
        "_hqe_hidden_popen_installed",
        False,
    )
):
    _HQEOriginalPopen = subprocess.Popen

    class _HQEHiddenPopen(_HQEOriginalPopen):
        def __init__(self, *args, **kwargs):
            creationflags = int(
                kwargs.get("creationflags", 0) or 0
            )
            creationflags |= subprocess.CREATE_NO_WINDOW
            kwargs["creationflags"] = creationflags
            super().__init__(*args, **kwargs)

    subprocess.Popen = _HQEHiddenPopen
    subprocess._hqe_hidden_popen_installed = True



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
    replay = recorded_replay_status(workspace)
    candidates: list[Path] = []
    if replay["ready"]:
        for raw in (
            replay["report_path"],
            replay["summary_path"],
            replay["evaluations_path"],
        ):
            path = Path(raw)
            if path.exists() and path not in candidates:
                candidates.append(path)
        return candidates

    freshness = current_day_report_status(workspace)
    if not freshness["today_ready"]:
        return []
    for path in (
        ensure_trader_report(workspace),
        resolve_latest_report(workspace),
        resolve_latest_evidence(workspace),
    ):
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


def configure_windows_dpi_awareness() -> None:
    if os.name != "nt":
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
        return
    except Exception:
        pass
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


# HQE_WINDOWS_TASKBAR_ICON_AND_ADVANCED_WHEEL_V1
HQE_WINDOWS_APP_USER_MODEL_ID = (
    "HunterQuantEngine.PaperOnly.AppV2"
)


def _configure_windows_taskbar_identity() -> None:
    if os.name != "nt":
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            HQE_WINDOWS_APP_USER_MODEL_ID
        )
    except Exception:
        pass


def _apply_hqe_window_icon(
    window: Any,
    icon_path: Path,
) -> bool:
    if not icon_path.exists():
        return False

    applied = False
    try:
        window.iconbitmap(default=str(icon_path))
        applied = True
    except Exception:
        try:
            window.iconbitmap(str(icon_path))
            applied = True
        except Exception:
            pass

    if os.name != "nt":
        return applied

    try:
        user32 = ctypes.windll.user32

        user32.LoadImageW.argtypes = (
            ctypes.c_void_p,
            ctypes.c_wchar_p,
            ctypes.c_uint,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_uint,
        )
        user32.LoadImageW.restype = ctypes.c_void_p

        user32.GetParent.argtypes = (ctypes.c_void_p,)
        user32.GetParent.restype = ctypes.c_void_p

        user32.SendMessageW.argtypes = (
            ctypes.c_void_p,
            ctypes.c_uint,
            ctypes.c_void_p,
            ctypes.c_void_p,
        )
        user32.SendMessageW.restype = ctypes.c_ssize_t

        image_icon = 1
        load_from_file = 0x0010
        load_default_size = 0x0040
        wm_seticon = 0x0080
        icon_small = 0
        icon_big = 1

        icon_handle = user32.LoadImageW(
            None,
            str(icon_path),
            image_icon,
            0,
            0,
            load_from_file | load_default_size,
        )
        if not icon_handle:
            return applied

        window.update_idletasks()
        tk_window = ctypes.c_void_p(int(window.winfo_id()))
        parent_window = user32.GetParent(tk_window)
        target_window = ctypes.c_void_p(
            int(parent_window or window.winfo_id())
        )

        user32.SendMessageW(
            target_window,
            wm_seticon,
            ctypes.c_void_p(icon_big),
            ctypes.c_void_p(icon_handle),
        )
        user32.SendMessageW(
            target_window,
            wm_seticon,
            ctypes.c_void_p(icon_small),
            ctypes.c_void_p(icon_handle),
        )

        handles = list(
            getattr(window, "_hqe_icon_handles", [])
        )
        handles.append(icon_handle)
        window._hqe_icon_handles = handles
        return True
    except Exception:
        return applied


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

    configure_windows_dpi_awareness()
    _configure_windows_taskbar_identity()
    root = tk.Tk()
    # HQE_STABILIZATION_BUNCH2_CALLBACK_RECOVERY
    def _hqe_report_callback_exception(
        exc_type: type[BaseException],
        exc_value: BaseException,
        exc_traceback: object,
    ) -> None:
        try:
            log_dir = Path(
                os.environ.get("APPDATA")
                or os.environ.get("LOCALAPPDATA")
                or str(Path.home())
            ) / "HQE_PRODUCT_APP"
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = log_dir / "hqe_ui_errors.log"
            rendered = "".join(
                traceback.format_exception(
                    exc_type,
                    exc_value,
                    exc_traceback,
                )
            )
            with log_file.open("a", encoding="utf-8") as handle:
                handle.write(
                    "\n"
                    + "=" * 72
                    + "\n"
                    + datetime.now().isoformat(timespec="seconds")
                    + "\n"
                    + rendered
                )
        except Exception:
            log_file = None

        message = (
            "This feature could not open safely. "
            "HQE is still running and no real order was sent."
        )
        if log_file is not None:
            message += f"\n\nError log: {log_file}"
        try:
            messagebox.showerror("HQE Feature Error", message)
        except Exception:
            pass

    root.report_callback_exception = _hqe_report_callback_exception
    root.title("Hunter Quant Engine")
    # HQE_STABILIZATION_GEOMETRY_V1
    screen_width = max(1024, root.winfo_screenwidth())
    screen_height = max(700, root.winfo_screenheight())
    window_width = min(1440, max(1000, int(screen_width * 0.92)))
    window_height = min(900, max(640, int(screen_height * 0.84)))
    window_x = max(0, (screen_width - window_width) // 2)
    window_y = max(0, (screen_height - window_height) // 3)
    # HQE_STABILIZATION_UI_POLISH_V1
    try:
        display_scaling = max(
            1.0,
            min(2.0, float(root.winfo_fpixels("1i")) / 72.0),
        )
        root.tk.call("tk", "scaling", display_scaling)
    except Exception:
        display_scaling = 1.0
    sidebar_width = min(250, max(205, int(window_width * 0.17)))
    action_panel_width = min(820, max(620, int(window_width * 0.58)))
    root.geometry(
        f"{window_width}x{window_height}+{window_x}+{window_y}"
    )
    root.minsize(1020, 680)

    icon = repo_root() / "assets" / "HQE_PRODUCT_APP.ico"
    _apply_hqe_window_icon(root, icon)
    root.after_idle(
        lambda: _apply_hqe_window_icon(root, icon)
    )

    palette = {
        "background": "#07111f",
        "sidebar": "#0b1728",
        "panel": "#101d31",
        "panel_alt": "#172841",
        "text": "#f8fafc",
        "muted": "#a8b8cc",
        "accent": "#2dd4bf",
        "safe": "#22c55e",
        "warning": "#f59e0b",
        "danger": "#ef4444",
        "border": "#29415f",
    }

    root.configure(bg=palette["background"])

    style = ttk.Style()
    style.theme_use("clam")
    style.configure(
        "HQE.TButton",
        font=("Segoe UI", 10, "bold"),
        padding=(14, 10),
        background=palette["accent"],
        foreground="#032f2d",
        borderwidth=0,
    )
    style.map(
        "HQE.TButton",
        background=[("active", "#5eead4")],
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
        background=[("active", "#29415f")],
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
        width=sidebar_width,
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
    # HQE_OVERVIEW_CENTERED_ACTIONS_V1
    broker_panel.pack_forget()

    action_panel_host = tk.Frame(
        body,
        bg=palette["panel"],
        width=action_panel_width,
        highlightbackground=palette["border"],
        highlightthickness=1,
    )
    action_panel_host.pack(
        side="top",
        fill="y",
        expand=True,
        padx=34,
        pady=(0, 18),
        anchor="center",
    )


    action_panel_host.pack_propagate(False)
    # HQE_STABILIZATION_SCROLL_V1
    hqe_scroll_canvas = tk.Canvas(
        action_panel_host,
        bg=palette["panel"],
        highlightthickness=0,
        borderwidth=0,
    )
    hqe_scrollbar = ttk.Scrollbar(
        action_panel_host,
        orient="vertical",
        command=hqe_scroll_canvas.yview,
    )
    hqe_scroll_canvas.configure(
        yscrollcommand=hqe_scrollbar.set,
    )
    hqe_scrollbar.pack(side="right", fill="y")
    hqe_scroll_canvas.pack(side="left", fill="both", expand=True)

    action_panel = tk.Frame(
        hqe_scroll_canvas,
        bg=palette["panel"],
    )
    action_panel_window = hqe_scroll_canvas.create_window(
        (0, 0),
        window=action_panel,
        anchor="nw",
    )

    def _sync_action_panel_scroll(_event=None) -> None:
        try:
            hqe_scroll_canvas.itemconfigure(
                action_panel_window,
                width=max(1, hqe_scroll_canvas.winfo_width()),
            )
            bounds = hqe_scroll_canvas.bbox("all")
            if bounds is not None:
                hqe_scroll_canvas.configure(scrollregion=bounds)
        except tk.TclError:
            return

    def _action_panel_mousewheel(event):
        try:
            left = hqe_scroll_canvas.winfo_rootx()
            top = hqe_scroll_canvas.winfo_rooty()
            right = left + hqe_scroll_canvas.winfo_width()
            bottom = top + hqe_scroll_canvas.winfo_height()
            if (
                left <= event.x_root <= right
                and top <= event.y_root <= bottom
            ):
                direction = -1 if event.delta > 0 else 1
                hqe_scroll_canvas.yview_scroll(direction, "units")
                return "break"
        except tk.TclError:
            return None
        return None

    action_panel.bind("<Configure>", _sync_action_panel_scroll)
    hqe_scroll_canvas.bind("<Configure>", _sync_action_panel_scroll)
    root.bind_all(
        "<MouseWheel>",
        _action_panel_mousewheel,
        add="+",
    )

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

    # HQE_FINAL_RICH_OVERVIEW_V2
    hqe_overview_hero = tk.Frame(
        action_panel,
        bg="#0a2a35",
        highlightbackground=palette["accent"],
        highlightthickness=1,
    )
    hqe_overview_hero.pack(fill="x", padx=28, pady=(24, 16))

    tk.Frame(
        hqe_overview_hero,
        bg=palette["accent"],
        height=4,
    ).pack(fill="x")

    tk.Label(
        hqe_overview_hero,
        text="HUNTER QUANT ENGINE",
        font=("Segoe UI Semibold", 9),
        bg="#0a2a35",
        fg=palette["accent"],
        anchor="w",
    ).pack(fill="x", padx=22, pady=(17, 3))

    tk.Label(
        hqe_overview_hero,
        text="Daily Operator Center",
        font=("Segoe UI Semibold", 22),
        bg="#0a2a35",
        fg=palette["text"],
        anchor="w",
    ).pack(fill="x", padx=22)

    tk.Label(
        hqe_overview_hero,
        text=(
            "Clean one-by-one access to every paper-validation action. "
            "Detailed live status remains available inside each center."
        ),
        font=("Segoe UI", 10),
        bg="#0a2a35",
        fg=palette["muted"],
        justify="left",
        wraplength=730,
        anchor="w",
    ).pack(fill="x", padx=22, pady=(7, 18))

    tk.Label(
        action_panel,
        text="Quick Actions",
        font=("Segoe UI", 14, "bold"),
        bg=palette["panel"],
        fg=palette["text"],
    ).pack(anchor="w", padx=18, pady=(18, 4))

    tk.Label(
        action_panel,
        text="Choose one action at a time. Every control remains paper/data only.",
        font=("Segoe UI", 9),
        bg=palette["panel"],
        fg=palette["muted"],
        wraplength=730,
        justify="left",
    ).pack(anchor="w", padx=18, pady=(0, 14))

    def apply_paper_watch_auth_gate(
        *,
        show_warning: bool = False,
    ) -> dict:
        gate = paper_watch_auth_gate(workspace)
        running = controller.is_running()

        if gate["allowed"]:
            setattr(
                apply_paper_watch_auth_gate,
                "_warning_key",
                "",
            )
            card_vars["broker"].set(gate["broker_card"])
            card_vars["data"].set(gate["data_card"])
            card_vars["watch"].set(
                gate["watch_card_running"]
                if running
                else gate["watch_card"]
            )
            footer_status.set(
                "Current-day data path verified. "
                + (
                    "Paper Watch is running in paper-only mode."
                    if running
                    else "Paper Watch is ready but not running."
                )
            )
            return gate

        card_vars["broker"].set(gate["broker_card"])
        card_vars["data"].set(gate["data_card"])
        card_vars["watch"].set(
            gate["watch_card_running"]
            if running
            else gate["watch_card"]
        )
        waiting_message = "Waiting for fresh current-day data"
        footer_status.set(
            f"{waiting_message}: {gate['message']}"
        )

        warning_key = (
            f"{gate['today']}|{gate['state']}|"
            f"{gate['workflow_status']}|{gate['workflow_stage']}"
        )
        previous = getattr(
            apply_paper_watch_auth_gate,
            "_warning_key",
            "",
        )

        if show_warning and previous != warning_key:
            setattr(
                apply_paper_watch_auth_gate,
                "_warning_key",
                warning_key,
            )
            root.after_idle(
                lambda title=gate["warning_title"],
                message=gate["warning_message"]: messagebox.showwarning(
                    title,
                    message,
                )
            )

        return gate

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
            selected["market_data_status"]["status"]
            .replace("_", " ")
            .title()
        )

        if controller.is_running():
            card_vars["watch"].set("Running in background")
        else:
            watch = payload["paper_watch"]["watch_status"]
            card_vars["watch"].set(
                watch.replace("_", " ").title()
            )

        footer_status.set("Status refreshed.")
        apply_paper_watch_auth_gate(show_warning=True)

        current_page = active_page.get()
        if current_page != "Overview":
            root.after_idle(
                lambda value=current_page: show_page(value, True)
            )

    def refresh_status_async() -> None:
        # Refresh startup status off the Tkinter UI thread.

        def worker() -> None:
            try:
                payload = app_status_payload(workspace)
                architecture = architecture_payload(workspace)
                running = controller.is_running()
                error = ""
            except Exception as exc:
                payload = {}
                architecture = {}
                running = False
                error = f"{type(exc).__name__}: {exc}"

            def apply_result() -> None:
                if error:
                    footer_status.set(
                        "Background status refresh failed safely. "
                        "Use Refresh All Status to retry."
                    )
                    return

                broker_id = selected_broker.get()
                selected = next(
                    (
                        item
                        for item in architecture.get("brokers", [])
                        if item.get("broker_id") == broker_id
                    ),
                    None,
                )
                if selected is None:
                    footer_status.set(
                        "Broker status is temporarily unavailable."
                    )
                    return

                card_vars["internet"].set(
                    payload.get("internet", {}).get("status", "UNKNOWN")
                )
                card_vars["broker"].set(
                    f"{selected['display_name']}: "
                    f"{selected['connection_test']['status'].replace('_', ' ').title()}"
                )
                card_vars["data"].set(
                    selected["market_data_status"]["status"]
                    .replace("_", " ")
                    .title()
                )
                if running:
                    card_vars["watch"].set("Running in background")
                else:
                    watch = (
                        payload.get("paper_watch", {})
                        .get("watch_status", "NOT_STARTED")
                    )
                    card_vars["watch"].set(
                        str(watch).replace("_", " ").title()
                    )

                footer_status.set("Status refreshed.")
                current_page = active_page.get()
                if current_page != "Overview":
                    root.after_idle(
                        lambda value=current_page: show_page(value, True)
                    )
                apply_paper_watch_auth_gate(show_warning=True)

            root.after(0, apply_result)

        threading.Thread(target=worker, daemon=True).start()

    def start_watch() -> None:
        gate = paper_watch_auth_gate(workspace)
        if not gate["allowed"]:
            apply_paper_watch_auth_gate(show_warning=False)
            messagebox.showwarning(
                gate["warning_title"],
                gate["warning_message"],
            )
            return

        result = controller.start()
        footer_status.set(
            result["status"].replace("_", " ").title()
        )
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
            today_report = current_day_report_status(workspace)
            report_state = (
                "TODAY READY"
                if today_report["today_ready"]
                else today_report["state"].replace("_", " ")
            )
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
        clear_operator_busy('Market-data refresh finished.')
        message = operation.get("message", "Market-data refresh finished.")
        footer_status.set(message)
        if operation.get("status") == "PASS":
            messagebox.showinfo("Market Data", message)
        elif operation.get("status") == "FAILED":
            messagebox.showerror("Market Data", message)

    operator_busy_state = {"count": 0}

    def set_operator_busy(message: str) -> None:
        operator_busy_state["count"] += 1
        footer_status.set(message)
        try:
            root.configure(cursor="watch")
            root.update_idletasks()
        except tk.TclError:
            pass

    def clear_operator_busy(message: str) -> None:
        operator_busy_state["count"] = max(
            0, operator_busy_state["count"] - 1
        )
        if operator_busy_state["count"] == 0:
            try:
                root.configure(cursor="")
            except tk.TclError:
                pass
        footer_status.set(message)

    def show_safe_operation_error(
        title: str,
        action: str,
        exc: BaseException,
    ) -> None:
        message = (
            f"{action} could not complete safely "
            f"({type(exc).__name__}).\n\n"
            "No real order was sent. Check the connection and try again."
        )
        clear_operator_busy(message.splitlines()[0])
        messagebox.showerror(title, message)

    def run_market_data_refresh() -> None:
        try:
            set_operator_busy('Refreshing market data safely...')
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
            show_safe_operation_error('Market Data', 'Market-data refresh', exc)
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
        dialog.configure(bg=palette.get("bg", palette.get("app_bg", "#0b1220")))
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
        dialog.configure(bg=palette.get("bg", palette.get("app_bg", "#0b1220")))
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
                detail = str(exc).strip()
                if secret_key:
                    detail = detail.replace(secret_key, "[REDACTED]")
                if auth_code:
                    detail = detail.replace(auth_code, "[REDACTED]")
                detail = " ".join(detail.split())[:500]
                safe_error = (
                    "Token refresh failed: "
                    + (
                        detail
                        if detail
                        else type(exc).__name__
                    )
                )
                root.after(
                    0,
                    lambda message=safe_error: finish_exchange(
                        None,
                        message,
                    ),
                )

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
            clear_operator_busy('Safe broker data test finished.')
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
            set_operator_busy('Running the safe broker data test...')
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
            show_safe_operation_error('Safe Data Test', 'Safe broker data test', exc)
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
            replay = recorded_replay_status(workspace)
            if replay["ready"]:
                report = Path(replay["report_path"])
                os.startfile(str(report))
                footer_status.set(
                    f"Opened recorded replay report: {report.name}"
                )
                refresh_daily_operations(False)
                return

            freshness = current_day_report_status(workspace)
            if not freshness["today_ready"]:
                messagebox.showwarning(
                    "Today's Trader Report",
                    replay["message"] + "\n\n" + freshness["message"],
                )
                footer_status.set(freshness["message"])
                return

            report = ensure_trader_report(workspace)
            if report is None or not report.exists():
                messagebox.showinfo(
                    "Today's Trader Report",
                    "Today's readable trader HTML is not ready yet.",
                )
                return
            os.startfile(str(report))
            footer_status.set(f"Opened today's trader report: {report.name}")
            refresh_daily_operations(False)
        except Exception as exc:
            footer_status.set("Today's trader report could not be opened.")
            messagebox.showerror("Today's Trader Report", str(exc))

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

        # HQE_BROKER_CONNECT_SCROLL_V1
        broker_scroll_shell = tk.Frame(
            page_panel,
            bg=palette["background"],
        )
        broker_scroll_shell.pack(fill="both", expand=True)

        broker_scroll_canvas = tk.Canvas(
            broker_scroll_shell,
            bg=palette["background"],
            highlightthickness=0,
            borderwidth=0,
        )
        broker_scrollbar = ttk.Scrollbar(
            broker_scroll_shell,
            orient="vertical",
            command=broker_scroll_canvas.yview,
        )
        broker_scroll_canvas.configure(
            yscrollcommand=broker_scrollbar.set,
        )
        broker_scrollbar.pack(side="right", fill="y")
        broker_scroll_canvas.pack(
            side="left",
            fill="both",
            expand=True,
        )

        broker_scroll_inner = tk.Frame(
            broker_scroll_canvas,
            bg=palette["background"],
        )
        broker_scroll_window = broker_scroll_canvas.create_window(
            (0, 0),
            window=broker_scroll_inner,
            anchor="nw",
        )

        def _sync_broker_connect_scroll(_event=None) -> None:
            try:
                broker_scroll_canvas.itemconfigure(
                    broker_scroll_window,
                    width=max(
                        1,
                        broker_scroll_canvas.winfo_width(),
                    ),
                )
                bounds = broker_scroll_canvas.bbox("all")
                if bounds is not None:
                    broker_scroll_canvas.configure(
                        scrollregion=bounds,
                    )
            except tk.TclError:
                return

        def _broker_connect_mousewheel(event):
            try:
                broker_scroll_canvas.yview_scroll(
                    -1 if event.delta > 0 else 1,
                    "units",
                )
                return "break"
            except tk.TclError:
                return None

        def _bind_broker_connect_scroll(widget) -> None:
            widget.bind(
                "<MouseWheel>",
                _broker_connect_mousewheel,
                add="+",
            )
            for child in widget.winfo_children():
                _bind_broker_connect_scroll(child)

        broker_scroll_inner.bind(
            "<Configure>",
            _sync_broker_connect_scroll,
        )
        broker_scroll_canvas.bind(
            "<Configure>",
            _sync_broker_connect_scroll,
        )

        intro = page_card(
            broker_scroll_inner,
            "Connection policy",
            "Broker connections are market-data only. "
            "Real orders and broker execution remain hard locked.",
        )
        intro.pack(fill="x", pady=(0, 12))

        architecture = architecture_payload(workspace)
        grid = tk.Frame(
            broker_scroll_inner,
            bg=palette["background"],
        )
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
            text="Fyers Login & Token Refresh",
            style="HQE.TButton",
            command=open_fyers_auth_dialog,
        ).pack(anchor="e", pady=(12, 0))

        ttk.Button(
            broker_scroll_inner,
            text="Open Guided Broker Connect",
            style="HQE.TButton",
            command=open_broker_connect_center,
        ).pack(
            anchor="e",
            padx=(0, 12),
            pady=(12, 18),
        )

        _bind_broker_connect_scroll(broker_scroll_canvas)
        _bind_broker_connect_scroll(broker_scroll_inner)
        _sync_broker_connect_scroll()

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
        page_title.set("Trader Report")
        page_subtitle.set(
            "Current IST report, genuine recorded replay and evidence"
        )
        clear_page_panel()

        replay = recorded_replay_status(workspace)
        freshness = current_day_report_status(workspace)

        if replay["ready"]:
            decisions = replay["decision_counts"]
            accepted = replay["accepted_side_counts"]
            report_value = (
                "RECORDED REPLAY READY\n"
                f"Trading date: {replay['today_pretty']}\n"
                f"Evaluations: {replay['evaluation_count']}\n"
                f"SMC: LONG={decisions.get('LONG', 0)} | "
                f"SHORT={decisions.get('SHORT', 0)} | "
                f"NEUTRAL={decisions.get('NEUTRAL', 0)}\n"
                f"Accepted: CE_BUY={accepted.get('CE_BUY', 0)} | "
                f"PE_BUY={accepted.get('PE_BUY', 0)}\n"
                "LONG -> CE BUY | SHORT -> PE BUY | "
                "NEUTRAL -> NO TRADE\n"
                "No position or P&L was created.\n"
                f"Report: {replay['report_path']}"
            )
            evidence_text = (
                "Verified recorded-replay JSON evidence:\n"
                f"{replay['summary_path']}\n\n"
                "Evaluation CSV:\n"
                f"{replay['evaluations_path']}"
            )
        elif freshness["today_ready"]:
            available = today_report_candidates(workspace)
            latest = available[0] if available else None
            report_value = (
                f"Today's trader report is ready: {latest.name}\n"
                f"Trading date: {freshness['today_pretty']}\n"
                f"Location: {latest.parent}"
                if latest is not None
                else freshness["message"]
            )
            evidence_text = (
                "Today's technical evidence:\n"
                f"{freshness['evidence_path'] or 'Not available'}"
            )
        else:
            report_value = (
                freshness["message"] + "\n\n"
                + replay["message"]
            )
            evidence_text = (
                "No verified current-day evidence is available "
                "on this computer yet."
            )

        page_card(
            page_panel,
            "Current-day trader report status",
            report_value,
        ).pack(fill="x", pady=(0, 12))

        page_card(
            page_panel,
            "Technical evidence status",
            evidence_text,
        ).pack(fill="x", pady=(0, 12))

        def open_page_evidence() -> None:
            if replay["ready"]:
                path = Path(replay["summary_path"])
                if not path.exists():
                    messagebox.showerror(
                        "Recorded Replay Evidence",
                        f"Evidence file is missing: {path}",
                    )
                    return
                os.startfile(str(path))
                footer_status.set(
                    f"Opened recorded replay evidence: {path.name}"
                )
                return
            open_latest_evidence()

        actions = tk.Frame(page_panel, bg=palette["background"])
        actions.pack(fill="x", pady=(8, 0))

        ttk.Button(
            actions,
            text="Open Trader Report",
            style="HQE.TButton",
            command=open_report,
        ).pack(side="left", padx=(0, 8))

        if replay["ready"]:
            ttk.Button(
                actions,
                text="Open Recorded Replay Evidence (JSON)",
                style="Secondary.TButton",
                command=open_page_evidence,
            ).pack(side="left", padx=8)
        else:
            ttk.Button(
                actions,
                text="Open Technical Evidence (JSON)",
                style="Secondary.TButton",
                command=open_page_evidence,
            ).pack(side="left", padx=8)

        ttk.Button(
            actions,
            text="Open Evidence Folder",
            style="Secondary.TButton",
            command=open_workspace,
        ).pack(side="left", padx=8)

        ttk.Button(
            actions,
            text="Refresh Trader Report",
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
    ).pack(fill="x", padx=28, pady=7)

    ttk.Button(
        action_panel,
        text="Start Paper Watch",
        style="HQE.TButton",
        command=start_watch,
    ).pack(fill="x", padx=28, pady=7)

    ttk.Button(
        action_panel,
        text="Stop Paper Watch",
        style="Secondary.TButton",
        command=stop_watch,
    ).pack(fill="x", padx=28, pady=7)

    broker_health_panel = tk.Frame(
        action_panel,
        bg=palette["panel_alt"],
        highlightbackground=palette["border"],
        highlightthickness=1,
    )
    broker_health_panel.pack(fill="x", padx=18, pady=(4, 8))
    broker_health_panel.pack_forget()

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
    ).pack(fill="x", padx=28, pady=7)

    ttk.Button(
        action_panel,
        text="Run Safe Data Test",
        style="Secondary.TButton",
        command=run_safe_broker_data_test,
    ).pack(fill="x", padx=28, pady=7)

    ttk.Button(
        action_panel,
        text="Broker Connect Center",
        style="Secondary.TButton",
        command=open_broker_connect_center,
    ).pack(fill="x", padx=28, pady=7)

    tk.Label(
        action_panel, text="Embedded Live Status", bg=palette["panel"],
        fg=palette["accent"], font=("Segoe UI", 10, "bold"), anchor="w",
    ).pack(fill="x", padx=18, pady=(10, 2))
    tk.Label(
        action_panel, textvariable=daily_ops_status, bg=palette["panel"],
        fg=palette["muted"], justify="left", anchor="w", wraplength=255,
        font=("Segoe UI", 9),
    ).pack(fill="x", padx=18, pady=(0, 7))
    ttk.Button(action_panel, text="Prepare Next Market Day", style="Secondary.TButton", command=prepare_next_market_day).pack(fill="x", padx=28, pady=7)
    ttk.Button(action_panel, text="Run Day Rollover Guard", style="Secondary.TButton", command=run_day_rollover_guard).pack(fill="x", padx=28, pady=7)
    ttk.Button(action_panel, text="Generate Daily Close Report", style="Secondary.TButton", command=generate_daily_close_report).pack(fill="x", padx=28, pady=7)
    ttk.Button(action_panel, text="Refresh Trader Report", style="Secondary.TButton", command=refresh_latest_report).pack(fill="x", padx=28, pady=7)
    ttk.Button(action_panel, text="Open Technical Evidence (JSON)", style="Secondary.TButton", command=open_latest_evidence).pack(fill="x", padx=28, pady=7)

    ttk.Button(
        action_panel,
        text="Open Trader Report",
        style="Secondary.TButton",
        command=open_report,
    ).pack(fill="x", padx=28, pady=7)

    ttk.Button(
        action_panel,
        text="Open Evidence Folder",
        style="Secondary.TButton",
        command=open_workspace,
    ).pack(fill="x", padx=28, pady=7)

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
    refresh_status_async()
    # HQE_STABILIZATION_STARTUP_V1
    root.after(15000, refresh_status_async)
    root.after(1200, lambda: refresh_daily_operations(False))

    def _deferred_fyers_startup() -> None:
        try:
            apply_stored_fyers_environment(overwrite=True)
            refresh_fyers_auth_status()
        except Exception as exc:
            footer_status.set(
                f"Broker startup refresh failed safely: {exc}"
            )

    root.after(1700, _deferred_fyers_startup)
    root.after(2400, lambda: refresh_broker_data_health(False))
    root.after(3100, lambda: refresh_market_data_center(False))

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
        clear_operator_busy('Daily startup operation finished.')
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
            set_operator_busy('Preparing the next market day safely...')
            launch_daily_startup_worker(repo_root(), workspace)
            daily_startup_status.set("Preparing next market day safely...")
            footer_status.set(
                "Next-day preparation running. Real orders remain blocked."
            )
            root.after(900, poll_daily_startup_operation)
        except Exception as exc:
            show_safe_operation_error('Daily Startup', 'Next-day preparation', exc)
            footer_status.set(
                f"Next-day preparation could not start: {exc}"
            )

    def open_daily_startup_center() -> None:
        snapshot = refresh_daily_startup_center(False)
        dialog = tk.Toplevel(root)
        dialog.title("HQE — Daily Startup & Checklist")
        dialog.geometry("700x560")
        dialog.configure(bg=palette.get("bg", palette.get("app_bg", "#0b1220")))
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
    daily_startup_panel.pack_forget()

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
    ).pack(fill="x", padx=28, pady=7)

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
        if kind == "report":
            open_report()
            return

        snapshot = refresh_daily_close_center(False)
        raw_path = str(
            snapshot.get("latest_evidence", "")
        ).strip()
        if not raw_path:
            messagebox.showwarning(
                "Daily Close & Report",
                "No latest technical evidence is available yet.",
            )
            return

        path = Path(raw_path)
        if not path.exists():
            messagebox.showerror(
                "Daily Close & Report",
                f"Latest technical evidence is missing: {path}",
            )
            return

        try:
            os.startfile(path)
        except Exception as exc:
            messagebox.showerror(
                "Daily Close & Report",
                str(exc),
            )

    def open_daily_close_center() -> None:
        snapshot = refresh_daily_close_center(False)
        dialog = tk.Toplevel(root)
        dialog.title("HQE — Daily Close & Report")
        dialog.geometry("700x540")
        dialog.configure(bg=palette.get("bg", palette.get("app_bg", "#0b1220")))
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
            text="Open Trader Report",
            command=lambda: open_daily_close_artifact("report"),
        ).pack(fill="x", pady=3)

        ttk.Button(
            frame,
            text="Open Technical Evidence (JSON)",
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
    daily_close_panel.pack_forget()

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
    ).pack(fill="x", padx=28, pady=7)

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
        dialog.configure(bg=palette.get("bg", palette.get("app_bg", "#0b1220")))
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
    session_history_panel.pack_forget()

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
    ).pack(fill="x", padx=28, pady=7)



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
        dialog.configure(bg=palette.get("bg", palette.get("app_bg", "#0b1220")))
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
    safety_evidence_panel.pack_forget()

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
    ).pack(fill="x", padx=28, pady=7)

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
            if operation.lower() == "start":
                gate = paper_watch_auth_gate(workspace)
                if not gate["allowed"]:
                    apply_paper_watch_auth_gate(
                        show_warning=False,
                    )
                    paper_watch_status.set(gate["message"])
                    messagebox.showwarning(
                        gate["warning_title"],
                        gate["warning_message"],
                    )
                    return

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
        dialog.configure(bg=palette.get("bg", palette.get("app_bg", "#0b1220")))
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
    paper_watch_panel.pack_forget()

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
    ).pack(fill="x", padx=28, pady=7)

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
        dialog.configure(bg=palette.get("bg", palette.get("app_bg", "#0b1220")))
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
    operator_dashboard_panel.pack_forget()

    tk.Label(
        operator_dashboard_panel,
        text="PRIMARY DAILY WORKFLOW",
        bg=palette["panel_alt"],
        fg=palette["text"],
        font=("Segoe UI Semibold", 11),
        anchor="w",
        padx=10,
        pady=8,
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
            footer_status.set("Market-data cache index rebuild started.")
            messagebox.showinfo(
                "Market Data Quality Center",
                "Cache index rebuild started safely in the background.",
            )
        except Exception as exc:
            footer_status.set(f"Cache-index rebuild failed safely: {exc}")
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
        dialog.configure(bg=palette.get("bg", palette.get("app_bg", "#0b1220")))
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
    market_data_quality_panel.pack_forget()

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
    ).pack(fill="x", padx=28, pady=7)



    strategy_pack_status = tk.StringVar(
        value="Strategy-pack registry will appear after refresh."
    )

    def refresh_strategy_pack_center(
        show_dialog: bool = False,
    ) -> dict:
        try:
            snapshot = strategy_pack_center_snapshot(
                repo_root(),
                workspace,
            )
            strategy_pack_status.set(snapshot["display_text"])
            footer_status.set(snapshot["display_text"])
            if show_dialog:
                messagebox.showinfo(
                    "Strategy Pack Center",
                    snapshot["display_text"],
                )
            return snapshot
        except Exception as exc:
            strategy_pack_status.set(
                "Strategy-pack refresh failed safely."
            )
            footer_status.set(f"Strategy-pack error: {exc}")
            if show_dialog:
                messagebox.showerror(
                    "Strategy Pack Center",
                    str(exc),
                )
            return {}

    def open_strategy_pack_center() -> None:
        from tkinter import filedialog, simpledialog

        snapshot = refresh_strategy_pack_center(False)
        all_packs = list(snapshot.get("packs", []))

        dialog = tk.Toplevel(root)
        dialog.title("HQE — Strategy Pack Center")
        dialog.geometry("1040x680")
        dialog.configure(bg=palette.get("bg", palette.get("app_bg", "#0b1220")))
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
            text="Strategy Pack Center",
            bg=palette["panel"],
            fg=palette["text"],
            font=("Segoe UI Semibold", 18),
            anchor="w",
        ).pack(fill="x")

        tk.Label(
            outer,
            text=(
                "Built-ins • Versioning • Import/Export • "
                "Locked Validation Candidate"
            ),
            bg=palette["panel"],
            fg=palette["muted"],
            anchor="w",
            pady=4,
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
        ).pack(fill="x", pady=(8, 10))

        body = tk.Frame(outer, bg=palette["panel"])
        body.pack(fill="both", expand=True)

        pack_list = tk.Listbox(
            body,
            width=45,
            exportselection=False,
        )
        pack_list.pack(
            side="left",
            fill="both",
            expand=False,
        )

        detail_var = tk.StringVar()
        detail = tk.Label(
            body,
            textvariable=detail_var,
            bg=palette["panel_alt"],
            fg=palette["muted"],
            justify="left",
            anchor="nw",
            wraplength=530,
            padx=12,
            pady=12,
        )
        detail.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(12, 0),
        )

        visible_packs: list[dict] = []

        def selected_pack() -> dict:
            selection = pack_list.curselection()
            if not selection:
                return {}
            index = int(selection[0])
            if index >= len(visible_packs):
                return {}
            return visible_packs[index]

        def show_selected(_event=None) -> None:
            record = selected_pack()
            if not record:
                detail_var.set("Select a strategy pack.")
                return
            payload = record.get("payload", {})
            safety = payload.get("safety", {})
            validation = payload.get("validation", {})
            detail_var.set(
                f"Name: {record.get('name', '')}\n"
                f"ID: {record.get('strategy_id', '')}\n"
                f"Version: {record.get('version', '')}\n"
                f"Category: {record.get('category', '')}\n"
                f"Status: {record.get('status', '')}\n"
                f"Source: {record.get('source', '')}\n"
                f"Valid: {record.get('valid', False)}\n"
                f"Locked candidate: "
                f"{validation.get('locked_candidate', False)}\n"
                f"Candidate ID: "
                f"{validation.get('candidate_id', '')}\n"
                f"Paper only: {safety.get('paper_only', False)}\n"
                f"Option selling blocked: "
                f"{safety.get('no_option_selling', False)}\n\n"
                f"{payload.get('description', '')}\n\n"
                f"Path:\n{record.get('path', '')}"
            )

        def populate(current: dict) -> None:
            nonlocal all_packs
            all_packs = list(current.get("packs", []))
            visible_packs.clear()
            pack_list.delete(0, "end")
            for record in all_packs:
                visible_packs.append(record)
                validity = "VALID" if record.get("valid") else "INVALID"
                pack_list.insert(
                    "end",
                    f"[{validity}] {record.get('name', '')} | "
                    f"{record.get('version', '')} | "
                    f"{record.get('source', '')}",
                )
            if visible_packs:
                pack_list.selection_set(0)
                show_selected()

        def refresh_dialog() -> None:
            current = refresh_strategy_pack_center(False)
            summary_var.set(current.get("display_text", ""))
            populate(current)

        def import_from_file() -> None:
            selected = filedialog.askopenfilename(
                parent=dialog,
                title="Import Strategy Pack",
                filetypes=[("HQE Strategy Pack", "*.json")],
            )
            if not selected:
                return
            try:
                target = import_strategy_pack(
                    Path(selected),
                    repo_root(),
                    workspace,
                )
                messagebox.showinfo(
                    "Strategy Pack Center",
                    f"Imported:\n{target}",
                )
                refresh_dialog()
            except Exception as exc:
                messagebox.showerror(
                    "Strategy Pack Center",
                    str(exc),
                )

        def export_selected() -> None:
            record = selected_pack()
            if not record:
                messagebox.showwarning(
                    "Strategy Pack Center",
                    "Select a strategy pack first.",
                )
                return
            try:
                target = export_strategy_pack(
                    Path(record["path"]),
                    repo_root(),
                    workspace,
                )
                messagebox.showinfo(
                    "Strategy Pack Center",
                    f"Exported:\n{target}",
                )
            except Exception as exc:
                messagebox.showerror(
                    "Strategy Pack Center",
                    str(exc),
                )

        def clone_selected() -> None:
            record = selected_pack()
            if not record:
                messagebox.showwarning(
                    "Strategy Pack Center",
                    "Select a strategy pack first.",
                )
                return
            new_id = simpledialog.askstring(
                "Clone Strategy Pack",
                "New strategy ID:",
                parent=dialog,
            )
            if not new_id:
                return
            new_name = simpledialog.askstring(
                "Clone Strategy Pack",
                "New strategy name:",
                parent=dialog,
            )
            if not new_name:
                return
            try:
                target = clone_strategy_pack(
                    Path(record["path"]),
                    repo_root(),
                    workspace,
                    new_strategy_id=new_id,
                    new_name=new_name,
                )
                messagebox.showinfo(
                    "Strategy Pack Center",
                    f"Draft created:\n{target}",
                )
                refresh_dialog()
            except Exception as exc:
                messagebox.showerror(
                    "Strategy Pack Center",
                    str(exc),
                )

        def open_selected_file() -> None:
            record = selected_pack()
            if not record:
                return
            path = Path(record["path"])
            if not path.exists():
                messagebox.showerror(
                    "Strategy Pack Center",
                    f"Pack file is missing: {path}",
                )
                return
            try:
                os.startfile(path)
            except Exception as exc:
                messagebox.showerror(
                    "Strategy Pack Center",
                    str(exc),
                )

        pack_list.bind("<<ListboxSelect>>", show_selected)
        pack_list.bind(
            "<Double-Button-1>",
            lambda _event: open_selected_file(),
        )

        buttons = tk.Frame(outer, bg=palette["panel"])
        buttons.pack(fill="x", pady=(12, 0))

        ttk.Button(
            buttons,
            text="Refresh Packs",
            command=refresh_dialog,
        ).pack(side="left", padx=(0, 6))

        ttk.Button(
            buttons,
            text="Import Strategy Pack",
            command=import_from_file,
        ).pack(side="left", padx=6)

        ttk.Button(
            buttons,
            text="Export Selected Pack",
            command=export_selected,
        ).pack(side="left", padx=6)

        ttk.Button(
            buttons,
            text="Clone Selected as Draft",
            command=clone_selected,
        ).pack(side="left", padx=6)

        ttk.Button(
            buttons,
            text="Open Selected Pack File",
            command=open_selected_file,
        ).pack(side="left", padx=6)

        tk.Label(
            outer,
            text=(
                "PAPER/RESEARCH ONLY • REAL ORDERS BLOCKED • "
                "OPTION SELLING BLOCKED"
            ),
            bg=palette["panel"],
            fg=palette["muted"],
            anchor="w",
            pady=10,
        ).pack(fill="x")

        populate(snapshot)

    strategy_pack_panel = tk.Frame(
        action_panel,
        bg=palette["panel_alt"],
        highlightbackground=palette["border"],
        highlightthickness=1,
    )
    strategy_pack_panel.pack(fill="x", padx=18, pady=(4, 8))
    strategy_pack_panel.pack_forget()

    tk.Label(
        strategy_pack_panel,
        textvariable=strategy_pack_status,
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
        text="Strategy Pack Center",
        style="Secondary.TButton",
        command=open_strategy_pack_center,
    ).pack(fill="x", padx=28, pady=7)



    strategy_builder_status = tk.StringVar(
        value="Strategy Builder & Selector will appear after refresh."
    )

    def refresh_strategy_builder_center(
        show_dialog: bool = False,
    ) -> dict:
        try:
            snapshot = builder_center_snapshot(
                repo_root(),
                workspace,
            )
            strategy_builder_status.set(snapshot["display_text"])
            footer_status.set(snapshot["display_text"])
            if show_dialog:
                messagebox.showinfo(
                    "Strategy Builder & Selector",
                    snapshot["display_text"],
                )
            return snapshot
        except Exception as exc:
            strategy_builder_status.set(
                "Strategy Builder refresh failed safely."
            )
            footer_status.set(f"Strategy Builder error: {exc}")
            if show_dialog:
                messagebox.showerror(
                    "Strategy Builder & Selector",
                    str(exc),
                )
            return {}

    def open_strategy_builder_center() -> None:
        snapshot = refresh_strategy_builder_center(False)

        dialog = tk.Toplevel(root)
        dialog.title("HQE — Strategy Builder & Selector")
        dialog.geometry("1120x760")
        dialog.minsize(980, 680)
        dialog.configure(bg=palette.get("bg", palette.get("app_bg", "#0b1220")))
        dialog.transient(root)

        outer = tk.Frame(
            dialog,
            bg=palette["panel"],
            padx=16,
            pady=14,
        )
        outer.pack(fill="both", expand=True, padx=14, pady=14)

        tk.Label(
            outer,
            text="Strategy Builder & Selector",
            bg=palette["panel"],
            fg=palette["text"],
            font=("Segoe UI Semibold", 18),
            anchor="w",
        ).pack(fill="x")

        active_var = tk.StringVar(
            value=snapshot.get(
                "selection",
                {},
            ).get(
                "display_text",
                "Active paper strategy: none selected",
            )
        )
        tk.Label(
            outer,
            textvariable=active_var,
            bg=palette["panel_alt"],
            fg=palette["muted"],
            anchor="w",
            padx=10,
            pady=8,
        ).pack(fill="x", pady=(8, 10))

        body = tk.Frame(outer, bg=palette["panel"])
        body.pack(fill="both", expand=True)

        form_frame = tk.LabelFrame(
            body,
            text="Visual Paper Strategy Form",
            bg=palette["panel"],
            fg=palette["text"],
            padx=10,
            pady=8,
        )
        form_frame.pack(
            side="left",
            fill="both",
            expand=False,
        )

        preview_frame = tk.LabelFrame(
            body,
            text="Validation Preview",
            bg=palette["panel"],
            fg=palette["text"],
            padx=10,
            pady=8,
        )
        preview_frame.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(12, 0),
        )

        fields = [
            ("strategy_id", "Strategy ID"),
            ("name", "Strategy Name"),
            ("description", "Description"),
            ("category", "Category"),
            ("symbol", "Symbol"),
            ("timeframe", "Timeframe"),
            ("option_sides", "Option Sides"),
            ("minimum_dte", "Minimum DTE"),
            ("ltp_min", "Option LTP Min"),
            ("ltp_max", "Option LTP Max"),
            (
                "minimum_estimated_net_reward",
                "Minimum Estimated Net Reward",
            ),
            ("entry_indicator", "Entry Indicator"),
            ("entry_period", "Entry Period"),
            (
                "confirmation_indicator",
                "Confirmation Indicator",
            ),
            ("confirmation_value", "Confirmation Value"),
            ("er20_min", "ER20 Minimum"),
            ("range24_min", "Range24 Minimum"),
            ("stop_loss_percent", "Stop Loss %"),
            ("target_percent", "Target %"),
            (
                "max_risk_per_trade_percent",
                "Max Paper Risk/Trade %",
            ),
            ("max_trades_per_day", "Max Trades/Day"),
            ("cooldown_bars", "Cooldown Bars"),
        ]

        variables: dict[str, tk.StringVar] = {}
        defaults = snapshot.get("defaults", {})

        for row, (key, label) in enumerate(fields):
            tk.Label(
                form_frame,
                text=label,
                bg=palette["panel"],
                fg=palette["muted"],
                anchor="w",
            ).grid(
                row=row,
                column=0,
                sticky="w",
                padx=(0, 8),
                pady=2,
            )
            value = defaults.get(key, "")
            if isinstance(value, list):
                value = ",".join(str(item) for item in value)
            variable = tk.StringVar(value=str(value))
            variables[key] = variable

            if key == "category":
                widget = ttk.Combobox(
                    form_frame,
                    textvariable=variable,
                    values=(
                        "breakout",
                        "momentum_trend",
                        "reversal",
                        "scalping",
                    ),
                    state="readonly",
                    width=30,
                )
            elif key == "symbol":
                widget = ttk.Combobox(
                    form_frame,
                    textvariable=variable,
                    values=(
                        "NIFTY",
                        "BANKNIFTY",
                        "FINNIFTY",
                        "SENSEX",
                    ),
                    state="readonly",
                    width=30,
                )
            elif key == "timeframe":
                widget = ttk.Combobox(
                    form_frame,
                    textvariable=variable,
                    values=("1m", "3m", "5m", "15m", "30m", "1h"),
                    state="readonly",
                    width=30,
                )
            else:
                widget = ttk.Entry(
                    form_frame,
                    textvariable=variable,
                    width=33,
                )
            widget.grid(
                row=row,
                column=1,
                sticky="ew",
                pady=2,
            )

        preview_text = tk.Text(
            preview_frame,
            wrap="word",
            height=26,
            width=58,
        )
        preview_text.pack(fill="both", expand=True)

        latest_preview = {"pack": None}

        pack_list = tk.Listbox(
            preview_frame,
            height=8,
            exportselection=False,
        )
        pack_list.pack(fill="x", pady=(10, 0))
        visible_packs: list[dict] = []

        def form_payload() -> dict:
            payload = {
                key: variable.get().strip()
                for key, variable in variables.items()
            }
            payload["option_sides"] = variables[
                "option_sides"
            ].get()
            return payload

        def render_preview(result: dict) -> None:
            preview = result["preview"]
            latest_preview["pack"] = result["pack"]
            preview_text.delete("1.0", "end")
            preview_text.insert(
                "end",
                preview.get("summary", ""),
            )
            warnings = preview.get("warnings", [])
            errors = preview.get("errors", [])
            if warnings:
                preview_text.insert(
                    "end",
                    "\n\nWARNINGS:\n- " + "\n- ".join(warnings),
                )
            if errors:
                preview_text.insert(
                    "end",
                    "\n\nERRORS:\n- " + "\n- ".join(errors),
                )
            preview_text.insert(
                "end",
                "\n\nPaper compatible: "
                + str(preview.get("paper_compatible", False)),
            )

        def preview_current() -> None:
            try:
                render_preview(
                    build_strategy_preview(form_payload())
                )
            except Exception as exc:
                latest_preview["pack"] = None
                preview_text.delete("1.0", "end")
                preview_text.insert("end", f"VALIDATION ERROR:\n{exc}")

        def save_current() -> None:
            try:
                target = save_builder_draft(
                    form_payload(),
                    workspace,
                )
                messagebox.showinfo(
                    "Strategy Builder & Selector",
                    f"Draft saved:\n{target}",
                )
                refresh_pack_list()
            except Exception as exc:
                messagebox.showerror(
                    "Strategy Builder & Selector",
                    str(exc),
                )

        def selected_record() -> dict:
            selection = pack_list.curselection()
            if not selection:
                return {}
            index = int(selection[0])
            if index >= len(visible_packs):
                return {}
            return visible_packs[index]

        def select_for_paper() -> None:
            record = selected_record()
            if not record:
                messagebox.showwarning(
                    "Strategy Builder & Selector",
                    "Select a valid strategy pack first.",
                )
                return
            try:
                target = select_paper_pack(
                    Path(record["path"]),
                    workspace,
                )
                messagebox.showinfo(
                    "Strategy Builder & Selector",
                    f"Selected for paper validation:\n{target}",
                )
                refresh_all()
            except Exception as exc:
                messagebox.showerror(
                    "Strategy Builder & Selector",
                    str(exc),
                )

        def clear_selection() -> None:
            clear_paper_selection(workspace)
            refresh_all()

        def refresh_pack_list() -> None:
            current = refresh_strategy_builder_center(False)
            registry = current.get("registry", {})
            visible_packs.clear()
            pack_list.delete(0, "end")
            for record in registry.get("packs", []):
                if not record.get("valid"):
                    continue
                visible_packs.append(record)
                pack_list.insert(
                    "end",
                    f"{record.get('name', '')} | "
                    f"{record.get('version', '')} | "
                    f"{record.get('source', '')}",
                )

        def refresh_all() -> None:
            current = refresh_strategy_builder_center(False)
            active_var.set(
                current.get(
                    "selection",
                    {},
                ).get(
                    "display_text",
                    "Active paper strategy: none selected",
                )
            )
            refresh_pack_list()

        buttons = tk.Frame(outer, bg=palette["panel"])
        buttons.pack(fill="x", pady=(12, 0))

        ttk.Button(
            buttons,
            text="Preview Strategy",
            command=preview_current,
        ).pack(side="left", padx=(0, 6))

        ttk.Button(
            buttons,
            text="Save as Draft",
            command=save_current,
        ).pack(side="left", padx=6)

        ttk.Button(
            buttons,
            text="Select for Paper Validation",
            command=select_for_paper,
        ).pack(side="left", padx=6)

        ttk.Button(
            buttons,
            text="Clear Active Selection",
            command=clear_selection,
        ).pack(side="left", padx=6)

        ttk.Button(
            buttons,
            text="Open Strategy Pack Center",
            command=open_strategy_pack_center,
        ).pack(side="left", padx=6)

        tk.Label(
            outer,
            text=(
                "PAPER SELECTION ONLY • NO STRATEGY EXECUTION • "
                "REAL ORDERS NO • OPTION SELLING NO"
            ),
            bg=palette["panel"],
            fg=palette["muted"],
            anchor="w",
            pady=10,
        ).pack(fill="x")

        refresh_pack_list()
        preview_current()

    strategy_builder_panel = tk.Frame(
        action_panel,
        bg=palette["panel_alt"],
        highlightbackground=palette["border"],
        highlightthickness=1,
    )
    strategy_builder_panel.pack(fill="x", padx=18, pady=(4, 8))
    strategy_builder_panel.pack_forget()

    tk.Label(
        strategy_builder_panel,
        textvariable=strategy_builder_status,
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
        text="Strategy Builder & Selector",
        style="Secondary.TButton",
        command=open_strategy_builder_center,
    ).pack(fill="x", padx=28, pady=7)



    backtest_product_status = tk.StringVar(
        value="Backtest Product Center will appear after refresh."
    )

    def refresh_backtest_product_center(
        show_dialog: bool = False,
    ) -> dict:
        try:
            snapshot = backtest_center_snapshot(
                repo_root(),
                workspace,
            )
            backtest_product_status.set(snapshot["display_text"])
            footer_status.set(snapshot["display_text"])
            if show_dialog:
                messagebox.showinfo(
                    "Backtest Product Center",
                    snapshot["display_text"],
                )
            return snapshot
        except Exception as exc:
            backtest_product_status.set(
                "Backtest Center refresh failed safely."
            )
            footer_status.set(f"Backtest Center error: {exc}")
            if show_dialog:
                messagebox.showerror(
                    "Backtest Product Center",
                    str(exc),
                )
            return {}


    backtest_product_panel = tk.Frame(
        action_panel,
        bg=palette["panel_alt"],
        highlightbackground=palette["border"],
        highlightthickness=1,
    )
    backtest_product_panel.pack(fill="x", padx=18, pady=(4, 8))
    backtest_product_panel.pack_forget()

    tk.Label(
        backtest_product_panel,
        textvariable=backtest_product_status,
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
        text="Backtest Product Center",
        style="Secondary.TButton",
        command=lambda: open_backtest_product_center(),
    ).pack(fill="x", padx=28, pady=7)



    paper_validation_report_status = tk.StringVar(
        value="Paper-validation intelligence will appear after refresh."
    )

    def refresh_paper_validation_report_center(
        show_dialog: bool = False,
    ) -> dict:
        try:
            snapshot = paper_validation_center_snapshot(
                repo_root(),
                workspace,
            )
            paper_validation_report_status.set(
                snapshot["display_text"]
            )
            footer_status.set(snapshot["display_text"])
            if show_dialog:
                messagebox.showinfo(
                    "Paper Validation Intelligence",
                    snapshot["display_text"],
                )
            return snapshot
        except Exception as exc:
            paper_validation_report_status.set(
                "Paper-validation refresh failed safely."
            )
            footer_status.set(
                f"Paper-validation report error: {exc}"
            )
            if show_dialog:
                messagebox.showerror(
                    "Paper Validation Intelligence",
                    str(exc),
                )
            return {}


    def generate_validation_report_pack() -> None:
        try:
            launch_report_pack_worker(
                repo_root(),
                workspace,
            )
            paper_validation_report_status.set(
                "Generating validation report pack safely..."
            )
            footer_status.set(
                "Paper-validation report generation started."
            )
            root.after(1000, poll_validation_report_pack)
        except Exception as exc:
            messagebox.showerror(
                "Paper Validation Intelligence",
                str(exc),
            )

    def open_latest_validation_report(kind: str) -> None:
        snapshot = refresh_paper_validation_report_center(False)
        latest = snapshot.get("latest_report", {})
        key = {
            "html": "html_path",
            "json": "json_path",
            "zip": "zip_path",
            "folder": "report_dir",
        }.get(kind, "report_dir")
        raw_path = str(latest.get(key, "")).strip()
        if not raw_path:
            messagebox.showwarning(
                "Paper Validation Intelligence",
                "No generated validation report is available yet.",
            )
            return
        path = Path(raw_path)
        if not path.exists():
            messagebox.showerror(
                "Paper Validation Intelligence",
                f"Report path is missing: {path}",
            )
            return
        try:
            os.startfile(path)
        except Exception as exc:
            messagebox.showerror(
                "Paper Validation Intelligence",
                str(exc),
            )

    def open_paper_validation_report_center() -> None:
        snapshot = refresh_paper_validation_report_center(False)

        dialog = tk.Toplevel(root)
        dialog.title("HQE — Paper Validation Intelligence")
        dialog.geometry("1080x740")
        dialog.minsize(940, 650)
        dialog.configure(bg=palette.get("bg", palette.get("app_bg", "#0b1220")))
        dialog.transient(root)

        outer = tk.Frame(
            dialog,
            bg=palette["panel"],
            padx=16,
            pady=14,
        )
        outer.pack(fill="both", expand=True, padx=14, pady=14)

        tk.Label(
            outer,
            text="Paper Validation Intelligence & Reports",
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
            anchor="w",
            padx=10,
            pady=8,
        ).pack(fill="x", pady=(8, 10))

        top = tk.Frame(outer, bg=palette["panel"])
        top.pack(fill="x")

        decision_var = tk.StringVar()
        progress_var = tk.StringVar()
        drift_var = tk.StringVar()

        for title, variable in (
            ("Decision", decision_var),
            ("Progress", progress_var),
            ("Strategy Drift", drift_var),
        ):
            card = tk.LabelFrame(
                top,
                text=title,
                bg=palette["panel"],
                fg=palette["text"],
                padx=10,
                pady=8,
            )
            card.pack(
                side="left",
                fill="both",
                expand=True,
                padx=4,
            )
            tk.Label(
                card,
                textvariable=variable,
                bg=palette["panel"],
                fg=palette["muted"],
                justify="left",
                anchor="nw",
                wraplength=300,
            ).pack(fill="both", expand=True)

        body = tk.Frame(outer, bg=palette["panel"])
        body.pack(fill="both", expand=True, pady=(12, 0))

        weekly_frame = tk.LabelFrame(
            body,
            text="Weekly Summary",
            bg=palette["panel"],
            fg=palette["text"],
            padx=8,
            pady=8,
        )
        weekly_frame.pack(
            side="left",
            fill="both",
            expand=True,
        )

        reason_frame = tk.LabelFrame(
            body,
            text="No-Trade Reasons",
            bg=palette["panel"],
            fg=palette["text"],
            padx=8,
            pady=8,
        )
        reason_frame.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(12, 0),
        )

        weekly_list = tk.Listbox(
            weekly_frame,
            exportselection=False,
        )
        weekly_list.pack(fill="both", expand=True)

        reason_list = tk.Listbox(
            reason_frame,
            exportselection=False,
        )
        reason_list.pack(fill="both", expand=True)

        def render(current: dict) -> None:
            summary_var.set(current.get("display_text", ""))
            decision = current.get("decision", {})
            progress = current.get("progress", {})
            drift = current.get("strategy_drift", {})

            decision_var.set(
                f"{decision.get('status', '')}\n"
                f"{decision.get('message', '')}"
            )
            progress_var.set(
                f"Days: {progress.get('observed_days', 0)}/"
                f"{progress.get('minimum_days', 20)}\n"
                f"Trades: {progress.get('observed_trades', 0)}/"
                f"{progress.get('minimum_trades', 30)}\n"
                f"Expiry weeks: {progress.get('expiry_weeks', 0)}/"
                f"{progress.get('minimum_expiry_weeks', 4)}\n"
                f"Valid trade days: "
                f"{progress.get('valid_trade_days', 0)}\n"
                f"No-trade days: "
                f"{progress.get('no_trade_days', 0)}"
            )
            drift_var.set(
                f"{drift.get('status', '')}\n"
                f"{drift.get('message', '')}"
            )

            weekly_list.delete(0, "end")
            for item in current.get("weekly_summaries", []):
                weekly_list.insert(
                    "end",
                    f"{item.get('iso_week', '')} | "
                    f"days {item.get('observed_days', 0)} | "
                    f"trades {item.get('trade_count', 0)} | "
                    f"no-trade {item.get('no_trade_days', 0)}",
                )

            reason_list.delete(0, "end")
            for item in current.get("no_trade_reasons", []):
                reason_list.insert(
                    "end",
                    f"{item.get('reason', '')} | "
                    f"{item.get('count', 0)} days | "
                    f"{item.get('percent_of_no_trade_days', 0)}%",
                )

        def refresh_dialog() -> None:
            render(refresh_paper_validation_report_center(False))

        buttons = tk.Frame(outer, bg=palette["panel"])
        buttons.pack(fill="x", pady=(12, 0))

        ttk.Button(
            buttons,
            text="Refresh Validation Status",
            command=refresh_dialog,
        ).pack(side="left", padx=(0, 6))

        ttk.Button(
            buttons,
            text="Generate Report Pack",
            command=generate_validation_report_pack,
        ).pack(side="left", padx=6)

        ttk.Button(
            buttons,
            text="Open Latest HTML Report",
            command=lambda: open_latest_validation_report("html"),
        ).pack(side="left", padx=6)

        ttk.Button(
            buttons,
            text="Open Latest JSON Report",
            command=lambda: open_latest_validation_report("json"),
        ).pack(side="left", padx=6)

        ttk.Button(
            buttons,
            text="Open Latest ZIP Pack",
            command=lambda: open_latest_validation_report("zip"),
        ).pack(side="left", padx=6)

        tk.Label(
            outer,
            text=(
                "PAPER/DATA ONLY • FORMAL REVIEW IS NOT REAL-TRADING "
                "APPROVAL • THIS IS NOT A PROFITABILITY CLAIM"
            ),
            bg=palette["panel"],
            fg=palette["muted"],
            anchor="w",
            pady=10,
        ).pack(fill="x")

        render(snapshot)

    paper_validation_report_panel = tk.Frame(
        action_panel,
        bg=palette["panel_alt"],
        highlightbackground=palette["border"],
        highlightthickness=1,
    )
    paper_validation_report_panel.pack(
        fill="x",
        padx=18,
        pady=(4, 8),
    )
    paper_validation_report_panel.pack_forget()

    tk.Label(
        paper_validation_report_panel,
        textvariable=paper_validation_report_status,
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
        text="Paper Validation Intelligence",
        style="Secondary.TButton",
        command=open_paper_validation_report_center,
    ).pack(fill="x", padx=28, pady=7)



    release_center_status = tk.StringVar(
        value="Windows Release Center will appear after refresh."
    )

    def refresh_release_center(
        show_dialog: bool = False,
    ) -> dict:
        try:
            snapshot = release_center_snapshot(
                repo_root(),
                workspace,
            )
            release_center_status.set(snapshot["display_text"])
            footer_status.set(snapshot["display_text"])
            if show_dialog:
                messagebox.showinfo(
                    "Windows Release Center",
                    snapshot["display_text"],
                )
            return snapshot
        except Exception as exc:
            release_center_status.set(
                "Release Center refresh failed safely."
            )
            footer_status.set(f"Release Center error: {exc}")
            if show_dialog:
                messagebox.showerror(
                    "Windows Release Center",
                    str(exc),
                )
            return {}


    def run_release_operation(
        operation: str,
        source_zip: str = "",
    ) -> None:
        try:
            launch_release_operation(
                repo_root(),
                workspace,
                operation,
                source_zip,
            )
            release_center_status.set(
                f"Release operation {operation} is running safely..."
            )
            footer_status.set(
                "Release operation running. Trading remains locked."
            )
            root.after(1000, poll_release_operation)
        except Exception as exc:
            messagebox.showerror(
                "Windows Release Center",
                str(exc),
            )

    def install_desktop_shortcut() -> None:
        try:
            launch_desktop_shortcut_install(repo_root())
            messagebox.showinfo(
                "Windows Release Center",
                "Desktop shortcut installation started.",
            )
        except Exception as exc:
            messagebox.showerror(
                "Windows Release Center",
                str(exc),
            )

    def open_release_output(kind: str) -> None:
        snapshot = refresh_release_center(False)
        latest = snapshot.get("latest_outputs", {})
        key = {
            "backup": "latest_backup",
            "restore": "latest_restore_staging",
            "diagnostics": "latest_diagnostics",
            "rc": "latest_rc_report",
        }.get(kind, "latest_rc_report")
        raw_path = str(latest.get(key, "")).strip()
        if not raw_path:
            messagebox.showwarning(
                "Windows Release Center",
                f"No {kind} output is available yet.",
            )
            return
        path = Path(raw_path)
        if not path.exists():
            messagebox.showerror(
                "Windows Release Center",
                f"Output path is missing: {path}",
            )
            return
        try:
            os.startfile(path)
        except Exception as exc:
            messagebox.showerror(
                "Windows Release Center",
                str(exc),
            )

    def open_release_center() -> None:
        from tkinter import filedialog

        snapshot = refresh_release_center(False)

        dialog = tk.Toplevel(root)
        dialog.title("HQE — Windows Release Center")
        dialog.geometry("1040x720")
        dialog.minsize(900, 620)
        dialog.configure(bg=palette.get("bg", palette.get("app_bg", "#0b1220")))
        dialog.transient(root)

        outer = tk.Frame(
            dialog,
            bg=palette["panel"],
            padx=16,
            pady=14,
        )
        outer.pack(fill="both", expand=True, padx=14, pady=14)

        tk.Label(
            outer,
            text="Windows Release Center",
            bg=palette["panel"],
            fg=palette["text"],
            font=("Segoe UI Semibold", 18),
            anchor="w",
        ).pack(fill="x")

        tk.Label(
            outer,
            text=(
                "One Icon • License • Backup/Restore • Diagnostics • "
                "Release-Candidate Dry Run"
            ),
            bg=palette["panel"],
            fg=palette["muted"],
            anchor="w",
            pady=4,
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
        ).pack(fill="x", pady=(8, 10))

        license_var = tk.StringVar()
        operation_var = tk.StringVar()

        top = tk.Frame(outer, bg=palette["panel"])
        top.pack(fill="x")

        for title, variable in (
            ("License Lifecycle", license_var),
            ("Latest Operation", operation_var),
        ):
            card = tk.LabelFrame(
                top,
                text=title,
                bg=palette["panel"],
                fg=palette["text"],
                padx=10,
                pady=8,
            )
            card.pack(
                side="left",
                fill="both",
                expand=True,
                padx=4,
            )
            tk.Label(
                card,
                textvariable=variable,
                bg=palette["panel"],
                fg=palette["muted"],
                justify="left",
                anchor="nw",
                wraplength=460,
            ).pack(fill="both", expand=True)

        checks_list = tk.Listbox(
            outer,
            exportselection=False,
        )
        checks_list.pack(
            fill="both",
            expand=True,
            pady=(12, 0),
        )

        def render(current: dict) -> None:
            summary_var.set(current.get("display_text", ""))
            license_data = current.get("license", {})
            details = license_data.get("details", {})
            license_var.set(
                f"Check: {license_data.get('status', '')}\n"
                f"Lifecycle: {details.get('status', '')}\n"
                f"{license_data.get('message', '')}"
            )
            operation = current.get("operation", {})
            operation_var.set(
                f"Status: {operation.get('status', 'IDLE')}\n"
                f"Operation: {operation.get('operation', '')}\n"
                f"{operation.get('message', '')}"
            )
            checks_list.delete(0, "end")
            for item in current.get("required_checks", []):
                checks_list.insert(
                    "end",
                    f"[{item.get('status', '')}] "
                    f"{item.get('name', '')} — "
                    f"{item.get('message', '')}",
                )

        def refresh_dialog() -> None:
            render(refresh_release_center(False))

        def choose_restore_backup() -> None:
            selected = filedialog.askopenfilename(
                parent=dialog,
                title="Select HQE Backup ZIP",
                filetypes=[("HQE Backup ZIP", "*.zip")],
            )
            if selected:
                run_release_operation(
                    "restore_stage",
                    selected,
                )

        buttons = tk.Frame(outer, bg=palette["panel"])
        buttons.pack(fill="x", pady=(12, 0))

        ttk.Button(
            buttons,
            text="Run RC Dry Run",
            command=lambda: run_release_operation("rc_dry_run"),
        ).pack(side="left", padx=(0, 5))

        ttk.Button(
            buttons,
            text="Create User Backup",
            command=lambda: run_release_operation("backup"),
        ).pack(side="left", padx=5)

        ttk.Button(
            buttons,
            text="Stage Restore from Backup",
            command=choose_restore_backup,
        ).pack(side="left", padx=5)

        ttk.Button(
            buttons,
            text="Create Diagnostics Bundle",
            command=lambda: run_release_operation("diagnostics"),
        ).pack(side="left", padx=5)

        ttk.Button(
            buttons,
            text="Install Desktop Shortcut",
            command=install_desktop_shortcut,
        ).pack(side="left", padx=5)

        second_buttons = tk.Frame(outer, bg=palette["panel"])
        second_buttons.pack(fill="x", pady=(8, 0))

        ttk.Button(
            second_buttons,
            text="Refresh Release Status",
            command=refresh_dialog,
        ).pack(side="left", padx=(0, 5))

        ttk.Button(
            second_buttons,
            text="Open Latest RC Report",
            command=lambda: open_release_output("rc"),
        ).pack(side="left", padx=5)

        ttk.Button(
            second_buttons,
            text="Open Latest Backup",
            command=lambda: open_release_output("backup"),
        ).pack(side="left", padx=5)

        ttk.Button(
            second_buttons,
            text="Open Latest Diagnostics",
            command=lambda: open_release_output("diagnostics"),
        ).pack(side="left", padx=5)

        ttk.Button(
            second_buttons,
            text="Open Restore Staging",
            command=lambda: open_release_output("restore"),
        ).pack(side="left", padx=5)

        tk.Label(
            outer,
            text=(
                "RC DRY RUN ONLY • RESTORE STAGING DOES NOT OVERWRITE • "
                "REAL ORDERS NO • BROKER EXECUTION NO"
            ),
            bg=palette["panel"],
            fg=palette["muted"],
            anchor="w",
            pady=10,
        ).pack(fill="x")

        render(snapshot)

    release_center_panel = tk.Frame(
        action_panel,
        bg=palette["panel_alt"],
        highlightbackground=palette["border"],
        highlightthickness=1,
    )
    release_center_panel.pack(
        fill="x",
        padx=18,
        pady=(4, 8),
    )
    release_center_panel.pack_forget()

    tk.Label(
        release_center_panel,
        textvariable=release_center_status,
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
        text="Windows Release Center",
        style="Secondary.TButton",
        command=open_release_center,
    ).pack(fill="x", padx=28, pady=7)



    rc_audit_status = tk.StringVar(
        value="Final RC audit status will appear after refresh."
    )

    def refresh_rc_audit_center(
        show_dialog: bool = False,
    ) -> dict:
        try:
            snapshot = rc_audit_center_snapshot(
                repo_root(),
                workspace,
            )
            rc_audit_status.set(snapshot["display_text"])
            footer_status.set(snapshot["display_text"])
            if show_dialog:
                messagebox.showinfo(
                    "Final RC Audit & Freeze",
                    snapshot["display_text"],
                )
            return snapshot
        except Exception as exc:
            rc_audit_status.set(
                "Final RC audit refresh failed safely."
            )
            footer_status.set(f"Final RC audit error: {exc}")
            if show_dialog:
                messagebox.showerror(
                    "Final RC Audit & Freeze",
                    str(exc),
                )
            return {}


    def run_final_rc_audit() -> None:
        try:
            launch_rc_audit_worker(
                repo_root(),
                workspace,
            )
            rc_audit_status.set(
                "End-to-end RC audit is running safely..."
            )
            footer_status.set(
                "RC audit running; no trading operation started."
            )
            root.after(1400, poll_rc_audit)
        except Exception as exc:
            messagebox.showerror(
                "Final RC Audit & Freeze",
                str(exc),
            )

    def open_rc_audit_path(kind: str) -> None:
        snapshot = refresh_rc_audit_center(False)
        raw_path = str(
            {
                "report": snapshot.get("latest_report", ""),
                "freeze": snapshot.get("freeze_manifest", ""),
                "guide": snapshot.get("operator_guide", ""),
            }.get(kind, "")
        ).strip()
        if not raw_path:
            messagebox.showwarning(
                "Final RC Audit & Freeze",
                f"No {kind} file is available yet.",
            )
            return
        path = Path(raw_path)
        if not path.exists():
            messagebox.showerror(
                "Final RC Audit & Freeze",
                f"File is missing: {path}",
            )
            return
        try:
            os.startfile(path)
        except Exception as exc:
            messagebox.showerror(
                "Final RC Audit & Freeze",
                str(exc),
            )

    def open_rc_audit_center() -> None:
        snapshot = refresh_rc_audit_center(False)

        dialog = tk.Toplevel(root)
        dialog.title("HQE — Final RC Audit & Freeze")
        dialog.geometry("980x650")
        dialog.minsize(860, 570)
        dialog.configure(bg=palette.get("bg", palette.get("app_bg", "#0b1220")))
        dialog.transient(root)

        outer = tk.Frame(
            dialog,
            bg=palette["panel"],
            padx=16,
            pady=14,
        )
        outer.pack(fill="both", expand=True, padx=14, pady=14)

        tk.Label(
            outer,
            text="Final RC Audit & Freeze",
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
            anchor="w",
            padx=10,
            pady=8,
        ).pack(fill="x", pady=(8, 10))

        freeze_var = tk.StringVar()
        audit_var = tk.StringVar()

        top = tk.Frame(outer, bg=palette["panel"])
        top.pack(fill="x")

        for title, variable in (
            ("Paper-Only Freeze", freeze_var),
            ("Latest End-to-End Audit", audit_var),
        ):
            card = tk.LabelFrame(
                top,
                text=title,
                bg=palette["panel"],
                fg=palette["text"],
                padx=10,
                pady=8,
            )
            card.pack(
                side="left",
                fill="both",
                expand=True,
                padx=4,
            )
            tk.Label(
                card,
                textvariable=variable,
                bg=palette["panel"],
                fg=palette["muted"],
                justify="left",
                anchor="nw",
                wraplength=430,
            ).pack(fill="both", expand=True)

        check_list = tk.Listbox(
            outer,
            exportselection=False,
        )
        check_list.pack(
            fill="both",
            expand=True,
            pady=(12, 0),
        )

        def render(current: dict) -> None:
            summary_var.set(current.get("display_text", ""))
            freeze = current.get("freeze", {})
            latest = current.get("latest_audit", {})
            freeze_var.set(
                f"Status: {freeze.get('status', '')}\n"
                f"Files: {freeze.get('file_count', 0)}\n"
                f"{freeze.get('message', '')}"
            )
            audit_var.set(
                f"Status: {latest.get('status', 'NOT_RUN')}\n"
                f"Passed: {latest.get('passed_count', 0)} | "
                f"Review: {latest.get('review_count', 0)} | "
                f"Failed: {latest.get('failed_count', 0)}\n"
                f"{latest.get('message', '')}"
            )
            check_list.delete(0, "end")
            for item in latest.get("checks", []):
                check_list.insert(
                    "end",
                    f"[{item.get('status', '')}] "
                    f"{item.get('name', '')} — "
                    f"{item.get('message', '')}",
                )

        def refresh_dialog() -> None:
            render(refresh_rc_audit_center(False))

        buttons = tk.Frame(outer, bg=palette["panel"])
        buttons.pack(fill="x", pady=(12, 0))

        ttk.Button(
            buttons,
            text="Run End-to-End RC Audit",
            command=run_final_rc_audit,
        ).pack(side="left", padx=(0, 6))

        ttk.Button(
            buttons,
            text="Open Latest Audit Report",
            command=lambda: open_rc_audit_path("report"),
        ).pack(side="left", padx=6)

        ttk.Button(
            buttons,
            text="Open Freeze Manifest",
            command=lambda: open_rc_audit_path("freeze"),
        ).pack(side="left", padx=6)

        ttk.Button(
            buttons,
            text="Open Operator Guide",
            command=lambda: open_rc_audit_path("guide"),
        ).pack(side="left", padx=6)

        ttk.Button(
            buttons,
            text="Refresh Audit Status",
            command=refresh_dialog,
        ).pack(side="left", padx=6)

        tk.Label(
            outer,
            text=(
                "PAPER/DATA/RESEARCH RC ONLY • NO TRADING OPERATION • "
                "THIS IS NOT A PROFITABILITY CLAIM"
            ),
            bg=palette["panel"],
            fg=palette["muted"],
            anchor="w",
            pady=10,
        ).pack(fill="x")

        render(snapshot)

    rc_audit_panel = tk.Frame(
        action_panel,
        bg=palette["panel_alt"],
        highlightbackground=palette["border"],
        highlightthickness=2,
    )
    rc_audit_panel.pack(fill="x", padx=18, pady=(6, 10))
    rc_audit_panel.pack_forget()

    tk.Label(
        rc_audit_panel,
        text="FINAL PAPER-ONLY RELEASE CANDIDATE",
        bg=palette["panel_alt"],
        fg=palette["text"],
        font=("Segoe UI Semibold", 11),
        anchor="w",
        padx=10,
        pady=8,
    ).pack(fill="x")

    tk.Label(
        rc_audit_panel,
        textvariable=rc_audit_status,
        bg=palette["panel_alt"],
        fg=palette["muted"],
        justify="left",
        anchor="w",
        wraplength=300,
        padx=10,
        pady=6,
    ).pack(fill="x")

    ttk.Button(
        rc_audit_panel,
        text="Final RC Audit & Freeze",
        command=open_rc_audit_center,
    ).pack(fill="x", padx=10, pady=(2, 10))



    operator_acceptance_status = tk.StringVar(
        value="Operator acceptance has not been run."
    )

    def refresh_operator_acceptance_center(
        show_dialog: bool = False,
    ) -> dict:
        try:
            snapshot = operator_acceptance_center_snapshot(
                repo_root(),
                workspace,
            )
            operator_acceptance_status.set(
                snapshot["display_text"]
            )
            footer_status.set(snapshot["display_text"])
            if show_dialog:
                messagebox.showinfo(
                    "Operator Acceptance & RC Sign-Off",
                    snapshot["display_text"],
                )
            return snapshot
        except Exception as exc:
            operator_acceptance_status.set(
                "Operator acceptance refresh failed safely."
            )
            footer_status.set(
                f"Operator acceptance error: {exc}"
            )
            if show_dialog:
                messagebox.showerror(
                    "Operator Acceptance & RC Sign-Off",
                    str(exc),
                )
            return {}


    def run_operator_acceptance() -> None:
        try:
            launch_operator_acceptance(
                repo_root(),
                workspace,
            )
            operator_acceptance_status.set(
                "Operator acceptance dry run is running..."
            )
            footer_status.set(
                "Read-only operator acceptance is running."
            )
            root.after(1200, poll_operator_acceptance)
        except Exception as exc:
            messagebox.showerror(
                "Operator Acceptance & RC Sign-Off",
                str(exc),
            )

    def open_operator_acceptance_path(kind: str) -> None:
        snapshot = refresh_operator_acceptance_center(False)
        latest = snapshot.get("latest", {})
        raw_path = str(
            {
                "html": latest.get("html_path", ""),
                "json": latest.get("json_path", ""),
                "folder": latest.get("report_dir", ""),
                "guide": snapshot.get("operator_guide", ""),
            }.get(kind, "")
        ).strip()
        if not raw_path:
            messagebox.showwarning(
                "Operator Acceptance & RC Sign-Off",
                f"No {kind} file is available yet.",
            )
            return
        path = Path(raw_path)
        if not path.exists():
            messagebox.showerror(
                "Operator Acceptance & RC Sign-Off",
                f"File is missing: {path}",
            )
            return
        try:
            os.startfile(path)
        except Exception as exc:
            messagebox.showerror(
                "Operator Acceptance & RC Sign-Off",
                str(exc),
            )

    def open_operator_acceptance_center() -> None:
        snapshot = refresh_operator_acceptance_center(False)

        dialog = tk.Toplevel(root)
        dialog.title("HQE — Operator Acceptance & RC Sign-Off")
        dialog.geometry("980x650")
        dialog.minsize(860, 570)
        dialog.configure(bg=palette.get("bg", palette.get("app_bg", "#0b1220")))
        dialog.transient(root)

        outer = tk.Frame(
            dialog,
            bg=palette["panel"],
            padx=16,
            pady=14,
        )
        outer.pack(fill="both", expand=True, padx=14, pady=14)

        tk.Label(
            outer,
            text="Operator Acceptance & RC Sign-Off",
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
            anchor="w",
            padx=10,
            pady=8,
        ).pack(fill="x", pady=(8, 10))

        decision_var = tk.StringVar()
        check_list = tk.Listbox(
            outer,
            exportselection=False,
        )
        check_list.pack(fill="both", expand=True)

        tk.Label(
            outer,
            textvariable=decision_var,
            bg=palette["panel_alt"],
            fg=palette["muted"],
            justify="left",
            anchor="w",
            wraplength=900,
            padx=10,
            pady=8,
        ).pack(fill="x", pady=(10, 0))

        def render(current: dict) -> None:
            summary_var.set(current.get("display_text", ""))
            report = current.get("latest", {}).get("report", {})
            decision = report.get("decision", {})
            decision_var.set(
                f"{decision.get('status', 'NOT_RUN')}\n"
                f"{decision.get('message', '')}"
            )
            check_list.delete(0, "end")
            for item in report.get("checks", []):
                check_list.insert(
                    "end",
                    f"[{item.get('status', '')}] "
                    f"{item.get('name', '')} — "
                    f"{item.get('message', '')}",
                )

        def refresh_dialog() -> None:
            render(refresh_operator_acceptance_center(False))

        buttons = tk.Frame(outer, bg=palette["panel"])
        buttons.pack(fill="x", pady=(12, 0))

        ttk.Button(
            buttons,
            text="Run Operator Acceptance Dry Run",
            command=run_operator_acceptance,
        ).pack(side="left", padx=(0, 6))

        ttk.Button(
            buttons,
            text="Open Acceptance HTML",
            command=lambda: open_operator_acceptance_path("html"),
        ).pack(side="left", padx=6)

        ttk.Button(
            buttons,
            text="Open Acceptance JSON",
            command=lambda: open_operator_acceptance_path("json"),
        ).pack(side="left", padx=6)

        ttk.Button(
            buttons,
            text="Open Operator Guide",
            command=lambda: open_operator_acceptance_path("guide"),
        ).pack(side="left", padx=6)

        ttk.Button(
            buttons,
            text="Refresh Acceptance Status",
            command=refresh_dialog,
        ).pack(side="left", padx=6)

        tk.Label(
            outer,
            text=(
                "POST-FREEZE ACCEPTANCE ONLY • NO PRODUCT FEATURE CHANGE • "
                "REAL ORDERS NO • THIS IS NOT A PROFITABILITY CLAIM"
            ),
            bg=palette["panel"],
            fg=palette["muted"],
            anchor="w",
            pady=10,
        ).pack(fill="x")

        render(snapshot)

    operator_acceptance_panel = tk.Frame(
        action_panel,
        bg=palette["panel_alt"],
        highlightbackground=palette["border"],
        highlightthickness=2,
    )
    operator_acceptance_panel.pack(
        fill="x",
        padx=18,
        pady=(6, 10),
    )
    operator_acceptance_panel.pack_forget()

    tk.Label(
        operator_acceptance_panel,
        text="FINAL OPERATOR ACCEPTANCE",
        bg=palette["panel_alt"],
        fg=palette["text"],
        font=("Segoe UI Semibold", 11),
        anchor="w",
        padx=10,
        pady=8,
    ).pack(fill="x")

    tk.Label(
        operator_acceptance_panel,
        textvariable=operator_acceptance_status,
        bg=palette["panel_alt"],
        fg=palette["muted"],
        justify="left",
        anchor="w",
        wraplength=300,
        padx=10,
        pady=6,
    ).pack(fill="x")

    ttk.Button(
        operator_acceptance_panel,
        text="Operator Acceptance & RC Sign-Off",
        command=open_operator_acceptance_center,
    ).pack(fill="x", padx=10, pady=(2, 10))


    def _hqe_report_callback_exception(
        exception_type,
        exception_value,
        exception_traceback,
    ) -> None:
        import traceback
        rendered = ''.join(
            traceback.format_exception(
                exception_type,
                exception_value,
                exception_traceback,
            )
        )
        error_path = (
            Path(workspace)
            / 'HQE_RELEASE_CENTER'
            / 'ui_errors'
            / 'HQE_UI_CALLBACK_ERROR.txt'
        )
        try:
            error_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )
            error_path.write_text(
                rendered,
                encoding='utf-8',
            )
        except Exception:
            pass
        messagebox.showerror(
            'HQE UI Error',
            'A UI action failed safely.\n\n'
            + str(exception_value)
            + '\n\nError log: '
            + str(error_path),
        )

    root.report_callback_exception = (
        _hqe_report_callback_exception
    )

    def open_backtest_product_center() -> None:
        snapshot = refresh_backtest_product_center(False)

        dialog = tk.Toplevel(root)
        dialog.title("HQE â€” Backtest Product Center")
        dialog.geometry("1160x760")
        dialog.minsize(1020, 680)
        dialog.configure(bg=palette.get("bg", palette.get("app_bg", "#0b1220")))
        dialog.transient(root)

        outer = tk.Frame(
            dialog,
            bg=palette["panel"],
            padx=16,
            pady=14,
        )
        outer.pack(fill="both", expand=True, padx=14, pady=14)

        tk.Label(
            outer,
            text="Backtest Product Center",
            bg=palette["panel"],
            fg=palette["text"],
            font=("Segoe UI Semibold", 18),
            anchor="w",
        ).pack(fill="x")

        tk.Label(
            outer,
            text=(
                "Recorded Data â€¢ Strategy Pack â€¢ Costs â€¢ "
                "Equity / Drawdown Evidence"
            ),
            bg=palette["panel"],
            fg=palette["muted"],
            anchor="w",
            pady=4,
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
        ).pack(fill="x", pady=(8, 10))

        body = tk.Frame(outer, bg=palette["panel"])
        body.pack(fill="both", expand=True)

        form_frame = tk.LabelFrame(
            body,
            text="Backtest Job Controls",
            bg=palette["panel"],
            fg=palette["text"],
            padx=10,
            pady=8,
        )
        form_frame.pack(
            side="left",
            fill="both",
            expand=False,
        )

        result_frame = tk.LabelFrame(
            body,
            text="Job Preview and Results",
            bg=palette["panel"],
            fg=palette["text"],
            padx=10,
            pady=8,
        )
        result_frame.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(12, 0),
        )

        datasets = list(snapshot.get("datasets", []))
        strategies = list(snapshot.get("strategies", []))
        compatible_runners = [
            runner
            for runner in snapshot.get("runners", [])
            if runner.get("compatible")
        ]

        dataset_map = {
            f"{item.get('name', '')} | score {item.get('score', 0)} | "
            f"rows {item.get('row_count', 0)}": item.get("path", "")
            for item in datasets
        }
        strategy_map = {
            f"{item.get('name', '')} | {item.get('version', '')} | "
            f"{item.get('source', '')}": item.get("path", "")
            for item in strategies
        }
        runner_map = {
            f"{item.get('name', '')} | guarded": item.get("path", "")
            for item in compatible_runners
        }

        variables = {
            "dataset": tk.StringVar(
                value=next(iter(dataset_map), "")
            ),
            "strategy": tk.StringVar(
                value=next(iter(strategy_map), "")
            ),
            "runner": tk.StringVar(
                value=next(iter(runner_map), "")
            ),
            "start_date": tk.StringVar(value=""),
            "end_date": tk.StringVar(value=""),
            "initial_capital": tk.StringVar(value="100000"),
            "brokerage_per_order": tk.StringVar(value="20"),
            "slippage_bps": tk.StringVar(value="5"),
            "tax_bps": tk.StringVar(value="2"),
            "max_trades_per_day": tk.StringVar(value="3"),
        }

        rows = [
            ("Dataset", "dataset", tuple(dataset_map)),
            ("Strategy Pack", "strategy", tuple(strategy_map)),
            ("Guarded Runner", "runner", tuple(runner_map)),
            ("Start Date YYYY-MM-DD", "start_date", None),
            ("End Date YYYY-MM-DD", "end_date", None),
            ("Initial Capital", "initial_capital", None),
            ("Brokerage / Order", "brokerage_per_order", None),
            ("Slippage BPS", "slippage_bps", None),
            ("Taxes / Charges BPS", "tax_bps", None),
            ("Max Trades / Day", "max_trades_per_day", None),
        ]

        for row, (label, key, values) in enumerate(rows):
            tk.Label(
                form_frame,
                text=label,
                bg=palette["panel"],
                fg=palette["muted"],
                anchor="w",
            ).grid(
                row=row,
                column=0,
                sticky="w",
                padx=(0, 8),
                pady=4,
            )
            if values is not None:
                widget = ttk.Combobox(
                    form_frame,
                    textvariable=variables[key],
                    values=values,
                    state="readonly",
                    width=54,
                )
            else:
                widget = ttk.Entry(
                    form_frame,
                    textvariable=variables[key],
                    width=57,
                )
            widget.grid(
                row=row,
                column=1,
                sticky="ew",
                pady=4,
            )

        preview_text = tk.Text(
            result_frame,
            wrap="word",
            height=25,
            width=62,
        )
        preview_text.pack(fill="both", expand=True)

        recent_list = tk.Listbox(
            result_frame,
            height=8,
            exportselection=False,
        )
        recent_list.pack(fill="x", pady=(10, 0))

        latest_job = {"path": ""}
        visible_runs: list[dict] = []

        def form_payload() -> dict:
            return {
                "dataset_path": dataset_map.get(
                    variables["dataset"].get(),
                    "",
                ),
                "strategy_path": strategy_map.get(
                    variables["strategy"].get(),
                    "",
                ),
                "start_date": variables["start_date"].get(),
                "end_date": variables["end_date"].get(),
                "initial_capital": variables[
                    "initial_capital"
                ].get(),
                "brokerage_per_order": variables[
                    "brokerage_per_order"
                ].get(),
                "slippage_bps": variables[
                    "slippage_bps"
                ].get(),
                "tax_bps": variables["tax_bps"].get(),
                "max_trades_per_day": variables[
                    "max_trades_per_day"
                ].get(),
            }

        def preview_job() -> None:
            preview_text.delete("1.0", "end")
            try:
                result = preview_backtest_job(form_payload())
                job = result["job"]
                validation = result["validation"]
                preview_text.insert(
                    "end",
                    f"Job ID: {job['job_id']}\n"
                    f"Mode: {job['mode']}\n"
                    f"Dataset: {job['dataset_path']}\n"
                    f"Strategy: "
                    f"{validation.get('strategy_name', '')}\n"
                    f"Dates: {job['start_date'] or 'all'} to "
                    f"{job['end_date'] or 'all'}\n"
                    f"Capital: {job['initial_capital']}\n"
                    f"Brokerage: {job['brokerage_per_order']}\n"
                    f"Slippage BPS: {job['slippage_bps']}\n"
                    f"Tax BPS: {job['tax_bps']}\n"
                    f"Max trades/day: "
                    f"{job['max_trades_per_day']}\n\n"
                    f"VALID: {validation['valid']}\n"
                    f"WARNINGS: "
                    f"{validation.get('warnings', [])}\n"
                    f"ERRORS: {validation.get('errors', [])}\n\n"
                    f"REAL ORDERS: NO\n"
                    f"BROKER EXECUTION: NO\n"
                    f"OPTION SELLING: NO"
                )
            except Exception as exc:
                preview_text.insert("end", f"VALIDATION ERROR:\n{exc}")

        def save_job() -> None:
            try:
                target = create_backtest_job(
                    form_payload(),
                    workspace,
                )
                latest_job["path"] = str(target)
                messagebox.showinfo(
                    "Backtest Product Center",
                    f"Backtest job saved:\n{target}",
                )
            except Exception as exc:
                messagebox.showerror(
                    "Backtest Product Center",
                    str(exc),
                )

        def poll_backtest() -> None:
            current = refresh_backtest_product_center(False)
            operation = current.get("operation", {})
            status = str(operation.get("status", ""))
            if status == "RUNNING":
                root.after(1200, poll_backtest)
                return
            refresh_dialog()
            message = str(
                operation.get(
                    "message",
                    "Backtest operation finished.",
                )
            )
            if status == "PASS":
                messagebox.showinfo(
                    "Backtest Product Center",
                    message,
                )
            elif status in {"FAILED", "BLOCKED"}:
                messagebox.showerror(
                    "Backtest Product Center",
                    message,
                )

        def run_job() -> None:
            runner_path = runner_map.get(
                variables["runner"].get(),
                "",
            )
            if not runner_path:
                messagebox.showwarning(
                    "Backtest Product Center",
                    "No compatible guarded backtest runner is available.",
                )
                return
            try:
                if not latest_job["path"]:
                    target = create_backtest_job(
                        form_payload(),
                        workspace,
                    )
                    latest_job["path"] = str(target)
                run_backtest_job(
                    repo_root(),
                    workspace,
                    Path(latest_job["path"]),
                    Path(runner_path),
                )
                footer_status.set(
                    "Recorded-data backtest running safely."
                )
                root.after(1200, poll_backtest)
            except Exception as exc:
                messagebox.showerror(
                    "Backtest Product Center",
                    str(exc),
                )

        def selected_run() -> dict:
            selection = recent_list.curselection()
            if not selection:
                return {}
            index = int(selection[0])
            if index >= len(visible_runs):
                return {}
            return visible_runs[index]

        def open_run_path(kind: str) -> None:
            record = selected_run()
            if not record and visible_runs:
                record = visible_runs[0]
            raw_path = str(
                record.get(
                    "summary_path" if kind == "summary" else "output_dir",
                    "",
                )
            )
            if not raw_path:
                messagebox.showwarning(
                    "Backtest Product Center",
                    "No backtest result is available yet.",
                )
                return
            path = Path(raw_path)
            if not path.exists():
                messagebox.showerror(
                    "Backtest Product Center",
                    f"Backtest result path is missing: {path}",
                )
                return
            try:
                os.startfile(path)
            except Exception as exc:
                messagebox.showerror(
                    "Backtest Product Center",
                    str(exc),
                )

        def render_runs(current: dict) -> None:
            visible_runs.clear()
            recent_list.delete(0, "end")
            for record in current.get("recent_runs", []):
                visible_runs.append(record)
                metrics = record.get("metrics", {})
                recent_list.insert(
                    "end",
                    f"{record.get('job_id', '')} | "
                    f"trades {metrics.get('trade_count', 0)} | "
                    f"net {metrics.get('net_pnl', 'n/a')} | "
                    f"DD {metrics.get('max_drawdown', 'n/a')}",
                )

        def refresh_dialog() -> None:
            current = refresh_backtest_product_center(False)
            summary_var.set(current.get("display_text", ""))
            render_runs(current)

        buttons = tk.Frame(outer, bg=palette["panel"])
        buttons.pack(fill="x", pady=(12, 0))

        ttk.Button(
            buttons,
            text="Preview Backtest Job",
            command=preview_job,
        ).pack(side="left", padx=(0, 6))

        ttk.Button(
            buttons,
            text="Save Backtest Job",
            command=save_job,
        ).pack(side="left", padx=6)

        ttk.Button(
            buttons,
            text="Run Guarded Backtest",
            command=run_job,
        ).pack(side="left", padx=6)

        ttk.Button(
            buttons,
            text="Open Latest Result Summary",
            command=lambda: open_run_path("summary"),
        ).pack(side="left", padx=6)

        ttk.Button(
            buttons,
            text="Open Result Folder",
            command=lambda: open_run_path("folder"),
        ).pack(side="left", padx=6)

        ttk.Button(
            buttons,
            text="Refresh Results",
            command=refresh_dialog,
        ).pack(side="left", padx=6)

        tk.Label(
            outer,
            text=(
                "RECORDED DATA ONLY â€¢ NO FAKE OPTION PRICES â€¢ "
                "REAL ORDERS NO â€¢ BROKER EXECUTION NO"
            ),
            bg=palette["panel"],
            fg=palette["muted"],
            anchor="w",
            pady=10,
        ).pack(fill="x")

        render_runs(snapshot)
        preview_job()

    def open_advanced_tools_hub() -> None:
        advanced_tools_dialog = tk.Toplevel(root)
        advanced_tools_dialog.title(
            'HQE - Advanced Tools & Product Centers'
        )
        advanced_tools_dialog.geometry('820x720')
        advanced_tools_dialog.minsize(680, 520)
        hub_bg = palette.get('bg', '#101a31')
        hub_panel = palette.get('panel', '#18243d')
        hub_text = palette.get('text', '#ffffff')
        hub_muted = palette.get('muted', '#a9bad7')
        hub_border = palette.get('border', '#34445f')
        advanced_tools_dialog.configure(bg=hub_bg)
        advanced_tools_dialog.transient(root)
        _apply_hqe_window_icon(advanced_tools_dialog, icon)
        advanced_tools_shell = tk.Frame(
            advanced_tools_dialog,
            bg=hub_bg,
            padx=16,
            pady=14,
        )
        advanced_tools_shell.pack(
            fill='both',
            expand=True,
        )
        tk.Label(
            advanced_tools_shell,
            text="Advanced Tools & Product Centers",
            bg=hub_bg,
            fg=hub_text,
            font=('Segoe UI Semibold', 18),
            anchor='w',
        ).pack(fill='x')
        tk.Label(
            advanced_tools_shell,
            text=(
                'Advanced centers load only when opened.'
            ),
            bg=hub_bg,
            fg=hub_muted,
            anchor='w',
            pady=6,
        ).pack(fill='x')
        advanced_tools_body = tk.Frame(
            advanced_tools_shell,
            bg=hub_bg,
        )
        advanced_tools_body.pack(
            fill='both',
            expand=True,
            pady=(8, 0),
        )
        advanced_tools_canvas = tk.Canvas(
            advanced_tools_body,
            bg=hub_bg,
            highlightthickness=0,
            borderwidth=0,
        )
        advanced_tools_scrollbar = ttk.Scrollbar(
            advanced_tools_body,
            orient='vertical',
            command=advanced_tools_canvas.yview,
        )
        advanced_tools_canvas.configure(
            yscrollcommand=
            advanced_tools_scrollbar.set,
        )
        advanced_tools_scrollbar.pack(
            side='right',
            fill='y',
        )
        advanced_tools_canvas.pack(
            side='left',
            fill='both',
            expand=True,
        )
        advanced_tools_inner = tk.Frame(
            advanced_tools_canvas,
            bg=hub_bg,
        )
        advanced_tools_window = (
            advanced_tools_canvas.create_window(
                (0, 0),
                window=advanced_tools_inner,
                anchor='nw',
            )
        )
        def _sync_advanced_tools(_event=None):
            advanced_tools_canvas.itemconfigure(
                advanced_tools_window,
                width=max(
                    1,
                    advanced_tools_canvas.winfo_width(),
                ),
            )
            advanced_tools_canvas.configure(
                scrollregion=
                advanced_tools_canvas.bbox('all'),
            )
        def _advanced_tools_wheel(event):
            delta = int(getattr(event, "delta", 0) or 0)
            if delta == 0:
                return None

            steps = max(1, abs(delta) // 120)
            advanced_tools_canvas.yview_scroll(
                -steps if delta > 0 else steps,
                "units",
            )
            return "break"


        def _advanced_tools_wheel_up(_event):
            advanced_tools_canvas.yview_scroll(-1, "units")
            return "break"


        def _advanced_tools_wheel_down(_event):
            advanced_tools_canvas.yview_scroll(1, "units")
            return "break"


        def _bind_advanced_tools_mousewheel_tree(widget) -> None:
            widget.bind(
                "<MouseWheel>",
                _advanced_tools_wheel,
            )
            widget.bind(
                "<Button-4>",
                _advanced_tools_wheel_up,
            )
            widget.bind(
                "<Button-5>",
                _advanced_tools_wheel_down,
            )
            for child in widget.winfo_children():
                _bind_advanced_tools_mousewheel_tree(child)
        advanced_tools_inner.bind(
            '<Configure>',
            _sync_advanced_tools,
        )
        advanced_tools_canvas.bind(
            '<Configure>',
            _sync_advanced_tools,
        )
        advanced_tools_canvas.bind(
            '<MouseWheel>',
            _advanced_tools_wheel,
        )

        card_1 = tk.Frame(
            advanced_tools_inner,
            bg=hub_panel,
            highlightthickness=1,
            highlightbackground=hub_border,
            padx=12,
            pady=10,
        )
        card_1.pack(
            fill='x',
            padx=4,
            pady=5,
        )
        tk.Label(
            card_1,
            text='Operator Dashboard',
            bg=hub_panel,
            fg=hub_text,
            font=('Segoe UI Semibold', 12),
            anchor='w',
        ).pack(fill='x')
        tk.Label(
            card_1,
            text='Guided Connect -> Prepare -> Watch -> Close -> Review flow.',
            bg=hub_panel,
            fg=hub_muted,
            anchor='w',
            justify='left',
            wraplength=650,
            pady=5,
        ).pack(fill='x')
        ttk.Button(
            card_1,
            text='Open Operator Dashboard',
            command=open_operator_dashboard,
        ).pack(
            side='right',
            pady=(4, 0),
        )
        card_2 = tk.Frame(
            advanced_tools_inner,
            bg=hub_panel,
            highlightthickness=1,
            highlightbackground=hub_border,
            padx=12,
            pady=10,
        )
        card_2.pack(
            fill='x',
            padx=4,
            pady=5,
        )
        tk.Label(
            card_2,
            text='Market Data Quality Center',
            bg=hub_panel,
            fg=hub_text,
            font=('Segoe UI Semibold', 12),
            anchor='w',
        ).pack(fill='x')
        tk.Label(
            card_2,
            text='Inspect gaps, duplicates, timestamps and OHLCV quality.',
            bg=hub_panel,
            fg=hub_muted,
            anchor='w',
            justify='left',
            wraplength=650,
            pady=5,
        ).pack(fill='x')
        ttk.Button(
            card_2,
            text='Open Market Data Quality Center',
            command=open_market_data_quality_center,
        ).pack(
            side='right',
            pady=(4, 0),
        )
        card_3 = tk.Frame(
            advanced_tools_inner,
            bg=hub_panel,
            highlightthickness=1,
            highlightbackground=hub_border,
            padx=12,
            pady=10,
        )
        card_3.pack(
            fill='x',
            padx=4,
            pady=5,
        )
        tk.Label(
            card_3,
            text='Strategy Pack Center',
            bg=hub_panel,
            fg=hub_text,
            font=('Segoe UI Semibold', 12),
            anchor='w',
        ).pack(fill='x')
        tk.Label(
            card_3,
            text='Review, clone, import and export paper-only strategy packs.',
            bg=hub_panel,
            fg=hub_muted,
            anchor='w',
            justify='left',
            wraplength=650,
            pady=5,
        ).pack(fill='x')
        ttk.Button(
            card_3,
            text='Open Strategy Pack Center',
            command=open_strategy_pack_center,
        ).pack(
            side='right',
            pady=(4, 0),
        )
        card_4 = tk.Frame(
            advanced_tools_inner,
            bg=hub_panel,
            highlightthickness=1,
            highlightbackground=hub_border,
            padx=12,
            pady=10,
        )
        card_4.pack(
            fill='x',
            padx=4,
            pady=5,
        )
        tk.Label(
            card_4,
            text='Strategy Builder & Selector',
            bg=hub_panel,
            fg=hub_text,
            font=('Segoe UI Semibold', 12),
            anchor='w',
        ).pack(fill='x')
        tk.Label(
            card_4,
            text='Build, validate and select a paper-only strategy draft.',
            bg=hub_panel,
            fg=hub_muted,
            anchor='w',
            justify='left',
            wraplength=650,
            pady=5,
        ).pack(fill='x')
        ttk.Button(
            card_4,
            text='Open Strategy Builder & Selector',
            command=open_strategy_builder_center,
        ).pack(
            side='right',
            pady=(4, 0),
        )
        card_5 = tk.Frame(
            advanced_tools_inner,
            bg=hub_panel,
            highlightthickness=1,
            highlightbackground=hub_border,
            padx=12,
            pady=10,
        )
        card_5.pack(
            fill='x',
            padx=4,
            pady=5,
        )
        tk.Label(
            card_5,
            text='Backtest Product Center',
            bg=hub_panel,
            fg=hub_text,
            font=('Segoe UI Semibold', 12),
            anchor='w',
        ).pack(fill='x')
        tk.Label(
            card_5,
            text='Create guarded recorded-data research backtest jobs.',
            bg=hub_panel,
            fg=hub_muted,
            anchor='w',
            justify='left',
            wraplength=650,
            pady=5,
        ).pack(fill='x')
        ttk.Button(
            card_5,
            text='Open Backtest Product Center',
            command=open_backtest_product_center,
        ).pack(
            side='right',
            pady=(4, 0),
        )
        card_6 = tk.Frame(
            advanced_tools_inner,
            bg=hub_panel,
            highlightthickness=1,
            highlightbackground=hub_border,
            padx=12,
            pady=10,
        )
        card_6.pack(
            fill='x',
            padx=4,
            pady=5,
        )
        tk.Label(
            card_6,
            text='Session History',
            bg=hub_panel,
            fg=hub_text,
            font=('Segoe UI Semibold', 12),
            anchor='w',
        ).pack(fill='x')
        tk.Label(
            card_6,
            text='Browse earlier paper sessions, reports and evidence.',
            bg=hub_panel,
            fg=hub_muted,
            anchor='w',
            justify='left',
            wraplength=650,
            pady=5,
        ).pack(fill='x')
        ttk.Button(
            card_6,
            text='Open Session History',
            command=open_session_history_center,
        ).pack(
            side='right',
            pady=(4, 0),
        )
        card_7 = tk.Frame(
            advanced_tools_inner,
            bg=hub_panel,
            highlightthickness=1,
            highlightbackground=hub_border,
            padx=12,
            pady=10,
        )
        card_7.pack(
            fill='x',
            padx=4,
            pady=5,
        )
        tk.Label(
            card_7,
            text='Paper Validation Intelligence',
            bg=hub_panel,
            fg=hub_text,
            font=('Segoe UI Semibold', 12),
            anchor='w',
        ).pack(fill='x')
        tk.Label(
            card_7,
            text='Track days, trades, expiry weeks, reasons and drift.',
            bg=hub_panel,
            fg=hub_muted,
            anchor='w',
            justify='left',
            wraplength=650,
            pady=5,
        ).pack(fill='x')
        ttk.Button(
            card_7,
            text='Open Paper Validation Intelligence',
            command=open_paper_validation_report_center,
        ).pack(
            side='right',
            pady=(4, 0),
        )
        card_8 = tk.Frame(
            advanced_tools_inner,
            bg=hub_panel,
            highlightthickness=1,
            highlightbackground=hub_border,
            padx=12,
            pady=10,
        )
        card_8.pack(
            fill='x',
            padx=4,
            pady=5,
        )
        tk.Label(
            card_8,
            text='Windows Release Center',
            bg=hub_panel,
            fg=hub_text,
            font=('Segoe UI Semibold', 12),
            anchor='w',
        ).pack(fill='x')
        tk.Label(
            card_8,
            text='Backup, restore staging, diagnostics and release checks.',
            bg=hub_panel,
            fg=hub_muted,
            anchor='w',
            justify='left',
            wraplength=650,
            pady=5,
        ).pack(fill='x')
        ttk.Button(
            card_8,
            text='Open Windows Release Center',
            command=open_release_center,
        ).pack(
            side='right',
            pady=(4, 0),
        )
        card_9 = tk.Frame(
            advanced_tools_inner,
            bg=hub_panel,
            highlightthickness=1,
            highlightbackground=hub_border,
            padx=12,
            pady=10,
        )
        card_9.pack(
            fill='x',
            padx=4,
            pady=5,
        )
        tk.Label(
            card_9,
            text='Final RC Audit & Freeze',
            bg=hub_panel,
            fg=hub_text,
            font=('Segoe UI Semibold', 12),
            anchor='w',
        ).pack(fill='x')
        tk.Label(
            card_9,
            text='Verify release safety, required files and freeze hashes.',
            bg=hub_panel,
            fg=hub_muted,
            anchor='w',
            justify='left',
            wraplength=650,
            pady=5,
        ).pack(fill='x')
        ttk.Button(
            card_9,
            text='Open Final RC Audit & Freeze',
            command=open_rc_audit_center,
        ).pack(
            side='right',
            pady=(4, 0),
        )
        card_10 = tk.Frame(
            advanced_tools_inner,
            bg=hub_panel,
            highlightthickness=1,
            highlightbackground=hub_border,
            padx=12,
            pady=10,
        )
        card_10.pack(
            fill='x',
            padx=4,
            pady=5,
        )
        tk.Label(
            card_10,
            text='Operator Acceptance & RC Sign-Off',
            bg=hub_panel,
            fg=hub_text,
            font=('Segoe UI Semibold', 12),
            anchor='w',
        ).pack(fill='x')
        tk.Label(
            card_10,
            text='Review final paper-only app acceptance evidence.',
            bg=hub_panel,
            fg=hub_muted,
            anchor='w',
            justify='left',
            wraplength=650,
            pady=5,
        ).pack(fill='x')
        ttk.Button(
            card_10,
            text='Open Operator Acceptance & RC Sign-Off',
            command=open_operator_acceptance_center,
        ).pack(
            side='right',
            pady=(4, 0),
        )
        _bind_advanced_tools_mousewheel_tree(advanced_tools_dialog)
        advanced_tools_dialog.update_idletasks()
        _sync_advanced_tools()

    ttk.Button(
        action_panel,
        text="Advanced Tools & Product Centers",
        style='Secondary.TButton',
        command=open_advanced_tools_hub,
    ).pack(fill="x", padx=28, pady=7)

    # HQE_STABILIZATION_MENU_V1
    hqe_menu_bar = tk.Menu(root)
    hqe_tools_menu = tk.Menu(hqe_menu_bar, tearoff=False)
    hqe_tools_menu.add_command(
        label="Advanced Tools & Product Centers",
        accelerator="Ctrl+T",
        command=open_advanced_tools_hub,
    )
    hqe_menu_bar.add_cascade(
        label="Tools",
        menu=hqe_tools_menu,
    )
    root.configure(menu=hqe_menu_bar)
    root.bind(
        "<Control-t>",
        lambda _event: open_advanced_tools_hub(),
    )

    if os.environ.get(
        'HQE_ADVANCED_TOOLS_SMOKE'
    ) == '1':
        def _hqe_smoke_advanced_tools():
            open_advanced_tools_hub()
            root.update_idletasks()
            dialogs = [
                child
                for child in root.winfo_children()
                if isinstance(child, tk.Toplevel)
                and 'Advanced Tools' in child.title()
            ]
            if not dialogs:
                raise RuntimeError(
                    'Advanced Tools dialog did not open.'
                )
            def _collect(widget):
                values = []
                try:
                    value = widget.cget('text')
                    if value:
                        values.append(str(value))
                except Exception:
                    pass
                for child in widget.winfo_children():
                    values.extend(_collect(child))
                return values
            rendered = '\n'.join(
                _collect(dialogs[-1])
            )
            required = ('Operator Dashboard', 'Market Data Quality Center', 'Strategy Pack Center', 'Strategy Builder & Selector', 'Backtest Product Center', 'Session History', 'Paper Validation Intelligence', 'Windows Release Center', 'Final RC Audit & Freeze', 'Operator Acceptance & RC Sign-Off')
            missing = [
                label
                for label in required
                if label not in rendered
            ]
            if missing:
                raise RuntimeError(
                    'Advanced hub missing: '
                    + ', '.join(missing)
                )
            print(
                'HQE_ADVANCED_TOOLS_SMOKE_PASS',
                flush=True,
            )
            root.after(250, root.destroy)
        root.after(
            250,
            _hqe_smoke_advanced_tools,
        )


    # HQE_STABILIZATION_BUNCH3_FULL_CENTER_SMOKE
    if os.environ.get("HQE_FULL_CENTER_SMOKE") == "1":
        failures: list[str] = []
        tested: list[str] = []
        candidates = []
        for name, callback in list(locals().items()):
            if not callable(callback):
                continue
            if not (
                name.startswith("open_")
                and (
                    name.endswith("_center")
                    or name.endswith("_hub")
                    or name.endswith("_dashboard")
                )
            ):
                continue
            try:
                signature = inspect.signature(callback)
                required = [
                    parameter
                    for parameter in signature.parameters.values()
                    if parameter.default is inspect.Parameter.empty
                    and parameter.kind
                    in (
                        inspect.Parameter.POSITIONAL_ONLY,
                        inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    )
                ]
            except (TypeError, ValueError):
                continue
            if required:
                continue
            candidates.append((name, callback))

        for name, callback in sorted(candidates):
            before = set(root.winfo_children())
            try:
                callback()
                root.update_idletasks()
                root.update()
                tested.append(name)
            except Exception as exc:
                failures.append(f"{name}: {type(exc).__name__}: {exc}")
            finally:
                after = set(root.winfo_children())
                for widget in after - before:
                    try:
                        if isinstance(widget, tk.Toplevel):
                            widget.destroy()
                    except Exception:
                        pass
                try:
                    root.update_idletasks()
                except Exception:
                    pass

        if not tested:
            failures.append("No zero-argument app centers were discovered.")

        if failures:
            print("HQE_FULL_CENTER_SMOKE_FAIL")
            for failure in failures:
                print(failure)
            root.destroy()
            return 3

        print(f"HQE_FULL_CENTER_SMOKE_PASS:{len(tested)}")
        for name in tested:
            print(f"PASS:{name}")
        root.destroy()
        return 0

    # HQE_AUTOMATIC_DAILY_WORKFLOW_V1
    root.after(
        1500,
        lambda: launch_app_background_worker(workspace),
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
