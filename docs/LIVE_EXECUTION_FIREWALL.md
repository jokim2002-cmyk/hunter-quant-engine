# HQE Live Execution Firewall

The live execution firewall is a deny-only scaffold for future live-readiness
order intents.

It is not live trading.

It does not enable real money.
It does not enable broker submission.
It does not enable live market data.
It does not enable real orders.
It does not claim profitability.

## Command

Run:

    .\scripts\paper_trading\hqe_live_execution_firewall_check.bat

The command writes:

    reports\paper_trading\live_execution_firewall\live_execution_firewall.json
    reports\paper_trading\live_execution_firewall\live_execution_firewall.txt
    reports\paper_trading\live_execution_firewall\manifest.json

## Default Policy

The default policy is deny-only:

- intent allowed is always false
- live trading approved is always false
- real money disabled
- broker submission disabled
- live market data disabled
- real orders disabled
- manual review required
- max single intent quantity set to 0

## Meaning of Pass

A pass means:

    the firewall stayed safely closed

A pass does not mean:

- live trading is approved
- real money is enabled
- broker submission is enabled
- live market data is enabled
- real orders are enabled
- the strategy is profitable

## Operator Rule

Any future change that can allow a real order intent must be a separate reviewed
module with explicit tests, documentation, rollback steps, and manual
acknowledgement.
