from __future__ import annotations

import argparse
import csv
import json
import math
import re
import subprocess
import sys
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

VERSION = "HQE_BACKTEST_PRODUCT_ENGINE_V1"
PRODUCT_FOLDER = "HQE_BACKTEST_PRODUCT"
STATUS_FILE = "HQE_BACKTEST_PRODUCT_STATUS.json"

DATA_FLAGS = ("--dataset", "--data-file", "--input-csv", "--csv")
STRATEGY_FLAGS = ("--strategy-pack", "--strategy-file", "--strategy")
OUTPUT_FLAGS = ("--output-dir", "--output-folder", "--output")
START_FLAGS = ("--start-date", "--from-date")
END_FLAGS = ("--end-date", "--to-date")
CAPITAL_FLAGS = ("--initial-capital", "--capital")
BROKERAGE_FLAGS = ("--brokerage-per-order", "--brokerage")
SLIPPAGE_FLAGS = ("--slippage-bps", "--slippage")
TAX_FLAGS = ("--tax-bps", "--charges-bps")
MAX_TRADES_FLAGS = ("--max-trades-per-day", "--daily-trade-limit")

FORBIDDEN_TOKENS = {
    "--live",
    "--real",
    "--real-orders",
    "--place-order",
    "--broker-execution",
    "--auto-trading",
    "--option-selling",
    "place_order",
    "orderbook",
    "tradebook",
}

SAFETY_LOCK = {
    "recorded_data_only": True,
    "research_only": True,
    "no_real_money": True,
    "no_real_orders": True,
    "no_broker_execution": True,
    "no_auto_trading": True,
    "no_option_selling": True,
    "no_fake_trades": True,
    "no_profitability_claim": True,
}


def utc_now_text() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    temporary.replace(path)


def safe_float(value: Any, field: str, *, minimum: float = 0.0) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be numeric.") from exc
    if not math.isfinite(parsed) or parsed < minimum:
        raise ValueError(f"{field} must be at least {minimum}.")
    return parsed


def safe_int(value: Any, field: str, *, minimum: int = 0) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be an integer.") from exc
    if parsed < minimum:
        raise ValueError(f"{field} must be at least {minimum}.")
    return parsed


def parse_iso_date(value: str, field: str) -> str:
    text = value.strip()
    if not text:
        return ""
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError as exc:
        raise ValueError(f"{field} must use YYYY-MM-DD.") from exc


def product_paths(workspace: Path) -> dict[str, Path]:
    root = workspace / PRODUCT_FOLDER
    return {
        "root": root,
        "jobs": root / "jobs",
        "runs": root / "runs",
        "status": root / STATUS_FILE,
    }


def discover_datasets(
    repo_root: Path,
    workspace: Path,
) -> list[dict[str, Any]]:
    from hqe_market_data_quality_engine import quality_snapshot

    snapshot = quality_snapshot(repo_root, workspace)
    datasets = [
        item
        for item in snapshot.get("analyses", [])
        if item.get("status") != "FAILED"
        and int(item.get("row_count", 0) or 0) > 0
    ]
    datasets.sort(
        key=lambda item: (
            int(item.get("score", 0) or 0),
            int(item.get("row_count", 0) or 0),
        ),
        reverse=True,
    )
    return datasets


def discover_strategy_packs(
    repo_root: Path,
    workspace: Path,
) -> list[dict[str, Any]]:
    from hqe_strategy_pack_registry import registry_snapshot

    snapshot = registry_snapshot(repo_root, workspace)
    return [
        record
        for record in snapshot.get("packs", [])
        if record.get("valid") is True
    ]


def runner_help(
    repo_root: Path,
    runner: Path,
) -> dict[str, Any]:
    completed = subprocess.run(
        [
            str(repo_root / ".venv" / "Scripts" / "python.exe"),
            str(runner),
            "--help",
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=60,
    )
    return {
        "status": "PASS" if completed.returncode == 0 else "FAILED",
        "return_code": completed.returncode,
        "text": (completed.stdout + "\n" + completed.stderr).strip(),
    }


def supported_options(help_text: str) -> set[str]:
    return set(
        re.findall(
            r"(?<!\w)--[a-z0-9][a-z0-9-]*",
            help_text.lower(),
        )
    )


def first_supported(
    options: set[str],
    candidates: tuple[str, ...],
) -> str:
    for candidate in candidates:
        if candidate in options:
            return candidate
    return ""


def runner_compatibility(
    repo_root: Path,
    runner: Path,
    *,
    help_text: str | None = None,
) -> dict[str, Any]:
    if help_text is None:
        help_payload = runner_help(repo_root, runner)
        if help_payload["status"] != "PASS":
            return {
                "compatible": False,
                "reason": "Runner --help failed.",
                "options": [],
            }
        help_text = str(help_payload["text"])

    options = supported_options(help_text)
    job_file_mode = "--job-file" in options
    dataset_flag = first_supported(options, DATA_FLAGS)
    output_flag = first_supported(options, OUTPUT_FLAGS)
    guard_ready = "--guard-check" in options
    compatible = bool(
        guard_ready
        and (
            job_file_mode
            or (dataset_flag and output_flag)
        )
    )
    reason = (
        "Compatible recorded-data runner."
        if compatible
        else (
            "Runner needs --guard-check and either --job-file "
            "or dataset/output flags."
        )
    )
    return {
        "compatible": compatible,
        "reason": reason,
        "job_file_mode": job_file_mode,
        "dataset_flag": dataset_flag,
        "strategy_flag": first_supported(options, STRATEGY_FLAGS),
        "output_flag": output_flag,
        "start_flag": first_supported(options, START_FLAGS),
        "end_flag": first_supported(options, END_FLAGS),
        "capital_flag": first_supported(options, CAPITAL_FLAGS),
        "brokerage_flag": first_supported(options, BROKERAGE_FLAGS),
        "slippage_flag": first_supported(options, SLIPPAGE_FLAGS),
        "tax_flag": first_supported(options, TAX_FLAGS),
        "max_trades_flag": first_supported(options, MAX_TRADES_FLAGS),
        "supports_write": "--write" in options,
        "supports_recorded_data_only": "--recorded-data-only" in options,
        "supports_paper_only": "--paper-only" in options,
        "options": sorted(options),
    }


def discover_backtest_runners(
    repo_root: Path,
) -> list[dict[str, Any]]:
    scripts = repo_root / "scripts"
    excluded = {
        "hqe_backtest_product_engine.py",
        "hqe_app_backtest_product_center.py",
    }
    candidates: list[Path] = []
    if scripts.exists():
        for path in scripts.glob("*backtest*.py"):
            if path.name in excluded or not path.is_file():
                continue
            candidates.append(path)

    records: list[dict[str, Any]] = []
    for path in sorted(candidates):
        help_payload = runner_help(repo_root, path)
        compatibility = runner_compatibility(
            repo_root,
            path,
            help_text=str(help_payload.get("text", "")),
        )
        records.append(
            {
                "name": path.name,
                "path": str(path),
                "help_status": help_payload["status"],
                **compatibility,
            }
        )

    records.sort(
        key=lambda item: (
            bool(item.get("compatible")),
            bool(item.get("job_file_mode")),
            item.get("name", ""),
        ),
        reverse=True,
    )
    return records


def make_job_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"BT_{stamp}_{uuid.uuid4().hex[:6].upper()}"


def create_job_spec(
    *,
    dataset_path: Path,
    strategy_path: Path,
    start_date: str = "",
    end_date: str = "",
    initial_capital: Any = 100000,
    brokerage_per_order: Any = 20,
    slippage_bps: Any = 5,
    tax_bps: Any = 2,
    max_trades_per_day: Any = 3,
) -> dict[str, Any]:
    job_id = make_job_id()
    return {
        "version": VERSION,
        "job_id": job_id,
        "mode": "RECORDED_DATA_RESEARCH_BACKTEST",
        "dataset_path": str(dataset_path),
        "strategy_path": str(strategy_path),
        "start_date": parse_iso_date(start_date, "start_date"),
        "end_date": parse_iso_date(end_date, "end_date"),
        "initial_capital": safe_float(
            initial_capital,
            "initial_capital",
            minimum=1,
        ),
        "brokerage_per_order": safe_float(
            brokerage_per_order,
            "brokerage_per_order",
            minimum=0,
        ),
        "slippage_bps": safe_float(
            slippage_bps,
            "slippage_bps",
            minimum=0,
        ),
        "tax_bps": safe_float(
            tax_bps,
            "tax_bps",
            minimum=0,
        ),
        "max_trades_per_day": safe_int(
            max_trades_per_day,
            "max_trades_per_day",
            minimum=1,
        ),
        "created_at_utc": utc_now_text(),
        "safety": dict(SAFETY_LOCK),
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "option_selling_enabled": False,
    }


def validate_job_spec(
    job: dict[str, Any],
) -> dict[str, Any]:
    from hqe_market_data_quality_engine import analyze_csv
    from hqe_strategy_pack_schema import validate_strategy_pack

    errors: list[str] = []
    warnings: list[str] = []

    if job.get("mode") != "RECORDED_DATA_RESEARCH_BACKTEST":
        errors.append("Backtest mode must remain recorded-data research.")

    dataset = Path(str(job.get("dataset_path", "")))
    strategy = Path(str(job.get("strategy_path", "")))
    if not dataset.exists():
        errors.append("Dataset file does not exist.")
    if not strategy.exists():
        errors.append("Strategy-pack file does not exist.")

    dataset_quality: dict[str, Any] = {}
    if dataset.exists():
        dataset_quality = analyze_csv(dataset)
        if dataset_quality.get("status") == "FAILED":
            errors.append("Dataset failed quality validation.")
        elif dataset_quality.get("status") == "CHECK":
            warnings.append("Dataset has quality warnings.")

    pack_validation: dict[str, Any] = {}
    pack: dict[str, Any] = {}
    if strategy.exists():
        pack = read_json(strategy)
        pack_validation = validate_strategy_pack(pack)
        if not pack_validation["valid"]:
            errors.extend(
                f"Strategy: {message}"
                for message in pack_validation["errors"]
            )

    start_text = str(job.get("start_date", ""))
    end_text = str(job.get("end_date", ""))
    if start_text and end_text:
        if date.fromisoformat(end_text) < date.fromisoformat(start_text):
            errors.append("end_date cannot be earlier than start_date.")

    safety = job.get("safety", {})
    for key, required in SAFETY_LOCK.items():
        if safety.get(key) is not required:
            errors.append(f"safety.{key} must remain {required}.")

    if (
        job.get("real_orders_enabled") is not False
        or job.get("broker_execution_enabled") is not False
        or job.get("auto_trading_enabled") is not False
        or job.get("option_selling_enabled") is not False
    ):
        errors.append("Execution safety flags must remain false.")

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "dataset_quality": dataset_quality,
        "strategy_validation": pack_validation,
        "strategy_name": str(pack.get("name", "")),
        "strategy_id": str(pack.get("strategy_id", "")),
    }


def save_job_spec(
    job: dict[str, Any],
    workspace: Path,
) -> Path:
    validation = validate_job_spec(job)
    if not validation["valid"]:
        raise ValueError(
            "Backtest job is invalid: "
            + "; ".join(validation["errors"])
        )
    paths = product_paths(workspace)
    paths["jobs"].mkdir(parents=True, exist_ok=True)
    target = paths["jobs"] / f"{job['job_id']}.json"
    write_json(target, job)
    return target


def runner_guard(
    repo_root: Path,
    runner: Path,
) -> dict[str, Any]:
    completed = subprocess.run(
        [
            str(repo_root / ".venv" / "Scripts" / "python.exe"),
            str(runner),
            "--guard-check",
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=90,
    )
    return {
        "status": "PASS" if completed.returncode == 0 else "FAILED",
        "return_code": completed.returncode,
        "stdout_tail": completed.stdout[-900:],
        "stderr_tail": completed.stderr[-900:],
    }


def append_pair(
    command: list[str],
    flag: str,
    value: Any,
) -> None:
    if flag and str(value) != "":
        command.extend((flag, str(value)))


def build_runner_command(
    repo_root: Path,
    runner: Path,
    job_path: Path,
    output_dir: Path,
    *,
    help_text: str | None = None,
) -> list[str]:
    job = read_json(job_path)
    validation = validate_job_spec(job)
    if not validation["valid"]:
        raise ValueError(
            "Backtest job is invalid: "
            + "; ".join(validation["errors"])
        )

    compatibility = runner_compatibility(
        repo_root,
        runner,
        help_text=help_text,
    )
    if not compatibility["compatible"]:
        raise RuntimeError(str(compatibility["reason"]))

    command = [
        str(repo_root / ".venv" / "Scripts" / "python.exe"),
        str(runner),
    ]
    if compatibility["job_file_mode"]:
        append_pair(command, "--job-file", job_path)
    else:
        append_pair(
            command,
            str(compatibility["dataset_flag"]),
            job["dataset_path"],
        )
        append_pair(
            command,
            str(compatibility["strategy_flag"]),
            job["strategy_path"],
        )
        append_pair(
            command,
            str(compatibility["output_flag"]),
            output_dir,
        )
        append_pair(
            command,
            str(compatibility["start_flag"]),
            job["start_date"],
        )
        append_pair(
            command,
            str(compatibility["end_flag"]),
            job["end_date"],
        )
        append_pair(
            command,
            str(compatibility["capital_flag"]),
            job["initial_capital"],
        )
        append_pair(
            command,
            str(compatibility["brokerage_flag"]),
            job["brokerage_per_order"],
        )
        append_pair(
            command,
            str(compatibility["slippage_flag"]),
            job["slippage_bps"],
        )
        append_pair(
            command,
            str(compatibility["tax_flag"]),
            job["tax_bps"],
        )
        append_pair(
            command,
            str(compatibility["max_trades_flag"]),
            job["max_trades_per_day"],
        )

    if compatibility["supports_recorded_data_only"]:
        command.append("--recorded-data-only")
    if compatibility["supports_paper_only"]:
        command.append("--paper-only")
    if compatibility["supports_write"]:
        command.append("--write")

    lowered = " ".join(command).lower()
    unsafe = sorted(
        token for token in FORBIDDEN_TOKENS if token in lowered
    )
    if unsafe:
        raise RuntimeError(
            "Unsafe backtest command token detected: "
            + ", ".join(unsafe)
        )
    return command


def normalized_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def pick_float(
    payload: dict[str, Any],
    keys: tuple[str, ...],
) -> float | None:
    normalized = {
        normalized_key(str(key)): value
        for key, value in payload.items()
    }
    for key in keys:
        if key not in normalized:
            continue
        try:
            return float(normalized[key])
        except (TypeError, ValueError):
            continue
    return None


def csv_trade_metrics(path: Path) -> dict[str, Any]:
    try:
        with path.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as handle:
            reader = csv.DictReader(handle)
            rows = list(reader)
    except Exception:
        return {}

    if not rows:
        return {
            "trade_count": 0,
            "win_count": 0,
            "loss_count": 0,
            "net_pnl": 0.0,
            "max_drawdown": 0.0,
            "equity_curve": [],
        }

    pnl_aliases = (
        "net_pnl",
        "net",
        "pnl",
        "profit_loss",
        "realized_pnl",
    )
    values: list[float] = []
    for row in rows:
        normalized = {
            normalized_key(str(key)): value
            for key, value in row.items()
        }
        pnl: float | None = None
        for alias in pnl_aliases:
            if alias not in normalized:
                continue
            try:
                pnl = float(normalized[alias])
                break
            except (TypeError, ValueError):
                continue
        if pnl is not None:
            values.append(pnl)

    if not values:
        return {"trade_count": len(rows)}

    equity: list[float] = []
    cumulative = 0.0
    peak = 0.0
    max_drawdown = 0.0
    for pnl in values:
        cumulative += pnl
        equity.append(round(cumulative, 4))
        peak = max(peak, cumulative)
        max_drawdown = max(max_drawdown, peak - cumulative)

    wins = sum(1 for value in values if value > 0)
    losses = sum(1 for value in values if value < 0)
    return {
        "trade_count": len(values),
        "win_count": wins,
        "loss_count": losses,
        "win_rate": round(wins / len(values), 6) if values else 0.0,
        "net_pnl": round(sum(values), 4),
        "average_net_per_trade": round(
            sum(values) / len(values),
            4,
        ) if values else 0.0,
        "max_drawdown": round(max_drawdown, 4),
        "equity_curve": equity,
    }


def normalize_backtest_results(
    output_dir: Path,
) -> dict[str, Any]:
    json_files = sorted(
        output_dir.rglob("*.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    ) if output_dir.exists() else []
    csv_files = sorted(
        output_dir.rglob("*.csv"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    ) if output_dir.exists() else []

    json_payloads = [
        (path, read_json(path))
        for path in json_files[:50]
    ]
    merged: dict[str, Any] = {}
    source_json = ""
    for path, payload in json_payloads:
        if not payload:
            continue
        for key, value in payload.items():
            merged.setdefault(str(key), value)
        if not source_json:
            source_json = str(path)

    trade_candidates = [
        path
        for path in csv_files
        if "trade" in path.name.lower()
    ]
    trade_path = (
        trade_candidates[0]
        if trade_candidates
        else (csv_files[0] if csv_files else None)
    )
    csv_metrics = csv_trade_metrics(trade_path) if trade_path else {}

    metric_keys = {
        "trade_count": ("trade_count", "completed_trades", "trades"),
        "win_rate": ("win_rate", "winning_rate"),
        "gross_pnl": ("gross_pnl", "gross", "gross_profit"),
        "charges": ("charges", "total_charges", "costs"),
        "net_pnl": ("net_pnl", "net", "net_profit"),
        "average_net_per_trade": (
            "average_net_per_trade",
            "avg_net",
            "average_trade",
        ),
        "max_drawdown": (
            "max_drawdown",
            "maximum_drawdown",
            "drawdown",
        ),
    }
    metrics: dict[str, Any] = {}
    for output_key, aliases in metric_keys.items():
        value = pick_float(merged, aliases)
        if value is not None:
            metrics[output_key] = value

    for key, value in csv_metrics.items():
        metrics.setdefault(key, value)

    trade_count = int(metrics.get("trade_count", 0) or 0)
    if trade_count and "win_rate" not in metrics:
        wins = int(metrics.get("win_count", 0) or 0)
        metrics["win_rate"] = round(wins / trade_count, 6)

    summary = {
        "version": VERSION,
        "generated_at_utc": utc_now_text(),
        "status": "RESULTS_FOUND" if (json_files or csv_files) else "NO_RESULTS",
        "output_dir": str(output_dir),
        "json_file_count": len(json_files),
        "csv_file_count": len(csv_files),
        "source_json": source_json,
        "source_trade_csv": str(trade_path) if trade_path else "",
        "metrics": metrics,
        "equity_curve": csv_metrics.get("equity_curve", []),
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "option_selling_enabled": False,
    }
    write_json(output_dir / "HQE_BACKTEST_PRODUCT_SUMMARY.json", summary)
    return summary


def execute_job(
    repo_root: Path,
    workspace: Path,
    job_path: Path,
    runner_path: Path,
) -> dict[str, Any]:
    paths = product_paths(workspace)
    status_path = paths["status"]
    job = read_json(job_path)
    validation = validate_job_spec(job)
    if not validation["valid"]:
        payload = {
            "version": VERSION,
            "status": "BLOCKED",
            "message": "Backtest job validation failed.",
            "errors": validation["errors"],
            "completed_at_utc": utc_now_text(),
        }
        write_json(status_path, payload)
        return payload

    guard = runner_guard(repo_root, runner_path)
    if guard["status"] != "PASS":
        payload = {
            "version": VERSION,
            "status": "BLOCKED",
            "message": "Backtest runner guard-check failed.",
            "guard": guard,
            "completed_at_utc": utc_now_text(),
        }
        write_json(status_path, payload)
        return payload

    output_dir = paths["runs"] / str(job["job_id"])
    output_dir.mkdir(parents=True, exist_ok=True)
    command = build_runner_command(
        repo_root,
        runner_path,
        job_path,
        output_dir,
    )
    log_path = output_dir / "HQE_BACKTEST_PRODUCT_RUN.log"

    write_json(
        status_path,
        {
            "version": VERSION,
            "status": "RUNNING",
            "message": "Recorded-data research backtest is running.",
            "job_id": job["job_id"],
            "job_path": str(job_path),
            "runner_path": str(runner_path),
            "output_dir": str(output_dir),
            "started_at_utc": utc_now_text(),
            "real_orders_enabled": False,
            "broker_execution_enabled": False,
        },
    )

    completed = subprocess.run(
        command,
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=1800,
    )
    log_path.write_text(
        "COMMAND:\n"
        + " ".join(command)
        + "\n\nSTDOUT:\n"
        + completed.stdout
        + "\n\nSTDERR:\n"
        + completed.stderr,
        encoding="utf-8",
    )

    summary = normalize_backtest_results(output_dir)
    passed = completed.returncode == 0
    payload = {
        "version": VERSION,
        "status": "PASS" if passed else "FAILED",
        "message": (
            "Recorded-data research backtest completed."
            if passed
            else "Backtest runner failed safely."
        ),
        "job_id": job["job_id"],
        "job_path": str(job_path),
        "runner_path": str(runner_path),
        "output_dir": str(output_dir),
        "summary_path": str(
            output_dir / "HQE_BACKTEST_PRODUCT_SUMMARY.json"
        ),
        "log_path": str(log_path),
        "return_code": completed.returncode,
        "completed_at_utc": utc_now_text(),
        "summary": summary,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "option_selling_enabled": False,
    }
    write_json(status_path, payload)
    return payload


def launch_job_worker(
    repo_root: Path,
    workspace: Path,
    job_path: Path,
    runner_path: Path,
) -> subprocess.Popen[Any]:
    pythonw = repo_root / ".venv" / "Scripts" / "pythonw.exe"
    executable = (
        pythonw
        if pythonw.exists()
        else repo_root / ".venv" / "Scripts" / "python.exe"
    )
    command = [
        str(executable),
        str(Path(__file__).resolve()),
        "--repo-root",
        str(repo_root),
        "--workspace",
        str(workspace),
        "--execute-job",
        str(job_path),
        "--runner",
        str(runner_path),
    ]
    return subprocess.Popen(
        command,
        cwd=repo_root,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def recent_runs(
    workspace: Path,
) -> list[dict[str, Any]]:
    paths = product_paths(workspace)
    records: list[dict[str, Any]] = []
    if paths["runs"].exists():
        for summary_path in paths["runs"].glob(
            "*/HQE_BACKTEST_PRODUCT_SUMMARY.json"
        ):
            payload = read_json(summary_path)
            records.append(
                {
                    "job_id": summary_path.parent.name,
                    "summary_path": str(summary_path),
                    "output_dir": str(summary_path.parent),
                    "status": str(payload.get("status", "")),
                    "metrics": payload.get("metrics", {}),
                    "updated_at_utc": datetime.fromtimestamp(
                        summary_path.stat().st_mtime,
                        timezone.utc,
                    ).replace(microsecond=0).isoformat(),
                }
            )
    records.sort(
        key=lambda item: item["updated_at_utc"],
        reverse=True,
    )
    return records


def product_snapshot(
    repo_root: Path,
    workspace: Path,
) -> dict[str, Any]:
    datasets = discover_datasets(repo_root, workspace)
    strategies = discover_strategy_packs(repo_root, workspace)
    runners = discover_backtest_runners(repo_root)
    compatible = [
        runner for runner in runners if runner.get("compatible")
    ]
    paths = product_paths(workspace)
    operation = read_json(paths["status"])
    runs = recent_runs(workspace)

    display = (
        f"Backtest Center: datasets {len(datasets)} | "
        f"strategies {len(strategies)} | "
        f"compatible runners {len(compatible)} | "
        f"runs {len(runs)} | "
        f"operation {operation.get('status', 'IDLE')}"
    )
    return {
        "version": VERSION,
        "display_text": display,
        "datasets": datasets,
        "strategies": strategies,
        "runners": runners,
        "compatible_runner_count": len(compatible),
        "operation": operation,
        "recent_runs": runs,
        "paths": {
            key: str(value)
            for key, value in paths.items()
        },
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "option_selling_enabled": False,
        "safety_lock": SAFETY_LOCK,
    }


def guard_payload() -> dict[str, Any]:
    return {
        "version": VERSION,
        "guard_check_status": "PASS",
        "workflow": "RECORDED_DATA_BACKTEST_PRODUCT_CENTER",
        "recorded_data_only": True,
        "runner_guard_required": True,
        "no_fake_option_prices": True,
        "real_money_enabled": False,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "option_selling_enabled": False,
        "safety_lock": SAFETY_LOCK,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="HQE recorded-data backtest product engine"
    )
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[1]),
    )
    parser.add_argument("--workspace", default="")
    parser.add_argument("--snapshot", action="store_true")
    parser.add_argument("--execute-job", default="")
    parser.add_argument("--runner", default="")
    parser.add_argument("--normalize-output", default="")
    parser.add_argument("--guard-check", action="store_true")
    args = parser.parse_args()

    if args.guard_check:
        print(json.dumps(guard_payload(), indent=2, sort_keys=True))
        return 0
    if args.normalize_output:
        print(json.dumps(
            normalize_backtest_results(Path(args.normalize_output)),
            indent=2,
            sort_keys=True,
        ))
        return 0
    if not args.workspace:
        parser.error("--workspace is required.")

    repo_root = Path(args.repo_root)
    workspace = Path(args.workspace)

    if args.snapshot:
        print(json.dumps(
            product_snapshot(repo_root, workspace),
            indent=2,
            sort_keys=True,
        ))
        return 0
    if args.execute_job:
        if not args.runner:
            parser.error("--runner is required with --execute-job.")
        payload = execute_job(
            repo_root,
            workspace,
            Path(args.execute_job),
            Path(args.runner),
        )
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if payload["status"] == "PASS" else 1

    parser.error(
        "Use --snapshot, --execute-job, --normalize-output "
        "or --guard-check."
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
