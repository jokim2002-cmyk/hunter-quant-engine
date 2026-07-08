"""
Paper Signal Cooldown and Duplicate Filter Review Pack

Module YYYY - paper/offline only.

This pack audits whether repeated, clustered, or near-duplicate paper signals can
inflate recorded-data paper backtest evidence before any future improved rerun.

It does NOT change strategy logic, run a backtest, optimize parameters, connect
to brokers, request live data, place orders, use real money, approve live
trading, or prove profitability.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence


DEFAULT_TUNING_INPUT = Path(
    "reports/paper_trading/paper_tuning_candidate_readiness_pack/"
    "paper_tuning_candidate_readiness_pack.json"
)
DEFAULT_EXIT_REVIEW_INPUT = Path(
    "reports/paper_trading/paper_exit_rule_sensitivity_review_pack/"
    "paper_exit_rule_sensitivity_review_pack.json"
)
DEFAULT_FREQUENCY_GUARD_INPUT = Path(
    "reports/paper_trading/paper_trade_frequency_guard/"
    "paper_trade_frequency_guard.json"
)
DEFAULT_OUTPUT_DIR = Path(
    "reports/paper_trading/paper_signal_cooldown_duplicate_filter_review_pack"
)

CANDIDATE_ID = "signal_cooldown_and_duplicate_filter"
REPORT_TYPE = "paper_signal_cooldown_duplicate_filter_review_pack"
SAFE_BROKER_MODE = "broker_disabled"
SAFE_DATA_MODE = "live_data_disabled"
SAFE_ORDER_MODE = "real_orders_disabled"

SAFETY_NOTICE = (
    "Paper/simulation signal cooldown and duplicate filter review only. This pack "
    "does not connect to brokers, request live market data, place real orders, use "
    "real money, approve live trading, or prove profitability."
)
NO_PROFIT_CLAIM = (
    "This is not a profitability claim. Signal spacing, cooldown, duplicate filter, "
    "trade count, win rate, expectancy, equity, and simulated total references remain "
    "paper/simulation evidence only."
)


@dataclass(frozen=True)
class CooldownDuplicateReviewItem:
    id: str
    title: str
    current_assumption: str
    risk: str
    required_evidence: str
    status: str


@dataclass(frozen=True)
class CooldownDuplicateReviewReport:
    report_type: str
    status: str
    generated_at_utc: str
    tuning_input_path: str
    exit_review_input_path: str
    frequency_guard_input_path: str
    output_directory: str
    candidate_id: str
    candidate_found: bool
    candidate_priority: str
    candidate_status: str
    accepted_for_future_cooldown_duplicate_review: bool
    exit_review_report_found: bool
    frequency_guard_report_found: bool
    item_count: int
    high_impact_item_count: int
    backtest_executed: bool
    optimization_executed: bool
    strategy_logic_changed: bool
    broker_execution_mode: str
    live_data_mode: str
    real_order_mode: str
    ready_for_live_or_real_money: bool
    profitability_claim_allowed: bool
    safety_notice: str
    no_profitability_claim_notice: str
    issues: list[dict[str, Any]]
    items: list[CooldownDuplicateReviewItem]


def _load_json(path: Path, *, missing_code: str) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    if not path.exists():
        return None, [
            {
                "code": missing_code,
                "severity": "warn",
                "message": f"Input report not found: {path}",
            }
        ]

    try:
        return json.loads(path.read_text(encoding="utf-8")), []
    except json.JSONDecodeError as exc:
        return None, [
            {
                "code": f"{missing_code}_invalid_json",
                "severity": "fail",
                "message": str(exc),
            }
        ]


def _candidates(payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not payload:
        return []
    candidates = payload.get("candidates", [])
    return candidates if isinstance(candidates, list) else []


def _find_candidate(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    for candidate in _candidates(payload):
        if str(candidate.get("candidate_id") or "") == CANDIDATE_ID:
            return candidate
    return None


def _standard_items() -> list[CooldownDuplicateReviewItem]:
    return [
        CooldownDuplicateReviewItem(
            "item-01",
            "Signal cooldown audit boundary",
            "Recorded-data SMC decisions can still create clustered trade opportunities after the SMC parameter-aligned gate.",
            "Closely spaced repeated signals may overstate robustness or inflate trade count before a realistic rerun.",
            "A future paper-only rerun should compare baseline signals with a documented cooldown window and same-direction spacing rule.",
            "review_required",
        ),
        CooldownDuplicateReviewItem(
            "item-02",
            "Duplicate or near-duplicate trade filter",
            "Frequency guard reduces executed ledger rows, but duplicate signal intent review remains separate from result reporting.",
            "Multiple signals from the same market structure may represent one idea repeated several times, not independent edge.",
            "A future filter should classify same-direction, same-session, and near-same-entry signals before comparison.",
            "review_required",
        ),
        CooldownDuplicateReviewItem(
            "item-03",
            "Overtrading confidence control",
            "The current paper baseline is useful evidence, but trade frequency still needs spacing and duplicate-control interpretation.",
            "Without signal-spacing evidence, paper win rate or simulated totals can look stronger than the underlying independent opportunities.",
            "Create a controlled paper-only comparison showing raw plans, guarded plans, cooldown-filtered plans, skipped reasons, and no-profit-claim wording.",
            "blocked_for_profit_claim",
        ),
        CooldownDuplicateReviewItem(
            "item-04",
            "Safety and execution boundary",
            "This pack reviews evidence only and does not change strategy logic or execute any backtest.",
            "Cooldown review must not be misread as live approval, real-money readiness, or profitability proof.",
            "Every output must lock ready_for_live_or_real_money=false and profitability_claim_allowed=false.",
            "passed",
        ),
    ]


def build_cooldown_duplicate_review_report(
    *,
    tuning_input_path: Path = DEFAULT_TUNING_INPUT,
    exit_review_input_path: Path = DEFAULT_EXIT_REVIEW_INPUT,
    frequency_guard_input_path: Path = DEFAULT_FREQUENCY_GUARD_INPUT,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> CooldownDuplicateReviewReport:
    tuning_payload, issues = _load_json(tuning_input_path, missing_code="tuning_input_missing")
    exit_payload, exit_issues = _load_json(exit_review_input_path, missing_code="exit_review_input_missing")
    frequency_guard_payload, guard_issues = _load_json(
        frequency_guard_input_path,
        missing_code="frequency_guard_input_missing",
    )
    issues.extend(exit_issues)
    issues.extend(guard_issues)

    candidate = _find_candidate(tuning_payload)
    candidate_found = candidate is not None
    candidate_priority = str((candidate or {}).get("priority") or "")
    candidate_status = str((candidate or {}).get("status") or "")

    if not candidate_found:
        issues.append(
            {
                "code": "candidate_missing",
                "severity": "warn",
                "message": f"Candidate not found: {CANDIDATE_ID}",
            }
        )

    accepted = (
        candidate_found
        and candidate_priority == "high"
        and candidate_status == "paper_candidate_ready"
    )
    items = _standard_items()
    high_impact = sum(
        1 for item in items if item.status in {"review_required", "blocked_for_profit_claim"}
    )
    failure_issues = [issue for issue in issues if issue.get("severity") == "fail"]
    status = "pass" if not failure_issues else "fail"

    return CooldownDuplicateReviewReport(
        report_type=REPORT_TYPE,
        status=status,
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        tuning_input_path=str(tuning_input_path),
        exit_review_input_path=str(exit_review_input_path),
        frequency_guard_input_path=str(frequency_guard_input_path),
        output_directory=str(output_dir),
        candidate_id=CANDIDATE_ID,
        candidate_found=candidate_found,
        candidate_priority=candidate_priority,
        candidate_status=candidate_status,
        accepted_for_future_cooldown_duplicate_review=accepted,
        exit_review_report_found=exit_payload is not None,
        frequency_guard_report_found=frequency_guard_payload is not None,
        item_count=len(items),
        high_impact_item_count=high_impact,
        backtest_executed=False,
        optimization_executed=False,
        strategy_logic_changed=False,
        broker_execution_mode=SAFE_BROKER_MODE,
        live_data_mode=SAFE_DATA_MODE,
        real_order_mode=SAFE_ORDER_MODE,
        ready_for_live_or_real_money=False,
        profitability_claim_allowed=False,
        safety_notice=SAFETY_NOTICE,
        no_profitability_claim_notice=NO_PROFIT_CLAIM,
        issues=issues,
        items=items,
    )


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_csv(path: Path, items: list[CooldownDuplicateReviewItem]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "id",
                "title",
                "current_assumption",
                "risk",
                "required_evidence",
                "status",
            ],
        )
        writer.writeheader()
        for item in items:
            writer.writerow(asdict(item))


def _text_report(report: CooldownDuplicateReviewReport) -> str:
    lines = [
        "HQE Paper Signal Cooldown and Duplicate Filter Review Pack",
        "=" * 80,
        f"Status: {report.status}",
        f"Candidate: {report.candidate_id}",
        f"Candidate found: {report.candidate_found}",
        f"Candidate priority: {report.candidate_priority}",
        f"Candidate status: {report.candidate_status}",
        (
            "Accepted for future cooldown/duplicate review: "
            f"{report.accepted_for_future_cooldown_duplicate_review}"
        ),
        f"Exit rule review report found: {report.exit_review_report_found}",
        f"Frequency guard report found: {report.frequency_guard_report_found}",
        f"Items: {report.item_count}",
        f"High impact items: {report.high_impact_item_count}",
        f"Backtest executed: {report.backtest_executed}",
        f"Optimization executed: {report.optimization_executed}",
        f"Strategy logic changed: {report.strategy_logic_changed}",
        f"Broker mode: {report.broker_execution_mode}",
        f"Live data mode: {report.live_data_mode}",
        f"Ready for live/real money: {report.ready_for_live_or_real_money}",
        f"Profitability claim allowed: {report.profitability_claim_allowed}",
        "",
        report.safety_notice,
        report.no_profitability_claim_notice,
        "",
        "Items:",
    ]
    for item in report.items:
        lines.extend(
            [
                "",
                f"- {item.id}: {item.title}",
                f"  Current: {item.current_assumption}",
                f"  Risk: {item.risk}",
                f"  Evidence: {item.required_evidence}",
                f"  Status: {item.status}",
            ]
        )
    if report.issues:
        lines.extend(["", "Issues:"])
        for issue in report.issues:
            lines.append(f"- {issue.get('code')}: {issue.get('message')}")
    return "\n".join(lines) + "\n"


def write_cooldown_duplicate_review_pack(
    report: CooldownDuplicateReviewReport,
    output_dir: Path,
) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    report_json = output_dir / f"{REPORT_TYPE}.json"
    report_txt = output_dir / f"{REPORT_TYPE}.txt"
    items_csv = output_dir / "paper_signal_cooldown_duplicate_filter_review_items.csv"
    manifest_json = output_dir / "manifest.json"

    _write_json(report_json, asdict(report))
    report_txt.write_text(_text_report(report), encoding="utf-8")
    _write_csv(items_csv, report.items)

    outputs = {
        "report_json": str(report_json),
        "report_txt": str(report_txt),
        "items_csv": str(items_csv),
        "manifest_json": str(manifest_json),
    }
    manifest_payload = {
        "report_type": REPORT_TYPE,
        "status": report.status,
        "generated_at_utc": report.generated_at_utc,
        "candidate_id": report.candidate_id,
        "accepted_for_future_cooldown_duplicate_review": report.accepted_for_future_cooldown_duplicate_review,
        "ready_for_live_or_real_money": False,
        "profitability_claim_allowed": False,
        "backtest_executed": False,
        "strategy_logic_changed": False,
        "outputs": outputs,
    }
    _write_json(manifest_json, manifest_payload)
    return outputs


def build_and_write_cooldown_duplicate_review_pack(
    *,
    tuning_input_path: Path = DEFAULT_TUNING_INPUT,
    exit_review_input_path: Path = DEFAULT_EXIT_REVIEW_INPUT,
    frequency_guard_input_path: Path = DEFAULT_FREQUENCY_GUARD_INPUT,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> tuple[CooldownDuplicateReviewReport, dict[str, str]]:
    report = build_cooldown_duplicate_review_report(
        tuning_input_path=tuning_input_path,
        exit_review_input_path=exit_review_input_path,
        frequency_guard_input_path=frequency_guard_input_path,
        output_dir=output_dir,
    )
    outputs = write_cooldown_duplicate_review_pack(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Paper signal cooldown and duplicate filter review pack."
    )
    parser.add_argument("--tuning-input", default=str(DEFAULT_TUNING_INPUT))
    parser.add_argument("--exit-review-input", default=str(DEFAULT_EXIT_REVIEW_INPUT))
    parser.add_argument("--frequency-guard-input", default=str(DEFAULT_FREQUENCY_GUARD_INPUT))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report, outputs = build_and_write_cooldown_duplicate_review_pack(
        tuning_input_path=Path(args.tuning_input),
        exit_review_input_path=Path(args.exit_review_input),
        frequency_guard_input_path=Path(args.frequency_guard_input),
        output_dir=Path(args.output_dir),
    )

    print("HQE paper signal cooldown and duplicate filter review pack completed.")
    print(report.safety_notice)
    print(report.no_profitability_claim_notice)
    print(f"Status: {report.status}")
    print(f"Candidate found: {report.candidate_found}")
    print(
        "Accepted for future cooldown/duplicate review: "
        f"{report.accepted_for_future_cooldown_duplicate_review}"
    )
    print(f"Exit rule review report found: {report.exit_review_report_found}")
    print(f"Frequency guard report found: {report.frequency_guard_report_found}")
    print(f"High impact items: {report.high_impact_item_count}")
    print(f"Report: {outputs['report_txt']}")
    print("This is not a profitability claim.")
    return 0 if report.status in {"pass", "warn"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
