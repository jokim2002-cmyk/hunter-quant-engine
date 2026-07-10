# HQE App V2 Silent Launch and Installer Final Freeze

## Purpose

This pack closes the owner-installer workflow with:

- hidden CMD launch through Windows Script Host,
- desktop shortcut targeting the silent launcher,
- uninstall/reinstall evidence requirements,
- final installer freeze gate,
- safety-lock verification.

## Required final smoke

1. Install the versioned owner package.
2. Launch from the desktop shortcut.
3. Confirm the app opens without a visible CMD window.
4. Start and stop Paper Watch.
5. Uninstall.
6. Confirm shortcut and install folder are removed.
7. Reinstall.
8. Repeat launch and Paper Watch smoke.
9. Run the final freeze gate.

## Safety

- Real money: NO
- Real orders: NO
- Broker execution: NO
- Auto trading: NO

This is not a profitability claim.
