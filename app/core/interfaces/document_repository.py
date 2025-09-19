import uuid
from abc import ABC, abstractmethod
from typing import List, Optional

from app.core.models.document import Document, DocumentBase
from app.core.models.search import SearchResult


class IDocumentRepository(ABC):
    @abstractmethod
    async def get_by_id(self, document_id: uuid.UUID) -> Optional[DocumentBase]:
        """
        Получение документа по ID

        Args:
            document_id: uuid.UUID - идентификатор документа

        Returns:
            Optional[DocumentBase]: Доменная модель документа или None если не найден

        Raises:
            RepositoryError: При ошибке выполнения запроса к БД
        """
        raise NotImplementedError

    @abstractmethod
    async def create(self, document: Document) -> DocumentBase:
        """
        Создание документа в базе данных
        Args:
            document: Document - доменная модель документа
        Returns:
            DocumentBase: Созданная доменная модель документа
        Raises:
            RepositoryError: При ошибке создания документа
        """
        raise NotImplementedError

    @abstractmethod
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
            RepositoryError: При ошибке выполнения поиска
        """
        raise NotImplementedError

    @abstractmethod
    async def get_by_hash(self, file_hash: str) -> Optional[Document]:
        """
        Получение документа из базы данных по хешу файла

        Args:
            file_hash: str - хеш файла

        Returns:
            Optional[Document]: Доменная модель документа или None если не найден

        Raises:
            RepositoryError: При ошибке выполнения запроса к БД
        """
        raise NotImplementedError

    @abstractmethod
    async def delete(self, document_id: uuid.UUID) -> None:
        """
        Удаление документа из базы данных

        Args:
            document_id: uuid.UUID - идентификатор документа

        Raises:
            RepositoryError: При ошибке удаления из БД
        """
        raise NotImplementedError
