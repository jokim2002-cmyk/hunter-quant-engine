# Hunter Quant Engine (HQE)

# Decision Log

This document records the major architectural decisions made during the development of Hunter Quant Engine (HQE).

The purpose of this log is to preserve the reasoning behind important decisions so future development remains consistent.

---

# Decision #001

## Use list position as candle index

### Decision

Detection engines currently use the candle's position in the input list as its index.

### Reason

- Simple
- Efficient
- Easy to understand
- No additional storage required

### Future

A dedicated `Candle.sequence` field may be introduced if required.

Status:

**Deferred**

---

# Decision #002

## Detection engines are stateless

### Decision

Every detection engine must be stateless.

### Reason

Stateless engines are:

- Easier to test
- Easier to reuse
- Deterministic
- Thread-safe
- Independent

Engine contract:

```python
events = engine.detect(...)
```

---

# Decision #003

## Market events are immutable

### Decision

All market events are immutable.

### Reason

Market history cannot change.

If market conditions change, a new event is created instead of modifying an existing one.

Implementation:

```python
@dataclass(frozen=True)
```

---

# Decision #004

## Detection logic is configuration-driven

### Decision

Detection parameters belong inside Config classes.

### Reason

Avoid hardcoded business rules.

Benefits:

- Easier testing
- Better maintainability
- Strategy independence

---

# Decision #005

## Liquidity Sweep stores analytical information

### Decision

LiquiditySweep includes:

- break_distance
- reclaimed

### Reason

Although not required for detection, these fields will be useful for:

- Strategy Engine
- Analytics
- AI Decision Engine

---

# Decision #006

## Official project name

### Decision

The official project name is:

# Hunter Quant Engine (HQE)

### Reason

The framework has evolved beyond an AI trading experiment.

HQE better reflects its purpose as a professional quantitative trading framework.

---

# Decision #007

## Independent event models

### Decision

Do not introduce a BaseEvent abstraction.

### Reason

Current event models are:

- Explicit
- Independent
- Easy to understand
- Low coupling
- Easy to test

A shared base class will only be introduced if it provides a clear architectural benefit.

Status:

**Deferred**

---

# Decision #008

## Reduce future complexity

### Decision

Every architectural decision must reduce future complexity rather than current effort.

### Reason

Short-term convenience should never compromise long-term maintainability.

When choosing between two designs, prefer the one that keeps the framework simpler over time.

---

# Decision #009

## Documentation reflects implementation

### Decision

Documentation must describe the architecture as implemented.

### Reason

Documentation should never describe planned or imagined behavior.

Whenever implementation changes, documentation must be updated accordingly.

---

# Decision Principles

Every future architectural decision should satisfy these questions:

- Does it reduce complexity?
- Does it improve maintainability?
- Is it reusable?
- Is it testable?
- Is it consistent with HQE philosophy?
- Does it avoid unnecessary coupling?

If the answer is "No", the change should be reconsidered.

---

# Guiding Philosophy

> **Discipline before Speed. Architecture before Features. Quality before Shortcuts.**