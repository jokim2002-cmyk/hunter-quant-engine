# Hunter Quant Engine (HQE)

> **Discipline before Speed. Architecture before Features. Quality before Shortcuts.**

---

# Overview

Hunter Quant Engine (HQE) is a production-grade, event-driven quantitative trading framework.

HQE is **not a trading bot**.

Its purpose is to transform raw market data into immutable market events that can later be consumed by strategy, backtesting, paper trading, live trading, and AI components.

The framework is designed with long-term maintainability as the highest priority.

---

# Design Philosophy

HQE follows these principles:

- Architecture First
- Quality Over Speed
- Stateless Detection Engines
- Immutable Market Events
- Configuration Driven Detection
- Independent, Reusable Components
- Test Before Trust
- Documentation is Part of Development

---

# High-Level Architecture

```
Market Data

    │

    ▼

Candles

    │

    ▼

Swing Detection

    │

    ▼

Market Structure

    │

    ▼

BOS

    │

    ▼

CHOCH

    │

    ▼

Liquidity

    │

    ▼

Equal Levels

    │

    ▼

Liquidity Clusters

    │

    ▼

Liquidity Sweep

    │

    ▼

Fair Value Gap

    │

    ▼

Order Block

    │

    ▼

Strategy Engine

    │

    ▼

Backtesting

    │

    ▼

Paper Trading

    │

    ▼

Live Trading

    │

    ▼

AI Decision Engine
```

---

# Detection Pipeline

Every detection engine receives immutable input data.

Each engine detects one market concept only.

Each engine returns immutable events.

Example:

```
candles

↓

SwingDetectionEngine.detect()

↓

SwingPoint events

↓

MarketStructureBuilder.build()

↓

MarketStructure

↓

BOSEngine.detect()

↓

BOS events
```

This pattern is followed throughout HQE.

---

# Detection Engine Rules

Every engine must:

- Be stateless
- Detect only one concept
- Return immutable events
- Never cache previous state
- Never make trading decisions
- Never mutate input objects

Engine contract:

```python
events = engine.detect(...)
```

---

# Market Events

HQE treats every detected structure as a market fact.

Examples:

- Swing Point
- BOS
- CHOCH
- Liquidity
- Equal Level
- Liquidity Cluster
- Liquidity Sweep
- Fair Value Gap
- Order Block

Market events never change after creation.

If market conditions change, a new event is created.

---

# Configuration Philosophy

Detection logic is configuration-driven.

Avoid:

```python
if gap_size > 0.5:
```

Instead:

```python
if gap_size > self.config.minimum_gap_size:
```

Business rules belong inside Config classes.

---

# Project Goals

HQE is designed to be:

- Modular
- Extensible
- Testable
- Readable
- Maintainable
- Production Ready

The framework should remain understandable and maintainable for the next 10–20 years.

---

# Current Status

Completed foundations:

- Candle
- Swing Detection
- Market Structure
- BOS
- CHOCH
- Liquidity
- Equal Levels
- Liquidity Clusters
- Liquidity Sweep
- Fair Value Gap
- Order Block

Current status:

- Stateless engines
- Immutable events
- Configuration-driven detection
- Comprehensive unit tests

---

# Future Layers

The next stages of HQE are:

- Strategy Engine
- Backtesting
- Paper Trading
- Live Trading
- AI Decision Engine

These layers will consume market events produced by the detection engines.

Detection engines will remain completely independent from execution logic.

---

# Conclusion

HQE is built on one guiding principle:

> **Discipline before Speed. Architecture before Features. Quality before Shortcuts.**