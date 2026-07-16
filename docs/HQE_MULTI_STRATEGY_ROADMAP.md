<!-- HQE_MULTI_STRATEGY_ROADMAP_V1 -->
# HQE Multi-Strategy Roadmap

## 1. Frozen working baseline

The current Hunter Quant Engine release is a verified, working, paper-only
baseline. It must remain usable while the multi-strategy layer is developed.

Baseline release:

- Branch: `master`
- Verified release HEAD: `c5704aa`
- Full regression: `3200 passed, 0 failed`
- Release and freeze gates: PASS
- Repository state at release: clean
- Product mode: PAPER ONLY / DATA ONLY / RESEARCH ONLY
- Real orders: disabled
- Broker execution: disabled
- Auto trading: disabled
- Real money: disabled
- Current canonical paper lifecycle: working
- CE BUY / PE BUY display: working
- OPEN / HELD / CLOSED lifecycle: working
- Entry, stop loss, target and latest option price: working
- Unrealized and realized paper P&L: working
- Ledger/history and restart recovery: working
- Product UI, Today Report, duplicate-start guard and hidden runtime: working

## 2. Problem being solved

HQE was created to evaluate many strategies through historical backtesting and
forward paper testing. The current product runtime is connected to one selected
locked candidate. That connection is a verified baseline, but it must not become
a permanent single-strategy architecture.

The next core path is to add a general multi-strategy system without breaking or
rewriting the working paper-trading release.

## 3. Non-negotiable invariants

1. Do not break or casually rewrite the release at `c5704aa`.
2. The current strategy must continue working through a compatibility adapter.
3. A strategy used in backtest and forward paper test must use the same strategy
   implementation and parameters.
4. A new strategy must not require edits throughout the HQE core.
5. Every strategy must be validated before it can be selected or started.
6. State, ledger, reports, P&L and restart recovery must be isolated per strategy.
7. No strategy may enable real orders, broker execution, auto trading or real
   money.
8. No commit or push is allowed until automated tests pass, visual checks pass,
   and the user explicitly says `ok commit`.
9. PowerShell scripts must not ask interactive questions. Ask the user in chat.
10. Side questions must be answered, then work must return to this roadmap.

## 4. Target architecture

### 4.1 Strategy contract

Create one versioned strategy interface/schema covering:

- strategy ID
- display name
- strategy version
- description
- supported instruments
- required timeframe
- required data columns
- parameter schema and defaults
- warm-up requirement
- signal output
- entry eligibility
- stop-loss rule
- target rule
- time/EOD exit rule
- state serialization version
- compatibility requirements

Canonical signal output must remain explicit and deterministic:

- `LONG`
- `SHORT`
- `NEUTRAL`

The option mapping layer may translate this to:

- `LONG -> CE_BUY`
- `SHORT -> PE_BUY`
- `NEUTRAL -> NO_TRADE`

### 4.2 Strategy registry

Add a central registry that:

- discovers registered strategies
- rejects duplicate IDs
- validates metadata and parameters
- reports load/import errors clearly
- exposes strategies to backtest, forward paper runtime and UI
- does not execute arbitrary untrusted code silently

### 4.3 Import/package format

Define a safe, versioned strategy package format. The first version should
prefer a local, reviewable package rather than unrestricted dynamic code
execution.

Minimum package contents:

- strategy manifest
- strategy implementation
- parameter schema
- optional documentation
- deterministic tests or examples
- package checksum/version information

### 4.4 Backtest and forward-test parity

Create one execution adapter so the exact same strategy logic is called by:

- historical backtest
- recorded replay
- forward paper test
- product paper runtime

The engine must record:

- strategy ID and version
- parameter snapshot
- data identity/time range
- signal reason
- entry/exit reason
- execution-mode identity
- result/ledger paths

### 4.5 Current strategy compatibility adapter

Do not delete the current locked candidate.

Wrap it as the first registered strategy and prove:

- its previous decisions remain compatible
- its paper lifecycle remains compatible
- its current ledger/state can still be read
- existing users do not lose the working strategy

### 4.6 Strategy selection in UI

Add a Strategy area that shows:

- available strategies
- selected strategy
- strategy version
- parameters
- validation status
- active/inactive status
- backtest result shortcut
- forward paper-test status

The user must be able to select the strategy intentionally. The runtime must
never silently switch strategy while a paper position is open.

### 4.7 Single and parallel test modes

Implement in stages:

**Stage A - one active strategy**

- one selected strategy may drive the canonical product paper position
- simplest and safest first milestone

**Stage B - parallel isolated paper tests**

- multiple strategies may be observed simultaneously
- every strategy gets its own state, ledger, report and P&L namespace
- one strategy cannot close or overwrite another strategy's position
- aggregate UI is read-only and clearly separated

### 4.8 Storage layout

Use per-strategy namespacing similar to:

```text
HQE_PAPER_PRODUCT_RUNTIME/
  strategies/
    <strategy_id>/
      <strategy_version>/
        state.json
        ledger.csv
        runtime.json
        report.md
        reason_log.csv
```

Migration must preserve the current runtime state and ledger.

### 4.9 Reliability and safety tests

Required test groups:

- registry discovery
- schema validation
- duplicate-ID rejection
- invalid package rejection
- parameter validation
- backtest/forward signal parity
- current-strategy compatibility
- state isolation
- ledger isolation
- restart recovery per strategy
- duplicate runtime protection
- no visible CMD window
- UI selection and reporting
- corrupt-state recovery
- no real-order/broker/auto-trading paths
- complete regression
- release/freeze gates

## 5. Development phases

### Phase 0 - Read-only audit

- Read README, schema, roadmap, vision, current status and release documents from
  the beginning.
- Map current backtest strategy interfaces and current paper-runtime interfaces.
- Produce an architecture proposal and file-impact map.
- Make no source changes.

### Phase 1 - Contract and registry design

- Define the strategy manifest/schema.
- Define the Python protocol/base contract.
- Define validation errors and versioning.
- Add tests before connecting the runtime.

### Phase 2 - Current strategy adapter

- Register the existing locked candidate through the new contract.
- Prove output compatibility.
- Keep the existing product behavior unchanged.

### Phase 3 - Backtest integration

- Route registered strategies through the existing backtest engine.
- Preserve existing reports and add strategy identity metadata.

### Phase 4 - Forward paper integration

- Route the selected registered strategy through the canonical paper lifecycle.
- Add per-strategy state and ledger paths.
- Preserve restart recovery and safety locks.

### Phase 5 - UI strategy manager

- Add strategy list, selected strategy, validation state and parameters.
- Add explicit change protection when a position is open.
- Keep unrelated UI unchanged.

### Phase 6 - Import workflow

- Add package selection, validation and review.
- Do not auto-activate imported strategies.
- Show exact errors without modifying the working registry on failure.

### Phase 7 - Parallel isolated paper tests

- Add multi-strategy paper observation after single-strategy selection is stable.
- Isolate all state, ledger and P&L.

### Phase 8 - Release closure

- Targeted tests PASS.
- Full regression PASS with zero failures.
- Visual acceptance PASS.
- Freeze manifest refresh.
- User says `ok commit`.
- Commit and push only after all gates pass.

## 6. Definition of done

Multi-strategy work is complete only when:

- a second independent strategy can be added without rewriting HQE core
- both strategies can be backtested through the common contract
- the selected strategy can be forward paper tested
- strategy identity and parameters are visible in reports
- the current strategy remains compatible
- per-strategy state, ledger and P&L are isolated
- restart recovery works
- invalid imports cannot damage the registry
- UI selection works without glitches
- no real-order path is enabled
- full regression and release gates pass
- documentation and handover are updated

## 7. Explicitly out of scope

Until separately approved:

- real-money trading
- broker order execution
- automatic live order placement
- option selling
- unrelated UI redesign
- replacing the existing backtest engine
- deleting the current working strategy
- changing license identity behavior
