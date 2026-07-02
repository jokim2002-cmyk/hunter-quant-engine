from typing import List

import pandas as pd

from src.models.candle import Candle
from src.utils.logger import logger


def create_candles_from_dataframe(data: pd.DataFrame) -> List[Candle]:
    logger.info("Creating candle objects from dataframe")

    candles = []

    for _, row in data.iterrows():
        candle = Candle(
            datetime=row["datetime"],
            open=float(row["open"]),
            high=float(row["high"]),
            low=float(row["low"]),
            close=float(row["close"]),
            volume=float(row["volume"]),
        )

        candles.append(candle)

    logger.info(f"Created {len(candles)} candle objects")

    return candles