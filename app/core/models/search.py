import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class SearchDocument:
    """Модель документа для результатов поиска (без содержимого)"""

    id: uuid.UUID
    user_id: uuid.UUID
    file_name: str  # Только имя файла без пути
    file_type: str
    uploaded_at: Optional[datetime] = None


@dataclass
class HighlightInfo:
    """Информация о выделении текста"""

    start: int
    length: int


@dataclass
class ContextInfo:
    """Информация о контексте фрагмента"""

    text: str  # Полный контекстный текст
    offset: int  # Смещение от начала документа
    length: int  # Длина контекстного текста
    highlight_start: int  # Позиция выделения в контексте
    highlight_length: int  # Длина выделенного текста


@dataclass
class SearchFragment:
    """Фрагмент текста с найденным совпадением"""

    text: str  # Найденный текст
    context: ContextInfo  # Контекст вокруг совпадения


@dataclass
class SearchResult:
    """Результат поиска документа с фрагментами"""

    document: SearchDocument
    fragments: List[SearchFragment]
    rank: float = 0.0
