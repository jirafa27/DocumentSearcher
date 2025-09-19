# DocumentSearcher

Система полнотекстового поиска по документам с поддержкой PDF и DOCX файлов.

## Описание

DocumentSearcher - это веб-приложение для загрузки, хранения и поиска по содержимому документов. Система поддерживает:

- **Загрузка документов**: PDF и DOCX файлы до 20MB
- **Полнотекстовый поиск**: Поиск по содержимому с поддержкой русской морфологии
- **Извлечение контекста**: Получение фрагментов текста с выделением найденных совпадений
- **Фильтрация**: Поиск по конкретному пользователю или документу
- **REST API**: Полноценный API для интеграции с другими системами

## Архитектура

```
├── app/
│   ├── api/           # REST API эндпоинты
│   ├── core/          # Базовые модели и конфигурация
│   ├── services/      # Бизнес-логика
│   ├── repositories/  # Работа с данными
│   └── models/        # SQLAlchemy модели
├── tests/             # Тесты (83% покрытия)
└── docker-compose.yml # Конфигурация Docker
```

### Технологический стек:
- **Backend**: FastAPI + Python 3.10
- **База данных**: PostgreSQL 15 с полнотекстовым поиском
- **ORM**: SQLAlchemy 2.0 (async)
- **Обработка файлов**: pdfplumber, python-docx
- **Тестирование**: pytest, pytest-asyncio
- **Контейнеризация**: Docker + Docker Compose

## Быстрый старт

### Требования
- Docker и Docker Compose
- Python 3.10+ (для локальной разработки)

### 1. Клонирование и запуск

#### Вариант A: С помощью Make (рекомендуется)

```bash
# Клонируем репозиторий
git clone <repository-url>
cd DocumentSearcher

# Запускаем все сервисы
make up
```

#### Вариант B: Напрямую через Docker

```bash
# Клонируем репозиторий
git clone <repository-url>
cd DocumentSearcher

# Сборка и запуск контейнеров
docker-compose up -d --build

# Проверка статуса
docker-compose ps

# Просмотр логов (опционально)
docker-compose logs -f
```

**Примечание**: При первом запуске миграции применяются автоматически. Если нужно применить миграции вручную:

```bash
# Через Make
make db-migrate

# Или напрямую через Docker
docker-compose exec app alembic upgrade head
```

### 2. Проверка работы

Приложение будет доступно по адресам:
- **API**: http://localhost:8000
- **Документация**: http://localhost:8000/docs
- **PostgreSQL**: localhost:5432

## API Документация

### Основные эндпоинты:

#### Загрузка документа
```http
POST /api/v1/documents/upload
Content-Type: multipart/form-data

Parameters:
- file: PDF или DOCX файл (max 20MB)
- user_id: UUID пользователя
```

#### Поиск по документам
```http
GET /api/v1/documents/search?query=текст&user_id=uuid

Parameters:
- query: Поисковый запрос (min 1 символ)
- user_id: Фильтр по пользователю (опционально)
- document_id: Поиск в конкретном документе (опционально)
- search_exact: Точное совпадение (default: false)
- context_size_before: Размер контекста до искомой фразы
- context_size_after: Размер контекста после искомой фразы
```

#### Получение документа
```http
GET /api/v1/documents/{document_id}
```

#### Удаление документа
```http
DELETE /api/v1/documents/{document_id}
```

### Примеры использования:

```bash
#Загрузка документа
curl --location  --request POST 'http://localhost:8000/api/v1/documents/upload?user_id=123e4567-e89b-12d3-a456-426614174000' \
--form 'file=@"{path_to_file}"'

# Поиск по содержимому
curl --location --request GET 'http://localhost:8000/api/v1/documents/search?query={query}&user_id={user_id}&document_id={document_id}'

# Точный поиск
curl --location --request GET "http://localhost:8000/api/v1/documents/search?query=точная%20фраза&search_exact=true"

curl --location --request DELETE 'http://localhost:8000/api/v1/documents/3a82afcd-16bf-4768-9641-c3690238bcc3'
```
