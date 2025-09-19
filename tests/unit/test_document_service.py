import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.core.exceptions.document import (
    DocumentAlreadyExistsError,
    DocumentDatabaseError,
    DocumentNotFoundError,
    DocumentValidationError,
)
from app.core.exceptions.file import FileDeleteError, FileValidationError
from app.core.exceptions.repository import RepositoryError
from app.core.models.document import DocumentBase
from app.core.models.file import FileContent
from app.core.models.search import (
    ContextInfo,
    SearchDocument,
    SearchFragment,
    SearchResult,
)
from app.services.document_service import DocumentService


@pytest.mark.unit
class TestDocumentService:
    """Unit тесты для DocumentService"""

    @pytest.fixture
    def mock_repository(self):
        """Мок репозитория документов"""
        return AsyncMock()

    @pytest.fixture
    def mock_file_service(self):
        """Мок файлового сервиса"""
        return AsyncMock()

    @pytest.fixture
    def document_service(self, mock_repository, mock_file_service):
        """Экземпляр DocumentService с моками"""
        return DocumentService(mock_repository, mock_file_service)

    @pytest.fixture
    def sample_file_content(self):
        """Тестовое содержимое файла"""
        return FileContent(
            filename="test.txt",
            content=b"Test document content",
            size=21,
            content_type="text/plain",
        )

    @pytest.fixture
    def sample_document(self):
        """Тестовый документ"""
        return DocumentBase(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            file_path="/test/path/file.txt",
            file_name="test.txt",
            file_size=21,
            file_type="txt",
            file_hash="abc123",
        )

    @pytest.mark.asyncio
    async def test_upload_document_success(
        self, document_service, mock_repository, mock_file_service, sample_file_content
    ):
        """Тест успешной загрузки документа"""
        user_id = uuid.uuid4()
        file_hash = "abc123"
        file_path = "/test/path/file.txt"
        extracted_content = "Test document content"

        # Настраиваем моки
        mock_file_service.calculate_hash.return_value = file_hash
        mock_repository.get_by_hash.return_value = None  # Документа нет
        mock_file_service.validate_file.return_value = None
        mock_file_service.save_file.return_value = file_path
        mock_file_service.extract_text.return_value = extracted_content

        created_document = DocumentBase(
            id=uuid.uuid4(),
            user_id=user_id,
            file_path=file_path,
            file_name=sample_file_content.filename,
            file_size=len(sample_file_content.get_content_bytes()),
            file_type="txt",
            file_hash=file_hash,
        )
        mock_repository.create.return_value = created_document

        # Выполняем тест
        result = await document_service.upload_document(sample_file_content, user_id)

        # Проверяем результат
        assert result == created_document

        # Проверяем вызовы моков
        mock_file_service.calculate_hash.assert_called_once()
        mock_repository.get_by_hash.assert_called_once_with(file_hash)
        mock_file_service.validate_file.assert_called_once()
        mock_file_service.save_file.assert_called_once()
        mock_file_service.extract_text.assert_called_once_with(file_path, "txt")
        mock_repository.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_document_already_exists(
        self,
        document_service,
        mock_repository,
        mock_file_service,
        sample_file_content,
        sample_document,
    ):
        """Тест ошибки при загрузке дубликата документа"""
        user_id = uuid.uuid4()
        file_hash = "abc123"

        # Настраиваем моки - документ уже существует
        mock_file_service.calculate_hash.return_value = file_hash
        mock_repository.get_by_hash.return_value = sample_document

        # Выполняем тест и ожидаем исключение
        with pytest.raises(DocumentAlreadyExistsError):
            await document_service.upload_document(sample_file_content, user_id)

        # Проверяем, что валидация и сохранение не вызывались
        mock_file_service.validate_file.assert_not_called()
        mock_file_service.save_file.assert_not_called()

    @pytest.mark.asyncio
    async def test_upload_document_validation_error(
        self, document_service, mock_repository, mock_file_service, sample_file_content
    ):
        """Тест ошибки валидации файла"""
        user_id = uuid.uuid4()
        file_hash = "abc123"

        # Настраиваем моки
        mock_file_service.calculate_hash.return_value = file_hash
        mock_repository.get_by_hash.return_value = None
        mock_file_service.validate_file.side_effect = FileValidationError(
            "Неподдерживаемый тип файла"
        )

        # Выполняем тест и ожидаем исключение
        with pytest.raises(DocumentValidationError):
            await document_service.upload_document(sample_file_content, user_id)

        # Проверяем, что сохранение не вызывалось
        mock_file_service.save_file.assert_not_called()

    @pytest.mark.asyncio
    async def test_upload_document_empty_content_error(
        self, document_service, mock_repository, mock_file_service, sample_file_content
    ):
        """Тест ошибки при пустом содержимом файла"""
        user_id = uuid.uuid4()
        file_hash = "abc123"
        file_path = "/test/path/file.txt"

        # Настраиваем моки - извлеченное содержимое пустое
        mock_file_service.calculate_hash.return_value = file_hash
        mock_repository.get_by_hash.return_value = None
        mock_file_service.validate_file.return_value = None
        mock_file_service.save_file.return_value = file_path
        mock_file_service.extract_text.return_value = ""  # Пустое содержимое

        # Мокаем os.path.exists чтобы файл "существовал"
        with patch("os.path.exists", return_value=True):
            # Выполняем тест и ожидаем исключение
            with pytest.raises(
                DocumentValidationError,
                match="Не удалось извлечь текст из файла или файл пуст",
            ):
                await document_service.upload_document(sample_file_content, user_id)

        # Проверяем, что файл был удален после ошибки
        mock_file_service.delete_file.assert_called_once_with(file_path)

    @pytest.mark.asyncio
    async def test_upload_document_repository_error(
        self, document_service, mock_repository, mock_file_service, sample_file_content
    ):
        """Тест ошибки репозитория при создании документа"""
        user_id = uuid.uuid4()
        file_hash = "abc123"
        file_path = "/test/path/file.txt"

        # Настраиваем моки
        mock_file_service.calculate_hash.return_value = file_hash
        mock_repository.get_by_hash.return_value = None
        mock_file_service.validate_file.return_value = None
        mock_file_service.save_file.return_value = file_path
        mock_file_service.extract_text.return_value = "Test content"
        mock_repository.create.side_effect = RepositoryError("Ошибка БД")

        # Мокаем os.path.exists чтобы файл "существовал"
        with patch("os.path.exists", return_value=True):
            # Выполняем тест и ожидаем исключение
            with pytest.raises(DocumentDatabaseError):
                await document_service.upload_document(sample_file_content, user_id)

        # Проверяем, что файл был удален после ошибки
        mock_file_service.delete_file.assert_called_once_with(file_path)

    @pytest.mark.asyncio
    async def test_upload_document_unexpected_error_cleanup(
        self, document_service, mock_repository, mock_file_service, sample_file_content
    ):
        """Тест очистки файла при неожиданной ошибке"""
        user_id = uuid.uuid4()
        file_hash = "abc123"
        file_path = "/test/path/file.txt"

        # Настраиваем моки
        mock_file_service.calculate_hash.return_value = file_hash
        mock_repository.get_by_hash.return_value = None
        mock_file_service.validate_file.return_value = None
        mock_file_service.save_file.return_value = file_path
        mock_file_service.extract_text.side_effect = Exception("Неожиданная ошибка")

        # Мокаем os.path.exists чтобы файл "существовал"
        with patch("os.path.exists", return_value=True):
            # Выполняем тест и ожидаем исключение
            with pytest.raises(Exception):
                await document_service.upload_document(sample_file_content, user_id)

        # Проверяем, что файл был удален после ошибки
        mock_file_service.delete_file.assert_called_once_with(file_path)

    @pytest.mark.asyncio
    async def test_get_document_success(
        self, document_service, mock_repository, sample_document
    ):
        """Тест успешного получения документа"""
        document_id = sample_document.id

        # Настраиваем мок
        mock_repository.get_by_id.return_value = sample_document

        # Выполняем тест
        result = await document_service.get_document(document_id)

        # Проверяем результат
        assert result == sample_document
        mock_repository.get_by_id.assert_called_once_with(document_id)

    @pytest.mark.asyncio
    async def test_get_document_not_found(self, document_service, mock_repository):
        """Тест ошибки при получении несуществующего документа"""
        document_id = uuid.uuid4()

        # Настраиваем мок - документ не найден
        mock_repository.get_by_id.return_value = None

        # Выполняем тест и ожидаем исключение
        with pytest.raises(DocumentNotFoundError):
            await document_service.get_document(document_id)

    @pytest.mark.asyncio
    async def test_get_document_repository_error(
        self, document_service, mock_repository
    ):
        """Тест ошибки репозитория при получении документа"""
        document_id = uuid.uuid4()

        # Настраиваем мок - ошибка репозитория
        mock_repository.get_by_id.side_effect = RepositoryError("Ошибка БД")

        # Выполняем тест и ожидаем исключение
        with pytest.raises(DocumentDatabaseError):
            await document_service.get_document(document_id)

    @pytest.mark.asyncio
    async def test_delete_document_success(
        self, document_service, mock_repository, mock_file_service, sample_document
    ):
        """Тест успешного удаления документа"""
        document_id = sample_document.id

        # Настраиваем моки
        mock_repository.get_by_id.return_value = sample_document
        mock_repository.delete.return_value = None
        mock_file_service.delete_file.return_value = None

        # Выполняем тест
        await document_service.delete_document(document_id)

        # Проверяем вызовы
        mock_repository.get_by_id.assert_called_once_with(document_id)
        mock_repository.delete.assert_called_once_with(document_id)
        mock_file_service.delete_file.assert_called_once_with(sample_document.file_path)

    @pytest.mark.asyncio
    async def test_delete_document_not_found(self, document_service, mock_repository):
        """Тест удаления несуществующего документа"""
        document_id = uuid.uuid4()

        # Настраиваем мок - документ не найден
        mock_repository.get_by_id.return_value = None

        # Выполняем тест и ожидаем исключение
        with pytest.raises(DocumentNotFoundError):
            await document_service.delete_document(document_id)

        # Проверяем, что delete не вызывался
        mock_repository.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_document_repository_error(
        self, document_service, mock_repository, sample_document
    ):
        """Тест ошибки репозитория при удалении документа"""
        document_id = sample_document.id

        # Настраиваем моки
        mock_repository.get_by_id.return_value = sample_document
        mock_repository.delete.side_effect = RepositoryError("Ошибка БД при удалении")

        # Выполняем тест и ожидаем исключение
        with pytest.raises(DocumentDatabaseError):
            await document_service.delete_document(document_id)

    @pytest.mark.asyncio
    async def test_delete_document_file_delete_error_ignored(
        self, document_service, mock_repository, mock_file_service, sample_document
    ):
        """Тест игнорирования ошибки удаления файла"""
        document_id = sample_document.id

        # Настраиваем моки - ошибка при удалении файла
        mock_repository.get_by_id.return_value = sample_document
        mock_repository.delete.return_value = None
        mock_file_service.delete_file.side_effect = FileDeleteError(
            "test.txt", "Ошибка удаления файла"
        )

        # Выполняем тест - ошибка файла должна игнорироваться
        await document_service.delete_document(document_id)

        # Проверяем, что репозиторий все равно вызвался
        mock_repository.delete.assert_called_once_with(document_id)

    @pytest.mark.asyncio
    async def test_search_success(self, document_service, mock_repository):
        """Тест успешного поиска документов"""
        query = "test query"
        user_id = uuid.uuid4()

        # Создаем мок результатов поиска
        mock_results = [
            SearchResult(
                document=SearchDocument(
                    id=uuid.uuid4(),
                    user_id=user_id,
                    file_size=100,
                    file_path="/test/path",
                    file_name="test.txt",
                    file_type="txt",
                ),
                fragments=[
                    SearchFragment(
                        text="test query found",
                        context=ContextInfo(
                            text="This is test query found in document",
                            offset=0,
                            length=35,
                            highlight_start=8,
                            highlight_length=10,
                        ),
                    )
                ],
            )
        ]

        # Настраиваем мок
        mock_repository.search.return_value = mock_results

        # Выполняем тест
        results = await document_service.search(query, user_id)

        # Проверяем результат
        assert results == mock_results
        mock_repository.search.assert_called_once_with(
            query, user_id, None, 50, 50, False
        )

    @pytest.mark.asyncio
    async def test_search_repository_error(self, document_service, mock_repository):
        """Тест ошибки репозитория при поиске"""
        query = "test query"

        # Настраиваем мок - ошибка репозитория
        mock_repository.search.side_effect = RepositoryError("Ошибка БД при поиске")

        # Выполняем тест и ожидаем исключение
        with pytest.raises(DocumentDatabaseError):
            await document_service.search(query)

    @pytest.mark.asyncio
    async def test_search_with_all_parameters(self, document_service, mock_repository):
        """Тест поиска со всеми параметрами"""
        query = "test query"
        user_id = uuid.uuid4()
        document_id = uuid.uuid4()
        context_before = 20
        context_after = 30
        search_exact = True

        # Настраиваем мок
        mock_repository.search.return_value = []

        # Выполняем тест
        await document_service.search(
            query, user_id, document_id, context_before, context_after, search_exact
        )

        # Проверяем вызов с правильными параметрами
        mock_repository.search.assert_called_once_with(
            query, user_id, document_id, context_before, context_after, search_exact
        )
