# Paper Tuning Candidate Readiness Pack

This pack defines safe future paper-only tuning candidate lanes from recorded backtest result review and assumption risk review evidence.

It does not change strategy logic and does not run optimization.

Candidate lanes include:

- option reference pricing reality check
- slippage and cost sensitivity
- signal cooldown and duplicate filter review
- exit rule sensitivity
- session and trade frequency filter review
- multi-dataset replay validation
- drawdown guardrail review

Safety scope:

- Paper/simulation only.
- No broker connection.
- No live market data request.
- No real orders.
- No real money.
- No profitability proof.
- No live trading approval.
- No strategy logic change in this pack.
- No optimization execution in this pack.

Shortcut:

.\scripts\paper_trading\hqe_paper_tuning_candidate_readiness_pack.bat
