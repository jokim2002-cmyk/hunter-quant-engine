"""
Run Option Buy Backtest Time-Scoped Replay Tests
"""

from scripts.run_option_buy_backtest import run_backtest


SCENARIO_CSV = """
snapshot_id,timestamp,signal_type,signal_strength,confidence,underlying_symbol,underlying_price,expiry_date,strike_price,option_type,lot_size,option_symbol,last_traded_price,bid_price,ask_price,volume,open_interest,rationale
s1,2026-07-06T09:15:00,long,strong,0.9,NIFTY,24210,2026-07-09,24200,CE,65,NIFTY26JUL24200CE,100,99,100,1000,50000,test setup
"""

PREMIUM_CSV = """
symbol,timestamp,open,high,low,close,volume
NIFTY26JUL24200CE,2026-07-06T09:10:00,100,170,95,165,1000
NIFTY26JUL24200CE,2026-07-06T09:20:00,100,105,95,100,1000
NIFTY26JUL24200CE,2026-07-06T09:25:00,100,170,95,165,1000
"""


def _write_csv(tmp_path, filename, content):
    path = tmp_path / filename
    path.write_text(content.strip() + "\n", encoding="utf-8")
    return path


def test_run_backtest_legacy_replay_can_see_pre_signal_premium_candles(tmp_path):
    scenario_csv = _write_csv(tmp_path, "scenario.csv", SCENARIO_CSV)
    premium_csv = _write_csv(tmp_path, "premium.csv", PREMIUM_CSV)

    summary = run_backtest(
        scenario_csv=scenario_csv,
        premium_csv=premium_csv,
    )

    assert summary.completed_trades == 1
    assert summary.results[0].exit_premium == 160.0
    assert summary.results[0].bars_held == 1


def test_run_backtest_time_scoped_replay_ignores_pre_signal_candles(tmp_path):
    scenario_csv = _write_csv(tmp_path, "scenario.csv", SCENARIO_CSV)
    premium_csv = _write_csv(tmp_path, "premium.csv", PREMIUM_CSV)

    summary = run_backtest(
        scenario_csv=scenario_csv,
        premium_csv=premium_csv,
        time_scope_premium_candles=True,
    )

    assert summary.completed_trades == 1
    assert summary.results[0].exit_premium == 160.0
    assert summary.results[0].bars_held == 2


def test_run_backtest_max_bars_held_caps_time_scoped_replay(tmp_path):
    scenario_csv = _write_csv(tmp_path, "scenario.csv", SCENARIO_CSV)
    premium_csv = _write_csv(tmp_path, "premium.csv", PREMIUM_CSV)

    summary = run_backtest(
        scenario_csv=scenario_csv,
        premium_csv=premium_csv,
        max_bars_held=1,
    )

    assert summary.completed_trades == 1
    assert summary.results[0].exit_premium == 100.0
    assert summary.results[0].bars_held == 1
