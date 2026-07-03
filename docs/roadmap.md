# Hunter Quant Engine (HQE)

# Roadmap

> This document tracks the long-term development plan for HQE.

---

# Vision

Hunter Quant Engine (HQE) aims to become a production-grade, event-driven quantitative trading framework designed for long-term maintainability, extensibility, and institutional-quality algorithmic trading.

HQE is not a trading bot.

Its purpose is to transform market data into reliable, reusable market events that can power multiple execution and analysis layers.

---

# Completed Foundations

## Core Models

- ✅ Candle
- ✅ SwingPoint
- ✅ MarketStructure
- ✅ BOSPoint
- ✅ CHOCHPoint
- ✅ LiquidityPoint
- ✅ EqualHighPoint
- ✅ EqualLowPoint
- ✅ LiquidityCluster
- ✅ FairValueGap
- ✅ LiquiditySweep
- ✅ OrderBlock

---

## Detection Engines

- ✅ Swing Detection
- ✅ Market Structure Builder
- ✅ BOS Engine
- ✅ CHOCH Engine
- ✅ Liquidity Engine
- ✅ Equal Level Engine
- ✅ Liquidity Cluster Engine
- ✅ Fair Value Gap Engine
- ✅ Liquidity Sweep Engine
- ✅ Order Block Engine

---

## Project Quality

- ✅ Stateless engines
- ✅ Immutable events
- ✅ Configuration-driven detection
- ✅ Comprehensive unit tests
- ✅ Architecture documentation

---

# Current Milestone

## HQE v0.6 Foundation Complete

Current status:

- Stable architecture
- Clean repository
- Complete documentation foundation
- Detection layer established

---

# Next Milestones

## HQE v0.7

Strategy Layer

Planned work:

- Strategy interfaces
- Event consumers
- Signal generation
- Strategy configuration

---

## HQE v0.8

Backtesting Engine

Planned work:

- Historical replay
- Position management
- Performance metrics
- Trade history

---

## HQE v0.9

Paper Trading

Planned work:

- Virtual execution
- Portfolio tracking
- Risk monitoring

---

## HQE v1.0

Live Trading

Planned work:

- Broker integration
- Order management
- Execution monitoring
- Logging

---

## HQE v2.0

AI Decision Layer

Possible capabilities:

- Event scoring
- Probability estimation
- Adaptive risk management
- Position sizing
- Strategy optimization

AI will consume market events.

AI will not replace deterministic detection engines.

---

# Long-Term Goals

HQE should become:

- Modular
- Extensible
- Well documented
- Highly testable
- Easy to maintain
- Suitable for long-term quantitative research

---

# Guiding Principle

> Every release should improve quality without sacrificing simplicity.