# HQE Construction Flow and Chat Handover Standard

## Purpose

This file prevents chat overload, context loss, and random development.

Every new chat should begin from this file plus the master vision and roadmap.

---

## Required files to keep updated

The repo must maintain:

- `docs/HQE_MASTER_PRODUCT_VISION.md`
- `docs/HQE_MASTER_PRODUCT_ROADMAP.md`
- `docs/HQE_CONSTRUCTION_FLOW_AND_CHAT_HANDOVER.md`
- `docs/HQE_CURRENT_STATUS.md`

If the chat becomes overloaded, paste only the latest **HQE_CURRENT_STATUS.md** summary into the next chat.

---

## How each build should work

Every development batch must follow this order:

1. Confirm roadmap phase.
2. Confirm exact objective.
3. Build only the required files.
4. Run tests.
5. Run safe smoke command.
6. Commit.
7. Push separately.
8. Update `docs/HQE_CURRENT_STATUS.md`.
9. Tell user:
   - What completed
   - What changed
   - What to test
   - Next roadmap step

---

## Commands style for user

The user is a trader, not a coder.

Always provide:

- Copy-paste PowerShell
- Use repo path: `D:\Hunter_Quant_Engine_PC_TRANSFER`
- Use venv: `.\.venv\Scripts\python.exe`
- Never use plain `python`
- Keep `git push` in a separate final block
- Do not ask user to paste huge terminal output
- Ask for only final 10-20 lines if needed

---

## Safety style

Always repeat safety status when relevant:

- Paper-only unless future unlocked phase
- Data-only unless clearly in execution phase
- No real orders
- No broker execution
- No auto trading
- No fake trades
- No profitability claim

---

## What not to do

Do not build:

- Random polish unrelated to product
- Extra modules only to increase module count
- Real order logic before risk/compliance gateway
- Broker execution hidden behind app
- Strategy tuning during validation
- Confusing technical UI for traders
- CMD-based public workflows after App V2 phase

---

## Chat handover prompt template

Use this at the start of a new chat:

```text
We are building HQE as a simple retail-trader product, not a developer script tool.

Repo: D:\Hunter_Quant_Engine_PC_TRANSFER
Venv: .\.venv\Scripts\python.exe
Workspace: D:\HQE_BACKTEST_RUNS\HQE_FORWARD_PAPER_VALIDATION_ACTIVE_20260708_204722

Read these project files first:
docs\HQE_MASTER_PRODUCT_VISION.md
docs\HQE_MASTER_PRODUCT_ROADMAP.md
docs\HQE_CONSTRUCTION_FLOW_AND_CHAT_HANDOVER.md
docs\HQE_CURRENT_STATUS.md

Current rule:
No random modules.
Only roadmap-based work.
No CMD/PowerShell in final public daily use.
Real trading remains locked.
Paper/data safety must stay on.

User wants Hinglish/Roman Hindi, practical copy-paste commands, and git push separately.
```

---

## Current status file format

`docs/HQE_CURRENT_STATUS.md` must contain:

- Latest commit
- Current module count
- Current roadmap phase
- Current completed work
- Current limitation
- Next build target
- Safety status
- Commands last used
- What user should test next

---

## Next build target after this document

**HQE App V2 Public Trader UI + Multi-Broker Architecture Pack**

Goal:

- No CMD visible in daily use
- Modern simple app
- Broker connect UI
- Internet/broker/data status cards
- App-based paper watch
- App-based report viewer
- Simple trader language
