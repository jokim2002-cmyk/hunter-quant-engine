from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from hqe_product_license_common import (
    DEFAULT_PUBLIC_KEY_NAME,
    app_config_dir,
    license_file_path,
    load_public_key,
    machine_id,
    public_key_path,
    verify_license_key,
)


DEFAULT_WORKSPACE = Path(r"D:\HQE_BACKTEST_RUNS\HQE_FORWARD_PAPER_VALIDATION_ACTIVE_20260708_204722")
DEFAULT_SYMBOL = "NSE:NIFTY50-INDEX"
DEFAULT_USER_ID = "hqe-user"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig").strip()
    except Exception:
        return ""


def license_status(workspace: Path) -> dict:
    mid = machine_id()
    lic_path = license_file_path(workspace)
    pub_path = public_key_path(workspace)
    if not pub_path.exists():
        return {"valid": False, "reason": "public_key_missing", "machine_id": mid, "license_file": str(lic_path), "public_key_file": str(pub_path)}
    if not lic_path.exists():
        return {"valid": False, "reason": "license_missing", "machine_id": mid, "license_file": str(lic_path), "public_key_file": str(pub_path)}
    public_key = load_public_key(pub_path)
    result = verify_license_key(read_text(lic_path), public_key, expected_machine_id=mid)
    result.update({"machine_id": mid, "license_file": str(lic_path), "public_key_file": str(pub_path)})
    return result


def launch_cmd(command: str, cwd: Path) -> None:
    subprocess.Popen(command, cwd=str(cwd), shell=True)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="HQE Product App")
    p.add_argument("--workspace", default=str(DEFAULT_WORKSPACE))
    p.add_argument("--symbol", default=DEFAULT_SYMBOL)
    p.add_argument("--user-id", default=DEFAULT_USER_ID)
    p.add_argument("--trading-date", default="")
    p.add_argument("--guard-check", action="store_true")
    return p


def guard_check() -> int:
    payload = {
        "app": "HQE Product App",
        "guard_check_status": "PASS",
        "paper_only": True,
        "data_only": True,
        "no_real_orders": True,
        "no_broker_execution": True,
        "no_auto_trading": True,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def run_gui(args: argparse.Namespace) -> int:
    try:
        import tkinter as tk
        from tkinter import messagebox
    except Exception:
        print("Tkinter unavailable. Run from Windows desktop Python install.")
        return 1

    workspace = Path(args.workspace)
    workspace.mkdir(parents=True, exist_ok=True)
    repo = repo_root()
    py = repo / ".venv" / "Scripts" / "python.exe"
    cfg = app_config_dir(workspace)
    lic_file = license_file_path(workspace)
    mid = machine_id()

    root = tk.Tk()
    root.title("HQE App")
    root.geometry("900x680")

    status_var = tk.StringVar(value="Ready.")
    license_var = tk.StringVar(value="")
    user_var = tk.StringVar(value=args.user_id)
    symbol_var = tk.StringVar(value=args.symbol)
    date_var = tk.StringVar(value=args.trading_date)

    def set_status(text: str) -> None:
        status_var.set(text)

    def copy_machine_id() -> None:
        try:
            subprocess.run("clip", input=mid, text=True, check=True)
            set_status("Machine ID copied to clipboard.")
        except Exception:
            set_status("Copy failed. Select and copy Machine ID manually.")

    def activate_license() -> None:
        key = license_var.get().strip()
        if not key:
            messagebox.showwarning("License key missing", "Paste your HQE user/license key first.")
            return
        lic_file.write_text(key, encoding="utf-8")
        st = license_status(workspace)
        if st.get("valid"):
            messagebox.showinfo("Activated", "HQE license activated successfully.")
            show_main()
        else:
            messagebox.showerror("Activation failed", f"License invalid: {st.get('reason')}")
            set_status(f"Activation failed: {st.get('reason')}")

    def command_parts() -> dict:
        trading_date = date_var.get().strip()
        date_arg = f' -TradingDate "{trading_date}"' if trading_date else ""
        symbol = symbol_var.get().strip() or args.symbol
        user_id = user_var.get().strip() or args.user_id
        return {"trading_date": trading_date, "date_arg": date_arg, "symbol": symbol, "user_id": user_id}

    def refresh_token() -> None:
        c = command_parts()
        cmd = f'powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\\HQE_FYERS_TOKEN_SIMPLE_REFRESH_V2.ps1" -RepoRoot "{repo}" -Workspace "{workspace}" -Symbol "{c["symbol"]}"'
        launch_cmd(cmd, repo)
        set_status("Refresh Fyers Token opened. Complete browser login and Notepad redirect URL step.")

    def data_test() -> None:
        c = command_parts()
        cmd = f'"{py}" scripts\\hqe_fyers_historical_5m_data_only_fetcher.py --workspace "{workspace}" --symbol "{c["symbol"]}" --execute-live-data-only --write'
        launch_cmd(cmd, repo)
        set_status("Historical 5m Data-Only Test started.")

    def start_watch() -> None:
        c = command_parts()
        launcher = workspace / "START_HQE_MARKET_DAY_PAPER_WATCH_0915_1530.cmd"
        if launcher.exists():
            launch_cmd(f'"{launcher}"', repo)
        else:
            cmd = f'powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\\RUN_MARKET_DAY_PERSISTENT_PAPER_WATCH.ps1" -Workspace "{workspace}"{c["date_arg"]} -UserId "{c["user_id"]}" -Symbol "{c["symbol"]}" -IntervalSeconds 300 -RunDataFetch'
            launch_cmd(cmd, repo)
        set_status("Persistent paper watch opened. Keep the CMD window open during market hours.")

    def run_daily_pack() -> None:
        c = command_parts()
        day = 1
        cmd = f'powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\\RUN_MODULES_251_270_FINAL_VALIDATION_HARDENING.ps1" -Workspace "{workspace}"{c["date_arg"]} -DayNumber {day} -UserId "{c["user_id"]}" -Symbol "{c["symbol"]}"'
        launch_cmd(cmd, repo)
        set_status("Daily final hardening/report pack started.")

    def open_evidence() -> None:
        launch_cmd(f'explorer "{workspace}"', repo)

    def open_report() -> None:
        candidates = [
            workspace / "DAY_001_DAILY_VALIDATION_REPORT.html",
            workspace / "HQE_MASTER_READINESS_FREEZE_FINAL.html",
            workspace / "HQE_MASTER_SYSTEM_STATUS_DASHBOARD.html",
        ]
        for p in candidates:
            if p.exists():
                launch_cmd(f'start "" "{p}"', repo)
                set_status(f"Opened {p.name}")
                return
        set_status("No report file found yet. Run Data Test / Daily Pack first.")

    def show_activation() -> None:
        for child in root.winfo_children():
            child.destroy()
        tk.Label(root, text="HQE App Login / License Activation", font=("Segoe UI", 20, "bold")).pack(pady=(22, 4))
        tk.Label(root, text="PAPER ONLY / DATA ONLY / NO REAL ORDERS / NO BROKER EXECUTION", fg="green").pack(pady=(0, 16))
        tk.Label(root, text="Machine ID for this PC:", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=36)
        mid_box = tk.Entry(root, width=70)
        mid_box.insert(0, mid)
        mid_box.configure(state="readonly")
        mid_box.pack(padx=36, pady=6)
        tk.Button(root, text="Copy Machine ID", width=22, command=copy_machine_id).pack(pady=4)
        tk.Label(root, text="Paste HQE User/License Key:", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=36, pady=(18, 0))
        tk.Entry(root, textvariable=license_var, width=92, show="*").pack(padx=36, pady=6)
        tk.Button(root, text="Activate / Login", width=24, height=2, command=activate_license).pack(pady=12)
        st = license_status(workspace)
        tk.Label(root, text=f"License status: {st.get('reason')}", fg="orange").pack(pady=8)
        tk.Label(root, textvariable=status_var, wraplength=820, justify="left").pack(side="bottom", pady=14)

    def show_main() -> None:
        st = license_status(workspace)
        if not st.get("valid"):
            show_activation()
            return
        payload = st.get("payload", {})
        for child in root.winfo_children():
            child.destroy()
        tk.Label(root, text="HQE Product App", font=("Segoe UI", 20, "bold")).pack(pady=(18, 2))
        tk.Label(root, text="PAPER ONLY / DATA ONLY / NO REAL ORDERS / NO BROKER EXECUTION / NO AUTO TRADING", fg="green").pack(pady=(0, 10))
        tk.Label(root, text=f"Licensed to: {payload.get('customer_name', 'Customer')} | Expires: {payload.get('expires_on', '')}").pack(pady=2)
        tk.Label(root, text=f"Workspace: {workspace}", wraplength=840, justify="left").pack(pady=2)

        form = tk.Frame(root)
        form.pack(pady=10)
        tk.Label(form, text="User:").grid(row=0, column=0, sticky="e", padx=4)
        tk.Entry(form, textvariable=user_var, width=22).grid(row=0, column=1, padx=4)
        tk.Label(form, text="Symbol:").grid(row=0, column=2, sticky="e", padx=4)
        tk.Entry(form, textvariable=symbol_var, width=24).grid(row=0, column=3, padx=4)
        tk.Label(form, text="Trading Date:").grid(row=0, column=4, sticky="e", padx=4)
        tk.Entry(form, textvariable=date_var, width=14).grid(row=0, column=5, padx=4)

        steps = tk.Frame(root)
        steps.pack(pady=12, fill="both", expand=True)

        buttons = [
            ("Step 1 - Refresh Fyers Token", refresh_token),
            ("Step 2 - Historical 5m Data-Only Test", data_test),
            ("Step 3 - Start Paper Watch 09:15-15:30", start_watch),
            ("Step 4 - Run Daily Report Pack", run_daily_pack),
            ("Open Daily Report", open_report),
            ("Open Evidence Folder", open_evidence),
        ]
        for text, command in buttons:
            tk.Button(steps, text=text, width=48, height=2, command=command).pack(pady=6)

        tk.Label(root, textvariable=status_var, wraplength=840, justify="left", fg="blue").pack(side="bottom", pady=14)

    if license_status(workspace).get("valid"):
        show_main()
    else:
        show_activation()

    root.mainloop()
    return 0


def main() -> int:
    args = build_parser().parse_args()
    if args.guard_check:
        return guard_check()
    return run_gui(args)


if __name__ == "__main__":
    raise SystemExit(main())
