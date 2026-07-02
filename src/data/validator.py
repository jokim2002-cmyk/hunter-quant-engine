import pandas as pd
from src.utils.logger import logger


REQUIRED_COLUMNS = ["datetime", "open", "high", "low", "close", "volume"]


def validate_market_data(data: pd.DataFrame) -> bool:
    logger.info("Starting market data validation")

    for column in REQUIRED_COLUMNS:
        if column not in data.columns:
            raise ValueError(f"Missing required column: {column}")

    if data.isnull().values.any():
        raise ValueError("Data contains missing values")

    if data["datetime"].duplicated().any():
        raise ValueError("Data contains duplicate datetime values")

    if not data["datetime"].is_monotonic_increasing:
        raise ValueError("Datetime column is not sorted")

    invalid_ohlc = data[
        (data["high"] < data["open"]) |
        (data["high"] < data["close"]) |
        (data["low"] > data["open"]) |
        (data["low"] > data["close"])
    ]

    if not invalid_ohlc.empty:
        raise ValueError("Invalid OHLC data found")

    logger.info("Market data validation completed successfully")
    return True