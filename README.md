# Hunter Quant Engine (HQE)

## Mission Statement

Build a production-grade, institutional-quality quantitative trading framework using clean architecture, professional engineering, rigorous testing, and explainable trading logic.

HQE is not a trading bot.

HQE is an event-driven quantitative trading framework designed to transform market data into immutable market events, strategy signals, and risk-approved trade plans.

---

## Project Motto

Engineer it right once. Improve it forever.

---

## Project Vision

Hunter Quant Engine is designed for long-term maintainability, extensibility, and institutional-quality trading research.

The goal is not to build a simple buy/sell script.

The goal is to build a modular, testable, scalable, and explainable framework that can support:

- Smart Money Concepts
- Market Structure
- Liquidity
- Equal High / Equal Low
- Liquidity Sweeps
- Fair Value Gaps
- Order Blocks
- Rule Composition
- Setup Validation
- Strategy Signal Generation
- Risk Management
- Trade Planning
- Backtesting
- Paper Trading
- Live Trading
- AI-based Decision Support
- Performance Analytics

---

## Current Architecture

```text
Market Data
    |
    vDetection Layer
    |
    v
Mmutable Market Events
    |
    v
StrategyContext
    |
    v
Reusable Rules
    |
    v
Rule Sets
    |
    v
Setup Validators
    |
    v
Strategies
    |
    v
TradeSignal
    |
    v
Risk Layer
    |
    v
TradePlan
    |
    v
Backtesting / Paper Trading / Live Trading
```

---

## Completed Layers

### Detection Layer

- Candle
- Swing Detection
- Market Structure
- BOS
- CHOCH
- Liquidity
- Equal High
- Equal Low
- Liquidity Clusters
- Liquidity Sweep
- Fair Value Gap
- Order Block

### Strategy Layer

- SignalType
- SignalStrength
- TradeSignal
- StrategyContext
- BaseStrategy
- BaseRule
- Market Structure Rules
- Liquidity Rules
- Fair Value Gap Rules
- Order Block Rules
- Rule Sets
- Setup Validators
- SMCStrategy

### Risk Layer

- RiskProfile
- TradePlan
- TradeLevels
- FixedRiskPositionSizer
- FixedRewardToRiskTradeLevelPlanner
- RiskManager

---

## Engineering Principles

- Architecture before features
- Quality before speed
- Immutable domain models
- Stateless engines
- Explicit contracts
- Test before trust
- Builders for test setup
- Documentation is part of development
- Refactor only when architecture becomes harder to understand

---

## Current Status

HQE currently supports:

- Immutable market event detection
- Strategy context construction
- Reusable event rules
- Rule composition
- SMC setup validation
- Deterministic SMC signal generation
- Fixed-risk trade planning

Current pipeline:

```text
Facts -> Evidence -> Validation -> Decision -> Risk Plan
```

---

## Next Major Milestone

The next major phase is:

```text
Backtesting Engine
```

The Backtesting Engine will consume strategy signals and risk-approved trade plans to simulate historical performance.

---

## Guiding Principle

Every release should improve quality without sacrificing simplicity.

