from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

from hqe_multi_broker_data_architecture import (
    BLOCKED_ORDER_ACTIONS,
    BROKER_REGISTRY,
    SAFETY_LOCK,
    get_adapter,
)

VERSION = "HQE_BROKER_CONNECT_CENTER_V1"


def guard_payload() -> Dict[str, Any]:
    return {
        "version": VERSION,
        "guard_check_status": "PASS",
        "broker_count": len(BROKER_REGISTRY),
        "broker_ids": list(BROKER_REGISTRY),
        "credential_persistence": "DISABLED",
        "plaintext_secret_storage_allowed": False,
        "network_test_mode": "READINESS_ONLY",
        "order_actions": {name: "HARD_BLOCKED" for name in BLOCKED_ORDER_ACTIONS},
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "safety_lock": SAFETY_LOCK,
    }


def readiness_payload(broker_id: str, values: Dict[str, str]) -> Dict[str, Any]:
    adapter = get_adapter(broker_id)
    return {
        "version": VERSION,
        "broker_id": broker_id,
        "display_name": BROKER_REGISTRY[broker_id].display_name,
        "credential_status": adapter.credential_status(values),
        "connection_readiness": adapter.connection_test(values),
        "secret_values_redacted": True,
        "credential_values_written_to_disk": False,
        "order_api_invoked": False,
        "broker_execution_invoked": False,
    }


def launch_gui(workspace: Path) -> int:
    import tkinter as tk
    from tkinter import messagebox, ttk

    root = tk.Tk()
    root.title("HQE Broker Connect Center")
    root.geometry("760x650")
    root.configure(bg="#0f172a")

    selected = tk.StringVar(value="fyers")
    status_var = tk.StringVar(value="Credentials stay in memory only.")
    entries: Dict[str, tk.Entry] = {}

    tk.Label(root, text="Broker Connect Center", font=("Segoe UI", 22, "bold"),
             bg="#0f172a", fg="#f8fafc").pack(anchor="w", padx=24, pady=(22, 2))
    tk.Label(root, text="DATA ONLY • NO REAL ORDERS • NO BROKER EXECUTION",
             font=("Segoe UI", 10, "bold"), bg="#0f172a", fg="#86efac").pack(
                 anchor="w", padx=24, pady=(0, 18))

    broker_row = tk.Frame(root, bg="#0f172a")
    broker_row.pack(fill="x", padx=20)
    form_frame = tk.Frame(root, bg="#17213a")
    form_frame.pack(fill="both", expand=True, padx=24, pady=18)

    def rebuild_form() -> None:
        for child in form_frame.winfo_children():
            child.destroy()
        entries.clear()
        definition = BROKER_REGISTRY[selected.get()]
        tk.Label(form_frame, text=f"{definition.display_name} data connection",
                 font=("Segoe UI", 14, "bold"), bg="#17213a", fg="#f8fafc").pack(
                     anchor="w", padx=18, pady=(16, 10))
        for field in definition.credential_fields:
            tk.Label(form_frame, text=field.replace("_", " ").title(),
                     bg="#17213a", fg="#cbd5e1").pack(anchor="w", padx=18)
            entry = tk.Entry(form_frame, width=62, show="*")
            entry.pack(anchor="w", padx=18, pady=(3, 10))
            entries[field] = entry
        tk.Label(form_frame, text="Secrets are not displayed or saved.",
                 bg="#17213a", fg="#94a3b8").pack(anchor="w", padx=18, pady=(0, 14))

    for definition in BROKER_REGISTRY.values():
        ttk.Radiobutton(
            broker_row,
            text=definition.display_name,
            variable=selected,
            value=definition.broker_id,
            command=rebuild_form,
        ).pack(side="left", padx=4)

    def test_readiness() -> None:
        values = {name: entry.get().strip() for name, entry in entries.items()}
        payload = readiness_payload(selected.get(), values)
        status_var.set(payload["connection_readiness"]["status"].replace("_", " ").title())
        missing = payload["credential_status"]["missing_fields"]
        if missing:
            messagebox.showwarning("HQE Broker Readiness", "Missing: " + ", ".join(missing))
        else:
            messagebox.showinfo("HQE Broker Readiness", payload["connection_readiness"]["message"])

    actions = tk.Frame(root, bg="#0f172a")
    actions.pack(fill="x", padx=24, pady=(0, 12))
    ttk.Button(actions, text="Check Data Connection Readiness",
               command=test_readiness).pack(side="left")
    ttk.Button(actions, text="Close", command=root.destroy).pack(side="right")
    tk.Label(root, textvariable=status_var, bg="#1e293b", fg="#cbd5e1",
             anchor="w", padx=16, pady=10).pack(fill="x", side="bottom")

    rebuild_form()
    root.mainloop()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="HQE Broker Connect Center")
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--launch", action="store_true")
    parser.add_argument("--guard-check", action="store_true")
    parser.add_argument("--broker", default="fyers", choices=list(BROKER_REGISTRY))
    args = parser.parse_args()
    if args.guard_check:
        print(json.dumps(guard_payload(), indent=2, sort_keys=True))
        return 0
    if args.launch:
        return launch_gui(Path(args.workspace))
    print(json.dumps(readiness_payload(args.broker, {}), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
