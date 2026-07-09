from __future__ import annotations

import argparse
import json
from pathlib import Path

from hqe_product_license_common import (
    DEFAULT_OWNER_KEY_DIR,
    DEFAULT_PRIVATE_KEY_NAME,
    DEFAULT_PUBLIC_KEY_NAME,
    app_config_dir,
    create_license_payload,
    init_owner_keys,
    load_private_key,
    machine_id,
    make_license_key,
)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="HQE owner license generator")
    p.add_argument("--owner-dir", default=str(DEFAULT_OWNER_KEY_DIR))
    p.add_argument("--init-owner-keys", action="store_true")
    p.add_argument("--force-new-keys", action="store_true")
    p.add_argument("--bits", type=int, default=1024)
    p.add_argument("--install-public-key-to-workspace", default="")
    p.add_argument("--print-machine-id", action="store_true")
    p.add_argument("--customer-name", default="")
    p.add_argument("--customer-email", default="")
    p.add_argument("--machine-id", default="")
    p.add_argument("--expires-on", default="")
    p.add_argument("--output", default="")
    return p


def main() -> int:
    args = build_parser().parse_args()
    owner = Path(args.owner_dir)
    owner.mkdir(parents=True, exist_ok=True)

    if args.print_machine_id:
        print(machine_id())
        return 0

    if args.init_owner_keys or args.force_new_keys or not (owner / DEFAULT_PRIVATE_KEY_NAME).exists():
        result = init_owner_keys(owner, bits=args.bits, force=args.force_new_keys)
        print(json.dumps({"owner_key_status": result}, indent=2, sort_keys=True))

    if args.install_public_key_to_workspace:
        public_src = owner / DEFAULT_PUBLIC_KEY_NAME
        if not public_src.exists():
            raise SystemExit("Public key not found. Run --init-owner-keys first.")
        dest = app_config_dir(args.install_public_key_to_workspace) / DEFAULT_PUBLIC_KEY_NAME
        dest.write_text(public_src.read_text(encoding="utf-8-sig"), encoding="utf-8")
        print(json.dumps({"installed_public_key": str(dest)}, indent=2, sort_keys=True))

    if args.customer_name or args.customer_email or args.machine_id or args.expires_on:
        missing = [name for name in ["customer-name", "machine-id", "expires-on"] if not getattr(args, name.replace("-", "_"))]
        if missing:
            raise SystemExit("Missing required license fields: " + ", ".join(missing))
        private_key = load_private_key(owner / DEFAULT_PRIVATE_KEY_NAME)
        payload = create_license_payload(args.customer_name, args.customer_email, args.machine_id, args.expires_on)
        key = make_license_key(payload, private_key)
        if args.output:
            out = Path(args.output)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(key, encoding="utf-8")
            print(json.dumps({"license_key_file": str(out), "machine_id": args.machine_id, "expires_on": args.expires_on}, indent=2, sort_keys=True))
        else:
            print(key)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
