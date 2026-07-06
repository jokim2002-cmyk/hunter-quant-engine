"""Run the safe local paper trading demo example.

The implementation lives in src.paper_trading.paper_trading_demo_cli so it can
also be run as a module command:

    python -m src.paper_trading.paper_trading_demo_cli

No broker SDK. No broker platform integration. No live/real market data.
No real orders are placed. Not a profitability claim.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.paper_trading.paper_trading_demo_cli import main, run_demo


if __name__ == "__main__":
    raise SystemExit(main())
