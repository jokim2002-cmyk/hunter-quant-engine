"""
Paper Exit Rule Sensitivity Review Pack.

Module XXXX - paper/offline only.

This pack audits the current paper exit-rule assumptions after the option pricing
reality check and slippage/cost sensitivity packs. It does not rerun a backtest,
change strategy logic, connect to brokers, request live market data, place real
orders, use real money, or prove profitability.
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
DEFAULT_SLIPPAGE_INPUT = Path(
    "reports/paper_trading/paper_slippage_and_cost_sensitivity_pack/"
    "paper_slippage_and_cost_sensitivity_pack.json"
)
DEFAULT_OUTPUT_DIR = Path(
    "reports/paper_trading/paper_exit_rule_sensitivity_review_pack"
)

CANDIDATE_ID = "exit_rule_sensitivity"
REPORT_TYPE = "paper_exit_rule_sensitivity_review_pack"

SAFETY_NOTICE = (
    "Paper/simulation exit-rule sensitivity review only. This pack does not "
    "connect to brokers, request live market data, place real orders, use real "
    "money, approve live trading, or prove profitability."
)
NO_PROFIT_CLAIM = (
    "This is not a profitability claim. Exit rule, stop loss, take profit, "
    "timeout, win rate, expectancy, equity, drawdown, and simulated total "
    "references remain paper/simulation evidence only."
)


@dataclass(frozen=True)
class ExitRuleSensitivityItem:
    id: str
    title: str
    current_assumption: str
    sensitivity_gap: str
    required_evidence: str
    status: str


@dataclass(frozen=True)
class ExitRuleSensitivityReport:
    report_type: str
    status: str
    generated_at_utc: str
    tuning_input_path: str
    slippage_input_path: str
    output_directory: str
    candidate_id: str
    candidate_found: bool
    candidate_priority: str
    candidate_status: str
    accepted_for_future_exit_rule_review: bool
    slippage_cost_report_found: bool
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
    items: list[ExitRuleSensitivityItem]


def _read_json(path: Path) -> tuple[dict[str, Any] | None, list[dict[str, str]]]:
    if not path.exists():
        return None, [
            {
                "code": "input_missing",
                "severity": "warn",
                "message": f"Input report not found: {path}",
            }
        ]

    try:
        return json.loads(path.read_text(encoding="utf-8")), []
    except json.JSONDecodeError as exc:
        return None, [
            {
                "code": "invalid_json",
                "severity": "fail",
                "message": str(exc),
            }
        ]


def _candidate_list(payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not payload:
        return []
    candidates = payload.get("candidates", [])
    return candidates if isinstance(candidates, list) else []


def _find_candidate(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    for candidate in _candidate_list(payload):
        if str(candidate.get("candidate_id") or "") == CANDIDATE_ID:
            return candidate
    return None


def _slippage_report_found(payload: dict[str, Any] | None) -> bool:
    if not payload:
        return False
    return str(payload.get("report_type") or "") == "paper_slippage_and_cost_sensitivity_pack"


def _standard_items() -> list[ExitRuleSensitivityItem]:
    return [
        ExitRuleSensitivityItem(
            id="item-01",
            title="Stop-loss and take-profit rule distribution",
            current_assumption=(
                "Current ledger evidence contains deterministic paper exits, but this pack "
                "does not prove the distribution remains stable under alternate stop/target rules."
            ),
            sensitivity_gap=(
                "A different stop, target, timeout, or partial-exit rule may materially change "
                "win rate, average win/loss, drawdown, and simulated totals."
            ),
            required_evidence=(
                "Future paper-only exit-rule matrix comparing current exit logic against "
                "controlled stop/target/timeout variants."
            ),
            status="review_required",
        ),
        ExitRuleSensitivityItem(
            id="item-02",
            title="Timeout and end-of-session exit sensitivity",
            current_assumption=(
                "Current paper lifecycle output is deterministic and does not separately prove "
                "which trades depend on timeout/end-of-session assumptions."
            ),
            sensitivity_gap=(
                "Trades that only work because of a favorable timeout or session close rule can "
                "create false confidence in paper evidence."
            ),
            required_evidence=(
                "Future exit reason distribution report with timeout/session-close sensitivity buckets."
            ),
            status="review_required",
        ),
        ExitRuleSensitivityItem(
            id="item-03",
            title="Intrabar path and option premium movement",
            current_assumption=(
                "Current recorded 5-minute replay does not prove the actual intrabar path for option "
                "premium stop/target fills."
            ),
            sensitivity_gap=(
                "Without intrabar or option-chain replay evidence, stop/target order of touch can "
                "remain ambiguous for some trades."
            ),
            required_evidence=(
                "Future offline replay assumption note or conservative intrabar sequencing rule before "
                "claiming improved paper reliability."
            ),
            status="blocked",
        ),
        ExitRuleSensitivityItem(
            id="item-04",
            title="Safety and no-profit boundary",
            current_assumption=(
                "Current simulated totals and exit metrics are paper reference numbers only."
            ),
            sensitivity_gap=(
                "Exit-rule sensitivity is not enough to approve live trading, real money, or a "
                "profitability claim."
            ),
            required_evidence=(
                "All reports must keep ready_for_live_or_real_money=false and "
                "profitability_claim_allowed=false."
            ),
            status="passed",
        ),
    ]


def build_exit_rule_sensitivity_report(
    *,
    tuning_input_path: Path = DEFAULT_TUNING_INPUT,
    slippage_input_path: Path = DEFAULT_SLIPPAGE_INPUT,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> ExitRuleSensitivityReport:
    tuning_payload, tuning_issues = _read_json(tuning_input_path)
    slippage_payload, slippage_issues = _read_json(slippage_input_path)

    candidate = _find_candidate(tuning_payload)
    candidate_found = candidate is not None
    candidate_priority = str((candidate or {}).get("priority") or "")
    candidate_status = str((candidate or {}).get("status") or "")
    slippage_found = _slippage_report_found(slippage_payload)

    issues: list[dict[str, Any]] = []
    issues.extend(tuning_issues)
    issues.extend(slippage_issues)

    if not candidate_found:
        issues.append(
            {
                "code": "candidate_missing",
                "severity": "warn",
                "message": f"Candidate not found: {CANDIDATE_ID}",
            }
        )
    if not slippage_found:
        issues.append(
            {
                "code": "slippage_cost_report_missing",
                "severity": "warn",
                "message": "Expected paper slippage and cost sensitivity report was not found.",
            }
        )

    items = _standard_items()
    high_impact = sum(1 for item in items if item.status in {"blocked", "review_required"})
    fail_issues = [issue for issue in issues if issue.get("severity") == "fail"]
    status = "pass" if not fail_issues else "fail"

    accepted = (
        candidate_found
        and candidate_priority == "high"
        and candidate_status == "paper_candidate_ready"
        and slippage_found
    )

    return ExitRuleSensitivityReport(
        report_type=REPORT_TYPE,
        status=status,
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        tuning_input_path=str(tuning_input_path),
        slippage_input_path=str(slippage_input_path),
        output_directory=str(output_dir),
        candidate_id=CANDIDATE_ID,
        candidate_found=candidate_found,
        candidate_priority=candidate_priority,
        candidate_status=candidate_status,
        accepted_for_future_exit_rule_review=accepted,
        slippage_cost_report_found=slippage_found,
        item_count=len(items),
        high_impact_item_count=high_impact,
        backtest_executed=False,
        optimization_executed=False,
        strategy_logic_changed=False,
        broker_execution_mode="broker_disabled",
        live_data_mode="live_data_disabled",
        real_order_mode="real_orders_disabled",
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


def _write_csv(path: Path, items: list[ExitRuleSensitivityItem]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "id",
                "title",
                "current_assumption",
                "sensitivity_gap",
                "required_evidence",
                "status",
            ],
        )
        writer.writeheader()
        for item in items:
            writer.writerow(asdict(item))


def _text_report(report: ExitRuleSensitivityReport) -> str:
    lines = [
        "HQE Paper Exit Rule Sensitivity Review Pack",
        "=" * 80,
        f"Status: {report.status}",
        f"Candidate: {report.candidate_id}",
        f"Candidate found: {report.candidate_found}",
        f"Candidate priority: {report.candidate_priority}",
        f"Candidate status: {report.candidate_status}",
        f"Accepted for future exit-rule review: {report.accepted_for_future_exit_rule_review}",
        f"Slippage/cost report found: {report.slippage_cost_report_found}",
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
                f"  Gap: {item.sensitivity_gap}",
                f"  Evidence: {item.required_evidence}",
                f"  Status: {item.status}",
            ]
        )

    if report.issues:
        lines.extend(["", "Issues:"])
        for issue in report.issues:
            lines.append(f"- {issue.get('code')}: {issue.get('message')}")

    return "\n".join(lines) + "\n"


def write_exit_rule_sensitivity_pack(
    report: ExitRuleSensitivityReport,
    output_dir: Path,
) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    report_json = output_dir / f"{REPORT_TYPE}.json"
    report_txt = output_dir / f"{REPORT_TYPE}.txt"
    items_csv = output_dir / "paper_exit_rule_sensitivity_review_items.csv"
    manifest = output_dir / "manifest.json"

    _write_json(report_json, asdict(report))
    report_txt.write_text(_text_report(report), encoding="utf-8")
    _write_csv(items_csv, report.items)

    outputs = {
        "report_json": str(report_json),
        "report_txt": str(report_txt),
        "items_csv": str(items_csv),
        "manifest_json": str(manifest),
    }
    _write_json(
        manifest,
        {
            "report_type": REPORT_TYPE,
            "status": report.status,
            "generated_at_utc": report.generated_at_utc,
            "candidate_id": report.candidate_id,
            "accepted_for_future_exit_rule_review": report.accepted_for_future_exit_rule_review,
            "slippage_cost_report_found": report.slippage_cost_report_found,
            "ready_for_live_or_real_money": False,
            "profitability_claim_allowed": False,
            "backtest_executed": False,
            "optimization_executed": False,
            "strategy_logic_changed": False,
            "outputs": outputs,
        },
    )
    return outputs


def build_and_write_exit_rule_sensitivity_pack(
    *,
    tuning_input_path: Path = DEFAULT_TUNING_INPUT,
    slippage_input_path: Path = DEFAULT_SLIPPAGE_INPUT,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> tuple[ExitRuleSensitivityReport, dict[str, str]]:
    report = build_exit_rule_sensitivity_report(
        tuning_input_path=tuning_input_path,
        slippage_input_path=slippage_input_path,
        output_dir=output_dir,
    )
    outputs = write_exit_rule_sensitivity_pack(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Paper exit-rule sensitivity review pack."
    )
    parser.add_argument("--tuning-input", default=str(DEFAULT_TUNING_INPUT))
    parser.add_argument("--slippage-input", default=str(DEFAULT_SLIPPAGE_INPUT))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report, outputs = build_and_write_exit_rule_sensitivity_pack(
        tuning_input_path=Path(args.tuning_input),
        slippage_input_path=Path(args.slippage_input),
        output_dir=Path(args.output_dir),
    )

    print("HQE paper exit rule sensitivity review pack completed.")
    print(report.safety_notice)
    print(report.no_profitability_claim_notice)
    print(f"Status: {report.status}")
    print(f"Candidate found: {report.candidate_found}")
    print(
        "Accepted for future exit-rule review: "
        f"{report.accepted_for_future_exit_rule_review}"
    )
    print(f"Slippage/cost report found: {report.slippage_cost_report_found}")
    print(f"High impact items: {report.high_impact_item_count}")
    print(f"Report: {outputs['report_txt']}")
    print("This is not a profitability claim.")
    return 0 if report.status in {"pass", "warn"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
