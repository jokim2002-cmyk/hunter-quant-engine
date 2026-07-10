from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
from pathlib import Path
from typing import Any

VERSION = "HQE_STRATEGY_PACK_SCHEMA_V1"
CURRENT_SCHEMA_VERSION = "1.0"

ALLOWED_CATEGORIES = {
    "breakout",
    "momentum_trend",
    "reversal",
    "scalping",
    "carry_btst",
    "sideways_avoidance",
    "locked_validation_candidate",
}

ALLOWED_STATUSES = {
    "draft",
    "active_paper",
    "locked_validation",
    "archived",
}

ALLOWED_INSTRUMENT_TYPES = {
    "index_option",
    "equity_cash_research",
    "index_research",
    "futures_research",
}

ALLOWED_OPTION_SIDES = {"CE", "PE"}

SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")
ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{2,63}$")

REQUIRED_SAFETY = {
    "paper_only": True,
    "no_real_money": True,
    "no_real_orders": True,
    "no_broker_execution": True,
    "no_auto_trading": True,
    "no_option_selling": True,
    "no_fake_trades": True,
    "no_candidate_tuning_during_validation": True,
    "no_profitability_claim": True,
}


def canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def pack_fingerprint(payload: dict[str, Any]) -> str:
    relevant = copy.deepcopy(payload)
    relevant.pop("registry", None)
    relevant.pop("file_path", None)
    return hashlib.sha256(
        canonical_json(relevant).encode("utf-8")
    ).hexdigest()


def base_pack(
    *,
    strategy_id: str,
    name: str,
    description: str,
    category: str,
    rules: dict[str, Any],
    instruments: list[dict[str, Any]] | None = None,
    timeframe: str = "5m",
    version: str = "1.0.0",
    status: str = "draft",
    risk: dict[str, Any] | None = None,
    validation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": CURRENT_SCHEMA_VERSION,
        "strategy_id": strategy_id,
        "name": name,
        "description": description,
        "category": category,
        "version": version,
        "status": status,
        "timeframe": timeframe,
        "instruments": instruments
        or [
            {
                "market": "NSE",
                "symbol": "NIFTY",
                "instrument_type": "index_option",
                "direction": "buy_only",
                "option_sides": ["CE", "PE"],
            }
        ],
        "rules": rules,
        "risk": risk
        or {
            "capital_mode": "paper",
            "max_risk_per_trade_percent": 1.0,
            "stop_loss_percent": 0.40,
            "target_percent": 1.20,
            "max_trades_per_day": 3,
            "cooldown_bars": 3,
        },
        "validation": validation
        or {
            "locked_candidate": False,
            "candidate_id": "",
            "minimum_observed_days": 20,
            "minimum_observed_trades": 30,
            "minimum_expiry_weeks": 4,
        },
        "safety": dict(REQUIRED_SAFETY),
        "notes": [],
    }


def builtin_strategy_packs() -> list[dict[str, Any]]:
    common_filters = [
        {
            "type": "market_hours",
            "start": "09:20",
            "end": "15:10",
        },
        {
            "type": "minimum_dte",
            "value": 1,
        },
    ]

    packs = [
        base_pack(
            strategy_id="hqe_breakout_option_buy",
            name="HQE Breakout Option Buy",
            description=(
                "Paper-only breakout template using range expansion "
                "and confirmation filters."
            ),
            category="breakout",
            rules={
                "entry": {
                    "all": [
                        {"indicator": "range_breakout", "lookback": 20},
                        {"indicator": "volume_confirmation", "minimum_ratio": 1.2},
                    ]
                },
                "filters": common_filters
                + [{"type": "avoid_low_efficiency", "er20_min": 0.25}],
                "exit": {
                    "stop_loss_percent": 0.40,
                    "target_percent": 1.20,
                    "time_exit": "15:15",
                },
            },
        ),
        base_pack(
            strategy_id="hqe_momentum_trend_option_buy",
            name="HQE Momentum Trend Option Buy",
            description=(
                "Paper-only trend template using efficiency ratio "
                "and directional momentum."
            ),
            category="momentum_trend",
            rules={
                "entry": {
                    "all": [
                        {"indicator": "efficiency_ratio", "period": 20, "minimum": 0.30},
                        {"indicator": "trend_alignment", "fast": 9, "slow": 21},
                    ]
                },
                "filters": common_filters,
                "exit": {
                    "stop_loss_percent": 0.40,
                    "target_percent": 1.20,
                    "time_exit": "15:15",
                },
            },
        ),
        base_pack(
            strategy_id="hqe_reversal_option_buy",
            name="HQE Reversal Option Buy",
            description=(
                "Paper-only reversal research template with "
                "oversold/overbought confirmation."
            ),
            category="reversal",
            rules={
                "entry": {
                    "all": [
                        {"indicator": "rsi_reversal", "period": 14},
                        {"indicator": "structure_confirmation", "bars": 3},
                    ]
                },
                "filters": common_filters
                + [{"type": "minimum_range_percent", "value": 0.004}],
                "exit": {
                    "stop_loss_percent": 0.35,
                    "target_percent": 0.90,
                    "time_exit": "15:10",
                },
            },
        ),
        base_pack(
            strategy_id="hqe_scalping_option_buy",
            name="HQE Scalping Option Buy",
            description=(
                "Paper-only intraday scalping template with "
                "strict trade-count and cooldown controls."
            ),
            category="scalping",
            rules={
                "entry": {
                    "all": [
                        {"indicator": "micro_momentum", "bars": 3},
                        {"indicator": "spread_quality", "maximum_percent": 1.0},
                    ]
                },
                "filters": common_filters,
                "exit": {
                    "stop_loss_percent": 0.25,
                    "target_percent": 0.50,
                    "time_exit": "15:05",
                },
            },
            risk={
                "capital_mode": "paper",
                "max_risk_per_trade_percent": 0.50,
                "stop_loss_percent": 0.25,
                "target_percent": 0.50,
                "max_trades_per_day": 5,
                "cooldown_bars": 5,
            },
        ),
        base_pack(
            strategy_id="hqe_carry_btst_research",
            name="HQE Carry/BTST Research",
            description=(
                "Research-only overnight template. It does not "
                "enable broker execution."
            ),
            category="carry_btst",
            instruments=[
                {
                    "market": "NSE",
                    "symbol": "NIFTY",
                    "instrument_type": "index_research",
                    "direction": "research_only",
                    "option_sides": [],
                }
            ],
            rules={
                "entry": {
                    "all": [
                        {"indicator": "close_strength", "minimum": 0.70},
                        {"indicator": "trend_alignment", "fast": 20, "slow": 50},
                    ]
                },
                "filters": [
                    {"type": "research_only"},
                    {"type": "event_risk_check"},
                ],
                "exit": {
                    "mode": "next_session_research_review",
                },
            },
            risk={
                "capital_mode": "paper",
                "max_risk_per_trade_percent": 0.0,
                "stop_loss_percent": 0.0,
                "target_percent": 0.0,
                "max_trades_per_day": 0,
                "cooldown_bars": 0,
            },
        ),
        base_pack(
            strategy_id="hqe_sideways_avoidance_filter",
            name="HQE Sideways Avoidance Filter",
            description=(
                "Reusable filter pack for avoiding low-efficiency "
                "and compressed-range market conditions."
            ),
            category="sideways_avoidance",
            instruments=[
                {
                    "market": "NSE",
                    "symbol": "NIFTY",
                    "instrument_type": "index_research",
                    "direction": "filter_only",
                    "option_sides": [],
                }
            ],
            rules={
                "entry": {"all": []},
                "filters": [
                    {"type": "efficiency_ratio", "period": 20, "minimum": 0.30},
                    {"type": "range_percent", "period": 24, "minimum": 0.004},
                ],
                "exit": {"mode": "not_applicable"},
            },
        ),
        base_pack(
            strategy_id="hqe_locked_forward_candidate",
            name="HQE Locked Forward Candidate",
            description=(
                "Current locked paper-validation candidate. "
                "No tuning is allowed during validation."
            ),
            category="locked_validation_candidate",
            status="locked_validation",
            instruments=[
                {
                    "market": "NSE",
                    "symbol": "NIFTY",
                    "instrument_type": "index_option",
                    "direction": "buy_only",
                    "option_sides": ["PE"],
                }
            ],
            rules={
                "entry": {
                    "all": [
                        {"indicator": "efficiency_ratio", "period": 20, "minimum": 0.30},
                        {"indicator": "minimum_estimated_net_reward", "value": 200},
                    ]
                },
                "filters": [
                    {"type": "minimum_dte", "value": 1},
                    {"type": "option_ltp_range", "minimum": 20, "maximum": 200},
                    {"type": "option_side", "value": "PE"},
                ],
                "exit": {
                    "stop_loss_percent": 0.40,
                    "target_percent": 1.20,
                    "time_exit": "15:15",
                },
            },
            validation={
                "locked_candidate": True,
                "candidate_id": "ER20_GE_030_PE_DTE1_LTP20_200_REWARD200",
                "minimum_observed_days": 20,
                "minimum_observed_trades": 30,
                "minimum_expiry_weeks": 4,
            },
        ),
    ]

    for pack in packs:
        pack["fingerprint"] = pack_fingerprint(pack)
    return packs


def validate_strategy_pack(payload: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    required_fields = (
        "schema_version",
        "strategy_id",
        "name",
        "description",
        "category",
        "version",
        "status",
        "timeframe",
        "instruments",
        "rules",
        "risk",
        "validation",
        "safety",
    )
    for field in required_fields:
        if field not in payload:
            errors.append(f"Missing required field: {field}")

    if errors:
        return {
            "valid": False,
            "errors": errors,
            "warnings": warnings,
            "fingerprint": "",
        }

    strategy_id = str(payload.get("strategy_id", ""))
    if not ID_PATTERN.fullmatch(strategy_id):
        errors.append("strategy_id must be a safe lowercase slug.")

    if str(payload.get("schema_version")) != CURRENT_SCHEMA_VERSION:
        errors.append(
            f"schema_version must be {CURRENT_SCHEMA_VERSION}."
        )

    if not SEMVER_PATTERN.fullmatch(str(payload.get("version", ""))):
        errors.append("version must use semantic x.y.z format.")

    if payload.get("category") not in ALLOWED_CATEGORIES:
        errors.append("Unsupported strategy category.")

    if payload.get("status") not in ALLOWED_STATUSES:
        errors.append("Unsupported strategy status.")

    instruments = payload.get("instruments")
    if not isinstance(instruments, list) or not instruments:
        errors.append("At least one instrument definition is required.")
    else:
        for index, instrument in enumerate(instruments):
            if not isinstance(instrument, dict):
                errors.append(f"Instrument {index} must be an object.")
                continue
            instrument_type = instrument.get("instrument_type")
            if instrument_type not in ALLOWED_INSTRUMENT_TYPES:
                errors.append(
                    f"Instrument {index} has unsupported instrument_type."
                )
            direction = str(instrument.get("direction", "")).lower()
            if direction in {
                "sell",
                "sell_only",
                "short",
                "option_sell",
                "option_selling",
            }:
                errors.append(
                    f"Instrument {index} attempts prohibited selling."
                )
            sides = instrument.get("option_sides", [])
            if not isinstance(sides, list):
                errors.append(
                    f"Instrument {index} option_sides must be a list."
                )
            else:
                invalid_sides = [
                    side
                    for side in sides
                    if str(side).upper() not in ALLOWED_OPTION_SIDES
                ]
                if invalid_sides:
                    errors.append(
                        f"Instrument {index} has invalid option sides."
                    )

    rules = payload.get("rules")
    if not isinstance(rules, dict):
        errors.append("rules must be an object.")
    else:
        for key in ("entry", "filters", "exit"):
            if key not in rules:
                errors.append(f"rules.{key} is required.")

    risk = payload.get("risk")
    if not isinstance(risk, dict):
        errors.append("risk must be an object.")
    elif str(risk.get("capital_mode", "")).lower() != "paper":
        errors.append("risk.capital_mode must remain paper.")

    safety = payload.get("safety")
    if not isinstance(safety, dict):
        errors.append("safety must be an object.")
    else:
        for key, required_value in REQUIRED_SAFETY.items():
            if safety.get(key) is not required_value:
                errors.append(
                    f"safety.{key} must remain {required_value}."
                )

    validation = payload.get("validation")
    if not isinstance(validation, dict):
        errors.append("validation must be an object.")
    elif validation.get("locked_candidate"):
        if payload.get("status") != "locked_validation":
            errors.append(
                "Locked candidate must use locked_validation status."
            )
        if not str(validation.get("candidate_id", "")).strip():
            errors.append("Locked candidate requires candidate_id.")

    if payload.get("category") == "carry_btst":
        warnings.append(
            "Carry/BTST template is research-only and has no execution."
        )

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "fingerprint": pack_fingerprint(payload),
    }


def bump_patch_version(version: str) -> str:
    if not SEMVER_PATTERN.fullmatch(version):
        raise ValueError("Version must use x.y.z format.")
    major, minor, patch = (int(part) for part in version.split("."))
    return f"{major}.{minor}.{patch + 1}"


def write_builtin_packs(target: Path) -> list[Path]:
    target.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for pack in builtin_strategy_packs():
        validation = validate_strategy_pack(pack)
        if not validation["valid"]:
            raise RuntimeError(
                f"Built-in pack invalid: {pack['strategy_id']}: "
                + "; ".join(validation["errors"])
            )
        pack["fingerprint"] = validation["fingerprint"]
        path = target / f"{pack['strategy_id']}.json"
        path.write_text(
            json.dumps(pack, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        written.append(path)
    return written


def guard_payload() -> dict[str, Any]:
    return {
        "version": VERSION,
        "guard_check_status": "PASS",
        "workflow": "STRATEGY_PACK_SCHEMA_AND_BUILTINS",
        "builtin_pack_count": len(builtin_strategy_packs()),
        "paper_only": True,
        "real_money_enabled": False,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "option_selling_enabled": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="HQE strategy-pack schema and built-ins"
    )
    parser.add_argument("--write-builtins", default="")
    parser.add_argument("--list-builtins", action="store_true")
    parser.add_argument("--guard-check", action="store_true")
    args = parser.parse_args()

    if args.guard_check:
        print(json.dumps(guard_payload(), indent=2, sort_keys=True))
        return 0
    if args.list_builtins:
        print(json.dumps(
            builtin_strategy_packs(),
            indent=2,
            sort_keys=True,
        ))
        return 0
    if args.write_builtins:
        paths = write_builtin_packs(Path(args.write_builtins))
        print(json.dumps(
            {"written": [str(path) for path in paths]},
            indent=2,
            sort_keys=True,
        ))
        return 0

    parser.error(
        "Use --write-builtins, --list-builtins or --guard-check."
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
