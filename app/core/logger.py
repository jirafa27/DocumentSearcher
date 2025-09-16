import logging

from app.core.config import settings

# Настраиваем логирование один раз при импорте
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format=settings.LOG_FORMAT,
    handlers=[
        logging.FileHandler(f"{settings.LOG_DIR}/{settings.LOG_FILE}"),
        logging.StreamHandler(),
    ],
)

# Создаем глобальный логгер
logger = logging.getLogger("app")
