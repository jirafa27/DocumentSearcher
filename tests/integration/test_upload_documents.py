import uuid
from unittest.mock import patch

import pytest
from httpx import AsyncClient

from app.core.exceptions.document import DocumentDatabaseError, DocumentValidationError


@pytest.mark.integration
@pytest.mark.database
class TestDocumentUpload:
    """Интеграционные тесты для эндпоинта загрузки документов"""

    @pytest.mark.asyncio
    async def test_upload_docx_document_success(
        self,
        test_client: AsyncClient,
        sample_file_docx,
        uploaded_files_checker,
        db_checker,
    ):
        """
        Тест успешной загрузки docx документа
        Загружаем docx документ с помощью /api/v1/documents/upload
        и проверяем, что он был сохранен в тестовой папке и БД
        и что в ответе получаем документ с корректными данными
        """
        user_id = str(uuid.uuid4())

        # Проверяем, что папка пуста перед загрузкой
        initial_files = uploaded_files_checker["get_files"]()
        assert len(initial_files) == 0

        # Проверяем, что БД пуста перед загрузкой
        initial_docs_count = await db_checker["count_documents"]()
        initial_content_count = await db_checker["count_contents"]()
        assert initial_docs_count == 0
        assert initial_content_count == 0

        response = await test_client.post(
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

        assert response.status_code == 200
        data = response.json()

        assert "message" in data
        assert "document" in data
        assert data["document"]["file_name"] == sample_file_docx["filename"]
        assert data["document"]["user_id"] == user_id
        assert data["document"]["file_type"] == "docx"
        assert "content" not in data["document"]  # content не должен возвращаться

        document_id = data["document"]["id"]

        # Проверяем, что файл был сохранен в тестовой папке
        uploaded_files = uploaded_files_checker["get_files"]()
        assert len(uploaded_files) == 1

        # Проверяем, что запись появилась в БД
        final_docs_count = await db_checker["count_documents"]()
        final_content_count = await db_checker["count_contents"]()
        assert final_docs_count == 1
        assert final_content_count == 1

        # Проверяем данные документа в БД
        db_document = await db_checker["get_document"](document_id)
        assert db_document is not None
        assert db_document.file_name == sample_file_docx["filename"]
        assert str(db_document.user_id) == user_id
        assert db_document.file_type == "docx"

        # Проверяем содержимое документа в БД
        db_content = await db_checker["get_content"](document_id)
        assert db_content is not None
        assert db_content.content is not None
        assert len(db_content.content.strip()) > 0  # Содержимое должно быть извлечено

    @pytest.mark.asyncio
    async def test_upload_pdf_document_success(
        self,
        test_client: AsyncClient,
        sample_file_pdf,
        uploaded_files_checker,
        db_checker,
    ):
        """
        Тест успешной загрузки PDF документа
        Загружаем документ с помощью /api/v1/documents/upload
        и проверяем, что он был сохранен в тестовой папке и БД
        и что в ответе получаем документ с корректными данными
        Проверяем, что PDF файл корректно загружается и обрабатывается
        """
        user_id = str(uuid.uuid4())

        # Проверяем, что папка пуста перед загрузкой
        initial_files = uploaded_files_checker["get_files"]()
        assert len(initial_files) == 0

        # Проверяем, что БД пуста перед загрузкой
        initial_docs_count = await db_checker["count_documents"]()
        initial_content_count = await db_checker["count_contents"]()
        assert initial_docs_count == 0
        assert initial_content_count == 0

        response = await test_client.post(
            "/api/v1/documents/upload",
            params={"user_id": user_id},
            files={
                "file": (
                    sample_file_pdf["filename"],
                    sample_file_pdf["content"],
                    sample_file_pdf["content_type"],
                )
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "message" in data
        assert "document" in data
        assert data["document"]["file_name"] == sample_file_pdf["filename"]
        assert data["document"]["user_id"] == user_id
        assert data["document"]["file_type"] == "pdf"
        assert "content" not in data["document"]  # content не должен возвращаться

        document_id = data["document"]["id"]

        # Проверяем, что файл был сохранен в тестовой папке
        uploaded_files = uploaded_files_checker["get_files"]()
        assert len(uploaded_files) == 1

        # Проверяем, что запись появилась в БД
        final_docs_count = await db_checker["count_documents"]()
        final_content_count = await db_checker["count_contents"]()
        assert final_docs_count == 1
        assert final_content_count == 1

        # Проверяем данные документа в БД
        db_document = await db_checker["get_document"](document_id)
        assert db_document is not None
        assert db_document.file_name == sample_file_pdf["filename"]
        assert str(db_document.user_id) == user_id
        assert db_document.file_type == "pdf"

        # Проверяем содержимое документа в БД
        db_content = await db_checker["get_content"](document_id)
        assert db_content is not None
        assert db_content.content is not None
        assert len(db_content.content.strip()) > 0  # Содержимое должно быть извлечено

    @pytest.mark.asyncio
    async def test_upload_invalid_format_error(
        self,
        test_client: AsyncClient,
        invalid_file_format,
        uploaded_files_checker,
        db_checker,
    ):
        """
        Тест ошибки при загрузке файла неподдерживаемого формата
        Проверяем, что система корректно отклоняет файлы с расширениями, которые не в ALLOWED_FILE_TYPES
        """
        user_id = str(uuid.uuid4())

        # Проверяем, что папка пуста перед попыткой загрузки
        initial_files = uploaded_files_checker["get_files"]()
        assert len(initial_files) == 0

        # Проверяем, что БД пуста перед попыткой загрузки
        initial_docs_count = await db_checker["count_documents"]()
        initial_content_count = await db_checker["count_contents"]()
        assert initial_docs_count == 0
        assert initial_content_count == 0

        response = await test_client.post(
            "/api/v1/documents/upload",
            params={"user_id": user_id},
            files={
                "file": (
                    invalid_file_format["filename"],
                    invalid_file_format["content"],
                    invalid_file_format["content_type"],
                )
            },
        )

        # Ожидаем ошибку валидации формата файла
        assert response.status_code == 400

        # Проверяем, что ошибка содержит поддерживаемые типы файлов
        error_data = response.json()
        assert "detail" in error_data
        assert "pdf" in error_data["detail"].lower()
        assert "docx" in error_data["detail"].lower()

        # Проверяем, что файл НЕ был сохранен в тестовой папке
        uploaded_files = uploaded_files_checker["get_files"]()
        assert len(uploaded_files) == 0

        # Проверяем, что запись НЕ появилась в БД
        final_docs_count = await db_checker["count_documents"]()
        final_content_count = await db_checker["count_contents"]()
        assert final_docs_count == 0
        assert final_content_count == 0

    @pytest.mark.asyncio
    async def test_upload_too_large_file_error(
        self,
        test_client: AsyncClient,
        invalid_file_too_large,
        uploaded_files_checker,
        db_checker,
    ):
        """
        Тест ошибки при загрузке файла, превышающего максимальный размер
        Проверяем, что система корректно отклоняет файлы больше MAX_FILE_SIZE (20MB)
        """
        user_id = str(uuid.uuid4())

        # Проверяем, что папка пуста перед попыткой загрузки
        initial_files = uploaded_files_checker["get_files"]()
        assert len(initial_files) == 0

        # Проверяем, что БД пуста перед попыткой загрузки
        initial_docs_count = await db_checker["count_documents"]()
        initial_content_count = await db_checker["count_contents"]()
        assert initial_docs_count == 0
        assert initial_content_count == 0

        response = await test_client.post(
            "/api/v1/documents/upload",
            params={"user_id": user_id},
            files={
                "file": (
                    invalid_file_too_large["filename"],
                    invalid_file_too_large["content"],
                    invalid_file_too_large["content_type"],
                )
            },
        )

        # Ожидаем ошибку превышения размера файла
        assert response.status_code == 400
        error_data = response.json()
        assert "detail" in error_data
        assert (
            "большой" in error_data["detail"].lower()
            or "size" in error_data["detail"].lower()
        )

        # Проверяем, что файл НЕ был сохранен в тестовой папке
        uploaded_files = uploaded_files_checker["get_files"]()
        assert len(uploaded_files) == 0

        # Проверяем, что запись НЕ появилась в БД
        final_docs_count = await db_checker["count_documents"]()
        final_content_count = await db_checker["count_contents"]()
        assert final_docs_count == 0
        assert final_content_count == 0

    @pytest.mark.asyncio
    async def test_duplicate_upload_error(
        self, test_client: AsyncClient, sample_file_docx
    ):
        """Тест ошибки при загрузке дубликата"""
        user_id = str(uuid.uuid4())

        # Первая загрузка
        response1 = await test_client.post(
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
        assert response1.status_code == 200

        # Попытка загрузить тот же файл
        response2 = await test_client.post(
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
        assert response2.status_code == 400  # Ошибка дубликата

        error_data = response2.json()
        assert "detail" in error_data

    # === ТЕСТЫ ОБРАБОТКИ ОШИБОК ===

    @pytest.mark.asyncio
    async def test_upload_database_error(self, test_client: AsyncClient, sample_file):
        """
        Тест обработки ошибки БД при загрузке документа
        Имитируем ошибку БД и проверяем, что API возвращает корректный HTTP 500
        """
        user_id = str(uuid.uuid4())

        # Мокаем DocumentService.upload_document чтобы выбросить ошибку БД
        with patch(
            "app.services.document_service.DocumentService.upload_document"
        ) as mock_upload:
            mock_upload.side_effect = DocumentDatabaseError("Ошибка подключения к БД")

            response = await test_client.post(
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

            assert response.status_code == 500
            error_data = response.json()
            assert "detail" in error_data
            assert "Ошибка подключения к БД" in error_data["detail"]

    @pytest.mark.asyncio
    async def test_upload_validation_error(self, test_client: AsyncClient, sample_file):
        """
        Тест обработки ошибки валидации при загрузке
        Имитируем ошибку валидации файла
        """
        user_id = str(uuid.uuid4())

        # Мокаем DocumentService.upload_document чтобы выбросить ошибку валидации
        with patch(
            "app.services.document_service.DocumentService.upload_document"
        ) as mock_upload:
            mock_upload.side_effect = DocumentValidationError("Файл поврежден или пуст")

            response = await test_client.post(
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

            assert response.status_code == 400
            error_data = response.json()
            assert "detail" in error_data
            assert "Файл поврежден или пуст" in error_data["detail"]

    @pytest.mark.asyncio
    async def test_upload_empty_filename_error(self, test_client: AsyncClient):
        """
        Тест обработки ошибки пустого имени файла
        Проверяем валидацию имени файла на уровне API
        """
        user_id = str(uuid.uuid4())

        response = await test_client.post(
            "/api/v1/documents/upload",
            params={"user_id": user_id},
            files={"file": ("", b"test content", "text/plain")},  # Пустое имя файла
        )

        assert response.status_code == 422  # Validation error from FastAPI
        error_data = response.json()
        assert "detail" in error_data

    @pytest.mark.asyncio
    async def test_upload_unexpected_error(self, test_client: AsyncClient, sample_file):
        """
        Тест обработки неожиданной ошибки при загрузке
        Имитируем неожиданное исключение
        """
        user_id = str(uuid.uuid4())

        # Мокаем DocumentService.upload_document чтобы выбросить неожиданную ошибку
        with patch(
            "app.services.document_service.DocumentService.upload_document"
        ) as mock_upload:
            mock_upload.side_effect = Exception("Неожиданная ошибка")

            response = await test_client.post(
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

            assert response.status_code == 500
            error_data = response.json()
            assert "detail" in error_data
            assert "Неожиданная ошибка" in error_data["detail"]
