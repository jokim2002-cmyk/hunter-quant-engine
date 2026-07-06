"""Run the safe local paper trading demo example.

The implementation lives in src.paper_trading.paper_trading_demo_cli so it can
also be run as a module command:

    python -m src.paper_trading.paper_trading_demo_cli

No broker SDK. No broker platform integration. No live/real market data.
No real orders are placed. Not a profitability claim.
"""

from __future__ import annotations

from src.paper_trading.paper_trading_demo_cli import main, run_demo


if __name__ == "__main__":
    raise SystemExit(main())
