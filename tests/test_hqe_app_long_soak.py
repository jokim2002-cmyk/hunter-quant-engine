from __future__ import annotations

import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SOAK = REPO / "scripts" / "hqe_app_long_soak.py"


def load_module():
    spec = importlib.util.spec_from_file_location("hqe_app_long_soak", SOAK)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_soak_runner_has_safe_defaults():
    module = load_module()
    parser = module.build_parser()
    args = parser.parse_args([])
    assert args.minutes == 5.0
    assert args.sample_seconds == 15.0


def test_soak_payload_hard_codes_no_execution(monkeypatch, tmp_path):
    module = load_module()

    class FakeProcess:
        pid = 12345
        def poll(self):
            return None
        def terminate(self):
            return None
        def wait(self, timeout=None):
            return 0

    monkeypatch.setattr(module.subprocess, "Popen", lambda *a, **k: FakeProcess())
    monkeypatch.setattr(module.time, "sleep", lambda *_a, **_k: None)
    monkeypatch.setattr(module, "process_snapshot", lambda _pid: {
        "pid": 12345,
        "responding": True,
        "working_set_bytes": 100_000_000,
        "handle_count": 50,
    })
    monkeypatch.setattr(module, "run_check", lambda *_a, **_k: {
        "returncode": 0,
        "stdout": "paper_only no_real_orders no_broker_execution no_auto_trading",
        "stderr": "",
    })

    ticks = iter([0.0, 0.0, 2.0, 2.0])
    monkeypatch.setattr(module.time, "monotonic", lambda: next(ticks, 2.0))

    payload = module.run_soak(0.01, 1.0, tmp_path)
    assert payload["status"] == "PASS"
    assert payload["real_order_invoked"] is False
    assert payload["broker_execution_invoked"] is False
    assert payload["auto_trading_invoked"] is False


def test_memory_ceiling_is_conservative():
    text = SOAK.read_text(encoding="utf-8-sig")
    assert "1_500_000_000" in text
    assert "--skip-license-check" in text
