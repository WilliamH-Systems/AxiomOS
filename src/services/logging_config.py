import logging
import sys
from ..config import config


def setup_logging():
    """Setup logging configuration for the application"""

    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, config.log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("axiomos.log"),
        ],
    )

    # Set specific logger levels
    logging.getLogger("langchain").setLevel(logging.WARNING)
    logging.getLogger("langchain_groq").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)

    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured at {config.log_level} level")

    return logger
