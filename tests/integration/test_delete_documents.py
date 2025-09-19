import uuid
from unittest.mock import patch

import pytest
from httpx import AsyncClient

from app.core.exceptions.document import DocumentDatabaseError


@pytest.mark.integration
@pytest.mark.database
class TestDocumentDelete:
    """Интеграционные тесты для эндпоинта удаления документов"""

    @pytest.mark.asyncio
    async def test_delete_document_success(
        self,
        test_client: AsyncClient,
        sample_file_docx,
        uploaded_files_checker,
        db_checker,
    ):
        """
        Тест успешного удаления документа
        Проверяем, что документ удаляется из БД и файловой системы
        """
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
        document_id = upload_response.json()["document"]["id"]

        # Проверяем, что файл и запись в БД созданы
        uploaded_files = uploaded_files_checker["get_files"]()
        assert len(uploaded_files) == 1

        docs_count = await db_checker["count_documents"]()
        content_count = await db_checker["count_contents"]()
        assert docs_count == 1
        assert content_count == 1

        # Удаляем документ
        response = await test_client.delete(f"/api/v1/documents/{document_id}")
        assert response.status_code == 200

        delete_data = response.json()
        assert "message" in delete_data
        assert delete_data["document_id"] == document_id

        # Проверяем, что документ удален из API
        get_response = await test_client.get(f"/api/v1/documents/{document_id}")
        assert get_response.status_code == 404

        # Проверяем, что файл удален из файловой системы
        files_after_delete = uploaded_files_checker["get_files"]()
        assert len(files_after_delete) == 0

        # Проверяем, что записи удалены из БД
        final_docs_count = await db_checker["count_documents"]()
        final_content_count = await db_checker["count_contents"]()
        assert final_docs_count == 0
        assert final_content_count == 0

    @pytest.mark.asyncio
    async def test_delete_nonexistent_document_error(self, test_client: AsyncClient):
        """
        Тест ошибки при удалении несуществующего документа
        Проверяем, что API корректно обрабатывает попытку удаления несуществующего документа
        """
        fake_document_id = str(uuid.uuid4())

        response = await test_client.delete(f"/api/v1/documents/{fake_document_id}")

        assert response.status_code == 404
        error_data = response.json()
        assert "detail" in error_data

    # === ТЕСТЫ ОБРАБОТКИ ОШИБОК ===

    @pytest.mark.asyncio
    async def test_delete_document_database_error(self, test_client: AsyncClient):
        """
        Тест обработки ошибки БД при удалении документа
        """
        fake_document_id = str(uuid.uuid4())

        # Мокаем DocumentService.delete_document чтобы выбросить ошибку БД
        with patch(
            "app.services.document_service.DocumentService.delete_document"
        ) as mock_delete:
            mock_delete.side_effect = DocumentDatabaseError("Ошибка БД при удалении")

            response = await test_client.delete(f"/api/v1/documents/{fake_document_id}")

            assert response.status_code == 500
            error_data = response.json()
            assert "detail" in error_data
            assert "Ошибка БД при удалении" in error_data["detail"]

    @pytest.mark.asyncio
    async def test_delete_document_unexpected_error(self, test_client: AsyncClient):
        """
        Тест обработки неожиданной ошибки при удалении документа
        """
        fake_document_id = str(uuid.uuid4())

        # Мокаем DocumentService.delete_document чтобы выбросить неожиданную ошибку
        with patch(
            "app.services.document_service.DocumentService.delete_document"
        ) as mock_delete:
            mock_delete.side_effect = Exception("Критическая ошибка удаления")

            response = await test_client.delete(f"/api/v1/documents/{fake_document_id}")

            assert response.status_code == 500
            error_data = response.json()
            assert "detail" in error_data
            assert "Неожиданная ошибка" in error_data["detail"]
