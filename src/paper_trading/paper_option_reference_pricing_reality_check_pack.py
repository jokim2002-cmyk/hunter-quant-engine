"""
Paper Option Reference Pricing Reality Check Pack.

Module VVVV is paper/simulation only. It audits deterministic option reference
pricing assumptions before any future realistic paper rerun. It does not run a
backtest, change strategy logic, connect to brokers, request live data, place
orders, use real money, approve live trading, or prove profitability.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

DEFAULT_INPUT = Path(
    "reports/paper_trading/paper_tuning_candidate_readiness_pack/"
    "paper_tuning_candidate_readiness_pack.json"
)
DEFAULT_OUTPUT_DIR = Path(
    "reports/paper_trading/paper_option_reference_pricing_reality_check_pack"
)

CANDIDATE_ID = "option_reference_pricing_reality_check"
REPORT_TYPE = "paper_option_reference_pricing_reality_check_pack"

SAFETY_NOTICE = (
    "Paper/simulation pricing reality check only. This pack does not connect to "
    "brokers, request live market data, place real orders, use real money, approve "
    "live trading, or prove profitability."
)
NO_PROFITABILITY_CLAIM_NOTICE = (
    "This is not a profitability claim. Deterministic option reference prices, "
    "simulated totals, win rate, expectancy, and equity references remain "
    "paper/simulation evidence only."
)


@dataclass(frozen=True)
class PricingRealityItem:
    id: str
    title: str
    current_assumption: str
    reality_gap: str
    required_evidence: str
    status: str


@dataclass(frozen=True)
class PricingRealityReport:
    report_type: str
    status: str
    generated_at_utc: str
    input_path: str
    output_directory: str
    candidate_id: str
    candidate_found: bool
    candidate_priority: str
    candidate_status: str
    accepted_for_future_reality_check: bool
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
    items: list[PricingRealityItem]


def _load_json(path: Path) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
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


def _standard_items() -> list[PricingRealityItem]:
    return [
        PricingRealityItem(
            "item-01",
            "Deterministic option reference price",
            "Current recorded-data ledger and metrics use deterministic paper reference prices.",
            "These values are not real bid/ask fills, not live option-chain quotes, and not broker executions.",
            "Future offline replay fixture or comparison report showing deterministic reference values versus realistic option-chain assumptions.",
            "review_required",
        ),
        PricingRealityItem(
            "item-02",
            "Option-chain replay availability",
            "No option-chain replay dataset is required or loaded by this pack.",
            "Without option-chain replay, premium, liquidity, spread, and fill assumptions remain unvalidated.",
            "Recorded option-chain schema and offline sample fixture before improved rerun.",
            "blocked",
        ),
        PricingRealityItem(
            "item-03",
            "Bid/ask spread and fill model",
            "Current output does not prove the paper trade could be filled at the reference price.",
            "Spread and fill assumptions can reduce or reverse paper reference results.",
            "Next paper-only cost/slippage sensitivity pack.",
            "review_required",
        ),
        PricingRealityItem(
            "item-04",
            "Safety and profit-claim boundary",
            "Simulated paper totals are reference numbers only.",
            "Pricing assumptions are not realistic enough to prove profitability or live readiness.",
            "Every report must lock ready_for_live_or_real_money=false and profitability_claim_allowed=false.",
            "passed",
        ),
    ]


def build_pricing_reality_report(
    *,
    input_path: Path = DEFAULT_INPUT,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> PricingRealityReport:
    payload, issues = _load_json(input_path)
    candidate = _find_candidate(payload)
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
    high_impact = sum(1 for item in items if item.status in {"blocked", "review_required"})
    status = "fail" if any(issue.get("severity") == "fail" for issue in issues) else "pass"

    return PricingRealityReport(
        report_type=REPORT_TYPE,
        status=status,
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        input_path=str(input_path),
        output_directory=str(output_dir),
        candidate_id=CANDIDATE_ID,
        candidate_found=candidate_found,
        candidate_priority=candidate_priority,
        candidate_status=candidate_status,
        accepted_for_future_reality_check=accepted,
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
        no_profitability_claim_notice=NO_PROFITABILITY_CLAIM_NOTICE,
        issues=issues,
        items=items,
    )


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_items_csv(path: Path, items: list[PricingRealityItem]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file_obj:
        writer = csv.DictWriter(
            file_obj,
            fieldnames=[
                "id",
                "title",
                "current_assumption",
                "reality_gap",
                "required_evidence",
                "status",
            ],
        )
        writer.writeheader()
        for item in items:
            writer.writerow(asdict(item))


def _text_report(report: PricingRealityReport) -> str:
    lines = [
        "HQE Paper Option Reference Pricing Reality Check Pack",
        "=" * 80,
        f"Status: {report.status}",
        f"Candidate: {report.candidate_id}",
        f"Candidate found: {report.candidate_found}",
        f"Candidate priority: {report.candidate_priority}",
        f"Candidate status: {report.candidate_status}",
        f"Accepted for future pricing reality check: {report.accepted_for_future_reality_check}",
        f"Items: {report.item_count}",
        f"High impact items: {report.high_impact_item_count}",
        f"Backtest executed: {report.backtest_executed}",
        f"Strategy logic changed: {report.strategy_logic_changed}",
        f"Broker mode: {report.broker_execution_mode}",
        f"Live data mode: {report.live_data_mode}",
        f"Real orders mode: {report.real_order_mode}",
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
                f"  Gap: {item.reality_gap}",
                f"  Evidence: {item.required_evidence}",
                f"  Status: {item.status}",
            ]
        )
    if report.issues:
        lines.extend(["", "Issues:"])
        for issue in report.issues:
            lines.append(f"- {issue.get('code')}: {issue.get('message')}")
    return "\n".join(lines) + "\n"


def write_pricing_reality_pack(
    report: PricingRealityReport,
    output_dir: Path,
) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    report_json = output_dir / f"{REPORT_TYPE}.json"
    report_txt = output_dir / f"{REPORT_TYPE}.txt"
    items_csv = output_dir / "paper_option_pricing_reality_check_items.csv"
    manifest_json = output_dir / "manifest.json"

    _write_json(report_json, asdict(report))
    report_txt.write_text(_text_report(report), encoding="utf-8")
    _write_items_csv(items_csv, report.items)

    outputs = {
        "report_json": str(report_json),
        "report_txt": str(report_txt),
        "items_csv": str(items_csv),
        "manifest_json": str(manifest_json),
    }
    _write_json(
        manifest_json,
        {
            "report_type": REPORT_TYPE,
            "status": report.status,
            "generated_at_utc": report.generated_at_utc,
            "candidate_id": report.candidate_id,
            "accepted_for_future_reality_check": report.accepted_for_future_reality_check,
            "ready_for_live_or_real_money": False,
            "profitability_claim_allowed": False,
            "backtest_executed": False,
            "strategy_logic_changed": False,
            "outputs": outputs,
        },
    )
    return outputs


def build_and_write_pricing_reality_pack(
    *,
    input_path: Path = DEFAULT_INPUT,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> tuple[PricingRealityReport, dict[str, str]]:
    report = build_pricing_reality_report(input_path=input_path, output_dir=output_dir)
    outputs = write_pricing_reality_pack(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Paper option reference pricing reality check pack."
    )
    parser.add_argument("--input", dest="input_path", default=str(DEFAULT_INPUT))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report, outputs = build_and_write_pricing_reality_pack(
        input_path=Path(args.input_path),
        output_dir=Path(args.output_dir),
    )
    print("HQE paper option reference pricing reality check pack completed.")
    print(report.safety_notice)
    print(report.no_profitability_claim_notice)
    print(f"Status: {report.status}")
    print(f"Candidate found: {report.candidate_found}")
    print(
        "Accepted for future pricing reality check: "
        f"{report.accepted_for_future_reality_check}"
    )
    print(f"High impact items: {report.high_impact_item_count}")
    print(f"Report: {outputs['report_txt']}")
    print("This is not a profitability claim.")
    return 0 if report.status in {"pass", "warn"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
