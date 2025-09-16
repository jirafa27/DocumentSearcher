import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class Document(BaseModel):
    """Доменная модель документа"""

    id: Optional[uuid.UUID] = None
    user_id: uuid.UUID
    file_path: str
    file_name: str  # Оригинальное имя файла
    file_size: int
    file_type: str
    file_hash: str
    content: str = ""
    uploaded_at: Optional[datetime] = None

    class Config:
        from_attributes = True
