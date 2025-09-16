# DocumentSearcher - команды управления
.PHONY: help build up down logs db-init db-migrate db-reset db-clean test clean setup

# Показать справку
help:
	@echo "🗄️  DocumentSearcher - Команды управления"
	@echo "================================================="
	@echo "build       - Собрать Docker образы"
	@echo "up          - Запустить все сервисы"
	@echo "down        - Остановить все сервисы"
	@echo "logs        - Показать логи"
	@echo "db-init     - Инициализировать базу данных"
	@echo "db-migrate  - Применить миграции"
	@echo "db-reset    - Пересоздать базу данных (удалить все данные)"
	@echo "db-clean    - Очистить только данные (сохранить структуру)"
	@echo "test        - Запустить тесты"
	@echo "clean       - Очистить Docker volumes и остановить сервисы"
	@echo "setup       - Первоначальная настройка проекта"
	@echo "================================================="

# Собрать образы
build:
	@echo "🔨 Сборка Docker образов..."
	docker-compose build

# Запустить все сервисы
up:
	@echo "🚀 Запуск сервисов..."
	docker-compose up -d
	@echo "✅ Сервисы запущены:"
	@echo "   📱 API: http://localhost:8000"
	@echo "   📚 Docs: http://localhost:8000/docs"
	@echo "   🗄️  PostgreSQL: localhost:5432"

# Остановить сервисы
down:
	@echo "🛑 Остановка сервисов..."
	docker-compose down

# Показать логи
logs:
	docker-compose logs -f

# Показать логи базы данных
logs-db:
	docker-compose logs -f db

# Показать логи приложения
logs-app:
	docker-compose logs -f app

# Инициализация БД (применение миграций)
db-init:
	@echo "🗄️  Инициализация базы данных..."
	docker-compose exec app alembic upgrade head

# Применить миграции (обновить структуру БД)
db-migrate:
	@echo "🔄 Применение миграций..."
	docker-compose exec app alembic upgrade head

# Пересоздать базу данных полностью (удалить все данные)
db-reset: down
	@echo "⚠️  Пересоздание базы данных (все данные будут потеряны)..."
	@echo "Удаление volume с данными..."
	docker volume rm documentsearcher_postgres_data || true
	@echo "Запуск свежей базы данных..."
	docker-compose up -d db
	@echo "⏳ Ожидание готовности БД..."
	sleep 10
	@echo "🔄 Применение миграций..."
	docker-compose up -d app
	@echo "✅ База данных пересоздана и готова к работе"

# Очистить только данные (сохранить структуру таблиц)
db-clean:
	@echo "🧹 Очистка данных в таблицах..."
	docker-compose exec app python -c "
	import asyncio
	from app.core.db_manager import db_manager

	async def clean():
		await db_manager.initialize()
		from app.core.database import Base
		from sqlalchemy import text
		import app.models.document
		
		async with db_manager.engine.begin() as conn:
			# Удалить все данные из таблиц
			await conn.execute(text('DELETE FROM document_contents'))
			await conn.execute(text('DELETE FROM documents'))
			print('✅ Данные очищены, структура сохранена')
		
		await db_manager.close()
	
	asyncio.run(clean())
	"

# Создать тестовые данные
db-seed:
	@echo "🌱 Создание тестовых данных..."
	docker-compose exec app python scripts/seed_db.py || echo "Файл seed_db.py не найден"

# Запустить тесты
test:
	@echo "🧪 Запуск тестов..."
	docker-compose exec app python -m pytest tests/ -v

# Очистка всего (остановка + удаление volumes)
clean: down
	@echo "🧹 Полная очистка..."
	docker-compose down -v
	docker volume rm documentsearcher_postgres_data || true
	docker system prune -f

# Первоначальная настройка
setup: build db-reset
	@echo "🎉 Проект готов к работе!"
	@echo "API доступен: http://localhost:8000"
	@echo "Документация: http://localhost:8000/docs"

# Быстрый перезапуск приложения
restart:
	@echo "🔄 Перезапуск приложения..."
	docker-compose restart app

# Статус сервисов
status:
	@echo "📊 Статус сервисов:"
	docker-compose ps
