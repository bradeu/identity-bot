import logging
from config.config import get_settings

settings = get_settings()

logger = logging.getLogger(settings.PROJECT_NAME)
logger.setLevel(settings.LOG_LEVEL)

if not logger.hasHandlers():
    handler = logging.StreamHandler()
    handler.setLevel(settings.LOG_LEVEL)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)

    logger.addHandler(handler)