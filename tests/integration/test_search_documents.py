import uuid
from unittest.mock import patch

import pytest
from httpx import AsyncClient

from app.core.exceptions.document import DocumentDatabaseError


@pytest.mark.integration
@pytest.mark.database
class TestDocumentSearch:
    """Интеграционные тесты для эндпоинта поиска документов"""

    @pytest.mark.asyncio
    async def test_search_documents(self, test_client: AsyncClient, sample_file_docx):
        """Тест поиска по документам"""
        user_id = str(uuid.uuid4())

        # Загружаем документ
        await test_client.post(
            "/api/v1/documents/upload",
            params={"user_id": user_id},
            files={
                "file": (
                    sample_file_docx["filename"],
                    sample_file_docx["content"],
                    sample_file_docx["content_type"],
                )
            },
        )

        # Ищем по содержимому
        response = await test_client.get(
            "/api/v1/documents/search",
            params={"query": "Test document", "user_id": user_id},
        )

        assert response.status_code == 200
        data = response.json()

        assert "meta" in data
        assert "results" in data
        assert data["meta"]["total_documents"] >= 1
        assert len(data["results"]) >= 1

        # Проверяем структуру результатов поиска
        result = data["results"][0]
        assert "document" in result
        assert "fragments" in result
        assert result["document"]["file_name"] == sample_file_docx["filename"]

    @pytest.mark.asyncio
    async def test_search_with_filters(
        self, test_client: AsyncClient, sample_file_docx
    ):
        """Тест поиска с различными фильтрами"""
        user_id = str(uuid.uuid4())

        # Загружаем документ
        upload_response = await test_client.post(
            "/api/v1/documents/upload",
            params={"user_id": user_id},
            files={
                "file": (
                    sample_file_docx["filename"],
                    sample_file_docx["content"],
                    sample_file_docx["content_type"],
                )
            },
        )
        document_id = upload_response.json().get("document").get("id")

        # Поиск с фильтром по пользователю
        response = await test_client.get(
            "/api/v1/documents/search",
            params={
                "query": "Test document",
                "user_id": user_id,
                "context_size_before": 20,
                "context_size_after": 20,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["meta"]["total_documents"] >= 1

        # Поиск с фильтром по документу
        response = await test_client.get(
            "/api/v1/documents/search",
            params={"query": "Test document", "document_id": document_id},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["meta"]["total_documents"] == 1
        assert data["results"][0]["document"]["id"] == document_id

    @pytest.mark.asyncio
    async def test_search_exact_match(self, test_client: AsyncClient, sample_file):
        """Тест точного поиска"""
        user_id = str(uuid.uuid4())

        # Загружаем документ
        await test_client.post(
            "/api/v1/documents/upload",
            params={"user_id": user_id},
            files={
                "file": (
                    sample_file["filename"],
                    sample_file["content"],
                    sample_file["content_type"],
                )
            },
        )

        # Точный поиск
        response = await test_client.get(
            "/api/v1/documents/search",
            params={
                "query": "Test document content",
                "user_id": user_id,
                "search_exact": True,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "meta" in data
        assert "results" in data

    @pytest.mark.asyncio
    async def test_search_word_forms(
        self, test_client: AsyncClient, search_test_document
    ):
        """
        Тест поиска по словоформам
        Проверяем, что поиск находит разные формы одного слова
        """
        user_id = str(uuid.uuid4())

        # Загружаем специальный документ для поиска
        upload_response = await test_client.post(
            "/api/v1/documents/upload",
            params={"user_id": user_id},
            files={
                "file": (
                    search_test_document["filename"],
                    search_test_document["content"],
                    search_test_document["content_type"],
                )
            },
        )
        assert upload_response.status_code == 200

        # Тест 1: Поиск по базовой форме слова "продажа"
        response = await test_client.get(
            "/api/v1/documents/search", params={"query": "продажа", "user_id": user_id}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["meta"]["total_documents"] >= 1
        assert (
            data["meta"]["total_fragments"] >= 3
        )  # Должно найти: продаж, продажи, продажа

        # Проверяем содержимое найденных фрагментов
        found_fragments = []
        for result in data["results"]:
            for fragment in result["fragments"]:
                found_fragments.append(fragment["text"].lower())

        # Проверяем, что найдены разные формы слова "продажа"
        product_related = [f for f in found_fragments if "продаж" in f or "продав" in f]
        assert len(product_related) >= 2  # Минимум 2 разные формы

        # Тест 2: Поиск по другой форме "продажи"
        response = await test_client.get(
            "/api/v1/documents/search", params={"query": "продажи", "user_id": user_id}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["meta"]["total_documents"] >= 1
        assert data["meta"]["total_fragments"] >= 1

        # Проверяем, что найденные фрагменты содержат искомое слово
        for result in data["results"]:
            for fragment in result["fragments"]:
                fragment_text = fragment["text"].lower()
                assert "продаж" in fragment_text or "продав" in fragment_text

    @pytest.mark.asyncio
    async def test_search_exact_phrase(
        self, test_client: AsyncClient, search_test_document
    ):
        """
        Тест точного поиска фразы
        Проверяем разницу между обычным и точным поиском
        """
        user_id = str(uuid.uuid4())

        # Загружаем специальный документ для поиска
        upload_response = await test_client.post(
            "/api/v1/documents/upload",
            params={"user_id": user_id},
            files={
                "file": (
                    search_test_document["filename"],
                    search_test_document["content"],
                    search_test_document["content_type"],
                )
            },
        )
        assert upload_response.status_code == 200

        # Обычный поиск - должен найти слова в разных местах
        response_fuzzy = await test_client.get(
            "/api/v1/documents/search",
            params={
                "query": "специальный поисковый запрос",
                "user_id": user_id,
                "search_exact": False,
            },
        )

        assert response_fuzzy.status_code == 200
        fuzzy_data = response_fuzzy.json()

        # Точный поиск - должен найти только точную фразу
        response_exact = await test_client.get(
            "/api/v1/documents/search",
            params={
                "query": "специальный поисковый запрос",
                "user_id": user_id,
                "search_exact": True,
            },
        )

        assert response_exact.status_code == 200
        exact_data = response_exact.json()

        # Точный поиск должен найти меньше или равно фрагментов
        assert (
            exact_data["meta"]["total_fragments"]
            <= fuzzy_data["meta"]["total_fragments"]
        )
        assert exact_data["meta"]["total_documents"] >= 1

        # Проверяем содержимое найденных фрагментов в точном поиске
        for result in exact_data["results"]:
            for fragment in result["fragments"]:
                fragment_text = fragment["text"].lower()
                # В точном поиске должна быть найдена именно эта фраза
                assert "специальный поисковый запрос" in fragment_text

                # Проверяем структуру контекста
                context = fragment["context"]
                assert "text" in context
                assert "offset" in context
                assert "length" in context
                assert "highlight_start" in context
                assert "highlight_length" in context
                assert len(context["text"]) > 0

    @pytest.mark.asyncio
    async def test_search_context_sizes(
        self, test_client: AsyncClient, search_test_document
    ):
        """
        Тест разных размеров контекста
        Проверяем, что параметры context_size влияют на результат
        """
        user_id = str(uuid.uuid4())

        # Загружаем специальный документ для поиска
        upload_response = await test_client.post(
            "/api/v1/documents/upload",
            params={"user_id": user_id},
            files={
                "file": (
                    search_test_document["filename"],
                    search_test_document["content"],
                    search_test_document["content_type"],
                )
            },
        )
        assert upload_response.status_code == 200

        # Поиск с маленьким контекстом
        response_small = await test_client.get(
            "/api/v1/documents/search",
            params={
                "query": "контекст",
                "user_id": user_id,
                "context_size_before": 5,
                "context_size_after": 5,
            },
        )

        # Поиск с большим контекстом
        response_large = await test_client.get(
            "/api/v1/documents/search",
            params={
                "query": "контекст",
                "user_id": user_id,
                "context_size_before": 50,
                "context_size_after": 50,
            },
        )

        assert response_small.status_code == 200
        assert response_large.status_code == 200

        small_data = response_small.json()
        large_data = response_large.json()

        # Проверяем, что найдены фрагменты
        assert small_data["meta"]["total_fragments"] >= 1
        assert large_data["meta"]["total_fragments"] >= 1

        # Проверяем, что контекст в большом запросе длиннее
        if small_data["results"] and large_data["results"]:
            small_fragment = small_data["results"][0]["fragments"][0]
            large_fragment = large_data["results"][0]["fragments"][0]

            small_context = small_fragment["context"]["text"]
            large_context = large_fragment["context"]["text"]

            # Проверяем размеры контекста
            assert len(large_context) >= len(small_context)

            # Проверяем, что найденное слово присутствует в обоих фрагментах
            assert "контекст" in small_fragment["text"].lower()
            assert "контекст" in large_fragment["text"].lower()

            # Проверяем структуру контекста
            for fragment in [small_fragment, large_fragment]:
                context = fragment["context"]
                assert context["highlight_start"] >= 0
                assert context["highlight_length"] > 0
                assert context["offset"] >= 0
                assert context["length"] > 0
                assert context["highlight_start"] + context["highlight_length"] <= len(
                    context["text"]
                )

    @pytest.mark.asyncio
    async def test_search_fragment_structure(
        self, test_client: AsyncClient, search_test_document
    ):
        """
        Тест структуры фрагментов поиска
        Детально проверяем содержимое и структуру возвращаемых фрагментов
        """
        user_id = str(uuid.uuid4())

        # Загружаем специальный документ для поиска
        upload_response = await test_client.post(
            "/api/v1/documents/upload",
            params={"user_id": user_id},
            files={
                "file": (
                    search_test_document["filename"],
                    search_test_document["content"],
                    search_test_document["content_type"],
                )
            },
        )
        assert upload_response.status_code == 200

        # Поиск по слову "анализ"
        response = await test_client.get(
            "/api/v1/documents/search",
            params={
                "query": "анализ",
                "user_id": user_id,
                "context_size_before": 10,
                "context_size_after": 10,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["meta"]["total_documents"] >= 1
        assert data["meta"]["total_fragments"] >= 1

        # Детально проверяем структуру первого результата
        result = data["results"][0]

        # Проверяем структуру документа в результате
        document = result["document"]
        assert "id" in document
        assert "file_name" in document
        assert "file_type" in document
        assert "file_size" in document
        assert document["file_name"] == search_test_document["filename"]

        # Проверяем структуру фрагментов
        assert len(result["fragments"]) >= 1

        for fragment in result["fragments"]:
            # Проверяем поля фрагмента
            assert "text" in fragment
            assert "context" in fragment

            # Проверяем, что найденное слово есть в тексте фрагмента
            assert "анализ" in fragment["text"].lower()

            # Детально проверяем контекст
            context = fragment["context"]
            required_fields = [
                "text",
                "offset",
                "length",
                "highlight_start",
                "highlight_length",
            ]
            for field in required_fields:
                assert field in context, f"Поле {field} отсутствует в контексте"

            # Проверяем логическую корректность значений контекста
            assert isinstance(context["offset"], int) and context["offset"] >= 0
            assert isinstance(context["length"], int) and context["length"] > 0
            assert (
                isinstance(context["highlight_start"], int)
                and context["highlight_start"] >= 0
            )
            assert (
                isinstance(context["highlight_length"], int)
                and context["highlight_length"] > 0
            )

            # Проверяем, что выделение находится в пределах контекста
            highlight_end = context["highlight_start"] + context["highlight_length"]
            assert highlight_end <= len(context["text"])

            # Проверяем, что выделенный текст содержит искомое слово
            highlighted_text = context["text"][
                context["highlight_start"] : highlight_end
            ]
            assert "анализ" in highlighted_text.lower()

    # === ТЕСТЫ ОБРАБОТКИ ОШИБОК ===

    @pytest.mark.asyncio
    async def test_search_database_error(self, test_client: AsyncClient):
        """
        Тест обработки ошибки БД при поиске
        Имитируем ошибку БД во время поиска
        """
        # Мокаем DocumentService.search чтобы выбросить ошибку БД
        with patch(
            "app.services.document_service.DocumentService.search"
        ) as mock_search:
            mock_search.side_effect = DocumentDatabaseError(
                "Ошибка подключения к БД при поиске"
            )

            response = await test_client.get(
                "/api/v1/documents/search", params={"query": "test"}
            )

            assert response.status_code == 500
            error_data = response.json()
            assert "detail" in error_data
            assert "Ошибка подключения к БД при поиске" in error_data["detail"]

    @pytest.mark.asyncio
    async def test_search_unexpected_error(self, test_client: AsyncClient):
        """
        Тест обработки неожиданной ошибки при поиске
        Имитируем неожиданное исключение во время поиска
        """
        # Мокаем DocumentService.search чтобы выбросить неожиданную ошибку
        with patch(
            "app.services.document_service.DocumentService.search"
        ) as mock_search:
            mock_search.side_effect = Exception("Критическая ошибка поиска")

            response = await test_client.get(
                "/api/v1/documents/search", params={"query": "test"}
            )

            assert response.status_code == 500
            error_data = response.json()
            assert "detail" in error_data
            assert "Внутренняя ошибка сервера" in error_data["detail"]

    @pytest.mark.asyncio
    async def test_search_empty_query_validation(self, test_client: AsyncClient):
        """
        Тест валидации пустого поискового запроса
        Проверяем, что API корректно валидирует минимальную длину запроса
        """
        response = await test_client.get(
            "/api/v1/documents/search", params={"query": ""}  # Пустой запрос
        )

        assert response.status_code == 422  # Validation error
        error_data = response.json()
        assert "detail" in error_data

    @pytest.mark.asyncio
    async def test_search_no_results(self, test_client: AsyncClient):
        """
        Тест поиска без результатов
        Проверяем, что API корректно обрабатывает случай, когда ничего не найдено
        """
        response = await test_client.get(
            "/api/v1/documents/search",
            params={"query": "несуществующий_уникальный_запрос_12345"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["meta"]["total_documents"] == 0
        assert data["meta"]["total_fragments"] == 0
        assert len(data["results"]) == 0
