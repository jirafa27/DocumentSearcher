import uuid
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

from app.core.models.document import Document
from app.core.models.search import SearchResult


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

class SearchMeta(BaseModel):
    """Метаинформация о поиске"""

    query: str = Field(..., description="Поисковый запрос")
    context_size_before: Optional[int] = Field(..., description="Размер контекста до выделения")
    context_size_after: Optional[int] = Field(..., description="Размер контекста после выделения")
    total_documents: int = Field(..., description="Общее количество найденных документов")
    total_fragments: int = Field(..., description="Общее количество найденных фрагментов")

class DocumentSearchResponse(BaseModel):
    """Ответ на запрос поиска по документам"""

    status: ProcessingStatus = Field(..., description="Статус обработки")
    meta: SearchMeta = Field(..., description="Метаинформация о поиске")
    results: List[SearchResult] = Field(..., description="Результаты поиска")

    class Config:
        use_enum_values = True


class DocumentDeleteResponse(BaseModel):
    """Ответ на запрос удаления документа"""

    status: ProcessingStatus = Field(..., description="Статус обработки документа")
    message: Optional[str] = Field(None, description="Сообщение о статусе")
    document_id: uuid.UUID = Field(..., description="ID документа")
