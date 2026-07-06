"""
Paper Backtest Evidence Runner Tests

Paper/simulation only. No broker. No live market data. No real orders.
"""

from datetime import date, datetime
from pathlib import Path

import pytest

from src.models.option_action import OptionAction
from src.models.option_chain_entry import OptionChainEntry
from src.models.option_contract import OptionContract
from src.models.option_type import OptionType
from src.paper_trading.paper_backtest_evidence_runner import (
    PaperBacktestEvidenceThresholds,
    build_paper_backtest_evidence_report,
    format_paper_backtest_evidence_report,
    paper_backtest_evidence_report_to_dict,
    run_paper_backtest_evidence,
)
from src.paper_trading.paper_realized_exit_record import PaperExitReason
from src.paper_trading.strategy_to_paper_bridge import (
    StrategyPaperExitInstruction,
    run_strategy_to_paper_bridge,
)
from src.strategy.signal_strength import SignalStrength
from src.strategy.signal_type import SignalType
from src.strategy.trade_signal import TradeSignal
from src.trade_planning.option_buy_trade_plan import OptionBuyTradePlan
from src.trade_planning.option_buy_trade_plan_status import OptionBuyTradePlanStatus


_CREATED_AT = datetime(2026, 7, 6, 9, 15)
_CLOSED_AT = datetime(2026, 7, 6, 9, 30)


def _signal() -> TradeSignal:
    return TradeSignal(
        signal_type=SignalType.LONG,
        strength=SignalStrength.STRONG,
        confidence=0.9,
        rationale=("paper evidence runner test signal",),
        created_at=_CREATED_AT,
    )


def _contract(symbol: str = "NIFTY26JUL24200CE") -> OptionContract:
    return OptionContract(
        underlying_symbol="NIFTY",
        expiry_date=date(2026, 7, 9),
        strike_price=24200.0,
        option_type=OptionType.CE,
        lot_size=65,
        symbol=symbol,
    )


def _entry(symbol: str = "NIFTY26JUL24200CE", premium: float = 100.0) -> OptionChainEntry:
    return OptionChainEntry(
        contract=_contract(symbol=symbol),
        last_traded_price=premium,
        bid_price=premium - 1.0,
        ask_price=premium + 1.0,
        volume=10000,
        open_interest=50000,
    )


def _plan(symbol: str = "NIFTY26JUL24200CE", premium: float = 100.0) -> OptionBuyTradePlan:
    return OptionBuyTradePlan(
        signal=_signal(),
        entry=_entry(symbol=symbol, premium=premium),
        action=OptionAction.BUY,
        underlying_price=24210.0,
        entry_premium=premium,
        stop_loss_premium=premium - 30.0,
        target_premium=premium + 60.0,
        lots=2,
        estimated_charges=40.0,
        status=OptionBuyTradePlanStatus.APPROVED,
        rejection_reasons=(),
    )


def _closed_session(tmp_path):
    bridge_result = run_strategy_to_paper_bridge(
        [_plan()],
        exit_instructions=[
            StrategyPaperExitInstruction(
                symbol="NIFTY26JUL24200CE",
                closed_at=_CLOSED_AT,
                exit_reason=PaperExitReason.TARGET,
                exit_price=135.0,
                estimated_exit_charges=10.0,
                estimated_slippage=5.0,
            )
        ],
        output_dir=tmp_path / "reports" / "strategy_to_paper",
        generated_at=_CREATED_AT,
    )
    return bridge_result.session


def test_paper_backtest_evidence_runner_writes_json_text_and_manifest(tmp_path):
    session = _closed_session(tmp_path)

    report, paths = run_paper_backtest_evidence(
        session,
        output_dir=tmp_path / "reports" / "paper_trading" / "evidence",
        generated_at=_CLOSED_AT,
    )

    assert report.passed is True
    assert report.closed_trades == 1
    assert report.open_positions == 0
    assert report.simulated_net_pnl == 4535.0
    assert report.blocking_reasons == ()

    assert paths.evidence_json.exists()
    assert paths.evidence_text.exists()
    assert paths.manifest_json.exists()

    text = paths.evidence_text.read_text(encoding="utf-8")
    assert "Hunter Quant Engine - Paper Backtest Evidence" in text
    assert "paper/simulation only" in text
    assert "not a profitability claim" in text
    assert "passed gates: True" in text


def test_paper_backtest_evidence_report_dict_is_json_safe(tmp_path):
    session = _closed_session(tmp_path)
    report, _paths = run_paper_backtest_evidence(
        session,
        output_dir=tmp_path / "reports" / "paper_trading" / "evidence",
        generated_at=_CLOSED_AT,
    )

    payload = paper_backtest_evidence_report_to_dict(report)

    assert payload["paper_evidence_is_simulation_only"] is True
    assert payload["no_broker_orders"] is True
    assert payload["no_live_market_data"] is True
    assert payload["no_real_orders"] is True
    assert payload["not_a_profitability_claim"] is True
    assert payload["thresholds"]["min_closed_trades"] == 1
    assert payload["blocking_reasons"] == []


def test_paper_backtest_evidence_blocks_when_no_closed_trades(tmp_path):
    bridge_result = run_strategy_to_paper_bridge(
        [_plan()],
        output_dir=tmp_path / "reports" / "strategy_to_paper",
    )

    report, _paths = run_paper_backtest_evidence(
        bridge_result.session,
        output_dir=tmp_path / "reports" / "paper_trading" / "evidence",
    )

    assert report.passed is False
    assert "closed trades below minimum: 0 < 1" in report.blocking_reasons
    assert "open positions above maximum: 1 > 0" in report.blocking_reasons


def test_paper_backtest_evidence_blocks_when_net_pnl_threshold_fails(tmp_path):
    session = _closed_session(tmp_path)

    report, _paths = run_paper_backtest_evidence(
        session,
        output_dir=tmp_path / "reports" / "paper_trading" / "evidence",
        thresholds=PaperBacktestEvidenceThresholds(min_simulated_net_pnl=10000.0),
    )

    assert report.passed is False
    assert "simulated net pnl below minimum: 4535.0 < 10000.0" in report.blocking_reasons


def test_build_paper_backtest_evidence_report_supports_custom_thresholds(tmp_path):
    session = _closed_session(tmp_path)
    report, _paths = run_paper_backtest_evidence(
        session,
        output_dir=tmp_path / "reports" / "paper_trading" / "evidence",
    )

    rebuilt = build_paper_backtest_evidence_report(
        report_summary_from_session(session),
        thresholds=PaperBacktestEvidenceThresholds(
            min_closed_trades=2,
            max_open_positions=0,
            max_unknown_trades=0,
        ),
        generated_at=_CLOSED_AT,
    )

    assert rebuilt.passed is False
    assert "closed trades below minimum: 1 < 2" in rebuilt.blocking_reasons


def test_format_paper_backtest_evidence_report_prints_blocking_reasons(tmp_path):
    bridge_result = run_strategy_to_paper_bridge(
        [],
        output_dir=tmp_path / "reports" / "strategy_to_paper",
    )
    report, _paths = run_paper_backtest_evidence(
        bridge_result.session,
        output_dir=tmp_path / "reports" / "paper_trading" / "evidence",
    )

    text = format_paper_backtest_evidence_report(report)

    assert "passed gates: False" in text
    assert "Blocking Reasons" in text
    assert "- closed trades below minimum: 0 < 1" in text


def test_paper_backtest_evidence_runner_rejects_output_outside_reports(tmp_path):
    session = _closed_session(tmp_path)

    with pytest.raises(ValueError, match="reports/"):
        run_paper_backtest_evidence(
            session,
            output_dir=tmp_path / "evidence",
        )


def test_paper_backtest_evidence_runner_source_has_no_external_order_execution_imports():
    source = Path("src/paper_trading/paper_backtest_evidence_runner.py").read_text(
        encoding="utf-8"
    ).lower()

    assert "import " + "fy" + "ers" not in source
    assert "from " + "fy" + "ers" not in source
    assert "place" + "_order" not in source
    assert "send" + "_order" not in source
    assert "execute" + "_order" not in source


def report_summary_from_session(session):
    from src.paper_trading.paper_trading_session_summary import (
        build_paper_trading_session_summary,
    )

    return build_paper_trading_session_summary(session)
