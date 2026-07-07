# HQE Live Readiness Gate

The live-readiness gate checks whether paper evidence is strong enough to start
live-readiness engineering.

It is not live trading.

It does not enable real money.
It does not enable broker execution.
It does not use live market data.
It does not claim profitability.

## Required Local Workflow

Run:

    .\hqe_paper_mvp_operator_demo.bat
    .\hqe_paper_evidence_aggregate.bat
    .\hqe_live_readiness_check.bat

The live-readiness check reads:

    reports\paper_trading\evidence_aggregate\aggregate.json

It writes:

    reports\paper_trading\live_readiness\live_readiness.json
    reports\paper_trading\live_readiness\live_readiness.txt
    reports\paper_trading\live_readiness\manifest.json

## Blocking Reasons

The gate blocks live-readiness engineering when:

- paper evidence aggregate is missing
- paper evidence aggregate failed its gates
- evidence report count is below the minimum
- closed trades are below the minimum
- open positions remain above the maximum
- unknown trades exceed the maximum
- simulated net PnL fails a configured threshold
- safety documentation is missing required safety text

## Meaning of Pass

A pass means only:

    live-readiness engineering may start

It does not mean:

- live trading is approved
- broker execution is enabled
- real money is enabled
- the strategy is profitable

## Next Phase

After this gate passes, the next phase can add live-readiness engineering
scaffolding behind disabled-by-default safety flags.
