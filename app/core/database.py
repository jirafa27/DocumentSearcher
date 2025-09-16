from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base

from app.core.config import settings

# Создание базового класса для моделей
Base = declarative_base()

# Переменные для ленивой инициализации
_engine = None
_async_session_maker = None


def get_engine():
    """Получить асинхронный движок (создается при первом вызове)"""
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            settings.DATABASE_URL,
            echo=settings.DEBUG,
            future=True,
            pool_pre_ping=True,
            pool_size=20,  # Увеличиваем для высоких нагрузок
            max_overflow=50,  # Больше overflow соединений
            pool_recycle=3600,  # 1 час для стабильности
            pool_timeout=60,  # Timeout получения соединения
            pool_reset_on_return="commit",  # Очистка состояния соединения
            connect_args={
                "server_settings": {
                    "application_name": "DocumentSearcher",
                    "statement_timeout": "300000",  # 5 минут
                    "idle_in_transaction_session_timeout": "300000",  # 5 минут
                    "tcp_keepalives_idle": "600",
                    "tcp_keepalives_interval": "30",
                    "tcp_keepalives_count": "3",
                    "enable_seqscan": "on",  # Включаем последовательное сканирование
                    "enable_indexscan": "on",  # Включаем сканирование по индексам
                },
                "command_timeout": 120,  # 2 минуты
            },
        )
    return _engine


def get_async_session_maker():
    """Получить фабрику асинхронных сессий (создается при первом вызове)"""
    global _async_session_maker
    if _async_session_maker is None:
        _async_session_maker = async_sessionmaker(
            bind=get_engine(), class_=AsyncSession, expire_on_commit=False
        )
    return _async_session_maker


async def get_async_session() -> AsyncSession:
    """
    Dependency для получения асинхронной сессии базы данных.
    Автоматически закрывает сессию после использования.
    """
    async with get_async_session_maker()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
