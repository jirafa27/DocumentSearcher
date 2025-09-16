from abc import ABC, abstractmethod


class IFileService(ABC):
    @abstractmethod
    async def save_file(self, filename: str, content: bytes, file_hash: str) -> str:
        """
        Сохранение файла на диск

        Args:
            filename: str - оригинальное имя файла
            content: bytes - содержимое файла
            file_hash: str - SHA-256 хеш файла

        Returns:
            str: Путь к сохраненному файлу

        Raises:
            FileError: Если не удалось сохранить файл на диск
        """
        raise NotImplementedError

    @abstractmethod
    async def validate_file(self, filename: str, content: bytes) -> None:
        """
        Валидация файла. Проверяется тип файла и размер файла.

        Args:
            filename: str - имя файла
            content: bytes - содержимое файла

        Raises:
            UnsupportedFileTypeError: Если тип файла не поддерживается
            FileTooLargeError: Если файл слишком большой
        """
        raise NotImplementedError

    @abstractmethod
    async def calculate_hash(self, content: bytes) -> str:
        """
        Вычисление SHA-256 хеша содержимого.

        Args:
            content: bytes - содержимое для хеширования

        Returns:
            str: SHA-256 хеш в hex формате
        """
        raise NotImplementedError

    @abstractmethod
    async def extract_text(self, file_path: str, file_type: str) -> str:
        """
        Извлечение текста из файла

        Args:
            file_path: str - путь к файлу
            file_type: str - тип файла (pdf, docx)

        Returns:
            str: Извлеченный текст

        Raises:
            TextExtractionError: Если не удалось извлечь текст из файла
            FileNotFoundError: Если файл не найден
        """
        raise NotImplementedError

    @abstractmethod
    async def delete_file(self, file_path: str) -> None:
        """
        Удаление файла с диска

        Args:
            file_path: str - путь к файлу

        Raises:
            FileNotFoundError: Если файл не найден
            PermissionError: Если нет прав на удаление файла
        """
        raise NotImplementedError
