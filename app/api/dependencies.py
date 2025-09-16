from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.repositories.document_repository import DocumentRepository
from app.services.document_service import DocumentService
from app.services.file_service import FileService


def get_document_service(
    session: AsyncSession = Depends(get_async_session),
) -> DocumentService:
    """Dependency для получения сервиса документов с автоматическим управлением сессией"""
    return DocumentService(
        repository=DocumentRepository(session=session),
        file_service=FileService(),
    )
