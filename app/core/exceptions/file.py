class FileError(Exception):
    """Ошибка при работе с файлом"""


class FileValidationError(FileError):
    """Ошибка валидации файла"""


class FileTooLargeError(FileValidationError):
    """Файл слишком большой"""

    def __init__(self, max_size: int):
        self.max_size = max_size
        super().__init__(
            f"Файл слишком большой. Максимальный размер: {max_size / 1024 / 1024:.1f}MB"
        )


class UnsupportedFileTypeError(FileValidationError):
    """Неподдерживаемый тип файла"""

    def __init__(self, allowed_types: list):
        self.allowed_types = allowed_types
        super().__init__(
            f"Неподдерживаемый тип файла. Разрешены: {', '.join(allowed_types)}"
        )


class TextExtractionError(FileError):
    """Ошибка извлечения текста из файла"""

    def __init__(self, file_path: str, reason: str = None):
        self.file_path = file_path
        self.reason = reason
        message = f"Не удалось извлечь текст из файла: {file_path}"
        if reason:
            message += f". Причина: {reason}"
        super().__init__(message)
