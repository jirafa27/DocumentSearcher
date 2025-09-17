import re
import uuid
from typing import List, Optional
import string

from sqlalchemy import delete, func, select, text, desc
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
from app.models.document import DocumentContent as SQLDocumentContent
from app.core.utils.text_analyzer import text_analyzer


class DocumentRepository(IDocumentRepository):
    """Реализация репозитория для работы с документами в PostgreSQL"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def _generate_tsvector(self, content: str) -> str:
        """
        Генерирует tsvector для текстового содержимого в базе данных

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
        Удаление документа из базы данных

        Args:
            document_id: uuid.UUID - идентификатор документа
        """
        try:
            await self.session.execute(delete(SQLDocument).where(SQLDocument.id == document_id))
            await self.session.execute(delete(SQLDocumentContent).where(SQLDocumentContent.document_id == document_id))
            await self.session.commit()
        except SQLAlchemyError as e:
            raise RepositoryError(f"Ошибка при удалении документа {document_id}: {str(e)}")


    async def create(self, domain_document: DomainDocument):
        """
        Создание документа в базе данных
        Args:
            domain_document: DomainDocument - доменная модель документа
        Returns:
            DomainDocument: Созданная доменная модель документа
        Raises:
            RepositoryError: При ошибке создания документа
        """
        try:
            sql_document = SQLDocument(
                id=domain_document.id or uuid.uuid4(),
                user_id=domain_document.user_id,
                file_path=domain_document.file_path,
                file_name=domain_document.file_name,
                file_size=domain_document.file_size,
                file_type=domain_document.file_type,
                file_hash=domain_document.file_hash
            )
            self.session.add(sql_document)
            await self.session.flush()

            sql_document_content = SQLDocumentContent(
                id=uuid.uuid4(),
                document_id=sql_document.id,
                content=domain_document.content,
                tsvector_col=await self._generate_tsvector(domain_document.content)
            )
            self.session.add(sql_document_content)
            await self.session.commit()
        except SQLAlchemyError as e:
            await self.session.rollback()
            raise RepositoryError(f"Ошибка при создании документа {sql_document.id}: {str(e)}")
        return DomainDocument(
            id=sql_document.id,
            user_id=sql_document.user_id,
            file_path=sql_document.file_path,
            file_name=sql_document.file_name,
            file_size=sql_document.file_size,
            file_type=sql_document.file_type,
            file_hash=sql_document.file_hash,
            content=sql_document_content.content,
            uploaded_at=sql_document.uploaded_at,
        )


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
                select(SQLDocument, SQLDocumentContent)
                .join(SQLDocumentContent, 
                SQLDocumentContent.document_id == SQLDocument.id)
                .where(SQLDocument.file_hash == file_hash)
            )
            row = result.fetchone()

            if not row:
                return None

            document, document_content = row

            return DomainDocument(
                id=document.id,
                user_id=document.user_id,
                file_path=document.file_path,
                file_name=document.file_name,
                file_size=document.file_size,
                file_type=document.file_type,
                file_hash=document.file_hash,
                content=document_content.content,
                uploaded_at=document.uploaded_at,
            )
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
            query = select(SQLDocument, SQLDocumentContent)\
                .join(SQLDocumentContent, SQLDocumentContent.document_id == SQLDocument.id)\
                .where(SQLDocument.id == document_id)
            result = await self.session.execute(query)
            row = result.fetchone()

            if not row:
                return None

            document, document_content = row

            return DomainDocument(
                id=document.id,
                user_id=document.user_id,
                file_path=document.file_path,
                file_name=document.file_name,
                file_size=document.file_size,
                file_type=document.file_type,
                file_hash=document.file_hash,
                content=document_content.content,
                uploaded_at=document.uploaded_at,
            )
        except SQLAlchemyError as e:
            raise RepositoryError(
                f"Ошибка при получении документа {document_id}: {str(e)}"
            )


    def _filter_fragments_by_relevance(self, fragments: List[SearchFragment], query: str) -> List[SearchFragment]:
        """
        Фильтрует фрагменты по наличию всех значимых слов из запроса
        Использует морфологический анализ для более точного поиска
        Args:
            fragments: List[SearchFragment] - список фрагментов
            query: str - поисковый запрос
        Returns:
            List[SearchFragment]: Фрагменты, содержащие все значимые слова запроса
        """
        return [
            fragment for fragment in fragments 
            if text_analyzer.all_query_words_present(fragment.text, query)
        ]

    async def _search_fulltext(
        self,
        query: str,
        user_id: Optional[uuid.UUID] = None,
        document_id: Optional[uuid.UUID] = None,
        context_size_before: int = 50,
        context_size_after: int = 50,
    ) -> List[SearchResult]:
        """
        Полнотекстовый поиск для базы знаний с поддержкой морфологии.
        Ищет фразы в разных формах (например, "длинный день" найдет "длинные дни").
        Args:
            query: str - поисковый запрос
            user_id: Optional[uuid.UUID] - фильтр по пользователю
            document_id: Optional[uuid.UUID] - фильтр по документу
            context_size_before: int - размер контекста (слов) до выделения
            context_size_after: int - размер контекста (слов) после выделения

        Returns:
            List[SearchResult]: Список результатов поиска с документами и фрагментами
        """
        try:
            query_words_count = len(query.split(' '))
            min_words_limit = max(context_size_before+query_words_count+context_size_after, 10)
            min_words = min(min_words_limit, 100)
            max_words_limit = min_words*2
            # Создаем поисковый запрос с морфологией
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
                    # Выделение найденных фрагментов с подсветкой
                    func.ts_headline(
                        'russian',
                        SQLDocumentContent.content,
                        func.phraseto_tsquery('russian', query),
                        f"MaxFragments=100, MaxWords={max_words_limit}, MinWords={min_words}, "
                        f"StartSel=<mark>, StopSel=</mark>, ShortWord=0, HighlightAll=false"
                    ).label('highlighted_content'),
                    func.ts_rank(
                        SQLDocumentContent.tsvector_col,
                        func.phraseto_tsquery('russian', query)
                    ).label('rank'),
                )
                .select_from(
                    SQLDocument.__table__.join(
                        SQLDocumentContent.__table__,
                        SQLDocument.id == SQLDocumentContent.document_id,
                    )
                )
                .where(
                    SQLDocumentContent.tsvector_col.op('@@')(
                        func.phraseto_tsquery('russian', query)
                    )
                )
            ).order_by(desc('rank'))

            # Добавляем фильтры
            if user_id is not None:
                search_query = search_query.where(SQLDocument.user_id == user_id)
            if document_id is not None:
                search_query = search_query.where(SQLDocument.id == document_id)


            result = await self.session.execute(search_query)
            rows = result.fetchall()
            search_results = []
    
            for row in rows:
                highlighted_content = self._merge_phrase_highlights(row.highlighted_content)
                fragments = self._parse_ts_headline_fragments(highlighted_content, context_size_before, context_size_after)
                filtered_fragments = self._filter_fragments_by_relevance(fragments, query)
                if filtered_fragments:
                    search_document = SearchDocument(id=row.id,
                                                    user_id=row.user_id,
                                                    file_name=row.file_name,
                                                    file_type=row.file_type,
                                                    file_size=row.file_size,
                                                    file_path=row.file_path,
                                                    uploaded_at=row.uploaded_at,)  
                    search_results.append(SearchResult(document=search_document,
                                                        fragments=filtered_fragments))

            return search_results if search_results else []


        except SQLAlchemyError as e:
            raise RepositoryError(f"Ошибка при полнотекстовом поиске: {str(e)}")

    def _filter_results_for_exact_match(self, results: List[SearchResult], query: str) -> List[SearchResult]:
        """
        Фильтрует результаты поиска по точным совпадениям
        Args:
            results: List[SearchResult] - список результатов поиска
            query: str - поисковый запрос
        Returns:
            List[SearchResult]: Список результатов поиска с точными совпадениями
        """
        filtered_results = []
        
        for result in results:
            exact_fragments = []
            for fragment in result.fragments:
                if text_analyzer.normalize_text(fragment.text).strip() == text_analyzer.normalize_text(query).strip():
                    exact_fragments.append(fragment)
            
            if exact_fragments:
                filtered_results.append(SearchResult(
                    document=result.document,
                    fragments=exact_fragments
                ))
        
        return filtered_results


    async def _search_exact(
        self,
        query: str,
        user_id: Optional[uuid.UUID] = None,
        document_id: Optional[uuid.UUID] = None,
        context_size_before: int = 50,
        context_size_after: int = 50,
    ) -> List[SearchResult]:
        """
        Точный поиск фраз для базы знаний.
        Ищет точные фразы. Использует результаты полнотекстового поиска и фильтрует их по точным совпадениям.
        Args:
            query: str - поисковый запрос
            user_id: Optional[uuid.UUID] - фильтр по пользователю
            document_id: Optional[uuid.UUID] - фильтр по документу
            context_size_before: int - размер контекста (слов) до выделения
            context_size_after: int - размер контекста (слов) после выделения

        Returns:
            List[SearchResult]: Список результатов поиска с документами и фрагментами
        """
        try:
            full_text_result = await self._search_fulltext(query, user_id, document_id, context_size_before, context_size_after)
            filtered_results = self._filter_results_for_exact_match(full_text_result, query)
            return filtered_results
    
        except SQLAlchemyError as e:
            raise RepositoryError(f"Ошибка при точном поиске: {str(e)}")
                        

            
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
        """
        if search_exact:
            return await self._search_exact(query, user_id, document_id, context_size_before, context_size_after)
        else:
            return await self._search_fulltext(query, user_id, document_id, context_size_before, context_size_after)

    def _merge_phrase_highlights(self, highlighted_html: str) -> str:
        """
        Объединяет выделения, разделенные служебными словами и пунктуацией
        """
        
        def should_merge(between_text: str) -> bool:
            # Только пробелы или пунктуация
            clean_text = between_text.translate(str.maketrans('', '', string.punctuation)).strip()
            if not clean_text:
                return True
            
            # Проверяем значимость слов
            meaningful_words = text_analyzer.extract_meaningful_words(between_text)
            return len(meaningful_words) == 0  # Нет значимых слов = объединяем
        
        pattern = r'</mark>(.*?)<mark>'
        return re.sub(pattern, lambda m: m.group(1) if should_merge(m.group(1)) else m.group(0), highlighted_html)


    def _parse_ts_headline_fragments(self, highlighted_html: str, context_size_before: int, context_size_after: int) -> List[SearchFragment]:
        """
        Парсит фрагменты из ts_headline с подсветкой.
        Args:
            highlighted_html: str - html с подсветкой
            context_size_before: int - размер контекста (слов) до выделения
            context_size_after: int - размер контекста (слов) после выделения
        Returns:
            List[SearchFragment]: Список фрагментов с подсветкой
        """
        fragments = []
        if not highlighted_html:
            return fragments

        pattern = r'<mark>(.*?)</mark>'
        matches = re.finditer(pattern, highlighted_html, re.DOTALL | re.IGNORECASE)
        
        for match in matches:
            highlighted_text = match.group(1)
            start, end = match.span()

            # Получаем контекст до выделенного текста
            words_before = highlighted_html[:start].split(' ')
            start_index = max(0, len(words_before) - (context_size_before+1))
            context_before = ' '.join(words_before[start_index:])
            
            # Получаем контекст после выделенного текста
            words_after = highlighted_html[end:].split(' ')
            end_index = min(len(words_after), context_size_after+1)
            context_after = ' '.join(words_after[:end_index])

            content_before = context_before.replace('<mark>', '').replace('</mark>', '')
            content_after = context_after.replace('<mark>', '').replace('</mark>', '')


            context_text = f'{content_before}{highlighted_text}{content_after}'

            all_text_without_tags = highlighted_html.replace('<mark>', '').replace('</mark>', '')
            offset = all_text_without_tags.find(highlighted_text)

            if highlighted_text:
                fragments.append(SearchFragment(
                    text=highlighted_text,
                    context=ContextInfo(
                        text=context_text,
                        offset=offset,
                        length=len(context_text),
                        highlight_start=len(context_before),
                        highlight_length=len(highlighted_text)
                    )
                ))
        
        return fragments
