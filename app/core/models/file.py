from tempfile import SpooledTemporaryFile
from typing import BinaryIO, Optional, Union

from pydantic import BaseModel, field_validator


class FileContent(BaseModel):
    """Модель содержимого файла"""

    filename: str
    content: Union[BinaryIO, SpooledTemporaryFile, bytes]  # Добавили bytes
    file_hash: Optional[str] = None
    size: int
    content_type: str

    class Config:
        arbitrary_types_allowed = True

    @field_validator("content")
    @classmethod
    def validate_content(cls, v):
        """Проверяем, что content является файловым объектом или bytes"""
        if isinstance(v, bytes):
            return v
        if not hasattr(v, "read"):
            raise ValueError("content должен быть файловым объектом или bytes")
        return v

    @property
    def file_extension(self) -> str:
        """Получить расширение файла"""
        return self.filename.split(".")[-1].lower() if "." in self.filename else ""

    def get_content_bytes(self) -> bytes:
        """Получить содержимое как bytes"""
        if isinstance(self.content, bytes):
            return self.content
        else:
            # Читаем из потока
            self.content.seek(0)
            data = self.content.read()
            self.content.seek(0)  # Возвращаем указатель в начало
            return data
