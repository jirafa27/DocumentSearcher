import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.database import Base


@pytest.fixture(scope="session")
def event_loop():
    """Создает event loop для async тестов"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def test_db_session():
    """Фикстура для тестовой БД"""
    engine = create_async_engine(
        "postgresql+asyncpg://postgres:postgres@localhost:5432/test_documentsearcher",
        echo=False,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture
def sample_document():
    """Фикстура с тестовым документом"""
    return {
        "file_name": "test.pdf",
        "file_type": "pdf",
        "content": "Отдел продаж компании показал отличные результаты"
    }