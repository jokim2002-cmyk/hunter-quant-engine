"""
Run Option Buy Backtest Robustness Controls Tests
"""

from scripts.run_option_buy_backtest import run_backtest


SCENARIO_CSV = """
snapshot_id,timestamp,signal_type,signal_strength,confidence,underlying_symbol,underlying_price,expiry_date,strike_price,option_type,lot_size,option_symbol,last_traded_price,bid_price,ask_price,volume,open_interest,rationale
s1,2026-07-06T09:15:00,long,strong,0.9,NIFTY,24210,2026-07-09,24200,CE,65,NIFTY26JUL24200CE,100,99,100,0,50000,test setup
"""

PREMIUM_CSV = """
symbol,timestamp,open,high,low,close,volume
NIFTY26JUL24200CE,2026-07-06T09:20:00,100,170,95,165,1000
"""


def _write_csv(tmp_path, filename, content):
    path = tmp_path / filename
    path.write_text(content.strip() + "\n", encoding="utf-8")
    return path


def test_run_backtest_rejects_illiquid_scenario_when_min_volume_enabled(tmp_path):
    scenario_csv = _write_csv(tmp_path, "scenario.csv", SCENARIO_CSV)
    premium_csv = _write_csv(tmp_path, "premium.csv", PREMIUM_CSV)

    summary = run_backtest(
        scenario_csv=scenario_csv,
        premium_csv=premium_csv,
        min_volume=1,
    )

    assert summary.planned_signals == 1
    assert summary.completed_trades == 0
    assert summary.rejected_plans == 1
    assert summary.rejection_reasons == (
        "CE strike 24200.0 rejected because volume below minimum 1",
    )


def test_run_backtest_keeps_legacy_behavior_when_min_volume_default_is_used(tmp_path):
    scenario_csv = _write_csv(tmp_path, "scenario.csv", SCENARIO_CSV)
    premium_csv = _write_csv(tmp_path, "premium.csv", PREMIUM_CSV)

    summary = run_backtest(
        scenario_csv=scenario_csv,
        premium_csv=premium_csv,
    )

    assert summary.planned_signals == 1
    assert summary.completed_trades == 1
    assert summary.rejected_plans == 0
