# Hunter Quant Engine (HQE)

# Coding Standards

> Good architecture is created by good engineering habits.

---

# Purpose

This document defines the coding standards used throughout Hunter Quant Engine (HQE).

Every source file should follow these standards to ensure consistency, readability, maintainability, and long-term stability.

---

# Core Principles

Every contribution to HQE must follow these principles:

- Architecture before features
- Quality before shortcuts
- Explicit is better than implicit
- Small, focused modules
- Single Responsibility Principle
- Stateless business logic
- Immutable market events
- Configuration-driven detection
- Test before trust

---

# Project Structure

Each major feature follows the same architecture.

```
Feature

↓

Enum

↓

Model

↓

Config

↓

Engine

↓

Model Tests

↓

Config Tests

↓

Engine Tests

↓

Integration

↓

Documentation
```

Do not skip layers unless they are genuinely unnecessary.

---

# Naming Conventions

## Files

Use lowercase snake_case.

Examples:

```
order_block.py
order_block_engine.py
order_block_config.py
```

---

## Classes

Use PascalCase.

Examples:

```
OrderBlock
OrderBlockEngine
LiquiditySweep
```

---

## Functions

Use snake_case.

Examples:

```
detect()

build()

create_order_block()
```

---

## Variables

Use descriptive names.

Prefer:

```
previous_candle
current_candle
liquidity_point
order_blocks
```

Avoid:

```
a
b
x
temp
obj
```

---

# Models

Models represent market facts.

Rules:

- Use dataclasses.
- Prefer immutable models.
- Never mutate events.
- Keep models simple.
- No business logic inside models.

Example:

```python
@dataclass(frozen=True)
class OrderBlock:
    ...
```

---

# Enums

Enums represent fixed domain concepts.

Examples:

- BOSDirection
- LiquidityType
- OrderBlockType

Never use raw strings when an Enum exists.

---

# Config Classes

All detection parameters belong in Config classes.

Avoid:

```python
if gap > 0.5:
```

Use:

```python
if gap > self.config.minimum_gap_size:
```

This makes behavior configurable and testable.

---

# Engines

Every engine must:

- Be stateless
- Detect only one concept
- Return immutable events
- Never cache state
- Never mutate inputs
- Never generate trade signals

Standard contract:

```python
events = engine.detect(...)
```

---

# Testing Standards

Every module requires tests.

At minimum:

- Model tests
- Config tests
- Engine tests

Tests should verify:

- Expected behavior
- Edge cases
- Empty inputs
- Disabled configurations
- Invalid scenarios

No feature is complete until its tests pass.

---

# Documentation

Documentation is part of the implementation.

Whenever architecture changes:

- Update documentation
- Update decision log if required

Documentation must reflect the current implementation.

---

# Code Style

Prefer readable code over clever code.

Good:

```python
if candle.is_bullish:
```

Avoid:

```python
if candle.close > candle.open:
```

when an existing property already expresses the intent.

Keep functions small and focused.

Avoid deep nesting.

Extract helper methods when logic grows.

---

# Dependency Rules

Modules should depend only on what they need.

Detection engines must not depend on:

- Strategy
- Backtesting
- AI
- Broker APIs

Maintain one-way dependencies.

---

# Git Workflow

Each completed feature should follow:

1. Implement
2. Test
3. Verify
4. Commit

Commit messages should be clear.

Examples:

```
Add Order Block foundation

Improve Liquidity Sweep detection

Refactor Equal Level engine
```

---

# HQE Philosophy

Every line of code should make the framework easier to understand, not harder.

When in doubt:

- Choose clarity.
- Choose simplicity.
- Choose maintainability.

---

# Final Principle

Code is temporary.

Architecture lasts.

Protect the architecture.