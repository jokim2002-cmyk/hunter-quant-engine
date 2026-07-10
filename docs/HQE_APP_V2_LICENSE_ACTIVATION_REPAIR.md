# HQE App V2 License Activation Repair

## Problem

App V2 exited with `machine_id_mismatch` because the stored license belonged to
a different PC identity.

## Repair

- App V2 now opens a license activation screen instead of silently closing.
- The current Machine ID is displayed and can be copied.
- A new machine-bound license key can be pasted and validated.
- The license is saved only after cryptographic validation succeeds.
- No license bypass was added.

## Safety

- Real money: NO
- Real orders: NO
- Broker execution: NO
- Auto trading: NO

This is not a profitability claim.
