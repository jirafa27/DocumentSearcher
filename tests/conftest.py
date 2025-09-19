import pytest
import pytest_asyncio
import asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.database import Base, get_async_session


# Переключаемся на auto режим для pytest-asyncio
pytest_plugins = ('pytest_asyncio',)


@pytest.fixture(scope="session")
def event_loop():
    """Создает event loop для async тестов"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def test_db_session():
    """Фикстура для тестовой БД"""
    engine = create_async_engine(
        "postgresql+asyncpg://postgres:postgres@localhost:5433/test_documentsearcher",
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


@pytest_asyncio.fixture
async def test_client(test_db_session):
    """Тестовый HTTP клиент с переопределенными зависимостями"""
    
    # Переопределяем зависимость БД для тестов
    def override_get_async_session():
        yield test_db_session
        
    app.dependency_overrides[get_async_session] = override_get_async_session
    
    # Новый синтаксис для httpx AsyncClient
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    
    app.dependency_overrides.clear()


@pytest.fixture
def sample_file():
    """Тестовый файл для загрузки"""
    return {
        "filename": "test.txt",
        "content": b"Test document content for integration testing",
        "content_type": "text/plain"
    }


@pytest.fixture
def sample_document():
    """Фикстура с тестовым документом"""
    return {
        "file_name": "test.pdf",
        "file_type": "pdf",
        "content": "Отдел продаж компании показал отличные результаты"
    }