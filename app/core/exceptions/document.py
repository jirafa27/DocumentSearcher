class DocumentError(Exception):
    """Ошибка при работе с документом"""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"Ошибка при работе с документом: {reason}")


class DocumentNotFoundError(DocumentError):
    """Документ не найден"""

    def __init__(self, document_id: str):
        self.document_id = document_id
        super().__init__(f"Документ с ID {document_id} не найден")


class DocumentAlreadyExistsError(DocumentError):
    """Документ с таким хешем уже существует в базе данных"""

    def __init__(self, file_hash: str):
        self.file_hash = file_hash
        super().__init__(
            f"Документ с таким хешем {file_hash} уже существует в базе данных"
        )


class DocumentDatabaseError(DocumentError):
    """Ошибка базы данных при работе с документом"""

    def __init__(self, reason: str):
        super().__init__(f"Ошибка базы данных: {reason}")


class TextExtractionError(DocumentError):
    """Ошибка извлечения текста из документа"""

    def __init__(self, reason: str):
        super().__init__(f"Не удалось извлечь текст: {reason}")
