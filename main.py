from src.config import settings
from src.utils.logger import logger
from src.data.loader import load_csv_data
from src.data.candle_factory import create_candles_from_dataframe


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

    logger.info("Application Finished Successfully")


if __name__ == "__main__":
    main()