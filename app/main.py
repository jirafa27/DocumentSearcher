from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.documents import router as documents_router
from app.core.config import settings
from app.core.database import get_engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    # Код, выполняемый при запуске
    print("Запуск DocumentSearcher API...")
    yield
    # Код, выполняемый при остановке
    print("Закрытие соединений с базой данных...")
    await get_engine().dispose()
    print("DocumentSearcher API остановлен.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="API для поиска по документам с использованием PostgreSQL full-text search",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене указать конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение роутеров
app.include_router(documents_router)


@app.get("/")
async def root():
    """Корневой эндпоинт API"""
    return {
        "message": "DocumentSearcher API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """Проверка состояния API"""
    return {"status": "healthy"}
