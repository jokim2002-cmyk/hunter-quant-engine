import logging
import os

# Ensure logs folder exists
os.makedirs("logs", exist_ok=True)

LOG_FILE = "logs/trading.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("AI_Algo_Trading")