"""
Recorded data paper strategy adapter evidence bundle acceptance gate.

Evidence-only gate for the final adapter evidence bundle. It validates the
bundle status, stage structure, required stages, and safety boundaries before
future release/readiness modules can consume it.

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

REQUIRED_STAGES = {
    "recorded_data_paper_strategy_adapter_readiness",
    "recorded_data_paper_strategy_adapter_dry_run_readiness",
}


@dataclass(frozen=True)
class AdapterEvidenceBundleAcceptanceIssue:
    severity: str
    code: str
    count: int
    message: str


@dataclass(frozen=True)
class AdapterEvidenceBundleAcceptanceReport:
    generated_at_utc: str
    adapter_evidence_bundle_path: str
    output_directory: str
    status: str
    accepted: bool
    allow_warnings: bool
    min_stages_required: int
    bundle_status: str
    ready_for_future_adapter_evidence: bool
    stage_count: int
    required_stage_count: int
    safety_notice: str
    issues: list[AdapterEvidenceBundleAcceptanceIssue]


def safety_notice() -> str:
    return (
        "Paper/simulation evidence only. This adapter evidence bundle acceptance "
        "gate does not execute strategy logic, create signals, create trade "
        "plans, connect to brokers, request live market data, place real orders, "
        "use real money, calculate PnL, or prove profitability."
    )


def _issue(
    severity: str,
    code: str,
    count: int,
    message: str,
) -> AdapterEvidenceBundleAcceptanceIssue:
    return AdapterEvidenceBundleAcceptanceIssue(
        severity=severity,
        code=code,
        count=count,
        message=message,
    )


def _status(issues: Sequence[AdapterEvidenceBundleAcceptanceIssue]) -> str:
    if any(issue.severity == "fail" for issue in issues):
        return "fail"
    if any(issue.severity == "warn" for issue in issues):
        return "warn"
    return "pass"


def _load_bundle(
    path: Path,
) -> tuple[Mapping[str, Any] | None, list[AdapterEvidenceBundleAcceptanceIssue]]:
    if not path.exists():
        return None, [
            _issue(
                "fail",
                "adapter_evidence_bundle_missing",
                1,
                "Adapter evidence bundle JSON does not exist. Run Module JJ first.",
            )
        ]

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [
            _issue(
                "fail",
                "adapter_evidence_bundle_invalid_json",
                1,
                f"Adapter evidence bundle JSON could not be parsed safely: {exc}",
            )
        ]

    if not isinstance(payload, Mapping):
        return None, [
            _issue(
                "fail",
                "adapter_evidence_bundle_invalid_shape",
                1,
                "Adapter evidence bundle JSON must be an object.",
            )
        ]

    return payload, []


def _safe_stage_results(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    stages = payload.get("stage_results", [])
    if not isinstance(stages, list):
        return []
    return [stage for stage in stages if isinstance(stage, Mapping)]


def _forbidden(payload: Mapping[str, Any]) -> set[str]:
    return {
        str(key)
        for key in payload.keys()
        if str(key).strip().lower() in FORBIDDEN_KEYS
    }


def _bundle_status_issues(
    payload: Mapping[str, Any],
    *,
    allow_warnings: bool,
) -> list[AdapterEvidenceBundleAcceptanceIssue]:
    issues: list[AdapterEvidenceBundleAcceptanceIssue] = []
    bundle_status = str(payload.get("status") or "unknown").lower()
    ready = bool(payload.get("ready_for_future_adapter_evidence"))

    if bundle_status == "warn":
        issues.append(
            _issue(
                "warn" if allow_warnings else "fail",
                "adapter_evidence_bundle_warn",
                1,
                "Adapter evidence bundle status is warn.",
            )
        )
    elif bundle_status == "fail":
        issues.append(
            _issue(
                "fail",
                "adapter_evidence_bundle_failed",
                1,
                "Adapter evidence bundle status is fail.",
            )
        )
    elif bundle_status != "pass":
        issues.append(
            _issue(
                "fail",
                "adapter_evidence_bundle_unknown_status",
                1,
                f"Adapter evidence bundle status is unknown: {bundle_status}.",
            )
        )

    if not ready:
        issues.append(
            _issue(
                "fail",
                "adapter_evidence_bundle_not_ready",
                1,
                "Adapter evidence bundle is not marked ready_for_future_adapter_evidence.",
            )
        )

    return issues


def _stage_issues(
    stages: Sequence[Mapping[str, Any]],
    *,
    allow_warnings: bool,
) -> list[AdapterEvidenceBundleAcceptanceIssue]:
    issues: list[AdapterEvidenceBundleAcceptanceIssue] = []
    missing_required_fields = 0
    not_accepted = 0
    invalid_status = 0
    forbidden_fields = 0

    seen_stage_names: set[str] = set()

    for stage in stages:
        stage_name = str(stage.get("stage") or "")
        seen_stage_names.add(stage_name)

        required_values = [
            stage.get("stage"),
            stage.get("status"),
            stage.get("output_directory"),
        ]
        if any(value in (None, "") for value in required_values):
            missing_required_fields += 1

        if not bool(stage.get("accepted")):
            not_accepted += 1

        stage_status = str(stage.get("status") or "unknown").lower()
        if stage_status == "warn" and not allow_warnings:
            invalid_status += 1
        elif stage_status not in {"pass", "warn"}:
            invalid_status += 1

        forbidden_fields += len(_forbidden(stage))

    missing_stages = REQUIRED_STAGES - seen_stage_names
    if missing_stages:
        issues.append(
            _issue(
                "fail",
                "adapter_evidence_bundle_missing_required_stages",
                len(missing_stages),
                "Adapter evidence bundle is missing required readiness stages.",
            )
        )

    if missing_required_fields:
        issues.append(
            _issue(
                "fail",
                "adapter_evidence_stage_missing_required_fields",
                missing_required_fields,
                "One or more bundle stages are missing required fields.",
            )
        )

    if not_accepted:
        issues.append(
            _issue(
                "fail",
                "adapter_evidence_stage_not_accepted",
                not_accepted,
                "One or more bundle stages are not accepted.",
            )
        )

    if invalid_status:
        issues.append(
            _issue(
                "fail",
                "adapter_evidence_stage_invalid_status",
                invalid_status,
                "One or more bundle stages have fail/unknown/warn-without-allowance status.",
            )
        )

    if forbidden_fields:
        issues.append(
            _issue(
                "fail",
                "adapter_evidence_stage_forbidden_fields",
                forbidden_fields,
                "Bundle stages contain forbidden execution/trading/profit fields.",
            )
        )

    return issues


def build_adapter_evidence_bundle_acceptance_report(
    *,
    adapter_evidence_bundle_path: Path,
    output_dir: Path,
    min_stages: int = 2,
    allow_warnings: bool = False,
) -> AdapterEvidenceBundleAcceptanceReport:
    min_stages = max(min_stages, 0)

    payload, issues = _load_bundle(adapter_evidence_bundle_path)

    if payload is None:
        status = _status(issues)
        return AdapterEvidenceBundleAcceptanceReport(
            generated_at_utc=datetime.now(timezone.utc).isoformat(),
            adapter_evidence_bundle_path=str(adapter_evidence_bundle_path),
            output_directory=str(output_dir),
            status=status,
            accepted=False,
            allow_warnings=allow_warnings,
            min_stages_required=min_stages,
            bundle_status="unknown",
            ready_for_future_adapter_evidence=False,
            stage_count=0,
            required_stage_count=len(REQUIRED_STAGES),
            safety_notice=safety_notice(),
            issues=issues,
        )

    issues.extend(_bundle_status_issues(payload, allow_warnings=allow_warnings))

    forbidden_top_level = _forbidden(payload)
    if forbidden_top_level:
        issues.append(
            _issue(
                "fail",
                "adapter_evidence_bundle_forbidden_fields",
                len(forbidden_top_level),
                "Adapter evidence bundle contains forbidden execution/trading/profit fields.",
            )
        )

    stages = _safe_stage_results(payload)
    issues.extend(_stage_issues(stages, allow_warnings=allow_warnings))

    if len(stages) < min_stages:
        issues.append(
            _issue(
                "fail",
                "insufficient_adapter_evidence_stages",
                min_stages - len(stages),
                (
                    "Adapter evidence bundle stage count below minimum. "
                    f"Required={min_stages}, actual={len(stages)}."
                ),
            )
        )

    status = _status(issues)
    accepted = status == "pass" or (status == "warn" and allow_warnings)

    return AdapterEvidenceBundleAcceptanceReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        adapter_evidence_bundle_path=str(adapter_evidence_bundle_path),
        output_directory=str(output_dir),
        status=status,
        accepted=accepted,
        allow_warnings=allow_warnings,
        min_stages_required=min_stages,
        bundle_status=str(payload.get("status") or "unknown").lower(),
        ready_for_future_adapter_evidence=bool(
            payload.get("ready_for_future_adapter_evidence")
        ),
        stage_count=len(stages),
        required_stage_count=len(REQUIRED_STAGES),
        safety_notice=safety_notice(),
        issues=issues,
    )


def write_adapter_evidence_bundle_acceptance_report(
    report: AdapterEvidenceBundleAcceptanceReport,
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    acceptance_json = output_dir / "paper_strategy_adapter_evidence_bundle_acceptance.json"
    acceptance_txt = output_dir / "paper_strategy_adapter_evidence_bundle_acceptance.txt"
    manifest_json = output_dir / "manifest.json"

    data = asdict(report)
    data["issues"] = [asdict(issue) for issue in report.issues]

    acceptance_json.write_text(
        json.dumps(data, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    lines = [
        "HQE Recorded Data Paper Strategy Adapter Evidence Bundle Acceptance Gate",
        "",
        report.safety_notice,
        "",
        f"Status: {report.status}",
        f"Accepted for future adapter evidence release/readiness: {report.accepted}",
        f"Allow warnings: {report.allow_warnings}",
        f"Bundle status: {report.bundle_status}",
        f"Ready for future adapter evidence: {report.ready_for_future_adapter_evidence}",
        f"Stage count: {report.stage_count}",
        f"Required stage count: {report.required_stage_count}",
        "",
        "Issues:",
    ]

    if not report.issues:
        lines.append("- PASS: Adapter evidence bundle meets this acceptance scaffold.")
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
        "report_type": "recorded_data_paper_strategy_adapter_evidence_bundle_acceptance",
        "generated_at_utc": report.generated_at_utc,
        "status": report.status,
        "accepted": report.accepted,
        "stage_count": report.stage_count,
        "required_stage_count": report.required_stage_count,
        "safety_notice": report.safety_notice,
        "outputs": {
            "paper_strategy_adapter_evidence_bundle_acceptance_json": str(acceptance_json),
            "paper_strategy_adapter_evidence_bundle_acceptance_txt": str(acceptance_txt),
            "manifest_json": str(manifest_json),
        },
    }
    manifest_json.write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {
        "paper_strategy_adapter_evidence_bundle_acceptance_json": acceptance_json,
        "paper_strategy_adapter_evidence_bundle_acceptance_txt": acceptance_txt,
        "manifest_json": manifest_json,
    }


def build_and_write_adapter_evidence_bundle_acceptance_report(
    *,
    adapter_evidence_bundle_path: Path,
    output_dir: Path,
    min_stages: int = 2,
    allow_warnings: bool = False,
) -> tuple[AdapterEvidenceBundleAcceptanceReport, dict[str, Path]]:
    report = build_adapter_evidence_bundle_acceptance_report(
        adapter_evidence_bundle_path=adapter_evidence_bundle_path,
        output_dir=output_dir,
        min_stages=min_stages,
        allow_warnings=allow_warnings,
    )
    outputs = write_adapter_evidence_bundle_acceptance_report(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Gate a no-execution paper strategy adapter evidence bundle."
    )
    parser.add_argument(
        "--adapter-evidence-bundle",
        default=(
            "reports/paper_trading/"
            "recorded_data_paper_strategy_adapter_evidence_bundle/"
            "paper_strategy_adapter_evidence_bundle.json"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default=(
            "reports/paper_trading/"
            "recorded_data_paper_strategy_adapter_evidence_bundle_acceptance"
        ),
    )
    parser.add_argument("--min-stages", type=int, default=2)
    parser.add_argument("--allow-warnings", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report, outputs = build_and_write_adapter_evidence_bundle_acceptance_report(
        adapter_evidence_bundle_path=Path(args.adapter_evidence_bundle),
        output_dir=Path(args.output_dir),
        min_stages=args.min_stages,
        allow_warnings=args.allow_warnings,
    )

    print("HQE recorded data paper strategy adapter evidence bundle acceptance completed.")
    print(report.safety_notice)
    print(f"Status: {report.status}")
    print(f"Accepted for future adapter evidence release/readiness: {report.accepted}")
    print(f"Stage count: {report.stage_count}")
    print(
        "Adapter evidence bundle acceptance report: "
        f"{outputs['paper_strategy_adapter_evidence_bundle_acceptance_txt']}"
    )
    print("This is not a profitability claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
