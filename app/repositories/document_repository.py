import asyncio
import re
import uuid
from typing import List, Optional

from sqlalchemy import delete, func, insert, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions.repository import RepositoryError
from app.core.interfaces.document_repository import IDocumentRepository
from app.core.logger import logger
from app.core.models.document import Document as DomainDocument
from app.core.models.search import (
    ContextInfo,
    SearchDocument,
    SearchFragment,
    SearchResult,
)
from app.models.document import Document as SQLDocument
from app.models.document import DocumentContent


class DocumentRepository(IDocumentRepository):
    """Реализация репозитория для работы с документами в PostgreSQL"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def _generate_tsvector(self, content: str) -> str:
        """
        Генерирует tsvector для текстового содержимого

        Args:
            content: str - текстовое содержимое

        Returns:
            str: tsvector в виде строки
        """
        try:
            result = await self.session.execute(
                text("SELECT to_tsvector('russian', :content)"),
                {"content": content},
            )
            return result.scalar()
        except Exception as e:
            logger.error(f"Ошибка при генерации tsvector: {e}")
            return ""


    async def delete(self, document_id: uuid.UUID):
        """
        Удаление документа

        Args:
            document_id: uuid.UUID - идентификатор документа
        """
        try:
            await self.session.execute(delete(SQLDocument).where(SQLDocument.id == document_id))
            await self.session.commit()
        except SQLAlchemyError as e:
            raise RepositoryError(f"Ошибка при удалении документа {document_id}: {str(e)}")


    async def create(self, document: DomainDocument):
        """
        Создание документа
        """
        try:
            await self.session.execute(insert(SQLDocument).values(document))
            await self.session.execute(insert(DocumentContent).values(document.content))
            await self.session.commit()
        except SQLAlchemyError as e:
            raise RepositoryError(f"Ошибка при создании документа {document.id}: {str(e)}")
        return document


    async def get_by_hash(self, file_hash: str) -> Optional[DomainDocument]:
        """
        Получение документа по хешу файла

        Args:
            file_hash: str - хеш файла

        Returns:
            Optional[DomainDocument]: Доменная модель документа или None если не найден
        """
        try:
            result = await self.session.execute(
                select(SQLDocument).where(SQLDocument.file_hash == file_hash)
            )
            document = result.scalar_one_or_none()
            return await self._to_domain_model(document) if document else None
        except SQLAlchemyError as e:
            raise RepositoryError(f"Ошибка при получении документа {file_hash}: {str(e)}")

    async def get_by_id(self, document_id: uuid.UUID) -> Optional[DomainDocument]:
        """
        Получение документа по ID

        Args:
            document_id: uuid.UUID - идентификатор документа

        Returns:
            Optional[DomainDocument]: Доменная модель документа или None если не найден
        """
        try:
            result = await self.session.execute(
                select(SQLDocument).where(SQLDocument.id == document_id)
            )
            document = result.scalar_one_or_none()
            return await self._to_domain_model(document) if document else None
        except SQLAlchemyError as e:
            raise RepositoryError(
                f"Ошибка при получении документа {document_id}: {str(e)}"
            )

    async def _search_fulltext(
        self,
        query: str,
        user_id: Optional[uuid.UUID] = None,
        document_id: Optional[uuid.UUID] = None,
        max_fragments: int = 3,
    ) -> List[SearchResult]:
        """
        Полнотекстовый поиск для базы знаний.
        Args:
            query: str - поисковый запрос
            user_id: Optional[uuid.UUID] - фильтр по пользователю
            document_id: Optional[uuid.UUID] - фильтр по документу
            max_fragments: int - максимальное количество фрагментов

        Returns:
            List[SearchResult]: Список результатов поиска с документами и фрагментами

        Raises:
            RepositoryError: При ошибке выполнения поиска
        """
        try:
            search_results = []
            return search_results

        except SQLAlchemyError as e:
            logger.error(f"Ошибка семантического поиска '{query}': {e}")
            raise RepositoryError(f"Ошибка при семантическом поиске: {str(e)}")

    async def _search_exact(
        self,
        query: str,
        user_id: Optional[uuid.UUID] = None,
        document_id: Optional[uuid.UUID] = None,
        context_size: int = 50,
    ) -> List[SearchResult]:
        """
        Точный поиск для базы знаний.
        Args:
            query: str - поисковый запрос
            user_id: Optional[uuid.UUID] - фильтр по пользователю
            document_id: Optional[uuid.UUID] - фильтр по документу

        Returns:
            List[SearchResult]: Список результатов поиска с документами и фрагментами

        Raises:
            RepositoryError: При ошибке выполнения поиска
        """
        try:

            query_param = f"%{query}%"
            
            conditions = [DocumentContent.content.ilike(query_param)]
            
            if user_id is not None:
                conditions.append(SQLDocument.user_id == user_id)
            if document_id is not None:
                conditions.append(SQLDocument.id == document_id)
            
            stmt = (
                select(DocumentContent, SQLDocument)
                .join(SQLDocument, SQLDocument.id == DocumentContent.document_id)
                .where(*conditions)
            )
            
            result = await self.session.execute(stmt)
            results = result.fetchall()
            search_results = []
            for document_content, sql_document in results:
                search_results.append(await self._to_search_result_exact(document_content, sql_document, query, context_size))
            return search_results

        except SQLAlchemyError as e:
            raise RepositoryError(f"Ошибка при точном поиске: {str(e)}")
            
    async def search(
        self,
        query: str,
        user_id: Optional[uuid.UUID] = None,
        document_id: Optional[uuid.UUID] = None,
        context_size: int = 50,
        search_exact: bool = False,
    ) -> List[SearchResult]:
        """
        Поиск документов с фрагментами текста
        """
        if search_exact:
            return await self._search_exact(query, user_id, document_id, context_size)
        else:
            return await self._search_fulltext(query, user_id, document_id, context_size)


    async def _to_domain_model(self, document) -> DomainDocument:
        """
        Преобразует SQL модель документа в доменную модель
        """
        return DomainDocument(
            id=document.id,
            user_id=document.user_id,
            file_path=document.file_path,
            file_name=document.file_name,
            file_size=document.file_size,
            file_type=document.file_type,
            file_hash=document.file_hash,
            content=document.content,
            uploaded_at=document.uploaded_at,
        )


    
    async def _to_search_result_exact(self, document_content: DocumentContent, document_model: SQLDocument, query: str, context_size: int) -> SearchResult:
        """
        Преобразует SQL модель документа в результат поиска
        """
        fragments = []
        for match in re.finditer(query, document_content.content):
            match_start = match.start()
            match_length = len(query)
            context_start = match_start - context_size if match_start - context_size > 0 else 0
            context_end = match_start + match_length + context_size \
                          if match_start + match_length + context_size < len(document_content.content) \
                          else len(document_content.content)

            context_text = document_content.content[context_start:context_end]
            highlight_start = re.search(query, context_text).start()
            highlight_length = len(query)
            search_fragment = SearchFragment(text=match.group(), 
                               context=ContextInfo(text=context_text, 
                                                   offset=match_start, 
                                                   length=match_length, 
                                                   highlight_start=highlight_start, 
                                                   highlight_length=highlight_length))
            fragments.append(search_fragment)
        return SearchResult(
            document=SearchDocument(id=document_content.document_id, 
                                    user_id=document_model.user_id,
                                    file_size=document_model.file_size,
                                    file_path=document_model.file_path,
                                    file_name=document_model.file_name, 
                                    file_type=document_model.file_type, 
                                    uploaded_at=document_model.uploaded_at),
            fragments=fragments,
        )
