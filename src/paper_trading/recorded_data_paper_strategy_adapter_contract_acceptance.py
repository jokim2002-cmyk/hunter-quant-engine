"""
Recorded data paper strategy adapter contract acceptance gate.

Evidence-only gate for adapter request manifests created by the paper strategy
adapter contract. It confirms the contract is structurally acceptable for a
future paper/simulation adapter dry-run phase.

This module never executes strategy logic, creates signals, creates trade plans,
connects to brokers, requests live market data, places orders, uses real money,
calculates PnL, or proves profitability.
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
    "order",
    "order_id",
    "orders",
    "pnl",
    "profit",
    "profit_loss",
    "signal",
    "signals",
    "trade",
    "trade_plan",
    "trades",
}


@dataclass(frozen=True)
class AdapterContractAcceptanceIssue:
    severity: str
    code: str
    count: int
    message: str


@dataclass(frozen=True)
class AdapterContractAcceptanceReport:
    generated_at_utc: str
    adapter_contract_path: str
    output_directory: str
    status: str
    accepted: bool
    allow_warnings: bool
    min_requests_required: int
    min_total_planned_bars_required: int
    contract_status: str
    ready_for_future_adapter: bool
    request_count: int
    total_planned_bars: int
    safety_notice: str
    issues: list[AdapterContractAcceptanceIssue]


def safety_notice() -> str:
    return (
        "Paper/simulation evidence only. This adapter contract acceptance gate "
        "does not execute strategy logic, create signals, create trade plans, "
        "connect to brokers, request live market data, place real orders, use "
        "real money, calculate PnL, or prove profitability."
    )


def _issue(
    severity: str,
    code: str,
    count: int,
    message: str,
) -> AdapterContractAcceptanceIssue:
    return AdapterContractAcceptanceIssue(
        severity=severity,
        code=code,
        count=count,
        message=message,
    )


def _status(issues: Sequence[AdapterContractAcceptanceIssue]) -> str:
    if any(issue.severity == "fail" for issue in issues):
        return "fail"
    if any(issue.severity == "warn" for issue in issues):
        return "warn"
    return "pass"


def _as_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    text = str(value).strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _load_contract(
    path: Path,
) -> tuple[Mapping[str, Any] | None, list[AdapterContractAcceptanceIssue]]:
    if not path.exists():
        return None, [
            _issue(
                "fail",
                "adapter_contract_missing",
                1,
                "Adapter contract JSON does not exist. Run Module DD first.",
            )
        ]

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [
            _issue(
                "fail",
                "adapter_contract_invalid_json",
                1,
                f"Adapter contract JSON could not be parsed safely: {exc}",
            )
        ]

    if not isinstance(payload, Mapping):
        return None, [
            _issue(
                "fail",
                "adapter_contract_invalid_shape",
                1,
                "Adapter contract JSON must be an object.",
            )
        ]

    return payload, []


def _safe_requests(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    requests = payload.get("adapter_requests", [])
    if not isinstance(requests, list):
        return []
    return [request for request in requests if isinstance(request, Mapping)]


def _forbidden(payload: Mapping[str, Any]) -> set[str]:
    return {
        str(key)
        for key in payload.keys()
        if str(key).strip().lower() in FORBIDDEN_KEYS
    }


def _contract_status_issues(
    payload: Mapping[str, Any],
    *,
    allow_warnings: bool,
) -> list[AdapterContractAcceptanceIssue]:
    issues: list[AdapterContractAcceptanceIssue] = []
    contract_status = str(payload.get("status") or "unknown").lower()
    ready = bool(payload.get("ready_for_future_adapter"))

    if contract_status == "warn":
        issues.append(
            _issue(
                "warn" if allow_warnings else "fail",
                "adapter_contract_warn",
                1,
                "Adapter contract status is warn.",
            )
        )
    elif contract_status == "fail":
        issues.append(
            _issue(
                "fail",
                "adapter_contract_failed",
                1,
                "Adapter contract status is fail.",
            )
        )
    elif contract_status != "pass":
        issues.append(
            _issue(
                "fail",
                "adapter_contract_unknown_status",
                1,
                f"Adapter contract status is unknown: {contract_status}.",
            )
        )

    if not ready:
        issues.append(
            _issue(
                "fail",
                "adapter_contract_not_ready",
                1,
                "Adapter contract is not marked ready_for_future_adapter.",
            )
        )

    return issues


def _request_issues(
    adapter_requests: Sequence[Mapping[str, Any]],
) -> tuple[list[AdapterContractAcceptanceIssue], int]:
    issues: list[AdapterContractAcceptanceIssue] = []
    total_bars = 0
    missing_required = 0
    wrong_modes = 0
    zero_bars = 0
    forbidden_count = 0

    for request in adapter_requests:
        required = [
            request.get("request_id"),
            request.get("scenario_id"),
            request.get("source_path"),
            request.get("first_timestamp"),
            request.get("last_timestamp"),
        ]
        if any(value in (None, "") for value in required):
            missing_required += 1

        planned_bar_count = _as_int(request.get("planned_bar_count")) or 0
        total_bars += planned_bar_count
        if planned_bar_count <= 0:
            zero_bars += 1

        if (
            request.get("adapter_mode") != "contract_only_no_strategy_execution"
            or request.get("strategy_execution_mode") != "not_executed_contract_only"
            or request.get("broker_execution_mode") != "broker_disabled"
            or request.get("output_mode") != "adapter_request_manifest_only"
        ):
            wrong_modes += 1

        forbidden_count += len(_forbidden(request))

    if missing_required:
        issues.append(
            _issue(
                "fail",
                "adapter_request_missing_required_fields",
                missing_required,
                "One or more adapter requests are missing identity/source/timestamp fields.",
            )
        )

    if zero_bars:
        issues.append(
            _issue(
                "fail",
                "adapter_request_zero_bars",
                zero_bars,
                "One or more adapter requests have zero planned bars.",
            )
        )

    if wrong_modes:
        issues.append(
            _issue(
                "fail",
                "adapter_request_wrong_modes",
                wrong_modes,
                "One or more adapter requests are not contract-only/broker-disabled/manifest-only.",
            )
        )

    if forbidden_count:
        issues.append(
            _issue(
                "fail",
                "adapter_request_forbidden_fields",
                forbidden_count,
                "Adapter requests contain forbidden execution/trading/profit fields.",
            )
        )

    return issues, total_bars


def build_adapter_contract_acceptance_report(
    *,
    adapter_contract_path: Path,
    output_dir: Path,
    min_requests: int = 1,
    min_total_planned_bars: int = 1,
    allow_warnings: bool = False,
) -> AdapterContractAcceptanceReport:
    min_requests = max(min_requests, 0)
    min_total_planned_bars = max(min_total_planned_bars, 0)

    payload, issues = _load_contract(adapter_contract_path)

    if payload is None:
        status = _status(issues)
        return AdapterContractAcceptanceReport(
            generated_at_utc=datetime.now(timezone.utc).isoformat(),
            adapter_contract_path=str(adapter_contract_path),
            output_directory=str(output_dir),
            status=status,
            accepted=False,
            allow_warnings=allow_warnings,
            min_requests_required=min_requests,
            min_total_planned_bars_required=min_total_planned_bars,
            contract_status="unknown",
            ready_for_future_adapter=False,
            request_count=0,
            total_planned_bars=0,
            safety_notice=safety_notice(),
            issues=issues,
        )

    issues.extend(_contract_status_issues(payload, allow_warnings=allow_warnings))

    forbidden_top_level = _forbidden(payload)
    if forbidden_top_level:
        issues.append(
            _issue(
                "fail",
                "adapter_contract_forbidden_fields",
                len(forbidden_top_level),
                "Adapter contract contains forbidden execution/trading/profit fields.",
            )
        )

    requests = _safe_requests(payload)
    request_issues, total_planned_bars = _request_issues(requests)
    issues.extend(request_issues)

    if len(requests) < min_requests:
        issues.append(
            _issue(
                "fail",
                "insufficient_adapter_requests",
                min_requests - len(requests),
                (
                    "Adapter request count below minimum. "
                    f"Required={min_requests}, actual={len(requests)}."
                ),
            )
        )

    if total_planned_bars < min_total_planned_bars:
        issues.append(
            _issue(
                "fail",
                "insufficient_total_planned_bars",
                min_total_planned_bars - total_planned_bars,
                (
                    "Adapter total planned bars below minimum. "
                    f"Required={min_total_planned_bars}, actual={total_planned_bars}."
                ),
            )
        )

    status = _status(issues)
    accepted = status == "pass" or (status == "warn" and allow_warnings)

    return AdapterContractAcceptanceReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        adapter_contract_path=str(adapter_contract_path),
        output_directory=str(output_dir),
        status=status,
        accepted=accepted,
        allow_warnings=allow_warnings,
        min_requests_required=min_requests,
        min_total_planned_bars_required=min_total_planned_bars,
        contract_status=str(payload.get("status") or "unknown").lower(),
        ready_for_future_adapter=bool(payload.get("ready_for_future_adapter")),
        request_count=len(requests),
        total_planned_bars=total_planned_bars,
        safety_notice=safety_notice(),
        issues=issues,
    )


def write_adapter_contract_acceptance_report(
    report: AdapterContractAcceptanceReport,
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    acceptance_json = output_dir / "paper_strategy_adapter_contract_acceptance.json"
    acceptance_txt = output_dir / "paper_strategy_adapter_contract_acceptance.txt"
    manifest_json = output_dir / "manifest.json"

    data = asdict(report)
    data["issues"] = [asdict(issue) for issue in report.issues]

    acceptance_json.write_text(
        json.dumps(data, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    lines = [
        "HQE Recorded Data Paper Strategy Adapter Contract Acceptance Gate",
        "",
        report.safety_notice,
        "",
        f"Status: {report.status}",
        f"Accepted for future adapter dry-run: {report.accepted}",
        f"Allow warnings: {report.allow_warnings}",
        f"Contract status: {report.contract_status}",
        f"Ready for future adapter: {report.ready_for_future_adapter}",
        f"Adapter requests: {report.request_count}",
        f"Total planned bars: {report.total_planned_bars}",
        "",
        "Issues:",
    ]

    if not report.issues:
        lines.append("- PASS: Adapter contract meets this contract-only acceptance scaffold.")
    else:
        for issue in report.issues:
            lines.append(
                f"- {issue.severity.upper()} {issue.code}: "
                f"{issue.message} Count={issue.count}"
            )

    lines.extend(
        [
            "",
            "Outputs:",
            f"- {acceptance_json}",
            f"- {acceptance_txt}",
            f"- {manifest_json}",
            "",
            "This gate does not execute strategy logic, create signals, calculate PnL, or create orders.",
            "This report is not a profitability claim.",
        ]
    )
    acceptance_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "report_type": "recorded_data_paper_strategy_adapter_contract_acceptance",
        "generated_at_utc": report.generated_at_utc,
        "status": report.status,
        "accepted": report.accepted,
        "request_count": report.request_count,
        "total_planned_bars": report.total_planned_bars,
        "safety_notice": report.safety_notice,
        "outputs": {
            "paper_strategy_adapter_contract_acceptance_json": str(acceptance_json),
            "paper_strategy_adapter_contract_acceptance_txt": str(acceptance_txt),
            "manifest_json": str(manifest_json),
        },
    }
    manifest_json.write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {
        "paper_strategy_adapter_contract_acceptance_json": acceptance_json,
        "paper_strategy_adapter_contract_acceptance_txt": acceptance_txt,
        "manifest_json": manifest_json,
    }


def build_and_write_adapter_contract_acceptance_report(
    *,
    adapter_contract_path: Path,
    output_dir: Path,
    min_requests: int = 1,
    min_total_planned_bars: int = 1,
    allow_warnings: bool = False,
) -> tuple[AdapterContractAcceptanceReport, dict[str, Path]]:
    report = build_adapter_contract_acceptance_report(
        adapter_contract_path=adapter_contract_path,
        output_dir=output_dir,
        min_requests=min_requests,
        min_total_planned_bars=min_total_planned_bars,
        allow_warnings=allow_warnings,
    )
    outputs = write_adapter_contract_acceptance_report(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Gate a no-execution paper strategy adapter contract."
    )
    parser.add_argument(
        "--adapter-contract",
        default=(
            "reports/paper_trading/"
            "recorded_data_paper_strategy_adapter_contract/"
            "paper_strategy_adapter_contract.json"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default=(
            "reports/paper_trading/"
            "recorded_data_paper_strategy_adapter_contract_acceptance"
        ),
    )
    parser.add_argument("--min-requests", type=int, default=1)
    parser.add_argument("--min-total-planned-bars", type=int, default=1)
    parser.add_argument("--allow-warnings", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report, outputs = build_and_write_adapter_contract_acceptance_report(
        adapter_contract_path=Path(args.adapter_contract),
        output_dir=Path(args.output_dir),
        min_requests=args.min_requests,
        min_total_planned_bars=args.min_total_planned_bars,
        allow_warnings=args.allow_warnings,
    )

    print("HQE recorded data paper strategy adapter contract acceptance completed.")
    print(report.safety_notice)
    print(f"Status: {report.status}")
    print(f"Accepted for future adapter dry-run: {report.accepted}")
    print(f"Adapter requests: {report.request_count}")
    print(
        "Adapter contract acceptance report: "
        f"{outputs['paper_strategy_adapter_contract_acceptance_txt']}"
    )
    print("This is not a profitability claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
