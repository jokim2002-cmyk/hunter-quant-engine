from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

VERSION = "HQE_STRATEGY_BUILDER_ENGINE_V1"
SELECTION_FILE = "HQE_ACTIVE_STRATEGY_SELECTION.json"

CATEGORY_DEFAULTS: dict[str, dict[str, Any]] = {
    "breakout": {
        "entry_indicator": "range_breakout",
        "entry_period": 20,
        "confirmation_indicator": "volume_confirmation",
        "confirmation_value": 1.20,
        "er20_min": 0.25,
        "range24_min": 0.004,
    },
    "momentum_trend": {
        "entry_indicator": "efficiency_ratio",
        "entry_period": 20,
        "confirmation_indicator": "trend_alignment",
        "confirmation_value": 21,
        "er20_min": 0.30,
        "range24_min": 0.000,
    },
    "reversal": {
        "entry_indicator": "rsi_reversal",
        "entry_period": 14,
        "confirmation_indicator": "structure_confirmation",
        "confirmation_value": 3,
        "er20_min": 0.00,
        "range24_min": 0.004,
    },
    "scalping": {
        "entry_indicator": "micro_momentum",
        "entry_period": 3,
        "confirmation_indicator": "spread_quality",
        "confirmation_value": 1.00,
        "er20_min": 0.20,
        "range24_min": 0.002,
    },
}

SAFE_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{2,63}$")

SAFETY_LOCK = {
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


def utc_now_text() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def safe_slug(value: str) -> str:
    cleaned = re.sub(
        r"[^a-z0-9_-]+",
        "_",
        value.strip().lower().replace(" ", "_"),
    ).strip("_")
    if not SAFE_ID.fullmatch(cleaned):
        raise ValueError(
            "Strategy ID must be 3-64 lowercase letters, numbers, _ or -."
        )
    return cleaned


def positive_float(value: Any, field: str, *, allow_zero: bool = False) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be numeric.") from exc
    if allow_zero:
        if parsed < 0:
            raise ValueError(f"{field} cannot be negative.")
    elif parsed <= 0:
        raise ValueError(f"{field} must be greater than zero.")
    return parsed


def positive_int(value: Any, field: str, *, allow_zero: bool = False) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be an integer.") from exc
    if allow_zero:
        if parsed < 0:
            raise ValueError(f"{field} cannot be negative.")
    elif parsed <= 0:
        raise ValueError(f"{field} must be greater than zero.")
    return parsed


def normalize_option_sides(value: Any) -> list[str]:
    if isinstance(value, str):
        raw = [
            item.strip().upper()
            for item in value.replace("|", ",").split(",")
            if item.strip()
        ]
    elif isinstance(value, list):
        raw = [str(item).strip().upper() for item in value if str(item).strip()]
    else:
        raw = []

    sides: list[str] = []
    for side in raw:
        if side not in {"CE", "PE"}:
            raise ValueError("Option sides can contain only CE and/or PE.")
        if side not in sides:
            sides.append(side)
    if not sides:
        raise ValueError("At least one option side is required.")
    return sides


def builder_defaults(category: str = "breakout") -> dict[str, Any]:
    key = category.strip().lower()
    if key not in CATEGORY_DEFAULTS:
        key = "breakout"
    category_defaults = copy.deepcopy(CATEGORY_DEFAULTS[key])
    return {
        "strategy_id": f"my_{key}_strategy",
        "name": f"My {key.replace('_', ' ').title()} Strategy",
        "description": "Paper-only strategy created in HQE Strategy Builder.",
        "category": key,
        "symbol": "NIFTY",
        "timeframe": "5m",
        "option_sides": ["CE", "PE"],
        "minimum_dte": 1,
        "ltp_min": 20.0,
        "ltp_max": 200.0,
        "minimum_estimated_net_reward": 200.0,
        "stop_loss_percent": 0.40,
        "target_percent": 1.20,
        "max_risk_per_trade_percent": 1.0,
        "max_trades_per_day": 3,
        "cooldown_bars": 3,
        **category_defaults,
    }


def build_strategy_pack(form: dict[str, Any]) -> dict[str, Any]:
    from hqe_strategy_pack_schema import (
        base_pack,
        pack_fingerprint,
        validate_strategy_pack,
    )

    category = str(form.get("category", "breakout")).strip().lower()
    if category not in CATEGORY_DEFAULTS:
        raise ValueError(
            "Builder supports breakout, momentum_trend, reversal or scalping."
        )

    strategy_id = safe_slug(str(form.get("strategy_id", "")))
    name = str(form.get("name", "")).strip()
    if len(name) < 3:
        raise ValueError("Strategy name must contain at least 3 characters.")

    description = str(form.get("description", "")).strip()
    if not description:
        description = "Paper-only strategy created in HQE Strategy Builder."

    symbol = str(form.get("symbol", "NIFTY")).strip().upper()
    if symbol not in {"NIFTY", "BANKNIFTY", "FINNIFTY", "SENSEX"}:
        raise ValueError("Unsupported builder symbol.")

    timeframe = str(form.get("timeframe", "5m")).strip().lower()
    if timeframe not in {"1m", "3m", "5m", "15m", "30m", "1h"}:
        raise ValueError("Unsupported timeframe.")

    option_sides = normalize_option_sides(
        form.get("option_sides", ["CE", "PE"])
    )
    minimum_dte = positive_int(
        form.get("minimum_dte", 1),
        "minimum_dte",
        allow_zero=True,
    )
    ltp_min = positive_float(form.get("ltp_min", 20), "ltp_min")
    ltp_max = positive_float(form.get("ltp_max", 200), "ltp_max")
    if ltp_max <= ltp_min:
        raise ValueError("ltp_max must be greater than ltp_min.")

    reward_min = positive_float(
        form.get("minimum_estimated_net_reward", 200),
        "minimum_estimated_net_reward",
        allow_zero=True,
    )
    stop_loss = positive_float(
        form.get("stop_loss_percent", 0.40),
        "stop_loss_percent",
    )
    target = positive_float(
        form.get("target_percent", 1.20),
        "target_percent",
    )
    risk_percent = positive_float(
        form.get("max_risk_per_trade_percent", 1.0),
        "max_risk_per_trade_percent",
    )
    max_trades = positive_int(
        form.get("max_trades_per_day", 3),
        "max_trades_per_day",
    )
    cooldown = positive_int(
        form.get("cooldown_bars", 3),
        "cooldown_bars",
        allow_zero=True,
    )
    entry_period = positive_int(
        form.get("entry_period", 20),
        "entry_period",
    )
    confirmation_value = positive_float(
        form.get("confirmation_value", 1.2),
        "confirmation_value",
        allow_zero=True,
    )
    er20_min = positive_float(
        form.get("er20_min", 0.0),
        "er20_min",
        allow_zero=True,
    )
    range24_min = positive_float(
        form.get("range24_min", 0.0),
        "range24_min",
        allow_zero=True,
    )

    filters: list[dict[str, Any]] = [
        {"type": "market_hours", "start": "09:20", "end": "15:10"},
        {"type": "minimum_dte", "value": minimum_dte},
        {
            "type": "option_ltp_range",
            "minimum": ltp_min,
            "maximum": ltp_max,
        },
        {"type": "option_side", "value": option_sides},
        {
            "type": "minimum_estimated_net_reward",
            "value": reward_min,
        },
    ]
    if er20_min > 0:
        filters.append(
            {
                "type": "efficiency_ratio",
                "period": 20,
                "minimum": er20_min,
            }
        )
    if range24_min > 0:
        filters.append(
            {
                "type": "range_percent",
                "period": 24,
                "minimum": range24_min,
            }
        )

    pack = base_pack(
        strategy_id=strategy_id,
        name=name,
        description=description,
        category=category,
        timeframe=timeframe,
        instruments=[
            {
                "market": "NSE" if symbol != "SENSEX" else "BSE",
                "symbol": symbol,
                "instrument_type": "index_option",
                "direction": "buy_only",
                "option_sides": option_sides,
            }
        ],
        rules={
            "entry": {
                "all": [
                    {
                        "indicator": str(
                            form.get(
                                "entry_indicator",
                                CATEGORY_DEFAULTS[category]["entry_indicator"],
                            )
                        ).strip(),
                        "period": entry_period,
                    },
                    {
                        "indicator": str(
                            form.get(
                                "confirmation_indicator",
                                CATEGORY_DEFAULTS[category][
                                    "confirmation_indicator"
                                ],
                            )
                        ).strip(),
                        "value": confirmation_value,
                    },
                ]
            },
            "filters": filters,
            "exit": {
                "stop_loss_percent": stop_loss,
                "target_percent": target,
                "time_exit": "15:15",
            },
        },
        risk={
            "capital_mode": "paper",
            "max_risk_per_trade_percent": risk_percent,
            "stop_loss_percent": stop_loss,
            "target_percent": target,
            "max_trades_per_day": max_trades,
            "cooldown_bars": cooldown,
        },
        validation={
            "locked_candidate": False,
            "candidate_id": "",
            "minimum_observed_days": 20,
            "minimum_observed_trades": 30,
            "minimum_expiry_weeks": 4,
        },
        status="draft",
    )
    pack["builder"] = {
        "engine_version": VERSION,
        "created_at_utc": utc_now_text(),
        "editable": True,
    }
    pack["safety"] = dict(SAFETY_LOCK)
    pack["fingerprint"] = pack_fingerprint(pack)

    result = validate_strategy_pack(pack)
    if not result["valid"]:
        raise ValueError(
            "Generated strategy pack failed validation: "
            + "; ".join(result["errors"])
        )
    pack["fingerprint"] = result["fingerprint"]
    return pack


def strategy_preview(pack: dict[str, Any]) -> dict[str, Any]:
    from hqe_strategy_pack_schema import validate_strategy_pack

    validation = validate_strategy_pack(pack)
    instruments = pack.get("instruments", [])
    instrument = instruments[0] if instruments else {}
    risk = pack.get("risk", {})
    rules = pack.get("rules", {})
    validation_block = pack.get("validation", {})

    warnings = list(validation.get("warnings", []))
    if float(risk.get("target_percent", 0) or 0) <= float(
        risk.get("stop_loss_percent", 0) or 0
    ):
        warnings.append(
            "Target percent is not greater than stop-loss percent."
        )
    if int(risk.get("max_trades_per_day", 0) or 0) > 5:
        warnings.append("High daily trade limit; review overtrading risk.")
    if float(risk.get("max_risk_per_trade_percent", 0) or 0) > 2:
        warnings.append("Risk per trade exceeds 2% paper-risk guideline.")

    summary_lines = [
        f"Name: {pack.get('name', '')}",
        f"ID: {pack.get('strategy_id', '')}",
        f"Category: {pack.get('category', '')}",
        f"Version: {pack.get('version', '')}",
        f"Status: {pack.get('status', '')}",
        f"Symbol: {instrument.get('symbol', '')}",
        f"Timeframe: {pack.get('timeframe', '')}",
        "Direction: BUY ONLY",
        f"Option sides: {', '.join(instrument.get('option_sides', []))}",
        (
            "Risk: SL "
            f"{risk.get('stop_loss_percent', '')}% | Target "
            f"{risk.get('target_percent', '')}% | Max trades "
            f"{risk.get('max_trades_per_day', '')}"
        ),
        f"Filters: {len(rules.get('filters', []))}",
        (
            "Locked candidate: "
            f"{validation_block.get('locked_candidate', False)}"
        ),
        "Real orders: NO",
        "Broker execution: NO",
        "Option selling: NO",
    ]
    return {
        "valid": bool(validation["valid"]),
        "errors": list(validation["errors"]),
        "warnings": warnings,
        "summary": "\n".join(summary_lines),
        "fingerprint": str(validation["fingerprint"]),
        "paper_compatible": bool(
            validation["valid"]
            and pack.get("safety", {}).get("paper_only") is True
            and pack.get("safety", {}).get("no_real_orders") is True
            and pack.get("safety", {}).get("no_option_selling") is True
        ),
    }


def save_draft(
    form: dict[str, Any],
    workspace: Path,
) -> Path:
    pack = build_strategy_pack(form)
    preview = strategy_preview(pack)
    if not preview["valid"]:
        raise ValueError("Cannot save invalid strategy draft.")

    target_dir = workspace / "strategy_packs" / "drafts"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / (
        f"{pack['strategy_id']}_{pack['version'].replace('.', '_')}.json"
    )
    target.write_text(
        json.dumps(pack, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return target


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def active_selection_snapshot(workspace: Path) -> dict[str, Any]:
    path = workspace / SELECTION_FILE
    payload = read_json(path)
    selected_path = Path(str(payload.get("pack_path", ""))) if payload else None
    available = bool(selected_path and selected_path.exists())
    return {
        "selection_file": str(path),
        "selected": bool(payload),
        "available": available,
        "strategy_id": str(payload.get("strategy_id", "")),
        "name": str(payload.get("name", "")),
        "version": str(payload.get("version", "")),
        "pack_path": str(payload.get("pack_path", "")),
        "fingerprint": str(payload.get("fingerprint", "")),
        "selected_at_utc": str(payload.get("selected_at_utc", "")),
        "mode": str(payload.get("mode", "PAPER_ONLY")),
        "display_text": (
            f"Active paper strategy: {payload.get('name', 'none')} "
            f"{payload.get('version', '')}"
            if payload
            else "Active paper strategy: none selected"
        ),
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "option_selling_enabled": False,
    }


def select_active_paper_pack(
    pack_path: Path,
    workspace: Path,
) -> Path:
    from hqe_strategy_pack_schema import validate_strategy_pack

    pack = read_json(pack_path)
    validation = validate_strategy_pack(pack)
    if not validation["valid"]:
        raise ValueError(
            "Cannot select invalid strategy pack: "
            + "; ".join(validation["errors"])
        )
    safety = pack.get("safety", {})
    if not all(
        (
            safety.get("paper_only") is True,
            safety.get("no_real_orders") is True,
            safety.get("no_broker_execution") is True,
            safety.get("no_auto_trading") is True,
            safety.get("no_option_selling") is True,
        )
    ):
        raise ValueError("Strategy safety locks are not valid.")

    selection = {
        "version": VERSION,
        "strategy_id": str(pack["strategy_id"]),
        "name": str(pack["name"]),
        "strategy_version": str(pack["version"]),
        "version_label": str(pack["version"]),
        "pack_path": str(pack_path.resolve()),
        "fingerprint": str(validation["fingerprint"]),
        "selected_at_utc": utc_now_text(),
        "mode": "PAPER_ONLY",
        "real_money_enabled": False,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "option_selling_enabled": False,
    }
    target = workspace / SELECTION_FILE
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(
        json.dumps(selection, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    temporary.replace(target)
    return target


def clear_active_selection(workspace: Path) -> bool:
    path = workspace / SELECTION_FILE
    if not path.exists():
        return False
    path.unlink()
    return True


def guard_payload() -> dict[str, Any]:
    return {
        "version": VERSION,
        "guard_check_status": "PASS",
        "workflow": "VISUAL_STRATEGY_BUILDER_AND_SELECTOR",
        "selection_mode": "PAPER_ONLY",
        "real_money_enabled": False,
        "real_orders_enabled": False,
        "broker_execution_enabled": False,
        "auto_trading_enabled": False,
        "option_selling_enabled": False,
        "safety_lock": SAFETY_LOCK,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="HQE strategy builder and selector engine"
    )
    parser.add_argument("--workspace", default="")
    parser.add_argument("--defaults", default="")
    parser.add_argument("--selection", action="store_true")
    parser.add_argument("--guard-check", action="store_true")
    args = parser.parse_args()

    if args.guard_check:
        print(json.dumps(guard_payload(), indent=2, sort_keys=True))
        return 0
    if args.defaults:
        print(json.dumps(
            builder_defaults(args.defaults),
            indent=2,
            sort_keys=True,
        ))
        return 0
    if args.selection:
        if not args.workspace:
            parser.error("--workspace is required with --selection.")
        print(json.dumps(
            active_selection_snapshot(Path(args.workspace)),
            indent=2,
            sort_keys=True,
        ))
        return 0

    parser.error("Use --defaults, --selection or --guard-check.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
