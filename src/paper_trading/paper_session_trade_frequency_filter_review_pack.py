"""
Paper Session and Trade Frequency Filter Review Pack

Module ZZZZ - paper/offline only.

This pack audits whether session-window and trade-frequency assumptions can
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
DEFAULT_COOLDOWN_INPUT = Path(
    "reports/paper_trading/paper_signal_cooldown_duplicate_filter_review_pack/"
    "paper_signal_cooldown_duplicate_filter_review_pack.json"
)
DEFAULT_FREQUENCY_GUARD_INPUT = Path(
    "reports/paper_trading/paper_trade_frequency_guard/"
    "paper_trade_frequency_guard.json"
)
DEFAULT_OUTPUT_DIR = Path(
    "reports/paper_trading/paper_session_trade_frequency_filter_review_pack"
)

CANDIDATE_ID = "session_and_trade_frequency_filter"
REPORT_TYPE = "paper_session_trade_frequency_filter_review_pack"
SAFE_BROKER_MODE = "broker_disabled"
SAFE_DATA_MODE = "live_data_disabled"
SAFE_ORDER_MODE = "real_orders_disabled"

SAFETY_NOTICE = (
    "Paper/simulation session and trade-frequency filter review only. This pack "
    "does not connect to brokers, request live market data, place real orders, use "
    "real money, approve live trading, or prove profitability."
)
NO_PROFIT_CLAIM = (
    "This is not a profitability claim. Session filtering, trade frequency, skipped "
    "trade counts, win rate, expectancy, equity, and simulated total references remain "
    "paper/simulation evidence only."
)


@dataclass(frozen=True)
class SessionFrequencyReviewItem:
    id: str
    title: str
    current_assumption: str
    risk: str
    required_evidence: str
    status: str


@dataclass(frozen=True)
class SessionFrequencyReviewReport:
    report_type: str
    status: str
    generated_at_utc: str
    tuning_input_path: str
    cooldown_input_path: str
    frequency_guard_input_path: str
    output_directory: str
    candidate_id: str
    candidate_found: bool
    candidate_priority: str
    candidate_status: str
    accepted_for_future_session_frequency_review: bool
    cooldown_review_report_found: bool
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
    items: list[SessionFrequencyReviewItem]


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


def _standard_items() -> list[SessionFrequencyReviewItem]:
    return [
        SessionFrequencyReviewItem(
            "item-01",
            "Session-window assumption review",
            "Recorded-data paper backtest currently uses available replay bars without a dedicated session-quality filter review.",
            "Opening noise, late-session liquidity changes, and partial sessions can distort paper result interpretation.",
            "Future paper-only comparison should classify full session, opening range, lunch/low-liquidity window, closing window, and partial-day bars.",
            "review_required",
        ),
        SessionFrequencyReviewItem(
            "item-02",
            "Trade-frequency filter boundary",
            "Frequency guard already reduces ledger rows, but a session-aware frequency rule is not yet documented as rerun evidence.",
            "Trade count can still be inflated if many trades occur inside the same session regime or repeated market condition.",
            "Future paper-only rerun should compare raw, frequency-guarded, cooldown-filtered, and session-filtered outputs with skipped reasons.",
            "review_required",
        ),
        SessionFrequencyReviewItem(
            "item-03",
            "Daily/session concentration risk",
            "A small number of sessions may dominate the paper evidence.",
            "If results depend on a few high-frequency days, paper metrics may not represent stable behaviour.",
            "Create session-level concentration evidence: trades per day, trades per session window, skipped count, and top-day contribution.",
            "blocked_for_profit_claim",
        ),
        SessionFrequencyReviewItem(
            "item-04",
            "Safety and execution boundary",
            "This pack reviews evidence only and does not run a backtest or change strategy logic.",
            "Session-frequency review must not be misread as live approval or profit proof.",
            "Every output must keep ready_for_live_or_real_money=false and profitability_claim_allowed=false.",
            "passed",
        ),
    ]


def build_session_frequency_review_report(
    *,
    tuning_input_path: Path = DEFAULT_TUNING_INPUT,
    cooldown_input_path: Path = DEFAULT_COOLDOWN_INPUT,
    frequency_guard_input_path: Path = DEFAULT_FREQUENCY_GUARD_INPUT,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> SessionFrequencyReviewReport:
    tuning_payload, issues = _load_json(tuning_input_path, missing_code="tuning_input_missing")
    cooldown_payload, cooldown_issues = _load_json(cooldown_input_path, missing_code="cooldown_input_missing")
    frequency_guard_payload, guard_issues = _load_json(
        frequency_guard_input_path,
        missing_code="frequency_guard_input_missing",
    )
    issues.extend(cooldown_issues)
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
        and candidate_priority == "medium"
        and candidate_status == "paper_candidate_ready"
    )
    items = _standard_items()
    high_impact = sum(
        1 for item in items if item.status in {"review_required", "blocked_for_profit_claim"}
    )
    failure_issues = [issue for issue in issues if issue.get("severity") == "fail"]
    status = "pass" if not failure_issues else "fail"

    return SessionFrequencyReviewReport(
        report_type=REPORT_TYPE,
        status=status,
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        tuning_input_path=str(tuning_input_path),
        cooldown_input_path=str(cooldown_input_path),
        frequency_guard_input_path=str(frequency_guard_input_path),
        output_directory=str(output_dir),
        candidate_id=CANDIDATE_ID,
        candidate_found=candidate_found,
        candidate_priority=candidate_priority,
        candidate_status=candidate_status,
        accepted_for_future_session_frequency_review=accepted,
        cooldown_review_report_found=cooldown_payload is not None,
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


def _write_csv(path: Path, items: list[SessionFrequencyReviewItem]) -> None:
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


def _text_report(report: SessionFrequencyReviewReport) -> str:
    lines = [
        "HQE Paper Session and Trade Frequency Filter Review Pack",
        "=" * 80,
        f"Status: {report.status}",
        f"Candidate: {report.candidate_id}",
        f"Candidate found: {report.candidate_found}",
        f"Candidate priority: {report.candidate_priority}",
        f"Candidate status: {report.candidate_status}",
        (
            "Accepted for future session/frequency review: "
            f"{report.accepted_for_future_session_frequency_review}"
        ),
        f"Cooldown review report found: {report.cooldown_review_report_found}",
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


def write_session_frequency_review_pack(
    report: SessionFrequencyReviewReport,
    output_dir: Path,
) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    report_json = output_dir / f"{REPORT_TYPE}.json"
    report_txt = output_dir / f"{REPORT_TYPE}.txt"
    items_csv = output_dir / "paper_session_trade_frequency_filter_review_items.csv"
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
        "accepted_for_future_session_frequency_review": report.accepted_for_future_session_frequency_review,
        "ready_for_live_or_real_money": False,
        "profitability_claim_allowed": False,
        "backtest_executed": False,
        "strategy_logic_changed": False,
        "outputs": outputs,
    }
    _write_json(manifest_json, manifest_payload)
    return outputs


def build_and_write_session_frequency_review_pack(
    *,
    tuning_input_path: Path = DEFAULT_TUNING_INPUT,
    cooldown_input_path: Path = DEFAULT_COOLDOWN_INPUT,
    frequency_guard_input_path: Path = DEFAULT_FREQUENCY_GUARD_INPUT,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> tuple[SessionFrequencyReviewReport, dict[str, str]]:
    report = build_session_frequency_review_report(
        tuning_input_path=tuning_input_path,
        cooldown_input_path=cooldown_input_path,
        frequency_guard_input_path=frequency_guard_input_path,
        output_dir=output_dir,
    )
    outputs = write_session_frequency_review_pack(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Paper session and trade-frequency filter review pack."
    )
    parser.add_argument("--tuning-input", default=str(DEFAULT_TUNING_INPUT))
    parser.add_argument("--cooldown-input", default=str(DEFAULT_COOLDOWN_INPUT))
    parser.add_argument("--frequency-guard-input", default=str(DEFAULT_FREQUENCY_GUARD_INPUT))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report, outputs = build_and_write_session_frequency_review_pack(
        tuning_input_path=Path(args.tuning_input),
        cooldown_input_path=Path(args.cooldown_input),
        frequency_guard_input_path=Path(args.frequency_guard_input),
        output_dir=Path(args.output_dir),
    )

    print("HQE paper session and trade-frequency filter review pack completed.")
    print(report.safety_notice)
    print(report.no_profitability_claim_notice)
    print(f"Status: {report.status}")
    print(f"Candidate found: {report.candidate_found}")
    print(
        "Accepted for future session/frequency review: "
        f"{report.accepted_for_future_session_frequency_review}"
    )
    print(f"Cooldown review report found: {report.cooldown_review_report_found}")
    print(f"Frequency guard report found: {report.frequency_guard_report_found}")
    print(f"High impact items: {report.high_impact_item_count}")
    print(f"Report: {outputs['report_txt']}")
    print("This is not a profitability claim.")
    return 0 if report.status in {"pass", "warn"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
