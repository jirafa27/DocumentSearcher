import os
import uuid
from typing import List, Optional

from app.core.exceptions.document import (
    DocumentAlreadyExistsError,
    DocumentDatabaseError,
    DocumentError,
    DocumentNotFoundError,
)
from app.core.exceptions.file import FileError, TextExtractionError
from app.core.exceptions.repository import RepositoryError
from app.core.interfaces.document_repository import IDocumentRepository
from app.core.interfaces.file_service import IFileService
from app.core.logger import logger
from app.core.models.document import Document
from app.core.models.file import FileContent
from app.core.models.search import SearchResult


class DocumentService:
    """Сервис для работы с документами"""

    def __init__(self, repository: IDocumentRepository, file_service: IFileService):
        self.repository = repository
        self.file_service = file_service

    async def upload_document(self, file: FileContent, user_id: uuid.UUID) -> Document:
        """
        Загрузка и обработка документа

        Args:
            file: FileContent - файл
            user_id: uuid.UUID - ID пользователя

        Returns:
            Document: Документ

        Raises:
            DocumentAlreadyExistsError: Если документ с таким содержимым уже существует
            DocumentError: Если не удалось обработать документ
        """
        file_path = None
        try:
            # Читаем содержимое один раз
            content_bytes = file.get_content_bytes()
            file_hash = await self.file_service.calculate_hash(content_bytes)

            existing_document = await self.repository.get_by_hash(file_hash)
            if existing_document:
                raise DocumentAlreadyExistsError(file_hash)

            # Валидируем файл
            await self.file_service.validate_file(file.filename, content_bytes)

            file_type = file.filename.split(".")[-1].lower()
            file_path = await self.file_service.save_file(
                file.filename, content_bytes, file_hash
            )
            file_size = len(content_bytes)
            content = await self.file_service.extract_text(file_path, file_type)
            logger.debug(f"Извлечен текст из файла: {file.content}")

            if not content.strip():
                raise TextExtractionError(
                    "Не удалось извлечь текст из файла или файл пуст"
                )

            document_data = Document(
                user_id=user_id,
                file_name=file.filename,
                file_path=file_path,
                file_size=file_size,
                file_type=file_type,
                file_hash=file_hash,
                content=content,
            )
            document = await self.repository.create(document_data)

            logger.info(f"Документ успешно загружен: {document.id}")
            return document

        except DocumentAlreadyExistsError as e:
            logger.info(
                f"Попытка загрузить дублирующийся документ {file.filename}: {e}"
            )
            raise

        except FileError as e:
            if file_path and os.path.exists(file_path):
                await self.file_service.delete_file(file_path)
            raise DocumentError(f"Не удалось обработать файл: {str(e)}")

        except RepositoryError as e:
            if file_path and os.path.exists(file_path):
                await self.file_service.delete_file(file_path)
            logger.error(f"Критическая ошибка БД при сохранении документа: {e}")
            raise DocumentDatabaseError(f"Не удалось сохранить документ: {str(e)}")

        except Exception as e:
            if file_path and os.path.exists(file_path):
                await self.file_service.delete_file(file_path)
            logger.error(
                f"Неожиданная ошибка при загрузке документа {file.filename}: {e}"
            )
            raise DocumentError(f"Не удалось загрузить документ: {str(e)}")

    async def delete_document(self, document_id: uuid.UUID) -> None:
        """
        Удаление документа и файла

        Args:
            document_id: uuid.UUID - ID документа

        Raises:
            DocumentNotFoundError: Если документ не найден
            DocumentError: При ошибке удаления
        """
        logger.info(f"Удаление документа: {document_id}")
        try:
            document = await self.repository.get_by_id(document_id)
            if not document:
                raise DocumentNotFoundError(str(document_id))

            deleted = await self.repository.delete(document_id)
            if not deleted:
                raise DocumentError(f"Не удалось удалить документ: {str(document_id)}")
            else:
                logger.info(f"Документ {document_id} успешно удален")
        except RepositoryError as e:
            logger.error(
                f"Критическая ошибка БД при удалении документа {document_id}: {e}"
            )
            raise DocumentError(f"Не удалось удалить документ: {str(document_id)}")

        if document.file_path:
            try:
                await self.file_service.delete_file(document.file_path)
                logger.info(f"Файл {document.file_path} успешно удален")
            except FileError as e:
                logger.error(
                    f"Не удалось удалить файл {document.file_path} из файловой системы: {e}"
                )

        logger.info(f"Документ {document_id} успешно удален")

    async def search_documents(
        self,
        query: str,
        user_id: Optional[uuid.UUID] = None,
        document_id: Optional[uuid.UUID] = None,
        context_size: int = 50,
    ) -> List[SearchResult]:
        """
        Поиск документов с фрагментами текста

        Args:
            query: str - поисковый запрос
            user_id: Optional[uuid.UUID] - фильтр по пользователю
            document_id: Optional[uuid.UUID] - фильтр по документу
            context_size: int - размер контекста (символов)

        Returns:
            List[SearchResult]: Список результатов поиска с документами и фрагментами

        Raises:
            DocumentError: При ошибке поиска
        """
        logger.info(f"Поиск документов по запросу: '{query}', user_id: {user_id}")
        try:
            return await self.repository.search(
                query, user_id, document_id, context_size
            )
        except RepositoryError as e:
            logger.error(f"Критическая ошибка БД при поиске документов: {e}")
            raise DocumentError(f"Ошибка поиска: {str(e)}")

    async def get_document(self, document_id: uuid.UUID) -> Document:
        """
        Получение документа по ID

        Args:
            document_id: uuid.UUID - ID документа

        Returns:
            Document: Доменная модель документа

        Raises:
            DocumentNotFoundError: Если документ не найден
        """
        try:
            document = await self.repository.get_by_id(document_id)
            if not document:
                raise DocumentNotFoundError(str(document_id))
            return document
        except RepositoryError as e:
            logger.error(
                f"Критическая ошибка БД при получении документа {document_id}: {e}"
            )
            raise DocumentNotFoundError(str(document_id))
