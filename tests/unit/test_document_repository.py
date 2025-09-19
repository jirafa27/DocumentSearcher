import uuid
from unittest.mock import AsyncMock, Mock

import pytest

from app.core.models.search import (
    ContextInfo,
    SearchDocument,
    SearchFragment,
    SearchResult,
)
from app.repositories.document_repository import DocumentRepository


class TestDocumentRepositoryUnit:

    @pytest.fixture
    def repository(self):
        mock_session = Mock()
        return DocumentRepository(mock_session)

    @pytest.mark.asyncio
    async def test_search_exact_filters_matching_fragments(self, repository):
        """Тест что _search_exact оставляет только точные совпадения"""
        # Подготавливаем тестовые данные
        query = "точный запрос"

        mock_document = SearchDocument(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            file_size=1024,
            file_path="/path/to/file.pdf",
            file_type="pdf",
            file_name="test.pdf",
        )

        mock_context = ContextInfo(
            text="Это точный запрос в контексте",
            offset=0,
            length=30,
            highlight_start=4,
            highlight_length=len(query),
        )

        # Мокаем результат _search_fulltext
        mock_fulltext_results = [
            SearchResult(
                document=mock_document,
                fragments=[
                    SearchFragment(
                        text="точный запрос", context=mock_context
                    ),  # Точное совпадение
                    SearchFragment(
                        text="точные запросы", context=mock_context
                    ),  # Не точное
                    SearchFragment(
                        text="Точный Запрос", context=mock_context
                    ),  # Еще одно точное
                ],
            ),
            SearchResult(
                document=mock_document,
                fragments=[
                    SearchFragment(
                        text="контекст без совпадений", context=mock_context
                    ),
                    SearchFragment(text="точный запрос", context=mock_context),
                    SearchFragment(text="Точный Запрос", context=mock_context),
                ],
            ),
        ]

        # Мокаем _search_fulltext
        repository._search_fulltext = AsyncMock(return_value=mock_fulltext_results)

        # Выполняем тест
        results = await repository._search_exact(query)

        # Проверяем результаты
        assert len(results) == 2
        assert len(results[0].fragments) == 2
        assert len(results[1].fragments) == 2

        for result in results:
            for fragment in result.fragments:
                assert fragment.text.lower() == query.lower()

        # Проверяем что _search_fulltext был вызван с правильными параметрами
        repository._search_fulltext.assert_called_once_with(query, None, None, 50, 50)

    @pytest.mark.asyncio
    async def test_search_exact_no_matches(self, repository):
        """Тест когда нет точных совпадений"""
        query = "точный запрос"

        mock_document = SearchDocument(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            file_size=1024,
            file_path="/path/to/file.pdf",
            file_type="pdf",
            file_name="test.pdf",
        )

        mock_context = ContextInfo(
            text="Контекст без совпадений",
            offset=0,
            length=25,
            highlight_start=0,
            highlight_length=8,
        )

        # Мокаем результат без точных совпадений
        mock_fulltext_results = [
            SearchResult(
                document=mock_document,
                fragments=[
                    SearchFragment(
                        text="точные запросы", context=mock_context
                    ),  # Не точное
                    SearchFragment(
                        text="запрос точный", context=mock_context
                    ),  # Не точное
                ],
            )
        ]

        repository._search_fulltext = AsyncMock(return_value=mock_fulltext_results)

        # Выполняем тест
        results = await repository._search_exact(query)

        # Проверяем что результатов нет
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_search_exact_with_user_filter(self, repository):
        """Тест передачи фильтров в _search_fulltext"""
        query = "тест"
        user_id = uuid.uuid4()
        document_id = uuid.uuid4()
        context_size_before = 30
        context_size_after = 30

        repository._search_fulltext = AsyncMock(return_value=[])

        await repository._search_exact(
            query, user_id, document_id, context_size_before, context_size_after
        )

        # Проверяем что параметры переданы корректно
        repository._search_fulltext.assert_called_once_with(
            query, user_id, document_id, context_size_before, context_size_after
        )

    @pytest.mark.asyncio
    async def test_search_exact_handles_sqlalchemy_error(self, repository):
        """Тест обработки ошибок SQLAlchemy"""
        from sqlalchemy.exc import SQLAlchemyError

        from app.core.exceptions.repository import RepositoryError

        query = "тест"

        # Мокаем исключение
        repository._search_fulltext = AsyncMock(side_effect=SQLAlchemyError("DB Error"))

        # Проверяем что исключение правильно обработано
        with pytest.raises(RepositoryError) as exc_info:
            await repository._search_exact(query)

        assert "Ошибка при точном поиске" in str(exc_info.value)
