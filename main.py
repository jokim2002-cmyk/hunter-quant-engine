from src.config import settings
from src.config.swing_config import DEFAULT_SWING_CONFIG
from src.utils.logger import logger
from src.data.loader import load_csv_data
from src.data.candle_factory import create_candles_from_dataframe
from src.engines.swing_detection_engine import SwingDetectionEngine


def main():
    logger.info("Application Started")

    print(f"{settings.APP_NAME} - Phase 1 Started")
    print(f"Environment: {settings.ENVIRONMENT}")
    print(f"Debug Mode: {settings.DEBUG}")

    data = load_csv_data("data/raw/nifty_5min.csv")
    candles = create_candles_from_dataframe(data)

    first_candle = candles[0]

    print("First Candle:")
    print(first_candle)
    print(f"Bullish: {first_candle.is_bullish}")
    print(f"Body Size: {first_candle.body_size}")
    print(f"Range Size: {first_candle.range_size}")

    swing_engine = SwingDetectionEngine(lookback=DEFAULT_SWING_CONFIG.lookback)
    swing_points = swing_engine.detect_swings(candles)

    print("Detected Swing Points:")
    for swing_point in swing_points:
        print(swing_point)

    print("Application Finished Successfully")


if __name__ == "__main__":
    main()