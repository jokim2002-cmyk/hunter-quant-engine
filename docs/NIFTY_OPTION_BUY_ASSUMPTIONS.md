# NIFTY Option-Buy Assumptions

This document locks the first execution direction for Hunter Quant Engine.

HQE first execution module is a dynamic NIFTY option-buy planning engine.

This document must be updated before code changes whenever the option-buy assumptions change.

---

## 1. Binding Direction

HQE first module is option-buy only.

Allowed:

- Bullish NIFTY signal -> Call / CE buy planning.
- Bearish NIFTY signal -> Put / PE buy planning.

Not allowed in the first module:

- Option selling.
- Short CE.
- Short PE.
- Futures execution.
- Equity execution.
- Fixed ATM-only strategy assumption.
- Fake profitability claims before option premium backtesting.

---

## 2. Signal Source

Signal source:

- NIFTY spot/index candles.

The underlying signal engine may use:

- SMC.
- Future strategy modules.
- Trend filters.
- Momentum filters.
- Volatility filters.

Current first strategy layer:

- SMC: Smart Money Concepts.

Current SMC benchmark results are underlying signal research only.

They are not final NIFTY option-buy profitability results.

---

## 3. Execution Target

Execution target:

- NIFTY options.

Allowed execution actions:

- Buy CE.
- Buy PE.

No option selling is allowed in the first module.

---

## 4. Lot Size

Current known lot size:

- 1 lot = 65 quantity.

The lot size must be configurable because exchange lot sizes can change.

No hardcoded lot-size assumptions should enter core logic without tests.

---

## 5. Intraday Scope

First module scope:

- Intraday option-buy planning.
- Intraday option-buy backtesting.
- Intraday risk controls.

Overnight holding is out of scope for the first module unless explicitly added later.

---

## 6. Dynamic Strike Selection

HQE must not be a fixed ATM option buyer.

For every valid NIFTY bullish or bearish signal, HQE should scan eligible option contracts and select a contract dynamically.

Possible strike-selection inputs:

- NIFTY spot price.
- CE or PE side based on signal direction.
- Strike distance from spot.
- Option premium.
- OI.
- Volume.
- Bid-ask spread.
- Liquidity.
- Delta.
- Theta.
- Vega.
- Gamma.
- Risk-reward.
- Expiry.
- Charges after estimated entry and exit.

The selected strike must include a clear reason.

Rejected strikes must include clear rejection reasons.

---

## 7. Direction Mapping

Bullish signal:

- Scan CE contracts.
- Choose best CE candidate.
- Build CE buy trade plan.

Bearish signal:

- Scan PE contracts.
- Choose best PE candidate.
- Build PE buy trade plan.

Neutral signal:

- No option trade plan.

Conflicting signal:

- No option trade plan unless a future conflict-resolution rule is explicitly added and tested.

---

## 8. Option Chain Checks

The option-buy planner should eventually check:

- OI.
- Volume.
- Bid price.
- Ask price.
- Spread.
- Last traded premium.
- IV when available.
- Greeks when available or calculated.
- Expiry.
- Strike distance.
- Premium range.

Contracts with weak liquidity should be rejected.

---

## 9. Greeks Checks

The first option-buy module should support Greeks checks:

- Delta.
- Theta.
- Vega.
- Gamma.

Pending configurable rules:

- Minimum Delta.
- Maximum Delta.
- Maximum Theta risk.
- Maximum spread.
- Minimum volume.
- Minimum OI.
- Maximum premium.
- Minimum premium.
- Maximum expiry risk.

No fake precision is allowed.

If IV or Greeks data is missing, the planner must clearly mark the data as missing instead of pretending it was checked.

---

## 10. Risk-Reward

The option-buy trade plan must check risk-reward before approving a plan.

Risk-reward should be calculated on option premium, not NIFTY spot points.

The plan should include:

- Entry premium.
- SL premium.
- Target premium.
- Gross risk.
- Gross reward.
- Estimated charges.
- Net risk-reward estimate.
- Lot size.
- Quantity.
- Maximum loss.
- Reason for approval or rejection.

---

## 11. SL and Target

SL and target must be option-premium based for final option-buy backtesting.

Possible future methods:

- Premium percentage SL.
- Premium structure-based SL.
- Underlying invalidation mapped to option premium.
- Time-based exit.
- Trailing SL.

Until option premium data exists, final option-buy profitability must not be claimed.

---

## 12. Charges

NIFTY option-buy results must use a FYERS NIFTY options intraday cost profile.

Required charge components:

- Brokerage.
- STT/CTT on sell-side premium.
- Exchange transaction charges.
- Clearing charges when applicable.
- SEBI charges.
- Stamp duty on buy-side premium.
- GST on applicable charges.
- Total charges.

Equity-intraday charges must not be used for final NIFTY options results.

---

## 13. Backtesting Requirement

Final option-buy profitability requires historical option premium data.

Required data:

- Option contract.
- Expiry.
- Strike.
- CE/PE type.
- Timestamp.
- Open premium.
- High premium.
- Low premium.
- Close premium.
- Volume.
- OI when available.

NIFTY spot/index data alone is not enough to claim option-buy profitability.

---

## 14. Output Trade Plan

A final option-buy trade plan should include:

- Signal timestamp.
- Underlying symbol.
- Underlying price.
- Signal direction.
- Option type: CE or PE.
- Action: BUY.
- Expiry.
- Strike.
- Entry premium.
- SL premium.
- Target premium.
- Lot size.
- Quantity.
- Estimated charges.
- Estimated max loss.
- Estimated net reward.
- Risk-reward.
- Approval status.
- Rejection reasons.
- Strategy reason.

---

## 15. Current HQE Status

Completed foundation:

- NIFTY underlying data workflow.
- SMC signal engine.
- Strict/Balanced/Relaxed modes.
- Benchmark runner.
- Progress timing.
- Max-candles safety control.
- Date-range safety control.
- Docs correction for NIFTY option-buy direction.

Current limitation:

- HQE does not yet have the final option-buy execution module.
- Current SMC mode benchmarks are underlying signal research only.

---

## 16. Next Engineering Steps

Immediate next steps:

1. Option contract models.
2. Option chain snapshot models.
3. FYERS NIFTY options charge profile.
4. Dynamic strike selection engine.
5. OI / volume / liquidity filters.
6. Greeks model and checks.
7. Option-buy trade plan model.
8. Option premium backtest engine.

---

## 17. Non-Negotiable Reminder

No final NIFTY option-buy profitability claim is allowed until:

- Option premium data is used.
- CE/PE buy execution is modeled.
- FYERS options charges are applied.
- Tests pass.
- Git is clean.

