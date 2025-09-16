import asyncio
from app.repositories.document_repository import DocumentRepository
from app.core.database import get_async_session


async def test():
    session = await get_async_session()
    document_repository = DocumentRepository(session)
    result = await document_repository.search("менеджер", None, None, 50, True)
    print(result)
asyncio.run(test()) # type: ignore