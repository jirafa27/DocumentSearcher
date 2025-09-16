import re
import uuid
import os
from typing import List, Optional

from sqlalchemy import func, select, text
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
            return self._to_domain_model(document) if document else None
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
            return self._to_domain_model(document) if document else None
        except SQLAlchemyError as e:
            raise RepositoryError(
                f"Ошибка при получении документа {document_id}: {str(e)}"
            )

    async def search_semantic(
        self,
        query: str,
        user_id: Optional[uuid.UUID] = None,
        document_id: Optional[uuid.UUID] = None,
        max_fragments: int = 3,
    ) -> List[SearchResult]:
        """
        Семантический поиск для базы знаний.
        Ищет по смыслу, а не по точному совпадению.
        """
        try:
            search_query = (
                select(
                    SQLDocument.id,
                    SQLDocument.user_id,
                    SQLDocument.file_path,
                    SQLDocument.file_name,
                    SQLDocument.file_size,
                    SQLDocument.file_type,
                    SQLDocument.file_hash,
                    SQLDocument.uploaded_at,
                    func.ts_headline(
                        'russian',
                        DocumentContent.content,
                        func.websearch_to_tsquery('russian', query),
                        f"MaxFragments={max_fragments}, MaxWords=50, MinWords=10, "
                        f"StartSel=<mark>, StopSel=</mark>, ShortWord=3"
                    ).label('highlighted_content'),
                    func.ts_rank_cd(
                        DocumentContent.tsvector_col,
                        func.websearch_to_tsquery('russian', query),
                    ).label('rank')
                )
                .select_from(
                    SQLDocument.__table__.join(
                        DocumentContent.__table__,
                        SQLDocument.id == DocumentContent.document_id,
                    )
                )
                .where(
                    DocumentContent.tsvector_col.op('@@')(
                        func.websearch_to_tsquery('russian', query)
                    )
                )
            )

            if user_id:
                search_query = search_query.where(SQLDocument.user_id == user_id)
            if document_id:
                search_query = search_query.where(SQLDocument.id == document_id)

            search_query = search_query.order_by(text('rank DESC'))

            result = await self.session.execute(search_query)
            rows = result.fetchall()

            search_results = []
            for row in rows:
                fragments = self._parse_ts_headline_fragments(row.highlighted_content)
                
                search_results.append(
                    SearchResult(
                        document=self._to_search_document_from_row(row),
                        fragments=fragments,
                        rank=float(row.rank) if row.rank else 0.0,
                    )
                )

            return search_results

        except SQLAlchemyError as e:
            logger.error(f"Ошибка семантического поиска '{query}': {e}")
            raise RepositoryError(f"Ошибка при семантическом поиске: {str(e)}")

    def _parse_ts_headline_fragments(self, highlighted_html: str) -> List[SearchFragment]:
        """
        Парсит готовые сниппеты из ts_headline.
        Просто извлекаем подсвеченные части - не нужно восстанавливать позиции.
        """
        fragments = []
        if not highlighted_html:
            return fragments

        
        pattern = r'<mark>(.*?)</mark>'
        matches = re.finditer(pattern, highlighted_html, re.DOTALL | re.IGNORECASE)
        
        for match in matches:
            highlighted_text = match.group(1)
            if highlighted_text.strip():
                fragments.append(SearchFragment(
                    text=highlighted_text,
                    context=ContextInfo(
                        text=highlighted_text,
                        offset=0,
                        length=len(highlighted_text),
                        highlight_start=0,
                        highlight_length=len(highlighted_text)
                    )
                ))
        
        return fragments



    def _to_search_document_from_row(self, row) -> SearchDocument:
        """Конвертация строки результата запроса в модель поиска (без содержимого)"""

        file_name = os.path.basename(row.file_path) if row.file_path else "unknown"

        return SearchDocument(
            id=row.id,
            user_id=row.user_id,
            file_name=file_name,
            file_type=row.file_type,
            uploaded_at=row.uploaded_at,
        )
