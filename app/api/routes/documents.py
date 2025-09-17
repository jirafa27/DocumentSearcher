import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile

from app.api.dependencies import get_document_service
from app.core.exceptions.document import (
    DocumentAlreadyExistsError,
    DocumentDatabaseError,
    DocumentError,
    DocumentNotFoundError,
)
from app.core.logger import logger
from app.core.models.file import FileContent
from app.schemas.document import (
    DocumentDeleteResponse,
    DocumentGetResponse,
    DocumentSearchResponse,
    DocumentUploadResponse,
    ProcessingStatus,
    SearchMeta,
)
from app.services.document_service import DocumentService

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    user_id: uuid.UUID = Query(..., description="ID пользователя"),
    document_service: DocumentService = Depends(get_document_service),
) -> DocumentUploadResponse:
    """
    Сохраняет документ в БД и файловой системе

    Args:
    - file: PDF или DOCX файл (максимум 20MB)
    - user_id: Уникальный идентификатор пользователя

    Returns:
    - DocumentUploadResponse: Ответ на запрос

    Raises:
    - HTTPException: 400 - Ошибка при загрузке документа
    - HTTPException: 500 - Внутренняя ошибка сервера
    """
    try:
        # Проверяем, что файл имеет имя
        if not file.filename:
            raise HTTPException(
                status_code=400, detail="Имя файла не может быть пустым"
            )

        logger.debug(f"Начало загрузки документа: {file.filename}")

        file_content = FileContent(
            filename=file.filename,
            content=file.file,
            size=file.size or 0,
            content_type=file.content_type or "application/octet-stream",
        )

        document = await document_service.upload_document(file_content, user_id)
        logger.info(f"Документ {document.id} успешно загружен")

        return DocumentUploadResponse(
            document=document,
            status=ProcessingStatus.SUCCESS,
            message="Документ успешно загружен",
        )
    except DocumentAlreadyExistsError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DocumentDatabaseError as e:
        logger.error(f"Ошибка БД при загрузке документа: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")
    except DocumentError as e:
        logger.error(f"Ошибка при загрузке документа: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")
    except Exception as e:
        logger.error(f"Неожиданная ошибка при загрузке документа: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search", response_model=DocumentSearchResponse)
async def search_fragments(
    query: str = Query(..., description="Строка поиска", min_length=1),
    search_exact: bool = Query(False, description="Поиск точного совпадения"),
    user_id: Optional[uuid.UUID] = Query(
        None, description="ID пользователя (опционально)"
    ),
    document_id: Optional[uuid.UUID] = Query(
        None, description="ID документа (опционально)"
    ),
    context_size_before: Optional[int] = Query(
        50, description="Размер контекста (слов)", ge=0, le=1000
    ),
    context_size_after: Optional[int] = Query(
        50, description="Размер контекста (слов)", ge=0, le=1000
    ),
    document_service: DocumentService = Depends(get_document_service),
):
    """
    Поиск фрагментов в документах

    Args:
    - query: Строка поиска (обязательный параметр)
    - search_exact: Поиск точного совпадения (опционально)
    - user_id: Фильтр по пользователю (опционально)
    - document_id: Поиск в конкретном документе (опционально)
    - context_size_before: Размер контекста (слов) до выделения (опционально)
    - context_size_after: Размер контекста (слов) после выделения (опционально)

    Returns:
    - DocumentSearchResponse: Ответ на запрос с фрагментами

    Raises:
    - HTTPException: 400 - Ошибка при поиске документов
    - HTTPException: 500 - Внутренняя ошибка сервера

    Возвращает список документов и их фрагментов, где найдено совпадение с запросом
    """

    try:
        results = await document_service.search(
            query, user_id, document_id, context_size_before, context_size_after, search_exact
        )
        logger.info(f"Найдено {len(results)} документов")

        total_fragments = 0

        for document in results:
            total_fragments += len(document.fragments)

        return DocumentSearchResponse(
            status=ProcessingStatus.SUCCESS,
            meta=SearchMeta(
                query=query,
                context_size_before=context_size_before,
                context_size_after=context_size_after,
                total_documents=len(results),
                total_fragments=total_fragments,
            ),
            results=results,
        )
    except DocumentError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Неожиданная ошибка при поиске документов: {e}")
        raise HTTPException(
            status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}"
        )


@router.get("/{document_id}", response_model=DocumentGetResponse)
async def get_document(
    document_id: uuid.UUID,
    document_service: DocumentService = Depends(get_document_service),
) -> DocumentGetResponse:
    """
    Получение метаинформации о документе

    - document_id: Уникальный идентификатор документа

    Returns:
    - DocumentGetResponse: Ответ на запрос

    Raises:
    - HTTPException: 404 - Документ не найден
    - HTTPException: 400 - Ошибка при получении документа
    - HTTPException: 500 - Внутренняя ошибка сервера
    """
    try:
        document = await document_service.get_document(document_id)
        return document
    except DocumentNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DocumentError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}"
        )


@router.delete("/{document_id}")
async def delete_document(
    document_id: uuid.UUID,
    document_service: DocumentService = Depends(get_document_service),
):
    """
    Удаляет документ и его содержимое из БД и файловой системы

    - document_id: Уникальный идентификатор документа

    Returns:
    - DocumentDeleteResponse: Ответ на запрос

    Raises:
    - HTTPException: 404 - Документ не найден
    - HTTPException: 400 - Ошибка при удалении документа
    - HTTPException: 500 - Внутренняя ошибка сервера
    """
    try:
        await document_service.delete_document(document_id)
        logger.info(f"Документ {document_id} успешно удален")
        return DocumentDeleteResponse(
            status=ProcessingStatus.SUCCESS,
            message="Документ успешно удален",
            document_id=document_id,
        )
    except DocumentNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DocumentError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Неожиданная ошибка при удалении документа {document_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Неожиданная ошибка: {str(e)}")
