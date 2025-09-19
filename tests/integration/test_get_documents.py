import uuid
from unittest.mock import patch

import pytest
from httpx import AsyncClient

from app.core.exceptions.document import DocumentDatabaseError


@pytest.mark.integration
@pytest.mark.database
class TestDocumentGet:
    """Интеграционные тесты для эндпоинта получения документа"""

    @pytest.mark.asyncio
    async def test_get_document_success(
        self, test_client: AsyncClient, sample_file_docx, db_checker
    ):
        """
        Тест получения документа по ID
        Загружаем документ с помощью /api/v1/documents/upload
        и получаем его по ID с помощью /api/v1/documents/{document_id}
        """
        user_id = str(uuid.uuid4())

        # Сначала загружаем документ
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
        document_id = upload_response.json()["document"]["id"]

        # Получаем документ
        response = await test_client.get(f"/api/v1/documents/{document_id}")

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == document_id
        assert data["file_name"] == sample_file_docx["filename"]
        assert data["user_id"] == user_id
        assert data["file_type"] == "docx"
        assert "content" not in data  # content не должен возвращаться

        # Проверяем, что данные соответствуют БД
        db_document = await db_checker["get_document"](document_id)
        assert db_document is not None
        assert data["file_name"] == db_document.file_name
        assert data["file_type"] == db_document.file_type
        assert data["file_size"] == db_document.file_size

    @pytest.mark.asyncio
    async def test_get_nonexistent_document_error(self, test_client: AsyncClient):
        """
        Тест ошибки при получении несуществующего документа
        Проверяем, что API корректно возвращает 404 для несуществующего ID
        """
        fake_document_id = str(uuid.uuid4())

        response = await test_client.get(f"/api/v1/documents/{fake_document_id}")

        assert response.status_code == 404
        error_data = response.json()
        assert "detail" in error_data

    @pytest.mark.asyncio
    async def test_get_document_invalid_uuid(self, test_client: AsyncClient):
        """
        Тест ошибки при получении документа с невалидным UUID
        Проверяем, что API корректно обрабатывает невалидные UUID
        """
        invalid_uuid = "not-a-valid-uuid"

        response = await test_client.get(f"/api/v1/documents/{invalid_uuid}")

        assert response.status_code == 422  # Validation error
        error_data = response.json()
        assert "detail" in error_data

    # === ТЕСТЫ ОБРАБОТКИ ОШИБОК ===

    @pytest.mark.asyncio
    async def test_get_document_database_error(self, test_client: AsyncClient):
        """
        Тест обработки ошибки БД при получении документа
        Имитируем ошибку БД при получении документа по ID
        """
        fake_document_id = str(uuid.uuid4())

        # Мокаем DocumentService.get_document чтобы выбросить ошибку БД
        with patch(
            "app.services.document_service.DocumentService.get_document"
        ) as mock_get:
            mock_get.side_effect = DocumentDatabaseError(
                "Ошибка БД при получении документа"
            )

            response = await test_client.get(f"/api/v1/documents/{fake_document_id}")

            assert response.status_code == 500
            error_data = response.json()
            assert "detail" in error_data
            assert "Ошибка БД при получении документа" in error_data["detail"]

    @pytest.mark.asyncio
    async def test_get_document_unexpected_error(self, test_client: AsyncClient):
        """
        Тест обработки неожиданной ошибки при получении документа
        """
        fake_document_id = str(uuid.uuid4())

        # Мокаем DocumentService.get_document чтобы выбросить неожиданную ошибку
        with patch(
            "app.services.document_service.DocumentService.get_document"
        ) as mock_get:
            mock_get.side_effect = Exception("Критическая ошибка получения")

            response = await test_client.get(f"/api/v1/documents/{fake_document_id}")

            assert response.status_code == 500
            error_data = response.json()
            assert "detail" in error_data
            assert "Внутренняя ошибка сервера" in error_data["detail"]
