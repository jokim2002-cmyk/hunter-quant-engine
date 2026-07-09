from __future__ import annotations

import argparse
import subprocess

from hqe_product_license_common import machine_id


def main() -> int:
    p = argparse.ArgumentParser(description="HQE customer machine ID tool")
    p.add_argument("--copy", action="store_true")
    args = p.parse_args()

    mid = machine_id()
    print(mid)

    if args.copy:
        try:
            subprocess.run("clip", input=mid, text=True, check=True)
            print("COPIED_TO_CLIPBOARD")
        except Exception:
            print("COPY_FAILED_MANUAL_COPY_REQUIRED")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
