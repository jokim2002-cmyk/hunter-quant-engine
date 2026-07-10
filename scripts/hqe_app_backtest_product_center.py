from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

VERSION = "HQE_APP_BACKTEST_PRODUCT_CENTER_V1"


def backtest_center_snapshot(
    repo_root: Path,
    workspace: Path,
) -> dict[str, Any]:
    from hqe_backtest_product_engine import product_snapshot

    snapshot = product_snapshot(repo_root, workspace)
    snapshot["version"] = VERSION
    return snapshot


def create_backtest_job(
    form: dict[str, Any],
    workspace: Path,
) -> Path:
    from hqe_backtest_product_engine import (
        create_job_spec,
        save_job_spec,
    )

    job = create_job_spec(
        dataset_path=Path(str(form["dataset_path"])),
        strategy_path=Path(str(form["strategy_path"])),
        start_date=str(form.get("start_date", "")),
        end_date=str(form.get("end_date", "")),
        initial_capital=form.get("initial_capital", 100000),
        brokerage_per_order=form.get("brokerage_per_order", 20),
        slippage_bps=form.get("slippage_bps", 5),
        tax_bps=form.get("tax_bps", 2),
        max_trades_per_day=form.get("max_trades_per_day", 3),
    )
    return save_job_spec(job, workspace)


def preview_backtest_job(
    form: dict[str, Any],
) -> dict[str, Any]:
    from hqe_backtest_product_engine import (
        create_job_spec,
        validate_job_spec,
    )

    job = create_job_spec(
        dataset_path=Path(str(form["dataset_path"])),
        strategy_path=Path(str(form["strategy_path"])),
        start_date=str(form.get("start_date", "")),
        end_date=str(form.get("end_date", "")),
        initial_capital=form.get("initial_capital", 100000),
        brokerage_per_order=form.get("brokerage_per_order", 20),
        slippage_bps=form.get("slippage_bps", 5),
        tax_bps=form.get("tax_bps", 2),
        max_trades_per_day=form.get("max_trades_per_day", 3),
    )
    validation = validate_job_spec(job)
    return {
        "job": job,
        "validation": validation,
    }


def run_backtest_job(
    repo_root: Path,
    workspace: Path,
    job_path: Path,
    runner_path: Path,
):
    from hqe_backtest_product_engine import launch_job_worker

    return launch_job_worker(
        repo_root,
        workspace,
        job_path,
        runner_path,
    )


def guard_payload() -> dict[str, Any]:
    return {
        "version": VERSION,
        "guard_check_status": "PASS",
        "workflow": "APP_BACKTEST_PRODUCT_CENTER",
        "recorded_data_only": True,
        "real_money_enabled": False,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "option_selling_enabled": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="HQE app backtest product center"
    )
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[1]),
    )
    parser.add_argument("--workspace", default="")
    parser.add_argument("--snapshot", action="store_true")
    parser.add_argument("--guard-check", action="store_true")
    args = parser.parse_args()

    if args.guard_check:
        print(json.dumps(guard_payload(), indent=2, sort_keys=True))
        return 0
    if not args.workspace:
        parser.error("--workspace is required.")
    if args.snapshot:
        print(json.dumps(
            backtest_center_snapshot(
                Path(args.repo_root),
                Path(args.workspace),
            ),
            indent=2,
            sort_keys=True,
        ))
        return 0
    parser.error("Use --snapshot or --guard-check.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
