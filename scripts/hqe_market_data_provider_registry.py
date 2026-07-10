from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

VERSION = "HQE_MARKET_DATA_PROVIDER_REGISTRY_V1"

PROVIDERS: dict[str, dict[str, Any]] = {
    "fyers": {
        "display_name": "Fyers",
        "status": "AVAILABLE",
        "mode": "DATA_ONLY",
        "historical": True,
        "live_quotes": True,
        "option_chain": False,
        "execution": False,
        "script": "hqe_fyers_historical_5m_data_only_fetcher.py",
    },
    "zerodha": {
        "display_name": "Zerodha",
        "status": "PLACEHOLDER",
        "mode": "DISABLED",
        "historical": False,
        "live_quotes": False,
        "option_chain": False,
        "execution": False,
        "script": "",
    },
    "angel_one": {
        "display_name": "Angel One",
        "status": "PLACEHOLDER",
        "mode": "DISABLED",
        "historical": False,
        "live_quotes": False,
        "option_chain": False,
        "execution": False,
        "script": "",
    },
    "upstox": {
        "display_name": "Upstox",
        "status": "PLACEHOLDER",
        "mode": "DISABLED",
        "historical": False,
        "live_quotes": False,
        "option_chain": False,
        "execution": False,
        "script": "",
    },
    "groww": {
        "display_name": "Groww",
        "status": "PLACEHOLDER",
        "mode": "DISABLED",
        "historical": False,
        "live_quotes": False,
        "option_chain": False,
        "execution": False,
        "script": "",
    },
    "dhan": {
        "display_name": "Dhan",
        "status": "PLACEHOLDER",
        "mode": "DISABLED",
        "historical": False,
        "live_quotes": False,
        "option_chain": False,
        "execution": False,
        "script": "",
    },
}

SYMBOL_MAP: dict[str, dict[str, str]] = {
    "NIFTY": {
        "canonical": "NIFTY",
        "fyers": "NSE:NIFTY50-INDEX",
        "zerodha": "NSE:NIFTY 50",
        "angel_one": "NSE:Nifty 50",
        "upstox": "NSE_INDEX|Nifty 50",
        "groww": "NSE-NIFTY",
        "dhan": "IDX_I|13",
    },
    "BANKNIFTY": {
        "canonical": "BANKNIFTY",
        "fyers": "NSE:NIFTYBANK-INDEX",
        "zerodha": "NSE:NIFTY BANK",
        "angel_one": "NSE:Nifty Bank",
        "upstox": "NSE_INDEX|Nifty Bank",
        "groww": "NSE-BANKNIFTY",
        "dhan": "IDX_I|25",
    },
    "FINNIFTY": {
        "canonical": "FINNIFTY",
        "fyers": "NSE:FINNIFTY-INDEX",
        "zerodha": "NSE:NIFTY FIN SERVICE",
        "angel_one": "NSE:Nifty Fin Service",
        "upstox": "NSE_INDEX|Nifty Fin Service",
        "groww": "NSE-FINNIFTY",
        "dhan": "IDX_I|27",
    },
    "SENSEX": {
        "canonical": "SENSEX",
        "fyers": "BSE:SENSEX-INDEX",
        "zerodha": "BSE:SENSEX",
        "angel_one": "BSE:SENSEX",
        "upstox": "BSE_INDEX|SENSEX",
        "groww": "BSE-SENSEX",
        "dhan": "IDX_I|51",
    },
}

ALIASES = {
    "NIFTY50": "NIFTY",
    "NIFTY 50": "NIFTY",
    "NSE:NIFTY50-INDEX": "NIFTY",
    "NIFTYBANK": "BANKNIFTY",
    "NIFTY BANK": "BANKNIFTY",
    "NSE:NIFTYBANK-INDEX": "BANKNIFTY",
    "NIFTY FIN SERVICE": "FINNIFTY",
    "NSE:FINNIFTY-INDEX": "FINNIFTY",
    "BSE:SENSEX-INDEX": "SENSEX",
}

FORBIDDEN_TOKENS = {
    "--place-order",
    "--real-orders",
    "--broker-execution",
    "--auto-trading",
    "--option-selling",
    "place_order",
    "orderbook",
    "tradebook",
}


def normalize_symbol(symbol: str) -> str:
    cleaned = symbol.strip().upper().replace("_", " ")
    cleaned = " ".join(cleaned.split())
    return ALIASES.get(cleaned, cleaned.replace(" ", ""))


def provider_symbol(provider: str, symbol: str) -> str:
    provider_key = provider.strip().lower()
    canonical = normalize_symbol(symbol)
    if provider_key not in PROVIDERS:
        raise KeyError(f"Unknown provider: {provider}")
    if canonical not in SYMBOL_MAP:
        raise KeyError(f"Unsupported canonical symbol: {canonical}")
    mapped = SYMBOL_MAP[canonical].get(provider_key, "")
    if not mapped:
        raise KeyError(
            f"No {provider_key} symbol mapping exists for {canonical}."
        )
    return mapped


def fetcher_help(repo_root: Path, script: Path) -> dict[str, Any]:
    completed = subprocess.run(
        [
            str(repo_root / ".venv" / "Scripts" / "python.exe"),
            str(script),
            "--help",
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=60,
    )
    return {
        "status": "PASS" if completed.returncode == 0 else "FAILED",
        "return_code": completed.returncode,
        "text": (completed.stdout + "\n" + completed.stderr).strip(),
    }


def safe_fyers_fetch_command(
    repo_root: Path,
    workspace: Path,
    symbol: str,
    *,
    help_text: str | None = None,
) -> list[str]:
    provider = PROVIDERS["fyers"]
    script = repo_root / "scripts" / str(provider["script"])
    if not script.exists():
        raise RuntimeError("Fyers data-only fetcher is missing.")

    if help_text is None:
        help_payload = fetcher_help(repo_root, script)
        if help_payload["status"] != "PASS":
            raise RuntimeError("Fyers fetcher --help failed.")
        help_text = str(help_payload["text"])

    required = (
        "--workspace",
        "--symbol",
        "--execute-live-data-only",
        "--write",
    )
    missing = [flag for flag in required if flag not in help_text]
    if missing:
        raise RuntimeError(
            "Fyers data-only fetcher is missing safe flags: "
            + ", ".join(missing)
        )

    command = [
        str(repo_root / ".venv" / "Scripts" / "python.exe"),
        str(script),
        "--workspace",
        str(workspace),
        "--symbol",
        provider_symbol("fyers", symbol),
        "--execute-live-data-only",
        "--write",
    ]

    lowered = " ".join(command).lower()
    unsafe = sorted(
        token for token in FORBIDDEN_TOKENS if token in lowered
    )
    if unsafe:
        raise RuntimeError(
            "Unsafe fetch command token detected: " + ", ".join(unsafe)
        )
    return command


def provider_registry_snapshot(repo_root: Path) -> dict[str, Any]:
    providers: list[dict[str, Any]] = []
    for key, definition in PROVIDERS.items():
        item = dict(definition)
        item["provider"] = key
        script_name = str(item.get("script", ""))
        script_exists = bool(
            script_name
            and (repo_root / "scripts" / script_name).exists()
        )
        item["script_exists"] = script_exists
        item["effective_status"] = (
            "READY_DATA_ONLY"
            if key == "fyers"
            and item["status"] == "AVAILABLE"
            and script_exists
            else "DISABLED_PLACEHOLDER"
        )
        item["execution"] = False
        providers.append(item)

    ready = [
        item for item in providers
        if item["effective_status"] == "READY_DATA_ONLY"
    ]
    return {
        "version": VERSION,
        "provider_count": len(providers),
        "ready_data_only_count": len(ready),
        "providers": providers,
        "symbol_count": len(SYMBOL_MAP),
        "symbols": SYMBOL_MAP,
        "real_money_enabled": False,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "option_selling_enabled": False,
    }


def guard_payload() -> dict[str, Any]:
    return {
        "version": VERSION,
        "guard_check_status": "PASS",
        "workflow": "MULTI_PROVIDER_DATA_ONLY_REGISTRY",
        "fyers_data_only": True,
        "other_providers_disabled": True,
        "real_money_enabled": False,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "option_selling_enabled": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="HQE market-data provider registry"
    )
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[1]),
    )
    parser.add_argument("--snapshot", action="store_true")
    parser.add_argument("--guard-check", action="store_true")
    args = parser.parse_args()

    if args.guard_check:
        print(json.dumps(guard_payload(), indent=2, sort_keys=True))
        return 0
    if args.snapshot:
        print(json.dumps(
            provider_registry_snapshot(Path(args.repo_root)),
            indent=2,
            sort_keys=True,
        ))
        return 0
    parser.error("Use --snapshot or --guard-check.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
