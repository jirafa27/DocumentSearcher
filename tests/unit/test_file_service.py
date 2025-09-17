import os
import pytest
import hashlib
from unittest.mock import patch
from app.core.exceptions.file import UnsupportedFileTypeError, FileTooLargeError
from app.services.file_service import FileService

class TestFileService:

    @pytest.fixture
    def file_service(self):
        return FileService()


    @pytest.mark.asyncio
    async def test_validate_file_supported_types(self, file_service):
        """Тест валидации поддерживаемых типов файлов"""
        # Эти тесты НЕ должны выбрасывать исключения
        await file_service.validate_file("test.pdf", b"content")
        await file_service.validate_file("test.docx", b"content")
        await file_service.validate_file("test.PDF", b"content")
        await file_service.validate_file("test.DOCX", b"content")
    
    @pytest.mark.asyncio
    async def test_validate_file_unsupported_types(self, file_service):
        """Тест валидации неподдерживаемых типов"""
        unsupported_types = ["txt", "exe", "jpg", "mp3", "html", "doc", "xls"]
        
        for file_type in unsupported_types:
            with pytest.raises(UnsupportedFileTypeError):
                await file_service.validate_file(f"test.{file_type}", b"content")
    
    @pytest.mark.asyncio
    async def test_validate_file_no_extension(self, file_service):
        """Тест валидации файла без расширения"""
        with pytest.raises(UnsupportedFileTypeError):
            await file_service.validate_file("filename_without_extension", b"content")
    
    @pytest.mark.asyncio
    async def test_validate_file_empty_filename(self, file_service):
        """Тест валидации пустого имени файла"""
        with pytest.raises(UnsupportedFileTypeError):
            await file_service.validate_file("", b"content")
    
    @pytest.mark.asyncio
    async def test_validate_file_exactly_max_size(self, file_service):
        """Тест файла точно максимального размера"""
        max_size_content = b"x" * file_service.max_file_size
        # НЕ должно выбросить исключение
        await file_service.validate_file("test.pdf", max_size_content)
    
    @pytest.mark.asyncio
    async def test_validate_file_file_too_large(self, file_service):
        """Тест, что файл с размером больше максимального вызывает исключение"""
        with pytest.raises(FileTooLargeError):
            await file_service.validate_file("test.docx", b"content" * 1024 * 1024 * 1024)

    
    @pytest.mark.asyncio
    async def test_calculate_hash_consistency(self, file_service):
        """Тест консистентности хеширования"""
        content = b"test content for hashing"
        hash1 = await file_service.calculate_hash(content)
        hash2 = await file_service.calculate_hash(content)
        
        assert hash1 == hash2
        assert len(hash1) == 64
        assert isinstance(hash1, str)
    
    @pytest.mark.asyncio
    async def test_calculate_hash_different_content(self, file_service):
        """Тест разных хешей для разного содержимого"""
        content1 = b"content1"
        content2 = b"content2"
        
        hash1 = await file_service.calculate_hash(content1)
        hash2 = await file_service.calculate_hash(content2)
        
        assert hash1 != hash2
    
    @pytest.mark.asyncio
    async def test_calculate_hash_empty_content(self, file_service):
        """Тест хеширования пустого содержимого"""
        hash_result = await file_service.calculate_hash(b"")
        
        # Проверяем что это правильный хеш пустой строки
        expected_hash = hashlib.sha256(b"").hexdigest()
        assert hash_result == expected_hash
        assert len(hash_result) == 64
    
    @pytest.mark.asyncio
    async def test_calculate_hash_large_content(self, file_service):
        """Тест хеширования большого содержимого"""
        large_content = b"x" * 100000
        hash_result = await file_service.calculate_hash(large_content)
        
        # Проверяем корректность
        expected_hash = hashlib.sha256(large_content).hexdigest()
        assert hash_result == expected_hash

    @pytest.mark.asyncio
    async def test_extract_text_supported_types_mocked(self, file_service):
        """Тест извлечения текста для поддерживаемых типов"""
        with patch.object(file_service, '_extract_text_from_pdf', return_value="PDF text content") as mock_pdf, \
             patch.object(file_service, '_extract_text_from_docx', return_value="DOCX text content") as mock_docx:
            
            # Тест PDF
            result_pdf = await file_service.extract_text("/path/to/file.pdf", "pdf")
            assert result_pdf == "PDF text content"
            
            mock_pdf.assert_called_once_with("/path/to/file.pdf")
            
            # Тест DOCX
            result_docx = await file_service.extract_text("/path/to/file.docx", "docx")
            assert result_docx == "DOCX text content"
            mock_docx.assert_called_once_with("/path/to/file.docx")

    @pytest.mark.asyncio
    async def test_extract_text_unsupported_types(self, file_service):
        """Тест всех неподдерживаемых типов"""
        unsupported_types = ["txt", "exe", "jpg", "mp3", "html"]
        
        for file_type in unsupported_types:
            with pytest.raises(UnsupportedFileTypeError):
                await file_service.extract_text(f"file.{file_type}", file_type)
    

    
    @pytest.mark.asyncio
    async def test_validate_file_multiple_extensions(self, file_service):
        """Тест файла с несколькими расширениями"""
        # Должно взять последнее расширение (.pdf)
        await file_service.validate_file("archive.backup.pdf", b"content")
        
        # Последнее расширение неподдерживаемое
        with pytest.raises(UnsupportedFileTypeError):
            await file_service.validate_file("document.pdf.txt", b"content")
    
    @pytest.mark.asyncio
    async def test_validate_file_edge_cases(self, file_service):
        """Тест граничных случаев имен файлов"""
        # Файл только с точкой
        with pytest.raises(UnsupportedFileTypeError):
            await file_service.validate_file(".", b"content")
        
        # Файл начинающийся с точки (скрытый файл)
        with pytest.raises(UnsupportedFileTypeError):
            await file_service.validate_file(".hidden", b"content")
        
        # Файл с точкой в конце
        with pytest.raises(UnsupportedFileTypeError):
            await file_service.validate_file("filename.", b"content")
