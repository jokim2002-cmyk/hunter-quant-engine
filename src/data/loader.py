import pandas as pd
from src.utils.logger import logger
from src.data.validator import validate_market_data


def load_csv_data(file_path: str) -> pd.DataFrame:
    logger.info(f"Loading historical data from: {file_path}")

    data = pd.read_csv(file_path)

    data["datetime"] = pd.to_datetime(data["datetime"])

    validate_market_data(data)

    logger.info(f"Historical data loaded successfully. Rows: {len(data)}")

    return data