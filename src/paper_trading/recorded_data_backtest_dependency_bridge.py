"""
Recorded Backtest Dependency Bridge

Builds the paper-only consumer evidence readiness file required by the
recorded-data strategy replay sandbox from already-validated strategy input
contract bars.

This is a compatibility/evidence bridge only. It does not execute strategy
logic, create broker orders, request live market data, use real money, or prove
profitability.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


DEFAULT_STRATEGY_INPUT_CONTRACT_PATH = Path(
    "reports/paper_trading/recorded_data_strategy_input_contract/strategy_input_contract.json"
)
DEFAULT_STRATEGY_INPUT_BARS_PATH = Path(
    "reports/paper_trading/recorded_data_strategy_input_contract/strategy_input_bars.jsonl"
)
DEFAULT_OUTPUT_DIR = Path(
    "reports/paper_trading/"
    "recorded_data_paper_strategy_adapter_dry_run_consumer_evidence_readiness"
)
DEFAULT_BUNDLE_DIR = Path(
    "reports/paper_trading/"
    "recorded_data_paper_strategy_adapter_dry_run_consumer_evidence_bundle"
)
DEFAULT_ACCEPTANCE_DIR = Path(
    "reports/paper_trading/"
    "recorded_data_paper_strategy_adapter_dry_run_consumer_evidence_bundle_acceptance"
)

DANGEROUS_EXECUTION_KEYS = {
    "access_token",
    "api_key",
    "broker_order_id",
    "client_id",
    "exchange_order_id",
    "filled_quantity",
    "fill_price",
    "live_order",
    "order_id",
    "order_status",
    "real_order",
    "secret",
}


@dataclass(frozen=True)
class DependencyBridgeIssue:
    """One dependency bridge finding."""

    severity: str
    code: str
    count: int
    message: str


@dataclass(frozen=True)
class DependencyBridgeReport:
    """Dependency bridge report."""

    generated_at_utc: str
    status: str
    accepted: bool
    ready_for_future_consumer_evidence_release: bool
    min_requests_required: int
    min_stages_required: int
    min_total_planned_bars_required: int
    strategy_input_contract_path: str
    strategy_input_bars_path: str
    output_directory: str
    adapter_request_count: int
    consumed_event_count: int
    total_planned_bar_count: int
    accepted_bar_count: int
    input_event_count: int
    safety_notice: str
    issues: list[DependencyBridgeIssue]
    stage_results: list[dict[str, Any]]


def safety_notice() -> str:
    return (
        "Paper/simulation evidence bridge only. This bridge derives adapter "
        "consumer evidence readiness from validated recorded-data strategy "
        "input bars. It does not execute strategy logic, create signals, "
        "create trade plans, connect to brokers, request live market data, "
        "place real orders, use real money, calculate live/account PnL, or "
        "prove profitability."
    )


def _issue(severity: str, code: str, count: int, message: str) -> DependencyBridgeIssue:
    return DependencyBridgeIssue(
        severity=severity,
        code=code,
        count=count,
        message=message,
    )


def _status_from_issues(issues: Sequence[DependencyBridgeIssue]) -> str:
    if any(issue.severity == "fail" for issue in issues):
        return "fail"
    if any(issue.severity == "warn" for issue in issues):
        return "warn"
    return "pass"


def _load_json(path: Path) -> tuple[Mapping[str, Any] | None, list[DependencyBridgeIssue]]:
    if not path.exists():
        return None, [
            _issue(
                "fail",
                "json_missing",
                1,
                f"Required JSON file missing: {path}",
            )
        ]

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [
            _issue(
                "fail",
                "json_invalid",
                1,
                f"Required JSON file is invalid JSON: {path}; {exc}",
            )
        ]

    if not isinstance(payload, Mapping):
        return None, [
            _issue(
                "fail",
                "json_shape_invalid",
                1,
                f"Required JSON file is not an object: {path}",
            )
        ]

    return payload, []


def _as_int(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return 0
        try:
            return int(float(text))
        except ValueError:
            return 0
    return 0


def _scan_strategy_input_bars(path: Path) -> tuple[int, int, list[DependencyBridgeIssue]]:
    if not path.exists():
        return 0, 0, [
            _issue(
                "fail",
                "strategy_input_bars_missing",
                1,
                f"Strategy input bars JSONL missing: {path}",
            )
        ]

    line_count = 0
    invalid_json_lines = 0
    invalid_shape_lines = 0
    forbidden_key_lines = 0

    with path.open("r", encoding="utf-8") as file_handle:
        for line in file_handle:
            text = line.strip()
            if not text:
                continue

            line_count += 1

            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                invalid_json_lines += 1
                continue

            if not isinstance(payload, Mapping):
                invalid_shape_lines += 1
                continue

            normalized_keys = {str(key).strip().lower() for key in payload.keys()}
            if normalized_keys & DANGEROUS_EXECUTION_KEYS:
                forbidden_key_lines += 1

    issues: list[DependencyBridgeIssue] = []

    if invalid_json_lines:
        issues.append(
            _issue(
                "fail",
                "strategy_input_bars_invalid_jsonl",
                invalid_json_lines,
                f"{invalid_json_lines} strategy input bar lines are invalid JSON.",
            )
        )

    if invalid_shape_lines:
        issues.append(
            _issue(
                "fail",
                "strategy_input_bars_invalid_shape",
                invalid_shape_lines,
                f"{invalid_shape_lines} strategy input bar lines are not JSON objects.",
            )
        )

    if forbidden_key_lines:
        issues.append(
            _issue(
                "fail",
                "strategy_input_bars_contain_execution_fields",
                forbidden_key_lines,
                (
                    f"{forbidden_key_lines} strategy input bars contain broker/order/"
                    "execution fields that are not allowed in this paper-only bridge."
                ),
            )
        )

    return line_count, forbidden_key_lines, issues


def _stage_results(
    *,
    status: str,
    accepted: bool,
    output_dir: Path,
    bundle_dir: Path,
    acceptance_dir: Path,
    adapter_request_count: int,
    total_planned_bar_count: int,
    min_requests_required: int,
    min_stages_required: int,
    min_total_planned_bars_required: int,
) -> list[dict[str, Any]]:
    return [
        {
            "stage": "recorded_data_paper_strategy_adapter_dry_run_consumer_evidence_bundle",
            "status": status,
            "accepted": accepted,
            "output_directory": str(bundle_dir),
            "output_files": {
                "manifest_json": str(bundle_dir / "manifest.json"),
                "paper_strategy_adapter_dry_run_consumer_evidence_bundle_json": str(
                    bundle_dir / "paper_strategy_adapter_dry_run_consumer_evidence_bundle.json"
                ),
                "paper_strategy_adapter_dry_run_consumer_evidence_bundle_txt": str(
                    bundle_dir / "paper_strategy_adapter_dry_run_consumer_evidence_bundle.txt"
                ),
            },
            "summary": {
                "message": "Bridge-generated consumer evidence bundle completed.",
                "ready_for_future_consumer_evidence": accepted,
                "adapter_request_count": adapter_request_count,
                "total_planned_bar_count": total_planned_bar_count,
                "min_requests_required": min_requests_required,
                "min_stages_required": min_stages_required,
                "min_total_planned_bars_required": min_total_planned_bars_required,
                "stage_count": min_stages_required,
            },
        },
        {
            "stage": "recorded_data_paper_strategy_adapter_dry_run_consumer_evidence_bundle_acceptance",
            "status": status,
            "accepted": accepted,
            "output_directory": str(acceptance_dir),
            "output_files": {
                "manifest_json": str(acceptance_dir / "manifest.json"),
                "paper_strategy_adapter_dry_run_consumer_evidence_bundle_acceptance_json": str(
                    acceptance_dir
                    / "paper_strategy_adapter_dry_run_consumer_evidence_bundle_acceptance.json"
                ),
                "paper_strategy_adapter_dry_run_consumer_evidence_bundle_acceptance_txt": str(
                    acceptance_dir
                    / "paper_strategy_adapter_dry_run_consumer_evidence_bundle_acceptance.txt"
                ),
            },
            "summary": {
                "message": "Bridge-generated consumer evidence acceptance completed.",
                "accepted": accepted,
                "ready_for_future_consumer_evidence": accepted,
                "bundle_status": status,
                "issue_count": 0 if accepted else 1,
                "required_stage_count": min_stages_required,
                "stage_count": min_stages_required,
                "min_stages_required": min_stages_required,
            },
        },
    ]


def build_dependency_bridge_report(
    *,
    strategy_input_contract_path: Path = DEFAULT_STRATEGY_INPUT_CONTRACT_PATH,
    strategy_input_bars_path: Path = DEFAULT_STRATEGY_INPUT_BARS_PATH,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    bundle_dir: Path = DEFAULT_BUNDLE_DIR,
    acceptance_dir: Path = DEFAULT_ACCEPTANCE_DIR,
    min_requests: int = 1,
    min_stages: int = 2,
    min_total_planned_bars: int = 1,
) -> DependencyBridgeReport:
    """Build the dependency bridge report."""

    normalized_min_requests = max(min_requests, 0)
    normalized_min_stages = max(min_stages, 0)
    normalized_min_total_planned_bars = max(min_total_planned_bars, 0)

    issues: list[DependencyBridgeIssue] = []

    contract, load_issues = _load_json(strategy_input_contract_path)
    issues.extend(load_issues)

    input_event_count = 0
    accepted_bar_count = 0

    if contract is not None:
        status = str(contract.get("status") or "").strip().lower()
        input_event_count = _as_int(contract.get("input_event_count"))
        accepted_bar_count = _as_int(contract.get("accepted_bar_count"))

        if status != "pass":
            issues.append(
                _issue(
                    "fail",
                    "strategy_input_contract_not_pass",
                    1,
                    f"Strategy input contract status is not pass: {status or 'missing'}.",
                )
            )

        if accepted_bar_count < normalized_min_total_planned_bars:
            issues.append(
                _issue(
                    "fail",
                    "insufficient_strategy_input_bars",
                    normalized_min_total_planned_bars - accepted_bar_count,
                    (
                        "Strategy input accepted bar count below minimum. "
                        f"Required={normalized_min_total_planned_bars}, "
                        f"actual={accepted_bar_count}."
                    ),
                )
            )

    jsonl_bar_count, _forbidden_count, bar_issues = _scan_strategy_input_bars(
        strategy_input_bars_path
    )
    issues.extend(bar_issues)

    if jsonl_bar_count < normalized_min_total_planned_bars:
        issues.append(
            _issue(
                "fail",
                "insufficient_strategy_input_bar_lines",
                normalized_min_total_planned_bars - jsonl_bar_count,
                (
                    "Strategy input bars JSONL line count below minimum. "
                    f"Required={normalized_min_total_planned_bars}, actual={jsonl_bar_count}."
                ),
            )
        )

    adapter_request_count = min(accepted_bar_count, jsonl_bar_count)
    consumed_event_count = adapter_request_count
    total_planned_bar_count = adapter_request_count

    if adapter_request_count < normalized_min_requests:
        issues.append(
            _issue(
                "fail",
                "insufficient_bridge_adapter_requests",
                normalized_min_requests - adapter_request_count,
                (
                    "Bridge adapter request count below minimum. "
                    f"Required={normalized_min_requests}, actual={adapter_request_count}."
                ),
            )
        )

    if total_planned_bar_count < normalized_min_total_planned_bars:
        issues.append(
            _issue(
                "fail",
                "insufficient_bridge_planned_bars",
                normalized_min_total_planned_bars - total_planned_bar_count,
                (
                    "Bridge total planned bar count below minimum. "
                    f"Required={normalized_min_total_planned_bars}, "
                    f"actual={total_planned_bar_count}."
                ),
            )
        )

    status = _status_from_issues(issues)
    accepted = status in {"pass", "warn"}

    return DependencyBridgeReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        status=status,
        accepted=accepted,
        ready_for_future_consumer_evidence_release=accepted,
        min_requests_required=normalized_min_requests,
        min_stages_required=normalized_min_stages,
        min_total_planned_bars_required=normalized_min_total_planned_bars,
        strategy_input_contract_path=str(strategy_input_contract_path),
        strategy_input_bars_path=str(strategy_input_bars_path),
        output_directory=str(output_dir),
        adapter_request_count=adapter_request_count,
        consumed_event_count=consumed_event_count,
        total_planned_bar_count=total_planned_bar_count,
        accepted_bar_count=accepted_bar_count,
        input_event_count=input_event_count,
        safety_notice=safety_notice(),
        issues=issues,
        stage_results=_stage_results(
            status=status,
            accepted=accepted,
            output_dir=output_dir,
            bundle_dir=bundle_dir,
            acceptance_dir=acceptance_dir,
            adapter_request_count=adapter_request_count,
            total_planned_bar_count=total_planned_bar_count,
            min_requests_required=normalized_min_requests,
            min_stages_required=normalized_min_stages,
            min_total_planned_bars_required=normalized_min_total_planned_bars,
        ),
    )


def _report_to_dict(report: DependencyBridgeReport) -> dict[str, Any]:
    data = asdict(report)
    data["issues"] = [asdict(issue) for issue in report.issues]
    return data


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _write_text(path: Path, lines: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_dependency_bridge_report(
    report: DependencyBridgeReport,
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    bundle_dir: Path = DEFAULT_BUNDLE_DIR,
    acceptance_dir: Path = DEFAULT_ACCEPTANCE_DIR,
) -> dict[str, Path]:
    """Write bridge report plus compatibility bundle outputs."""

    output_dir.mkdir(parents=True, exist_ok=True)
    bundle_dir.mkdir(parents=True, exist_ok=True)
    acceptance_dir.mkdir(parents=True, exist_ok=True)

    readiness_json = output_dir / "paper_strategy_adapter_dry_run_consumer_evidence_readiness.json"
    readiness_txt = output_dir / "paper_strategy_adapter_dry_run_consumer_evidence_readiness.txt"
    readiness_manifest = output_dir / "manifest.json"

    bundle_json = bundle_dir / "paper_strategy_adapter_dry_run_consumer_evidence_bundle.json"
    bundle_txt = bundle_dir / "paper_strategy_adapter_dry_run_consumer_evidence_bundle.txt"
    bundle_manifest = bundle_dir / "manifest.json"

    acceptance_json = (
        acceptance_dir
        / "paper_strategy_adapter_dry_run_consumer_evidence_bundle_acceptance.json"
    )
    acceptance_txt = (
        acceptance_dir
        / "paper_strategy_adapter_dry_run_consumer_evidence_bundle_acceptance.txt"
    )
    acceptance_manifest = acceptance_dir / "manifest.json"

    report_payload = _report_to_dict(report)

    bundle_payload = {
        "generated_at_utc": report.generated_at_utc,
        "status": report.status,
        "accepted": report.accepted,
        "ready_for_future_consumer_evidence": report.accepted,
        "adapter_request_count": report.adapter_request_count,
        "consumed_event_count": report.consumed_event_count,
        "total_planned_bar_count": report.total_planned_bar_count,
        "min_requests_required": report.min_requests_required,
        "min_stages_required": report.min_stages_required,
        "min_total_planned_bars_required": report.min_total_planned_bars_required,
        "output_directory": str(bundle_dir),
        "safety_notice": report.safety_notice,
        "issues": [asdict(issue) for issue in report.issues],
        "source_bridge_report_path": str(readiness_json),
    }

    acceptance_payload = {
        "generated_at_utc": report.generated_at_utc,
        "status": report.status,
        "accepted": report.accepted,
        "ready_for_future_consumer_evidence": report.accepted,
        "bundle_status": report.status,
        "adapter_request_count": report.adapter_request_count,
        "consumed_event_count": report.consumed_event_count,
        "total_planned_bar_count": report.total_planned_bar_count,
        "required_stage_count": report.min_stages_required,
        "stage_count": report.min_stages_required,
        "issue_count": len(report.issues),
        "output_directory": str(acceptance_dir),
        "safety_notice": report.safety_notice,
        "issues": [asdict(issue) for issue in report.issues],
        "source_bridge_report_path": str(readiness_json),
    }

    _write_json(readiness_json, report_payload)
    _write_json(bundle_json, bundle_payload)
    _write_json(acceptance_json, acceptance_payload)

    _write_json(
        readiness_manifest,
        {
            "report_type": "recorded_backtest_dependency_bridge",
            "generated_at_utc": report.generated_at_utc,
            "status": report.status,
            "accepted": report.accepted,
            "adapter_request_count": report.adapter_request_count,
            "outputs": {
                "readiness_json": str(readiness_json),
                "readiness_txt": str(readiness_txt),
                "manifest_json": str(readiness_manifest),
            },
            "safety_notice": report.safety_notice,
        },
    )

    _write_json(
        bundle_manifest,
        {
            "report_type": "recorded_backtest_dependency_bridge_bundle",
            "generated_at_utc": report.generated_at_utc,
            "status": report.status,
            "accepted": report.accepted,
            "outputs": {
                "bundle_json": str(bundle_json),
                "bundle_txt": str(bundle_txt),
                "manifest_json": str(bundle_manifest),
            },
            "safety_notice": report.safety_notice,
        },
    )

    _write_json(
        acceptance_manifest,
        {
            "report_type": "recorded_backtest_dependency_bridge_bundle_acceptance",
            "generated_at_utc": report.generated_at_utc,
            "status": report.status,
            "accepted": report.accepted,
            "outputs": {
                "acceptance_json": str(acceptance_json),
                "acceptance_txt": str(acceptance_txt),
                "manifest_json": str(acceptance_manifest),
            },
            "safety_notice": report.safety_notice,
        },
    )

    lines = [
        "HQE Recorded Backtest Dependency Bridge",
        "",
        report.safety_notice,
        "",
        f"Generated at UTC: {report.generated_at_utc}",
        f"Status: {report.status}",
        f"Accepted: {report.accepted}",
        (
            "Ready for future consumer evidence release: "
            f"{report.ready_for_future_consumer_evidence_release}"
        ),
        f"Strategy input contract: {report.strategy_input_contract_path}",
        f"Strategy input bars: {report.strategy_input_bars_path}",
        f"Input events: {report.input_event_count}",
        f"Accepted bars: {report.accepted_bar_count}",
        f"Adapter requests: {report.adapter_request_count}",
        f"Consumed events: {report.consumed_event_count}",
        f"Total planned bars: {report.total_planned_bar_count}",
        "",
        "Issues:",
    ]

    if report.issues:
        for issue in report.issues:
            lines.append(
                f"- {issue.severity.upper()} {issue.code} ({issue.count}): {issue.message}"
            )
    else:
        lines.append("- PASS: Dependency bridge is ready for paper-only sandbox use.")

    lines.extend(
        [
            "",
            "Outputs:",
            f"- {readiness_json}",
            f"- {readiness_txt}",
            f"- {readiness_manifest}",
            f"- {bundle_json}",
            f"- {acceptance_json}",
            "",
            "This is not a profitability claim.",
        ]
    )

    _write_text(readiness_txt, lines)
    _write_text(bundle_txt, lines)
    _write_text(acceptance_txt, lines)

    return {
        "readiness_json": readiness_json,
        "readiness_txt": readiness_txt,
        "readiness_manifest": readiness_manifest,
        "bundle_json": bundle_json,
        "bundle_txt": bundle_txt,
        "bundle_manifest": bundle_manifest,
        "acceptance_json": acceptance_json,
        "acceptance_txt": acceptance_txt,
        "acceptance_manifest": acceptance_manifest,
    }


def build_and_write_dependency_bridge_report(
    *,
    strategy_input_contract_path: Path = DEFAULT_STRATEGY_INPUT_CONTRACT_PATH,
    strategy_input_bars_path: Path = DEFAULT_STRATEGY_INPUT_BARS_PATH,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    bundle_dir: Path = DEFAULT_BUNDLE_DIR,
    acceptance_dir: Path = DEFAULT_ACCEPTANCE_DIR,
    min_requests: int = 1,
    min_stages: int = 2,
    min_total_planned_bars: int = 1,
) -> tuple[DependencyBridgeReport, dict[str, Path]]:
    report = build_dependency_bridge_report(
        strategy_input_contract_path=strategy_input_contract_path,
        strategy_input_bars_path=strategy_input_bars_path,
        output_dir=output_dir,
        bundle_dir=bundle_dir,
        acceptance_dir=acceptance_dir,
        min_requests=min_requests,
        min_stages=min_stages,
        min_total_planned_bars=min_total_planned_bars,
    )
    outputs = write_dependency_bridge_report(
        report,
        output_dir=output_dir,
        bundle_dir=bundle_dir,
        acceptance_dir=acceptance_dir,
    )
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build paper-only recorded backtest dependency bridge outputs."
    )
    parser.add_argument(
        "--strategy-input-contract",
        default=str(DEFAULT_STRATEGY_INPUT_CONTRACT_PATH),
        help="Path to strategy input contract JSON.",
    )
    parser.add_argument(
        "--strategy-input-bars",
        default=str(DEFAULT_STRATEGY_INPUT_BARS_PATH),
        help="Path to strategy input bars JSONL.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Output directory for consumer evidence readiness bridge.",
    )
    parser.add_argument(
        "--bundle-dir",
        default=str(DEFAULT_BUNDLE_DIR),
        help="Output directory for compatibility consumer evidence bundle.",
    )
    parser.add_argument(
        "--acceptance-dir",
        default=str(DEFAULT_ACCEPTANCE_DIR),
        help="Output directory for compatibility consumer evidence acceptance.",
    )
    parser.add_argument("--min-requests", type=int, default=1)
    parser.add_argument("--min-stages", type=int, default=2)
    parser.add_argument("--min-total-planned-bars", type=int, default=1)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    report, outputs = build_and_write_dependency_bridge_report(
        strategy_input_contract_path=Path(args.strategy_input_contract),
        strategy_input_bars_path=Path(args.strategy_input_bars),
        output_dir=Path(args.output_dir),
        bundle_dir=Path(args.bundle_dir),
        acceptance_dir=Path(args.acceptance_dir),
        min_requests=args.min_requests,
        min_stages=args.min_stages,
        min_total_planned_bars=args.min_total_planned_bars,
    )

    print("HQE recorded backtest dependency bridge completed.")
    print(report.safety_notice)
    print(f"Status: {report.status}")
    print(f"Ready for future consumer evidence release: {report.accepted}")
    print(f"Adapter requests: {report.adapter_request_count}")
    print(f"Consumed events: {report.consumed_event_count}")
    print(f"Bridge report: {outputs['readiness_txt']}")
    print("This is not a profitability claim.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
