# HQE Owner Seller Guide

## Owner key model

Your private owner key stays only with you:

```text
D:\HQE_PRODUCT_LICENSE_OWNER\hqe_owner_private_key.json
```

Customer app receives only the public verify key. Do not send private key to customers.

## First-time owner setup

```powershell
Set-Location "D:\Hunter_Quant_Engine_PC_TRANSFER"
.\.venv\Scripts\python.exe scripts\hqe_owner_license_generator.py --init-owner-keys --install-public-key-to-workspace "D:\HQE_BACKTEST_RUNS\HQE_FORWARD_PAPER_VALIDATION_ACTIVE_20260708_204722"
```

## Generate customer license

Ask customer to open HQE App and send Machine ID.

Then generate license:

```powershell
.\.venv\Scripts\python.exe scripts\hqe_owner_license_generator.py --customer-name "Customer Name" --customer-email "customer@example.com" --machine-id "HQE-PASTE-MACHINE-ID" --expires-on "2027-12-31" --output "D:\HQE_PRODUCT_LICENSE_OWNER\licenses\customer.key"
```

Send only the generated `.key` content to the customer.

## Create release zip

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\PACK_HQE_CUSTOMER_RELEASE_ZIP.ps1
```

## Important

Offline licensing can be bypassed by advanced attackers. Stronger licensing requires an online license server later.
