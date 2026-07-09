# HQE Customer User Guide

## What HQE App does

HQE App is a paper-only/data-only validation app. It does not place real orders, does not execute broker trades, and does not auto-trade.

## Install on customer PC

1. Copy or clone the HQE folder to the PC.
2. Open PowerShell as normal user.
3. Run:

```powershell
Set-Location "D:\Hunter_Quant_Engine_PC_TRANSFER"
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\INSTALL_HQE_PRODUCT_APP_NEW_PC.ps1
```

4. Desktop will show one icon: **HQE App**.
5. Open HQE App.
6. Copy Machine ID and send it to the owner.
7. Paste owner-provided User/License Key into the app.
8. Click Activate / Login.

## Daily paper validation flow

1. Open **HQE App** desktop icon.
2. Step 1: Refresh Fyers Token.
3. Step 2: Historical 5m Data-Only Test.
4. Step 3: Start Paper Watch 09:15-15:30.
5. Keep watch CMD open during market time.
6. Step 4: Run Daily Report Pack after market.
7. Open Daily Report.

## Safety rules

- Real money: NO
- Real orders: NO
- Broker execution: NO
- Auto trading: NO
- Fake trades: NO
- No profitability claim
