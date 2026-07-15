from datetime import datetime
from pathlib import Path

from scripts import run_forward_intraday_paper_supervisor as s


NOW = datetime(2026, 7, 15, 13, 0, 0)


def premium(
    side: str,
    symbol: str,
    *,
    high: float = 110.0,
    low: float = 90.0,
    close: float = 100.0,
) -> s.Candle:
    return s.Candle(
        dt=NOW,
        open=100.0,
        high=high,
        low=low,
        close=close,
        last_traded_price=close,
        dte=6,
        symbol=symbol,
        signal_side=side,
    )


def index_candles() -> list[s.Candle]:
    return [
        s.Candle(
            dt=NOW,
            open=24000.0,
            high=24010.0,
            low=23990.0,
            close=24000.0,
        )
        for _ in range(21)
    ]


def patch_cycle_io(monkeypatch, tmp_path, index_rows, premium_rows, state):
    captured = {}

    monkeypatch.setattr(
        s,
        "read_candles",
        lambda path, *, premium:
            premium_rows if premium else index_rows,
    )
    monkeypatch.setattr(
        s,
        "data_ready",
        lambda index_candles, premium_candles, now:
            (True, "DATA_READY"),
    )
    monkeypatch.setattr(
        s,
        "load_position_state",
        lambda path: dict(state),
    )
    monkeypatch.setattr(
        s,
        "save_json",
        lambda path, payload:
            captured.__setitem__(Path(path).name, dict(payload)),
    )
    monkeypatch.setattr(s, "append_csv", lambda *args, **kwargs: None)
    monkeypatch.setattr(s, "write_report", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        s,
        "evaluator_status_text",
        lambda path: "TEST_LEDGER_OK",
    )

    paths = s.SupervisorPaths(
        index_csv=tmp_path / "index.csv",
        premium_csv=tmp_path / "premium.csv",
        out_dir=tmp_path / "out",
        state_json=tmp_path / "position.json",
        ledger_csv=tmp_path / "ledger.csv",
    )
    return paths, captured


def test_selects_exact_open_position_side_and_symbol():
    ce = premium("CE_BUY", "NSE:TESTCE")
    pe = premium("PE_BUY", "NSE:TESTPE")

    selected = s.select_position_premium_candle(
        [ce, pe],
        {"side": "CE_BUY", "option_symbol": "NSE:TESTCE"},
    )

    assert selected is ce


def test_ce_position_does_not_use_last_pe_candle(monkeypatch, tmp_path):
    ce = premium(
        "CE_BUY",
        "NSE:TESTCE",
        high=110.0,
        low=90.0,
        close=100.0,
    )
    pe = premium(
        "PE_BUY",
        "NSE:TESTPE",
        high=300.0,
        low=10.0,
        close=200.0,
    )

    state = {
        "status": "OPEN",
        "side": "CE_BUY",
        "option_symbol": "NSE:TESTCE",
        "entry": 100.0,
        "stop_loss": 60.0,
        "target": 220.0,
        "quantity": 1,
        "paper_only": True,
    }

    paths, captured = patch_cycle_io(
        monkeypatch,
        tmp_path,
        index_candles(),
        [ce, pe],
        state,
    )

    summary = s.run_one_cycle(paths, NOW)

    assert summary["event"] == "POSITION_HELD"
    assert summary["signal_side"] == "CE_BUY"
    assert captured["position.json"]["status"] == "OPEN"


def test_open_ce_signal_saves_active_candidate_and_symbol(
    monkeypatch,
    tmp_path,
):
    ce = premium("CE_BUY", "NSE:TESTCE")
    pe = premium("PE_BUY", "NSE:TESTPE")

    paths, captured = patch_cycle_io(
        monkeypatch,
        tmp_path,
        index_candles(),
        [ce, pe],
        {"status": "FLAT", "paper_only": True},
    )

    monkeypatch.setattr(
        s,
        "evaluate_active_smc_candidate",
        lambda *args, **kwargs: s.SignalDecision(
            signal_generated=True,
            pe_reason=(
                "SMC_DECISION=LONG;"
                "OPTION_SIDE=CE_BUY;"
                "ER20_OK(0.5000)"
            ),
            entry=100.0,
            stop_loss=60.0,
            target=220.0,
            er20=0.5,
            dte=6,
            ltp=100.0,
        ),
    )

    summary = s.run_one_cycle(paths, NOW)
    saved = captured["position.json"]

    assert summary["event"] == "POSITION_OPENED"
    assert saved["side"] == "CE_BUY"
    assert saved["option_symbol"] == "NSE:TESTCE"
    assert saved["candidate"] == s.ACTIVE_SMC_CANDIDATE["name"]


def test_closed_position_preserves_ce_side_and_symbol():
    state = {
        "status": "OPEN",
        "side": "CE_BUY",
        "option_symbol": "NSE:TESTCE",
        "entry": 100.0,
        "stop_loss": 60.0,
        "target": 120.0,
        "quantity": 1,
    }

    closed, event = s.evaluate_open_position(
        state,
        premium(
            "CE_BUY",
            "NSE:TESTCE",
            high=125.0,
            low=95.0,
            close=122.0,
        ),
        NOW,
    )

    assert event["event"] == "POSITION_CLOSED"
    assert event["side"] == "CE_BUY"
    assert event["option_symbol"] == "NSE:TESTCE"
    assert closed["last_closed_side"] == "CE_BUY"
    assert event["paper_pnl"] == 20.0



def test_legacy_unlabelled_premium_stream_uses_latest_candle():
    first = premium("", "", close=100.0)
    second = premium("", "", close=120.0)

    selected = s.select_position_premium_candle(
        [first, second],
        {"side": "PE_BUY", "option_symbol": ""},
    )

    assert selected is second
