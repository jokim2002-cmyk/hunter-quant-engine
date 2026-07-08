"""
Paper Slippage and Cost Sensitivity Pack

Module WWWW - paper/offline only.

This pack audits the next realism layer after the paper option reference pricing
reality check: slippage, spread, charges, and cost sensitivity. It does not run a
backtest, optimize parameters, connect to brokers, request live data, place real
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


DEFAULT_INPUT = Path(
    "reports/paper_trading/paper_tuning_candidate_readiness_pack/"
    "paper_tuning_candidate_readiness_pack.json"
)
DEFAULT_PRICING_REALITY_INPUT = Path(
    "reports/paper_trading/paper_option_reference_pricing_reality_check_pack/"
    "paper_option_reference_pricing_reality_check_pack.json"
)
DEFAULT_OUTPUT_DIR = Path(
    "reports/paper_trading/paper_slippage_and_cost_sensitivity_pack"
)

CANDIDATE_ID = "slippage_and_cost_sensitivity"
REPORT_TYPE = "paper_slippage_and_cost_sensitivity_pack"
SAFE_BROKER_MODE = "broker_disabled"
SAFE_DATA_MODE = "live_data_disabled"
SAFE_ORDER_MODE = "real_orders_disabled"

SAFETY_NOTICE = (
    "Paper/simulation slippage and cost sensitivity pack only. This pack does not "
    "connect to brokers, request live market data, place real orders, use real money, "
    "approve live trading, or prove profitability."
)
NO_PROFIT_CLAIM = (
    "This is not a profitability claim. Slippage, spread, charge, win rate, expectancy, "
    "equity, and simulated total references remain paper/simulation evidence only."
)


@dataclass(frozen=True)
class SlippageCostItem:
    """One paper-only cost/slippage sensitivity item."""

    id: str
    title: str
    current_assumption: str
    sensitivity_risk: str
    required_evidence: str
    status: str


@dataclass(frozen=True)
class SlippageCostReport:
    """Structured output for the WWWW pack."""

    report_type: str
    status: str
    generated_at_utc: str
    input_path: str
    pricing_reality_input_path: str
    output_directory: str
    candidate_id: str
    candidate_found: bool
    candidate_priority: str
    candidate_status: str
    accepted_for_future_sensitivity_review: bool
    pricing_reality_report_found: bool
    pricing_reality_status: str
    pricing_reality_profitability_claim_allowed: bool
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
    items: list[SlippageCostItem]


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


def _standard_items() -> list[SlippageCostItem]:
    return [
        SlippageCostItem(
            "item-01",
            "Paper slippage sensitivity scenarios",
            "Current paper ledger/result evidence does not prove fills after adverse slippage.",
            "Small per-trade slippage can materially reduce or reverse reference totals in option-buy simulations.",
            "Future paper-only scenario table covering low, medium, and high slippage assumptions before improved rerun.",
            "review_required",
        ),
        SlippageCostItem(
            "item-02",
            "Bid/ask spread sensitivity",
            "Current deterministic reference price is not a real bid/ask executable fill.",
            "Wide option spreads may make entry/exit worse than reference price, especially around illiquid strikes.",
            "Future offline spread assumption model or option-chain replay fixture before live-paper observer work.",
            "review_required",
        ),
        SlippageCostItem(
            "item-03",
            "Charges and transaction-cost boundary",
            "Paper totals are review evidence and may not fully represent all realistic option-buy costs.",
            "Costs can reduce win rate quality, expectancy, and final simulated total references.",
            "Future cost-adjusted comparison report with explicit brokerage, taxes, fees, and sensitivity bands.",
            "review_required",
        ),
        SlippageCostItem(
            "item-04",
            "Safety and non-profitability boundary",
            "Strategy logic remains unchanged and no backtest or optimization is executed by this pack.",
            "Without this boundary, sensitivity output could be misread as strategy selection or proof.",
            "Report must keep ready_for_live_or_real_money=false and profitability_claim_allowed=false.",
            "passed",
        ),
    ]


def build_slippage_cost_report(
    *,
    input_path: Path = DEFAULT_INPUT,
    pricing_reality_input_path: Path = DEFAULT_PRICING_REALITY_INPUT,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> SlippageCostReport:
    tuning_payload, issues = _load_json(input_path)
    pricing_payload, pricing_issues = _load_json(pricing_reality_input_path)
    issues.extend(pricing_issues)

    candidate = _find_candidate(tuning_payload)
    items = _standard_items()

    candidate_found = candidate is not None
    candidate_priority = str((candidate or {}).get("priority") or "")
    candidate_status = str((candidate or {}).get("status") or "")
    accepted = (
        candidate_found
        and candidate_priority == "high"
        and candidate_status == "paper_candidate_ready"
    )

    pricing_found = pricing_payload is not None
    pricing_status = str((pricing_payload or {}).get("status") or "")
    pricing_profit_claim = bool(
        (pricing_payload or {}).get("profitability_claim_allowed", False)
    )

    if not candidate_found:
        issues.append(
            {
                "code": "candidate_missing",
                "severity": "warn",
                "message": f"Candidate not found: {CANDIDATE_ID}",
            }
        )
    if pricing_profit_claim:
        issues.append(
            {
                "code": "pricing_profit_claim_unexpected",
                "severity": "fail",
                "message": "Pricing reality input unexpectedly allows profitability claims.",
            }
        )

    high_impact = sum(
        1 for item in items if item.status in {"blocked", "review_required"}
    )
    failure_issues = [issue for issue in issues if issue.get("severity") == "fail"]
    status = "pass" if not failure_issues else "fail"

    return SlippageCostReport(
        report_type=REPORT_TYPE,
        status=status,
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        input_path=str(input_path),
        pricing_reality_input_path=str(pricing_reality_input_path),
        output_directory=str(output_dir),
        candidate_id=CANDIDATE_ID,
        candidate_found=candidate_found,
        candidate_priority=candidate_priority,
        candidate_status=candidate_status,
        accepted_for_future_sensitivity_review=accepted,
        pricing_reality_report_found=pricing_found,
        pricing_reality_status=pricing_status,
        pricing_reality_profitability_claim_allowed=pricing_profit_claim,
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
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_csv(path: Path, items: list[SlippageCostItem]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "id",
                "title",
                "current_assumption",
                "sensitivity_risk",
                "required_evidence",
                "status",
            ],
        )
        writer.writeheader()
        for item in items:
            writer.writerow(asdict(item))


def _text_report(report: SlippageCostReport) -> str:
    lines = [
        "HQE Paper Slippage and Cost Sensitivity Pack",
        "=" * 80,
        f"Status: {report.status}",
        f"Candidate: {report.candidate_id}",
        f"Candidate found: {report.candidate_found}",
        f"Candidate priority: {report.candidate_priority}",
        f"Candidate status: {report.candidate_status}",
        f"Accepted for future sensitivity review: {report.accepted_for_future_sensitivity_review}",
        f"Pricing reality report found: {report.pricing_reality_report_found}",
        f"Pricing reality status: {report.pricing_reality_status}",
        f"Pricing reality profitability claim allowed: {report.pricing_reality_profitability_claim_allowed}",
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
                f"  Risk: {item.sensitivity_risk}",
                f"  Evidence: {item.required_evidence}",
                f"  Status: {item.status}",
            ]
        )
    if report.issues:
        lines.extend(["", "Issues:"])
        for issue in report.issues:
            lines.append(f"- {issue.get('code')}: {issue.get('message')}")
    return "\n".join(lines) + "\n"


def write_slippage_cost_pack(
    report: SlippageCostReport,
    output_dir: Path,
) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    report_json = output_dir / f"{REPORT_TYPE}.json"
    report_txt = output_dir / f"{REPORT_TYPE}.txt"
    items_csv = output_dir / "paper_slippage_and_cost_sensitivity_items.csv"
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
    manifest_payload = {
        "report_type": REPORT_TYPE,
        "status": report.status,
        "generated_at_utc": report.generated_at_utc,
        "candidate_id": report.candidate_id,
        "accepted_for_future_sensitivity_review": report.accepted_for_future_sensitivity_review,
        "ready_for_live_or_real_money": False,
        "profitability_claim_allowed": False,
        "backtest_executed": False,
        "strategy_logic_changed": False,
        "outputs": outputs,
    }
    _write_json(manifest, manifest_payload)
    return outputs


def build_and_write_slippage_cost_pack(
    *,
    input_path: Path = DEFAULT_INPUT,
    pricing_reality_input_path: Path = DEFAULT_PRICING_REALITY_INPUT,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> tuple[SlippageCostReport, dict[str, str]]:
    report = build_slippage_cost_report(
        input_path=input_path,
        pricing_reality_input_path=pricing_reality_input_path,
        output_dir=output_dir,
    )
    outputs = write_slippage_cost_pack(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Paper slippage and cost sensitivity pack."
    )
    parser.add_argument("--input", dest="input_path", default=str(DEFAULT_INPUT))
    parser.add_argument(
        "--pricing-reality-input",
        dest="pricing_reality_input_path",
        default=str(DEFAULT_PRICING_REALITY_INPUT),
    )
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report, outputs = build_and_write_slippage_cost_pack(
        input_path=Path(args.input_path),
        pricing_reality_input_path=Path(args.pricing_reality_input_path),
        output_dir=Path(args.output_dir),
    )
    print("HQE paper slippage and cost sensitivity pack completed.")
    print(report.safety_notice)
    print(report.no_profitability_claim_notice)
    print(f"Status: {report.status}")
    print(f"Candidate found: {report.candidate_found}")
    print(
        "Accepted for future sensitivity review: "
        f"{report.accepted_for_future_sensitivity_review}"
    )
    print(f"Pricing reality report found: {report.pricing_reality_report_found}")
    print(f"High impact items: {report.high_impact_item_count}")
    print(f"Report: {outputs['report_txt']}")
    print("This is not a profitability claim.")
    return 0 if report.status in {"pass", "warn"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
