import os
import uuid
from typing import List, Optional

from app.core.exceptions.document import (
    DocumentAlreadyExistsError,
    DocumentDatabaseError,
    DocumentNotFoundError,
    DocumentValidationError,
)
from app.core.exceptions.file import FileDeleteError, FileValidationError
from app.core.exceptions.repository import RepositoryError
from app.core.interfaces.document_repository import IDocumentRepository
from app.core.interfaces.file_service import IFileService
from app.core.logger import logger
from app.core.models.document import Document, DocumentBase
from app.core.models.file import FileContent
from app.core.models.search import SearchResult


class DocumentService:
    """Сервис для работы с документами"""

    def __init__(self, repository: IDocumentRepository, file_service: IFileService):
        self.repository = repository
        self.file_service = file_service

    async def upload_document(
        self, file: FileContent, user_id: uuid.UUID
    ) -> DocumentBase:
        """
        Загрузка и обработка документа

        Args:
            file: FileContent - файл
            user_id: uuid.UUID - ID пользователя

        Returns:
            DocumentBase: Документ

        Raises:
            DocumentValidationError: Если не удалось валидировать документ
            DocumentAlreadyExistsError: Если документ с таким содержимым уже существует
            DocumentDatabaseError: Если не удалось сохранить документ в базу данных
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

            if not content.strip():
                raise DocumentValidationError(
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
            return DocumentBase.model_validate(document.model_dump(exclude={"content"}))

        except DocumentAlreadyExistsError as e:
            logger.info(
                f"Попытка загрузить дублирующийся документ {file.filename}: {e}"
            )
            raise

        except FileValidationError as e:
            if file_path and os.path.exists(file_path):
                await self.file_service.delete_file(file_path)
            logger.info(
                f"Ошибка валидации файла {file.filename} от пользователя {user_id}: {str(e)}"
            )
            raise DocumentValidationError(str(e))

        except RepositoryError as e:
            if file_path and os.path.exists(file_path):
                await self.file_service.delete_file(file_path)
            logger.error(
                f"Ошибка базы данных при сохранении документа {file.filename} от пользователя {user_id}: {e}"
            )
            raise DocumentDatabaseError(f"Не удалось сохранить документ: {str(e)}")

        except Exception as e:
            if file_path and os.path.exists(file_path):
                await self.file_service.delete_file(file_path)
            logger.error(
                f"Неожиданная ошибка при загрузке документа {file.filename}: {e}"
            )
            raise e

    async def delete_document(self, document_id: uuid.UUID) -> None:
        """
        Удаление документа и файла

        Args:
            document_id: uuid.UUID - ID документа

        Raises:
            DocumentNotFoundError: Если документ не найден
            DocumentDatabaseError: Если не удалось удалить документ из базы данных
        """
        logger.info(f"Удаление документа: {document_id}")
        try:
            document = await self.repository.get_by_id(document_id)
            if not document:
                raise DocumentNotFoundError(str(document_id))

            await self.repository.delete(document_id)
            logger.info(f"Документ {document_id} успешно удален")

            if document.file_path:
                await self.file_service.delete_file(document.file_path)
                logger.info(f"Файл {document.file_path} успешно удален")

            logger.info(f"Документ {document_id} успешно удален")
        except RepositoryError as e:
            logger.error(
                f"Критическая ошибка БД при удалении документа {document_id}: {e}"
            )
            raise DocumentDatabaseError(str(e))
        except FileDeleteError as e:
            logger.warning(
                f"Документ {document_id} удален, но не удалось очистить файл: {e}"
            )
        except Exception as e:
            logger.error(
                f"Неожиданная ошибка при удалении документа {document_id}: {e}"
            )
            raise e

    async def search(
        self,
        query: str,
        user_id: Optional[uuid.UUID] = None,
        document_id: Optional[uuid.UUID] = None,
        context_size_before: int = 50,
        context_size_after: int = 50,
        search_exact: bool = False,
    ) -> List[SearchResult]:
        """
        Поиск документов с фрагментами текста

        Args:
            query: str - поисковый запрос
            user_id: Optional[uuid.UUID] - фильтр по пользователю
            document_id: Optional[uuid.UUID] - фильтр по документу
            context_size_before: int - размер контекста (слов) до выделения
            context_size_after: int - размер контекста (слов) после выделения
            search_exact: bool - поиск точного совпадения

        Returns:
            List[SearchResult]: Список результатов поиска с документами и фрагментами

        Raises:
            DocumentDatabaseError: При ошибке поиска
        """
        logger.info(f"Поиск документов по запросу: '{query}', user_id: {user_id}")
        try:
            results = await self.repository.search(
                query,
                user_id,
                document_id,
                context_size_before,
                context_size_after,
                search_exact,
            )
            return results
        except RepositoryError as e:
            logger.error(f"Критическая ошибка БД при поиске документов: {e}")
            raise DocumentDatabaseError(str(e))

    async def get_document(self, document_id: uuid.UUID) -> DocumentBase:
        """
        Получение метаданных документа по ID

        Args:
            document_id: uuid.UUID - ID документа

        Returns:
            DocumentBase: Доменная модель метаданных документа

        Raises:
            DocumentNotFoundError: Если документ не найден
            DocumentDatabaseError: Если не удалось получить документ из базы данных
        """
        try:
            logger.info(f"Получение метаданных документа: {document_id}")
            document = await self.repository.get_by_id(document_id)
            if not document:
                raise DocumentNotFoundError(str(document_id))
            logger.info(f"Метаданные документа {document_id} успешно получены")
            return DocumentBase.model_validate(document.model_dump(exclude={"content"}))
        except RepositoryError as e:
            logger.error(
                f"Критическая ошибка БД при получении метаданных документа {document_id}: {e}"
            )
            raise DocumentDatabaseError(str(e))
