"""
Transaction Cost Profile Presets

Named broker/segment transaction cost profiles.
"""

from src.costs.transaction_cost_profile import TransactionCostProfile


COST_PROFILE_CUSTOM = "custom"
COST_PROFILE_FYERS_EQUITY_INTRADAY = "fyers-equity-intraday"
COST_PROFILE_FYERS_NIFTY_OPTIONS_INTRADAY = "fyers-nifty-options-intraday"

FYERS_EQUITY_INTRADAY_BROKERAGE_RATE = 0.0003
FYERS_EQUITY_INTRADAY_BROKERAGE_CAP_PER_ORDER = 20.0
FYERS_EQUITY_INTRADAY_STT_RATE = 0.00025
FYERS_EQUITY_INTRADAY_EXCHANGE_TRANSACTION_CHARGE_RATE = 0.000030699
FYERS_EQUITY_INTRADAY_SEBI_CHARGE_RATE = 0.000001
FYERS_EQUITY_INTRADAY_STAMP_DUTY_RATE = 0.00003
FYERS_EQUITY_INTRADAY_GST_RATE = 0.18

FYERS_NIFTY_OPTIONS_INTRADAY_BROKERAGE_PER_ORDER = 20.0
FYERS_NIFTY_OPTIONS_INTRADAY_STT_RATE = 0.0015
FYERS_NIFTY_OPTIONS_INTRADAY_EXCHANGE_TRANSACTION_CHARGE_RATE = 0.000355299
FYERS_NIFTY_OPTIONS_INTRADAY_SEBI_CHARGE_RATE = 0.000001
FYERS_NIFTY_OPTIONS_INTRADAY_STAMP_DUTY_RATE = 0.00003
FYERS_NIFTY_OPTIONS_INTRADAY_GST_RATE = 0.18
FYERS_NIFTY_OPTIONS_INTRADAY_CLEARING_CHARGE_RATE = 0.00009
FYERS_NIFTY_OPTIONS_INTRADAY_INVESTOR_PROTECTION_FUND_RATE = 0.0000001


def supported_transaction_cost_profile_names() -> tuple[str, ...]:
    """
    Return supported transaction cost profile names.

    Returns:
        Supported profile names.
    """
    return (
        COST_PROFILE_CUSTOM,
        COST_PROFILE_FYERS_EQUITY_INTRADAY,
        COST_PROFILE_FYERS_NIFTY_OPTIONS_INTRADAY,
    )


def build_transaction_cost_profile_from_name(
    profile_name: str,
) -> TransactionCostProfile:
    """
    Build transaction cost profile from preset name.

    Args:
        profile_name: Preset profile name.

    Returns:
        Immutable TransactionCostProfile.
    """
    if profile_name == COST_PROFILE_CUSTOM:
        return TransactionCostProfile()

    if profile_name == COST_PROFILE_FYERS_EQUITY_INTRADAY:
        return TransactionCostProfile(
            brokerage_rate=FYERS_EQUITY_INTRADAY_BROKERAGE_RATE,
            brokerage_cap_per_order=FYERS_EQUITY_INTRADAY_BROKERAGE_CAP_PER_ORDER,
            stt_rate=FYERS_EQUITY_INTRADAY_STT_RATE,
            exchange_transaction_charge_rate=(
                FYERS_EQUITY_INTRADAY_EXCHANGE_TRANSACTION_CHARGE_RATE
            ),
            sebi_charge_rate=FYERS_EQUITY_INTRADAY_SEBI_CHARGE_RATE,
            stamp_duty_rate=FYERS_EQUITY_INTRADAY_STAMP_DUTY_RATE,
            gst_rate=FYERS_EQUITY_INTRADAY_GST_RATE,
        )

    if profile_name == COST_PROFILE_FYERS_NIFTY_OPTIONS_INTRADAY:
        return TransactionCostProfile(
            brokerage_per_order=FYERS_NIFTY_OPTIONS_INTRADAY_BROKERAGE_PER_ORDER,
            stt_rate=FYERS_NIFTY_OPTIONS_INTRADAY_STT_RATE,
            exchange_transaction_charge_rate=(
                FYERS_NIFTY_OPTIONS_INTRADAY_EXCHANGE_TRANSACTION_CHARGE_RATE
            ),
            sebi_charge_rate=FYERS_NIFTY_OPTIONS_INTRADAY_SEBI_CHARGE_RATE,
            stamp_duty_rate=FYERS_NIFTY_OPTIONS_INTRADAY_STAMP_DUTY_RATE,
            clearing_charge_rate=FYERS_NIFTY_OPTIONS_INTRADAY_CLEARING_CHARGE_RATE,
            investor_protection_fund_rate=(
                FYERS_NIFTY_OPTIONS_INTRADAY_INVESTOR_PROTECTION_FUND_RATE
            ),
            gst_rate=FYERS_NIFTY_OPTIONS_INTRADAY_GST_RATE,
        )

    raise ValueError(f"Unsupported transaction cost profile: {profile_name}")
