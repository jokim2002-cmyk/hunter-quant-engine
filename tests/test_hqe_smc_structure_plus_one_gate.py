from src.paper_trading import recorded_data_strategy_decision_audit as audit


def bars():
    return [
        {"open": 100.0, "high": 102.0, "low": 98.0, "close": 101.0}
        for _ in range(audit.SMC_MIN_HISTORY_BARS)
    ]


def run_gate(monkeypatch, bullish, bearish):
    monkeypatch.setattr(
        audit,
        "_recent_liquidity_sweep",
        lambda *, direction, **kwargs:
            bullish[0] if direction == "LONG" else bearish[0],
    )
    monkeypatch.setattr(
        audit,
        "_market_structure_break",
        lambda *, direction, **kwargs:
            bullish[1] if direction == "LONG" else bearish[1],
    )
    monkeypatch.setattr(
        audit,
        "_recent_fair_value_gap_or_displacement",
        lambda *, direction, **kwargs:
            bullish[2] if direction == "LONG" else bearish[2],
    )

    return audit._decision_for_smc_parameter_gate(
        previous_close=100.0,
        close=101.0,
        event={"open": 100.0, "high": 103.0, "low": 99.0, "close": 101.0},
        previous_events=bars(),
        threshold_points=0.0,
        total_sandbox_events=audit.SMC_MIN_HISTORY_BARS + 1,
    )


def test_long_accepts_structure_plus_entry_zone(monkeypatch):
    decision, reason, _ = run_gate(
        monkeypatch,
        bullish=(False, True, True),
        bearish=(False, False, False),
    )
    assert decision == "LONG"
    assert "LONG_CE_BUY_ALLOWED" in reason


def test_short_accepts_structure_plus_liquidity(monkeypatch):
    decision, reason, _ = run_gate(
        monkeypatch,
        bullish=(False, False, False),
        bearish=(True, True, False),
    )
    assert decision == "SHORT"
    assert "SHORT_PE_BUY_ALLOWED" in reason


def test_structure_remains_mandatory(monkeypatch):
    decision, _, _ = run_gate(
        monkeypatch,
        bullish=(True, False, True),
        bearish=(False, False, False),
    )
    assert decision == "NEUTRAL"


def test_conflicting_setups_remain_neutral(monkeypatch):
    decision, reason, _ = run_gate(
        monkeypatch,
        bullish=(False, True, True),
        bearish=(True, True, False),
    )
    assert decision == "NEUTRAL"
    assert "CONFLICTING_SMC_SETUPS" in reason
