import uuid
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

from app.core.models.document import Document
from app.core.models.search import ContextInfo, HighlightInfo, SearchDocument


class ProcessingStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"


class DocumentUploadResponse(BaseModel):
    """Схема ответа при загрузке документа"""

    status: ProcessingStatus = Field(..., description="Статус обработки документа")
    message: Optional[str] = Field(None, description="Сообщение о статусе")
    document: Document = Field(..., description="Информация о документе")

    class Config:
        use_enum_values = True
        from_attributes = True


class DocumentGetResponse(Document):
    """Схема ответа при получении информации о документе"""

    class Config:
        from_attributes = True


class HighlightInfo(BaseModel):
    """Информация о выделении текста"""

    start: int = Field(..., description="Начальная позиция выделения")
    length: int = Field(..., description="Длина выделенного текста")


class ContextInfo(BaseModel):
    """Информация о контексте фрагмента"""

    text: str = Field(..., description="Полный контекстный текст")
    offset: int = Field(..., description="Смещение от начала документа")
    length: int = Field(..., description="Длина контекстного текста")
    highlight_start: int = Field(..., description="Позиция выделения в контексте")
    highlight_length: int = Field(..., description="Длина выделенного текста")


class SearchFragment(BaseModel):
    """Фрагмент текста с найденным совпадением"""

    text: str = Field(..., description="Найденный текст")
    context: ContextInfo = Field(..., description="Контекст вокруг совпадения")


class SearchDocumentResult(BaseModel):
    """Результат поиска - документ с найденными фрагментами"""

    document: SearchDocument = Field(..., description="Информация о документе")
    fragments: List[SearchFragment] = Field(
        ..., description="Найденные фрагменты текста"
    )

    class Config:
        from_attributes = True


class SearchMeta(BaseModel):
    """Метаинформация о поиске"""

    query: str = Field(..., description="Поисковый запрос")
    context_size: int = Field(..., description="Размер контекста")
    total_documents: int = Field(
        ..., description="Общее количество найденных документов"
    )
    total_fragments: int = Field(
        ..., description="Общее количество найденных фрагментов"
    )


class DocumentSearchResponse(BaseModel):
    """Ответ на запрос поиска по документам"""

    status: ProcessingStatus = Field(..., description="Статус обработки")
    meta: SearchMeta = Field(..., description="Метаинформация о поиске")
    results: List[SearchDocumentResult] = Field(..., description="Результаты поиска")

    class Config:
        use_enum_values = True


class DocumentDeleteResponse(BaseModel):
    """Ответ на запрос удаления документа"""

    status: ProcessingStatus = Field(..., description="Статус обработки документа")
    message: Optional[str] = Field(None, description="Сообщение о статусе")
    document_id: uuid.UUID = Field(..., description="ID документа")
