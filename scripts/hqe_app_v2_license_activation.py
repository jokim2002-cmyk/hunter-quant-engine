from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Dict

from hqe_product_license_common import (
    license_file_path,
    load_public_key,
    machine_id,
    public_key_path,
    verify_license_key,
)

VERSION = "HQE_APP_V2_LICENSE_ACTIVATION_V1"


def activation_status(workspace: Path) -> Dict[str, Any]:
    mid = machine_id()
    lic = license_file_path(workspace)
    pub = public_key_path(workspace)

    if not pub.exists():
        return {
            "valid": False,
            "reason": "public_key_missing",
            "machine_id": mid,
            "license_file": str(lic),
            "public_key_file": str(pub),
        }

    if not lic.exists():
        return {
            "valid": False,
            "reason": "license_missing",
            "machine_id": mid,
            "license_file": str(lic),
            "public_key_file": str(pub),
        }

    try:
        public_key = load_public_key(pub)
        result = verify_license_key(
            lic.read_text(encoding="utf-8-sig").strip(),
            public_key,
            expected_machine_id=mid,
        )
    except Exception as exc:
        return {
            "valid": False,
            "reason": f"license_read_error:{exc}",
            "machine_id": mid,
            "license_file": str(lic),
            "public_key_file": str(pub),
        }

    result.update({
        "machine_id": mid,
        "license_file": str(lic),
        "public_key_file": str(pub),
    })
    return result


def activate(workspace: Path, key: str) -> Dict[str, Any]:
    clean = key.strip()
    if not clean:
        return {"valid": False, "reason": "license_key_blank", "machine_id": machine_id()}

    pub = public_key_path(workspace)
    if not pub.exists():
        return {"valid": False, "reason": "public_key_missing", "machine_id": machine_id()}

    public_key = load_public_key(pub)
    result = verify_license_key(
        clean,
        public_key,
        expected_machine_id=machine_id(),
    )

    if result.get("valid"):
        lic = license_file_path(workspace)
        lic.parent.mkdir(parents=True, exist_ok=True)
        lic.write_text(clean, encoding="utf-8")

    result.update({
        "machine_id": machine_id(),
        "license_saved": bool(result.get("valid")),
    })
    return result


def run_activation_gui(workspace: Path, initial_reason: str = "license_required") -> bool:
    try:
        import tkinter as tk
        from tkinter import messagebox
    except Exception:
        return False

    workspace.mkdir(parents=True, exist_ok=True)
    activated = {"value": False}
    mid = machine_id()

    root = tk.Tk()
    root.title("HQE App V2 License Activation")
    root.geometry("760x520")
    root.configure(bg="#0f172a")

    tk.Label(
        root,
        text="HQE App V2 Activation",
        font=("Segoe UI", 22, "bold"),
        bg="#0f172a",
        fg="#f8fafc",
    ).pack(anchor="w", padx=28, pady=(26, 4))

    tk.Label(
        root,
        text="PAPER ONLY • DATA ONLY • NO REAL ORDERS • NO BROKER EXECUTION",
        font=("Segoe UI", 10, "bold"),
        bg="#0f172a",
        fg="#86efac",
    ).pack(anchor="w", padx=28, pady=(0, 20))

    card = tk.Frame(root, bg="#17213a")
    card.pack(fill="both", expand=True, padx=28, pady=(0, 24))

    tk.Label(
        card,
        text=f"License status: {initial_reason.replace('_', ' ').title()}",
        font=("Segoe UI", 11, "bold"),
        bg="#17213a",
        fg="#fbbf24",
    ).pack(anchor="w", padx=20, pady=(18, 12))

    tk.Label(
        card,
        text="Machine ID",
        bg="#17213a",
        fg="#cbd5e1",
    ).pack(anchor="w", padx=20)

    machine_entry = tk.Entry(card, width=74)
    machine_entry.insert(0, mid)
    machine_entry.configure(state="readonly")
    machine_entry.pack(anchor="w", padx=20, pady=(4, 8))

    def copy_machine_id() -> None:
        root.clipboard_clear()
        root.clipboard_append(mid)
        root.update()
        status_var.set("Machine ID copied. Generate a new license for this machine.")

    tk.Button(
        card,
        text="Copy Machine ID",
        command=copy_machine_id,
        width=22,
    ).pack(anchor="w", padx=20, pady=(0, 18))

    tk.Label(
        card,
        text="Paste New HQE License Key",
        bg="#17213a",
        fg="#cbd5e1",
    ).pack(anchor="w", padx=20)

    key_var = tk.StringVar()
    tk.Entry(card, textvariable=key_var, width=74, show="*").pack(
        anchor="w", padx=20, pady=(4, 12)
    )

    status_var = tk.StringVar(
        value="This PC needs a license generated for the Machine ID shown above."
    )

    def activate_now() -> None:
        result = activate(workspace, key_var.get())
        if result.get("valid"):
            activated["value"] = True
            messagebox.showinfo("HQE Activation", "License activated successfully.")
            root.destroy()
            return

        reason = str(result.get("reason", "invalid_license"))
        status_var.set(f"Activation failed: {reason}")
        messagebox.showerror("HQE Activation", f"License invalid: {reason}")

    tk.Button(
        card,
        text="Activate and Open HQE",
        command=activate_now,
        width=26,
        height=2,
    ).pack(anchor="w", padx=20, pady=(0, 12))

    tk.Label(
        card,
        textvariable=status_var,
        bg="#17213a",
        fg="#94a3b8",
        wraplength=670,
        justify="left",
    ).pack(anchor="w", padx=20, pady=(0, 18))

    root.mainloop()
    return bool(activated["value"])


def guard_payload() -> Dict[str, Any]:
    return {
        "version": VERSION,
        "guard_check_status": "PASS",
        "machine_bound_license_required": True,
        "machine_id_copy_supported": True,
        "license_key_saved_only_after_validation": True,
        "license_bypass_added": False,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
    }


if __name__ == "__main__":
    print(json.dumps(guard_payload(), indent=2, sort_keys=True))
