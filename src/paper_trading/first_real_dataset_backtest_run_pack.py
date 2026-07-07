"""
First real dataset backtest run pack.

Module MMM in the post-v1.0 Real Backtest Usage Sprint.

This module reads the real dataset backtest input pack and creates an
operator-safe first-run pack for recorded-data paper backtesting.

It does not connect to brokers, request live market data, place real orders,
use real money, or prove profitability.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


FORBIDDEN_KEYS = {
    "broker",
    "broker_order_id",
    "exchange_order_id",
    "live_order",
    "order",
    "order_id",
    "orders",
    "real_money",
}


@dataclass(frozen=True)
class FirstBacktestRunCommand:
    step_index: int
    command: str
    purpose: str
    expected_output: str


@dataclass(frozen=True)
class FirstBacktestRunIssue:
    severity: str
    code: str
    count: int
    message: str


@dataclass(frozen=True)
class FirstBacktestRunPackReport:
    generated_at_utc: str
    input_pack_path: str
    output_directory: str
    status: str
    ready_for_operator_first_real_backtest_run: bool
    selected_dataset_path: str
    discovered_file_count: int
    safety_notice: str
    command_count: int
    expected_output_count: int
    issues: list[FirstBacktestRunIssue]
    commands: list[FirstBacktestRunCommand]
    expected_outputs: list[str]


def safety_notice() -> str:
    return (
        "Paper/simulation first real dataset backtest run pack only. This pack "
        "turns saved recorded-data discovery into an operator run order. It "
        "does not connect to brokers, request live market data, place real "
        "orders, use real money, or prove profitability."
    )


def _issue(
    severity: str,
    code: str,
    count: int,
    message: str,
) -> FirstBacktestRunIssue:
    return FirstBacktestRunIssue(
        severity=severity,
        code=code,
        count=count,
        message=message,
    )


def _status(issues: Sequence[FirstBacktestRunIssue]) -> str:
    if any(issue.severity == "fail" for issue in issues):
        return "fail"
    if any(issue.severity == "warn" for issue in issues):
        return "warn"
    return "pass"


def _to_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    text = str(value).strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _forbidden(payload: Mapping[str, Any]) -> set[str]:
    return {
        str(key)
        for key in payload.keys()
        if str(key).strip().lower() in FORBIDDEN_KEYS
    }


def _load_input_pack(
    path: Path,
) -> tuple[Mapping[str, Any] | None, list[FirstBacktestRunIssue]]:
    if not path.exists():
        return None, [
            _issue(
                "fail",
                "real_dataset_input_pack_missing",
                1,
                f"Real dataset input pack missing: {path}",
            )
        ]

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [
            _issue(
                "fail",
                "real_dataset_input_pack_invalid_json",
                1,
                f"Real dataset input pack JSON parse failed: {exc}",
            )
        ]

    if not isinstance(payload, Mapping):
        return None, [
            _issue(
                "fail",
                "real_dataset_input_pack_invalid_shape",
                1,
                "Real dataset input pack must be a JSON object.",
            )
        ]

    return payload, []


def _input_pack_issues(
    pack: Mapping[str, Any] | None,
    *,
    min_files: int,
    allow_warnings: bool,
    require_selected_dataset_exists: bool,
) -> list[FirstBacktestRunIssue]:
    if pack is None:
        return []

    issues: list[FirstBacktestRunIssue] = []

    status = str(pack.get("status") or "unknown").lower()
    ready = bool(pack.get("ready_for_future_first_real_backtest_run"))
    selected_dataset_path = str(pack.get("selected_dataset_path") or "").strip()
    discovered_file_count = _to_int(pack.get("discovered_file_count")) or 0

    if status == "warn":
        issues.append(
            _issue(
                "warn" if allow_warnings else "fail",
                "real_dataset_input_pack_warn",
                1,
                "Real dataset input pack status is warn.",
            )
        )
    elif status != "pass":
        issues.append(
            _issue(
                "fail",
                "real_dataset_input_pack_not_pass",
                1,
                f"Real dataset input pack status is not pass: {status}.",
            )
        )

    if not ready:
        issues.append(
            _issue(
                "fail",
                "real_dataset_input_pack_not_ready",
                1,
                "Real dataset input pack is not ready for first real backtest run.",
            )
        )

    if discovered_file_count < min_files:
        issues.append(
            _issue(
                "fail",
                "insufficient_discovered_dataset_files",
                max(min_files - discovered_file_count, 0),
                (
                    "Discovered dataset file count below minimum. "
                    f"Required={min_files}, actual={discovered_file_count}."
                ),
            )
        )

    if not selected_dataset_path:
        issues.append(
            _issue(
                "fail",
                "selected_dataset_path_missing",
                1,
                "Real dataset input pack must include selected_dataset_path.",
            )
        )
    elif require_selected_dataset_exists and not Path(selected_dataset_path).exists():
        issues.append(
            _issue(
                "fail",
                "selected_dataset_missing_on_disk",
                1,
                f"Selected dataset file does not exist on disk: {selected_dataset_path}",
            )
        )

    forbidden = _forbidden(pack)
    if forbidden:
        issues.append(
            _issue(
                "fail",
                "real_dataset_input_pack_forbidden_fields",
                len(forbidden),
                "Real dataset input pack contains forbidden broker/order/real-money fields.",
            )
        )

    pack_issues = pack.get("issues")
    if isinstance(pack_issues, list):
        fail_count = sum(
            1
            for item in pack_issues
            if isinstance(item, Mapping) and str(item.get("severity") or "") == "fail"
        )
        if fail_count:
            issues.append(
                _issue(
                    "fail",
                    "real_dataset_input_pack_contains_fail_issues",
                    fail_count,
                    "Real dataset input pack contains fail issues.",
                )
            )

    return issues


def _commands(selected_dataset_path: str) -> list[FirstBacktestRunCommand]:
    return [
        FirstBacktestRunCommand(
            1,
            ".\\hqe_real_dataset_backtest_input_pack.bat",
            "Confirm saved recorded dataset discovery.",
            "real_dataset_backtest_input_pack.json",
        ),
        FirstBacktestRunCommand(
            2,
            ".\\hqe_recorded_data_inventory.bat",
            "Inventory recorded dataset files.",
            "inventory.json",
        ),
        FirstBacktestRunCommand(
            3,
            ".\\hqe_recorded_data_replay_dataset.bat",
            "Normalize recorded dataset into replay bars.",
            "dataset.json and dataset.jsonl",
        ),
        FirstBacktestRunCommand(
            4,
            ".\\hqe_recorded_data_replay_quality_gate.bat",
            "Validate replay dataset quality before strategy replay.",
            "quality_gate.json",
        ),
        FirstBacktestRunCommand(
            5,
            ".\\hqe_recorded_data_backtest_readiness_gate.bat",
            "Run paper-only recorded-data backtest readiness chain.",
            "backtest_readiness_gate.json",
        ),
        FirstBacktestRunCommand(
            6,
            ".\\hqe_v1_testing_release_gate.bat",
            "Validate v1 testing release gate evidence after first run.",
            "v1_testing_release_gate.json",
        ),
        FirstBacktestRunCommand(
            7,
            ".\\hqe_v1_testing_operator_handoff_pack.bat",
            "Create operator handoff pack for reviewing first run outputs.",
            "v1_testing_operator_handoff_pack.json",
        ),
        FirstBacktestRunCommand(
            8,
            f"Selected dataset reference: {selected_dataset_path or '<missing>'}",
            "Keep selected dataset visible for operator review.",
            "Operator confirms dataset path.",
        ),
    ]


def _expected_outputs() -> list[str]:
    return [
        "reports/paper_trading/recorded_data_inventory/inventory.json",
        "reports/paper_trading/recorded_data_replay_dataset/dataset.json",
        "reports/paper_trading/recorded_data_replay_quality_gate/quality_gate.json",
        "reports/paper_trading/recorded_data_backtest_trade_ledger/backtest_trade_ledger.json",
        "reports/paper_trading/recorded_data_backtest_metrics_engine/backtest_metrics.json",
        "reports/paper_trading/recorded_data_backtest_report_writer/backtest_report.json",
        "reports/paper_trading/recorded_data_backtest_readiness_gate/backtest_readiness_gate.json",
        "reports/paper_trading/v1_testing_release_gate/v1_testing_release_gate.json",
        "reports/paper_trading/v1_testing_operator_handoff_pack/v1_testing_operator_handoff_pack.json",
    ]


def build_first_backtest_run_pack_report(
    *,
    input_pack_path: Path,
    output_dir: Path,
    min_files: int = 1,
    allow_warnings: bool = False,
    require_selected_dataset_exists: bool = True,
) -> FirstBacktestRunPackReport:
    min_files = max(min_files, 0)

    pack, load_issues = _load_input_pack(input_pack_path)
    issues: list[FirstBacktestRunIssue] = []
    issues.extend(load_issues)
    issues.extend(
        _input_pack_issues(
            pack,
            min_files=min_files,
            allow_warnings=allow_warnings,
            require_selected_dataset_exists=require_selected_dataset_exists,
        )
    )

    selected_dataset_path = str((pack or {}).get("selected_dataset_path") or "")
    discovered_file_count = _to_int((pack or {}).get("discovered_file_count")) or 0
    commands = _commands(selected_dataset_path)
    expected_outputs = _expected_outputs()
    status = _status(issues)

    return FirstBacktestRunPackReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        input_pack_path=str(input_pack_path),
        output_directory=str(output_dir),
        status=status,
        ready_for_operator_first_real_backtest_run=status in {"pass", "warn"},
        selected_dataset_path=selected_dataset_path,
        discovered_file_count=discovered_file_count,
        safety_notice=safety_notice(),
        command_count=len(commands),
        expected_output_count=len(expected_outputs),
        issues=issues,
        commands=commands,
        expected_outputs=expected_outputs,
    )


def write_first_backtest_run_pack_report(
    report: FirstBacktestRunPackReport,
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    pack_json = output_dir / "first_real_dataset_backtest_run_pack.json"
    pack_txt = output_dir / "first_real_dataset_backtest_run_pack.txt"
    commands_bat = output_dir / "first_real_dataset_backtest_run_commands.bat"
    expected_outputs_json = output_dir / "first_real_dataset_backtest_expected_outputs.json"
    manifest_json = output_dir / "manifest.json"

    data = asdict(report)
    data["issues"] = [asdict(issue) for issue in report.issues]
    data["commands"] = [asdict(command) for command in report.commands]
    pack_json.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

    expected_outputs_json.write_text(
        json.dumps(
            {
                "expected_output_count": report.expected_output_count,
                "expected_outputs": report.expected_outputs,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    bat_lines = [
        "@echo off",
        "setlocal",
        "echo HQE first real dataset paper backtest run",
        "echo Paper/simulation only. No broker orders. No real money.",
        "echo.",
    ]
    for command in report.commands:
        if command.command.startswith("Selected dataset reference:"):
            bat_lines.append(f"echo {command.command}")
        else:
            bat_lines.append(command.command)
            bat_lines.append("if %ERRORLEVEL% neq 0 exit /b %ERRORLEVEL%")
    commands_bat.write_text("\n".join(bat_lines) + "\n", encoding="utf-8")

    lines = [
        "HQE First Real Dataset Backtest Run Pack",
        "",
        report.safety_notice,
        "",
        f"Status: {report.status}",
        f"Ready for operator first real backtest run: {report.ready_for_operator_first_real_backtest_run}",
        f"Selected dataset path: {report.selected_dataset_path}",
        f"Discovered file count: {report.discovered_file_count}",
        "",
        "Run order:",
    ]

    for command in report.commands:
        lines.append(
            f"{command.step_index}. {command.command} -> {command.purpose} Expected: {command.expected_output}"
        )

    lines.extend(["", "Expected outputs after run:"])
    for output in report.expected_outputs:
        lines.append(f"- {output}")

    lines.extend(
        [
            "",
            "Safety:",
            "- LONG = CE BUY paper plan only.",
            "- SHORT = PE BUY paper plan only.",
            "- NEUTRAL = no trade.",
            "- No option selling.",
            "- No broker orders.",
            "- No live market data.",
            "- No real money.",
            "- This report is not a profitability claim.",
            "",
            "Issues:",
        ]
    )

    if not report.issues:
        lines.append("- PASS: First real dataset backtest run pack is ready for operator use.")
    else:
        for issue in report.issues:
            lines.append(
                f"- {issue.severity.upper()} {issue.code}: {issue.message} Count={issue.count}"
            )

    lines.extend(
        [
            "",
            "Outputs:",
            f"- {pack_json}",
            f"- {pack_txt}",
            f"- {commands_bat}",
            f"- {expected_outputs_json}",
            f"- {manifest_json}",
        ]
    )
    pack_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "report_type": "first_real_dataset_backtest_run_pack",
        "generated_at_utc": report.generated_at_utc,
        "status": report.status,
        "ready_for_operator_first_real_backtest_run": report.ready_for_operator_first_real_backtest_run,
        "selected_dataset_path": report.selected_dataset_path,
        "discovered_file_count": report.discovered_file_count,
        "command_count": report.command_count,
        "expected_output_count": report.expected_output_count,
        "safety_notice": report.safety_notice,
        "outputs": {
            "first_real_dataset_backtest_run_pack_json": str(pack_json),
            "first_real_dataset_backtest_run_pack_txt": str(pack_txt),
            "first_real_dataset_backtest_run_commands_bat": str(commands_bat),
            "first_real_dataset_backtest_expected_outputs_json": str(expected_outputs_json),
            "manifest_json": str(manifest_json),
        },
    }
    manifest_json.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    return {
        "first_real_dataset_backtest_run_pack_json": pack_json,
        "first_real_dataset_backtest_run_pack_txt": pack_txt,
        "first_real_dataset_backtest_run_commands_bat": commands_bat,
        "first_real_dataset_backtest_expected_outputs_json": expected_outputs_json,
        "manifest_json": manifest_json,
    }


def build_and_write_first_backtest_run_pack_report(
    *,
    input_pack_path: Path,
    output_dir: Path,
    min_files: int = 1,
    allow_warnings: bool = False,
    require_selected_dataset_exists: bool = True,
) -> tuple[FirstBacktestRunPackReport, dict[str, Path]]:
    report = build_first_backtest_run_pack_report(
        input_pack_path=input_pack_path,
        output_dir=output_dir,
        min_files=min_files,
        allow_warnings=allow_warnings,
        require_selected_dataset_exists=require_selected_dataset_exists,
    )
    outputs = write_first_backtest_run_pack_report(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build first real dataset paper backtest run pack."
    )
    parser.add_argument(
        "--input-pack",
        default=(
            "reports/paper_trading/"
            "real_dataset_backtest_input_pack/"
            "real_dataset_backtest_input_pack.json"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default="reports/paper_trading/first_real_dataset_backtest_run_pack",
    )
    parser.add_argument("--min-files", type=int, default=1)
    parser.add_argument("--allow-warnings", action="store_true")
    parser.add_argument("--skip-selected-dataset-existence-check", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    report, outputs = build_and_write_first_backtest_run_pack_report(
        input_pack_path=Path(args.input_pack),
        output_dir=Path(args.output_dir),
        min_files=args.min_files,
        allow_warnings=args.allow_warnings,
        require_selected_dataset_exists=not args.skip_selected_dataset_existence_check,
    )

    print("HQE first real dataset backtest run pack completed.")
    print(report.safety_notice)
    print(f"Status: {report.status}")
    print(f"Ready for operator first real backtest run: {report.ready_for_operator_first_real_backtest_run}")
    print(f"Selected dataset path: {report.selected_dataset_path}")
    print(f"Run pack: {outputs['first_real_dataset_backtest_run_pack_txt']}")
    print("This is not a profitability claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
